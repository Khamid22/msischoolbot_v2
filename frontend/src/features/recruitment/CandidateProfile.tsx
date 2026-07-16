import {
  Activity,
  ArrowLeft,
  BriefcaseBusiness,
  CalendarClock,
  Check,
  ClipboardCheck,
  FileText,
  Loader2,
  MessageSquareText,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  useEffect,
  useId,
  useState,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { InterviewSessionModal } from "@/features/recruitment/InterviewSessionModal";
import {
  appointmentConflictDetails,
  formValues,
  jsonBody,
  recruitmentRequest,
} from "@/features/recruitment/api";
import {
  dateLabel,
  dateTimeLabel,
  humanize,
  manualStages,
  stageLabels,
  type RecruitmentAppointment,
  type RecruitmentCandidate,
  type RecruitmentOptions,
} from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  DefinitionGrid,
  EmptyLine,
  PageState,
  buttonClass,
  fieldClass,
  queryError,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { Drawer } from "@/shared/ui/Drawer";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { IconButton } from "@/shared/ui/IconButton";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type ProfileTab =
  "overview" | "evaluations" | "documents" | "hiring" | "activity";
type ProfileAction =
  | { kind: "edit_profile" }
  | { kind: "move_candidate" }
  | { kind: "upload_document"; document?: Record<string, unknown> }
  | { kind: "record_interview"; appointment?: RecruitmentAppointment }
  | { kind: "record_test" }
  | { kind: "record_demo"; appointment?: RecruitmentAppointment }
  | {
      kind: "schedule_appointment";
      appointmentType: "job_interview" | "demo_lesson";
    }
  | { kind: "reschedule_appointment"; appointment: RecruitmentAppointment }
  | {
      kind: "appointment_status";
      appointment: RecruitmentAppointment;
      status: "cancelled" | "no_show";
    }
  | { kind: "assign_evaluators" }
  | { kind: "request_approval"; previous?: Record<string, unknown> }
  | { kind: "record_outcome" }
  | {
      kind: "review_approval";
      approval: Record<string, unknown>;
      status: "approved" | "returned";
    }
  | { kind: "withdraw_candidate" }
  | {
      kind: "void_evaluation";
      evaluationType: "interview" | "subject_test" | "demo";
      attempt: Record<string, unknown>;
    }
  | { kind: "add_task" }
  | { kind: "add_note" };

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
type InlineEditTarget = { id: string; label: string };
const profileTabs: Array<{ key: ProfileTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "evaluations", label: "Evaluations" },
  { key: "documents", label: "Documents" },
  { key: "hiring", label: "Hiring" },
  { key: "activity", label: "Activity" },
];
const hrProfileTabs = profileTabs.filter((item) => item.key !== "activity");

function text(value: unknown) {
  return String(value ?? "");
}

function scheduledDatePart(value: unknown) {
  const parsed = new Date(text(value));
  return Number.isNaN(parsed.getTime())
    ? "Not scheduled"
    : new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "Asia/Tashkent" }).format(parsed);
}

function scheduledTimePart(value: unknown) {
  const parsed = new Date(text(value));
  return Number.isNaN(parsed.getTime())
    ? "Not scheduled"
    : new Intl.DateTimeFormat("en", { timeStyle: "short", timeZone: "Asia/Tashkent" }).format(parsed);
}

