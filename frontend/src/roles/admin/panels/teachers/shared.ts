// Shared types, constants, and pure helpers for the Teachers panel.
import { asString } from "../../shared";
import { csrfHeaders } from "@/shared/lib/api";

export type TeacherTab = "hiring" | "training" | "academy" | "active";
export type ToastTone = "success" | "danger";
export type Candidate = Record<string, unknown>;
export type Teacher = Record<string, unknown>;

export const TAB_STORAGE_KEY = "msi.admin.teacherTab";
export const TRAINING_FILTER_STORAGE_KEY = "msi.admin.teacherTrainingFilter";
export const DETAIL_CANDIDATE_STORAGE_KEY = "msi.admin.teacherDetailCandidateId";

export const tabs: Array<{ key: TeacherTab; label: string; hint: string }> = [
  { key: "hiring", label: "Hiring Pipeline", hint: "Interview and test stages" },
  { key: "training", label: "Lesson Practice", hint: "Lesson evaluation" },
  { key: "academy", label: "Teacher Academy", hint: "New Academy teachers" },
  { key: "active", label: "Active Teachers", hint: "Assigned staff" },
];

export const hiringStages = [
  { key: "new", title: "New", detail: "Fresh applications to screen." },
  { key: "interview", title: "Interview", detail: "Fluency, mindset, professionalism." },
  { key: "math_test", title: "Math Test", detail: "Subject knowledge and accuracy." },
  { key: "training_ready", title: "Practice", detail: "Passed hiring, ready for lesson review." },
];

export const TRAINING_TARGET_LESSONS = 12;
export const HIRING_STAGE_PAGE_SIZE = 2;
export const TABLE_PAGE_SIZE = 8;

export const trainingRubric: Array<{ key: string; label: string; detail: string }> = [
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
export const trainingScoreScale: Array<{ score: string; label: string; tone: string }> = [
  { score: "0", label: "Not shown", tone: "bg-muted text-muted-foreground" },
  { score: "5", label: "Weak", tone: "bg-amber-50 text-amber-700" },
  { score: "7", label: "Pass mark", tone: "bg-sky-50 text-sky-700" },
  { score: "10", label: "Excellent", tone: "bg-emerald-50 text-emerald-700" },
];

export const statusLabels: Record<string, string> = {
  new: "New",
  interview: "Interview",
  math_test: "Math Test",
  training_ready: "Practice Ready",
  training_passed: "Awaiting Decision",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const candidateStatusOptions = [
  "new",
  "interview",
  "math_test",
  "training_ready",
  "training_passed",
  "hired",
  "rejected",
  "withdrawn",
];

export const teacherCategories = [
  { key: "junior", label: "Junior Teacher" },
  { key: "trained", label: "Trained Teacher" },
  { key: "experienced_igcse", label: "Experienced IGCSE Teacher" },
];

export const semesterStages = ["1-2", "3-4", "5-6"];

export const lessonPayrates: Record<string, Record<string, Record<number, number>>> = {
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

export function teacherCategoryLabel(value: unknown) {
  const normalized = asString(value) || "junior";
  return teacherCategories.find((category) => category.key === normalized)?.label || "Junior Teacher";
}

export function scoreBand(value: unknown) {
  const score = Number(value);
  if (score >= 10) return 10;
  if (score >= 9) return 9;
  if (score >= 8) return 8;
  return 7;
}

export function suggestedLessonRate(category: unknown, semesterStage: unknown, performanceScore: unknown) {
  const categoryKey = asString(category) || "junior";
  const stageKey = asString(semesterStage) || "1-2";
  return lessonPayrates[categoryKey]?.[stageKey]?.[scoreBand(performanceScore)] || 0;
}

export function formatUzs(value: number) {
  return value ? `${value.toLocaleString("en-US")} UZS` : "";
}

export async function postForm(url: string, fields: Record<string, string>, csrf: string) {
  const body = new FormData();
  Object.entries(fields).forEach(([key, value]) => body.set(key, value));
  body.set("csrf_token", csrf);
  let data: Record<string, unknown> = {};
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: csrfHeaders(csrf),
      body,
    });
    try {
      data = (await res.json()) as Record<string, unknown>;
    } catch {
      data = {};
    }
    const isApiSuccess = data.status === "success" && data.data && typeof data.data === "object";
    const isApiError = data.status === "error";
    const payload = isApiSuccess ? data.data as Record<string, unknown> : data;
    return { ok: res.ok && !isApiError && data.ok !== false, data: payload };
  } catch {
    return { ok: false, data: { message: "Network error. Please try again." } };
  }
}

export function latestCandidateEvent(candidate: Candidate) {
  const events = Array.isArray(candidate.events) ? candidate.events : [];
  return events[0] as Record<string, unknown> | undefined;
}

export function candidateEvents(candidate: Candidate) {
  return (Array.isArray(candidate.events) ? candidate.events : []) as Array<Record<string, unknown>>;
}

export function trainingEvaluationEvents(candidate: Candidate) {
  return candidateEvents(candidate).filter((event) => asString(event.event_type) === "training_evaluation");
}

export function trainingAverageScore(events: Array<Record<string, unknown>>) {
  const scores = events
    .map((event) => Number(event.score))
    .filter((score) => Number.isFinite(score));
  if (!scores.length) return 0;
  return Math.round((scores.reduce((sum, score) => sum + score, 0) / scores.length) * 10) / 10;
}

export function formatCandidateEvent(value: unknown) {
  const normalized = asString(value).toLowerCase();
  const labels: Record<string, string> = {
    created: "Candidate added",
    scheduled: "Interview scheduled",
    passed: "Passed",
    rejected: "Rejected",
    manual_correction: "Stage corrected",
    stage_corrected: "Stage corrected",
    training_evaluation: "Practice evaluated",
    training_passed: "Awaiting decision",
    awaiting_decision: "Awaiting decision",
    training_complete: "Practice complete",
    final_decision: "Final decision",
    returned_to_training: "Returned to practice",
    hired: "Hired",
    training_repeat: "Repeat practice",
    training_hold: "Practice on hold",
    training_rejected: "Rejected after practice",
    reopened: "Reopened",
    training_ready: "Ready for practice",
    withdrawn: "Withdrawn",
  };
  return labels[normalized] || asString(value) || "Updated";
}

export function formatCandidateEventNote(value: unknown) {
  const note = asString(value);
  if (!note) return "";
  if (note.toLowerCase() === "manual stage correction.") {
    return "";
  }
  return note;
}


export function daysSince(iso: string): number | null {
  if (!iso) return null;
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return null;
  return Math.floor((Date.now() - parsed) / 86_400_000);
}

// Derived training stats for one candidate, used by the table and detail view.
export function trainingMeta(candidate: Candidate) {
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

export function criterionAverages(history: Array<Record<string, unknown>>) {
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
