import { Ban, CalendarPlus, ListFilter, Loader2, Search, Trash2, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useDeferredValue, useEffect, useRef, useState, type FormEvent } from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { appointmentConflictDetails, formValues, jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import {
  dateLabel,
  humanize,
  manualStages,
  primaryStages,
  stageLabels,
  type RecruitmentAppointment,
  type RecruitmentCandidate,
  type RecruitmentOptions,
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
import { Drawer } from "@/shared/ui/Drawer";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type PipelineData = {
  stages: Record<string, RecruitmentCandidate[]>;
  counts: Record<string, number>;
  total: number;
};

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
type PipelineFilters = {
  search: string;
  position: string;
  source: string;
  application_from: string;
  application_to: string;
  evaluator_account_id: string;
};
type HoldSelection = { candidate: RecruitmentCandidate };
type RejectSelection = { candidate: RecruitmentCandidate };
type ScheduleSelection = { candidate: RecruitmentCandidate; appointmentType: "job_interview" | "demo_lesson" };
type UndoTrash = { candidate: RecruitmentCandidate; previousCandidate: RecruitmentCandidate };

const filterKeys: Array<keyof PipelineFilters> = [
  "search",
  "position",
  "source",
  "application_from",
  "application_to",
  "evaluator_account_id",
];

const chartStages = [
  { stage: "new_candidate", label: "New", color: "bg-white ring-1 ring-inset ring-slate-400 dark:bg-slate-100", legend: "bg-white border border-slate-400" },
  { stage: "responded", label: "Responded", color: "bg-blue-600", legend: "bg-blue-600" },
  { stage: "on_hold", label: "On Hold", color: "bg-slate-400", legend: "bg-slate-400" },
  { stage: "job_interview", label: "Job Interview", color: "bg-emerald-300", legend: "bg-emerald-300" },
  { stage: "test_and_demo", label: "Demo & Test", color: "bg-emerald-600", legend: "bg-emerald-600" },
  { stage: "teacher_academy", label: "Teacher Academy", color: "bg-amber-500", legend: "bg-amber-500" },
  { stage: "active_teacher", label: "Active Teachers", color: "bg-emerald-900", legend: "bg-emerald-900" },
] as const;

function initialFilters(): PipelineFilters {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(filterKeys.map((key) => [key, params.get(key) || ""])) as PipelineFilters;
}

function matchingAppointment(candidate: RecruitmentCandidate) {
  const expectedType = candidate.status === "job_interview"
    ? "job_interview"
    : candidate.status === "test_and_demo"
      ? "demo_lesson"
      : "";
  if (!expectedType) return null;
  const appointments = candidate.appointments || [];
  return appointments.find((item) => item.status === "scheduled" && item.appointment_type === expectedType)
    || (candidate.next_appointment?.appointment_type === expectedType ? candidate.next_appointment : null);
}

function PipelineSummary({ counts }: { counts: Record<string, number> }) {
  const total = chartStages.reduce((sum, item) => sum + Number(counts[item.stage] || 0), 0);
  const rawValues = chartStages.map((item) => ({
    ...item,
    count: Number(counts[item.stage] || 0),
    rawPercentage: total ? Number(counts[item.stage] || 0) / total * 100 : 0,
  }));
  const floorTotal = rawValues.reduce((sum, item) => sum + Math.floor(item.rawPercentage), 0);
  const remainderOrder = rawValues
    .map((item, index) => ({ index, fraction: item.rawPercentage - Math.floor(item.rawPercentage) }))
    .sort((left, right) => right.fraction - left.fraction || left.index - right.index);
  const roundedUp = new Set(remainderOrder.slice(0, total ? 100 - floorTotal : 0).map((item) => item.index));
  const values = rawValues.map((item, index) => ({
    ...item,
    percentage: Math.floor(item.rawPercentage) + (roundedUp.has(index) ? 1 : 0),
  }));
  const summary = values.map((item) => `${item.label}: ${item.count} (${item.percentage}%)`).join(", ");
  return (
    <section className="rounded-xl border border-border bg-card px-3 py-2.5" aria-label={`Pipeline distribution. Total ${total}. ${summary}`}>
      <div className="flex items-center gap-3">
        <div className="shrink-0 text-xs font-semibold text-foreground"><span className="text-muted-foreground">Total</span> <span className="tabular-nums">{total}</span></div>
        <div className="flex h-2.5 min-w-0 flex-1 overflow-hidden rounded-full border border-slate-300 bg-muted" aria-hidden="true">
          {values.filter((item) => item.count > 0).map((item) => (
            <span key={item.stage} className={`${item.color} first:rounded-l-full last:rounded-r-full`} style={{ width: `${item.rawPercentage}%` }} />
          ))}
        </div>
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1.5 text-[11px] text-muted-foreground">
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
        <label className="text-xs font-semibold">Position<input className={`${fieldClass} mt-1`} value={draft.position} onChange={(event) => update("position", event.target.value)} /></label>
        <label className="text-xs font-semibold">Source<select className={`${fieldClass} mt-1`} value={draft.source} onChange={(event) => update("source", event.target.value)}><option value="">All sources</option>{options?.sources.map((source) => <option key={source}>{source}</option>)}</select></label>
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">Applied from<input type="date" className={`${fieldClass} mt-1`} value={draft.application_from} onChange={(event) => update("application_from", event.target.value)} /></label><label className="text-xs font-semibold">Applied to<input type="date" className={`${fieldClass} mt-1`} value={draft.application_to} onChange={(event) => update("application_to", event.target.value)} /></label></div>
        <label className="text-xs font-semibold">Evaluator<select className={`${fieldClass} mt-1`} value={draft.evaluator_account_id} onChange={(event) => update("evaluator_account_id", event.target.value)}><option value="">All evaluators</option>{options?.staff.filter((person) => ["academic_director", "head_of_department"].includes(person.role)).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
      </div>
    </Drawer>
  );
}

function CandidateCard({
  candidate,
  basePath,
  onDragStart,
  onDragEnd,
  onSchedule,
}: {
  candidate: RecruitmentCandidate;
  basePath: string;
  onDragStart: (candidate: RecruitmentCandidate) => void;
  onDragEnd: () => void;
  onSchedule: (candidate: RecruitmentCandidate, appointmentType: "job_interview" | "demo_lesson") => void;
}) {
  const canMove = Boolean(candidate.permissions?.can_move_stage) && !["teacher_academy", "active_teacher"].includes(candidate.status);
  const appointment = matchingAppointment(candidate);
  const unscheduledType = candidate.status === "job_interview" && !appointment
    ? "job_interview"
    : candidate.status === "test_and_demo" && !appointment
      ? "demo_lesson"
      : null;
  let detailLabel = "";
  let detailValue = "";
  if (candidate.status === "new_candidate") { detailLabel = "Applied"; detailValue = dateLabel(candidate.application_date); }
  if (candidate.status === "responded") { detailLabel = "Responded"; detailValue = dateLabel(candidate.stage_changed_at); }
  if (appointment) { detailLabel = appointment.appointment_type === "job_interview" ? "Job interview" : "Demo lesson"; detailValue = dateLabel(appointment.starts_at); }
  if (candidate.status === "under_review") { detailLabel = "Under review since"; detailValue = dateLabel(candidate.stage_changed_at); }
  if (candidate.status === "on_hold") { detailLabel = candidate.hold_reason || "On Hold"; detailValue = dateLabel(candidate.hold_application_date || candidate.application_date); }
  if (["teacher_academy", "active_teacher"].includes(candidate.status)) { detailLabel = "Accepted"; detailValue = dateLabel(candidate.final_decision_at || candidate.stage_changed_at); }

  return (
    <article
      draggable={canMove}
      onDragStart={(event) => {
        if (!canMove) { event.preventDefault(); return; }
        event.dataTransfer.setData("text/plain", String(candidate.id));
        event.dataTransfer.effectAllowed = "move";
        onDragStart(candidate);
      }}
      onDragEnd={onDragEnd}
      className={`rounded-lg border border-border bg-card shadow-sm transition-colors motion-reduce:transition-none hover:border-primary/30 focus-within:ring-2 focus-within:ring-primary/25 ${canMove ? "cursor-grab active:cursor-grabbing" : ""}`}
    >
      <a href={`${basePath}/candidates/${candidate.id}?tab=overview&origin=pipeline`} onClick={() => rememberRecruitmentReturn("pipeline")} className="block rounded-t-lg px-3 pb-2 pt-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30" title={candidate.full_name}>
        <p className="truncate text-sm font-semibold text-foreground">{candidate.full_name}</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">{candidate.applied_position || candidate.subject || "Position not set"}</p>
        {detailLabel ? <div className="mt-2 rounded-md bg-muted/55 px-2 py-1.5 text-xs"><span className="block truncate font-medium text-foreground">{detailLabel}</span><span className="text-muted-foreground">{detailValue}</span></div> : null}
      </a>
      {unscheduledType ? (
        <button type="button" onClick={() => onSchedule(candidate, unscheduledType)} className="mx-2 mb-2 flex min-h-11 w-[calc(100%-1rem)] items-center gap-2 rounded-md border border-amber-400/50 bg-amber-100 px-2 text-left text-xs font-semibold text-amber-900 transition-colors hover:bg-amber-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/40 dark:bg-amber-400/15 dark:text-amber-100">
          <CalendarPlus className="h-4 w-4 shrink-0" />{unscheduledType === "job_interview" ? "Interview not scheduled" : "Demo lesson not scheduled"}
        </button>
      ) : null}
    </article>
  );
}

export function PipelineView({
  basePath,
  options,
  onAnnouncement,
}: {
  basePath: string;
  options?: RecruitmentOptions;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const initial = new URLSearchParams(window.location.search);
  const initialStage = initial.get("stage") || primaryStages[0];
  const [mobileStage, setMobileStage] = useState((primaryStages as readonly string[]).includes(initialStage) ? initialStage : primaryStages[0]);
  const [filters, setFilters] = useState<PipelineFilters>(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [draggedCandidate, setDraggedCandidate] = useState<RecruitmentCandidate | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [dragOverOutcome, setDragOverOutcome] = useState<"trash_bin" | "rejected" | null>(null);
  const [holdSelection, setHoldSelection] = useState<HoldSelection | null>(null);
  const [rejectSelection, setRejectSelection] = useState<RejectSelection | null>(null);
  const [scheduleSelection, setScheduleSelection] = useState<ScheduleSelection | null>(null);
  const [scheduleConflicts, setScheduleConflicts] = useState<RecruitmentAppointment[]>([]);
  const [undoTrash, setUndoTrash] = useState<UndoTrash | null>(null);
  const draggedCandidateRef = useRef<RecruitmentCandidate | null>(null);
  const deferredSearch = useDeferredValue(filters.search);
  const requestParams = new URLSearchParams();
  Object.entries({ ...filters, search: deferredSearch }).forEach(([key, value]) => { if (value) requestParams.set(key, value); });
  const pipeline = useQuery({
    queryKey: ["recruitment", "pipeline", { ...filters, search: deferredSearch }],
    queryFn: () => recruitmentRequest<PipelineData>(`${RECRUITMENT_API}/pipeline${requestParams.size ? `?${requestParams}` : ""}`),
  });

  useEffect(() => {
    replaceUrlParams({ stage: mobileStage, ...filters });
  }, [filters, mobileStage]);
  useEffect(() => {
    if (pipeline.data) restoreRecruitmentReturn("pipeline");
  }, [pipeline.data]);
  useEffect(() => {
    if (!undoTrash) return undefined;
    const timer = window.setTimeout(() => setUndoTrash(null), 5000);
    return () => window.clearTimeout(timer);
  }, [undoTrash]);

  const move = useMutation({
    mutationFn: ({ candidate, stage }: { candidate: RecruitmentCandidate; stage: string }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/stage`, { method: "POST", body: jsonBody({ stage, expected_version: candidate.version, reason: "Pipeline move" }) }),
    onMutate: async ({ candidate, stage }) => {
      await queryClient.cancelQueries({ queryKey: ["recruitment", "pipeline"] });
      const entries = queryClient.getQueriesData<PipelineData>({ queryKey: ["recruitment", "pipeline"] });
      entries.forEach(([key, previous]) => {
        if (!previous) return;
        const stages = Object.fromEntries(Object.entries(previous.stages).map(([name, values]) => [name, values.filter((item) => item.id !== candidate.id)]));
        stages[stage] = [{ ...candidate, status: stage, stage_changed_at: new Date().toISOString(), next_appointment: null, version: candidate.version + 1 }, ...(stages[stage] || [])];
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
  const hold = useMutation({
    mutationFn: ({ candidate, values }: { candidate: RecruitmentCandidate; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/hold`, { method: "POST", body: jsonBody({ ...values, expected_version: candidate.version }) }),
    onSuccess: (result) => { setHoldSelection(null); onAnnouncement(result.message || "Candidate placed On Hold."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const reject = useMutation({
    mutationFn: ({ candidate, values }: { candidate: RecruitmentCandidate; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/final-decisions`, { method: "POST", body: jsonBody({ decision: "rejected", ...values }) }),
    onSuccess: (result) => { setRejectSelection(null); onAnnouncement(result.message || "Candidate rejected."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const schedule = useMutation({
    mutationFn: ({ candidate, appointmentType, values }: { candidate: RecruitmentCandidate; appointmentType: ScheduleSelection["appointmentType"]; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments`, { method: "POST", body: jsonBody({ ...values, appointment_type: appointmentType, allow_conflict: Boolean(scheduleConflicts.length) }) }),
    onSuccess: (result) => { setScheduleSelection(null); setScheduleConflicts([]); onAnnouncement(result.message || "Appointment scheduled."); },
    onError: (error) => { const conflicts = appointmentConflictDetails<RecruitmentAppointment>(error); if (conflicts.length) setScheduleConflicts(conflicts); onAnnouncement(queryError(error), "error"); },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });

  const activeAdvanced = filterKeys.filter((key) => key !== "search" && Boolean(filters[key]));
  const clearFilters = () => setFilters(Object.fromEntries(filterKeys.map((key) => [key, ""])) as PipelineFilters);
  const finishDrag = () => { draggedCandidateRef.current = null; setDraggedCandidate(null); setDragOverStage(null); setDragOverOutcome(null); };

  if (pipeline.isLoading) return <PageState>Loading recruitment pipeline…</PageState>;
  if (pipeline.error || !pipeline.data) return <PageState tone="error">{queryError(pipeline.error)}</PageState>;

  const cards = (items: RecruitmentCandidate[]) => (
    <div className="space-y-2">
      {items.map((candidate) => <CandidateCard key={candidate.id} candidate={candidate} basePath={basePath} onDragStart={(value) => { draggedCandidateRef.current = value; setDraggedCandidate(value); }} onDragEnd={finishDrag} onSchedule={(value, appointmentType) => { setScheduleConflicts([]); setScheduleSelection({ candidate: value, appointmentType }); }} />)}
      {!items.length ? <EmptyLine>No candidates in this stage.</EmptyLine> : null}
    </div>
  );

  return (
    <div className="space-y-3">
      <PipelineSummary counts={pipeline.data.counts} />
      <section className="rounded-xl border border-border bg-card p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="min-w-0 flex-1 text-xs font-semibold text-muted-foreground">Search<span className="relative mt-1 block"><Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4" /><input className={`${fieldClass} pl-9`} value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Candidate name" /></span></label>
          <button type="button" className={secondaryButtonClass} onClick={() => setFiltersOpen(true)}><ListFilter className="h-4 w-4" />Filters{activeAdvanced.length ? ` (${activeAdvanced.length})` : ""}</button>
          {(filters.search || activeAdvanced.length) ? <button type="button" className={secondaryButtonClass} onClick={clearFilters}><X className="h-4 w-4" />Clear</button> : null}
        </div>
      </section>

      <div className="md:hidden">
        <label className="text-xs font-semibold text-muted-foreground">Pipeline stage<select className={`${fieldClass} mt-1`} value={mobileStage} onChange={(event) => setMobileStage(event.target.value as typeof mobileStage)}>{primaryStages.map((stage) => <option key={stage} value={stage}>{stageLabels[stage]} · {pipeline.data.counts[stage] || 0}</option>)}</select></label>
        <section aria-label={`${stageLabels[mobileStage]} candidates`} className="mt-3 rounded-xl border border-border bg-muted/25 p-2.5"><div className="mb-2 flex min-h-11 items-center justify-between gap-2 px-1"><h2 className="text-xs font-semibold uppercase tracking-wide">{stageLabels[mobileStage]}</h2><span className="rounded-full bg-card px-2 py-1 text-xs font-semibold tabular-nums">{pipeline.data.counts[mobileStage] || 0}</span></div>{cards(pipeline.data.stages[mobileStage] || [])}</section>
      </div>

      <div className="hidden overflow-x-auto pb-1 md:block">
        <div className="grid min-w-[1600px] grid-cols-8 gap-2">
          {primaryStages.map((stage) => {
            const acceptsDrop = (manualStages as readonly string[]).includes(stage);
            const highlighted = dragOverStage === stage;
            const items = pipeline.data.stages[stage] || [];
            return (
              <section key={stage} aria-label={`${stageLabels[stage]} candidates`} onDragEnter={(event) => { if (acceptsDrop && draggedCandidateRef.current) { event.preventDefault(); setDragOverStage(stage); } }} onDragOver={(event) => { if (acceptsDrop && draggedCandidateRef.current) event.preventDefault(); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverStage(null); }} onDrop={(event) => { event.preventDefault(); setDragOverStage(null); const candidate = draggedCandidateRef.current; finishDrag(); if (!candidate || candidate.status === stage || !acceptsDrop) return; if (stage === "on_hold") setHoldSelection({ candidate }); else move.mutate({ candidate, stage }); }} className={`flex h-[calc(100dvh-20rem)] min-h-[28rem] max-h-[52rem] flex-col overflow-hidden rounded-xl border transition-colors motion-reduce:transition-none ${highlighted ? "border-primary bg-primary/5 ring-2 ring-primary/15" : "border-border bg-muted/25"}`}>
                <div className="flex min-h-12 shrink-0 items-center justify-between gap-2 border-b border-border bg-muted/95 px-3"><h2 className="text-[11px] font-semibold uppercase tracking-wide text-foreground">{stageLabels[stage]}</h2><span className="rounded-full bg-card px-2 py-1 text-[11px] font-semibold text-muted-foreground tabular-nums">{items.length}</span></div>
                <div className="miniapp-scroll flex-1 overflow-y-auto p-2">{cards(items)}</div>
              </section>
            );
          })}
        </div>
      </div>

      {draggedCandidate ? (
        <div className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--app-bottom-inset)+1rem)] z-40 flex justify-center px-4">
          <section aria-label="Candidate outcome drop targets" className="pointer-events-auto grid w-full max-w-md grid-cols-2 gap-2 rounded-xl border border-border bg-card/95 p-2 shadow-card-hover backdrop-blur">
            {(["trash_bin", "rejected"] as const).map((target) => {
              const danger = target === "trash_bin";
              const highlighted = dragOverOutcome === target;
              return <div key={target} onDragEnter={(event) => { event.preventDefault(); setDragOverOutcome(target); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragOverOutcome(null)} onDrop={(event) => { event.preventDefault(); const candidate = draggedCandidateRef.current; finishDrag(); if (!candidate) return; if (target === "trash_bin") move.mutate({ candidate, stage: "trash_bin" }); else setRejectSelection({ candidate }); }} className={`flex min-h-14 items-center justify-center gap-2 rounded-lg border border-dashed px-3 text-sm font-semibold transition-colors ${danger ? "border-destructive/50 bg-destructive/10 text-destructive" : "border-red-700/40 bg-red-700/5 text-red-800 dark:text-red-300"} ${highlighted ? "ring-2 ring-current/20" : ""}`}>{target === "trash_bin" ? <Trash2 className="h-4 w-4" /> : <Ban className="h-4 w-4" />}{target === "trash_bin" ? "Trash Bin" : "Reject"}</div>;
            })}
          </section>
        </div>
      ) : null}

      {undoTrash ? <div role="status" className="fixed bottom-[calc(var(--app-bottom-inset)+1rem)] left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-lg bg-foreground px-3 py-2 text-sm font-semibold text-background shadow-card-hover"><span>{undoTrash.candidate.full_name} moved to Trash Bin.</span><button type="button" className="min-h-11 rounded-md px-2 text-primary underline" onClick={() => { if (undoTrash.previousCandidate.status === "on_hold") hold.mutate({ candidate: undoTrash.candidate, values: { reason: undoTrash.previousCandidate.hold_reason || "Restored after undoing Trash Bin move.", application_date: undoTrash.previousCandidate.hold_application_date || undoTrash.previousCandidate.application_date || "" } }); else move.mutate({ candidate: undoTrash.candidate, stage: undoTrash.previousCandidate.status }); setUndoTrash(null); }}>Undo</button></div> : null}

      <FiltersDrawer open={filtersOpen} filters={filters} options={options} onClose={() => setFiltersOpen(false)} onApply={(next) => { setFilters(next); setFiltersOpen(false); }} />

      <Modal open={Boolean(holdSelection)} onClose={() => { if (!hold.isPending) setHoldSelection(null); }} title="Place candidate On Hold" subtitle={holdSelection?.candidate.full_name} size="sm">
        {holdSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); hold.mutate({ candidate: holdSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody className="grid gap-3"><label className="text-xs font-semibold">Reason<textarea autoFocus required name="reason" className={`${fieldClass} mt-1 min-h-24`} /></label><label className="text-xs font-semibold">Application date<input required type="date" name="application_date" defaultValue={holdSelection.candidate.application_date?.slice(0, 10)} className={`${fieldClass} mt-1`} /></label></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setHoldSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={hold.isPending}>{hold.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Place On Hold</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(rejectSelection)} onClose={() => { if (!reject.isPending) setRejectSelection(null); }} title="Reject candidate" subtitle={rejectSelection?.candidate.full_name} size="sm">
        {rejectSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); reject.mutate({ candidate: rejectSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody className="grid gap-3"><label className="text-xs font-semibold">Rejection reason<select autoFocus required name="rejection_reason" className={`${fieldClass} mt-1`}><option value="">Select a reason</option>{(options?.rejection_reason_options || []).map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><label className="text-xs font-semibold">Explanation<textarea name="reason_detail" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="text-xs text-muted-foreground">The system will record that the candidate was rejected from {stageLabels[rejectSelection.candidate.status] || humanize(rejectSelection.candidate.status)}.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setRejectSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={reject.isPending}>{reject.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}Reject</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(scheduleSelection)} onClose={() => { if (!schedule.isPending) { setScheduleSelection(null); setScheduleConflicts([]); } }} title={scheduleSelection?.appointmentType === "job_interview" ? "Schedule job interview" : "Schedule demo lesson"} subtitle={scheduleSelection?.candidate.full_name} size="md">
        {scheduleSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); schedule.mutate({ candidate: scheduleSelection.candidate, appointmentType: scheduleSelection.appointmentType, values: formValues(event.currentTarget) }); }}><ModalBody><AppointmentForm appointmentType={scheduleSelection.appointmentType} options={options} conflicts={scheduleConflicts} /></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => { setScheduleSelection(null); setScheduleConflicts([]); }}>Cancel</button><button type="submit" className={buttonClass} disabled={schedule.isPending}>{schedule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{scheduleConflicts.length ? "Schedule anyway" : "Schedule"}</button></div></ModalFooter></form> : null}
      </Modal>
    </div>
  );
}