function Panel({
  title,
  icon,
  action,
  children,
}: {
  title: string;
  icon: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-3 py-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
          {icon}
          {title}
        </h2>
        {action}
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

function InlineField({
  fieldId,
  label,
  value,
  displayValue,
  type = "text",
  multiline = false,
  options = [],
  busy,
  editing,
  onRequestEdit,
  onDirtyChange,
  onRequestDismiss,
  onFinish,
  onCancel,
  onSave,
}: {
  fieldId: string;
  label: string;
  value: string | number | null | undefined;
  displayValue?: string;
  type?: string;
  multiline?: boolean;
  options?: Array<{ value: string | number; label: string }>;
  busy: boolean;
  editing: boolean;
  onRequestEdit: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onRequestDismiss: (event?: KeyboardEvent | PointerEvent) => void;
  onFinish: () => void;
  onCancel: () => void;
  onSave: (value: string) => void;
}) {
  const [draft, setDraft] = useState(String(value ?? ""));
  const inlineLayerRef = useDismissibleLayer<HTMLDivElement>({
    enabled: editing,
    onDismiss: onRequestDismiss,
  });
  useEffect(() => {
    if (!editing) setDraft(String(value ?? ""));
  }, [editing, value]);
  const originalValue = String(value ?? "");
  const updateDraft = (next: string) => {
    setDraft(next);
    onDirtyChange(next !== originalValue);
  };

  return (
    <div ref={inlineLayerRef} className="relative h-16 min-h-16 min-w-0">
      {!editing ? (
      <button
        data-inline-edit-trigger
        type="button"
        disabled={busy}
        onClick={onRequestEdit}
        className="h-16 w-full min-w-0 overflow-hidden rounded-lg bg-muted/45 px-3 py-2.5 text-left transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait"
        aria-label={`Edit ${label}`}
      >
        <span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <span className="mt-0.5 block truncate text-[13px] font-semibold text-foreground" title={displayValue || String(value ?? "") || "Not set"}>
          {displayValue || String(value ?? "") || "Not set"}
        </span>
      </button>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSave(draft);
            onDirtyChange(false);
            onFinish();
          }}
          className={`absolute inset-x-0 top-0 z-20 rounded-lg border border-primary/30 bg-card p-1.5 shadow-card-hover focus-within:ring-2 focus-within:ring-primary/20 ${multiline ? "min-h-40" : "h-16"}`}
        >
          <div className={multiline ? "grid gap-1.5" : "grid h-full grid-cols-[minmax(0,1fr)_2.75rem_2.75rem] items-center gap-1"}>
            <label className={multiline ? "text-[11px] font-semibold uppercase tracking-wide text-muted-foreground" : "relative min-w-0"}>
              <span className={multiline ? "block" : "pointer-events-none absolute left-3 top-1 z-10 text-[9px] font-semibold uppercase tracking-wide text-muted-foreground"}>{label}</span>
              {options.length ? (
                <select
                  id={`candidate-inline-${fieldId}`}
                  autoFocus
                  value={draft}
                  onChange={(event) => updateDraft(event.target.value)}
                  className={`${fieldClass} ${multiline ? "mt-1" : "h-12 pt-4"}`}
                  aria-label={label}
                >
                  <option value="">Not set</option>
                  {options.map((option) => (
                    <option key={String(option.value)} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : multiline ? (
                <textarea
                  id={`candidate-inline-${fieldId}`}
                  autoFocus
                  value={draft}
                  onChange={(event) => updateDraft(event.target.value)}
                  className={`${fieldClass} mt-1 min-h-24 normal-case tracking-normal`}
                />
              ) : (
                <input
                  id={`candidate-inline-${fieldId}`}
                  autoFocus
                  type={type}
                  value={draft}
                  onChange={(event) => updateDraft(event.target.value)}
                  className={`${fieldClass} h-12 pt-4 normal-case tracking-normal`}
                  aria-label={label}
                />
              )}
            </label>
            <div className={multiline ? "flex justify-end gap-2" : "contents"}>
              <button
                type="button"
                onClick={() => {
                  onDirtyChange(false);
                  onCancel();
                }}
                className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                aria-label={`Cancel editing ${label}`}
                title="Cancel"
              >
                <X className="h-4 w-4" />
              </button>
              <button
                type="submit"
                disabled={busy}
                className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-wait disabled:opacity-50"
                aria-label={`Save ${label}`}
                title="Save"
              >
                <Check className="h-4 w-4" />
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}

function AttemptList({
  items,
  empty,
  onVoid,
}: {
  items: Array<Record<string, unknown>>;
  empty: string;
  onVoid?: (item: Record<string, unknown>) => void;
}) {
  if (!items.length) return <EmptyLine>{empty}</EmptyLine>;
  return (
    <div className="space-y-2">
      {items.map((item) => {
        const isVoided = Boolean(item.voided_at);
        const isFailed = text(item.result).toLowerCase() === "failed";
        return (
          <article
            key={text(item.id)}
            className={`rounded-lg border p-3 ${isFailed && !isVoided ? "border-destructive/30 bg-destructive/5" : "border-border"} ${isVoided ? "opacity-60" : ""}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <StatusBadge
                  status={isVoided ? "voided" : text(item.result || "recorded")}
                />
                {isFailed && !isVoided ? (
                  <span className="text-xs font-semibold text-destructive">
                    Failed
                  </span>
                ) : null}
              </div>
              <div className="flex items-center gap-1">
                <span className="text-xs text-muted-foreground">
                  {dateLabel(
                    item.interview_at ||
                      item.test_at ||
                      item.demo_at ||
                      item.created_at,
                  )}
                </span>
                {onVoid && !isVoided ? (
                  <ActionMenu
                    items={[
                      {
                        key: "void",
                        label: "Void mistaken result",
                        danger: true,
                        onClick: () => onVoid(item),
                      },
                    ]}
                    label="Evaluation actions"
                  />
                ) : null}
              </div>
            </div>
            {item.score !== null && item.score !== undefined ? (
              <p className="mt-2 text-[13px] font-semibold">
                Score: {text(item.score)}
                {item.maximum_score
                  ? ` / ${text(item.maximum_score)} (${text(item.percentage || 0)}%)`
                  : " / 10"}
              </p>
            ) : null}
            {item.overall_score !== null && item.overall_score !== undefined ? <p className="mt-2 text-[13px] font-semibold">Overall: {text(item.overall_score)} / 10{item.communication_score !== null && item.communication_score !== undefined ? ` · Communication: ${text(item.communication_score)} / 10` : ""}{item.cefr_level ? ` · CEFR ${text(item.cefr_level)}` : ""}</p> : null}
            {item.paper ? <p className="mt-1 text-xs text-muted-foreground">Paper: {text(item.paper)}</p> : null}
            {Array.isArray(item.topic_scores) && item.topic_scores.length ? <div className="mt-2 flex flex-wrap gap-1">{item.topic_scores.map((entry, index) => { const score = entry as Record<string, unknown>; return <span key={`${text(score.topic)}-${index}`} className="rounded-full bg-muted px-2 py-1 text-[11px]">{text(score.topic)}: {text(score.score)}/{text(score.maximum_score)}</span>; })}</div> : null}
            {Array.isArray(item.criteria_scores) && item.criteria_scores.length ? <div className="mt-2 flex flex-wrap gap-1">{item.criteria_scores.map((entry, index) => { const score = entry as Record<string, unknown>; return <span key={`${text(score.criterion)}-${index}`} className="rounded-full bg-muted px-2 py-1 text-[11px]">{text(score.criterion)}: {text(score.score)}/{text(score.maximum_score)}</span>; })}</div> : null}
            <p className="mt-1.5 whitespace-pre-wrap text-[13px] leading-5 text-muted-foreground">
              {text(
                item.notes ||
                  item.overview ||
                  item.recommendation ||
                  "No notes",
              )}
            </p>
            {isVoided ? (
              <p className="mt-2 text-xs text-muted-foreground">
                Voided: {text(item.void_reason)} · {dateLabel(item.voided_at)}
              </p>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

function OutcomeFields({
  candidate,
  options,
}: {
  candidate: RecruitmentCandidate;
  options?: RecruitmentOptions;
}) {
  const canFinalize = Boolean(candidate.permissions?.can_finalize);
  const canReject = Boolean(candidate.permissions?.can_reject);
  const availableDecisions = canFinalize
    ? [
        "candidate_withdrew",
        "rejected",
        "teacher_academy",
        "active_teacher",
      ]
    : canReject
      ? ["rejected"]
      : ["candidate_withdrew"];
  const [decision, setDecision] = useState(availableDecisions[0]);
  const [rejectionReason, setRejectionReason] = useState("");
  const rejectionReasons = options?.rejection_reason_options?.length
    ? options.rejection_reason_options
    : (options?.rejection_reasons || []).map((value) => ({
        value,
        label: humanize(value),
      }));
  const approved = (candidate.approvals || []).filter(
    (item) => item.status === "approved",
  );
  const isHire =
    decision === "teacher_academy" || decision === "active_teacher";
  return (
    <>
      <label className="text-xs font-semibold">
        Decision
        <select
          name="decision"
          value={decision}
          onChange={(event) => setDecision(event.target.value)}
          className={`${fieldClass} mt-1`}
        >
          {availableDecisions.map((value) => (
            <option key={value} value={value}>
              {stageLabels[value]}
            </option>
          ))}
        </select>
      </label>
      {isHire ? (
        <label className="text-xs font-semibold">
          Approved request
          <select required name="approval_id" className={`${fieldClass} mt-1`}>
            <option value="">Select an approved request</option>
            {approved
              .filter((item) => item.requested_outcome === decision)
              .map((item) => (
                <option key={Number(item.id)} value={Number(item.id)}>
                  #{text(item.id)} · {stageLabels[text(item.requested_outcome)]}
                </option>
              ))}
          </select>
        </label>
      ) : null}
      {decision === "rejected" ? (
        <label className="text-xs font-semibold">
          Rejection reason
          <select
            required
            name="rejection_reason"
            value={rejectionReason}
            onChange={(event) => setRejectionReason(event.target.value)}
            className={`${fieldClass} mt-1`}
          >
            <option value="">Select a reason</option>
            {rejectionReasons.map((reason) => (
              <option key={reason.value} value={reason.value}>
                {reason.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {["rejected", "candidate_withdrew"].includes(decision) ? (
        <label className="text-xs font-semibold">
          Reason / explanation
          <textarea
            name="reason_detail"
            required={rejectionReason === "other"}
            className={`${fieldClass} mt-1 min-h-24`}
          />
        </label>
      ) : null}
    </>
  );
}

function MoveCandidateFields({
  candidate,
}: {
  candidate: RecruitmentCandidate;
}) {
  const [stage, setStage] = useState("");
  return (
    <div className="grid gap-3">
      <label className="text-xs font-semibold">
        New stage
        <select
          required
          name="stage"
          value={stage}
          onChange={(event) => setStage(event.target.value)}
          className={`${fieldClass} mt-1`}
        >
          <option value="">Choose a stage</option>
          {manualStages
            .filter((value) => value !== candidate.status)
            .map((value) => (
              <option key={value} value={value}>
                {stageLabels[value]}
              </option>
            ))}
          {candidate.status !== "trash_bin" ? (
            <option value="trash_bin">{stageLabels.trash_bin}</option>
          ) : null}
        </select>
      </label>
      <label className="text-xs font-semibold">
        Reason
        <textarea
          name="reason"
          defaultValue="Candidate profile move"
          className={`${fieldClass} mt-1 min-h-20`}
        />
      </label>
      <p className="text-xs leading-5 text-muted-foreground">
        Interview and demo appointments are scheduled separately after the move.
        Protected Academy/Active outcomes continue through Hiring.
      </p>
    </div>
  );
}

function CandidateOptionFields({ candidate, options }: { candidate: RecruitmentCandidate; options?: RecruitmentOptions }) {
  const [sourceId, setSourceId] = useState(String(candidate.source_option_id || ""));
  const [subsourceId, setSubsourceId] = useState(String(candidate.subsource_option_id || ""));
  const category = (name: string) => options?.option_categories?.[name] || [];
  return (
    <>
      <label className="text-xs font-semibold">Source<select name="source_option_id" value={sourceId} onChange={(event) => { setSourceId(event.target.value); setSubsourceId(""); }} className={`${fieldClass} mt-1`}><option value="">Not set</option>{(options?.sources || []).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label className="text-xs font-semibold">Subsource<select name="subsource_option_id" value={subsourceId} onChange={(event) => setSubsourceId(event.target.value)} disabled={!sourceId} required={Boolean(sourceId && (options?.subsources || []).some((item) => String(item.parent_id || "") === sourceId))} className={`${fieldClass} mt-1 disabled:opacity-60`}><option value="">{sourceId ? "Select subsource" : "Select a source first"}</option>{(options?.subsources || []).filter((item) => String(item.parent_id || "") === sourceId).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label className="text-xs font-semibold">English level<select name="english_level_option_id" defaultValue={candidate.english_level_option_id || ""} className={`${fieldClass} mt-1`}><option value="">Not set</option>{category("english_level").map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label className="text-xs font-semibold">Schedule<select name="schedule_option_id" defaultValue={candidate.schedule_option_id || ""} className={`${fieldClass} mt-1`}><option value="">Not set</option>{category("schedule").map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label className="text-xs font-semibold">Availability<select name="availability_option_id" defaultValue={candidate.availability_option_id || ""} className={`${fieldClass} mt-1`}><option value="">Not set</option>{category("availability").map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label className="text-xs font-semibold">Expected salary<select name="expected_salary_option_id" defaultValue={candidate.expected_salary_option_id || ""} className={`${fieldClass} mt-1`}><option value="">Not set</option>{category("expected_salary").map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label className="text-xs font-semibold sm:col-span-2">Teaching experience<select name="teaching_experience_option_id" defaultValue={candidate.teaching_experience_option_id || ""} className={`${fieldClass} mt-1`}><option value="">Not set</option>{category("teaching_experience").map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    </>
  );
}

function ActionFields({
  action,
  candidate,
  options,
  conflicts,
}: {
  action: ProfileAction;
  candidate: RecruitmentCandidate;
  options?: RecruitmentOptions;
  conflicts: RecruitmentAppointment[];
}) {
  switch (action.kind) {
    case "edit_profile":
      return (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-xs font-semibold">
            Full name
            <input
              name="full_name"
              defaultValue={candidate.full_name}
              required
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold">
            Phone
            <input
              name="phone"
              type="tel"
              defaultValue={candidate.phone}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold">
            Telegram
            <input
              name="telegram_username"
              defaultValue={candidate.telegram_username}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold">
            Position
            <input
              name="applied_position"
              defaultValue={candidate.applied_position}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold">Subject<select name="subject_id" defaultValue={candidate.subject_id || ""} className={`${fieldClass} mt-1`}><option value="">Not set</option>{options?.subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>
          <label className="text-xs font-semibold">
            Application date
            <input
              name="application_date"
              type="date"
              defaultValue={candidate.application_date?.slice(0, 10)}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <CandidateOptionFields candidate={candidate} options={options} />
          <label className="text-xs font-semibold">
            Age
            <input
              name="age"
              type="number"
              min="14"
              max="100"
              defaultValue={candidate.age || ""}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold">
            Available start date
            <input
              name="available_start_date"
              type="date"
              defaultValue={candidate.available_start_date?.slice(0, 10)}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold sm:col-span-2">
            Address
            <textarea
              name="address"
              defaultValue={candidate.address}
              className={`${fieldClass} mt-1 min-h-20`}
            />
          </label>
          <label className="text-xs font-semibold sm:col-span-2">
            Education background
            <textarea
              name="education_background"
              defaultValue={candidate.education_background}
              className={`${fieldClass} mt-1 min-h-20`}
            />
          </label>
          <label className="text-xs font-semibold sm:col-span-2">
            Work experience
            <textarea
              name="work_experience"
              defaultValue={candidate.work_experience}
              className={`${fieldClass} mt-1 min-h-20`}
            />
          </label>
          <label className="text-xs font-semibold sm:col-span-2">
            Motivation & expectations
            <textarea
              name="motivation_expectations"
              defaultValue={candidate.motivation_expectations}
              className={`${fieldClass} mt-1 min-h-20`}
            />
          </label>
          <label className="text-xs font-semibold sm:col-span-2">
            Interests & hobbies
            <textarea
              name="interests_hobbies"
              defaultValue={candidate.interests_hobbies}
              className={`${fieldClass} mt-1 min-h-20`}
            />
          </label>
        </div>
      );
    case "move_candidate":
      return <MoveCandidateFields candidate={candidate} />;
    case "upload_document":
      return (
        <div className="grid gap-3">
          <label className="text-xs font-semibold">
            Document type
            <select
              name="document_type"
              required
              defaultValue={text(action.document?.document_type)}
              className={`${fieldClass} mt-1`}
            >
              <option value="">Select document type</option>
              {options?.document_types.map((type) => (
                <option key={type} value={type}>
                  {humanize(type)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold">
            PDF, DOC/DOCX, JPG or PNG (max 20 MB)
            <input
              name="document"
              required
              type="file"
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
              className={`${fieldClass} mt-1 file:mr-2 file:border-0 file:bg-transparent file:font-semibold`}
            />
          </label>
          {action.document ? (
            <input
              type="hidden"
              name="replaces_document_id"
              value={Number(action.document.id)}
            />
          ) : null}
          {!options?.document_upload_enabled ? (
            <p className="text-xs text-muted-foreground">
              Storage is not configured. Uploads remain disabled.
            </p>
          ) : null}
        </div>
      );
    case "record_interview":
      return (
        <div className="grid gap-3">
          {action.appointment ? (
            <input
              type="hidden"
              name="appointment_id"
              value={action.appointment.id}
            />
          ) : null}
          <label className="text-xs font-semibold">
            Result
            <select required name="result" className={`${fieldClass} mt-1`}>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="additional_interview">Additional interview</option>
              <option value="candidate_withdrew">Candidate withdrew</option>
            </select>
          </label>
          <label className="text-xs font-semibold">
            Format
            <input
              name="interview_format"
              defaultValue={action.appointment?.appointment_format}
              className={`${fieldClass} mt-1`}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="text-xs font-semibold">CEFR<select name="cefr_level" className={`${fieldClass} mt-1`}><option value="">Not set</option>{["A1", "A2", "B1", "B2", "C1", "C2"].map((value) => <option key={value}>{value}</option>)}</select></label>
            <label className="text-xs font-semibold">Overall (0–10)<input name="overall_score" type="number" min="0" max="10" step="0.1" className={`${fieldClass} mt-1`} /></label>
            <label className="text-xs font-semibold">Communication (0–10)<input name="communication_score" type="number" min="0" max="10" step="0.1" className={`${fieldClass} mt-1`} /></label>
          </div>
          <label className="text-xs font-semibold">Recommendation<select name="recommendation_code" className={`${fieldClass} mt-1`}><option value="">Not set</option><option value="proceed">Proceed</option><option value="hold">Hold</option><option value="reject">Reject</option></select></label>
          <label className="text-xs font-semibold">
            Notes
            <textarea name="notes" className={`${fieldClass} mt-1 min-h-24`} />
          </label>
          <label className="text-xs font-semibold">
            HR recommendation
            <textarea
              name="hr_recommendation"
              className={`${fieldClass} mt-1 min-h-24`}
            />
          </label>
        </div>
      );
    case "record_test":
      return (
        <div className="grid gap-3">
          <label className="text-xs font-semibold">Paper / version<input name="paper" className={`${fieldClass} mt-1`} /></label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs font-semibold">
              Score
              <input
                name="score"
                type="number"
                min="0"
                step="0.01"
                className={`${fieldClass} mt-1`}
              />
            </label>
            <label className="text-xs font-semibold">
              Maximum score
              <input
                name="maximum_score"
                type="number"
                min="0.01"
                step="0.01"
                className={`${fieldClass} mt-1`}
              />
            </label>
          </div>
          <fieldset className="rounded-lg border border-border p-3"><legend className="px-1 text-xs font-semibold">Topic result (optional)</legend><div className="grid gap-2 sm:grid-cols-3"><input name="topic_name" placeholder="Topic" className={fieldClass} /><input name="topic_score" aria-label="Topic score" type="number" min="0" step="0.1" placeholder="Score" className={fieldClass} /><input name="topic_maximum" aria-label="Topic maximum" type="number" min="0.1" step="0.1" placeholder="Maximum" className={fieldClass} /></div></fieldset>
          <label className="text-xs font-semibold">
            Result
            <select name="result" className={`${fieldClass} mt-1`}>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="retake_required">Retake required</option>
              <option value="not_completed">Not completed</option>
            </select>
          </label>
          <label className="text-xs font-semibold">
            Notes
            <textarea name="notes" className={`${fieldClass} mt-1 min-h-24`} />
          </label>
        </div>
      );
    case "record_demo":
      return (
        <div className="grid gap-3">
          <input type="hidden" name="appointment_id" value={action.appointment?.id || ""} />
          <input type="hidden" name="topic" value={action.appointment?.topic || ""} />
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg bg-muted/60 px-3 py-2"><span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Date</span><strong className="mt-0.5 block text-sm">{scheduledDatePart(action.appointment?.starts_at)}</strong></div>
            <div className="rounded-lg bg-muted/60 px-3 py-2"><span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Time</span><strong className="mt-0.5 block text-sm">{scheduledTimePart(action.appointment?.starts_at)}</strong></div>
          </div>
          <div className="rounded-lg bg-muted/60 px-3 py-2"><span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Full name</span><strong className="mt-0.5 block text-sm">{candidate.full_name}</strong></div>
          <label className="text-xs font-semibold">
            Evaluator's notes
            <textarea
              autoFocus
              required
              name="overview"
              className={`${fieldClass} mt-1 min-h-28 resize-y`}
            />
          </label>
        </div>
      );
    case "schedule_appointment":
      return (
        <AppointmentForm
          appointmentType={action.appointmentType}
          options={options}
          conflicts={conflicts}
        />
      );
    case "reschedule_appointment":
      return (
        <AppointmentForm
          appointmentType={action.appointment.appointment_type}
          appointment={action.appointment}
          options={options}
          conflicts={conflicts}
        />
      );
    case "appointment_status":
      return (
        <label className="text-xs font-semibold">
          Reason / note
          <textarea
            autoFocus
            required={action.status === "cancelled"}
            name="reason"
            className={`${fieldClass} mt-1 min-h-24`}
          />
        </label>
      );
    case "assign_evaluators": {
      const assigned = new Set(
        (candidate.assignments || []).map((item) =>
          Number(item.assignee_account_id),
        ),
      );
      const evaluators =
        options?.staff.filter((person) =>
          ["academic_director", "head_of_department"].includes(person.role),
        ) || [];
      return (
        <fieldset>
          <legend className="text-xs font-semibold">Assigned evaluators</legend>
          <div className="mt-2 space-y-2">
            {evaluators.map((person) => (
              <label
                key={person.id}
                className="flex min-h-11 items-center gap-3 rounded-lg border border-border px-3 text-sm"
              >
                <input
                  type="checkbox"
                  name="assignee_account_ids"
                  value={person.id}
                  defaultChecked={assigned.has(person.id)}
                  className="h-4 w-4"
                />
                <span>
                  <span className="font-semibold">{person.name}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {humanize(person.role)}
                  </span>
                </span>
              </label>
            ))}
          </div>
          {!evaluators.length ? (
            <EmptyLine>No eligible evaluators.</EmptyLine>
          ) : null}
        </fieldset>
      );
    }
    case "request_approval":
      return (
        <div className="grid gap-3">
          <label className="text-xs font-semibold">
            Requested outcome
            <select
              name="requested_outcome"
              defaultValue={
                text(action.previous?.requested_outcome) || "teacher_academy"
              }
              className={`${fieldClass} mt-1`}
            >
              <option value="teacher_academy">Teacher Academy</option>
              <option value="active_teacher">Active Teacher</option>
            </select>
          </label>
          <label className="text-xs font-semibold">
            Request note
            <textarea
              name="request_note"
              defaultValue={text(action.previous?.request_note)}
              className={`${fieldClass} mt-1 min-h-24`}
            />
          </label>
        </div>
      );
    case "record_outcome":
      return (
        <div className="grid gap-3">
          <OutcomeFields candidate={candidate} options={options} />
        </div>
      );
    case "review_approval":
      return (
        <div className="grid gap-3">
          <p className="rounded-lg bg-muted/50 p-3 text-sm">
            {action.status === "approved"
              ? `${stageLabels[text(action.approval.requested_outcome)]} will be approved and finalized. The onboarding record will remain pending.`
              : `${stageLabels[text(action.approval.requested_outcome)]} approval will be returned to HR.`}
          </p>
          <label className="text-xs font-semibold">
            Comment
            <textarea
              name="review_comment"
              required={action.status === "returned"}
              defaultValue={
                action.status === "approved"
                  ? "Approved and finalized by Academic Director."
                  : ""
              }
              className={`${fieldClass} mt-1 min-h-24`}
            />
          </label>
        </div>
      );
    case "withdraw_candidate":
      return (
        <label className="text-xs font-semibold">
          Withdrawal reason
          <textarea
            autoFocus
            required
            name="reason_detail"
            className={`${fieldClass} mt-1 min-h-24`}
          />
        </label>
      );
    case "void_evaluation":
      return (
        <div className="grid gap-3">
          <p className="rounded-lg bg-muted/50 p-3 text-sm">
            This keeps the result in history but excludes it from the
            candidate's latest evaluation summary.
          </p>
          <label className="text-xs font-semibold">
            Why is this result being voided?
            <textarea
              autoFocus
              required
              name="reason"
              className={`${fieldClass} mt-1 min-h-24`}
            />
          </label>
        </div>
      );
    case "add_task":
      return (
        <div className="grid gap-3">
          <label className="text-xs font-semibold">
            Title
            <input required name="title" className={`${fieldClass} mt-1`} />
          </label>
          <label className="text-xs font-semibold">
            Due date
            <input
              name="due_at"
              type="datetime-local"
              className={`${fieldClass} mt-1`}
            />
          </label>
          <label className="text-xs font-semibold">
            Note
            <textarea name="note" className={`${fieldClass} mt-1 min-h-24`} />
          </label>
          <input type="hidden" name="status" value="pending" />
        </div>
      );
    case "add_note":
      return (
        <label className="text-xs font-semibold">
          Note
          <textarea
            autoFocus
            required
            name="body"
            className={`${fieldClass} mt-1 min-h-32`}
          />
        </label>
      );
  }
}

function actionTitle(action: ProfileAction | null) {
  if (!action) return "Candidate action";
  switch (action.kind) {
    case "edit_profile":
      return "Edit candidate profile";
    case "move_candidate":
      return "Move candidate";
    case "upload_document":
      return action.document ? "Replace document" : "Upload document";
    case "record_interview":
      return "Record interview";
    case "record_test":
      return "Record subject test";
    case "record_demo":
      return "Record demo lesson";
    case "schedule_appointment":
      return action.appointmentType === "job_interview"
        ? "Schedule job interview"
        : "Schedule demo lesson";
    case "reschedule_appointment":
      return "Reschedule appointment";
    case "appointment_status":
      return action.status === "cancelled"
        ? "Cancel appointment"
        : "Mark no-show";
    case "assign_evaluators":
      return "Assign evaluators";
    case "request_approval":
      return "Request hiring approval";
    case "record_outcome":
      return "Record outcome";
    case "review_approval":
      return action.status === "approved"
        ? "Approve and finalize"
        : "Return request";
    case "withdraw_candidate":
      return "Candidate withdrew";
    case "void_evaluation":
      return "Void evaluation result";
    case "add_task":
      return "Add task";
    case "add_note":
      return "Add note";
  }
}

function actionSubmitLabel(action: ProfileAction | null) {
  if (!action) return "Save";
  if (action.kind === "move_candidate") return "Move candidate";
  if (action.kind === "schedule_appointment") return "Schedule appointment";
  if (action.kind === "reschedule_appointment") return "Save appointment";
  if (action.kind === "appointment_status")
    return action.status === "cancelled"
      ? "Cancel appointment"
      : "Mark no-show";
  if (action.kind === "review_approval")
    return action.status === "approved"
      ? "Approve & finalize"
      : "Return request";
  if (action.kind === "upload_document")
    return action.document ? "Replace" : "Upload";
  return "Save";
}

export function CandidateProfile({
  candidateId,
  basePath,
  role,
  onAnnouncement,
}: {
  candidateId: number;
  basePath: string;
  role: string;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const visibleProfileTabs =
    role === "hr_manager" ? hrProfileTabs : profileTabs;
  const requestedTab =
    new URLSearchParams(window.location.search).get("tab") || "overview";
  const [tab, setTab] = useState<ProfileTab>(
    visibleProfileTabs.some((item) => item.key === requestedTab)
      ? (requestedTab as ProfileTab)
      : "overview",
  );
  const [action, setAction] = useState<ProfileAction | null>(null);
  const [interviewSession, setInterviewSession] = useState<RecruitmentAppointment | null>(null);
  const [appointmentConflicts, setAppointmentConflicts] = useState<
    RecruitmentAppointment[]
  >([]);
  const [removeDocument, setRemoveDocument] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [activeInlineField, setActiveInlineField] = useState<InlineEditTarget | null>(null);
  const [inlineFieldDirty, setInlineFieldDirty] = useState(false);
  const [pendingInlineField, setPendingInlineField] = useState<InlineEditTarget | null>(null);
  const [confirmInlineClose, setConfirmInlineClose] = useState(false);
  const formId = useId();
  const detail = useQuery({
    queryKey: ["recruitment", "candidate", candidateId],
    queryFn: () =>
      recruitmentRequest<RecruitmentCandidate>(
        `${RECRUITMENT_API}/candidates/${candidateId}`,
      ),
  });
  const options = useQuery({
    queryKey: ["recruitment", "options"],
    queryFn: () =>
      recruitmentRequest<RecruitmentOptions>(`${RECRUITMENT_API}/options`),
  });
  const mutation = useMutation({
    mutationFn: ({
      url,
      method = "POST",
      values,
      formData,
    }: {
      url: string;
      method?: string;
      values?: unknown;
      formData?: FormData;
    }) =>
      recruitmentRequest<MutationPayload>(url, {
        method,
        body: formData || jsonBody(values || {}),
      }),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Recruitment record saved.");
      if (result.candidate)
        queryClient.setQueryData(
          ["recruitment", "candidate", candidateId],
          result.candidate,
        );
      const completedDirectorDecision =
        role === "academic_director" &&
        ((action?.kind === "review_approval" && action.status === "approved") ||
          action?.kind === "record_outcome");
      if (completedDirectorDecision) {
        window.location.assign(`${basePath}/decisions?updated=1`);
        return;
      }
      setAction(null);
      setAppointmentConflicts([]);
      setRemoveDocument(null);
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => {
      const conflicts =
        appointmentConflictDetails<RecruitmentAppointment>(error);
      if (conflicts.length) setAppointmentConflicts(conflicts);
      onAnnouncement(queryError(error), "error");
    },
  });

  useEffect(() => {
    const onPopState = () => {
      const next =
        new URLSearchParams(window.location.search).get("tab") || "overview";
      if (visibleProfileTabs.some((item) => item.key === next))
        setTab(next as ProfileTab);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [visibleProfileTabs]);

  if (detail.isLoading)
    return <PageState>Loading candidate profile…</PageState>;
  if (detail.error || !detail.data)
    return <PageState tone="error">{queryError(detail.error)}</PageState>;
  const candidate = detail.data;
  const permissions = candidate.permissions;
  const approved = (candidate.approvals || []).filter(
    (item) => item.status === "approved",
  );
  const pendingApprovals = (candidate.approvals || []).filter(
    (item) => item.status === "requested",
  );
  const latestInterview = candidate.interviews?.find((item) => !item.voided_at);
  const latestTest = candidate.subject_tests?.find((item) => !item.voided_at);
  const latestDemo = candidate.demo_lessons?.find((item) => !item.voided_at);
  const scheduledAppointments = (candidate.appointments || []).filter(
    (item) => ["scheduled", "in_progress"].includes(item.status),
  );
  const pendingTasks = (candidate.tasks || []).filter((task) =>
    ["pending", "overdue"].includes(task.effective_status),
  );

  const saveInlineField = (
    field: keyof RecruitmentCandidate,
    rawValue: string,
  ) => {
    let value: string | number | null = rawValue.trim() || null;
    if (["age", "expected_salary_uzs", "subject_id", "source_option_id", "subsource_option_id", "english_level_option_id", "schedule_option_id", "availability_option_id", "expected_salary_option_id", "teaching_experience_option_id"].includes(field) && value !== null)
      value = Number(value);
    mutation.mutate({
      url: `${RECRUITMENT_API}/candidates/${candidateId}`,
      method: "PATCH",
      values: {
        [field]: value,
        ...(field === "source_option_id" ? { subsource_option_id: null } : {}),
        expected_version: candidate.version,
      },
    });
  };

  const saveInlineSource = (selection: string) => {
    const [source, subsource] = selection.split(":");
    mutation.mutate({
      url: `${RECRUITMENT_API}/candidates/${candidateId}`,
      method: "PATCH",
      values: {
        source_option_id: source ? Number(source) : null,
        subsource_option_id: subsource ? Number(subsource) : null,
        expected_version: candidate.version,
      },
    });
  };

  const requestInlineEdit = (target: InlineEditTarget) => {
    if (activeInlineField?.id === target.id) return;
    if (activeInlineField && inlineFieldDirty) {
      setPendingInlineField(target);
      return;
    }
    setConfirmInlineClose(false);
    setInlineFieldDirty(false);
    setActiveInlineField(target);
  };
  const closeInlineEdit = () => {
    setPendingInlineField(null);
    setConfirmInlineClose(false);
    setInlineFieldDirty(false);
    setActiveInlineField(null);
  };
  const requestInlineDismiss = (event?: KeyboardEvent | PointerEvent) => {
    if (event instanceof PointerEvent && event.target instanceof Element && event.target.closest("[data-inline-edit-trigger]")) return;
    if (!activeInlineField) return;
    if (inlineFieldDirty) {
      setConfirmInlineClose(true);
      return;
    }
    closeInlineEdit();
  };
  const inlineEditProps = (id: string, label: string) => ({
    fieldId: id,
    editing: activeInlineField?.id === id,
    onRequestEdit: () => requestInlineEdit({ id, label }),
    onDirtyChange: setInlineFieldDirty,
    onRequestDismiss: requestInlineDismiss,
    onFinish: closeInlineEdit,
    onCancel: closeInlineEdit,
  });

  const setProfileTab = (next: ProfileTab) => {
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setTab(next);
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  };

  const handleTabKeyDown = (
    event: ReactKeyboardEvent<HTMLButtonElement>,
    current: ProfileTab,
  ) => {
    const currentIndex = visibleProfileTabs.findIndex(
      (item) => item.key === current,
    );
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight")
      nextIndex = (currentIndex + 1) % visibleProfileTabs.length;
    if (event.key === "ArrowLeft")
      nextIndex =
        (currentIndex - 1 + visibleProfileTabs.length) %
        visibleProfileTabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = visibleProfileTabs.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    const next = visibleProfileTabs[nextIndex].key;
    setProfileTab(next);
    requestAnimationFrame(() =>
      document.getElementById(`candidate-tab-${next}`)?.focus(),
    );
  };

  const params = new URLSearchParams(window.location.search);
  const origin = params.get("origin");
  const returnQuery = params.get("return") || "";
  const safeReturn = returnQuery.startsWith("?") ? returnQuery : "";
  const backHref =
    origin === "pipeline"
      ? `${basePath}/pipeline`
      : origin === "decisions"
        ? `${basePath}/decisions`
      : origin === "schedule"
          ? `${basePath}/schedule`
          : origin === "teachers"
            ? `${basePath}/teachers`
          : origin === "tasks"
            ? `${basePath}/tasks`
            : origin === "trash" ? `${basePath}/trash${safeReturn}`
              : origin === "rejected"
                ? `${basePath}/rejected${safeReturn}`
                : role === "hr_manager"
                  ? `${basePath}/pipeline`
                  : `${basePath}/candidates${safeReturn}`;
  const backLabel =
    origin === "pipeline"
      ? "Pipeline"
      : origin === "decisions"
        ? "Decisions"
        : origin === "schedule"
          ? "Schedule"
          : origin === "tasks"
            ? "Tasks"
            : origin === "trash" ? "Trash Bin"
              : origin === "rejected"
                ? "Rejected"
                : role === "hr_manager"
                  ? "Pipeline"
                  : "Candidates";
  const backPath =
    origin === "pipeline"
      ? `${basePath}/pipeline`
      : origin === "decisions"
        ? `${basePath}/decisions`
        : origin === "schedule"
          ? `${basePath}/schedule`
          : origin === "tasks"
            ? `${basePath}/tasks`
            : origin === "trash" ? `${basePath}/trash`
              : origin === "rejected"
                ? `${basePath}/rejected`
                : role === "hr_manager"
                  ? `${basePath}/pipeline`
                  : `${basePath}/candidates`;

  const submit = (path: string, values: unknown, method = "POST") =>
    mutation.mutate({
      url: `${RECRUITMENT_API}/candidates/${candidateId}${path}`,
      method,
      values,
    });
  const submitAction = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!action) return;
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const form = event.currentTarget;
    if (action.kind === "upload_document") {
      mutation.mutate({
        url: `${RECRUITMENT_API}/candidates/${candidateId}/documents`,
        method: "POST",
        formData: new FormData(form),
      });
    } else if (action.kind === "edit_profile") {
      submit("", formValues(form), "PATCH");
    } else if (action.kind === "move_candidate") {
      const values = formValues(form);
      submit("/stage", { ...values, expected_version: candidate.version });
    } else if (action.kind === "record_interview") {
      submit("/interviews", formValues(form));
    } else if (action.kind === "record_test") {
      const values = formValues(form);
      const topic = String(values.topic_name || "").trim();
      const topicScore = Number(values.topic_score);
      const topicMaximum = Number(values.topic_maximum);
      delete values.topic_name;
      delete values.topic_score;
      delete values.topic_maximum;
      submit("/subject-tests", {
        ...values,
        subject_id: candidate.subject_id || null,
        topic_scores: topic && Number.isFinite(topicScore) && topicMaximum > 0 ? [{ topic, score: topicScore, maximum_score: topicMaximum }] : [],
      });
    } else if (action.kind === "record_demo") {
      const values = formValues(form);
      const result = submitter?.name === "result" ? submitter.value : "";
      if (!['passed', 'failed'].includes(result)) return;
      submit("/demo-lessons", {
        ...values,
        result,
        subject_id: candidate.subject_id || null,
        criteria_scores: [],
      });
    } else if (action.kind === "schedule_appointment") {
      submit("/appointments", {
        ...formValues(form),
        appointment_type: action.appointmentType,
        allow_conflict: Boolean(appointmentConflicts.length),
      });
    } else if (action.kind === "reschedule_appointment") {
      submit(
        `/appointments/${action.appointment.id}`,
        {
          ...formValues(form),
          expected_version: action.appointment.version,
          allow_conflict: Boolean(appointmentConflicts.length),
        },
        "PATCH",
      );
    } else if (action.kind === "appointment_status") {
      submit(
        `/appointments/${action.appointment.id}/${action.status === "cancelled" ? "cancel" : "no-show"}`,
        { ...formValues(form), expected_version: action.appointment.version },
      );
    } else if (action.kind === "assign_evaluators") {
      const ids = new FormData(form)
        .getAll("assignee_account_ids")
        .map(Number)
        .filter(Boolean);
      submit(
        "/assignments",
        { assignee_account_ids: ids, subject_id: candidate.subject_id || null },
        "PUT",
      );
    } else if (action.kind === "request_approval") {
      submit("/approval-requests", formValues(form));
    } else if (action.kind === "record_outcome") {
      const values = formValues(form);
      submit("/final-decisions", {
        ...values,
        approval_id: values.approval_id ? Number(values.approval_id) : null,
      });
    } else if (action.kind === "review_approval") {
      submit(`/approval-requests/${Number(action.approval.id)}/review`, {
        status: action.status,
        ...formValues(form),
      });
    } else if (action.kind === "withdraw_candidate") {
      submit("/final-decisions", {
        decision: "candidate_withdrew",
        ...formValues(form),
      });
    } else if (action.kind === "void_evaluation") {
      const segment =
        action.evaluationType === "interview"
          ? "interviews"
          : action.evaluationType === "subject_test"
            ? "subject-tests"
            : "demo-lessons";
      submit(`/${segment}/${Number(action.attempt.id)}/void`, formValues(form));
    } else if (action.kind === "add_task") {
      submit("/tasks", formValues(form));
    } else if (action.kind === "add_note") {
      submit("/notes", formValues(form));
    }
  };

  const evaluationItems: ActionMenuItem[] = [];
  if (permissions?.can_manage_appointments) {
    if (candidate.status === "job_interview")
      evaluationItems.push({
        key: "schedule_interview",
        label: "Schedule interview",
        onClick: () => {
          setAppointmentConflicts([]);
          setAction({
            kind: "schedule_appointment",
            appointmentType: "job_interview",
          });
        },
      });
    if (candidate.status === "test_and_demo")
      evaluationItems.push({
        key: "schedule_demo",
        label: "Schedule demo lesson",
        onClick: () => {
          setAppointmentConflicts([]);
          setAction({
            kind: "schedule_appointment",
            appointmentType: "demo_lesson",
          });
        },
      });
  }
  if (permissions?.can_add_academic_evaluation) {
    evaluationItems.push({
      key: "test",
      label: "Record subject test",
      onClick: () => setAction({ kind: "record_test" }),
    });
    const scheduledDemo = scheduledAppointments.find((item) => item.appointment_type === "demo_lesson" && item.status === "scheduled");
    if (scheduledDemo) evaluationItems.push({
      key: "demo",
      label: "Record demo lesson",
      onClick: () => setAction({ kind: "record_demo", appointment: scheduledDemo }),
    });
  }
  const hiringItems: ActionMenuItem[] = [];
  if (role !== "hr_manager" && permissions?.can_manage_assignments)
    hiringItems.push({
      key: "assign",
      label: "Assign evaluators",
      onClick: () => setAction({ kind: "assign_evaluators" }),
    });
  if (role !== "hr_manager" && permissions?.can_request_approval)
    hiringItems.push({
      key: "request",
      label: "Request hiring approval",
      onClick: () => setAction({ kind: "request_approval" }),
    });
  if (
    role !== "hr_manager" &&
    (permissions?.can_finalize || permissions?.can_reject)
  )
    hiringItems.push({
      key: "outcome",
      label:
        permissions?.can_reject && !permissions?.can_finalize
          ? "Reject candidate"
          : "Record outcome",
      onClick: () => setAction({ kind: "record_outcome" }),
    });
  const activityItems: ActionMenuItem[] = [];
  if (permissions?.can_manage_tasks)
    activityItems.push({
      key: "task",
      label: "Add task",
      onClick: () => setAction({ kind: "add_task" }),
    });
  if (permissions?.can_add_note)
    activityItems.push({
      key: "note",
      label: "Add note",
      onClick: () => setAction({ kind: "add_note" }),
    });

  const overviewItems: ActionMenuItem[] = [];
  if (
    permissions?.can_move_stage &&
    !["teacher_academy", "active_teacher"].includes(candidate.status)
  ) {
    overviewItems.push({
      key: "move",
      label: "Move candidate",
      onClick: () => setAction({ kind: "move_candidate" }),
    });
  }
  if (
    role === "hr_manager" &&
    ![
      "candidate_withdrew",
      "rejected",
      "trash_bin",
      "teacher_academy",
      "active_teacher",
    ].includes(candidate.status)
  ) {
    overviewItems.push({
      key: "withdraw",
      label: "Candidate withdrew",
      onClick: () => setAction({ kind: "withdraw_candidate" }),
    });
  }
  if (role === "hr_manager")
    overviewItems.push({
      key: "history",
      label: "View history",
      onClick: () => setHistoryOpen(true),
    });

  const returnedApproval = (candidate.approvals || []).find(
    (item) => item.status === "returned",
  );
  const hrHiringAction =
    role === "hr_manager" && permissions?.can_request_approval ? (
      <button
        type="button"
        className={buttonClass}
        onClick={() =>
          setAction({ kind: "request_approval", previous: returnedApproval })
        }
      >
        <ShieldCheck className="h-4 w-4" />
        {returnedApproval ? "Resubmit" : "Send to Academic Director"}
      </button>
    ) : null;

  const tabAction =
    tab === "overview" &&
    (permissions?.can_edit_profile || overviewItems.length) ? (
      <div className="flex items-center gap-1">
        {role !== "hr_manager" && permissions?.can_edit_profile ? (
          <button
            type="button"
            className={buttonClass}
            aria-label="Edit profile"
            title="Edit profile"
            onClick={() => setAction({ kind: "edit_profile" })}
          >
            <Pencil className="h-4 w-4" />
            <span className="hidden sm:inline">Edit profile</span>
          </button>
        ) : null}
        {overviewItems.length ? (
          <ActionMenu items={overviewItems} label="Candidate actions" />
        ) : null}
      </div>
    ) : tab === "evaluations" && evaluationItems.length ? (
      <ActionMenu items={evaluationItems} label="Add evaluation" />
    ) : tab === "documents" && permissions?.can_manage_documents ? (
      <button
        type="button"
        className={buttonClass}
        aria-label="Upload document"
        title="Upload document"
        disabled={!options.data?.document_upload_enabled}
        onClick={() => setAction({ kind: "upload_document" })}
      >
        <Plus className="h-4 w-4" />
        <span className="hidden sm:inline">Upload</span>
      </button>
    ) : tab === "hiring" && (hrHiringAction || hiringItems.length) ? (
      <div className="flex items-center gap-1">
        {hrHiringAction}
        {hiringItems.length ? (
          <ActionMenu items={hiringItems} label="Hiring actions" />
        ) : null}
      </div>
    ) : tab === "activity" && activityItems.length ? (
      <ActionMenu items={activityItems} label="Activity actions" />
    ) : null;

  return (
    <div className="space-y-3">
      <header className="sticky top-[calc(var(--app-top-inset)+4.5rem)] z-20 rounded-xl border border-border bg-card/95 p-3 shadow-sm backdrop-blur lg:top-3">
        <div className="flex items-start gap-2">
          <a
            href={backHref}
            onClick={(event) => {
              try {
                const previous = new URL(document.referrer);
                if (
                  origin &&
                  previous.origin === window.location.origin &&
                  previous.pathname === backPath
                ) {
                  event.preventDefault();
                  window.history.back();
                }
              } catch {
                /* Direct deep links use the safe fallback href. */
              }
            }}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            aria-label={`Back to ${backLabel}`}
            title={`Back to ${backLabel}`}
          >
            <ArrowLeft className="h-4 w-4" />
          </a>
          <div className="min-w-0 flex-1 py-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-lg font-bold tracking-tight sm:text-xl">
                {candidate.full_name}
              </h1>
              <StatusBadge status={candidate.status}>
                {stageLabels[candidate.status] || humanize(candidate.status)}
              </StatusBadge>
            </div>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {candidate.applied_position ||
                candidate.subject ||
                "Position not set"}
              {candidate.next_appointment
                ? ` · Next: ${candidate.next_appointment.appointment_type === "job_interview" ? "Interview" : "Demo"} ${dateLabel(candidate.next_appointment.starts_at)}`
                : candidate.next_task
                  ? ` · Next: ${candidate.next_task.title}`
                  : ""}
            </p>
          </div>
          <div className="shrink-0">{tabAction}</div>
        </div>
        <label className="mt-2 block text-xs font-semibold text-muted-foreground sm:hidden">
          Profile section
          <select
            value={tab}
            onChange={(event) =>
              setProfileTab(event.target.value as ProfileTab)
            }
            className={`${fieldClass} mt-1`}
          >
            {visibleProfileTabs.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <div
          className="mt-2 hidden gap-1 border-t border-border pt-2 sm:flex"
          role="tablist"
          aria-label="Candidate profile sections"
        >
          {visibleProfileTabs.map((item) => (
            <button
              key={item.key}
              id={`candidate-tab-${item.key}`}
              type="button"
              role="tab"
              tabIndex={tab === item.key ? 0 : -1}
              aria-selected={tab === item.key}
              aria-controls={`candidate-panel-${item.key}`}
              onClick={() => setProfileTab(item.key)}
              onKeyDown={(event) => handleTabKeyDown(event, item.key)}
              className={`min-h-11 rounded-lg px-3 text-[13px] font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${tab === item.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      {tab === "overview" ? (
        <div
          id="candidate-panel-overview"
          role="tabpanel"
          aria-labelledby="candidate-tab-overview"
          className="grid gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]"
        >
          <Panel
            title="Personal & background"
            icon={<UserRound className="h-4 w-4" />}
          >
            {role === "hr_manager" && permissions?.can_edit_profile ? (
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                <InlineField
                  label="Full name"
                  {...inlineEditProps("full_name", "Full name")}
                  value={candidate.full_name}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("full_name", value)}
                />
                <InlineField
                  label="Position"
                  {...inlineEditProps("applied_position", "Position")}
                  value={candidate.applied_position}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("applied_position", value)}
                />
                <InlineField
                  label="Subject"
                  {...inlineEditProps("subject_id", "Subject")}
                  value={candidate.subject_id}
                  displayValue={candidate.subject}
                  options={(options.data?.subjects || []).map((item) => ({ value: String(item.id), label: item.name }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("subject_id", value)}
                />
                <InlineField
                  label="Phone"
                  {...inlineEditProps("phone", "Phone")}
                  value={candidate.phone}
                  type="tel"
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("phone", value)}
                />
                <InlineField
                  label="Telegram"
                  {...inlineEditProps("telegram_username", "Telegram")}
                  value={candidate.telegram_username}
                  busy={mutation.isPending}
                  onSave={(value) =>
                    saveInlineField("telegram_username", value)
                  }
                />
                <InlineField
                  label="Application date"
                  {...inlineEditProps("application_date", "Application date")}
                  value={candidate.application_date?.slice(0, 10)}
                  displayValue={dateLabel(candidate.application_date)}
                  type="date"
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("application_date", value)}
                />
                <InlineField
                  label="Source → Subsource"
                  {...inlineEditProps("source_selection", "Source and subsource")}
                  value={candidate.source_option_id ? `${candidate.source_option_id}:${candidate.subsource_option_id || ""}` : ""}
                  displayValue={[candidate.source, candidate.subsource].filter(Boolean).join(" → ")}
                  options={(options.data?.sources || []).flatMap((source) => {
                    const children = (options.data?.subsources || []).filter((item) => item.parent_id === source.id);
                    return children.length
                      ? children.map((child) => ({ value: `${source.id}:${child.id}`, label: `${source.label} → ${child.label}` }))
                      : [{ value: `${source.id}:`, label: source.label }];
                  })}
                  busy={mutation.isPending}
                  onSave={saveInlineSource}
                />
                <InlineField
                  label="Age"
                  {...inlineEditProps("age", "Age")}
                  value={candidate.age}
                  type="number"
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("age", value)}
                />
                <InlineField
                  label="English"
                  {...inlineEditProps("english_level_option_id", "English")}
                  value={candidate.english_level_option_id}
                  displayValue={candidate.english_level}
                  options={(options.data?.option_categories?.english_level || []).map((item) => ({ value: item.id, label: item.label }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("english_level_option_id", value)}
                />
                <InlineField
                  label="Schedule"
                  {...inlineEditProps("schedule_option_id", "Schedule")}
                  value={candidate.schedule_option_id}
                  displayValue={candidate.preferred_schedule}
                  options={(options.data?.option_categories?.schedule || []).map((item) => ({ value: item.id, label: item.label }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("schedule_option_id", value)}
                />
                <InlineField
                  label="Availability"
                  {...inlineEditProps("availability_option_id", "Availability")}
                  value={candidate.availability_option_id}
                  displayValue={candidate.employment_availability}
                  options={(options.data?.option_categories?.availability || []).map((item) => ({ value: item.id, label: item.label }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("availability_option_id", value)}
                />
                <InlineField
                  label="Start date"
                  {...inlineEditProps("available_start_date", "Start date")}
                  value={candidate.available_start_date?.slice(0, 10)}
                  displayValue={dateLabel(candidate.available_start_date)}
                  type="date"
                  busy={mutation.isPending}
                  onSave={(value) =>
                    saveInlineField("available_start_date", value)
                  }
                />
                <InlineField
                  label="Expected salary"
                  {...inlineEditProps("expected_salary_option_id", "Expected salary")}
                  value={candidate.expected_salary_option_id}
                  displayValue={candidate.expected_salary}
                  options={(options.data?.option_categories?.expected_salary || []).map((item) => ({ value: item.id, label: item.label }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("expected_salary_option_id", value)}
                />
                <InlineField
                  label="Address"
                  {...inlineEditProps("address", "Address")}
                  value={candidate.address}
                  multiline
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("address", value)}
                />
                <InlineField
                  label="Previous workplace"
                  {...inlineEditProps("previous_workplace", "Previous workplace")}
                  value={candidate.previous_workplace}
                  multiline
                  busy={mutation.isPending}
                  onSave={(value) =>
                    saveInlineField("previous_workplace", value)
                  }
                />
                <InlineField
                  label="Education background"
                  {...inlineEditProps(
                    "education_background",
                    "Education background",
                  )}
                  value={candidate.education_background}
                  multiline
                  busy={mutation.isPending}
                  onSave={(value) =>
                    saveInlineField("education_background", value)
                  }
                />
                <InlineField
                  label="Motivation"
                  {...inlineEditProps("motivation_expectations", "Motivation")}
                  value={candidate.motivation_expectations}
                  multiline
                  busy={mutation.isPending}
                  onSave={(value) =>
                    saveInlineField("motivation_expectations", value)
                  }
                />
                <InlineField
                  label="Work experience"
                  {...inlineEditProps("work_experience", "Work experience")}
                  value={candidate.work_experience}
                  multiline
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("work_experience", value)}
                />
                <InlineField
                  label="Teaching experience"
                  {...inlineEditProps("teaching_experience_option_id", "Teaching experience")}
                  value={candidate.teaching_experience_option_id}
                  displayValue={candidate.teaching_experience}
                  options={(options.data?.option_categories?.teaching_experience || []).map((item) => ({ value: item.id, label: item.label }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("teaching_experience_option_id", value)}
                />
                <InlineField
                  label="Interests"
                  {...inlineEditProps("interests_hobbies", "Interests")}
                  value={candidate.interests_hobbies}
                  multiline
                  busy={mutation.isPending}
                  onSave={(value) =>
                    saveInlineField("interests_hobbies", value)
                  }
                />
              </div>
            ) : (
              <>
                <DefinitionGrid
                  values={[
                    ["Phone", candidate.phone],
                    ["Subject", candidate.subject],
                    ["Telegram", candidate.telegram_username],
                    ["Application date", dateLabel(candidate.application_date)],
                    ["Source", candidate.source],
                    ["Subsource", candidate.subsource],
                    ["Age", candidate.age],
                    ["English", candidate.english_level],
                    ["Schedule", candidate.preferred_schedule],
                    ["Availability", candidate.employment_availability],
                    ["Start date", dateLabel(candidate.available_start_date)],
                    [
                      "Expected salary",
                      candidate.expected_salary_uzs
                        ? `${Number(candidate.expected_salary_uzs).toLocaleString()} UZS`
                        : "",
                    ],
                    ["Address", candidate.address],
                    ["Previous workplace", candidate.previous_workplace],
                    ["Education background", candidate.education_background],
                  ]}
                />
                <div className="mt-2">
                  <DefinitionGrid
                    values={[
                      ["Motivation", candidate.motivation_expectations],
                      ["Work experience", candidate.work_experience],
                      ["Teaching experience", candidate.teaching_experience],
                      ["Interests", candidate.interests_hobbies],
                    ]}
                  />
                </div>
              </>
            )}
          </Panel>
          <div className="space-y-3">
            <Panel
              title="Next action"
              icon={<CalendarClock className="h-4 w-4" />}
            >
              {candidate.next_appointment ? (
                <button
                  type="button"
                  className="w-full rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                  onClick={() => {
                    const next = candidate.next_appointment;
                    if (!next) return;
                    if (next.appointment_type === "job_interview") setInterviewSession(next);
                    else setTab("evaluations");
                  }}
                >
                  <p className="text-sm font-semibold">
                    {candidate.next_appointment.appointment_type ===
                    "job_interview"
                      ? "Job interview"
                      : "Demo lesson"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {dateTimeLabel(candidate.next_appointment.starts_at)}
                    {candidate.next_appointment.responsible_name
                      ? ` · ${candidate.next_appointment.responsible_name}`
                      : ""}
                  </p>
                </button>
              ) : candidate.next_task ? (
                <div>
                  <p className="text-sm font-semibold">
                    {candidate.next_task.title}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Due {dateLabel(candidate.next_task.due_at)}
                  </p>
                </div>
              ) : (
                <EmptyLine>No next action.</EmptyLine>
              )}
              {candidate.current_sla ? <div className={`mt-3 rounded-lg px-3 py-2 text-xs font-semibold ${candidate.current_sla.status === "red" ? "bg-red-50 text-red-700" : candidate.current_sla.status === "yellow" ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"}`}>{candidate.current_sla.status === "red" ? "SLA overdue" : `Stage SLA due ${dateLabel(candidate.current_sla.due_at)}`}</div> : null}
            </Panel>
            <Panel
              title="Recruitment progress"
              icon={<BriefcaseBusiness className="h-4 w-4" />}
            >
              <ol className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-1">{(candidate.progress || []).map((item) => <li key={item.key} className={`flex min-h-9 items-center gap-2 rounded-lg px-2.5 text-xs font-semibold ${item.status === "completed" ? "bg-emerald-50 text-emerald-800" : item.status === "current" ? "bg-amber-50 text-amber-800" : "bg-muted/50 text-muted-foreground"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${item.status === "completed" ? "bg-emerald-500" : item.status === "current" ? "bg-amber-500" : "bg-slate-300"}`} />{item.label}</li>)}</ol>
              {candidate.document_progress ? <p className="mt-3 text-xs text-muted-foreground">Required documents: <strong className="text-foreground">{candidate.document_progress.required_uploaded}/{candidate.document_progress.required_total}</strong> · Optional: {candidate.document_progress.optional_uploaded}/{candidate.document_progress.optional_total}</p> : null}
            </Panel>
          </div>
        </div>
      ) : null}

      {tab === "evaluations" ? (
        <div
          id="candidate-panel-evaluations"
          role="tabpanel"
          aria-labelledby="candidate-tab-evaluations"
          className="space-y-3"
        >
          <div className="grid gap-3 xl:grid-cols-3">
            <Panel
              title="Job Interviews"
              icon={<ClipboardCheck className="h-4 w-4" />}
            >
              <div className="mb-3 space-y-2">
                {scheduledAppointments.filter((item) => item.appointment_type === "job_interview").map((appointment) => <button key={appointment.id} type="button" onClick={() => setInterviewSession(appointment)} className={`flex min-h-14 w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${appointment.is_overdue ? "border-red-300 bg-red-50 text-red-800" : "border-amber-300 bg-amber-50 text-amber-900"}`}><span><strong className="block text-[13px]">{appointment.status === "in_progress" ? "Interview in progress" : appointment.is_overdue ? "Interview overdue" : "Scheduled interview"}</strong><span className="mt-0.5 block text-xs">{dateTimeLabel(appointment.starts_at)}</span></span><span className="text-xs font-semibold">{appointment.status === "in_progress" ? "Resume" : "Start"}</span></button>)}
              </div>
              <AttemptList
                items={candidate.interviews || []}
                empty="No interviews recorded."
                onVoid={
                  permissions?.can_void_evaluations &&
                  !["academic_director", "head_of_department"].includes(role)
                    ? (attempt) =>
                        setAction({
                          kind: "void_evaluation",
                          evaluationType: "interview",
                          attempt,
                        })
                    : undefined
                }
              />
            </Panel>
            <Panel
              title="Demo Lessons"
              icon={<ClipboardCheck className="h-4 w-4" />}
            >
              <div className="mb-3 space-y-2">
                {scheduledAppointments.filter((item) => item.appointment_type === "demo_lesson").map((appointment) => <button key={appointment.id} type="button" disabled={!permissions?.can_add_academic_evaluation} onClick={() => setAction({ kind: "record_demo", appointment })} className={`flex min-h-14 w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-default ${appointment.is_overdue ? "border-red-300 bg-red-50 text-red-800" : "border-amber-300 bg-amber-50 text-amber-900"}`}><span className="min-w-0"><strong className="block truncate text-[13px]">{appointment.is_overdue ? "Demo lesson overdue" : "Scheduled demo lesson"}</strong><span className="mt-0.5 block truncate text-xs">{dateTimeLabel(appointment.starts_at)}{appointment.responsible_name ? ` · ${appointment.responsible_name}` : ""}</span>{appointment.topic ? <span className="mt-0.5 block truncate text-xs">Topic: {appointment.topic}</span> : null}</span>{permissions?.can_add_academic_evaluation ? <span className="text-xs font-semibold">Evaluate</span> : null}</button>)}
              </div>
              <AttemptList
                items={candidate.demo_lessons || []}
                empty="No demo lessons recorded."
                onVoid={
                  permissions?.can_void_evaluations
                    ? (attempt) =>
                        setAction({
                          kind: "void_evaluation",
                          evaluationType: "demo",
                          attempt,
                        })
                    : undefined
                }
              />
            </Panel>
            <Panel
              title="Subject Knowledge Tests"
              icon={<ClipboardCheck className="h-4 w-4" />}
            >
              <AttemptList
                items={candidate.subject_tests || []}
                empty="No subject knowledge tests recorded."
                onVoid={
                  permissions?.can_void_evaluations
                    ? (attempt) =>
                        setAction({
                          kind: "void_evaluation",
                          evaluationType: "subject_test",
                          attempt,
                        })
                    : undefined
                }
              />
            </Panel>
          </div>
        </div>
      ) : null}

      {tab === "documents" ? (
        <div
          id="candidate-panel-documents"
          role="tabpanel"
          aria-labelledby="candidate-tab-documents"
        >
          <Panel
            title="Documents"
            icon={<FileText className="h-4 w-4" />}
            action={
              <span className="text-xs text-muted-foreground">
                Required: {candidate.document_progress?.required_uploaded || 0}/{candidate.document_progress?.required_total || 3}
              </span>
            }
          >
            <div className="divide-y divide-border rounded-lg border border-border">
              {(candidate.documents || []).map((document) => {
                const fileName = text(document.original_file_name) || "Candidate document";
                return (
                  <div
                    key={Number(document.id)}
                    className="flex min-h-14 items-center gap-1"
                  >
                    <a
                      href={`${RECRUITMENT_API}/candidates/${candidateId}/documents/${text(document.id)}/open`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex min-h-14 min-w-0 flex-1 items-center gap-3 rounded-md px-3 py-2 transition-colors hover:bg-muted/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
                      aria-label={`Open ${fileName}`}
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      <span className="min-w-0">
                        <span className="block truncate text-[13px] font-semibold text-foreground">{fileName}</span>
                        <span className="block text-xs text-muted-foreground">{humanize(document.document_type)} · v{text(document.version)}</span>
                      </span>
                    </a>
                    {role === "hr_manager" && permissions?.can_manage_documents ? (
                      <div className="flex shrink-0 items-center gap-1 pr-1">
                        <IconButton label={`Replace ${fileName}`} onClick={() => setAction({ kind: "upload_document", document })}>
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </IconButton>
                        <IconButton label={`Remove ${fileName}`} danger onClick={() => setRemoveDocument(document)}>
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </IconButton>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {!(candidate.documents || []).length ? (
              <EmptyLine>No documents uploaded.</EmptyLine>
            ) : null}
            <div className="mt-3 grid gap-2 sm:grid-cols-2"><p className="rounded-lg bg-muted/50 p-2 text-xs leading-5"><strong className="block text-foreground">Required documents</strong>{candidate.document_progress?.missing_required_types.length ? `Missing: ${candidate.document_progress.missing_required_types.map(humanize).join(", ")}` : "Complete"}</p><p className="rounded-lg bg-muted/50 p-2 text-xs leading-5"><strong className="block text-foreground">Optional documents</strong>{candidate.document_progress?.optional_uploaded || 0} of {candidate.document_progress?.optional_total || 0} uploaded</p></div>
            <p className="mt-2 text-xs text-muted-foreground">Document progress is informational and never blocks stage movement.</p>
          </Panel>
        </div>
      ) : null}

      {tab === "hiring" ? (
        <div
          id="candidate-panel-hiring"
          role="tabpanel"
          aria-labelledby="candidate-tab-hiring"
          className="space-y-3"
        >
          <Panel
            title="Under-review summary"
            icon={<ShieldCheck className="h-4 w-4" />}
          >
            <DefinitionGrid
              values={Object.entries(candidate.under_review || {}).map(
                ([key, value]) => [humanize(key), value],
              )}
            />
          </Panel>
          <div className="grid gap-3 xl:grid-cols-3">
            <Panel title="Assignments" icon={<UserRound className="h-4 w-4" />}>
              <div className="space-y-2">
                {(candidate.assignments || []).map((item) => (
                  <article
                    key={Number(item.id)}
                    className="rounded-lg border border-border p-3"
                  >
                    <p className="text-[13px] font-semibold">
                      {text(item.assignee_name)}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {humanize(item.assignee_role)}
                      {item.subject ? ` · ${text(item.subject)}` : ""}
                    </p>
                  </article>
                ))}
                {!(candidate.assignments || []).length ? (
                  <EmptyLine>No evaluators assigned.</EmptyLine>
                ) : null}
              </div>
            </Panel>
            <Panel
              title="Approval requests"
              icon={<ShieldCheck className="h-4 w-4" />}
            >
              <div className="space-y-2">
                {(candidate.approvals || []).map((item) => {
                  const reviewItems: ActionMenuItem[] =
                    !permissions?.can_review_approval
                      ? []
                      : item.status === "requested"
                        ? [
                            {
                              key: "approve",
                              label: "Approve & finalize",
                              onClick: () =>
                                setAction({
                                  kind: "review_approval",
                                  approval: item,
                                  status: "approved",
                                }),
                            },
                            {
                              key: "return",
                              label: "Return with comment",
                              onClick: () =>
                                setAction({
                                  kind: "review_approval",
                                  approval: item,
                                  status: "returned",
                                }),
                            },
                          ]
                        : item.status === "approved"
                          ? [
                              {
                                key: "finalize",
                                label: "Finalize approved request",
                                onClick: () =>
                                  setAction({
                                    kind: "review_approval",
                                    approval: item,
                                    status: "approved",
                                  }),
                              },
                            ]
                          : [];
                  return (
                    <article
                      key={Number(item.id)}
                      className="rounded-lg border border-border p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="text-[13px] font-semibold">
                            {stageLabels[text(item.requested_outcome)]}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {text(item.request_note || "No request note")}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <StatusBadge status={text(item.status)} />
                          {reviewItems.length ? (
                            <ActionMenu
                              items={reviewItems}
                              label={`Review approval ${text(item.id)}`}
                            />
                          ) : null}
                        </div>
                      </div>
                      {item.review_comment ? (
                        <p className="mt-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs text-muted-foreground">
                          Review: {text(item.review_comment)}
                          {item.reviewed_by
                            ? ` · ${text(item.reviewed_by)}`
                            : ""}
                        </p>
                      ) : null}
                    </article>
                  );
                })}
                {!(candidate.approvals || []).length ? (
                  <EmptyLine>No approval requests.</EmptyLine>
                ) : null}
              </div>
            </Panel>
            <Panel
              title="Final decisions"
              icon={<BriefcaseBusiness className="h-4 w-4" />}
            >
              <div className="space-y-2">
                {(candidate.decisions || []).map((item) => (
                  <article
                    key={Number(item.id)}
                    className={`rounded-lg border border-border p-3 ${item.voided_at ? "opacity-60" : ""}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[13px] font-semibold">
                        {stageLabels[text(item.decision)]}{item.voided_at ? " · Voided" : ""}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {dateLabel(item.created_at)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {humanize(item.rejection_reason) ||
                        text(item.reason_detail || "No reason")}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.decided_by ? `By ${text(item.decided_by)}` : "Recorded by system"}
                      {item.source_evaluation_type ? ` · ${humanize(item.source_evaluation_type)} evaluation #${text(item.source_evaluation_id)}` : ""}
                    </p>
                  </article>
                ))}
                {!(candidate.decisions || []).length ? (
                  <EmptyLine>No final decision.</EmptyLine>
                ) : null}
              </div>
            </Panel>
          </div>
          {pendingApprovals.length ? (
            <p className="text-xs text-muted-foreground">
              The Academic Director can approve and finalize the requested
              outcome or return it to HR.
            </p>
          ) : null}
          {approved.length ? (
            <p className="text-xs text-muted-foreground">
              Legacy approved requests remain available for finalization.
            </p>
          ) : null}
        </div>
      ) : null}

      {tab === "activity" ? (
        <div
          id="candidate-panel-activity"
          role="tabpanel"
          aria-labelledby="candidate-tab-activity"
          className="grid gap-3 xl:grid-cols-3"
        >
          <Panel title="Tasks" icon={<CalendarClock className="h-4 w-4" />}>
            <div className="space-y-2">
              {(candidate.tasks || []).map((task) => (
                <article
                  key={task.id}
                  className="flex min-h-14 items-center justify-between gap-3 rounded-lg border border-border p-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-semibold">
                      {task.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {dateLabel(task.due_at)}
                    </p>
                  </div>
                  <StatusBadge status={task.effective_status} />
                </article>
              ))}
              {!(candidate.tasks || []).length ? (
                <EmptyLine>No tasks.</EmptyLine>
              ) : null}
            </div>
          </Panel>
          <Panel title="Notes" icon={<MessageSquareText className="h-4 w-4" />}>
            <div className="space-y-2">
              {(candidate.notes || []).map((note) => (
                <article
                  key={Number(note.id)}
                  className="rounded-lg border border-border p-3"
                >
                  <p className="whitespace-pre-wrap text-[13px] leading-5">
                    {text(note.body)}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {text(note.author || "Unknown actor")} ·{" "}
                    {dateLabel(note.created_at)}
                  </p>
                </article>
              ))}
              {!(candidate.notes || []).length ? (
                <EmptyLine>No notes.</EmptyLine>
              ) : null}
            </div>
          </Panel>
          <Panel title="Timeline" icon={<Activity className="h-4 w-4" />}>
            <ol className="space-y-3">
              {(candidate.activity || []).map((item) => (
                <li
                  key={Number(item.id)}
                  className="border-l-2 border-primary/30 pl-3"
                >
                  <p className="text-[13px] font-semibold">
                    {humanize(item.event_type)}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {text(item.actor || "System")} ·{" "}
                    {dateLabel(item.created_at)}
                  </p>
                </li>
              ))}
              {!(candidate.activity || []).length ? (
                <EmptyLine>No activity yet.</EmptyLine>
              ) : null}
            </ol>
          </Panel>
        </div>
      ) : null}

      <Drawer
        open={Boolean(action && action.kind !== "record_demo")}
        onClose={() => {
          if (!mutation.isPending) {
            mutation.reset();
            setAction(null);
            setAppointmentConflicts([]);
          }
        }}
        title={actionTitle(action)}
        description={candidate.full_name}
        widthClass="sm:max-w-xl"
        footer={
          action && action.kind !== "record_demo" ? (
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className={secondaryButtonClass}
                disabled={mutation.isPending}
                onClick={() => {
                  mutation.reset();
                  setAction(null);
                  setAppointmentConflicts([]);
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                form={formId}
                className={buttonClass}
                disabled={
                  mutation.isPending ||
                  (action.kind === "upload_document" &&
                    !options.data?.document_upload_enabled)
                }
              >
                {mutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : null}
                {appointmentConflicts.length
                  ? "Schedule anyway"
                  : actionSubmitLabel(action)}
              </button>
            </div>
          ) : undefined
        }
      >
        {mutation.error ? (
          <div
            role="alert"
            className="mb-3 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          >
            {queryError(mutation.error)}
          </div>
        ) : null}
        {action && action.kind !== "record_demo" ? (
          <form id={formId} onSubmit={submitAction}>
            <ActionFields
              action={action}
              candidate={candidate}
              options={options.data}
              conflicts={appointmentConflicts}
            />
          </form>
        ) : null}
      </Drawer>

      <Modal
        open={action?.kind === "record_demo"}
        onClose={() => {
          if (!mutation.isPending) {
            mutation.reset();
            setAction(null);
          }
        }}
        title="Record demo lesson"
        subtitle={candidate.full_name}
        size="sm"
        mobileMode="sheet"
        closeOnEscape={!mutation.isPending}
        closeOnOutsideClick={!mutation.isPending}
      >
        <form id={`${formId}-demo`} onSubmit={submitAction}>
          <ModalBody>
            {mutation.error ? <div role="alert" className="mb-3 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">{queryError(mutation.error)}</div> : null}
            {action?.kind === "record_demo" ? <ActionFields action={action} candidate={candidate} options={options.data} conflicts={[]} /> : null}
          </ModalBody>
          <ModalFooter>
            <div className="flex flex-wrap justify-end gap-2">
              <button type="button" className={secondaryButtonClass} disabled={mutation.isPending} onClick={() => { mutation.reset(); setAction(null); }}>Cancel</button>
              <button type="submit" name="result" value="passed" className="flex min-h-11 items-center justify-center rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 disabled:opacity-60" disabled={mutation.isPending}>{mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}Pass</button>
              <button type="submit" name="result" value="failed" className="flex min-h-11 items-center justify-center rounded-lg bg-destructive px-4 text-sm font-semibold text-destructive-foreground transition-colors hover:bg-destructive/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/40 disabled:opacity-60" disabled={mutation.isPending}><X className="h-4 w-4" />Reject</button>
            </div>
          </ModalFooter>
        </form>
      </Modal>

      <Drawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        title="Candidate history"
        description="Read-only audit trail"
        widthClass="sm:max-w-md"
      >
        <ol className="space-y-3">
          {(candidate.stage_history || []).map((item) => (
            <li key={`stage-${item.id}`} className="border-l-2 border-emerald-400 pl-3"><p className="text-[13px] font-semibold">Entered {stageLabels[item.stage] || humanize(item.stage)}</p><p className="mt-0.5 text-xs text-muted-foreground">{item.responsible_name || "System"} · {dateLabel(item.entered_at)} · {humanize(item.transition_source)}</p>{item.comment ? <p className="mt-1 text-xs text-muted-foreground">{item.comment}</p> : null}</li>
          ))}
          {(candidate.activity || []).map((item) => (
            <li
              key={Number(item.id)}
              className="border-l-2 border-primary/30 pl-3"
            >
              <p className="text-[13px] font-semibold">
                {humanize(item.event_type)}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {text(item.actor || "System")} · {dateLabel(item.created_at)}
              </p>
            </li>
          ))}
          {!(candidate.activity || []).length && !(candidate.stage_history || []).length ? (
            <EmptyLine>No history yet.</EmptyLine>
          ) : null}
        </ol>
      </Drawer>

      {interviewSession ? (
        <InterviewSessionModal
          open
          candidate={candidate}
          appointment={interviewSession}
          onClose={() => setInterviewSession(null)}
          onAnnouncement={onAnnouncement}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(pendingInlineField || confirmInlineClose)}
        title="Discard unsaved change?"
        message={
          <>
            You changed <strong>{activeInlineField?.label}</strong>. {pendingInlineField ? <>Discard that change before editing <strong>{pendingInlineField.label}</strong>?</> : <>Discard that change and close the editor?</>}
          </>
        }
        confirmLabel="Discard & continue"
        cancelLabel="Keep editing"
        danger
        onCancel={() => {
          setPendingInlineField(null);
          setConfirmInlineClose(false);
          window.requestAnimationFrame(() => {
            if (activeInlineField) document.getElementById(`candidate-inline-${activeInlineField.id}`)?.focus();
          });
        }}
        onConfirm={() => {
          const next = pendingInlineField;
          setPendingInlineField(null);
          setConfirmInlineClose(false);
          setInlineFieldDirty(false);
          setActiveInlineField(next);
        }}
      />

      <ConfirmDialog
        open={Boolean(removeDocument)}
        title="Remove document?"
        message={
          <>
            The stored object for{" "}
            <strong>{text(removeDocument?.original_file_name)}</strong> will be
            deleted while its audit metadata remains.
          </>
        }
        confirmLabel="Remove"
        danger
        busy={mutation.isPending}
        onCancel={() => setRemoveDocument(null)}
        onConfirm={() => {
          if (removeDocument)
            mutation.mutate({
              url: `${RECRUITMENT_API}/candidates/${candidateId}/documents/${Number(removeDocument.id)}`,
              method: "DELETE",
            });
        }}
      />
    </div>
  );
}
