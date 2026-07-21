import { AlertTriangle, Archive, Ban, CalendarPlus, Check, CheckCircle2, Clock3, ListFilter, Loader2, Plus, Save, Search, Settings2, Trash2, UserMinus, X } from "lucide-react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  memo,
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { InterviewSessionModal } from "@/features/recruitment/InterviewSessionModal";
import { formValues, jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { useCanonicalTeacherRosterTotals } from "@/features/teacher-academy/TeacherAcademyRoster";
import {
  dateLabel,
  dateTimeLabel,
  humanize,
  recruitmentStageLabel,
  type RecruitmentAppointment,
  type RecruitmentCandidate,
  type RecruitmentOptions,
  type RecruitmentPipelineStage,
  type PipelineStageColorToken,
} from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  EmptyLine,
  PageState,
  buttonClass,
  fieldClass,
  queryError,
  rememberRecruitmentReturn,
  replaceUrlParams,
  restoreRecruitmentReturn,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { ActionMenu } from "@/shared/ui/ActionMenu";
import { Drawer } from "@/shared/ui/Drawer";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type PipelineData = {
  columns: RecruitmentPipelineStage[];
  stages: Record<string, RecruitmentCandidate[]>;
  counts: Record<string, number>;
  total: number;
};

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
type PipelineFilters = {
  search: string;
  position: string;
  source: string;
  subject_id: string;
  application_from: string;
  application_to: string;
  evaluator_account_id: string;
};
type RejectSelection = { candidate: RecruitmentCandidate };
type ScheduleSelection = { candidate: RecruitmentCandidate; appointmentType: "job_interview" | "demo_lesson" };
type RescheduleSelection = { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment };
type CancelSelection = { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment };
type UndoTrash = { candidate: RecruitmentCandidate; previousCandidate: RecruitmentCandidate };

type PipelineStagesData = {
  items: RecruitmentPipelineStage[];
  read_only: boolean;
  color_tokens: PipelineStageColorToken[];
};

const filterKeys: Array<keyof PipelineFilters> = [
  "search",
  "position",
  "source",
  "subject_id",
  "application_from",
  "application_to",
  "evaluator_account_id",
];

const stageColorStyles: Record<PipelineStageColorToken, { card: string; segment: string; legend: string; swatch: string }> = {
  neutral: { card: "border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-900/45", segment: "bg-slate-400", legend: "border border-slate-400 bg-slate-100", swatch: "bg-slate-400" },
  blue: { card: "border-blue-300 bg-blue-50 dark:border-blue-600/60 dark:bg-blue-950/30", segment: "bg-blue-600", legend: "bg-blue-600", swatch: "bg-blue-600" },
  cyan: { card: "border-cyan-300 bg-cyan-50 dark:border-cyan-600/60 dark:bg-cyan-950/30", segment: "bg-cyan-500", legend: "bg-cyan-500", swatch: "bg-cyan-500" },
  violet: { card: "border-violet-300 bg-violet-50 dark:border-violet-600/60 dark:bg-violet-950/30", segment: "bg-violet-600", legend: "bg-violet-600", swatch: "bg-violet-600" },
  green: { card: "border-emerald-300 bg-emerald-50 dark:border-emerald-600/60 dark:bg-emerald-950/30", segment: "bg-emerald-600", legend: "bg-emerald-600", swatch: "bg-emerald-600" },
  amber: { card: "border-amber-300 bg-amber-50 dark:border-amber-600/60 dark:bg-amber-950/30", segment: "bg-amber-500", legend: "bg-amber-500", swatch: "bg-amber-500" },
  orange: { card: "border-orange-300 bg-orange-50 dark:border-orange-600/60 dark:bg-orange-950/30", segment: "bg-orange-500", legend: "bg-orange-500", swatch: "bg-orange-500" },
  rose: { card: "border-rose-300 bg-rose-50 dark:border-rose-600/60 dark:bg-rose-950/30", segment: "bg-rose-500", legend: "bg-rose-500", swatch: "bg-rose-500" },
};

const canonicalSummaryColors: Record<string, PipelineStageColorToken> = {
  new_candidate: "neutral",
  responded: "blue",
  job_interview: "green",
  test_and_demo: "green",
  under_review: "violet",
  teacher_academy: "amber",
  active_teacher: "blue",
};

function initialFilters(): PipelineFilters {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(filterKeys.map((key) => [key, params.get(key) || ""])) as PipelineFilters;
}

function matchingAppointment(candidate: RecruitmentCandidate) {
  if (!["responded", "job_interview", "test_and_demo"].includes(candidate.status)) return null;
  // Sequential flow: interview bookings surface until the interview is passed,
  // then demo bookings take over.
  const expectedType = candidate.status === "test_and_demo" && candidate.latest_interview_result === "passed"
    ? "demo_lesson"
    : "job_interview";
  const active = (candidate.appointments || []).filter((item) => ["scheduled", "in_progress"].includes(item.status));
  return active.find((item) => item.appointment_type === expectedType)
    || active[0]
    || (candidate.next_appointment?.appointment_type === expectedType ? candidate.next_appointment : null);
}

function sortableTime(value?: string | null) {
  const parsed = value ? Date.parse(value) : Number.NaN;
  return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
}

function pipelineCardRecency(candidate: RecruitmentCandidate) {
  if (candidate.status === "new_candidate" || candidate.status_kind === "custom") {
    return sortableTime(candidate.application_date || candidate.stage_changed_at);
  }
  return sortableTime(candidate.stage_changed_at || candidate.application_date);
}

function sortPipelineCards(stageKey: string, candidates: RecruitmentCandidate[]) {
  return [...candidates].sort((left, right) => {
    if (["job_interview", "test_and_demo"].includes(stageKey)) {
      const leftAppointment = matchingAppointment(left);
      const rightAppointment = matchingAppointment(right);
      if (leftAppointment && rightAppointment) {
        const appointmentDifference = sortableTime(leftAppointment.starts_at) - sortableTime(rightAppointment.starts_at);
        if (appointmentDifference !== 0) return appointmentDifference;
      } else if (leftAppointment) {
        return -1;
      } else if (rightAppointment) {
        return 1;
      }
    }
    const recencyDifference = pipelineCardRecency(right) - pipelineCardRecency(left);
    return recencyDifference || right.id - left.id;
  });
}

function PipelineSummary({ counts, stages, action }: { counts: Record<string, number>; stages: RecruitmentPipelineStage[]; action?: ReactNode }) {
  const total = stages.reduce((sum, item) => sum + Number(counts[item.stage_key] || 0), 0);
  const values = stages.map((item) => {
    const colorToken = item.color_token || canonicalSummaryColors[item.stage_key] || "neutral";
    const count = Number(counts[item.stage_key] || 0);
    return {
      stage: item.stage_key,
      label: item.label,
      color: stageColorStyles[colorToken].segment,
      legend: stageColorStyles[colorToken].legend,
      count,
      rawPercentage: total ? count / total * 100 : 0,
      percentage: (total ? count / total * 100 : 0).toFixed(1),
    };
  });
  const summary = values.map((item) => `${item.label}: ${item.count} (${item.percentage}%)`).join(", ");
  return (
    <section className="rounded-xl border border-border bg-card px-3 py-1.5" aria-label={`Pipeline distribution. Total ${total}. ${summary}`}>
      <div className="flex items-center gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className="shrink-0 text-xs font-semibold text-foreground"><span className="text-muted-foreground">Total</span> <span className="tabular-nums">{total}</span></div>
          <div className="flex h-2 min-w-0 flex-1 overflow-hidden rounded-full border border-slate-300 bg-muted" aria-hidden="true">
            {values.filter((item) => item.count > 0).map((item) => (
              <span key={item.stage} className={`${item.color} first:rounded-l-full last:rounded-r-full`} style={{ width: `${item.rawPercentage}%` }} />
            ))}
          </div>
        </div>
        {action}
      </div>
      <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[10px] leading-4 text-muted-foreground sm:text-[11px]">
        {values.map((item) => (
          <li key={item.stage} className="inline-flex items-center gap-1.5 whitespace-nowrap">
            <span className={`h-2.5 w-2.5 rounded-sm ${item.legend}`} aria-hidden="true" />
            <span>{item.label}</span>
            <span className="font-semibold tabular-nums text-foreground">{item.percentage}%</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function FiltersDrawer({
  open,
  filters,
  options,
  onClose,
  onApply,
}: {
  open: boolean;
  filters: PipelineFilters;
  options?: RecruitmentOptions;
  onClose: () => void;
  onApply: (filters: PipelineFilters) => void;
}) {
  const [draft, setDraft] = useState(filters);
  useEffect(() => { if (open) setDraft(filters); }, [filters, open]);
  const update = (key: keyof PipelineFilters, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Pipeline filters"
      description="Filter every column and the percentage summary together."
      footer={<div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={onClose}>Cancel</button><button type="button" className={buttonClass} onClick={() => onApply(draft)}>Apply filters</button></div>}
    >
      <div className="grid gap-4">
        <label className="text-xs font-semibold">Position<select className={`${fieldClass} mt-1`} value={draft.position} onChange={(event) => update("position", event.target.value)}><option value="">All positions</option>{options?.option_categories.position?.map((position) => <option key={position.id} value={position.id}>{position.label}</option>)}</select></label>
        <label className="text-xs font-semibold">Source<select className={`${fieldClass} mt-1`} value={draft.source} onChange={(event) => update("source", event.target.value)}><option value="">All sources</option>{options?.sources.map((source) => <option key={source.id} value={source.id}>{source.label}</option>)}</select></label>
        <label className="text-xs font-semibold">Subject<select className={`${fieldClass} mt-1`} value={draft.subject_id} onChange={(event) => update("subject_id", event.target.value)}><option value="">All subjects</option>{options?.subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
        <div className="grid gap-2 sm:grid-cols-2"><label className="text-xs font-semibold">Applied from<input type="date" className={`${fieldClass} mt-1`} value={draft.application_from} onChange={(event) => update("application_from", event.target.value)} /></label><label className="text-xs font-semibold">Applied to<input type="date" className={`${fieldClass} mt-1`} value={draft.application_to} onChange={(event) => update("application_to", event.target.value)} /></label></div>
        <label className="text-xs font-semibold">Evaluator<select className={`${fieldClass} mt-1`} value={draft.evaluator_account_id} onChange={(event) => update("evaluator_account_id", event.target.value)}><option value="">All evaluators</option>{options?.staff.filter((person) => ["academic_director", "head_of_department"].includes(person.role)).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      </div>
    </Drawer>
  );
}

function StageColorPicker({ value, onChange }: { value: PipelineStageColorToken; onChange: (value: PipelineStageColorToken) => void }) {
  return (
    <fieldset>
      <legend className="text-xs font-semibold">Card color</legend>
      <div className="mt-1.5 flex flex-wrap gap-2">
        {(Object.keys(stageColorStyles) as PipelineStageColorToken[]).map((token) => (
          <label key={token} className={`flex h-11 min-w-11 cursor-pointer items-center justify-center rounded-lg border bg-card px-2 focus-within:ring-2 focus-within:ring-primary/35 ${value === token ? "border-primary ring-1 ring-primary/20" : "border-border"}`} title={humanize(token)}>
            <input className="sr-only" type="radio" name="color_token" value={token} checked={value === token} onChange={() => onChange(token)} />
            <span className={`h-5 w-5 rounded-full ${stageColorStyles[token].swatch}`} aria-hidden="true" />
            <span className="sr-only">{humanize(token)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function PipelineStageEditor({
  stage,
  stages,
  pending,
  readOnly,
  onSave,
  onArchive,
}: {
  stage: RecruitmentPipelineStage;
  stages: RecruitmentPipelineStage[];
  pending: boolean;
  readOnly: boolean;
  onSave: (stage: RecruitmentPipelineStage, values: { label: string; color_token?: PipelineStageColorToken; sla_target_days?: number; after_stage_key?: string }) => void;
  onArchive: (stage: RecruitmentPipelineStage) => void;
}) {
  const [label, setLabel] = useState(stage.label);
  const [color, setColor] = useState<PipelineStageColorToken>(stage.color_token);
  const [slaDays, setSlaDays] = useState(String(stage.sla_target_days || 1));
  const [afterStage, setAfterStage] = useState("");
  const custom = stage.stage_kind === "custom";
  if (readOnly) {
    return (
      <article className="rounded-xl border border-border bg-card p-3 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-2">
            <span className={`mt-1 h-3 w-3 shrink-0 rounded-full ${stageColorStyles[stage.color_token].swatch}`} aria-hidden="true" />
            <div className="min-w-0">
              <p className="break-words text-sm font-semibold">{stage.label}</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">{custom ? "Custom manual stage" : "Protected system stage"}</p>
            </div>
          </div>
          <span className="shrink-0 rounded-full bg-muted px-2 py-1 text-[10px] font-semibold">SLA {stage.sla_target_days || "—"}d</span>
        </div>
      </article>
    );
  }
  return (
    <form
      className="rounded-xl border border-border bg-card p-3 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(stage, {
          label,
          ...(custom ? { color_token: color, sla_target_days: Number(slaDays), ...(afterStage ? { after_stage_key: afterStage } : {}) } : {}),
        });
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{custom ? "Custom workflow stage" : "System workflow stage"}</p>
          <p className="mt-0.5 break-all text-[10px] text-muted-foreground">{stage.stage_key}</p>
        </div>
        <span className="rounded-full bg-muted px-2 py-1 text-[10px] font-semibold">SLA {stage.sla_target_days || "—"}d</span>
      </div>
      <label className="mt-3 block text-xs font-semibold">Column name<input required maxLength={80} className={`${fieldClass} mt-1`} value={label} onChange={(event) => setLabel(event.target.value)} /></label>
      {custom ? (
        <div className="mt-3 grid gap-3">
          <StageColorPicker value={color} onChange={setColor} />
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="text-xs font-semibold">SLA after application<input required type="number" min={1} max={90} className={`${fieldClass} mt-1`} value={slaDays} onChange={(event) => setSlaDays(event.target.value)} /><span className="mt-1 block text-[10px] font-normal text-muted-foreground">Calendar days in Asia/Tashkent.</span></label>
            <label className="text-xs font-semibold">Move after<select className={`${fieldClass} mt-1`} value={afterStage} onChange={(event) => setAfterStage(event.target.value)}><option value="">Keep current position</option>{stages.filter((item) => item.stage_key !== stage.stage_key).map((item) => <option key={item.stage_key} value={item.stage_key}>{item.label}</option>)}</select></label>
          </div>
        </div>
      ) : <p className="mt-2 text-[11px] text-muted-foreground">Renaming changes this stage label everywhere. Its workflow behavior and position stay protected.</p>}
      <div className="mt-3 flex flex-wrap justify-end gap-2">
        {custom ? <button type="button" className={`${secondaryButtonClass} text-destructive hover:text-destructive`} disabled={pending} onClick={() => onArchive(stage)}><Archive className="h-4 w-4" />Remove</button> : null}
        <button type="submit" className={buttonClass} disabled={pending || !label.trim()}>{pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}Save</button>
      </div>
    </form>
  );
}

function PipelineStagesDrawer({
  open,
  onClose,
  onAnnouncement,
}: {
  open: boolean;
  onClose: () => void;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const stagesQuery = useQuery({
    queryKey: ["recruitment", "pipeline-stages"],
    queryFn: () => recruitmentRequest<PipelineStagesData>(`${RECRUITMENT_API}/pipeline-stages`),
    enabled: open,
  });
  const stages = stagesQuery.data?.items || [];
  const readOnly = Boolean(stagesQuery.data?.read_only);
  const [createLabel, setCreateLabel] = useState("");
  const [createColor, setCreateColor] = useState<PipelineStageColorToken>("blue");
  const [createAfter, setCreateAfter] = useState("");
  const [createSla, setCreateSla] = useState("2");
  const [archiveStage, setArchiveStage] = useState<RecruitmentPipelineStage | null>(null);
  const [archiveDestination, setArchiveDestination] = useState("");

  useEffect(() => {
    if (!open || !stages.length) return;
    setCreateAfter((current) => current && stages.some((stage) => stage.stage_key === current) ? current : stages[stages.length - 1].stage_key);
  }, [open, stages]);

  const refresh = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["recruitment", "pipeline-stages"] }),
    queryClient.invalidateQueries({ queryKey: ["recruitment", "pipeline"] }),
    queryClient.invalidateQueries({ queryKey: ["recruitment", "options"] }),
    queryClient.invalidateQueries({ queryKey: ["hr-analytics"] }),
  ]);
  const createStage = useMutation({
    mutationFn: (values: Record<string, unknown>) => recruitmentRequest<{ message: string; stage: RecruitmentPipelineStage }>(`${RECRUITMENT_API}/pipeline-stages`, { method: "POST", body: jsonBody(values) }),
    onSuccess: (result) => { setCreateLabel(""); onAnnouncement(result.message || "Pipeline column created."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: refresh,
  });
  const updateStage = useMutation({
    mutationFn: ({ stage, values }: { stage: RecruitmentPipelineStage; values: Record<string, unknown> }) => recruitmentRequest<{ message: string; stage: RecruitmentPipelineStage }>(`${RECRUITMENT_API}/pipeline-stages/${encodeURIComponent(stage.stage_key)}`, { method: "PATCH", body: jsonBody({ ...values, expected_version: stage.version }) }),
    onSuccess: (result) => onAnnouncement(result.message || "Pipeline column updated."),
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: refresh,
  });
  const archive = useMutation({
    mutationFn: ({ stage, destination }: { stage: RecruitmentPipelineStage; destination: string }) => recruitmentRequest<{ message: string }>(`${RECRUITMENT_API}/pipeline-stages/${encodeURIComponent(stage.stage_key)}/archive`, { method: "POST", body: jsonBody({ expected_version: stage.version, replacement_stage_key: destination }) }),
    onSuccess: (result) => { setArchiveStage(null); setArchiveDestination(""); onAnnouncement(result.message || "Pipeline column removed."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: refresh,
  });
  const anyPending = createStage.isPending || updateStage.isPending || archive.isPending;

  return (
    <Drawer open={open} onClose={() => { if (!anyPending) onClose(); }} title="Pipeline columns" description="Rename system columns or add manual workflow stages. Automatic interview, demo, and test progression continues to use the protected system stages." widthClass="sm:max-w-2xl" footer={<div className="flex justify-end"><button type="button" className={secondaryButtonClass} disabled={anyPending} onClick={onClose}>Close</button></div>}>
      {stagesQuery.isLoading ? <PageState>Loading pipeline columns…</PageState> : stagesQuery.error ? <PageState tone="error">{queryError(stagesQuery.error)}</PageState> : (
        <div className="space-y-4">
          {!readOnly ? <form className="rounded-xl border border-primary/20 bg-primary/5 p-3" onSubmit={(event) => { event.preventDefault(); createStage.mutate({ label: createLabel, color_token: createColor, after_stage_key: createAfter, sla_target_days: Number(createSla) }); }}>
            <div className="flex items-center gap-2"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Plus className="h-4 w-4" /></div><div><h3 className="text-sm font-semibold">Add workflow stage</h3><p className="text-[11px] text-muted-foreground">Candidates enter this stage only when HR or CEO drags them here.</p></div></div>
            <div className="mt-3 grid gap-3">
              <label className="text-xs font-semibold">Column name<input autoFocus required maxLength={80} className={`${fieldClass} mt-1`} value={createLabel} onChange={(event) => setCreateLabel(event.target.value)} placeholder="For example: Reference Check" /></label>
              <StageColorPicker value={createColor} onChange={setCreateColor} />
              <div className="grid gap-2 sm:grid-cols-2">
                <label className="text-xs font-semibold">Insert after<select required className={`${fieldClass} mt-1`} value={createAfter} onChange={(event) => setCreateAfter(event.target.value)}>{stages.map((stage) => <option key={stage.stage_key} value={stage.stage_key}>{stage.label}</option>)}</select></label>
                <label className="text-xs font-semibold">SLA after application<input required type="number" min={1} max={90} className={`${fieldClass} mt-1`} value={createSla} onChange={(event) => setCreateSla(event.target.value)} /><span className="mt-1 block text-[10px] font-normal text-muted-foreground">Deadline = application date + calendar days.</span></label>
              </div>
            </div>
            <div className="mt-3 flex justify-end"><button type="submit" className={buttonClass} disabled={anyPending || !createLabel.trim() || !createAfter}>{createStage.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Add column</button></div>
          </form> : <div className="rounded-xl border border-border bg-muted/30 p-3 text-xs text-muted-foreground">You can review the live column order, labels, colors, and SLAs. Only the HR Manager can change pipeline columns.</div>}

          <section aria-labelledby="existing-pipeline-columns"><div className="mb-2 flex items-center justify-between gap-2"><div><h3 id="existing-pipeline-columns" className="text-sm font-semibold">Existing columns</h3><p className="text-[11px] text-muted-foreground">Shown in the same order as the board.</p></div><span className="rounded-full bg-muted px-2 py-1 text-xs font-semibold tabular-nums">{stages.length}</span></div><div className="grid gap-3">{stages.map((stage) => <PipelineStageEditor key={`${stage.stage_key}:${stage.version}`} stage={stage} stages={stages} pending={anyPending} readOnly={readOnly} onSave={(selected, values) => updateStage.mutate({ stage: selected, values })} onArchive={(selected) => { setArchiveStage(selected); setArchiveDestination(stages.find((item) => item.stage_key !== selected.stage_key)?.stage_key || ""); }} />)}</div></section>

          {archiveStage ? (
            <section role="alertdialog" aria-labelledby="archive-stage-title" className="sticky bottom-0 rounded-xl border border-destructive/30 bg-card p-3 shadow-card-hover">
              <h3 id="archive-stage-title" className="text-sm font-semibold text-destructive">Remove “{archiveStage.label}”?</h3>
              <p className="mt-1 text-xs text-muted-foreground">Candidates currently in this stage will be moved transactionally. Historical visits keep this stage name.</p>
              <label className="mt-3 block text-xs font-semibold">Move candidates to<select autoFocus required className={`${fieldClass} mt-1`} value={archiveDestination} onChange={(event) => setArchiveDestination(event.target.value)}>{stages.filter((stage) => stage.stage_key !== archiveStage.stage_key).map((stage) => <option key={stage.stage_key} value={stage.stage_key}>{stage.label}</option>)}</select></label>
              <div className="mt-3 flex flex-wrap justify-end gap-2"><button type="button" className={secondaryButtonClass} disabled={archive.isPending} onClick={() => setArchiveStage(null)}>Cancel</button><button type="button" className={`${buttonClass} bg-destructive text-destructive-foreground hover:bg-destructive/90`} disabled={archive.isPending || !archiveDestination} onClick={() => archive.mutate({ stage: archiveStage, destination: archiveDestination })}>{archive.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Archive className="h-4 w-4" />}Move and remove</button></div>
            </section>
          ) : null}
        </div>
      )}
    </Drawer>
  );
}

const CandidateCard = memo(function CandidateCard({
  candidate,
  basePath,
  onDragStart,
  onDragEnd,
  onSchedule,
  onInterview,
  onReschedule,
  onCancelAppointment,
  stage,
  compact = false,
}: {
  candidate: RecruitmentCandidate;
  basePath: string;
  onDragStart: (candidate: RecruitmentCandidate) => void;
  onDragEnd: () => void;
  onSchedule: (candidate: RecruitmentCandidate, appointmentType: "job_interview" | "demo_lesson") => void;
  onInterview: (candidate: RecruitmentCandidate, appointment: RecruitmentAppointment) => void;
  onReschedule: (candidate: RecruitmentCandidate, appointment: RecruitmentAppointment) => void;
  onCancelAppointment: (candidate: RecruitmentCandidate, appointment: RecruitmentAppointment) => void;
  stage?: RecruitmentPipelineStage;
  compact?: boolean;
}) {
  const canMove = Boolean(candidate.permissions?.can_move_stage) && !["teacher_academy", "active_teacher"].includes(candidate.status);
  const canManageAppointments = Boolean(candidate.permissions?.can_manage_appointments);
  const appointment = matchingAppointment(candidate);
  const interviewDone = candidate.latest_interview_result === "passed";
  // Buttons unlock one by one: interview first, then the demo lesson. The
  // Interview Schedule (responded) column shows no prompt — scheduling starts
  // at the Job Interview column (still available from the profile earlier).
  const unscheduledType = appointment
    ? null
    : candidate.status === "job_interview" && !interviewDone
      ? "job_interview"
      : candidate.status === "test_and_demo"
        ? (!interviewDone ? "job_interview" : !candidate.latest_demo_result ? "demo_lesson" : null)
        : null;
  // The application date belongs to the candidate, not to a workflow stage.
  // Keep it visible when the candidate enters a custom column (for example,
  // "Not Responding") while allowing operational stages to show their more
  // relevant appointment or stage-entry detail below.
  let detailLabel = "Applied";
  let detailValue = dateLabel(candidate.application_date);
  if (candidate.status === "responded") { detailLabel = "Responded"; detailValue = dateLabel(candidate.stage_changed_at); }
  if (appointment) { detailLabel = appointment.status === "in_progress" ? "Interview in progress" : appointment.appointment_type === "job_interview" ? "Job interview" : "Demo lesson"; detailValue = dateTimeLabel(appointment.started_at || appointment.starts_at); }
  if (candidate.status === "under_review") { detailLabel = "Under review since"; detailValue = dateLabel(candidate.stage_changed_at); }
  if (["teacher_academy", "active_teacher"].includes(candidate.status)) { detailLabel = "Accepted"; detailValue = dateLabel(candidate.final_decision_at || candidate.stage_changed_at); }

  const overdue = Boolean(appointment?.is_overdue);
  const evaluationStates = candidate.evaluation_states;
  // Truthful, record-backed states: a stage reached without a real evaluation
  // record reads as "missing" (red), never a fabricated "passed".
  const interviewMissing = candidate.status === "test_and_demo" && evaluationStates?.interview === "missing";
  const demoMissing = candidate.status === "under_review" && evaluationStates?.demo === "missing";
  const demoResult = candidate.status === "test_and_demo" ? candidate.latest_demo_result || "" : "";
  const demoPassed = demoResult === "passed";
  const passedInterview = candidate.status === "job_interview" && candidate.latest_interview_result === "passed" && !appointment;
  const alertState = interviewMissing || demoMissing;
  const customTone = stage?.stage_kind === "custom"
    ? stageColorStyles[stage.color_token || "neutral"].card
    : "border-border bg-card";
  const toneClass = alertState
    ? "border-red-400 bg-red-50 dark:border-red-500/50 dark:bg-red-950/25"
    : overdue
      ? "border-amber-400 bg-amber-50 dark:border-amber-500/50 dark:bg-amber-950/20"
    : passedInterview || demoPassed || candidate.status === "under_review"
        ? "border-emerald-400 bg-emerald-50 dark:border-emerald-500/50 dark:bg-emerald-950/20"
        : ["job_interview", "test_and_demo"].includes(candidate.status)
          ? "border-amber-400 bg-amber-50 dark:border-amber-500/50 dark:bg-amber-950/20"
          : customTone;
  if (overdue) { detailLabel = "Overdue"; detailValue = dateTimeLabel(appointment?.starts_at); }
  if (passedInterview) { detailLabel = "Interview passed"; detailValue = "Ready for the next stage"; }
  if (demoResult) { detailLabel = demoPassed ? "Demo lesson passed" : "Demo lesson evaluated"; detailValue = candidate.latest_demo_at ? dateTimeLabel(candidate.latest_demo_at) : detailValue; }
  const StatusIcon = alertState || overdue ? AlertTriangle : passedInterview || demoPassed || candidate.status === "under_review" ? CheckCircle2 : Clock3;
  const sla = candidate.current_sla;
  const slaLabel = sla ? (sla.status === "red" ? "SLA overdue" : `${Math.max(0, Math.ceil(sla.remaining_seconds / 86400))}d SLA left`) : "";
  const slaClass = sla?.status === "red" ? "bg-red-100 text-red-700 dark:bg-red-400/15 dark:text-red-200" : sla?.status === "yellow" ? "bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-100" : "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-100";
  const subjectKnowledgeWarning = candidate.status === "under_review" && evaluationStates?.subject_test !== "passed";
  const needsSubjectTest =
    candidate.status === "test_and_demo" &&
    demoPassed &&
    evaluationStates?.subject_test !== "passed";
  const chipBase = compact ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-1 text-[10px]";
  const emeraldChip = "bg-emerald-100 font-semibold text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-100";
  const redChip = "bg-red-100 font-semibold text-red-700 dark:bg-red-400/15 dark:text-red-200";

  return (
    <article
      data-candidate-card
      draggable={canMove}
      onDragStart={(event) => {
        if (!canMove) { event.preventDefault(); return; }
        event.dataTransfer.setData("text/plain", String(candidate.id));
        event.dataTransfer.effectAllowed = "move";
        onDragStart(candidate);
      }}
      onDragEnd={onDragEnd}
      className={`w-full min-w-0 overflow-hidden border shadow-sm transition-colors motion-reduce:transition-none hover:border-primary/40 focus-within:ring-2 focus-within:ring-primary/25 ${compact ? "rounded-md" : "rounded-lg"} ${toneClass} ${canMove ? "cursor-grab active:cursor-grabbing" : ""}`}
    >
      <a href={`${basePath}/candidates/${candidate.id}?tab=overview&origin=pipeline`} onClick={() => rememberRecruitmentReturn("pipeline")} className={`relative block focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30 ${compact ? "rounded-t-md px-2.5 pb-1.5 pt-2" : "rounded-t-lg px-3 pb-2 pt-3"}`} title={candidate.full_name}>
        <div className="flex min-w-0 items-start justify-between gap-1.5">
          <p className={`min-w-0 break-words font-semibold text-foreground ${compact ? "text-[13px] leading-4" : "text-sm"}`}>{candidate.full_name}</p>
          {sla ? <span className={`shrink-0 rounded-full text-right font-semibold leading-tight ${slaClass} ${compact ? "max-w-20 px-1.5 py-0.5 text-[9px]" : "max-w-24 px-2 py-1 text-[10px]"}`} title={`SLA due ${dateLabel(sla.due_at)}`}>{slaLabel}</span> : null}
        </div>
        <p className={`break-words text-muted-foreground ${compact ? "mt-0.5 text-[11px] leading-4" : "mt-1 text-xs"}`}>{candidate.applied_position || candidate.subject || "Position not set"}</p>
        {detailLabel ? <div className={`rounded-md bg-background/65 ${compact ? "mt-1.5 px-1.5 py-1 text-[11px] leading-4" : "mt-2 px-2 py-1.5 text-xs"}`}><span className="flex items-center gap-1.5 truncate font-semibold text-foreground"><StatusIcon className={`${compact ? "h-3 w-3" : "h-3.5 w-3.5"} shrink-0`} />{detailLabel}</span><span className={`block truncate text-muted-foreground ${compact ? "" : "mt-0.5"}`}>{detailValue}</span>{candidate.status === "test_and_demo" && appointment ? <span className={`${compact ? "mt-0.5" : "mt-1"} block text-muted-foreground`}><span className="block truncate">Evaluator: {appointment.responsible_name || "Not assigned"}</span>{appointment.topic ? <span className="block truncate">Topic: {appointment.topic}</span> : null}<span className={`block font-semibold ${overdue ? "text-red-700 dark:text-red-300" : "text-amber-800 dark:text-amber-200"}`}>{overdue ? "Overdue" : "Scheduled"}</span></span> : null}</div> : null}
        {candidate.status === "test_and_demo" ? (
          <div className={`flex flex-wrap gap-1 ${compact ? "mt-1" : "mt-2"}`}>
            {evaluationStates?.interview === "passed" ? <span className={`inline-flex rounded-full ${emeraldChip} ${chipBase}`}>Interview passed</span> : interviewMissing ? <span className={`inline-flex rounded-full ${redChip} ${chipBase}`}>No interview recorded</span> : null}
            {demoResult ? <span className={`inline-flex rounded-full ${demoPassed ? emeraldChip : redChip} ${chipBase}`}>{demoPassed ? "Demo passed" : "Demo not passed"}</span> : null}
          </div>
        ) : null}
        {candidate.status === "test_and_demo" && demoResult && candidate.latest_demo_note ? <p className={`mt-1 truncate italic text-muted-foreground ${compact ? "text-[10px] leading-4" : "text-[11px]"}`} title={candidate.latest_demo_note}>“{candidate.latest_demo_note}”</p> : null}
        {candidate.status === "under_review" ? <div className={`flex flex-wrap gap-1 ${compact ? "mt-1" : "mt-2"}`}><span className={`inline-flex rounded-full ${demoMissing ? redChip : emeraldChip} ${chipBase}`}>{demoMissing ? "No demo recorded" : "Demo passed"}</span><span className={`inline-flex rounded-full ${subjectKnowledgeWarning ? redChip : emeraldChip} ${chipBase}`}>{subjectKnowledgeWarning ? "Subject test missing/not passed" : "Subject test passed"}</span></div> : null}
      </a>
      {unscheduledType ? (
        <button type="button" draggable={false} onClick={(event) => { event.stopPropagation(); onSchedule(candidate, unscheduledType); }} className={`${compact ? "mx-1.5 mb-1.5 w-[calc(100%-0.75rem)] text-[11px]" : "mx-2 mb-2 w-[calc(100%-1rem)] text-xs"} flex min-h-9 items-center gap-2 rounded-md border border-amber-400/50 bg-amber-100 px-2 text-left font-semibold text-amber-900 transition-colors hover:bg-amber-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/40 dark:bg-amber-400/15 dark:text-amber-100`}>
          <CalendarPlus className="h-4 w-4 shrink-0" />{unscheduledType === "job_interview" ? "Interview not scheduled" : "Demo lesson not scheduled"}
        </button>
      ) : null}
      {appointment ? (
        <div draggable={false} onClick={(event) => event.stopPropagation()} className={`flex items-center gap-1.5 ${compact ? "mx-1.5 mb-1.5" : "mx-2 mb-2"}`}>
          {appointment.appointment_type === "job_interview" ? (
            <button type="button" draggable={false} onClick={(event) => { event.stopPropagation(); onInterview(candidate, appointment); }} className={`flex min-h-9 flex-1 items-center justify-center gap-2 rounded-md bg-primary px-2 font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${compact ? "text-[11px]" : "text-xs"}`}><Clock3 className="h-4 w-4" />{appointment.status === "in_progress" ? "Resume interview" : "Start interview"}</button>
          ) : (
            <span className={`flex min-h-9 flex-1 items-center gap-2 truncate rounded-md border border-amber-400/50 bg-amber-50 px-2 font-semibold text-amber-900 dark:bg-amber-400/10 dark:text-amber-100 ${compact ? "text-[11px]" : "text-xs"}`}><CalendarPlus className="h-4 w-4 shrink-0" /><span className="truncate">Demo scheduled</span></span>
          )}
          {canManageAppointments ? (
            <ActionMenu
              label="Appointment actions"
              items={[
                { key: "reschedule", label: "Reschedule", onClick: () => onReschedule(candidate, appointment) },
                { key: "cancel", label: "Cancel appointment", danger: true, onClick: () => onCancelAppointment(candidate, appointment) },
              ]}
            />
          ) : null}
        </div>
      ) : null}
      {needsSubjectTest ? (
        <a
          href={`${basePath}/candidates/${candidate.id}?tab=evaluations&origin=pipeline`}
          onClick={() => rememberRecruitmentReturn("pipeline")}
          className={`${compact ? "mx-1.5 mb-1.5 w-[calc(100%-0.75rem)] text-[11px]" : "mx-2 mb-2 w-[calc(100%-1rem)] text-xs"} flex min-h-9 items-center justify-center gap-2 rounded-md bg-primary px-2 font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40`}
        >
          <CheckCircle2 className="h-4 w-4" />
          Record subject test
        </a>
      ) : null}
    </article>
  );
});

export function PipelineView({
  basePath,
  options,
  canAddCandidate = false,
  canViewStageConfiguration = false,
  onAddCandidate,
  onAnnouncement,
}: {
  basePath: string;
  options?: RecruitmentOptions;
  canAddCandidate?: boolean;
  canViewStageConfiguration?: boolean;
  onAddCandidate?: () => void;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const initial = new URLSearchParams(window.location.search);
  const initialStage = initial.get("stage") || "new_candidate";
  const [mobileStage, setMobileStage] = useState(initialStage);
  const [filters, setFilters] = useState<PipelineFilters>(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [stageManagerOpen, setStageManagerOpen] = useState(false);
  const [boardPanning, setBoardPanning] = useState(false);
  const [draggedCandidate, setDraggedCandidate] = useState<RecruitmentCandidate | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [dragOverOutcome, setDragOverOutcome] = useState<"trash_bin" | "rejected" | "candidate_withdrew" | null>(null);
  const [rejectSelection, setRejectSelection] = useState<RejectSelection | null>(null);
  const [withdrawSelection, setWithdrawSelection] = useState<RejectSelection | null>(null);
  const [scheduleSelection, setScheduleSelection] = useState<ScheduleSelection | null>(null);
  const [rescheduleSelection, setRescheduleSelection] = useState<RescheduleSelection | null>(null);
  const [cancelSelection, setCancelSelection] = useState<CancelSelection | null>(null);
  const [interviewSelection, setInterviewSelection] = useState<{ candidate: RecruitmentCandidate; appointment: RecruitmentAppointment } | null>(null);
  const [undoTrash, setUndoTrash] = useState<UndoTrash | null>(null);
  const draggedCandidateRef = useRef<RecruitmentCandidate | null>(null);
  const searchTriggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const boardViewportRef = useRef<HTMLDivElement>(null);
  const boardScrollFrameRef = useRef<number | null>(null);
  const boardScrollTargetRef = useRef(0);
  const boardPanRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    scrollLeft: number;
    active: boolean;
  } | null>(null);
  const deferredSearch = useDeferredValue(filters.search);
  const teacherRosterTotals = useCanonicalTeacherRosterTotals();
  const requestParams = new URLSearchParams();
  Object.entries({ ...filters, search: deferredSearch }).forEach(([key, value]) => { if (value) requestParams.set(key, value); });
  const pipeline = useQuery({
    queryKey: ["recruitment", "pipeline", { ...filters, search: deferredSearch }],
    queryFn: () => recruitmentRequest<PipelineData>(`${RECRUITMENT_API}/pipeline${requestParams.size ? `?${requestParams}` : ""}`),
    placeholderData: keepPreviousData,
  });

  useEffect(() => {
    replaceUrlParams({ stage: mobileStage, ...filters });
  }, [filters, mobileStage]);
  useEffect(() => {
    if (pipeline.data) restoreRecruitmentReturn("pipeline");
  }, [pipeline.data]);
  useEffect(() => {
    const columns = pipeline.data?.columns || [];
    if (!columns.length || columns.some((stage) => stage.stage_key === mobileStage)) return;
    setMobileStage(columns[0].stage_key);
  }, [mobileStage, pipeline.data?.columns]);
  useEffect(() => {
    if (!undoTrash) return undefined;
    const timer = window.setTimeout(() => setUndoTrash(null), 5000);
    return () => window.clearTimeout(timer);
  }, [undoTrash]);
  useEffect(() => () => {
    if (boardScrollFrameRef.current !== null) {
      window.cancelAnimationFrame(boardScrollFrameRef.current);
    }
  }, []);

  const closeSearch = useCallback((event?: KeyboardEvent | PointerEvent) => {
    setSearchOpen(false);
    if (!event || event instanceof KeyboardEvent) {
      window.requestAnimationFrame(() => searchTriggerRef.current?.focus());
    }
  }, []);
  const searchLayerRef = useDismissibleLayer<HTMLDivElement>({
    enabled: searchOpen,
    onDismiss: closeSearch,
  });
  useEffect(() => {
    if (!searchOpen) return;
    window.requestAnimationFrame(() => searchInputRef.current?.focus());
  }, [searchOpen]);

  const move = useMutation({
    mutationFn: ({ candidate, stage }: { candidate: RecruitmentCandidate; stage: string }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/stage`, { method: "POST", body: jsonBody({ stage, expected_version: candidate.version, reason: "Pipeline move" }) }),
    onMutate: async ({ candidate, stage }) => {
      await queryClient.cancelQueries({ queryKey: ["recruitment", "pipeline"] });
      const entries = queryClient.getQueriesData<PipelineData>({ queryKey: ["recruitment", "pipeline"] });
      entries.forEach(([key, previous]) => {
        if (!previous) return;
        const stages = Object.fromEntries(Object.entries(previous.stages).map(([name, values]) => [name, values.filter((item) => item.id !== candidate.id)]));
        const target = previous.columns.find((item) => item.stage_key === stage);
        const movedCandidate = { ...candidate, status: stage, status_label: target?.label, status_kind: target?.stage_kind, status_color_token: target?.color_token, stage_changed_at: new Date().toISOString(), next_appointment: null, version: candidate.version + 1 };
        stages[stage] = sortPipelineCards(stage, [movedCandidate, ...(stages[stage] || [])]);
        queryClient.setQueryData(key, { ...previous, stages, counts: Object.fromEntries(Object.entries(stages).map(([name, values]) => [name, values.length])) });
      });
      return { entries };
    },
    onError: (error, _variables, context) => {
      context?.entries.forEach(([key, previous]) => queryClient.setQueryData(key, previous));
      onAnnouncement(`Move failed. ${queryError(error)}`, "error");
    },
    onSuccess: (result, variables) => {
      onAnnouncement(result.message || "Candidate moved.");
      if (variables.stage === "trash_bin" && result.candidate) setUndoTrash({ candidate: result.candidate, previousCandidate: variables.candidate });
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const reject = useMutation({
    mutationFn: ({ candidate, values }: { candidate: RecruitmentCandidate; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/final-decisions`, { method: "POST", body: jsonBody({ decision: "rejected", ...values }) }),
    onSuccess: (result) => { setRejectSelection(null); onAnnouncement(result.message || "Candidate rejected."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const withdraw = useMutation({
    mutationFn: ({ candidate, values }: { candidate: RecruitmentCandidate; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/final-decisions`, { method: "POST", body: jsonBody({ decision: "candidate_withdrew", ...values }) }),
    onSuccess: (result) => { setWithdrawSelection(null); onAnnouncement(result.message || "Candidate marked as withdrawn."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const schedule = useMutation({
    mutationFn: ({ candidate, appointmentType, values }: { candidate: RecruitmentCandidate; appointmentType: ScheduleSelection["appointmentType"]; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments`, { method: "POST", body: jsonBody({ ...values, appointment_type: appointmentType }) }),
    onSuccess: (result) => { setScheduleSelection(null); onAnnouncement(result.message || "Appointment scheduled."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const reschedule = useMutation({
    mutationFn: ({ candidate, appointment, values }: { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${appointment.id}`, { method: "PATCH", body: jsonBody({ ...values, expected_version: appointment.version }) }),
    onSuccess: (result) => { setRescheduleSelection(null); onAnnouncement(result.message || "Appointment rescheduled."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const cancelAppointment = useMutation({
    mutationFn: ({ candidate, appointment, values }: { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${appointment.id}/cancel`, { method: "POST", body: jsonBody({ ...values, expected_version: appointment.version }) }),
    onSuccess: (result) => { setCancelSelection(null); onAnnouncement(result.message || "Appointment cancelled."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const activeAdvanced = filterKeys.filter((key) => key !== "search" && Boolean(filters[key]));
  const activeFilterCount = activeAdvanced.length + (filters.search ? 1 : 0);
  const clearFilters = () => setFilters(Object.fromEntries(filterKeys.map((key) => [key, ""])) as PipelineFilters);
  const closeFilters = () => {
    setFiltersOpen(false);
    window.requestAnimationFrame(() => searchTriggerRef.current?.focus());
  };
  const finishDrag = useCallback(() => { draggedCandidateRef.current = null; setDraggedCandidate(null); setDragOverStage(null); setDragOverOutcome(null); }, []);
  const handleCardDragStart = useCallback((value: RecruitmentCandidate) => { draggedCandidateRef.current = value; setDraggedCandidate(value); }, []);
  const handleCardSchedule = useCallback((value: RecruitmentCandidate, appointmentType: "job_interview" | "demo_lesson") => { setScheduleSelection({ candidate: value, appointmentType }); }, []);
  const handleCardInterview = useCallback((value: RecruitmentCandidate, appointment: RecruitmentAppointment) => setInterviewSelection({ candidate: value, appointment }), []);
  const handleCardReschedule = useCallback((value: RecruitmentCandidate, appointment: RecruitmentAppointment) => { setRescheduleSelection({ candidate: value, appointment }); }, []);
  const handleCardCancelAppointment = useCallback((value: RecruitmentCandidate, appointment: RecruitmentAppointment) => setCancelSelection({ candidate: value, appointment }), []);

  const canStartBoardPan = (target: EventTarget | null) => {
    if (!(target instanceof Element)) return true;
    return !target.closest("[data-candidate-card], a, button, input, select, textarea, [role='menu'], [role='dialog']");
  };
  const stopBoardScrollAnimation = useCallback(() => {
    if (boardScrollFrameRef.current !== null) {
      window.cancelAnimationFrame(boardScrollFrameRef.current);
      boardScrollFrameRef.current = null;
    }
    boardScrollTargetRef.current = boardViewportRef.current?.scrollLeft || 0;
  }, []);
  const smoothScrollBoardBy = useCallback((delta: number) => {
    const viewport = boardViewportRef.current;
    if (!viewport) return false;
    const maxScrollLeft = Math.max(0, viewport.scrollWidth - viewport.clientWidth);
    const currentTarget = boardScrollFrameRef.current === null
      ? viewport.scrollLeft
      : boardScrollTargetRef.current;
    const nextTarget = Math.min(maxScrollLeft, Math.max(0, currentTarget + delta));
    if (Math.abs(nextTarget - currentTarget) < 0.5) return false;
    boardScrollTargetRef.current = nextTarget;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      viewport.scrollLeft = nextTarget;
      return true;
    }
    if (boardScrollFrameRef.current === null) {
      const move = () => {
        const activeViewport = boardViewportRef.current;
        if (!activeViewport) {
          boardScrollFrameRef.current = null;
          return;
        }
        const remaining = boardScrollTargetRef.current - activeViewport.scrollLeft;
        if (Math.abs(remaining) < 0.75) {
          activeViewport.scrollLeft = boardScrollTargetRef.current;
          boardScrollFrameRef.current = null;
          return;
        }
        activeViewport.scrollLeft += remaining * 0.24;
        boardScrollFrameRef.current = window.requestAnimationFrame(move);
      };
      boardScrollFrameRef.current = window.requestAnimationFrame(move);
    }
    return true;
  }, []);
  const startBoardPan = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || !canStartBoardPan(event.target)) return;
    stopBoardScrollAnimation();
    boardPanRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      scrollLeft: event.currentTarget.scrollLeft,
      active: false,
    };
  };
  const moveBoardPan = (event: ReactPointerEvent<HTMLDivElement>) => {
    const pan = boardPanRef.current;
    if (!pan || pan.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - pan.startX;
    const deltaY = event.clientY - pan.startY;
    if (!pan.active) {
      if (Math.abs(deltaX) < 6 || Math.abs(deltaX) <= Math.abs(deltaY)) return;
      pan.active = true;
      event.currentTarget.setPointerCapture(event.pointerId);
      setBoardPanning(true);
    }
    event.currentTarget.scrollLeft = pan.scrollLeft - deltaX;
    event.preventDefault();
  };
  const finishBoardPan = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (boardPanRef.current?.pointerId !== event.pointerId) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    boardPanRef.current = null;
    boardScrollTargetRef.current = event.currentTarget.scrollLeft;
    setBoardPanning(false);
  };
  const scrollWheelBoard = useCallback((event: WheelEvent) => {
    const verticalIntent = Math.abs(event.deltaY) >= Math.abs(event.deltaX);
    const columnScroller = event.target instanceof Element
      ? event.target.closest<HTMLElement>("[data-pipeline-column-scroll]")
      : null;
    // A vertical gesture that starts inside a column always belongs to that
    // column, even when it has reached its top or bottom. Converting the
    // leftover delta at an edge made the board jump sideways unexpectedly.
    if (columnScroller && verticalIntent && !event.shiftKey) return;
    const rawDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE
      ? 16
      : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
        ? boardViewportRef.current?.clientWidth || window.innerWidth
        : 1;
    if (!rawDelta || !smoothScrollBoardBy(rawDelta * unit)) return;
    event.preventDefault();
    event.stopPropagation();
  }, [smoothScrollBoardBy]);
  useEffect(() => {
    const viewport = boardViewportRef.current;
    if (!viewport) return undefined;
    viewport.addEventListener("wheel", scrollWheelBoard, { passive: false });
    return () => viewport.removeEventListener("wheel", scrollWheelBoard);
  }, [pipeline.data, scrollWheelBoard]);

  const cards = useCallback((items: RecruitmentCandidate[], compact = false, stage?: RecruitmentPipelineStage) => (
    <div className={compact ? "space-y-1.5" : "space-y-2"}>
      {items.map((candidate) => <CandidateCard key={candidate.id} candidate={candidate} stage={stage} basePath={basePath} onDragStart={handleCardDragStart} onDragEnd={finishDrag} onSchedule={handleCardSchedule} onInterview={handleCardInterview} onReschedule={handleCardReschedule} onCancelAppointment={handleCardCancelAppointment} compact={compact} />)}
      {!items.length ? <EmptyLine>No candidates in this stage.</EmptyLine> : null}
    </div>
  ), [basePath, handleCardDragStart, finishDrag, handleCardSchedule, handleCardInterview, handleCardReschedule, handleCardCancelAppointment]);

  const data = pipeline.data;
  const summaryCounts = useMemo(() => ({
    ...(pipeline.data?.counts || {}),
    teacher_academy: teacherRosterTotals.teacher_academy,
    active_teacher: teacherRosterTotals.active_teacher,
  }), [
    pipeline.data?.counts,
    teacherRosterTotals.active_teacher,
    teacherRosterTotals.teacher_academy,
  ]);
  const summaryStages = useMemo(() => {
    const active = data?.columns || [];
    const terminal = (options?.stage_definitions || []).filter((stage) => ["teacher_academy", "active_teacher"].includes(stage.stage_key));
    return [...active, ...terminal];
  }, [data?.columns, options?.stage_definitions]);
  const moveMutate = move.mutate;
  const desktopBoard = useMemo(() => {
    if (!data) return null;
    return (
      <div className="grid w-full gap-2 2xl:gap-2" style={{ gridTemplateColumns: `repeat(${data.columns.length}, minmax(15rem, 1fr))`, minWidth: `max(100%, ${data.columns.length * 15}rem)` }}>
        {data.columns.map((stage) => {
          const acceptsDrop = true;
          const highlighted = dragOverStage === stage.stage_key;
          const items = data.stages[stage.stage_key] || [];
          return (
            <section key={stage.stage_key} aria-label={`${stage.label} candidates`} onDragEnter={(event) => { if (acceptsDrop && draggedCandidateRef.current) { event.preventDefault(); setDragOverStage(stage.stage_key); } }} onDragOver={(event) => { if (acceptsDrop && draggedCandidateRef.current) event.preventDefault(); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverStage(null); }} onDrop={(event) => { event.preventDefault(); setDragOverStage(null); const candidate = draggedCandidateRef.current; finishDrag(); if (!candidate || candidate.status === stage.stage_key || !acceptsDrop) return; moveMutate({ candidate, stage: stage.stage_key }); }} className={`flex min-w-0 h-[calc(100dvh-9.75rem)] min-h-[32rem] flex-col overflow-hidden rounded-t-xl border-x border-t transition-colors motion-reduce:transition-none ${highlighted ? "border-primary bg-primary/5 ring-2 ring-primary/15" : "border-border bg-muted/25"}`}>
              <div className="flex min-h-12 shrink-0 items-center justify-between gap-2 border-b border-border bg-muted/95 px-2"><div className="flex min-w-0 items-center gap-1.5">{stage.stage_key === "new_candidate" && canAddCandidate && onAddCandidate ? <button type="button" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-primary transition-colors hover:bg-card focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" onClick={onAddCandidate} aria-label="Add candidate" title="Add candidate"><Plus className="h-4 w-4" /></button> : null}{stage.stage_kind === "custom" ? <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${stageColorStyles[stage.color_token].swatch}`} aria-hidden="true" /> : null}<h2 className="break-words text-[11px] font-semibold uppercase leading-4 tracking-wide text-foreground">{stage.label}</h2></div><span className="rounded-full bg-card px-2 py-1 text-[11px] font-semibold text-muted-foreground tabular-nums">{items.length}</span></div>
              <div data-pipeline-column-scroll className="miniapp-scroll flex-1 overflow-y-auto overscroll-y-contain p-1.5">{cards(items, true, stage)}</div>
            </section>
          );
        })}
      </div>
    );
  }, [data, dragOverStage, canAddCandidate, onAddCandidate, cards, moveMutate, finishDrag]);
  const mobileStageDefinition = data?.columns.find((stage) => stage.stage_key === mobileStage);
  const mobileCards = useMemo(() => (data ? cards(data.stages[mobileStage] || [], false, mobileStageDefinition) : null), [data, mobileStage, mobileStageDefinition, cards]);

  if (pipeline.isLoading || teacherRosterTotals.isLoading) return <PageState>Loading recruitment pipeline…</PageState>;
  if (pipeline.error || !pipeline.data) return <PageState tone="error">{queryError(pipeline.error)}</PageState>;

  return (
    <div className="min-w-0 max-w-full space-y-2 overflow-x-clip">
      <PipelineSummary
        counts={summaryCounts}
        stages={summaryStages}
        action={(
          <div className="flex shrink-0 items-center gap-1.5">
            {canViewStageConfiguration ? <button type="button" className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" onClick={() => setStageManagerOpen(true)} aria-label="View pipeline columns" title="Pipeline columns"><Settings2 className="h-4 w-4" /></button> : null}
          <div ref={searchLayerRef} className="relative">
            <button
              ref={searchTriggerRef}
              type="button"
              className={`relative flex h-9 w-9 items-center justify-center rounded-lg border bg-card text-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${activeFilterCount ? "border-primary text-primary" : "border-border"}`}
              aria-label={`Search and filters${activeFilterCount ? `, ${activeFilterCount} active` : ""}`}
              aria-expanded={searchOpen}
              aria-controls="pipeline-search-popover"
              onClick={() => setSearchOpen((open) => !open)}
              title="Search and filters"
            >
              <Search className="h-4 w-4" />
              {activeFilterCount ? <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[9px] font-bold text-primary-foreground">{activeFilterCount}</span> : null}
            </button>
            {searchOpen ? (
              <div id="pipeline-search-popover" role="group" aria-label="Search candidates and filters" className="absolute right-0 top-[calc(100%+0.5rem)] z-30 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-border bg-card p-3 shadow-card-hover">
                <label className="text-xs font-semibold text-muted-foreground">Search candidates<span className="relative mt-1 block"><Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" /><input ref={searchInputRef} className={`${fieldClass} pl-9`} value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Candidate name" /></span></label>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button type="button" className={secondaryButtonClass} onClick={() => { setSearchOpen(false); setFiltersOpen(true); }}><ListFilter className="h-4 w-4" />Filters{activeAdvanced.length ? ` (${activeAdvanced.length})` : ""}</button>
                  {activeFilterCount ? <button type="button" className={secondaryButtonClass} onClick={clearFilters}><X className="h-4 w-4" />Clear</button> : null}
                </div>
              </div>
            ) : null}
          </div>
          </div>
        )}
      />

      <div className="xl:hidden">
        <label className="text-xs font-semibold text-muted-foreground">Pipeline stage<select className={`${fieldClass} mt-1`} value={mobileStage} onChange={(event) => setMobileStage(event.target.value)}>{pipeline.data.columns.map((stage) => <option key={stage.stage_key} value={stage.stage_key}>{stage.label} · {pipeline.data.counts[stage.stage_key] || 0}</option>)}</select></label>
        <section aria-label={`${mobileStageDefinition?.label || recruitmentStageLabel(mobileStage, options?.stage_labels)} candidates`} className="mt-3 rounded-xl border border-border bg-muted/25 p-2.5"><div className="mb-2 flex min-h-9 items-center justify-between gap-2 px-1"><div className="flex min-w-0 items-center gap-2">{mobileStage === "new_candidate" && canAddCandidate && onAddCandidate ? <button type="button" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-primary transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" onClick={onAddCandidate} aria-label="Add candidate" title="Add candidate"><Plus className="h-4 w-4" /></button> : null}{mobileStageDefinition?.stage_kind === "custom" ? <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${stageColorStyles[mobileStageDefinition.color_token].swatch}`} aria-hidden="true" /> : null}<h2 className="break-words text-xs font-semibold uppercase tracking-wide">{mobileStageDefinition?.label || recruitmentStageLabel(mobileStage, options?.stage_labels)}</h2></div><span className="rounded-full bg-card px-2 py-1 text-xs font-semibold tabular-nums">{pipeline.data.counts[mobileStage] || 0}</span></div>{mobileCards}</section>
      </div>

      <div
        ref={boardViewportRef}
        className={`pipeline-board-scroll hidden w-full min-w-0 max-w-full overflow-x-auto overflow-y-hidden overscroll-x-contain pb-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 xl:block ${boardPanning ? "cursor-grabbing select-none" : "cursor-grab"}`}
        tabIndex={0}
        aria-label="Recruitment pipeline board. Use left and right arrow keys to move horizontally."
        onPointerDown={startBoardPan}
        onPointerMove={moveBoardPan}
        onPointerUp={finishBoardPan}
        onPointerCancel={finishBoardPan}
        onKeyDown={(event) => {
          if (event.currentTarget !== event.target || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
          event.preventDefault();
          smoothScrollBoardBy(event.key === "ArrowLeft" ? -240 : 240);
        }}
      >
        {desktopBoard}
      </div>

      {draggedCandidate ? (() => {
        const targets = ["trash_bin", "rejected", "candidate_withdrew"] as const;
        return (
          <div className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--app-bottom-inset)+1rem)] z-40 flex justify-center px-3">
            <section aria-label="Candidate outcome drop targets" className="pointer-events-auto grid w-full max-w-2xl grid-cols-3 gap-2 rounded-xl border border-border bg-card/95 p-2 shadow-card-hover backdrop-blur">
              {targets.map((target) => {
                const highlighted = dragOverOutcome === target;
                const Icon = target === "trash_bin" ? Trash2 : target === "rejected" ? Ban : UserMinus;
                const label = target === "trash_bin" ? "Trash Bin" : target === "rejected" ? "Reject" : "Withdraw";
                const toneCls = target === "trash_bin" ? "border-destructive/50 bg-destructive/10 text-destructive" : target === "rejected" ? "border-red-700/40 bg-red-700/5 text-red-800 dark:text-red-300" : "border-rose-400/50 bg-rose-100/70 text-rose-800 dark:bg-rose-400/10 dark:text-rose-200";
                return <div key={target} onDragEnter={(event) => { event.preventDefault(); setDragOverOutcome(target); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragOverOutcome(null)} onDrop={(event) => { event.preventDefault(); const candidate = draggedCandidateRef.current; finishDrag(); if (!candidate) return; if (target === "trash_bin") move.mutate({ candidate, stage: "trash_bin" }); else if (target === "rejected") setRejectSelection({ candidate }); else setWithdrawSelection({ candidate }); }} className={`flex min-h-14 items-center justify-center gap-2 rounded-lg border border-dashed px-2 text-center text-xs font-semibold transition-colors sm:text-sm ${toneCls} ${highlighted ? "ring-2 ring-current/20" : ""}`}><Icon className="h-4 w-4 shrink-0" />{label}</div>;
              })}
            </section>
          </div>
        );
      })() : null}

      {undoTrash ? <div role="status" className="fixed bottom-[calc(var(--app-bottom-inset)+1rem)] left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-lg bg-foreground px-3 py-1.5 text-sm font-semibold text-background shadow-card-hover"><span>{undoTrash.candidate.full_name} moved to Trash Bin.</span><button type="button" className="min-h-9 rounded-md px-2 text-primary underline" onClick={() => { move.mutate({ candidate: undoTrash.candidate, stage: undoTrash.previousCandidate.status }); setUndoTrash(null); }}>Undo</button></div> : null}

      <FiltersDrawer open={filtersOpen} filters={filters} options={options} onClose={closeFilters} onApply={(next) => { setFilters(next); closeFilters(); }} />
      <PipelineStagesDrawer open={stageManagerOpen} onClose={() => setStageManagerOpen(false)} onAnnouncement={onAnnouncement} />

      <Modal open={Boolean(rejectSelection)} onClose={() => { if (!reject.isPending) setRejectSelection(null); }} title="Reject candidate" subtitle={rejectSelection?.candidate.full_name} size="sm">
        {rejectSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); reject.mutate({ candidate: rejectSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody className="grid gap-2"><label className="text-xs font-semibold">Rejection reason<select autoFocus required name="rejection_reason" className={`${fieldClass} mt-1`}><option value="">Select a reason</option>{(options?.rejection_reason_options || []).map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><label className="text-xs font-semibold">Explanation<textarea name="reason_detail" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="text-xs text-muted-foreground">The system will record that the candidate was rejected from {rejectSelection.candidate.status_label || recruitmentStageLabel(rejectSelection.candidate.status, options?.stage_labels)}.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setRejectSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={reject.isPending}>{reject.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}Reject</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(withdrawSelection)} onClose={() => { if (!withdraw.isPending) setWithdrawSelection(null); }} title="Candidate withdrew" subtitle={withdrawSelection?.candidate.full_name} size="sm">
        {withdrawSelection ? <form className="flex min-h-0 flex-1 flex-col" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); withdraw.mutate({ candidate: withdrawSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody><label className="text-xs font-semibold">Withdrawal reason<textarea autoFocus required name="reason_detail" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="mt-3 text-xs text-muted-foreground">The system records that this candidate withdrew from {withdrawSelection.candidate.status_label || recruitmentStageLabel(withdrawSelection.candidate.status, options?.stage_labels)} and cancels active appointments.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setWithdrawSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={withdraw.isPending}>{withdraw.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserMinus className="h-4 w-4" />}Confirm withdrawal</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(scheduleSelection)} onClose={() => { if (!schedule.isPending) setScheduleSelection(null); }} title={scheduleSelection?.appointmentType === "job_interview" ? "Schedule job interview" : "Schedule demo lesson"} subtitle={scheduleSelection?.candidate.full_name} size="md">
        {scheduleSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); schedule.mutate({ candidate: scheduleSelection.candidate, appointmentType: scheduleSelection.appointmentType, values: formValues(event.currentTarget) }); }}><ModalBody><AppointmentForm appointmentType={scheduleSelection.appointmentType} options={options} /></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setScheduleSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={schedule.isPending}>{schedule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Schedule</button></div></ModalFooter></form> : null}
      </Modal>
      <Modal open={Boolean(rescheduleSelection)} onClose={() => { if (!reschedule.isPending) setRescheduleSelection(null); }} title={rescheduleSelection?.appointment.appointment_type === "job_interview" ? "Reschedule job interview" : "Reschedule demo lesson"} subtitle={rescheduleSelection?.candidate.full_name} size="md">
        {rescheduleSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); reschedule.mutate({ candidate: rescheduleSelection.candidate, appointment: rescheduleSelection.appointment, values: formValues(event.currentTarget) }); }}><ModalBody><AppointmentForm appointmentType={rescheduleSelection.appointment.appointment_type} appointment={rescheduleSelection.appointment} options={options} /></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setRescheduleSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={reschedule.isPending}>{reschedule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Save appointment</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(cancelSelection)} onClose={() => { if (!cancelAppointment.isPending) setCancelSelection(null); }} title={cancelSelection?.appointment.appointment_type === "job_interview" ? "Cancel job interview" : "Cancel demo lesson"} subtitle={cancelSelection?.candidate.full_name} size="sm">
        {cancelSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); cancelAppointment.mutate({ candidate: cancelSelection.candidate, appointment: cancelSelection.appointment, values: formValues(event.currentTarget) }); }}><ModalBody><label className="text-xs font-semibold">Reason / note<textarea autoFocus required name="reason" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="mt-3 text-xs text-muted-foreground">The booking is cancelled and the candidate stays in {cancelSelection.candidate.status_label || recruitmentStageLabel(cancelSelection.candidate.status, options?.stage_labels)}. You can schedule a new one anytime.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setCancelSelection(null)}>Keep appointment</button><button type="submit" className={buttonClass} disabled={cancelAppointment.isPending}>{cancelAppointment.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}Cancel appointment</button></div></ModalFooter></form> : null}
      </Modal>

      {interviewSelection ? <InterviewSessionModal candidate={interviewSelection.candidate} appointment={interviewSelection.appointment} options={options} open onClose={() => setInterviewSelection(null)} onAnnouncement={onAnnouncement} /> : null}
    </div>
  );
}
