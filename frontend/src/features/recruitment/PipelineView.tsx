import { AlertTriangle, Ban, CalendarPlus, Check, CheckCircle2, Clock3, GraduationCap, ListFilter, Loader2, Plus, Search, Trash2, UserMinus, X } from "lucide-react";
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
  type WheelEvent as ReactWheelEvent,
} from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { InterviewSessionModal } from "@/features/recruitment/InterviewSessionModal";
import { appointmentConflictDetails, formValues, jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { useCanonicalTeacherRosterTotals } from "@/features/teacher-academy/TeacherAcademyRoster";
import {
  dateLabel,
  dateTimeLabel,
  boardStages,
  humanize,
  manualStages,
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
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { ActionMenu } from "@/shared/ui/ActionMenu";
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
  subject_id: string;
  application_from: string;
  application_to: string;
  evaluator_account_id: string;
};
type RejectSelection = { candidate: RecruitmentCandidate };
type ScheduleSelection = { candidate: RecruitmentCandidate; appointmentType: "job_interview" | "demo_lesson" };
type RescheduleSelection = { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment };
type CancelSelection = { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment };
type AcceptSelection = { candidate: RecruitmentCandidate };
type UndoTrash = { candidate: RecruitmentCandidate; previousCandidate: RecruitmentCandidate };

const filterKeys: Array<keyof PipelineFilters> = [
  "search",
  "position",
  "source",
  "subject_id",
  "application_from",
  "application_to",
  "evaluator_account_id",
];

const chartStages = [
  { stage: "new_candidate", label: "Application Received", color: "bg-white ring-1 ring-inset ring-slate-400 dark:bg-slate-100", legend: "bg-white border border-slate-400" },
  { stage: "responded", label: "Interview Schedule", color: "bg-blue-600", legend: "bg-blue-600" },
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
  return appointments.find((item) => ["scheduled", "in_progress"].includes(item.status) && item.appointment_type === expectedType)
    || (candidate.next_appointment?.appointment_type === expectedType ? candidate.next_appointment : null);
}

function PipelineSummary({ counts, action }: { counts: Record<string, number>; action?: ReactNode }) {
  const total = chartStages.reduce((sum, item) => sum + Number(counts[item.stage] || 0), 0);
  const values = chartStages.map((item) => ({
    ...item,
    count: Number(counts[item.stage] || 0),
    rawPercentage: total ? Number(counts[item.stage] || 0) / total * 100 : 0,
    percentage: (total ? Number(counts[item.stage] || 0) / total * 100 : 0).toFixed(1),
  }));
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

const CandidateCard = memo(function CandidateCard({
  candidate,
  basePath,
  onDragStart,
  onDragEnd,
  onSchedule,
  onInterview,
  onReschedule,
  onCancelAppointment,
  onAccept,
  onReject,
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
  onAccept: (candidate: RecruitmentCandidate) => void;
  onReject: (candidate: RecruitmentCandidate) => void;
  compact?: boolean;
}) {
  const canMove = Boolean(candidate.permissions?.can_move_stage) && !["teacher_academy", "active_teacher"].includes(candidate.status);
  const canManageAppointments = Boolean(candidate.permissions?.can_manage_appointments);
  const appointment = matchingAppointment(candidate);
  const unscheduledType = candidate.status === "job_interview" && !appointment && candidate.latest_interview_result !== "passed"
    ? "job_interview"
    : candidate.status === "test_and_demo" && !appointment && !candidate.latest_demo_result
      ? "demo_lesson"
      : null;
  let detailLabel = "";
  let detailValue = "";
  if (candidate.status === "new_candidate") { detailLabel = "Applied"; detailValue = dateLabel(candidate.application_date); }
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
  const alertState = overdue || interviewMissing || demoMissing;
  const toneClass = alertState
    ? "border-red-400 bg-red-50 dark:border-red-500/50 dark:bg-red-950/25"
    : passedInterview || demoPassed || candidate.status === "under_review"
        ? "border-emerald-400 bg-emerald-50 dark:border-emerald-500/50 dark:bg-emerald-950/20"
        : ["job_interview", "test_and_demo"].includes(candidate.status)
          ? "border-amber-400 bg-amber-50 dark:border-amber-500/50 dark:bg-amber-950/20"
          : "border-border bg-card";
  if (overdue) { detailLabel = "Overdue"; detailValue = dateTimeLabel(appointment?.starts_at); }
  if (passedInterview) { detailLabel = "Interview passed"; detailValue = "Ready for the next stage"; }
  if (demoResult) { detailLabel = demoPassed ? "Demo lesson passed" : "Demo lesson evaluated"; detailValue = candidate.latest_demo_at ? dateTimeLabel(candidate.latest_demo_at) : detailValue; }
  const StatusIcon = alertState ? AlertTriangle : passedInterview || demoPassed || candidate.status === "under_review" ? CheckCircle2 : Clock3;
  const sla = candidate.current_sla;
  const slaLabel = sla ? (sla.status === "red" ? "SLA overdue" : `${Math.max(0, Math.ceil(sla.remaining_seconds / 86400))}d SLA left`) : "";
  const slaClass = sla?.status === "red" ? "bg-red-100 text-red-700 dark:bg-red-400/15 dark:text-red-200" : sla?.status === "yellow" ? "bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-100" : "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-100";
  const subjectKnowledgeWarning = candidate.status === "under_review" && evaluationStates?.subject_test !== "passed";
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
      <a href={`${basePath}/candidates/${candidate.id}?tab=overview&origin=pipeline`} onClick={() => rememberRecruitmentReturn("pipeline")} className={`block focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30 ${compact ? "rounded-t-md px-2.5 pb-1.5 pt-2" : "rounded-t-lg px-3 pb-2 pt-3"}`} title={candidate.full_name}>
        <p className={`truncate font-semibold text-foreground ${compact ? "text-[13px] leading-4" : "text-sm"}`}>{candidate.full_name}</p>
        <p className={`truncate text-muted-foreground ${compact ? "mt-0.5 text-[11px] leading-4" : "mt-1 text-xs"}`}>{candidate.applied_position || candidate.subject || "Position not set"}</p>
        {detailLabel ? <div className={`rounded-md bg-background/65 ${compact ? "mt-1.5 px-1.5 py-1 text-[11px] leading-4" : "mt-2 px-2 py-1.5 text-xs"}`}><span className="flex items-center gap-1.5 truncate font-semibold text-foreground"><StatusIcon className={`${compact ? "h-3 w-3" : "h-3.5 w-3.5"} shrink-0`} />{detailLabel}</span><span className={`block truncate text-muted-foreground ${compact ? "" : "mt-0.5"}`}>{detailValue}</span>{candidate.status === "test_and_demo" && appointment ? <span className={`${compact ? "mt-0.5" : "mt-1"} block text-muted-foreground`}><span className="block truncate">Evaluator: {appointment.responsible_name || "Not assigned"}</span>{appointment.topic ? <span className="block truncate">Topic: {appointment.topic}</span> : null}<span className={`block font-semibold ${overdue ? "text-red-700 dark:text-red-300" : "text-amber-800 dark:text-amber-200"}`}>{overdue ? "Overdue" : "Scheduled"}</span></span> : null}</div> : null}
        {candidate.status === "test_and_demo" ? (
          <div className={`flex flex-wrap gap-1 ${compact ? "mt-1" : "mt-2"}`}>
            {evaluationStates?.interview === "passed" ? <span className={`inline-flex rounded-full ${emeraldChip} ${chipBase}`}>Interview passed</span> : interviewMissing ? <span className={`inline-flex rounded-full ${redChip} ${chipBase}`}>No interview recorded</span> : null}
            {demoResult ? <span className={`inline-flex rounded-full ${demoPassed ? emeraldChip : redChip} ${chipBase}`}>{demoPassed ? "Demo passed" : "Demo not passed"}</span> : null}
          </div>
        ) : null}
        {candidate.status === "test_and_demo" && demoResult && candidate.latest_demo_note ? <p className={`mt-1 truncate italic text-muted-foreground ${compact ? "text-[10px] leading-4" : "text-[11px]"}`} title={candidate.latest_demo_note}>“{candidate.latest_demo_note}”</p> : null}
        {candidate.status === "under_review" ? <div className={`flex flex-wrap gap-1 ${compact ? "mt-1" : "mt-2"}`}><span className={`inline-flex rounded-full ${demoMissing ? redChip : emeraldChip} ${chipBase}`}>{demoMissing ? "No demo recorded" : "Demo passed"}</span><span className={`inline-flex rounded-full ${subjectKnowledgeWarning ? redChip : emeraldChip} ${chipBase}`}>{subjectKnowledgeWarning ? "Subject test missing/not passed" : "Subject test passed"}</span></div> : null}
        {sla ? <span className={`inline-flex rounded-full font-semibold ${slaClass} ${compact ? "mt-1 px-1.5 py-0.5 text-[9px]" : "mt-2 px-2 py-1 text-[10px]"}`} title={`SLA due ${dateLabel(sla.due_at)}`}>{slaLabel}</span> : null}
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
      {candidate.status === "under_review" && (candidate.permissions?.can_request_approval || candidate.permissions?.can_reject) ? (
        <div draggable={false} onClick={(event) => event.stopPropagation()} className={`flex items-center gap-1.5 ${compact ? "mx-1.5 mb-1.5" : "mx-2 mb-2"}`}>
          {candidate.permissions?.can_request_approval ? <button type="button" draggable={false} onClick={(event) => { event.stopPropagation(); onAccept(candidate); }} className={`flex min-h-9 flex-1 items-center justify-center gap-1.5 rounded-md bg-emerald-600 px-2 font-semibold text-white transition-colors hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 ${compact ? "text-[11px]" : "text-xs"}`}><GraduationCap className="h-4 w-4 shrink-0" />Accept</button> : null}
          {candidate.permissions?.can_reject ? <button type="button" draggable={false} onClick={(event) => { event.stopPropagation(); onReject(candidate); }} className={`flex min-h-9 flex-1 items-center justify-center gap-1.5 rounded-md border border-red-300 bg-red-50 px-2 font-semibold text-red-700 transition-colors hover:bg-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200 ${compact ? "text-[11px]" : "text-xs"}`}><Ban className="h-4 w-4 shrink-0" />Reject</button> : null}
        </div>
      ) : null}
    </article>
  );
});

export function PipelineView({
  basePath,
  options,
  canAddCandidate = false,
  onAddCandidate,
  onAnnouncement,
}: {
  basePath: string;
  options?: RecruitmentOptions;
  canAddCandidate?: boolean;
  onAddCandidate?: () => void;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const initial = new URLSearchParams(window.location.search);
  const initialStage = initial.get("stage") || boardStages[0];
  const [mobileStage, setMobileStage] = useState((boardStages as readonly string[]).includes(initialStage) ? initialStage : boardStages[0]);
  const [filters, setFilters] = useState<PipelineFilters>(initialFilters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [boardPanning, setBoardPanning] = useState(false);
  const [draggedCandidate, setDraggedCandidate] = useState<RecruitmentCandidate | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [dragOverOutcome, setDragOverOutcome] = useState<"trash_bin" | "rejected" | "candidate_withdrew" | "teacher_academy" | null>(null);
  const [rejectSelection, setRejectSelection] = useState<RejectSelection | null>(null);
  const [withdrawSelection, setWithdrawSelection] = useState<RejectSelection | null>(null);
  const [scheduleSelection, setScheduleSelection] = useState<ScheduleSelection | null>(null);
  const [rescheduleSelection, setRescheduleSelection] = useState<RescheduleSelection | null>(null);
  const [cancelSelection, setCancelSelection] = useState<CancelSelection | null>(null);
  const [acceptSelection, setAcceptSelection] = useState<AcceptSelection | null>(null);
  const [interviewSelection, setInterviewSelection] = useState<{ candidate: RecruitmentCandidate; appointment: RecruitmentAppointment } | null>(null);
  const [scheduleConflicts, setScheduleConflicts] = useState<RecruitmentAppointment[]>([]);
  const [undoTrash, setUndoTrash] = useState<UndoTrash | null>(null);
  const draggedCandidateRef = useRef<RecruitmentCandidate | null>(null);
  const searchTriggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const boardViewportRef = useRef<HTMLDivElement>(null);
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
    if (!undoTrash) return undefined;
    const timer = window.setTimeout(() => setUndoTrash(null), 5000);
    return () => window.clearTimeout(timer);
  }, [undoTrash]);

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
    mutationFn: ({ candidate, appointmentType, values }: { candidate: RecruitmentCandidate; appointmentType: ScheduleSelection["appointmentType"]; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments`, { method: "POST", body: jsonBody({ ...values, appointment_type: appointmentType, allow_conflict: Boolean(scheduleConflicts.length) }) }),
    onSuccess: (result) => { setScheduleSelection(null); setScheduleConflicts([]); onAnnouncement(result.message || "Appointment scheduled."); },
    onError: (error) => { const conflicts = appointmentConflictDetails<RecruitmentAppointment>(error); if (conflicts.length) setScheduleConflicts(conflicts); onAnnouncement(queryError(error), "error"); },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const reschedule = useMutation({
    mutationFn: ({ candidate, appointment, values }: { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${appointment.id}`, { method: "PATCH", body: jsonBody({ ...values, expected_version: appointment.version, allow_conflict: Boolean(scheduleConflicts.length) }) }),
    onSuccess: (result) => { setRescheduleSelection(null); setScheduleConflicts([]); onAnnouncement(result.message || "Appointment rescheduled."); },
    onError: (error) => { const conflicts = appointmentConflictDetails<RecruitmentAppointment>(error); if (conflicts.length) setScheduleConflicts(conflicts); onAnnouncement(queryError(error), "error"); },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const cancelAppointment = useMutation({
    mutationFn: ({ candidate, appointment, values }: { candidate: RecruitmentCandidate; appointment: RecruitmentAppointment; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${appointment.id}/cancel`, { method: "POST", body: jsonBody({ ...values, expected_version: appointment.version }) }),
    onSuccess: (result) => { setCancelSelection(null); onAnnouncement(result.message || "Appointment cancelled."); },
    onError: (error) => onAnnouncement(queryError(error), "error"),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: ["recruitment"] }),
  });
  const accept = useMutation({
    mutationFn: ({ candidate, values }: { candidate: RecruitmentCandidate; values: Record<string, unknown> }) => recruitmentRequest<MutationPayload>(`${RECRUITMENT_API}/candidates/${candidate.id}/approval-requests`, { method: "POST", body: jsonBody({ requested_outcome: "teacher_academy", ...values }) }),
    onSuccess: (result) => { setAcceptSelection(null); onAnnouncement(result.message || "Candidate sent to the Academic Director."); },
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
  const handleCardSchedule = useCallback((value: RecruitmentCandidate, appointmentType: "job_interview" | "demo_lesson") => { setScheduleConflicts([]); setScheduleSelection({ candidate: value, appointmentType }); }, []);
  const handleCardInterview = useCallback((value: RecruitmentCandidate, appointment: RecruitmentAppointment) => setInterviewSelection({ candidate: value, appointment }), []);
  const handleCardReschedule = useCallback((value: RecruitmentCandidate, appointment: RecruitmentAppointment) => { setScheduleConflicts([]); setRescheduleSelection({ candidate: value, appointment }); }, []);
  const handleCardCancelAppointment = useCallback((value: RecruitmentCandidate, appointment: RecruitmentAppointment) => setCancelSelection({ candidate: value, appointment }), []);
  const handleCardAccept = useCallback((value: RecruitmentCandidate) => setAcceptSelection({ candidate: value }), []);
  const handleCardReject = useCallback((value: RecruitmentCandidate) => setRejectSelection({ candidate: value }), []);

  const canStartBoardPan = (target: EventTarget | null) => {
    if (!(target instanceof Element)) return true;
    return !target.closest("[data-candidate-card], a, button, input, select, textarea, [role='menu'], [role='dialog']");
  };
  const startBoardPan = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || !canStartBoardPan(event.target)) return;
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
    setBoardPanning(false);
  };
  const shiftWheelBoard = (event: ReactWheelEvent<HTMLDivElement>) => {
    if (!event.shiftKey || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    event.currentTarget.scrollLeft += event.deltaY;
    event.preventDefault();
  };

  const cards = useCallback((items: RecruitmentCandidate[], compact = false) => (
    <div className={compact ? "space-y-1.5" : "space-y-2"}>
      {items.map((candidate) => <CandidateCard key={candidate.id} candidate={candidate} basePath={basePath} onDragStart={handleCardDragStart} onDragEnd={finishDrag} onSchedule={handleCardSchedule} onInterview={handleCardInterview} onReschedule={handleCardReschedule} onCancelAppointment={handleCardCancelAppointment} onAccept={handleCardAccept} onReject={handleCardReject} compact={compact} />)}
      {!items.length ? <EmptyLine>No candidates in this stage.</EmptyLine> : null}
    </div>
  ), [basePath, handleCardDragStart, finishDrag, handleCardSchedule, handleCardInterview, handleCardReschedule, handleCardCancelAppointment, handleCardAccept, handleCardReject]);

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
  const moveMutate = move.mutate;
  const desktopBoard = useMemo(() => {
    if (!data) return null;
    return (
      <div className="grid w-full min-w-0 grid-cols-5 gap-2 2xl:gap-2">
        {boardStages.map((stage) => {
          const acceptsDrop = (manualStages as readonly string[]).includes(stage);
          const highlighted = dragOverStage === stage;
          const items = data.stages[stage] || [];
          return (
            <section key={stage} aria-label={`${stageLabels[stage]} candidates`} onDragEnter={(event) => { if (acceptsDrop && draggedCandidateRef.current) { event.preventDefault(); setDragOverStage(stage); } }} onDragOver={(event) => { if (acceptsDrop && draggedCandidateRef.current) event.preventDefault(); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverStage(null); }} onDrop={(event) => { event.preventDefault(); setDragOverStage(null); const candidate = draggedCandidateRef.current; finishDrag(); if (!candidate || candidate.status === stage || !acceptsDrop) return; moveMutate({ candidate, stage }); }} className={`flex min-w-0 h-[calc(100dvh-9.75rem)] min-h-[32rem] flex-col overflow-hidden rounded-t-xl border-x border-t transition-colors motion-reduce:transition-none ${highlighted ? "border-primary bg-primary/5 ring-2 ring-primary/15" : "border-border bg-muted/25"}`}>
              <div className="flex min-h-12 shrink-0 items-center justify-between gap-2 border-b border-border bg-muted/95 px-2"><div className="flex min-w-0 items-center gap-1.5">{stage === "new_candidate" && canAddCandidate && onAddCandidate ? <button type="button" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-primary transition-colors hover:bg-card focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" onClick={onAddCandidate} aria-label="Add candidate" title="Add candidate"><Plus className="h-4 w-4" /></button> : null}<h2 className="truncate text-[11px] font-semibold uppercase tracking-wide text-foreground">{stageLabels[stage]}</h2></div><span className="rounded-full bg-card px-2 py-1 text-[11px] font-semibold text-muted-foreground tabular-nums">{items.length}</span></div>
              <div className="miniapp-scroll flex-1 overflow-y-auto p-1.5">{cards(items, true)}</div>
            </section>
          );
        })}
      </div>
    );
  }, [data, dragOverStage, canAddCandidate, onAddCandidate, cards, moveMutate, finishDrag]);
  const mobileCards = useMemo(() => (data ? cards(data.stages[mobileStage] || []) : null), [data, mobileStage, cards]);

  if (pipeline.isLoading || teacherRosterTotals.isLoading) return <PageState>Loading recruitment pipeline…</PageState>;
  if (pipeline.error || !pipeline.data) return <PageState tone="error">{queryError(pipeline.error)}</PageState>;

  return (
    <div className="space-y-2">
      <PipelineSummary
        counts={summaryCounts}
        action={(
          <div ref={searchLayerRef} className="relative shrink-0">
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
        )}
      />

      <div className="xl:hidden">
        <label className="text-xs font-semibold text-muted-foreground">Pipeline stage<select className={`${fieldClass} mt-1`} value={mobileStage} onChange={(event) => setMobileStage(event.target.value as typeof mobileStage)}>{boardStages.map((stage) => <option key={stage} value={stage}>{stageLabels[stage]} · {pipeline.data.counts[stage] || 0}</option>)}</select></label>
        <section aria-label={`${stageLabels[mobileStage]} candidates`} className="mt-3 rounded-xl border border-border bg-muted/25 p-2.5"><div className="mb-2 flex min-h-9 items-center justify-between gap-2 px-1"><div className="flex min-w-0 items-center gap-2">{mobileStage === "new_candidate" && canAddCandidate && onAddCandidate ? <button type="button" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-primary transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" onClick={onAddCandidate} aria-label="Add candidate" title="Add candidate"><Plus className="h-4 w-4" /></button> : null}<h2 className="truncate text-xs font-semibold uppercase tracking-wide">{stageLabels[mobileStage]}</h2></div><span className="rounded-full bg-card px-2 py-1 text-xs font-semibold tabular-nums">{pipeline.data.counts[mobileStage] || 0}</span></div>{mobileCards}</section>
      </div>

      <div
        ref={boardViewportRef}
        className={`no-scrollbar hidden w-full min-w-0 max-w-full overflow-x-auto pb-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 xl:block ${boardPanning ? "cursor-grabbing select-none" : "cursor-grab"}`}
        tabIndex={0}
        aria-label="Recruitment pipeline board. Use left and right arrow keys to move horizontally."
        onPointerDown={startBoardPan}
        onPointerMove={moveBoardPan}
        onPointerUp={finishBoardPan}
        onPointerCancel={finishBoardPan}
        onWheel={shiftWheelBoard}
        onKeyDown={(event) => {
          if (event.currentTarget !== event.target || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
          event.preventDefault();
          event.currentTarget.scrollBy({ left: event.key === "ArrowLeft" ? -240 : 240, behavior: "smooth" });
        }}
      >
        {desktopBoard}
      </div>

      {draggedCandidate ? (() => {
        const canAccept = draggedCandidate.status === "under_review" && Boolean(draggedCandidate.permissions?.can_request_approval);
        const targets = (canAccept
          ? ["teacher_academy", "trash_bin", "rejected", "candidate_withdrew"]
          : ["trash_bin", "rejected", "candidate_withdrew"]) as Array<"teacher_academy" | "trash_bin" | "rejected" | "candidate_withdrew">;
        return (
          <div className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--app-bottom-inset)+1rem)] z-40 flex justify-center px-3">
            <section aria-label="Candidate outcome drop targets" className={`pointer-events-auto grid w-full max-w-2xl gap-2 rounded-xl border border-border bg-card/95 p-2 shadow-card-hover backdrop-blur ${canAccept ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-3"}`}>
              {targets.map((target) => {
                const highlighted = dragOverOutcome === target;
                const Icon = target === "teacher_academy" ? GraduationCap : target === "trash_bin" ? Trash2 : target === "rejected" ? Ban : UserMinus;
                const label = target === "teacher_academy" ? "Accept" : target === "trash_bin" ? "Trash Bin" : target === "rejected" ? "Reject" : "Withdraw";
                const toneCls = target === "teacher_academy" ? "border-emerald-500/50 bg-emerald-50 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-200" : target === "trash_bin" ? "border-destructive/50 bg-destructive/10 text-destructive" : target === "rejected" ? "border-red-700/40 bg-red-700/5 text-red-800 dark:text-red-300" : "border-rose-400/50 bg-rose-100/70 text-rose-800 dark:bg-rose-400/10 dark:text-rose-200";
                return <div key={target} onDragEnter={(event) => { event.preventDefault(); setDragOverOutcome(target); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragOverOutcome(null)} onDrop={(event) => { event.preventDefault(); const candidate = draggedCandidateRef.current; finishDrag(); if (!candidate) return; if (target === "trash_bin") move.mutate({ candidate, stage: "trash_bin" }); else if (target === "rejected") setRejectSelection({ candidate }); else if (target === "candidate_withdrew") setWithdrawSelection({ candidate }); else setAcceptSelection({ candidate }); }} className={`flex min-h-14 items-center justify-center gap-2 rounded-lg border border-dashed px-2 text-center text-xs font-semibold transition-colors sm:text-sm ${toneCls} ${highlighted ? "ring-2 ring-current/20" : ""}`}><Icon className="h-4 w-4 shrink-0" />{label}</div>;
              })}
            </section>
          </div>
        );
      })() : null}

      {undoTrash ? <div role="status" className="fixed bottom-[calc(var(--app-bottom-inset)+1rem)] left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-lg bg-foreground px-3 py-1.5 text-sm font-semibold text-background shadow-card-hover"><span>{undoTrash.candidate.full_name} moved to Trash Bin.</span><button type="button" className="min-h-9 rounded-md px-2 text-primary underline" onClick={() => { move.mutate({ candidate: undoTrash.candidate, stage: undoTrash.previousCandidate.status }); setUndoTrash(null); }}>Undo</button></div> : null}

      <FiltersDrawer open={filtersOpen} filters={filters} options={options} onClose={closeFilters} onApply={(next) => { setFilters(next); closeFilters(); }} />

      <Modal open={Boolean(rejectSelection)} onClose={() => { if (!reject.isPending) setRejectSelection(null); }} title="Reject candidate" subtitle={rejectSelection?.candidate.full_name} size="sm">
        {rejectSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); reject.mutate({ candidate: rejectSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody className="grid gap-2"><label className="text-xs font-semibold">Rejection reason<select autoFocus required name="rejection_reason" className={`${fieldClass} mt-1`}><option value="">Select a reason</option>{(options?.rejection_reason_options || []).map((reason) => <option key={reason.value} value={reason.value}>{reason.label}</option>)}</select></label><label className="text-xs font-semibold">Explanation<textarea name="reason_detail" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="text-xs text-muted-foreground">The system will record that the candidate was rejected from {stageLabels[rejectSelection.candidate.status] || humanize(rejectSelection.candidate.status)}.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setRejectSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={reject.isPending}>{reject.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}Reject</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(withdrawSelection)} onClose={() => { if (!withdraw.isPending) setWithdrawSelection(null); }} title="Candidate withdrew" subtitle={withdrawSelection?.candidate.full_name} size="sm">
        {withdrawSelection ? <form className="flex min-h-0 flex-1 flex-col" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); withdraw.mutate({ candidate: withdrawSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody><label className="text-xs font-semibold">Withdrawal reason<textarea autoFocus required name="reason_detail" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="mt-3 text-xs text-muted-foreground">The system records that this candidate withdrew from {stageLabels[withdrawSelection.candidate.status] || humanize(withdrawSelection.candidate.status)} and cancels active appointments.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setWithdrawSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={withdraw.isPending}>{withdraw.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserMinus className="h-4 w-4" />}Confirm withdrawal</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(scheduleSelection)} onClose={() => { if (!schedule.isPending) { setScheduleSelection(null); setScheduleConflicts([]); } }} title={scheduleSelection?.appointmentType === "job_interview" ? "Schedule job interview" : "Schedule demo lesson"} subtitle={scheduleSelection?.candidate.full_name} size="md">
        {scheduleSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); schedule.mutate({ candidate: scheduleSelection.candidate, appointmentType: scheduleSelection.appointmentType, values: formValues(event.currentTarget) }); }}><ModalBody><AppointmentForm appointmentType={scheduleSelection.appointmentType} options={options} conflicts={scheduleConflicts} allowHistoricalRestoration={canAddCandidate} /></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => { setScheduleSelection(null); setScheduleConflicts([]); }}>Cancel</button><button type="submit" className={buttonClass} disabled={schedule.isPending}>{schedule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{scheduleConflicts.length ? "Schedule anyway" : "Schedule"}</button></div></ModalFooter></form> : null}
      </Modal>
      <Modal open={Boolean(rescheduleSelection)} onClose={() => { if (!reschedule.isPending) { setRescheduleSelection(null); setScheduleConflicts([]); } }} title={rescheduleSelection?.appointment.appointment_type === "job_interview" ? "Reschedule job interview" : "Reschedule demo lesson"} subtitle={rescheduleSelection?.candidate.full_name} size="md">
        {rescheduleSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); reschedule.mutate({ candidate: rescheduleSelection.candidate, appointment: rescheduleSelection.appointment, values: formValues(event.currentTarget) }); }}><ModalBody><AppointmentForm appointmentType={rescheduleSelection.appointment.appointment_type} appointment={rescheduleSelection.appointment} options={options} conflicts={scheduleConflicts} allowHistoricalRestoration={canAddCandidate} /></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => { setRescheduleSelection(null); setScheduleConflicts([]); }}>Cancel</button><button type="submit" className={buttonClass} disabled={reschedule.isPending}>{reschedule.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{scheduleConflicts.length ? "Reschedule anyway" : "Save appointment"}</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(cancelSelection)} onClose={() => { if (!cancelAppointment.isPending) setCancelSelection(null); }} title={cancelSelection?.appointment.appointment_type === "job_interview" ? "Cancel job interview" : "Cancel demo lesson"} subtitle={cancelSelection?.candidate.full_name} size="sm">
        {cancelSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); cancelAppointment.mutate({ candidate: cancelSelection.candidate, appointment: cancelSelection.appointment, values: formValues(event.currentTarget) }); }}><ModalBody><label className="text-xs font-semibold">Reason / note<textarea autoFocus required name="reason" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="mt-3 text-xs text-muted-foreground">The booking is cancelled and the candidate stays in {stageLabels[cancelSelection.candidate.status] || humanize(cancelSelection.candidate.status)}. You can schedule a new one anytime.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setCancelSelection(null)}>Keep appointment</button><button type="submit" className={buttonClass} disabled={cancelAppointment.isPending}>{cancelAppointment.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}Cancel appointment</button></div></ModalFooter></form> : null}
      </Modal>

      <Modal open={Boolean(acceptSelection)} onClose={() => { if (!accept.isPending) setAcceptSelection(null); }} title="Accept candidate" subtitle={acceptSelection?.candidate.full_name} size="sm">
        {acceptSelection ? <form onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); accept.mutate({ candidate: acceptSelection.candidate, values: formValues(event.currentTarget) }); }}><ModalBody className="grid gap-2"><label className="text-xs font-semibold">Requested outcome<select name="requested_outcome" defaultValue="teacher_academy" className={`${fieldClass} mt-1`}><option value="teacher_academy">Teacher Academy</option><option value="active_teacher">Active Teacher</option></select></label><label className="text-xs font-semibold">Note for the Academic Director<textarea name="request_note" className={`${fieldClass} mt-1 min-h-24`} /></label><p className="text-xs text-muted-foreground">The candidate is sent to the Academic Director for final sign-off. The Teacher Academy account is provisioned once approved.</p></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButtonClass} onClick={() => setAcceptSelection(null)}>Cancel</button><button type="submit" className={buttonClass} disabled={accept.isPending}>{accept.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <GraduationCap className="h-4 w-4" />}Send to Academic Director</button></div></ModalFooter></form> : null}
      </Modal>
      {interviewSelection ? <InterviewSessionModal candidate={interviewSelection.candidate} appointment={interviewSelection.appointment} open onClose={() => setInterviewSelection(null)} onAnnouncement={onAnnouncement} /> : null}
    </div>
  );
}
