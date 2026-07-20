import {
  Activity,
  ArrowLeft,
  Ban,
  BriefcaseBusiness,
  CalendarClock,
  CalendarPlus,
  Check,
  ChevronDown,
  ClipboardCheck,
  FileText,
  GraduationCap,
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
  Fragment,
  useEffect,
  useId,
  useMemo,
  useState,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";

import { AppointmentForm } from "@/features/recruitment/AppointmentForm";
import { DemoSessionModal } from "@/features/recruitment/DemoSessionModal";
import { InterviewSessionModal } from "@/features/recruitment/InterviewSessionModal";
import {
  formValues,
  jsonBody,
  recruitmentRequest,
} from "@/features/recruitment/api";
import {
  academyTrainingRows,
  academyTrainingSummary,
  dateLabel,
  dateTimeLabel,
  humanize,
  stageLabels,
  type RecruitmentAppointment,
  type RecruitmentCandidate,
  type RecruitmentOptions,
  type AcademyTrainingRow,
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
  "overview" | "evaluations" | "documents" | "hiring" | "training" | "activity";
type ProfileAction =
  | { kind: "edit_profile" }
  | { kind: "upload_document"; document?: Record<string, unknown> }
  | { kind: "record_test" }
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
  | { kind: "place_teacher_academy" }
  | { kind: "reject_candidate" }
  | { kind: "record_outcome" }
  | {
      kind: "review_approval";
      approval: Record<string, unknown>;
      status: "approved" | "returned";
    }
  | { kind: "withdraw_candidate" }
  | {
      kind: "delete_evaluation";
      evaluationType: "interview" | "subject_test" | "demo";
      attempt: Record<string, unknown>;
    }
  | { kind: "add_task" }
  | { kind: "add_note" };

type MutationPayload = { message: string; candidate?: RecruitmentCandidate };
type InlineEditTarget = { id: string; label: string };
// Appointment actions open in a centered popup (same as the pipeline), not the
// action drawer.
const modalActionKinds = new Set<ProfileAction["kind"]>([
  "schedule_appointment",
  "reschedule_appointment",
  "appointment_status",
]);
const profileTabs: Array<{ key: ProfileTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "evaluations", label: "Evaluations" },
  { key: "documents", label: "Documents" },
  { key: "hiring", label: "Hiring" },
  { key: "activity", label: "Activity" },
];
// HR completes final placement from the Next action card. The Hiring tab stays
// available to approval reviewers through the full profileTabs set.
const hrProfileTabs = profileTabs.filter((item) => item.key !== "activity" && item.key !== "hiring");
const trainingProfileTab: { key: ProfileTab; label: string } = {
  key: "training",
  label: "Training",
};
const profileTabKeys = new Set<ProfileTab>([
  ...profileTabs.map((item) => item.key),
  trainingProfileTab.key,
]);

function text(value: unknown) {
  return String(value ?? "");
}

function subjectTestPaperTitle(candidate: RecruitmentCandidate) {
  let subject = text(candidate.subject).trim();
  if (!subject) {
    subject = text(candidate.applied_position)
      .replace(/\s+teachers?$/i, "")
      .trim();
  }
  subject ||= "Subject";
  if (!/^igcse\b/i.test(subject)) subject = `IGCSE ${subject}`;
  return `${subject} Paper Test`;
}

function Panel({
  title,
  icon,
  action,
  compact = false,
  children,
}: {
  title: string;
  icon: ReactNode;
  action?: ReactNode;
  compact?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card shadow-sm">
      <div className={`flex items-center justify-between gap-2 border-b border-border px-3 ${
        compact ? "min-h-9 flex-wrap py-1.5 sm:flex-nowrap" : "min-h-12 py-1.5"
      }`}>
        <h2 className="flex shrink-0 items-center gap-2 text-sm font-semibold text-foreground">
          {icon}
          {title}
        </h2>
        {action}
      </div>
      <div className={compact ? "p-2" : "p-3"}>{children}</div>
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
        className="h-16 w-full min-w-0 overflow-hidden rounded-lg bg-muted/45 px-3 py-1.5 text-left transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-wait"
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
                className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                aria-label={`Cancel editing ${label}`}
                title="Cancel"
              >
                <X className="h-4 w-4" />
              </button>
              <button
                type="submit"
                disabled={busy}
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-wait disabled:opacity-50"
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
  onDelete,
}: {
  items: Array<Record<string, unknown>>;
  empty: string;
  onDelete?: (item: Record<string, unknown>) => void;
}) {
  if (!items.length) return <EmptyLine>{empty}</EmptyLine>;
  return (
    <div className="space-y-2">
      {items.map((item) => {
        const isFailed = text(item.result).toLowerCase() === "failed";
        return (
          <article
            key={text(item.id)}
            className={`rounded-lg border p-3 ${isFailed ? "border-destructive/30 bg-destructive/5" : "border-border"}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <StatusBadge
                  status={text(item.result || "recorded")}
                />
                {isFailed ? (
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
                {onDelete ? (
                  <ActionMenu
                    items={[
                      {
                        key: "delete",
                        label: "Delete",
                        danger: true,
                        onClick: () => onDelete(item),
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
          </article>
        );
      })}
    </div>
  );
}

function SubjectTestList({
  items,
  onDelete,
}: {
  items: Array<Record<string, unknown>>;
  onDelete?: (item: Record<string, unknown>) => void;
}) {
  if (!items.length) return <EmptyLine>No subject knowledge tests recorded.</EmptyLine>;
  return (
    <div className="space-y-2">
      {items.map((item) => {
        const maximum = item.maximum_score == null ? Number.NaN : Number(item.maximum_score);
        const score = item.score == null ? Number.NaN : Number(item.score);
        const percentage = item.percentage == null ? Number.NaN : Number(item.percentage);
        const displayPercentage = Number.isFinite(percentage)
          ? percentage
          : Number.isFinite(score) && maximum > 0
            ? Math.round((score / maximum) * 1000) / 10
            : null;
        const paper = text(item.paper) || `${text(item.subject) || "Subject"} Paper Test`;
        return (
          <article
            key={text(item.id)}
            className={`rounded-lg border p-3 ${text(item.result).toLowerCase() === "failed" ? "border-destructive/30 bg-destructive/5" : "border-border"}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-[13px] font-semibold">{paper}</p>
                <p className="mt-1 flex items-center gap-2 text-xs font-semibold">
                  <span className="text-muted-foreground">Status:</span>
                  <StatusBadge status={text(item.result)} />
                </p>
              </div>
              <div className="flex shrink-0 items-start gap-1">
                <div className="text-right">
                  <strong className="block text-lg text-foreground">
                    {displayPercentage === null ? "—" : `${displayPercentage}%`}
                  </strong>
                <span className="text-xs text-muted-foreground">
                  {dateLabel(item.test_at || item.created_at)}
                </span>
                </div>
                {onDelete ? (
                  <ActionMenu
                    items={[{ key: "delete", label: "Delete", danger: true, onClick: () => onDelete(item) }]}
                    label="Subject test actions"
                  />
                ) : null}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function trainingLessonTitle(row: AcademyTrainingRow) {
  const number =
    text(row.lesson.lesson_number).trim() ||
    (row.lesson.sequence_no ? String(row.lesson.sequence_no) : "");
  const topic =
    text(row.lesson.lesson_topic).trim() ||
    text(row.assessment?.lesson_topic).trim();
  return {
    number: number
      ? /^lesson\b/i.test(number)
        ? number
        : `Lesson ${number}`
      : "Academy lesson",
    topic: topic || "Topic not recorded",
  };
}

function trainingEvaluationDate(row: AcademyTrainingRow) {
  return row.assessment?.assessment_datetime
    ? dateTimeLabel(row.assessment.assessment_datetime)
    : "Awaiting evaluation";
}

function academyDepartmentName(subject?: string, position?: string) {
  const value = `${text(subject)} ${text(position)}`.toLocaleLowerCase();
  if (value.includes("math")) return "Math";
  if (value.includes("chem")) return "Chemistry";
  if (value.includes("physics")) return "Physics";
  if (value.includes("biology")) return "Biology";
  if (value.includes("english") || value.includes("esl")) return "ESL";

  const cleaned = text(subject || position)
    .replace(/\bIGCSE\b/gi, "")
    .replace(/\bTeacher\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || "Subject";
}

function trainingEvaluator(
  row: AcademyTrainingRow,
  subject?: string,
  position?: string,
) {
  const recordedEvaluator =
    text(row.assessment?.evaluator_name).trim() ||
    text(row.lesson.evaluator_name).trim();
  const role = `Head Of ${academyDepartmentName(subject, position)} Department`;
  return {
    label: role,
    title: recordedEvaluator ? `${role} · ${recordedEvaluator}` : role,
  };
}

function trainingScore(value: number | null | undefined) {
  const score = Number(value);
  return Number.isFinite(score)
    ? new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(score)
    : "—";
}

const academyPassingDecisions = new Set([
  "passed",
  "ready_for_final_evaluation",
  "approved_for_active_teacher",
]);

const academySectionDetails = [
  ["starter", "Starter"],
  ["warmup", "Warm-up"],
  ["teaching_session_1", "Teaching session 1"],
  ["teaching_session_2", "Teaching session 2"],
  ["teaching_session_3", "Teaching session 3"],
  ["end_activity", "End activity"],
  ["homework", "Homework"],
] as const;

const academyCriterionDetails = [
  ["tgc", "teacher_guidance_compliance_score", "Teacher guidance compliance"],
  ["ta", "timing_adherence_score", "Timing adherence"],
  ["rf", "resource_familiarity_score", "Resource familiarity"],
  ["ef", "english_fluency_score", "English fluency"],
  ["con", "confidence_delivery_score", "Confidence & delivery"],
  ["se", "engagement_technique_score", "Student engagement"],
] as const;

function academyFeedback(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  return {};
}

function academyFeedbackEntry(
  feedback: Record<string, unknown>,
  key: string,
) {
  const value = feedback[key];
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function academyAssessmentPassed(row: AcademyTrainingRow) {
  return academyPassingDecisions.has(
    text(row.assessment?.decision).toLowerCase(),
  );
}

function AcademyAssessmentDetails({
  row,
}: {
  row: AcademyTrainingRow;
}) {
  const assessment = row.assessment;
  if (!assessment) return null;
  const feedback = academyFeedback(assessment.section_feedback);
  const criteriaFeedback = academyFeedback(feedback.marking_criteria);
  const sections = academySectionDetails
    .map(([key, label]) => {
      const entry = academyFeedbackEntry(feedback, key);
      const status = text(entry.status).trim();
      const timeUsed = text(entry.time_used).trim();
      const remarks = text(entry.remarks).trim();
      return { key, label, status, timeUsed, remarks };
    })
    .filter(
      (item) =>
        item.status &&
        item.status !== "not_applicable" ||
        item.timeUsed ||
        item.remarks,
    );
  const criteria = academyCriterionDetails
    .map(([key, scoreKey, label]) => {
      const entry = academyFeedbackEntry(criteriaFeedback, key);
      const rawScore =
        assessment[scoreKey] ??
        (entry.score === "" || entry.score === null ? null : entry.score);
      const score = Number(rawScore);
      return {
        key,
        label,
        score: Number.isFinite(score) ? score : null,
        remarks: text(entry.remarks).trim(),
      };
    })
    .filter((item) => item.score !== null || item.remarks);
  const notes = [
    ["Strengths", text(assessment.strengths).trim()],
    ["Improve next", text(assessment.areas_for_improvement).trim()],
    ["Recommendation", text(assessment.final_recommendation).trim()],
  ].filter((item) => item[1]);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-foreground">
          Full lesson evaluation
        </p>
        <p className="text-[11px] text-muted-foreground">
          {dateTimeLabel(assessment.assessment_datetime)}
          {assessment.class_label ? ` · ${assessment.class_label}` : ""}
        </p>
      </div>

      {sections.length ? (
        <section>
          <h4 className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Lesson areas
          </h4>
          <div className="mt-1.5 grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
            {sections.map((item) => (
              <div
                key={item.key}
                className="rounded-md border border-border bg-card px-2.5 py-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <strong className="text-xs text-foreground">{item.label}</strong>
                  <span className="shrink-0 text-[10px] font-semibold text-muted-foreground">
                    {[item.status ? humanize(item.status) : "", item.timeUsed]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </div>
                {item.remarks ? (
                  <p className="mt-1 whitespace-pre-wrap text-[11px] leading-4 text-muted-foreground">
                    {item.remarks}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {criteria.length ? (
        <section>
          <h4 className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Assessment criteria
          </h4>
          <div className="mt-1.5 grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
            {criteria.map((item) => (
              <div
                key={item.key}
                className="rounded-md border border-primary/10 bg-primary/5 px-2.5 py-1.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <strong className="text-xs text-foreground">{item.label}</strong>
                  <span className="shrink-0 text-xs font-bold tabular-nums text-primary">
                    {item.score === null ? "—" : trainingScore(item.score)}
                  </span>
                </div>
                {item.remarks ? (
                  <p className="mt-1 whitespace-pre-wrap text-[11px] leading-4 text-muted-foreground">
                    {item.remarks}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {notes.length ? (
        <dl className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
          {notes.map(([label, value]) => (
            <div key={label} className="rounded-md bg-muted/55 px-2.5 py-1.5">
              <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {label}
              </dt>
              <dd className="mt-1 whitespace-pre-wrap text-[11px] leading-4 text-foreground">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}

      {!sections.length && !criteria.length && !notes.length ? (
        <p className="rounded-md border border-dashed border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
          No detailed comments were recorded for this evaluation.
        </p>
      ) : null}
    </div>
  );
}

function TrainingPanel({
  rows,
  subject,
  position,
  startDate,
  promotionState,
  onPromote,
}: {
  rows: AcademyTrainingRow[];
  subject?: string;
  position?: string;
  startDate?: string | null;
  promotionState?: "available" | "requested" | "approved" | "returned";
  onPromote?: () => void;
}) {
  const [expandedLessonId, setExpandedLessonId] = useState<number | null>(null);
  const summary = academyTrainingSummary(rows);
  const progressPercentage = summary.completionPercentage;
  const lessonsLeft = Math.max(0, summary.assigned - summary.evaluated);
  const metrics = [
    {
      label: "Start date",
      value: startDate ? dateLabel(startDate) : "Not recorded",
      tone: "border-border bg-card",
      valueTone: "text-foreground",
    },
    {
      label: "Assigned",
      value: summary.assigned,
      tone: "border-border bg-card",
      valueTone: "text-foreground",
    },
    {
      label: "Passed",
      value: summary.passed,
      tone: "border-success/25 bg-success/10",
      valueTone: "text-success",
    },
    {
      label: "Failed",
      value: summary.failed,
      tone: "border-destructive/20 bg-destructive/10",
      valueTone: "text-destructive",
    },
    {
      label: "Avg score",
      value: summary.averageScore === null ? "—" : summary.averageScore,
      tone: "border-warning/30 bg-warning/15",
      valueTone: "text-warning",
    },
  ];

  return (
    <div
      id="candidate-panel-training"
      role="tabpanel"
      aria-labelledby="candidate-tab-training"
      className="space-y-2"
    >
      <div className={`grid grid-cols-2 gap-1.5 rounded-xl ${
        summary.isComplete ? "ring-2 ring-emerald-300/60" : ""
      } md:grid-cols-5`}>
        {metrics.map(({ label, value, tone, valueTone }) => (
          <section
            key={label}
            className={`min-w-0 rounded-lg border px-2.5 py-1.5 shadow-sm ${tone}`}
            aria-label={`${label}: ${value}`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {label}
            </p>
            <p
              className={`truncate text-base font-bold tabular-nums ${valueTone}`}
              title={String(value)}
            >
              {value}
            </p>
          </section>
        ))}
      </div>

      <Panel
        title="Academy training"
        icon={<GraduationCap className="h-4 w-4" />}
        compact
        action={
          <div className="flex w-full min-w-0 flex-1 items-center justify-end gap-2 sm:w-auto">
            <div
              className="min-w-32 max-w-5xl flex-1"
              aria-label={`${summary.evaluated} of ${summary.assigned} lessons covered, ${lessonsLeft} left`}
            >
              <div className="mb-0.5 flex items-center justify-between gap-2 text-[10px] font-semibold text-muted-foreground">
                <span>
                  {summary.isComplete ? "Teacher Academy completed" : `${summary.evaluated}/${summary.assigned} covered`}
                </span>
                <span>{lessonsLeft} left · {progressPercentage}%</span>
              </div>
              <div
                role="progressbar"
                aria-label="Academy training progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progressPercentage}
                className="h-2 overflow-hidden rounded-full bg-muted"
              >
                <div
                  className={`h-full rounded-full transition-[width] duration-200 motion-reduce:transition-none ${
                    summary.isComplete ? "bg-emerald-500" : "bg-primary"
                  }`}
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>
            {summary.canPromote && onPromote ? (
              <button
                type="button"
                onClick={onPromote}
                disabled={promotionState === "requested" || promotionState === "approved"}
                className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-lg bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <ShieldCheck className="h-4 w-4" />
                {promotionState === "requested"
                  ? "Requested"
                  : promotionState === "approved"
                    ? "Approved"
                    : promotionState === "returned"
                      ? "Resubmit"
                      : "Promote"}
              </button>
            ) : null}
          </div>
        }
      >
        {!rows.length ? (
          <EmptyLine>No Academy lessons assigned.</EmptyLine>
        ) : (
          <>
            <div className="hidden min-w-0 max-w-full overflow-x-auto overscroll-x-contain rounded-lg border border-border lg:block">
              <table className="w-full min-w-[60rem] table-fixed text-left">
                <caption className="sr-only">
                  Teacher Academy lesson delivery and latest evaluation details
                </caption>
                <thead className="bg-muted/60 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th scope="col" className="w-[31%] px-3 py-1.5">Assigned Topics</th>
                    <th scope="col" className="w-[19%] px-3 py-1.5">Evaluated Date</th>
                    <th scope="col" className="w-[20%] px-3 py-1.5">Evaluated By</th>
                    <th scope="col" className="w-[14%] px-3 py-1.5">Average Score</th>
                    <th scope="col" className="w-[16%] px-3 py-1.5">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rows.map((row) => {
                    const title = trainingLessonTitle(row);
                    const assessment = row.assessment;
                    const expanded = expandedLessonId === row.lesson.id;
                    const evaluator = trainingEvaluator(row, subject, position);
                    const result = academyAssessmentPassed(row) ? "Passed" : "Failed";
                    const toggleExpanded = () => {
                      if (!assessment) return;
                      setExpandedLessonId(expanded ? null : row.lesson.id);
                    };
                    return (
                      <Fragment key={row.lesson.id}>
                        <tr
                          role={assessment ? "button" : undefined}
                          tabIndex={assessment ? 0 : undefined}
                          aria-expanded={assessment ? expanded : undefined}
                          aria-controls={assessment ? `training-evaluation-${row.lesson.id}` : undefined}
                          onClick={toggleExpanded}
                          onKeyDown={(event: ReactKeyboardEvent<HTMLTableRowElement>) => {
                            if (assessment && (event.key === "Enter" || event.key === " ")) {
                              event.preventDefault();
                              toggleExpanded();
                            }
                          }}
                          className={`align-middle transition-colors motion-reduce:transition-none ${
                            assessment
                              ? "cursor-pointer hover:bg-muted/45 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
                              : ""
                          }`}
                        >
                          <th scope="row" className="px-3 py-1.5">
                            <span className="block truncate text-[13px] font-semibold text-foreground" title={title.number}>
                              {title.number}
                            </span>
                            <span className="mt-0.5 block truncate text-xs font-normal text-muted-foreground" title={title.topic}>
                              {title.topic}
                            </span>
                          </th>
                          <td className="px-3 py-1.5 text-xs">
                            <span className="block text-foreground">
                              {trainingEvaluationDate(row)}
                            </span>
                          </td>
                          <td className="truncate px-3 py-1.5 text-xs text-foreground" title={evaluator.title}>
                            {evaluator.label}
                          </td>
                          <td className="px-3 py-1.5">
                            {assessment ? (
                              <span className="text-[13px] font-semibold tabular-nums text-foreground">
                                {trainingScore(assessment.weighted_overall_score)}
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="px-3 py-1.5">
                            {assessment ? (
                              <span className="flex items-center justify-between gap-2">
                                <StatusBadge status={academyAssessmentPassed(row) ? "completed" : "failed"}>
                                  {result}
                                </StatusBadge>
                                <ChevronDown
                                  className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform motion-reduce:transition-none ${expanded ? "rotate-180" : ""}`}
                                  aria-hidden="true"
                                />
                              </span>
                            ) : (
                              <StatusBadge status="pending">Awaiting evaluation</StatusBadge>
                            )}
                          </td>
                        </tr>
                        {assessment && expanded ? (
                          <tr id={`training-evaluation-${row.lesson.id}`}>
                            <td colSpan={5} className="bg-muted/35 px-3 py-3">
                              <AcademyAssessmentDetails row={row} />
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="space-y-2 lg:hidden">
              {rows.map((row) => {
                const title = trainingLessonTitle(row);
                const assessment = row.assessment;
                const expanded = expandedLessonId === row.lesson.id;
                const evaluator = trainingEvaluator(row, subject, position);
                const result = academyAssessmentPassed(row) ? "Passed" : "Failed";
                const toggleExpanded = () => {
                  if (!assessment) return;
                  setExpandedLessonId(expanded ? null : row.lesson.id);
                };
                return (
                  <article
                    key={row.lesson.id}
                    role={assessment ? "button" : undefined}
                    tabIndex={assessment ? 0 : undefined}
                    aria-expanded={assessment ? expanded : undefined}
                    aria-controls={assessment ? `training-card-evaluation-${row.lesson.id}` : undefined}
                    onClick={toggleExpanded}
                    onKeyDown={(event: ReactKeyboardEvent<HTMLElement>) => {
                      if (assessment && (event.key === "Enter" || event.key === " ")) {
                        event.preventDefault();
                        toggleExpanded();
                      }
                    }}
                    className={`min-w-0 rounded-lg border border-border bg-card p-3 transition-colors motion-reduce:transition-none ${
                      assessment
                        ? "cursor-pointer hover:bg-muted/35 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                        : ""
                    }`}
                  >
                    <div className="flex min-w-0 items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold" title={title.number}>
                          {title.number}
                        </h3>
                        <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-muted-foreground">
                          {title.topic}
                        </p>
                      </div>
                      <StatusBadge status={assessment ? (academyAssessmentPassed(row) ? "completed" : "failed") : "pending"}>
                        {assessment ? result : "Awaiting evaluation"}
                      </StatusBadge>
                    </div>
                    <dl className="mt-3 grid min-w-0 grid-cols-2 gap-2 text-xs">
                      <div className="min-w-0 rounded-md bg-muted/45 px-2.5 py-1.5">
                        <dt className="font-semibold text-muted-foreground">Evaluated date</dt>
                        <dd className="mt-0.5 text-foreground">{trainingEvaluationDate(row)}</dd>
                      </div>
                      <div className="min-w-0 rounded-md bg-muted/45 px-2.5 py-1.5">
                        <dt className="font-semibold text-muted-foreground">Evaluated by</dt>
                        <dd className="mt-0.5 truncate text-foreground" title={evaluator.title}>{evaluator.label}</dd>
                      </div>
                    </dl>
                    {assessment ? (
                      <div className="mt-2 flex min-h-9 w-full items-center justify-between gap-2 rounded-md border border-border px-3">
                        <span className="text-xs">
                          <strong className="mr-2 tabular-nums text-foreground">
                            {trainingScore(assessment.weighted_overall_score)}
                          </strong>
                          <span className={academyAssessmentPassed(row) ? "text-success" : "text-destructive"}>{result}</span>
                        </span>
                        <ChevronDown
                          className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform motion-reduce:transition-none ${expanded ? "rotate-180" : ""}`}
                          aria-hidden="true"
                        />
                      </div>
                    ) : (
                      <div className="mt-2 flex min-h-9 items-center">
                        <StatusBadge status="pending">
                          Awaiting evaluation
                        </StatusBadge>
                      </div>
                    )}
                    {assessment && expanded ? (
                      <div
                        id={`training-card-evaluation-${row.lesson.id}`}
                        className="mt-2 rounded-md bg-muted/45 px-3 py-1.5"
                      >
                        <AcademyAssessmentDetails row={row} />
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </>
        )}
      </Panel>
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
    ? ["active_teacher"]
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
}: {
  action: ProfileAction;
  candidate: RecruitmentCandidate;
  options?: RecruitmentOptions;
}) {
  switch (action.kind) {
    case "edit_profile":
      return (
        <div className="grid gap-2 sm:grid-cols-2">
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
            <select name="position_option_id" defaultValue={candidate.position_option_id || ""} className={`${fieldClass} mt-1`}>
              <option value="">Not set</option>
              {options?.option_categories.position?.map((position) => <option key={position.id} value={position.id}>{position.label}</option>)}
            </select>
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
    case "upload_document":
      return (
        <div className="grid gap-2">
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
    case "record_test":
      return (
        <div className="grid gap-2">
          <div className="rounded-lg bg-muted/60 px-3 py-1.5">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Subject test
            </span>
            <strong className="mt-0.5 block text-sm">
              {subjectTestPaperTitle(candidate)}
            </strong>
          </div>
          <label className="text-xs font-semibold">
            Percentage
            <div className="relative mt-1">
              <input
                autoFocus
                required
                name="percentage"
                type="number"
                min="0"
                max="100"
                step="0.1"
                inputMode="decimal"
                className={`${fieldClass} pr-10`}
              />
              <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm font-semibold text-muted-foreground">%</span>
            </div>
          </label>
          <label className="text-xs font-semibold">
            Status
            <select required name="result" className={`${fieldClass} mt-1`}>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
            </select>
          </label>
        </div>
      );
    case "schedule_appointment":
      return (
        <AppointmentForm
          appointmentType={action.appointmentType}
          options={options}
        />
      );
    case "reschedule_appointment":
      return (
        <AppointmentForm
          appointmentType={action.appointment.appointment_type}
          appointment={action.appointment}
          options={options}
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
                className="flex min-h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm"
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
        <div className="grid gap-2">
          <input type="hidden" name="requested_outcome" value="active_teacher" />
          <p className="rounded-lg bg-muted/50 p-3 text-sm">
            Request Academic Director permission to place this candidate in
            Active Teachers. Academic approval records permission; CEO
            finalization remains a future step.
          </p>
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
    case "place_teacher_academy":
      return (
        <p className="rounded-lg border border-primary/25 bg-primary/5 p-3 text-sm">
          Add <strong>{candidate.full_name}</strong> directly to Teacher
          Academy? Academic Director approval is not required.
        </p>
      );
    case "reject_candidate":
      return (
        <div className="grid gap-2">
          <label className="text-xs font-semibold">
            Rejection reason
            <select autoFocus required name="rejection_reason" className={`${fieldClass} mt-1`}>
              <option value="">Select a reason</option>
              {(options?.rejection_reason_options || []).map((reason) => (
                <option key={reason.value} value={reason.value}>{reason.label}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold">
            Explanation
            <textarea name="reason_detail" className={`${fieldClass} mt-1 min-h-24`} />
          </label>
        </div>
      );
    case "record_outcome":
      return (
        <div className="grid gap-2">
          <OutcomeFields candidate={candidate} options={options} />
        </div>
      );
    case "review_approval":
      return (
        <div className="grid gap-2">
          <p className="rounded-lg bg-muted/50 p-3 text-sm">
            {action.status === "approved"
              ? `${stageLabels[text(action.approval.requested_outcome)]} will be approved for future CEO finalization. The candidate will not be activated yet.`
              : `${stageLabels[text(action.approval.requested_outcome)]} approval will be returned to HR.`}
          </p>
          <label className="text-xs font-semibold">
            Comment
            <textarea
              name="review_comment"
              required={action.status === "returned"}
              defaultValue={
                action.status === "approved"
                  ? "Approved by Academic Director for CEO review."
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
    case "delete_evaluation":
      return (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          This evaluation and its linked schedule entry will be permanently
          deleted. The candidate workflow will be recalculated.
        </p>
      );
    case "add_task":
      return (
        <div className="grid gap-2">
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
    case "upload_document":
      return action.document ? "Replace document" : "Upload document";
    case "record_test":
      return "Record subject test";
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
    case "place_teacher_academy":
      return "Add to Teacher Academy";
    case "reject_candidate":
      return "Reject candidate";
    case "record_outcome":
      return "Record outcome";
    case "review_approval":
      return action.status === "approved"
        ? "Approve Active Teacher request"
        : "Return request";
    case "withdraw_candidate":
      return "Candidate withdrew";
    case "delete_evaluation":
      return "Delete evaluation";
    case "add_task":
      return "Add task";
    case "add_note":
      return "Add note";
  }
}

function actionSubmitLabel(action: ProfileAction | null) {
  if (!action) return "Save";
  if (action.kind === "schedule_appointment") return "Schedule appointment";
  if (action.kind === "reschedule_appointment") return "Save appointment";
  if (action.kind === "appointment_status")
    return action.status === "cancelled"
      ? "Cancel appointment"
      : "Mark no-show";
  if (action.kind === "review_approval")
    return action.status === "approved"
      ? "Approve request"
      : "Return request";
  if (action.kind === "upload_document")
    return action.document ? "Replace" : "Upload";
  if (action.kind === "reject_candidate") return "Reject candidate";
  if (action.kind === "place_teacher_academy") return "Proceed";
  if (action.kind === "delete_evaluation") return "Delete";
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
  const requestedTab =
    new URLSearchParams(window.location.search).get("tab") || "overview";
  const [tab, setTab] = useState<ProfileTab>(
    profileTabKeys.has(requestedTab as ProfileTab)
      ? (requestedTab as ProfileTab)
      : "overview",
  );
  const [action, setAction] = useState<ProfileAction | null>(null);
  const [interviewSession, setInterviewSession] = useState<RecruitmentAppointment | null>(null);
  const [demoSession, setDemoSession] = useState<RecruitmentAppointment | null>(null);
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
  const visibleProfileTabs = useMemo(
    () =>
      role === "hr_manager"
        ? detail.data?.academy
          ? [...hrProfileTabs, trainingProfileTab]
          : hrProfileTabs
        : profileTabs,
    [detail.data?.academy, role],
  );
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
      setRemoveDocument(null);
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
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

  useEffect(() => {
    if (
      detail.isLoading ||
      visibleProfileTabs.some((item) => item.key === tab)
    ) {
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set("tab", "overview");
    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
    setTab("overview");
  }, [detail.isLoading, tab, visibleProfileTabs]);

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
  const activeTeacherPromotionRequest = (candidate.approvals || []).find(
    (item) =>
      text(item.requested_outcome) === "active_teacher" &&
      ["requested", "approved", "returned"].includes(text(item.status)),
  );
  const latestInterview = candidate.interviews?.find((item) => !item.voided_at);
  const latestTest = candidate.subject_tests?.find((item) => !item.voided_at);
  const latestDemo = candidate.demo_lessons?.find((item) => !item.voided_at);
  const scheduledAppointments = (candidate.appointments || []).filter(
    (item) => ["scheduled", "in_progress"].includes(item.status),
  );
  const canManageAppointments = Boolean(permissions?.can_manage_appointments);
  const hasScheduledInterview = scheduledAppointments.some((item) => item.appointment_type === "job_interview");
  const hasScheduledDemo = scheduledAppointments.some((item) => item.appointment_type === "demo_lesson");
  // Evaluations unlock one by one: interview -> demo lesson -> subject test.
  const interviewPassed = candidate.evaluation_states?.interview === "passed";
  const demoPassed = candidate.evaluation_states?.demo === "passed";
  const subjectTestPassed =
    candidate.evaluation_states?.subject_test === "passed";
  const allRequiredPassed =
    interviewPassed && demoPassed && subjectTestPassed;
  const academySupplement = candidate.status === "teacher_academy";
  const canScheduleInterview =
    canManageAppointments &&
    ["responded", "job_interview", "test_and_demo", "teacher_academy"].includes(candidate.status) &&
    (academySupplement || !interviewPassed) &&
    !hasScheduledInterview;
  const canScheduleDemo =
    canManageAppointments &&
    ["job_interview", "test_and_demo", "teacher_academy"].includes(candidate.status) &&
    (academySupplement || interviewPassed) &&
    (academySupplement || !demoPassed) &&
    !hasScheduledDemo;
  const canRecordSubjectTest =
    Boolean(permissions?.can_add_subject_test) &&
    demoPassed &&
    !subjectTestPassed;
  const openReschedule = (appointment: RecruitmentAppointment) => {
    setAction({ kind: "reschedule_appointment", appointment });
  };
  const appointmentActionMenu = (appointment: RecruitmentAppointment) =>
    canManageAppointments ? (
      <ActionMenu
        label="Appointment actions"
        items={[
          { key: "reschedule", label: "Reschedule", onClick: () => openReschedule(appointment) },
          { key: "cancel", label: "Cancel appointment", danger: true, onClick: () => setAction({ kind: "appointment_status", appointment, status: "cancelled" }) },
        ]}
      />
    ) : null;
  const scheduleHeaderButton = (appointmentType: "job_interview" | "demo_lesson") => (
    <button
      type="button"
      className={secondaryButtonClass}
      onClick={() => setAction({ kind: "schedule_appointment", appointmentType })}
    >
      <CalendarPlus className="h-4 w-4" />
      <span className="hidden sm:inline">Schedule</span>
    </button>
  );
  const pendingTasks = (candidate.tasks || []).filter((task) =>
    ["pending", "overdue"].includes(task.effective_status),
  );
  const trainingRows = academyTrainingRows(
    candidate.academy?.lessons,
    candidate.academy?.assessments,
  );

  const saveInlineField = (
    field: keyof RecruitmentCandidate,
    rawValue: string,
  ) => {
    let value: string | number | null = rawValue.trim() || null;
    if (["age", "expected_salary_uzs", "subject_id", "position_option_id", "source_option_id", "subsource_option_id", "english_level_option_id", "schedule_option_id", "availability_option_id", "expected_salary_option_id", "teaching_experience_option_id"].includes(field) && value !== null)
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
    const form = event.currentTarget;
    if (action.kind === "upload_document") {
      mutation.mutate({
        url: `${RECRUITMENT_API}/candidates/${candidateId}/documents`,
        method: "POST",
        formData: new FormData(form),
      });
    } else if (action.kind === "edit_profile") {
      submit("", formValues(form), "PATCH");
    } else if (action.kind === "record_test") {
      const values = formValues(form);
      const percentage = Number(values.percentage);
      if (!Number.isFinite(percentage) || percentage < 0 || percentage > 100)
        return;
      submit("/subject-tests", {
        result: values.result,
        subject_id: candidate.subject_id || null,
        subject_label: candidate.subject || "",
        paper: subjectTestPaperTitle(candidate),
        score: percentage,
        maximum_score: 100,
        topic_scores: [],
        notes: "",
      });
    } else if (action.kind === "schedule_appointment") {
      submit("/appointments", {
        ...formValues(form),
        appointment_type: action.appointmentType,
      });
    } else if (action.kind === "reschedule_appointment") {
      submit(
        `/appointments/${action.appointment.id}`,
        {
          ...formValues(form),
          expected_version: action.appointment.version,
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
    } else if (action.kind === "place_teacher_academy") {
      submit("/final-decisions", {
        decision: "teacher_academy",
        reason_detail: "Placed in Teacher Academy by HR.",
      });
    } else if (action.kind === "reject_candidate") {
      submit("/final-decisions", {
        decision: "rejected",
        ...formValues(form),
      });
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
    } else if (action.kind === "delete_evaluation") {
      const segment =
        action.evaluationType === "interview"
          ? "interviews"
          : action.evaluationType === "subject_test"
            ? "subject-tests"
            : "demo-lessons";
      submit(`/${segment}/${Number(action.attempt.id)}`, {}, "DELETE");
    } else if (action.kind === "add_task") {
      submit("/tasks", formValues(form));
    } else if (action.kind === "add_note") {
      submit("/notes", formValues(form));
    }
  };

  const evaluationItems: ActionMenuItem[] = [];
  if (canScheduleInterview)
    evaluationItems.push({
      key: "schedule_interview",
      label: "Schedule interview",
      onClick: () => {
        setAction({
          kind: "schedule_appointment",
          appointmentType: "job_interview",
        });
      },
    });
  if (canScheduleDemo)
    evaluationItems.push({
      key: "schedule_demo",
      label: "Schedule demo lesson",
      onClick: () => {
        setAction({
          kind: "schedule_appointment",
          appointmentType: "demo_lesson",
        });
      },
    });
  if (permissions?.can_add_academic_evaluation) {
    const scheduledDemo = scheduledAppointments.find(
      (item) => item.appointment_type === "demo_lesson",
    );
    if (scheduledDemo) evaluationItems.push({
      key: "demo",
      label: scheduledDemo.status === "in_progress" ? "Resume demo lesson" : "Start demo lesson",
      onClick: () => setDemoSession(scheduledDemo),
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
    role === "ceo" &&
    candidate.status === "under_review" &&
    allRequiredPassed &&
    permissions?.can_finalize
  )
    hiringItems.push({
      key: "outcome",
      label: "Record outcome",
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
    role === "hr_manager" &&
    permissions?.can_reject &&
    ![
      "candidate_withdrew",
      "rejected",
      "trash_bin",
      "teacher_academy",
      "active_teacher",
    ].includes(candidate.status)
  ) {
    overviewItems.push({
      key: "reject",
      label: "Reject",
      danger: true,
      onClick: () => setAction({ kind: "reject_candidate" }),
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
      label: "Candidate Withdraw",
      onClick: () => setAction({ kind: "withdraw_candidate" }),
    });
  }
  if (role === "hr_manager")
    overviewItems.push({
      key: "history",
      label: "View History",
      onClick: () => setHistoryOpen(true),
    });

  const returnedApproval = (candidate.approvals || []).find(
    (item) => item.status === "returned",
  );
  const hrHiringAction = null;

  const tabAction =
    tab === "evaluations" && evaluationItems.length ? (
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
  const candidateMenu = overviewItems.length ? (
    <ActionMenu items={overviewItems} label="Candidate actions" />
  ) : null;

  // A single, unambiguous "do this next" CTA derived from the candidate's real
  // state so HR always knows the exact step to complete.
  const nextStep: { label: string; sublabel: string; onClick: () => void } | null = (() => {
    const appt = candidate.next_appointment;
    if (appt) {
      const canConduct =
        appt.appointment_type === "job_interview"
          ? role === "hr_manager"
          : Boolean(permissions?.can_add_academic_evaluation);
      return {
        label: canConduct
          ? appt.appointment_type === "job_interview"
            ? "Start interview"
            : "Open demo lesson"
          : appt.appointment_type === "job_interview"
            ? "Interview scheduled"
            : "Demo lesson scheduled",
        sublabel: `${dateTimeLabel(appt.starts_at)}${appt.responsible_name ? ` · ${appt.responsible_name}` : ""}`,
        onClick: () => {
          if (!canConduct) {
            setProfileTab("evaluations");
          } else if (appt.appointment_type === "job_interview") {
            setInterviewSession(appt);
          } else {
            setDemoSession(appt);
          }
        },
      };
    }
    // Sequential flow: interview -> demo lesson -> subject test.
    if (canScheduleInterview) {
      return { label: "Schedule job interview", sublabel: candidate.evaluation_states?.interview === "missing" ? "No interview recorded" : "No interview scheduled yet", onClick: () => setAction({ kind: "schedule_appointment", appointmentType: "job_interview" }) };
    }
    if (canScheduleDemo) {
      return { label: "Schedule demo lesson", sublabel: "No demo scheduled yet", onClick: () => setAction({ kind: "schedule_appointment", appointmentType: "demo_lesson" }) };
    }
    if (candidate.status === "test_and_demo" && canRecordSubjectTest) {
      return { label: "Record subject test", sublabel: "Subject test pending", onClick: () => { setProfileTab("evaluations"); setAction({ kind: "record_test" }); } };
    }
    if (candidate.next_task) {
      return { label: candidate.next_task.title, sublabel: `Due ${dateLabel(candidate.next_task.due_at)}`, onClick: () => setProfileTab("evaluations") };
    }
    return null;
  })();
  const finalPlacementButtons =
    role === "hr_manager" &&
    candidate.status === "under_review" &&
    allRequiredPassed ? (
      <div className="grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          className={`${buttonClass} w-full justify-center`}
          onClick={() => setAction({ kind: "place_teacher_academy" })}
        >
          <GraduationCap className="h-4 w-4" />
          Teacher Academy
        </button>
        {permissions?.can_request_approval ? (
          <button
            type="button"
            className={`${secondaryButtonClass} w-full justify-center`}
            onClick={() =>
              setAction({
                kind: "request_approval",
                previous: returnedApproval,
              })
            }
          >
            <UserRound className="h-4 w-4" />
            Active Teachers
          </button>
        ) : null}
      </div>
    ) : null;

  return (
    <div className="space-y-2">
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
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
            aria-label={`Back to ${backLabel}`}
            title={`Back to ${backLabel}`}
          >
            <ArrowLeft className="h-4 w-4" />
          </a>
          <div className="min-w-0 flex-1 py-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="min-w-0 break-words text-lg font-bold tracking-tight sm:text-xl">
                {candidate.full_name}
              </h1>
              <StatusBadge status={candidate.status}>
                {stageLabels[candidate.status] || humanize(candidate.status)}
              </StatusBadge>
            </div>
            <p className="mt-0.5 break-words text-xs text-muted-foreground">
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
          <div className="flex max-w-full shrink-0 flex-wrap items-center justify-end gap-1">
            {tabAction}
            {candidateMenu}
          </div>
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
              className={`min-h-9 rounded-lg px-3 text-[13px] font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${tab === item.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
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
          className="grid gap-2 xl:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]"
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
                  {...inlineEditProps("position_option_id", "Position")}
                  value={candidate.position_option_id}
                  displayValue={candidate.applied_position}
                  options={(options.data?.option_categories.position || []).map((item) => ({ value: String(item.id), label: item.label }))}
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("position_option_id", value)}
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
                  label="Email"
                  {...inlineEditProps("email", "Email")}
                  value={candidate.email}
                  type="email"
                  busy={mutation.isPending}
                  onSave={(value) => saveInlineField("email", value)}
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
                    ["Email", candidate.email],
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
          <div className="space-y-2">
            {candidate.academy ? (
              <Panel
                title="Teacher Academy"
                icon={<GraduationCap className="h-4 w-4" />}
              >
                <DefinitionGrid
                  values={[
                    ["Status", humanize(candidate.academy.status || "not_set")],
                    ["Subject", candidate.academy.subject],
                  ]}
                />
                {candidate.profile_origin === "academy_direct" ? (
                  <p className="mt-2 rounded-lg bg-muted px-3 py-1.5 text-xs text-muted-foreground">
                    Created directly from Teacher Academy. No application history has been generated.
                  </p>
                ) : null}
              </Panel>
            ) : null}
            <Panel
              title="Next action"
              icon={<CalendarClock className="h-4 w-4" />}
              action={
                candidate.current_sla ? (
                  <span
                    className={`max-w-[12rem] rounded-md px-2 py-1 text-right text-[11px] font-semibold leading-tight ${
                      candidate.current_sla.status === "red"
                        ? "bg-red-50 text-red-700"
                        : candidate.current_sla.status === "yellow"
                          ? "bg-amber-50 text-amber-800"
                          : "bg-emerald-50 text-emerald-800"
                    }`}
                  >
                    {candidate.current_sla.status === "red"
                      ? "SLA overdue"
                      : `SLA due ${dateLabel(candidate.current_sla.due_at)}`}
                  </span>
                ) : undefined
              }
            >
              {finalPlacementButtons || (nextStep ? (
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-left transition-colors hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                  onClick={nextStep.onClick}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-primary">{nextStep.label}</span>
                    <span className="mt-0.5 block truncate text-xs text-muted-foreground">{nextStep.sublabel}</span>
                  </span>
                  <ChevronDown className="h-4 w-4 shrink-0 -rotate-90 text-primary" aria-hidden="true" />
                </button>
              ) : (
                <EmptyLine>No next action.</EmptyLine>
              ))}
            </Panel>
            <Panel
              title="Recruitment progress"
              icon={<BriefcaseBusiness className="h-4 w-4" />}
            >
              <ol className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-1">{(candidate.progress || []).map((item) => {
                const subjectWarning = candidate.status === "under_review" && item.key === "subject_test" && candidate.evaluation_states?.subject_test !== "passed";
                return <li key={item.key} className={`flex min-h-9 items-center gap-2 rounded-lg px-2.5 text-xs font-semibold ${subjectWarning ? "bg-red-50 text-red-700" : item.status === "completed" ? "bg-emerald-50 text-emerald-800" : item.status === "current" ? "bg-amber-50 text-amber-800" : "bg-muted/50 text-muted-foreground"}`}><span aria-hidden="true" className={`h-2 w-2 rounded-full ${subjectWarning ? "bg-red-500" : item.status === "completed" ? "bg-emerald-500" : item.status === "current" ? "bg-amber-500" : "bg-slate-300"}`} />{subjectWarning ? "Subject test missing/not passed" : item.label}</li>;
              })}</ol>
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
          className="space-y-2"
        >
          <div className="grid gap-2 xl:grid-cols-3">
            <Panel
              title="Job Interviews"
              icon={<ClipboardCheck className="h-4 w-4" />}
              action={canScheduleInterview ? scheduleHeaderButton("job_interview") : undefined}
            >
              <div className="mb-3 space-y-2">
                {scheduledAppointments.filter((item) => item.appointment_type === "job_interview").map((appointment) => (
                  <div key={appointment.id} className="flex items-center gap-1.5">
                    <button type="button" onClick={() => setInterviewSession(appointment)} className={`flex min-h-14 min-w-0 flex-1 items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${appointment.is_overdue ? "border-amber-300 bg-amber-50 text-amber-900" : appointment.status === "in_progress" ? "border-violet-300 bg-violet-50 text-violet-900" : "border-blue-300 bg-blue-50 text-blue-900"}`}><span className="min-w-0"><strong className="block break-words text-[13px]">{appointment.status === "in_progress" ? "Interview in progress" : appointment.is_overdue ? "Interview overdue" : "Scheduled interview"}</strong><span className="mt-0.5 block break-words text-xs">{dateTimeLabel(appointment.starts_at)}</span></span><span className="shrink-0 text-xs font-semibold">{appointment.status === "in_progress" ? "Resume" : "Start"}</span></button>
                    {appointmentActionMenu(appointment)}
                  </div>
                ))}
              </div>
              {candidate.evaluation_states?.interview === "missing" && !hasScheduledInterview && !(candidate.interviews || []).length ? (
                <p className="mb-3 flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200">
                  <Ban className="h-4 w-4 shrink-0" />No interview recorded for this candidate.
                </p>
              ) : null}
              <AttemptList
                items={candidate.interviews || []}
                empty="No interviews recorded."
                onDelete={
                  permissions?.can_delete_evaluations &&
                  !["academic_director", "head_of_department"].includes(role)
                    ? (attempt) =>
                        setAction({
                          kind: "delete_evaluation",
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
              action={canScheduleDemo ? scheduleHeaderButton("demo_lesson") : undefined}
            >
              <div className="mb-3 space-y-2">
                {scheduledAppointments.filter((item) => item.appointment_type === "demo_lesson").map((appointment) => (
                  <div key={appointment.id} className="flex items-center gap-1.5">
                    <button type="button" disabled={!permissions?.can_add_academic_evaluation} onClick={() => setDemoSession(appointment)} className={`flex min-h-14 flex-1 items-center justify-between gap-2 rounded-lg border px-3 py-1.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-default ${appointment.is_overdue ? "border-amber-300 bg-amber-50 text-amber-900" : "border-blue-300 bg-blue-50 text-blue-900"}`}><span className="min-w-0"><strong className="block break-words text-[13px]">{appointment.status === "in_progress" ? "Demo lesson in progress" : appointment.is_overdue ? "Demo lesson overdue" : "Scheduled demo lesson"}</strong><span className="mt-0.5 block break-words text-xs">{dateTimeLabel(appointment.starts_at)}{appointment.responsible_name ? ` · ${appointment.responsible_name}` : ""}</span>{appointment.topic ? <span className="mt-0.5 block break-words text-xs">Topic: {appointment.topic}</span> : null}</span>{permissions?.can_add_academic_evaluation ? <span className="text-xs font-semibold">{appointment.status === "in_progress" ? "Resume" : "Start"}</span> : null}</button>
                    {appointmentActionMenu(appointment)}
                  </div>
                ))}
              </div>
              {candidate.evaluation_states?.demo === "missing" && !hasScheduledDemo && !(candidate.demo_lessons || []).length ? (
                <p className="mb-3 flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-200">
                  <Ban className="h-4 w-4 shrink-0" />No demo lesson recorded for this candidate.
                </p>
              ) : null}
              <AttemptList
                items={candidate.demo_lessons || []}
                empty="No demo lessons recorded."
                onDelete={
                  permissions?.can_delete_evaluations
                    ? (attempt) =>
                        setAction({
                          kind: "delete_evaluation",
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
              {canRecordSubjectTest ? (
                <button
                  type="button"
                  onClick={() => setAction({ kind: "record_test" })}
                  className="mb-3 inline-flex min-h-9 w-full items-center justify-center rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  Record subject test
                </button>
              ) : permissions?.can_add_subject_test && !demoPassed ? (
                <p className="mb-3 rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
                  Available after the demo lesson is passed.
                </p>
              ) : null}
              <SubjectTestList
                items={candidate.subject_tests || []}
                onDelete={
                  permissions?.can_delete_evaluations
                    ? (attempt) =>
                        setAction({
                          kind: "delete_evaluation",
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
                      className="flex min-h-14 min-w-0 flex-1 items-center gap-2 rounded-md px-3 py-1.5 transition-colors hover:bg-muted/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
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
          className="space-y-2"
        >
          <Panel
            title="Under-review summary"
            icon={<ShieldCheck className="h-4 w-4" />}
          >
            {candidate.status === "under_review" && candidate.evaluation_states?.subject_test !== "passed" ? <div role="status" className="mb-3 rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700">Subject test missing/not passed. Final outcome actions remain locked.</div> : null}
            <DefinitionGrid
              values={Object.entries(candidate.under_review || {}).map(
                ([key, value]) => [humanize(key), value],
              )}
            />
          </Panel>
          <div className="grid gap-2 xl:grid-cols-3">
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
                              label: "Approve for CEO review",
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
              The Academic Director can approve the request for future CEO
              finalization or return it to HR.
            </p>
          ) : null}
          {approved.length ? (
            <p className="text-xs text-muted-foreground">
              Legacy approved requests remain available for finalization.
            </p>
          ) : null}
        </div>
      ) : null}

      {tab === "training" && role === "hr_manager" && candidate.academy ? (
        <TrainingPanel
          rows={trainingRows}
          subject={candidate.academy.subject}
          position={candidate.applied_position}
          startDate={candidate.academy.start_date}
          promotionState={
            activeTeacherPromotionRequest?.status as
              | "requested"
              | "approved"
              | "returned"
              | undefined
          }
          onPromote={
            candidate.status === "teacher_academy" &&
            permissions?.can_request_approval
              ? () =>
                  setAction({
                    kind: "request_approval",
                    previous: {
                      ...(activeTeacherPromotionRequest || {}),
                      requested_outcome: "active_teacher",
                      request_note:
                        text(activeTeacherPromotionRequest?.request_note) ||
                        "Teacher Academy completed: all assigned lessons passed with an average score above 7.0.",
                    },
                  })
              : undefined
          }
        />
      ) : null}

      {tab === "activity" ? (
        <div
          id="candidate-panel-activity"
          role="tabpanel"
          aria-labelledby="candidate-tab-activity"
          className="grid gap-2 xl:grid-cols-3"
        >
          <Panel title="Tasks" icon={<CalendarClock className="h-4 w-4" />}>
            <div className="space-y-2">
              {(candidate.tasks || []).map((task) => (
                <article
                  key={task.id}
                  className="flex min-h-14 items-center justify-between gap-2 rounded-lg border border-border p-3"
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
            <ol className="space-y-2">
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
        open={Boolean(
          action &&
            action.kind !== "record_test" &&
            !modalActionKinds.has(action.kind),
        )}
        onClose={() => {
          if (!mutation.isPending) {
            mutation.reset();
            setAction(null);
          }
        }}
        title={actionTitle(action)}
        description={candidate.full_name}
        widthClass="sm:max-w-xl"
        footer={
          action &&
          action.kind !== "record_test" &&
          !modalActionKinds.has(action.kind) ? (
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className={secondaryButtonClass}
                disabled={mutation.isPending}
                onClick={() => {
                  mutation.reset();
                  setAction(null);
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
                {actionSubmitLabel(action)}
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
        {action &&
        action.kind !== "record_test" &&
        !modalActionKinds.has(action.kind) ? (
          <form id={formId} onSubmit={submitAction}>
            <ActionFields
              action={action}
              candidate={candidate}
              options={options.data}
            />
          </form>
        ) : null}
      </Drawer>

      <Modal
        open={Boolean(action && modalActionKinds.has(action.kind))}
        onClose={() => {
          if (!mutation.isPending) {
            mutation.reset();
            setAction(null);
          }
        }}
        title={actionTitle(action)}
        subtitle={candidate.full_name}
        size={action?.kind === "appointment_status" ? "sm" : "md"}
      >
        {action && modalActionKinds.has(action.kind) ? (
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={submitAction}>
            <ModalBody>
              {mutation.error ? (
                <div
                  role="alert"
                  className="mb-3 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
                >
                  {queryError(mutation.error)}
                </div>
              ) : null}
              <ActionFields
                action={action}
                candidate={candidate}
                options={options.data}
              />
            </ModalBody>
            <ModalFooter>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  disabled={mutation.isPending}
                  onClick={() => {
                    mutation.reset();
                    setAction(null);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className={buttonClass} disabled={mutation.isPending}>
                  {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {actionSubmitLabel(action)}
                </button>
              </div>
            </ModalFooter>
          </form>
        ) : null}
      </Modal>

      <Modal
        open={action?.kind === "record_test"}
        onClose={() => {
          if (!mutation.isPending) {
            mutation.reset();
            setAction(null);
          }
        }}
        title="Record subject test"
        subtitle={candidate.full_name}
        size="sm"
        mobileMode="sheet"
        closeOnEscape={!mutation.isPending}
        closeOnOutsideClick={!mutation.isPending}
      >
        <form id={`${formId}-subject-test`} onSubmit={submitAction}>
          <ModalBody>
            {mutation.error ? (
              <div role="alert" className="mb-3 rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                {queryError(mutation.error)}
              </div>
            ) : null}
            {action?.kind === "record_test" ? (
              <ActionFields action={action} candidate={candidate} options={options.data} />
            ) : null}
          </ModalBody>
          <ModalFooter>
            <div className="flex justify-end gap-2">
              <button type="button" className={secondaryButtonClass} disabled={mutation.isPending} onClick={() => { mutation.reset(); setAction(null); }}>
                Cancel
              </button>
              <button type="submit" className={buttonClass} disabled={mutation.isPending}>
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save
              </button>
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
        <ol className="space-y-2">
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
          options={options.data}
          onClose={() => setInterviewSession(null)}
          onAnnouncement={onAnnouncement}
        />
      ) : null}
      {demoSession ? (
        <DemoSessionModal
          open
          candidate={candidate}
          appointment={demoSession}
          onClose={() => setDemoSession(null)}
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
