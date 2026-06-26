import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  ClipboardCheck,
  GraduationCap,
  Info,
  Pencil,
  Plus,
  SlidersHorizontal,
  Trash2,
  Users,
  X,
  XCircle,
} from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "../shared";

type TeacherTab = "hiring" | "training" | "active";
type ToastTone = "success" | "danger";
type Candidate = Record<string, unknown>;
type Teacher = Record<string, unknown>;

const TAB_STORAGE_KEY = "msi.admin.teacherTab";
const TRAINING_FILTER_STORAGE_KEY = "msi.admin.teacherTrainingFilter";
const DETAIL_CANDIDATE_STORAGE_KEY = "msi.admin.teacherDetailCandidateId";

const tabs: Array<{ key: TeacherTab; label: string; hint: string }> = [
  { key: "hiring", label: "Hiring Pipeline", hint: "Interview and test stages" },
  { key: "training", label: "Training", hint: "Lesson evaluation" },
  { key: "active", label: "Active Teachers", hint: "Assigned staff" },
];

const hiringStages = [
  { key: "new", title: "New", detail: "Fresh applications to screen." },
  { key: "interview", title: "Interview", detail: "Fluency, mindset, professionalism." },
  { key: "math_test", title: "Math Test", detail: "Subject knowledge and accuracy." },
  { key: "training_ready", title: "Training", detail: "Passed hiring, ready for practice." },
];

const TRAINING_TARGET_LESSONS = 12;

const trainingRubric: Array<{ key: string; label: string; detail: string }> = [
  {
    key: "TGC",
    label: "Teacher Guidance Compliance",
    detail: "Prepared from the teacher guidance and follows the expected MSI lesson method.",
  },
  {
    key: "TA",
    label: "Timing Adherence",
    detail: "Keeps warm-up, teaching, practice, and recap inside the planned lesson timing.",
  },
  {
    key: "RF",
    label: "Resource Familiarity",
    detail: "Uses slides, board work, worksheets, answers, and lesson materials confidently.",
  },
  {
    key: "C",
    label: "Confidence",
    detail: "Leads the class calmly, clearly, and with professional presence.",
  },
  {
    key: "EF",
    label: "English Fluency",
    detail: "Uses accurate, natural classroom English and explains mathematical ideas smoothly.",
  },
  {
    key: "SE",
    label: "Student Engagement",
    detail: "Checks understanding, asks useful questions, and keeps students actively involved.",
  },
];
const trainingScoreScale: Array<{ score: string; label: string; tone: string }> = [
  { score: "0", label: "Not shown", tone: "bg-muted text-muted-foreground" },
  { score: "5", label: "Weak", tone: "bg-amber-50 text-amber-700" },
  { score: "7", label: "Pass mark", tone: "bg-sky-50 text-sky-700" },
  { score: "10", label: "Excellent", tone: "bg-emerald-50 text-emerald-700" },
];

const statusLabels: Record<string, string> = {
  new: "New",
  interview: "Interview",
  math_test: "Math Test",
  training_ready: "Training Ready",
  training_passed: "Awaiting Decision",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const candidateStatusOptions = [
  "new",
  "interview",
  "math_test",
  "training_ready",
  "training_passed",
  "hired",
  "rejected",
  "withdrawn",
];

const teacherCategories = [
  { key: "junior", label: "Junior Teacher" },
  { key: "trained", label: "Trained Teacher" },
  { key: "experienced_igcse", label: "Experienced IGCSE Teacher" },
];

const semesterStages = ["1-2", "3-4", "5-6"];

const lessonPayrates: Record<string, Record<string, Record<number, number>>> = {
  junior: {
    "1-2": { 7: 80000, 8: 85000, 9: 90000, 10: 100000 },
    "3-4": { 7: 90000, 8: 95000, 9: 100000, 10: 110000 },
    "5-6": { 7: 100000, 8: 105000, 9: 110000, 10: 120000 },
  },
  trained: {
    "1-2": { 7: 100000, 8: 105000, 9: 110000, 10: 120000 },
    "3-4": { 7: 110000, 8: 115000, 9: 120000, 10: 130000 },
    "5-6": { 7: 120000, 8: 125000, 9: 130000, 10: 140000 },
  },
  experienced_igcse: {
    "1-2": { 7: 120000, 8: 130000, 9: 140000, 10: 150000 },
    "3-4": { 7: 140000, 8: 150000, 9: 160000, 10: 170000 },
    "5-6": { 7: 160000, 8: 170000, 9: 180000, 10: 200000 },
  },
};

function teacherCategoryLabel(value: unknown) {
  const normalized = asString(value) || "junior";
  return teacherCategories.find((category) => category.key === normalized)?.label || "Junior Teacher";
}

function scoreBand(value: unknown) {
  const score = Number(value);
  if (score >= 10) return 10;
  if (score >= 9) return 9;
  if (score >= 8) return 8;
  return 7;
}

function suggestedLessonRate(category: unknown, semesterStage: unknown, performanceScore: unknown) {
  const categoryKey = asString(category) || "junior";
  const stageKey = asString(semesterStage) || "1-2";
  return lessonPayrates[categoryKey]?.[stageKey]?.[scoreBand(performanceScore)] || 0;
}

function formatUzs(value: number) {
  return value ? `${value.toLocaleString("en-US")} UZS` : "";
}

async function postForm(url: string, fields: Record<string, string>, csrf: string) {
  const body = new FormData();
  Object.entries(fields).forEach(([key, value]) => body.set(key, value));
  body.set("csrf_token", csrf);
  let data: Record<string, unknown> = {};
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf },
      body,
    });
    try {
      data = (await res.json()) as Record<string, unknown>;
    } catch {
      data = {};
    }
    return { ok: res.ok && data.ok !== false, data };
  } catch {
    return { ok: false, data: { message: "Network error. Please try again." } };
  }
}

function latestCandidateEvent(candidate: Candidate) {
  const events = Array.isArray(candidate.events) ? candidate.events : [];
  return events[0] as Record<string, unknown> | undefined;
}

function candidateEvents(candidate: Candidate) {
  return (Array.isArray(candidate.events) ? candidate.events : []) as Array<Record<string, unknown>>;
}

function trainingEvaluationEvents(candidate: Candidate) {
  return candidateEvents(candidate).filter((event) => asString(event.event_type) === "training_evaluation");
}

function trainingAverageScore(events: Array<Record<string, unknown>>) {
  const scores = events
    .map((event) => Number(event.score))
    .filter((score) => Number.isFinite(score));
  if (!scores.length) return 0;
  return Math.round((scores.reduce((sum, score) => sum + score, 0) / scores.length) * 10) / 10;
}

function formatCandidateEvent(value: unknown) {
  const normalized = asString(value).toLowerCase();
  const labels: Record<string, string> = {
    created: "Candidate added",
    scheduled: "Interview scheduled",
    passed: "Passed",
    rejected: "Rejected",
    manual_correction: "Stage corrected",
    stage_corrected: "Stage corrected",
    training_evaluation: "Training evaluated",
    training_passed: "Awaiting decision",
    awaiting_decision: "Awaiting decision",
    training_complete: "Training complete",
    final_decision: "Final decision",
    returned_to_training: "Returned to training",
    hired: "Hired",
    training_repeat: "Repeat training",
    training_hold: "Training on hold",
    training_rejected: "Rejected after training",
    reopened: "Reopened",
    training_ready: "Ready for training",
    withdrawn: "Withdrawn",
  };
  return labels[normalized] || asString(value) || "Updated";
}

function formatCandidateEventNote(value: unknown) {
  const note = asString(value);
  if (!note) return "";
  if (note.toLowerCase() === "manual stage correction.") {
    return "";
  }
  return note;
}

function CandidateModal({
  csrf,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  csrf: string;
  submitting: boolean;
  error: string;
  onSubmit: (fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    onSubmit(fields);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4">
      <div className="flex max-h-[88dvh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">Add Candidate</h3>
            <p className="text-xs text-muted-foreground">Basic details are enough to start the pipeline.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto px-4 py-4">
          <input type="hidden" name="csrf_token" value={csrf} />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Full Name
              </span>
              <input
                type="text"
                name="candidate_full_name"
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Subject
              </span>
              <input
                type="text"
                name="candidate_subject"
                placeholder="IGCSE Mathematics A"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Phone
              </span>
              <input
                type="text"
                name="candidate_phone"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Telegram
              </span>
              <input
                type="text"
                name="candidate_telegram"
                placeholder="@username"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Email
              </span>
              <input
                type="email"
                name="candidate_email"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Source
              </span>
              <input
                type="text"
                name="candidate_source"
                placeholder="Telegram, referral, HH..."
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Notes
              </span>
              <textarea
                name="candidate_notes"
                rows={3}
                className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
          </div>

          {error ? (
            <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
          ) : null}

          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60"
            >
              {submitting ? "Saving..." : "Save Candidate"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StageButton({
  label,
  tone = "primary",
  disabled,
  onClick,
}: {
  label: string;
  tone?: "primary" | "muted" | "danger";
  disabled: boolean;
  onClick: () => void;
}) {
  const toneClass =
    tone === "danger"
      ? "border border-destructive/20 bg-destructive/10 text-destructive hover:bg-destructive/15"
      : tone === "muted"
        ? "border border-foreground/10 bg-surface text-foreground hover:bg-muted"
        : "bg-primary text-primary-foreground hover:opacity-90";
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`h-8 rounded-lg px-3 text-xs font-bold transition-opacity disabled:opacity-50 ${toneClass}`}
    >
      {label}
    </button>
  );
}

function TrainingEvaluationModal({
  candidate,
  editingEvent,
  busy,
  onClose,
  onSave,
}: {
  candidate: Candidate;
  editingEvent?: Record<string, unknown> | null;
  busy: boolean;
  onClose: () => void;
  onSave: (candidateId: number, eventId: number | null, fields: Record<string, string>) => void;
}) {
  const editDetail = (editingEvent && typeof editingEvent.detail === "object" ? editingEvent.detail : {}) as Record<string, unknown>;
  const editScores = (editDetail.scores && typeof editDetail.scores === "object" ? editDetail.scores : {}) as Record<string, unknown>;
  const editComments = (editDetail.comments && typeof editDetail.comments === "object" ? editDetail.comments : {}) as Record<string, unknown>;
  const lessonNumber = editingEvent
    ? Number(editDetail.lesson) || 0
    : trainingEvaluationEvents(candidate).length + 1;
  const [scores, setScores] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      trainingRubric.map((item) => [
        item.key,
        editingEvent && editScores[item.key] !== undefined ? String(editScores[item.key]) : "7",
      ]),
    ),
  );
  const scoreValues = trainingRubric
    .map((item) => Number(scores[item.key]))
    .filter((value) => Number.isFinite(value));
  const average = scoreValues.length
    ? Math.round((scoreValues.reduce((sum, value) => sum + value, 0) / scoreValues.length) * 10) / 10
    : 0;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const outcome = asString(data.get("training_outcome")) || "accepted";
    const comments: Record<string, string> = {};
    const criteriaScores: Record<string, number> = {};
    trainingRubric.forEach((item) => {
      const numeric = Number(scores[item.key]);
      if (Number.isFinite(numeric)) {
        criteriaScores[item.key] = numeric;
      }
      const comment = asString(data.get(`comment_${item.key}`));
      if (comment) {
        comments[item.key] = comment;
      }
    });
    const detail = {
      lesson: lessonNumber,
      target: TRAINING_TARGET_LESSONS,
      date: asString(data.get("training_date")),
      evaluator: asString(data.get("training_evaluator")),
      class: asString(data.get("training_class")),
      type: asString(data.get("training_type")),
      topic: asString(data.get("training_topic")),
      outcome,
      average,
      scores: criteriaScores,
      comments,
      strengths: asString(data.get("training_strengths")),
      problems: asString(data.get("training_problems")),
      next_action: asString(data.get("training_next_action")),
    };
    const rubricText = trainingRubric
      .map((item) => {
        const comment = asString(data.get(`comment_${item.key}`));
        return `${item.key} (${item.label}): ${scores[item.key] || "-"}${comment ? ` - ${comment}` : ""}`;
      })
      .join("\n");
    const notes = [
      `Lesson: ${lessonNumber}/${TRAINING_TARGET_LESSONS}`,
      `Outcome: ${outcome === "accepted" ? "Accepted" : "Redo"}`,
      `Lesson date: ${asString(data.get("training_date")) || "-"}`,
      `Evaluator: ${asString(data.get("training_evaluator")) || "-"}`,
      `Class: ${asString(data.get("training_class")) || "-"}`,
      `Type: ${asString(data.get("training_type")) || "-"}`,
      `Topic: ${asString(data.get("training_topic")) || "-"}`,
      `Criteria:\n${rubricText}`,
      `Strengths: ${asString(data.get("training_strengths")) || "-"}`,
      `Problems: ${asString(data.get("training_problems")) || "-"}`,
      `Next action: ${asString(data.get("training_next_action")) || "-"}`,
    ].join("\n");

    const fields: Record<string, string> = {
      candidate_result: outcome,
      candidate_score: String(average),
      candidate_event_notes: notes,
      candidate_event_detail: JSON.stringify(detail),
    };
    if (!editingEvent) {
      fields.candidate_status = "training_ready";
      fields.candidate_event_type = "training_evaluation";
    }
    onSave(asNumber(candidate.id), editingEvent ? asNumber(editingEvent.id) : null, fields);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4">
      <div className="flex max-h-[90dvh] w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">{editingEvent ? "Edit Evaluation" : "Training Evaluation"}</h3>
            <p className="text-xs text-muted-foreground">
              {asString(candidate.full_name)} · lesson {lessonNumber}/{TRAINING_TARGET_LESSONS} · average {average.toFixed(1)}/10
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto px-4 py-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Date</span>
              <input name="training_date" type="date" defaultValue={asString(editDetail.date)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evaluator</span>
              <input name="training_evaluator" type="text" defaultValue={asString(editDetail.evaluator)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Class</span>
              <input name="training_class" type="text" defaultValue={asString(editDetail.class)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Type</span>
              <select name="training_type" defaultValue={asString(editDetail.type) || "demo"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
                <option value="demo">Demo</option>
                <option value="shadow">Shadow</option>
                <option value="trial">Trial Lesson</option>
                <option value="real_class">Real Class</option>
              </select>
            </label>
            <label className="block sm:col-span-2 lg:col-span-4">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Topic</span>
              <input name="training_topic" type="text" defaultValue={asString(editDetail.topic)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {trainingRubric.map((item) => (
              <div key={item.key} className="rounded-lg border border-foreground/8 bg-background p-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <span className="block text-[11px] font-bold text-foreground">
                      {item.key} · {item.label}
                    </span>
                    <p className="mt-0.5 text-[10px] leading-4 text-muted-foreground">{item.detail}</p>
                  </div>
                  <input
                    aria-label={`${item.label} score`}
                    type="number"
                    min="0"
                    max="10"
                    step="0.5"
                    value={scores[item.key] || ""}
                    onChange={(event) => setScores((current) => ({ ...current, [item.key]: event.target.value }))}
                    className="h-8 w-16 shrink-0 rounded-lg border border-foreground/10 bg-surface px-2 text-xs font-bold outline-none"
                  />
                </div>
                <textarea
                  name={`comment_${item.key}`}
                  rows={2}
                  defaultValue={asString(editComments[item.key])}
                  placeholder="Comment for this criterion"
                  className="mt-2 w-full resize-none rounded-lg border border-foreground/10 bg-surface px-2 py-1.5 text-xs outline-none"
                />
              </div>
            ))}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Lesson Outcome</span>
              <select name="training_outcome" defaultValue={asString(editDetail.outcome) || "accepted"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
                <option value="accepted">Accepted</option>
                <option value="redo">Redo</option>
              </select>
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Next Action</span>
              <input name="training_next_action" type="text" defaultValue={asString(editDetail.next_action)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block sm:col-span-3">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Strengths</span>
              <textarea name="training_strengths" rows={2} defaultValue={asString(editDetail.strengths)} className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block sm:col-span-3">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Problems</span>
              <textarea name="training_problems" rows={2} defaultValue={asString(editDetail.problems)} className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
          </div>

          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button type="button" onClick={onClose} className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted">
              Cancel
            </button>
            <button type="submit" disabled={busy} className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60">
              {editingEvent ? "Update Evaluation" : "Save Evaluation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CandidateCard({
  candidate,
  busy,
  onAction,
}: {
  candidate: Candidate;
  busy: boolean;
  onAction: (
    candidateId: number,
    fields: Record<string, string>,
    opts?: { confirmMessage?: string },
  ) => void;
}) {
  const status = asString(candidate.status) || "new";
  const id = asNumber(candidate.id);
  const latestEvent = latestCandidateEvent(candidate);
  const candidateName = asString(candidate.full_name) || "this candidate";
  const latestEventAuthor = latestEvent ? asString(latestEvent.created_by) : "";
  const latestEventNote = latestEvent ? formatCandidateEventNote(latestEvent.notes) : "";
  const [score, setScore] = useState("");
  const [stage, setStage] = useState(status);
  const [editingStage, setEditingStage] = useState(false);

  function advance(fields: Record<string, string>, confirmMessage?: string) {
    onAction(id, fields, confirmMessage ? { confirmMessage } : undefined);
  }

  return (
    <div className="rounded-lg border border-foreground/8 bg-surface p-3 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold">{asString(candidate.full_name)}</p>
          <p className="truncate text-xs text-muted-foreground">{asString(candidate.subject) || "Subject not set"}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <span className="rounded-md bg-muted px-2 py-1 text-[10px] font-bold text-muted-foreground">
            {statusLabels[status] || status}
          </span>
          <button
            type="button"
            onClick={() => setEditingStage((open) => !open)}
            disabled={busy}
            aria-label="Correct stage"
            title="Correct stage"
            className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-50"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {(asString(candidate.phone) || asString(candidate.telegram_username) || asString(candidate.source)) ? (
        <div className="mt-2 grid gap-1 text-[11px] text-muted-foreground">
          {asString(candidate.phone) ? <span>{asString(candidate.phone)}</span> : null}
          {asString(candidate.telegram_username) ? <span>{asString(candidate.telegram_username)}</span> : null}
          {asString(candidate.source) ? <span>Source: {asString(candidate.source)}</span> : null}
        </div>
      ) : null}

      {latestEvent ? (
        <div className="mt-2 rounded-md bg-background px-2.5 py-2 text-[11px] text-muted-foreground">
          <span className="font-bold text-foreground">{formatCandidateEvent(latestEvent.result)}</span>
          {latestEventAuthor ? <span> · by {latestEventAuthor}</span> : null}
          {latestEvent.score !== null && latestEvent.score !== undefined ? (
            <span> · Score {asString(latestEvent.score)}</span>
          ) : null}
          {latestEventNote ? <p className="mt-1 leading-4">{latestEventNote}</p> : null}
        </div>
      ) : null}

      {editingStage ? (
        <div className="mt-3 rounded-lg border border-foreground/8 bg-background p-2">
          <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
            Correct Stage
          </span>
          <div className="grid grid-cols-[minmax(0,1fr)_4.5rem] gap-2">
            <select
              value={stage}
              onChange={(event) => setStage(event.target.value)}
              className="h-8 rounded-lg border border-foreground/10 bg-surface px-2 text-xs font-semibold outline-none"
            >
              {candidateStatusOptions.map((option) => (
                <option key={option} value={option}>
                  {statusLabels[option] || option}
                </option>
              ))}
            </select>
            <StageButton
              label="Set"
              tone="muted"
              disabled={busy}
              onClick={() => {
                setEditingStage(false);
                advance({
                  candidate_status: stage,
                  candidate_event_type: "manual_correction",
                  candidate_result: "stage_corrected",
                  candidate_event_notes: `Stage manually set to ${statusLabels[stage] || stage}.`,
                });
              }}
            />
          </div>
        </div>
      ) : null}

      <div className="mt-3 grid gap-2">
        {status === "new" ? (
          <StageButton
            label="Move to Interview"
            disabled={busy}
            onClick={() =>
              advance({
                candidate_status: "interview",
                candidate_event_type: "interview",
                candidate_result: "scheduled",
              })
            }
          />
        ) : null}

        {status === "interview" ? (
          <div className="grid grid-cols-2 gap-2">
            <StageButton
              label="Pass"
              disabled={busy}
              onClick={() =>
                advance({
                  candidate_status: "math_test",
                  candidate_event_type: "interview",
                  candidate_result: "passed",
                })
              }
            />
            <StageButton
              label="Reject"
              tone="danger"
              disabled={busy}
              onClick={() =>
                advance(
                  {
                    candidate_status: "rejected",
                    candidate_event_type: "interview",
                    candidate_result: "rejected",
                  },
                  `Reject ${candidateName}?`,
                )
              }
            />
          </div>
        ) : null}

        {status === "math_test" ? (
          <div className="grid gap-2">
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={score}
              onChange={(event) => setScore(event.target.value)}
              placeholder="Test score (optional)"
              className="h-8 rounded-lg border border-foreground/10 bg-surface px-2 text-xs outline-none"
            />
            <div className="grid grid-cols-2 gap-2">
              <StageButton
                label="Pass Test"
                disabled={busy}
                onClick={() =>
                  advance({
                    candidate_status: "training_ready",
                    candidate_event_type: "math_test",
                    candidate_result: "passed",
                    candidate_score: score,
                  })
                }
              />
              <StageButton
                label="Reject"
                tone="danger"
                disabled={busy}
                onClick={() =>
                  advance(
                    {
                      candidate_status: "rejected",
                      candidate_event_type: "math_test",
                      candidate_result: "rejected",
                      candidate_score: score,
                    },
                    `Reject ${candidateName}?`,
                  )
                }
              />
            </div>
          </div>
        ) : null}

        {status === "training_ready" ? (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Ready for training
          </div>
        ) : null}
      </div>
    </div>
  );
}

function TeacherAssignmentModal({
  state,
  isEdit,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: any;
  isEdit: boolean;
  submitting: boolean;
  error: string;
  onSubmit: (fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const {
    teacherEdit,
    props,
    teacherMode,
    setTeacherMode,
    teacherSchool,
    setTeacherSchool,
    availableSubjectSchools,
    filteredTeacherOptions,
    filteredGroupOptions,
  } = state;
  const [category, setCategory] = useState(asString(teacherEdit?.category) || "junior");
  const [semesterStage, setSemesterStage] = useState(asString(teacherEdit?.semester_stage) || "1-2");
  const [performanceScore, setPerformanceScore] = useState(asString(teacherEdit?.performance_score) || "7");
  const suggestedRate = suggestedLessonRate(category, semesterStage, performanceScore);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    onSubmit(fields);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4">
      <div className="flex max-h-[88dvh] w-full max-w-xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">{isEdit ? "Edit Teacher" : "Assign Teacher"}</h3>
            <p className="text-xs text-muted-foreground">Create or assign a teacher to a group.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto px-4 py-4">
          <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
          <input type="hidden" name="teacher_mode" value={teacherMode} />

          <div className="mb-4 inline-flex rounded-lg border-2 border-foreground/10 bg-background p-0.5">
            <button
              type="button"
              onClick={() => setTeacherMode("select")}
              className={`h-8 rounded-md px-3 text-xs font-bold ${
                teacherMode === "select"
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              Existing
            </button>
            <button
              type="button"
              onClick={() => setTeacherMode("add")}
              className={`h-8 rounded-md px-3 text-xs font-bold ${
                teacherMode === "add"
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              New
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                School
              </span>
              <select
                name="teacher_assigned_school"
                value={teacherSchool}
                onChange={(event) => setTeacherSchool(event.target.value)}
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select school
                </option>
                {availableSubjectSchools.map((option: { code: string; label: string }) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Group
              </span>
              <select
                name="teacher_assigned_group"
                defaultValue={teacherEdit ? asString(teacherEdit.assigned_group) : ""}
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select group
                </option>
                {filteredGroupOptions.map((option: { name: string }) => (
                  <option key={option.name} value={option.name}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {teacherMode === "select" ? (
              <label className="block sm:col-span-2">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Teacher
                </span>
                <select
                  name="teacher_selected_name"
                  defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                  required
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                >
                  <option value="" disabled>
                    Select from existing teachers
                  </option>
                  {filteredTeacherOptions.map((option: { name: string }) => (
                    <option key={option.name} value={option.name}>
                      {option.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Full Name
                  </span>
                  <input
                    type="text"
                    name="teacher_full_name"
                    defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                    className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Pay Rate
                  </span>
                  <input
                    type="number"
                    name="teacher_pay_rate"
                    step="0.01"
                    min="0"
                    defaultValue={teacherEdit ? asString(teacherEdit.pay_rate) : ""}
                    className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                  />
                </label>
              </>
            )}
          </div>

          <div className="mt-4 border-t border-foreground/8 pt-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Rank
                </span>
                <select
                  name="teacher_category"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                >
                  {teacherCategories.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Semester Stage
                </span>
                <select
                  name="teacher_semester_stage"
                  value={semesterStage}
                  onChange={(event) => setSemesterStage(event.target.value)}
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                >
                  {semesterStages.map((stage) => (
                    <option key={stage} value={stage}>
                      {stage}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Score
                </span>
                <input
                  type="number"
                  name="teacher_performance_score"
                  min="0"
                  max="10"
                  step="0.1"
                  value={performanceScore}
                  onChange={(event) => setPerformanceScore(event.target.value)}
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Supervised Lessons
                </span>
                <input
                  type="number"
                  name="teacher_supervised_lessons"
                  min="0"
                  step="1"
                  defaultValue={teacherEdit ? asString(teacherEdit.supervised_lessons) : "0"}
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
              <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2.5 sm:col-span-2">
                <span className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Suggested Lesson Rate
                </span>
                <span className="mt-1 block text-sm font-bold">
                  {formatUzs(suggestedRate) || "Set score and rank"}
                </span>
              </div>
              <label className="block sm:col-span-3">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  IGCSE Evidence
                </span>
                <textarea
                  name="teacher_igcse_evidence"
                  rows={2}
                  defaultValue={teacherEdit ? asString(teacherEdit.igcse_evidence) : ""}
                  placeholder="Certification, Pearson Edexcel experience, exam-material evidence..."
                  className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
              <label className="block sm:col-span-3">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Promotion Notes
                </span>
                <textarea
                  name="teacher_promotion_notes"
                  rows={2}
                  defaultValue={teacherEdit ? asString(teacherEdit.promotion_notes) : ""}
                  placeholder="Approval notes from Academic Director, Head of Centre, or Subject Lead."
                  className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
            </div>
          </div>

          {error ? (
            <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
          ) : null}

          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60"
            >
              {submitting ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function daysSince(iso: string): number | null {
  if (!iso) return null;
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return null;
  return Math.floor((Date.now() - parsed) / 86_400_000);
}

// Derived training stats for one candidate, used by the table and detail view.
function trainingMeta(candidate: Candidate) {
  const history = trainingEvaluationEvents(candidate);
  const acceptedHistory = history.filter((event) => {
    const detail = (event.detail && typeof event.detail === "object" ? event.detail : {}) as Record<string, unknown>;
    return (asString(detail.outcome) || asString(event.result)) !== "redo";
  });
  const lessonCount = acceptedHistory.length;
  const average = trainingAverageScore(acceptedHistory.length ? acceptedHistory : history);
  const lastAt = history[0] ? asString(history[0].created_at) : "";
  const sinceLast = daysSince(lastAt);
  const status = asString(candidate.status);
  const stale = lessonCount > 0 && status === "training_ready" && (sinceLast ?? 0) >= 14;
  const readyToPass =
    status === "training_ready" && lessonCount >= TRAINING_TARGET_LESSONS && average >= 7;
  const progress = Math.min(100, Math.round((lessonCount / TRAINING_TARGET_LESSONS) * 100));
  return { history, acceptedHistory, lessonCount, average, lastAt, sinceLast, stale, readyToPass, progress, status };
}

function criterionAverages(history: Array<Record<string, unknown>>) {
  const sums: Record<string, { total: number; count: number }> = {};
  history.forEach((event) => {
    const detail = (event.detail && typeof event.detail === "object" ? event.detail : {}) as Record<string, unknown>;
    if ((asString(detail.outcome) || asString(event.result)) === "redo") {
      return;
    }
    const scores = (detail.scores && typeof detail.scores === "object" ? detail.scores : {}) as Record<string, unknown>;
    trainingRubric.forEach((item) => {
      const value = Number(scores[item.key]);
      if (Number.isFinite(value)) {
        const bucket = sums[item.key] || { total: 0, count: 0 };
        bucket.total += value;
        bucket.count += 1;
        sums[item.key] = bucket;
      }
    });
  });
  return trainingRubric.map((item) => {
    const bucket = sums[item.key];
    return {
      key: item.key,
      label: item.label,
      avg: bucket && bucket.count ? Math.round((bucket.total / bucket.count) * 10) / 10 : null,
    };
  });
}

function RubricModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={onClose}>
      <div
        className="flex max-h-[85dvh] w-full max-w-lg flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">How a trial lesson is graded</h3>
            <p className="text-xs text-muted-foreground">Each lesson is scored on six practical areas.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto px-4 py-4">
          <div className="mb-3 flex flex-wrap gap-1.5">
            {trainingScoreScale.map((step) => (
              <span key={step.score} className={`rounded-md px-2 py-1 text-[10px] font-bold ${step.tone}`}>
                {step.score} · {step.label}
              </span>
            ))}
          </div>
          <div className="grid gap-2">
            {trainingRubric.map((criteria) => (
              <div key={criteria.key} className="rounded-md border border-foreground/8 bg-background px-3 py-2">
                <p className="text-xs font-bold">
                  {criteria.key} · {criteria.label}
                </p>
                <p className="mt-0.5 text-[11px] leading-4 text-muted-foreground">{criteria.detail}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-muted-foreground">
            Trainees usually need {TRAINING_TARGET_LESSONS} lessons before a final decision. The overall lesson score is the
            average of the six areas.
          </p>
        </div>
      </div>
    </div>
  );
}

function PromoteModal({
  candidate,
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  candidate: Candidate;
  state: any;
  submitting: boolean;
  error: string;
  onSubmit: (candidateId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const availableSubjectSchools: Array<{ code: string; label: string }> = state.availableSubjectSchools || [];
  const groupOptions: Array<{ name: string; school_codes: string[] }> = state.groupOptions || [];
  const [school, setSchool] = useState(availableSubjectSchools[0]?.code || "");
  const training = trainingMeta(candidate);
  const [category, setCategory] = useState("junior");
  const [semesterStage, setSemesterStage] = useState("1-2");
  const [performanceScore, setPerformanceScore] = useState(training.average ? String(training.average) : "7");
  const suggestedRate = suggestedLessonRate(category, semesterStage, performanceScore);
  const groups = groupOptions.filter(
    (group) => !school || !group.school_codes.length || group.school_codes.includes(school),
  );

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit(asNumber(candidate.id), {
      teacher_assigned_school: school,
      teacher_assigned_group: asString(data.get("teacher_assigned_group")),
      teacher_pay_rate: asString(data.get("teacher_pay_rate")),
      teacher_category: category,
      teacher_semester_stage: semesterStage,
      teacher_performance_score: performanceScore,
      teacher_supervised_lessons: asString(data.get("teacher_supervised_lessons")),
      teacher_igcse_evidence: asString(data.get("teacher_igcse_evidence")),
      teacher_promotion_notes: asString(data.get("teacher_promotion_notes")),
    });
  }

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-foreground/60 p-4">
      <div className="flex w-full max-w-md flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">Promote to Active Teacher</h3>
            <p className="text-xs text-muted-foreground">{asString(candidate.full_name)} · assign a group and rate.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-4 py-4">
          <div className="grid gap-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">School</span>
              <select
                value={school}
                onChange={(event) => setSchool(event.target.value)}
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select school
                </option>
                {availableSubjectSchools.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Group</span>
              <select
                name="teacher_assigned_group"
                required
                defaultValue=""
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select group
                </option>
                {groups.map((group) => (
                  <option key={group.name} value={group.name}>
                    {group.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pay Rate</span>
              <input
                type="number"
                name="teacher_pay_rate"
                step="0.01"
                min="0"
                defaultValue={suggestedRate || ""}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Rank</span>
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                {teacherCategories.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Semester Stage</span>
              <select
                value={semesterStage}
                onChange={(event) => setSemesterStage(event.target.value)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                {semesterStages.map((stage) => (
                  <option key={stage} value={stage}>
                    {stage}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Score</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={performanceScore}
                onChange={(event) => setPerformanceScore(event.target.value)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Supervised Lessons</span>
              <input
                type="number"
                name="teacher_supervised_lessons"
                min="0"
                step="1"
                defaultValue={String(training.lessonCount || 0)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2.5">
              <span className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Suggested Rate</span>
              <span className="mt-1 block text-sm font-bold">{formatUzs(suggestedRate)}</span>
            </div>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">IGCSE Evidence</span>
              <textarea
                name="teacher_igcse_evidence"
                rows={2}
                className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Promotion Notes</span>
              <textarea
                name="teacher_promotion_notes"
                rows={2}
                className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
          </div>
          {error ? (
            <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
          ) : null}
          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60"
            >
              {submitting ? "Promoting..." : "Promote"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CandidateDetailModal({
  candidate,
  busy,
  onClose,
  onAddEvaluation,
  onAction,
  onPromote,
  onEditEvent,
  onDeleteEvent,
}: {
  candidate: Candidate;
  busy: boolean;
  onClose: () => void;
  onAddEvaluation: () => void;
  onAction: (candidateId: number, fields: Record<string, string>, opts?: { confirmMessage?: string }) => void;
  onPromote: () => void;
  onEditEvent: (event: Record<string, unknown>) => void;
  onDeleteEvent: (eventId: number) => void;
}) {
  const id = asNumber(candidate.id);
  const name = asString(candidate.full_name) || "Candidate";
  const meta = trainingMeta(candidate);
  const perCriterion = criterionAverages(meta.history);
  const isPassed = meta.status === "training_passed";
  const isRejected = ["rejected", "withdrawn"].includes(meta.status);
  const isHired = meta.status === "hired";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={onClose}>
      <div
        className="flex max-h-[90dvh] w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-sm font-bold">{name}</h3>
              <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold ${
                isHired
                  ? "bg-sky-50 text-sky-700"
                  : isPassed
                    ? "bg-emerald-50 text-emerald-700"
                    : isRejected
                      ? "bg-destructive/10 text-destructive"
                      : "bg-muted text-muted-foreground"
              }`}>
                {statusLabels[meta.status] || meta.status}
              </span>
            </div>
            <p className="truncate text-xs text-muted-foreground">{asString(candidate.subject) || "Subject not set"}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <div className="rounded-lg border border-foreground/8 bg-background p-3">
            <div className="flex items-center justify-between gap-3 text-xs font-bold">
              <span>{meta.lessonCount}/{TRAINING_TARGET_LESSONS} accepted lessons</span>
              <span>{meta.average ? `${meta.average.toFixed(1)}/10 avg` : "No score yet"}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: `${meta.progress}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {meta.sinceLast !== null ? (
                <span className="rounded-md bg-surface px-2 py-1 text-[10px] font-semibold text-muted-foreground">
                  Last evaluated {meta.sinceLast === 0 ? "today" : `${meta.sinceLast}d ago`}
                </span>
              ) : null}
              {meta.readyToPass ? (
                <span className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">Ready to pass</span>
              ) : null}
              {meta.stale ? (
                <span className="rounded-md bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700">Stalled</span>
              ) : null}
            </div>
          </div>
          {meta.lessonCount ? (
            <div className="mt-3 rounded-lg border border-foreground/8 bg-background p-3">
              <p className="mb-2 text-xs font-bold">Criteria averages</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {perCriterion.map((item) => (
                  <div key={item.key} className="flex items-center gap-2">
                    <span className="w-10 shrink-0 text-[10px] font-bold text-muted-foreground">{item.key}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${item.avg !== null ? Math.min(100, (item.avg / 10) * 100) : 0}%` }}
                      />
                    </div>
                    <span className="w-8 shrink-0 text-right text-[10px] font-bold">{item.avg !== null ? item.avg.toFixed(1) : "—"}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          <div className="mt-3">
            <p className="mb-2 text-xs font-bold">Evaluation history</p>
            {meta.history.length ? (
              <div className="grid gap-2">
                {meta.history.map((event, index) => {
                  const note = formatCandidateEventNote(event.notes);
                  const detail = (event.detail && typeof event.detail === "object" ? event.detail : {}) as Record<string, unknown>;
                  const outcome = asString(detail.outcome);
                  return (
                    <div key={`${asNumber(event.id)}-${index}`} className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
                      <div className="flex items-center justify-between gap-2 text-[11px]">
                        <span className="flex items-center gap-1.5 font-bold text-foreground">
                          Lesson {asNumber(detail.lesson) || meta.history.length - index}
                          {outcome ? (
                            <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                              outcome === "accepted" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                            }`}>
                              {outcome === "accepted" ? "Accepted" : "Redo"}
                            </span>
                          ) : null}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground">
                            {event.score !== null && event.score !== undefined ? `${asString(event.score)}/10` : "—"}
                            {asString(event.created_at) ? ` · ${asString(event.created_at).slice(0, 10)}` : ""}
                          </span>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => onEditEvent(event)}
                            className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-50"
                            aria-label="Edit evaluation"
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => onDeleteEvent(asNumber(event.id))}
                            className="flex h-6 w-6 items-center justify-center rounded-md text-destructive hover:bg-destructive/10 disabled:opacity-50"
                            aria-label="Delete evaluation"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                      {asString(event.created_by) ? (
                        <p className="mt-0.5 text-[10px] text-muted-foreground">by {asString(event.created_by)}</p>
                      ) : null}
                      {note ? <p className="mt-1 whitespace-pre-wrap text-[11px] leading-4 text-muted-foreground">{note}</p> : null}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-foreground/15 bg-background px-3 py-5 text-center text-xs text-muted-foreground">
                No evaluations recorded yet.
              </p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2 border-t border-foreground/8 px-4 py-3">
          {isRejected ? (
            <>
              <StageButton
                label="Reopen Hiring"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "interview",
                      candidate_event_type: "redeem",
                      candidate_result: "reopened",
                      candidate_event_notes: "Candidate reopened for hiring review.",
                    },
                    { confirmMessage: `Reopen ${name} for hiring review?` },
                  )
                }
              />
              <StageButton
                label="Send to Training"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "training_ready",
                      candidate_event_type: "redeem",
                      candidate_result: "reopened",
                      candidate_event_notes: "Candidate restored to training.",
                    },
                    { confirmMessage: `Restore ${name} to training?` },
                  )
                }
              />
            </>
          ) : isHired ? (
            <span className="text-xs font-semibold text-muted-foreground">Now an active teacher.</span>
          ) : isPassed ? (
            // Awaiting the head of department's final decision.
            <>
              <StageButton
                label="Back to Training"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(id, {
                    candidate_status: "training_ready",
                    candidate_event_type: "review",
                    candidate_result: "returned_to_training",
                    candidate_event_notes: "Returned to training for more lessons.",
                  })
                }
              />
              <StageButton
                label="Reject"
                tone="danger"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "rejected",
                      candidate_event_type: "final_decision",
                      candidate_result: "training_rejected",
                      candidate_event_notes: "Not approved for hire after training.",
                    },
                    { confirmMessage: `Reject ${name} after training?` },
                  )
                }
              />
              <StageButton label="Promote to Teacher" disabled={busy} onClick={onPromote} />
            </>
          ) : (
            <>
              <StageButton label="Add Evaluation" disabled={busy} onClick={onAddEvaluation} />
              <StageButton
                label="Mark Training Complete"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "training_passed",
                      candidate_event_type: "training_complete",
                      candidate_result: "awaiting_decision",
                      candidate_event_notes: "Training complete — sent to the head of department for a decision.",
                    },
                    { confirmMessage: `Send ${name} to the head for a final decision?` },
                  )
                }
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TeachersPanel({ state }: { state: any }) {
  const { teacherEdit, props, currentSchool } = state;
  const csrf: string = props.csrfToken || "";

  const [activeTab, setActiveTab] = useState<TeacherTab>(() => {
    if (typeof window !== "undefined") {
      const saved = window.sessionStorage.getItem(TAB_STORAGE_KEY);
      if (saved === "hiring" || saved === "training" || saved === "active") {
        return saved;
      }
    }
    return "hiring";
  });

  const [teachers, setTeachers] = useState<Teacher[]>(
    Array.isArray(state.teachers) ? state.teachers : [],
  );
  const [candidates, setCandidates] = useState<Candidate[]>(
    Array.isArray(props.adminTeacherCandidates) ? props.adminTeacherCandidates : [],
  );

  const [modalOpen, setModalOpen] = useState(Boolean(teacherEdit));
  const [candidateOpen, setCandidateOpen] = useState(false);
  const [trainingCandidate, setTrainingCandidate] = useState<Candidate | null>(null);
  const [editingTrainingEvent, setEditingTrainingEvent] = useState<Record<string, unknown> | null>(null);
  const [busyCandidateId, setBusyCandidateId] = useState<number | null>(null);
  const [teacherSubmitting, setTeacherSubmitting] = useState(false);
  const [candidateSubmitting, setCandidateSubmitting] = useState(false);
  const [modalError, setModalError] = useState("");
  const [candidateError, setCandidateError] = useState("");
  const [rubricOpen, setRubricOpen] = useState(false);
  const [detailCandidateId, setDetailCandidateId] = useState<number | null>(null);
  const [promoteCandidate, setPromoteCandidate] = useState<Candidate | null>(null);
  const [promoteSubmitting, setPromoteSubmitting] = useState(false);
  const [promoteError, setPromoteError] = useState("");
  const [trainingFilter, setTrainingFilter] = useState<"in_training" | "passed" | "rejected">(() => {
    if (typeof window !== "undefined") {
      const saved = window.sessionStorage.getItem(TRAINING_FILTER_STORAGE_KEY);
      if (saved === "in_training" || saved === "passed" || saved === "rejected") {
        return saved;
      }
    }
    return "in_training";
  });
  const [trainingSearch, setTrainingSearch] = useState("");
  const [trainingSort, setTrainingSort] = useState<"recent" | "progress" | "average" | "name">("recent");
  const [toast, setToast] = useState<{ message: string; tone: ToastTone } | null>(null);
  const toastTimer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (toastTimer.current) {
        window.clearTimeout(toastTimer.current);
      }
    };
  }, []);

  useEffect(() => {
    try {
      const saved = window.sessionStorage.getItem(DETAIL_CANDIDATE_STORAGE_KEY);
      if (!saved) {
        return;
      }
      const parsed = Number(saved);
      window.sessionStorage.removeItem(DETAIL_CANDIDATE_STORAGE_KEY);
      if (Number.isFinite(parsed) && parsed > 0) {
        setDetailCandidateId(parsed);
      }
    } catch {
    }
  }, []);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(TRAINING_FILTER_STORAGE_KEY, trainingFilter);
    } catch {
    }
  }, [trainingFilter]);

  function showToast(message: string, tone: ToastTone = "success") {
    setToast({ message, tone });
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
    }
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  }

  function selectTab(tab: TeacherTab) {
    setActiveTab(tab);
    try {
      window.sessionStorage.setItem(TAB_STORAGE_KEY, tab);
    } catch {
    }
  }

  function clearEditUrl() {
    if (teacherEdit && window.history?.replaceState) {
      window.history.replaceState(
        {},
        "",
        `/?panel=teachers&school=${encodeURIComponent(currentSchool)}`,
      );
    }
  }

  async function runCandidateAction(
    candidateId: number,
    fields: Record<string, string>,
    opts?: { confirmMessage?: string },
  ) {
    if (opts?.confirmMessage && !window.confirm(opts.confirmMessage)) {
      return;
    }
    setBusyCandidateId(candidateId);
    const { ok, data } = await postForm(routes.adminTeacherCandidateStatus(candidateId), fields, csrf);
    setBusyCandidateId(null);
    if (!ok) {
      showToast(asString(data.message) || "Could not update candidate.", "danger");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    showToast(asString(data.message) || "Candidate updated.");
  }

  async function saveTrainingEvaluation(
    candidateId: number,
    eventId: number | null,
    fields: Record<string, string>,
  ) {
    setBusyCandidateId(candidateId);
    const url =
      eventId !== null
        ? routes.adminTeacherCandidateEventEdit(candidateId, eventId)
        : routes.adminTeacherCandidateStatus(candidateId);
    const { ok, data } = await postForm(url, fields, csrf);
    setBusyCandidateId(null);
    if (!ok) {
      showToast(asString(data.message) || "Could not save evaluation.", "danger");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    setTrainingCandidate(null);
    setEditingTrainingEvent(null);
    showToast(asString(data.message) || (eventId !== null ? "Evaluation updated." : "Evaluation saved."));
  }

  async function deleteTrainingEvaluation(candidateId: number, eventId: number) {
    if (!window.confirm("Delete this lesson evaluation?")) {
      return;
    }
    setBusyCandidateId(candidateId);
    const { ok, data } = await postForm(routes.adminTeacherCandidateEventDelete(candidateId, eventId), {}, csrf);
    setBusyCandidateId(null);
    if (!ok) {
      showToast(asString(data.message) || "Could not delete evaluation.", "danger");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    showToast(asString(data.message) || "Evaluation deleted.");
  }

  async function submitCandidate(fields: Record<string, string>) {
    setCandidateSubmitting(true);
    setCandidateError("");
    const { ok, data } = await postForm(routes.adminTeacherCandidateCreate, fields, csrf);
    setCandidateSubmitting(false);
    if (!ok) {
      setCandidateError(asString(data.message) || "Could not add candidate.");
      return;
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    setCandidateOpen(false);
    showToast(asString(data.message) || "Candidate added.");
  }

  async function submitTeacher(fields: Record<string, string>) {
    setTeacherSubmitting(true);
    setModalError("");
    const url = teacherEdit
      ? routes.adminTeacherUpdate(asNumber(teacherEdit.id))
      : routes.adminTeacherCreate;
    const { ok, data } = await postForm(url, fields, csrf);
    setTeacherSubmitting(false);
    if (!ok) {
      setModalError(asString(data.message) || "Could not save teacher.");
      return;
    }
    if (Array.isArray(data.teachers)) {
      setTeachers(data.teachers as Teacher[]);
    }
    setModalOpen(false);
    clearEditUrl();
    showToast(asString(data.message) || "Teacher saved.");
  }

  async function deleteTeacher(teacherId: number, teacherName: string) {
    if (!window.confirm(`Delete ${teacherName || "this teacher"}?`)) {
      return;
    }
    const { ok, data } = await postForm(routes.adminTeacherDelete(teacherId), {}, csrf);
    if (!ok) {
      showToast(asString(data.message) || "Could not delete teacher.", "danger");
      return;
    }
    if (Array.isArray(data.teachers)) {
      setTeachers(data.teachers as Teacher[]);
    }
    showToast(asString(data.message) || "Teacher deleted.");
  }

  function closeTeacherModal() {
    setModalOpen(false);
    setModalError("");
    clearEditUrl();
  }

  async function runPromote(candidateId: number, fields: Record<string, string>) {
    setPromoteSubmitting(true);
    setPromoteError("");
    const { ok, data } = await postForm(routes.adminTeacherCandidatePromote(candidateId), fields, csrf);
    setPromoteSubmitting(false);
    if (!ok) {
      setPromoteError(asString(data.message) || "Could not promote candidate.");
      return;
    }
    if (Array.isArray(data.teachers)) {
      setTeachers(data.teachers as Teacher[]);
    }
    if (Array.isArray(data.candidates)) {
      setCandidates(data.candidates as Candidate[]);
    }
    setPromoteCandidate(null);
    setDetailCandidateId(null);
    showToast(asString(data.message) || "Candidate promoted.");
  }

  const activeCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return !["rejected", "withdrawn", "hired"].includes(status);
  });
  const closedCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return ["rejected", "withdrawn"].includes(status);
  });
  const trainingCandidates = candidates.filter(
    (candidate) => ["training_ready", "training_passed"].includes(asString(candidate.status)),
  );
  const inTrainingCount = trainingCandidates.filter(
    (candidate) => asString(candidate.status) === "training_ready",
  ).length;
  const trainingPassedCount = trainingCandidates.filter(
    (candidate) => asString(candidate.status) === "training_passed",
  ).length;
  const rejectedCandidates = closedCandidates;

  // Always re-read the open candidate from the live list so the detail view
  // reflects the latest data after an async action.
  const detailCandidate =
    detailCandidateId !== null
      ? candidates.find((candidate) => asNumber(candidate.id) === detailCandidateId) || null
      : null;

  const trainingFilterCounts = {
    in_training: inTrainingCount,
    passed: trainingPassedCount,
    rejected: rejectedCandidates.length,
  };
  const trainingFilters: Array<{
    key: "in_training" | "passed" | "rejected";
    label: string;
    tone: string;
  }> = [
    { key: "in_training", label: "In training", tone: "" },
    { key: "passed", label: "Awaiting decision", tone: "text-emerald-700" },
    { key: "rejected", label: "Rejected", tone: "text-destructive" },
  ];

  const trainingBase =
    trainingFilter === "passed"
      ? candidates.filter((candidate) => asString(candidate.status) === "training_passed")
      : trainingFilter === "rejected"
        ? rejectedCandidates
        : candidates.filter((candidate) => asString(candidate.status) === "training_ready");

  const trainingSearchNorm = trainingSearch.trim().toLowerCase();
  const trainingRows = trainingBase
    .filter((candidate) => {
      if (!trainingSearchNorm) return true;
      return (
        asString(candidate.full_name).toLowerCase().includes(trainingSearchNorm) ||
        asString(candidate.subject).toLowerCase().includes(trainingSearchNorm)
      );
    })
    .sort((a, b) => {
      const metaA = trainingMeta(a);
      const metaB = trainingMeta(b);
      if (trainingSort === "name") {
        return asString(a.full_name).localeCompare(asString(b.full_name));
      }
      if (trainingSort === "progress") {
        return metaB.lessonCount - metaA.lessonCount;
      }
      if (trainingSort === "average") {
        return metaB.average - metaA.average;
      }
      return asString(b.updated_at).localeCompare(asString(a.updated_at));
    });

  return (
    <div className="space-y-4">
      {toast ? (
        <div
          className={`fixed right-4 top-[calc(var(--app-top-inset)+4rem)] lg:top-4 z-[60] flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold shadow-card-hover ${
            toast.tone === "danger" ? "bg-destructive text-destructive-foreground" : "bg-foreground text-background"
          }`}
          role="status"
        >
          {toast.tone === "danger" ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
          {toast.message}
        </div>
      ) : null}

      {modalOpen ? (
        <TeacherAssignmentModal
          state={state}
          isEdit={Boolean(teacherEdit)}
          submitting={teacherSubmitting}
          error={modalError}
          onSubmit={submitTeacher}
          onClose={closeTeacherModal}
        />
      ) : null}
      {candidateOpen ? (
        <CandidateModal
          csrf={csrf}
          submitting={candidateSubmitting}
          error={candidateError}
          onSubmit={submitCandidate}
          onClose={() => {
            setCandidateOpen(false);
            setCandidateError("");
          }}
        />
      ) : null}
      {trainingCandidate ? (
        <TrainingEvaluationModal
          candidate={trainingCandidate}
          editingEvent={editingTrainingEvent}
          busy={busyCandidateId === asNumber(trainingCandidate.id)}
          onSave={saveTrainingEvaluation}
          onClose={() => {
            setTrainingCandidate(null);
            setEditingTrainingEvent(null);
          }}
        />
      ) : null}
      {rubricOpen ? <RubricModal onClose={() => setRubricOpen(false)} /> : null}
      {detailCandidate ? (
        <CandidateDetailModal
          candidate={detailCandidate}
          busy={busyCandidateId === asNumber(detailCandidate.id)}
          onClose={() => setDetailCandidateId(null)}
          onAddEvaluation={() => {
            setEditingTrainingEvent(null);
            setTrainingCandidate(detailCandidate);
            setDetailCandidateId(null);
          }}
          onAction={runCandidateAction}
          onPromote={() => {
            setPromoteError("");
            setPromoteCandidate(detailCandidate);
          }}
          onEditEvent={(event) => {
            setEditingTrainingEvent(event);
            setTrainingCandidate(detailCandidate);
            setDetailCandidateId(null);
          }}
          onDeleteEvent={(eventId) => deleteTrainingEvaluation(asNumber(detailCandidate.id), eventId)}
        />
      ) : null}
      {promoteCandidate ? (
        <PromoteModal
          candidate={promoteCandidate}
          state={state}
          submitting={promoteSubmitting}
          error={promoteError}
          onSubmit={runPromote}
          onClose={() => setPromoteCandidate(null)}
        />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-foreground/10 bg-surface p-1 shadow-card">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => selectTab(tab.key)}
                className={`rounded-md px-3 py-2 text-left text-xs font-bold transition-colors sm:px-4 ${
                  isActive ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <span className="block">{tab.label}</span>
                <span
                  className={`hidden text-[10px] font-semibold sm:block ${
                    isActive ? "text-background/70" : "text-muted-foreground"
                  }`}
                >
                  {tab.hint}
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap gap-2">
          {activeTab === "hiring" ? (
            <button
              type="button"
              onClick={() => {
                setCandidateError("");
                setCandidateOpen(true);
              }}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground"
            >
              <Plus className="h-4 w-4" />
              Add Candidate
            </button>
          ) : null}
          {activeTab === "active" ? (
            <button
              type="button"
              onClick={() => {
                setModalError("");
                setModalOpen(true);
              }}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground"
            >
              <Plus className="h-4 w-4" />
              Assign Teacher
            </button>
          ) : null}
        </div>
      </div>

      {activeTab === "hiring" ? (
        <ChartCard
          title="Hiring Pipeline"
          subtitle={`${activeCandidates.length} active · ${closedCandidates.length} closed`}
          icon={<ClipboardCheck className="h-4 w-4 text-info" />}
        >
          <div className="-mx-1 flex snap-x gap-3 overflow-x-auto px-1 pb-1 xl:grid xl:grid-cols-4 xl:overflow-visible">
            {hiringStages.map((stage) => {
              const stageCandidates = activeCandidates.filter(
                (candidate) => (asString(candidate.status) || "new") === stage.key,
              );
              return (
                <div
                  key={stage.key}
                  className="min-h-[13rem] w-[16rem] shrink-0 snap-start rounded-lg border border-foreground/8 bg-background p-3 xl:w-auto"
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold">{stage.title}</p>
                      <p className="text-[11px] leading-4 text-muted-foreground">{stage.detail}</p>
                    </div>
                    <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground">
                      {stageCandidates.length}
                    </span>
                  </div>

                  <div className="grid gap-2">
                    {stageCandidates.length ? (
                      stageCandidates.map((candidate) => (
                        <CandidateCard
                          key={asNumber(candidate.id)}
                          candidate={candidate}
                          busy={busyCandidateId === asNumber(candidate.id)}
                          onAction={runCandidateAction}
                        />
                      ))
                    ) : (
                      <div className="rounded-lg border border-dashed border-foreground/12 bg-surface/60 px-3 py-6 text-center">
                        <p className="text-xs font-bold text-muted-foreground">No candidates</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>
      ) : null}

      {activeTab === "training" ? (
        <ChartCard
          title="Training"
          subtitle={`${inTrainingCount} in training · ${trainingPassedCount} awaiting decision`}
          icon={<GraduationCap className="h-4 w-4 text-info" />}
          headerActions={
            <button
              type="button"
              onClick={() => setRubricOpen(true)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold text-foreground hover:bg-muted"
            >
              <Info className="h-3.5 w-3.5 text-info" />
              How grading works
            </button>
          }
        >
          <div className="mb-4 grid grid-cols-3 gap-2">
            {trainingFilters.map((filter) => {
              const isActive = trainingFilter === filter.key;
              return (
                <button
                  key={filter.key}
                  type="button"
                  onClick={() => setTrainingFilter(filter.key)}
                  className={`rounded-lg border px-3 py-2.5 text-left transition-colors ${
                    isActive
                      ? "border-foreground/30 bg-background ring-2 ring-foreground/15"
                      : "border-foreground/8 bg-background hover:bg-muted"
                  }`}
                >
                  <p className={`text-lg font-bold leading-none ${filter.tone}`}>
                    {trainingFilterCounts[filter.key]}
                  </p>
                  <p className="mt-1 text-[11px] font-semibold text-muted-foreground">{filter.label}</p>
                </button>
              );
            })}
          </div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={trainingSearch}
              onChange={(event) => setTrainingSearch(event.target.value)}
              placeholder="Search by name or subject"
              className="h-8 min-w-[12rem] flex-1 rounded-lg border border-foreground/10 bg-surface px-3 text-xs outline-none"
            />
            <select
              value={trainingSort}
              onChange={(event) => setTrainingSort(event.target.value as typeof trainingSort)}
              className="h-8 rounded-lg border border-foreground/10 bg-surface px-2 text-xs font-semibold outline-none"
              aria-label="Sort candidates"
            >
              <option value="recent">Recently updated</option>
              <option value="progress">Most lessons</option>
              <option value="average">Highest average</option>
              <option value="name">Name (A–Z)</option>
            </select>
          </div>
          <div className="miniapp-table-scroll max-h-[70dvh]">
            <table className="w-full min-w-[640px] text-left">
              <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="border-b border-foreground/5">
                  {["Candidate", "Progress", "Average", "Last evaluated", ""].map((heading) => (
                    <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trainingRows.length ? (
                  trainingRows.map((candidate) => {
                    const meta = trainingMeta(candidate);
                    return (
                      <tr
                        key={asNumber(candidate.id)}
                        onClick={() => setDetailCandidateId(asNumber(candidate.id))}
                        className="cursor-pointer border-b border-foreground/5 hover:bg-muted/50"
                      >
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <span className="block text-sm font-bold">{asString(candidate.full_name)}</span>
                            {meta.readyToPass ? (
                              <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700">Ready</span>
                            ) : null}
                            {meta.stale ? (
                              <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[9px] font-bold text-amber-700">Stalled</span>
                            ) : null}
                          </div>
                          <span className="text-xs text-muted-foreground">{asString(candidate.subject) || "Subject not set"}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                              <div className="h-full rounded-full bg-primary" style={{ width: `${meta.progress}%` }} />
                            </div>
                            <span className="text-[11px] font-semibold text-muted-foreground">
                              {meta.lessonCount}/{TRAINING_TARGET_LESSONS}
                            </span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-xs font-semibold">
                          {meta.average ? `${meta.average.toFixed(1)}/10` : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-xs text-muted-foreground">
                          {meta.sinceLast === null ? "—" : meta.sinceLast === 0 ? "Today" : `${meta.sinceLast}d ago`}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <span className="text-[11px] font-bold text-info">Open</span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center">
                      <p className="text-sm font-bold">
                        {trainingFilter === "rejected"
                          ? "No rejected candidates"
                          : trainingFilter === "passed"
                            ? "No candidates awaiting decision yet"
                            : "No candidates in training"}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {trainingFilter === "in_training"
                          ? "Candidates appear here once they pass the Math Test in the hiring pipeline."
                          : "Nothing to show for this filter yet."}
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </ChartCard>
      ) : null}

      {activeTab === "active" ? (
        <ChartCard
          title="Active Teachers"
          subtitle={`${teachers.length} assigned`}
          icon={<Users className="h-4 w-4 text-info" />}
        >
          <div className="miniapp-table-scroll max-h-[70dvh]">
            <table className="w-full min-w-[920px] text-left">
              <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="border-b border-foreground/5">
                  {["Teacher", "Rank", "Progress", "Pay Rate", "Assigned Group", "Actions"].map((heading) => (
                    <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {teachers.length ? (
                  teachers.map((teacher) => (
                    <tr key={asNumber(teacher.id)} className="border-b border-foreground/5">
                      <td className="px-3 py-2.5">
                        <span className="block text-sm font-bold">{asString(teacher.full_name)}</span>
                        <span className="text-xs text-muted-foreground">ID {asNumber(teacher.id)}</span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-700">
                          {teacherCategoryLabel(teacher.category)}
                        </span>
                        <span className="mt-1 block text-[11px] font-semibold text-muted-foreground">
                          Sem {asString(teacher.semester_stage) || "1-2"} · Score {asString(teacher.performance_score) || "7"}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full rounded-full bg-primary"
                              style={{ width: `${Math.min(100, Math.round((asNumber(teacher.supervised_lessons) / 120) * 100))}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-semibold text-muted-foreground">
                            {asNumber(teacher.supervised_lessons)}/120
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-xs">{asString(teacher.pay_rate) || "-"}</td>
                      <td className="px-3 py-2.5 text-xs font-semibold">
                        {asString(teacher.assigned_group) || "-"}
                        {asString(teacher.login) ? (
                          <span className="mt-1 block text-[10px] font-normal text-muted-foreground">
                            Login {asString(teacher.login)} · Pass {asString(teacher.password) || "—"}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <a
                            href={routes.adminTeacherEdit(asNumber(teacher.id), currentSchool)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                            aria-label={`Edit ${asString(teacher.full_name)}`}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </a>
                          <button
                            type="button"
                            onClick={() => deleteTeacher(asNumber(teacher.id), asString(teacher.full_name))}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10"
                            aria-label={`Delete ${asString(teacher.full_name)}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-sm text-muted-foreground">
                      No active teachers yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </ChartCard>
      ) : null}
    </div>
  );
}
