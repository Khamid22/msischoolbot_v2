import { useState, useEffect, useMemo, useRef } from "react";
import type { FormEvent, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import {
  ArrowRight,
  BookMarked,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock,
  Layers,
  Plus,
  RotateCcw,
  Search,
  Users,
  UserX,
  X,
} from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, AdminTab, normalizeSubjectKey } from "../shared";

function FieldLabel({ children }: { children: string }) {
  return (
    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}

function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-foreground/10 bg-muted px-2 text-xs font-semibold text-muted-foreground">
      {children}
    </span>
  );
}

function MiniMetric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-lg font-bold leading-none">{value}</p>
    </div>
  );
}

const subjectSwatches = [
  "bg-primary",
  "bg-info",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-violet-500",
] as const;

function subjectSwatch(value: string) {
  const seed = Array.from(value || "group").reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return subjectSwatches[seed % subjectSwatches.length];
}

const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const timetableStartHour = 8;
const timetableEndHour = 22;

function dateFromIso(value: string) {
  const [year, month, day] = value.split("-").map((part) => Number(part));
  if (!year || !month || !day) return new Date();
  return new Date(year, month - 1, day);
}

function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfWeek(date: Date) {
  const next = new Date(date);
  const weekday = (next.getDay() + 6) % 7;
  next.setDate(next.getDate() - weekday);
  next.setHours(0, 0, 0, 0);
  return next;
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function formatWeekRange(weekStart: Date) {
  const end = addDays(weekStart, 6);
  const fmt = new Intl.DateTimeFormat("en", { month: "short", day: "numeric" });
  return `${fmt.format(weekStart)} - ${fmt.format(end)}, ${end.getFullYear()}`;
}

function timeToMinutes(value: string) {
  const [hour, minute] = value.split(":").map((part) => Number(part));
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return timetableStartHour * 60;
  return hour * 60 + minute;
}

function formatSessionTime(start: string, end: string) {
  return `${start || "--:--"}-${end || "--:--"}`;
}

function hasUsableLessonDate(value: unknown) {
  const text = asString(value);
  return Boolean(text && /\d/.test(text));
}

function lessonDateToIso(value: unknown) {
  const text = asString(value);
  if (!hasUsableLessonDate(text)) return "";
  const isoMatch = text.match(/^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$/);
  if (isoMatch) {
    const year = Number(isoMatch[1]);
    const month = Number(isoMatch[2]);
    const day = Number(isoMatch[3]);
    if (year && month && day) {
      return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    }
  }
  const numericMatch = text.match(/^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?$/);
  if (numericMatch) {
    const day = Number(numericMatch[1]);
    const month = Number(numericMatch[2]);
    const yearToken = asString(numericMatch[3]);
    const year = yearToken ? (yearToken.length <= 2 ? 2000 + Number(yearToken) : Number(yearToken)) : new Date().getFullYear();
    if (year && month && day) {
      return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    }
  }
  const parsed = new Date(text);
  if (!Number.isNaN(parsed.getTime())) return isoDate(parsed);
  return "";
}

function isCancelledText(value: unknown) {
  const text = asString(value).toLowerCase();
  return text.includes("cancelled") || text.includes("canceled");
}

function lessonStatus(lesson: LessonHistoryRow) {
  return isCancelledText(lesson.lesson_number) || isCancelledText(lesson.lesson_topic) ? "cancelled" : "completed";
}

function sessionTone(status: unknown) {
  const normalized = asString(status).toLowerCase();
  if (normalized === "cancelled" || normalized === "canceled") {
    return { label: "Cancelled", className: "border-red-500/35 bg-red-600 text-white" };
  }
  if (normalized === "completed" || normalized === "complete" || normalized === "done" || normalized === "accomplished") {
    return { label: "Completed", className: "border-emerald-500/35 bg-emerald-600 text-white" };
  }
  return { label: "Scheduled", className: "border-foreground/10 bg-foreground text-background" };
}

function subjectCode(value: unknown) {
  const subject = asString(value).toLowerCase();
  if (subject.includes("math")) return "Math";
  if (subject.includes("english") || subject.includes("eng")) return "Eng";
  if (subject.includes("chem")) return "Chem";
  return asString(value).slice(0, 4) || "Subj";
}

function subjectColorClass(value: unknown, status: "scheduled" | "completed" | "cancelled") {
  if (status === "cancelled") return "border-red-500/35 bg-red-600 text-white";
  const subject = asString(value).toLowerCase();
  if (status === "completed") {
    if (subject.includes("math")) return "border-emerald-500/35 bg-emerald-600 text-white";
    if (subject.includes("english") || subject.includes("eng")) return "border-sky-500/35 bg-sky-600 text-white";
    if (subject.includes("chem")) return "border-violet-500/35 bg-violet-600 text-white";
    return "border-emerald-500/35 bg-emerald-600 text-white";
  }
  if (subject.includes("math")) return "border-blue-500/35 bg-blue-600 text-white";
  if (subject.includes("english") || subject.includes("eng")) return "border-amber-500/35 bg-amber-500 text-white";
  if (subject.includes("chem")) return "border-violet-500/35 bg-violet-600 text-white";
  return "border-foreground/10 bg-foreground text-background";
}

function school5LessonTime(lesson: LessonHistoryRow) {
  const school = asString(lesson.school_code).toLowerCase();
  if (school !== "school5" && school !== "school 5") return null;

  const group = asString(lesson.group_name).replace(/\s+/g, "").toUpperCase();
  const subject = asString(lesson.subject_name).toLowerCase();

  if (subject.includes("math")) {
    if (group === "MG1" || group === "MMG1") return { start_time: "08:00", end_time: "09:20" };
    if (group === "MG2" || group === "MMG2") return { start_time: "14:00", end_time: "15:20" };
  }

  if (subject.includes("english") || subject.includes("eng")) {
    if (group === "MG1" || group === "ENGMG1") return { start_time: "08:00", end_time: "09:20" };
    if (group === "AFT1" || group === "ENGAFT1") return { start_time: "14:00", end_time: "15:20" };
  }

  return null;
}

function scheduleWeekdays(value: unknown) {
  return asString(value)
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item >= 0 && item <= 6);
}

function scheduleTimeForLesson(lesson: LessonHistoryRow, schedules: ScheduleRow[]) {
  const lessonDate = lessonDateToIso(lesson.lesson_date);
  if (!lessonDate) return null;
  const lessonDay = dateFromIso(lessonDate);
  const weekday = (lessonDay.getDay() + 6) % 7;
  const matchingSchedule = schedules.find((schedule) => {
    if (asString(schedule.status).toLowerCase() === "cancelled") return false;
    if (String(schedule.group_id) !== String(lesson.group_id)) return false;
    if (lessonDate < asString(schedule.start_date) || lessonDate > asString(schedule.end_date)) return false;
    const weekdays = scheduleWeekdays(schedule.weekdays);
    return weekdays.length === 0 || weekdays.includes(weekday);
  });
  if (matchingSchedule) {
    return {
      start_time: asString(matchingSchedule.start_time),
      end_time: asString(matchingSchedule.end_time),
    };
  }
  return school5LessonTime(lesson);
}

function sameSubjectName(left: unknown, right: unknown) {
  return normalizeSubjectKey(left) === normalizeSubjectKey(right);
}

type Lesson = {
  id: number;
  lessonNumber: string;
  topic: string;
  date: string;
  order: number;
};

type Enrollment = {
  enrollmentId: number;
  publicDashboardId?: number;
  fullName: string;
  averageGrade: number;
  coins: number;
  active?: boolean;
  status?: string;
  disqualificationReason?: string;
  disqualifiedAt?: string;
  attendance: Record<string, string>;
  homework: Record<string, number>;
  exams?: Record<string, number>;
};

type GradebookData = {
  group: { id: number; name: string; subjectName: string; schoolCode: string };
  lessons: Lesson[];
  enrollments: Enrollment[];
  examLabels?: string[];
  allEnrollments?: Enrollment[];
};

type ScheduleRow = {
  id: number;
  group_id: number;
  group_name: string;
  subject_name: string;
  school_code: string;
  teacher_id?: number;
  teacher_name?: string;
  weekdays: string;
  start_time: string;
  end_time: string;
  start_date: string;
  end_date: string;
  room?: string;
  online_url?: string;
  title?: string;
  status?: string;
};

type SessionRow = {
  id: number;
  schedule_id: number;
  group_id: number;
  group_name: string;
  subject_name: string;
  school_code: string;
  teacher_id?: number;
  teacher_name?: string;
  session_date: string;
  start_time: string;
  end_time: string;
  room?: string;
  online_url?: string;
  status?: string;
};

type LessonHistoryRow = {
  id: number;
  school_id: number;
  subject_id: number;
  group_id: number;
  school_code: string;
  subject_name: string;
  group_name: string;
  lesson_number: string;
  lesson_topic: string;
  lesson_date: string;
  lesson_order: number;
};

type TimetableSession = SessionRow & {
  lane: number;
  laneCount: number;
};

type TimetableLessonBlock = {
  id: string;
  group_id: number;
  group_name: string;
  subject_name: string;
  lesson_number?: string;
  lesson_topic?: string;
  teacher_name?: string;
  session_date: string;
  start_time: string;
  end_time: string;
  status: "scheduled" | "completed" | "cancelled";
  // Stacked-row layout: overlapping classes share a time band and stack as
  // full-width rows (row index within rowCount) instead of cramped columns.
  row: number;
  rowCount: number;
  bandStartMin: number;
  bandEndMin: number;
};

type RawTimetableBlock = Omit<TimetableLessonBlock, "row" | "rowCount" | "bandStartMin" | "bandEndMin">;

function layoutSessionsForDay(sessionsForDay: RawTimetableBlock[]): TimetableLessonBlock[] {
  const sorted = [...sessionsForDay].sort((a, b) => {
    const startDiff = timeToMinutes(asString(a.start_time)) - timeToMinutes(asString(b.start_time));
    if (startDiff !== 0) return startDiff;
    return timeToMinutes(asString(a.end_time)) - timeToMinutes(asString(b.end_time));
  });
  const output: TimetableLessonBlock[] = [];
  let cluster: RawTimetableBlock[] = [];
  let clusterEnd = -1;

  function flushCluster() {
    if (cluster.length === 0) return;
    // Every overlapping class is shown as a full-width row within the shared band.
    const bandStartMin = Math.min(...cluster.map((session) => timeToMinutes(asString(session.start_time))));
    const bandEndMin = Math.max(...cluster.map((session) => timeToMinutes(asString(session.end_time))));
    const rowCount = cluster.length;
    cluster.forEach((session, index) => {
      output.push({ ...session, row: index, rowCount, bandStartMin, bandEndMin });
    });
    cluster = [];
    clusterEnd = -1;
  }

  sorted.forEach((session) => {
    const start = timeToMinutes(asString(session.start_time));
    const end = timeToMinutes(asString(session.end_time));
    if (cluster.length > 0 && start >= clusterEnd) flushCluster();
    cluster.push(session);
    clusterEnd = Math.max(clusterEnd, end);
  });
  flushCluster();
  return output;
}

type ActiveCell = {
  enrollmentId: number;
  lesson: Lesson;
  kind: "att" | "hw";
  anchorRect: DOMRect;
};

const ATT_VALUES = ["present", "absent", "justified"] as const;
type AttValue = (typeof ATT_VALUES)[number] | "";

function attLabel(v: string) {
  if (v === "present") return "P";
  if (v === "absent") return "A";
  if (v === "justified") return "J";
  return "";
}

function attCls(v: string) {
  if (v === "present") return "bg-emerald-500 text-white";
  if (v === "absent") return "bg-red-500 text-white";
  if (v === "justified") return "bg-amber-400 text-white";
  return "";
}

function EnrollmentList({
  title,
  icon,
  rows,
  emptyText,
  actionLabel,
  actionIcon,
  actionTone,
  savingId,
  onAction,
}: {
  title: string;
  icon: ReactNode;
  rows: Enrollment[];
  emptyText: string;
  actionLabel: string;
  actionIcon: ReactNode;
  actionTone: "danger" | "neutral";
  savingId: number | null;
  onAction: (enrollmentId: number) => void;
}) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background">
      <div className="flex items-center justify-between border-b border-foreground/8 px-3 py-2">
        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
          {icon}
          {title}
        </span>
        <span className="text-xs font-semibold text-muted-foreground">{rows.length}</span>
      </div>
      <div className="max-h-64 overflow-y-auto p-2">
        {rows.length === 0 ? (
          <p className="px-2 py-4 text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <div className="space-y-1.5">
            {rows.map((row) => (
              <div
                key={row.enrollmentId}
                className="flex items-center justify-between gap-3 rounded-lg border border-foreground/5 bg-surface px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{row.fullName}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    ID {row.publicDashboardId || row.enrollmentId}
                    {row.disqualificationReason ? ` · ${row.disqualificationReason}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={savingId === row.enrollmentId}
                  onClick={() => onAction(row.enrollmentId)}
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-bold disabled:opacity-50 ${
                    actionTone === "danger"
                      ? "bg-red-50 text-red-700 hover:bg-red-100"
                      : "bg-muted text-muted-foreground hover:bg-foreground/10"
                  }`}
                >
                  {actionIcon}
                  {savingId === row.enrollmentId ? "Saving" : actionLabel}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function GroupGradebook({
  groupId,
  csrf,
  groups,
  onClose,
}: {
  groupId: number;
  csrf: string;
  groups: Array<Record<string, unknown>>;
  onClose: () => void;
}) {
  const [data, setData] = useState<GradebookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState<ActiveCell | null>(null);
  const [hwInput, setHwInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [enrollmentSearch, setEnrollmentSearch] = useState("");
  const [statusSavingId, setStatusSavingId] = useState<number | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<Enrollment | null>(null);
  const [moveGroupId, setMoveGroupId] = useState("");
  const [moveSaving, setMoveSaving] = useState(false);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    load(groupId, controller.signal);
    return () => controller.abort();
  }, [groupId]);

  useEffect(() => {
    if (!active) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [active]);

  async function load(id: number, signal?: AbortSignal) {
    setLoading(true);
    setError("");
    setActive(null);
    try {
      const res = await fetch(routes.adminAcademicGradebookApi(id), { signal });
      const json = await res.json();
      if (json.ok) setData(json as GradebookData);
      else setError(json.message || "Failed to load.");
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }

  function openCell(
    e: React.MouseEvent<HTMLButtonElement>,
    enrollmentId: number,
    lesson: Lesson,
    kind: "att" | "hw",
    currentHw: number | undefined,
  ) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setActive({ enrollmentId, lesson, kind, anchorRect: rect });
    setHwInput(currentHw !== undefined ? String(currentHw) : "");
  }

  function close() {
    setActive(null);
    setSaving(false);
  }

  async function saveAtt(status: AttValue) {
    if (!active || saving) return;
    setSaving(true);
    try {
      await fetch(routes.adminAcademicAttendanceApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_label: active.lesson.lessonNumber,
          status: status || "present",
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          attendance_type: "regular",
        }),
      });
      patchAtt(active.enrollmentId, active.lesson.lessonNumber, status);
      close();
    } finally {
      setSaving(false);
    }
  }

  async function saveHw() {
    if (!active || saving || hwInput === "") return;
    const score = parseFloat(hwInput);
    if (isNaN(score)) return;
    setSaving(true);
    try {
      await fetch(routes.adminAcademicHomeworkApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_label: active.lesson.lessonNumber,
          score,
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          score_type: "Homework",
        }),
      });
      patchHw(active.enrollmentId, active.lesson.lessonNumber, score);
      close();
    } finally {
      setSaving(false);
    }
  }

  function patchAtt(enrollmentId: number, lessonNumber: string, status: AttValue) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) => {
          if (en.enrollmentId !== enrollmentId) return en;
          const att = { ...en.attendance };
          if (status) att[lessonNumber] = status;
          else delete att[lessonNumber];
          return { ...en, attendance: att };
        }),
      };
    });
  }

  function patchHw(enrollmentId: number, lessonNumber: string, score: number) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) =>
          en.enrollmentId !== enrollmentId
            ? en
            : { ...en, homework: { ...en.homework, [lessonNumber]: score } },
        ),
      };
    });
  }

  async function updateEnrollmentStatus(enrollmentId: number, status: "active" | "disqualified" | "banned") {
    if (statusSavingId) return;
    let reason = "";
    if (status === "disqualified") {
      reason = window.prompt("Reason for disqualification?", "") || "";
    }
    setStatusSavingId(enrollmentId);
    try {
      const res = await fetch(routes.adminAcademicEnrollmentStatusApi(enrollmentId), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ status, reason }),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Unable to update enrollment.");
        return;
      }
      setSelectedStudent(null);
      await load(groupId);
    } catch {
      setError("Network error.");
    } finally {
      setStatusSavingId(null);
    }
  }

  async function moveEnrollment(enrollmentId: number) {
    if (!moveGroupId || moveSaving) return;
    setMoveSaving(true);
    setError("");
    try {
      const res = await fetch(routes.adminAcademicEnrollmentGroupApi(enrollmentId), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ group_id: Number(moveGroupId) }),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Unable to move student.");
        return;
      }
      setSelectedStudent(null);
      setMoveGroupId("");
      await load(groupId);
    } catch {
      setError("Network error.");
    } finally {
      setMoveSaving(false);
    }
  }

  const lessons = data?.lessons ?? [];
  const examLabels = data?.examLabels ?? [];
  const enrollments = data?.enrollments ?? [];
  const allEnrollments = data?.allEnrollments ?? enrollments;
  const disqualifiedEnrollments = allEnrollments.filter((en) => en.status === "disqualified");
  const bannedEnrollments = allEnrollments.filter((en) => en.status === "banned");
  const removedEnrollments = allEnrollments.filter((en) => en.status === "disqualified" || en.status === "banned");
  const enrollmentQuery = enrollmentSearch.trim().toLowerCase();
  const visibleAllEnrollments = allEnrollments.filter((en) => {
    if (!enrollmentQuery) return true;
    return `${en.fullName} ${en.publicDashboardId || ""}`.toLowerCase().includes(enrollmentQuery);
  });
  const visibleActiveEnrollments = visibleAllEnrollments.filter((en) => en.status !== "disqualified" && en.status !== "banned");
  const visibleRemovedEnrollments = visibleAllEnrollments.filter((en) => en.status === "disqualified" || en.status === "banned");

  const popTop = active
    ? Math.min(active.anchorRect.bottom + 4, window.innerHeight - 200)
    : 0;
  const popLeft = active
    ? Math.min(active.anchorRect.left, window.innerWidth - 220)
    : 0;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-foreground/10 bg-surface px-4 py-3">
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1 rounded-lg border border-foreground/10 px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Groups
          </button>
          {data && (
            <span className="text-sm font-bold">
              {data.group.name}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {data.group.subjectName} · {data.group.schoolCode}
              </span>
            </span>
          )}
          {data && (
            <span className="text-xs text-muted-foreground">
              {enrollments.length} active · {disqualifiedEnrollments.length} disqualified · {bannedEnrollments.length} banned · {lessons.length} lessons · {examLabels.length} exams
            </span>
          )}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-emerald-500 text-[9px] font-bold text-white">P</span> Present
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-red-500 text-[9px] font-bold text-white">A</span> Absent
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-amber-400 text-[9px] font-bold text-white">J</span> Justified
            </span>
          </div>
        </div>
      </div>

      {data && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-end gap-3">
            <label className="relative block w-full sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="search"
                value={enrollmentSearch}
                onChange={(event) => setEnrollmentSearch(event.target.value)}
                placeholder="Search students"
                className="h-9 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
              />
            </label>
          </div>
          <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface">
            <div className="max-h-64 overflow-auto">
              <table className="w-full min-w-[760px] text-left text-xs">
                <thead className="sticky top-0 z-20 bg-surface text-[10px] font-bold uppercase tracking-wider text-muted-foreground shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                  <tr>
                    <th className="px-3 py-2">Student</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-center">AAP</th>
                    <th className="px-3 py-2 text-center">Exams</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-foreground/5">
                  {visibleActiveEnrollments.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-sm text-muted-foreground">No students found.</td>
                    </tr>
                  ) : (
                    visibleActiveEnrollments.map((row) => {
                      const isBanned = row.status === "banned";
                      const examCount = Object.keys(row.exams || {}).length;
                      return (
                        <tr
                          key={row.enrollmentId}
                          className="cursor-pointer hover:bg-foreground/[0.025]"
                          onClick={() => {
                            setSelectedStudent(row);
                            setMoveGroupId("");
                          }}
                        >
                          <td className="px-3 py-2">
                            <p className="font-semibold">{row.fullName}</p>
                            <p className="text-[11px] text-muted-foreground">ID {row.publicDashboardId || row.enrollmentId}</p>
                          </td>
                          <td className="px-3 py-2">
                            <span className={`rounded-md px-2 py-1 text-[10px] font-bold uppercase ${isBanned ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
                              {isBanned ? "Banned" : "Active"}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-center font-bold">{row.averageGrade > 0 ? row.averageGrade.toFixed(0) : "-"}</td>
                          <td className="px-3 py-2 text-center font-bold">{examCount}</td>
                          <td className="px-3 py-2 text-right">
                            <button
                              type="button"
                              disabled={statusSavingId === row.enrollmentId}
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedStudent(row);
                                setMoveGroupId("");
                              }}
                              className="rounded-lg bg-muted px-2.5 py-1.5 text-xs font-bold text-muted-foreground hover:bg-foreground/10 disabled:opacity-50"
                            >
                              Manage
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
          {removedEnrollments.length > 0 ? (
            <div className="overflow-hidden rounded-xl border border-red-200 bg-red-50/45">
              <div className="border-b border-red-200 px-3 py-2">
                <p className="text-xs font-bold uppercase tracking-wide text-red-700">Disqualified / banned students</p>
              </div>
              <div className="max-h-56 overflow-auto">
                <table className="w-full min-w-[640px] text-left text-xs">
                  <thead className="sticky top-0 z-20 bg-red-50 text-[10px] font-bold uppercase tracking-wider text-red-700 shadow-[0_1px_0_rgba(185,28,28,0.18)]">
                    <tr>
                      <th className="px-3 py-2">Student</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Reason</th>
                      <th className="px-3 py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-red-200/70">
                    {visibleRemovedEnrollments.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-3 py-6 text-center text-sm text-red-700/70">No removed students match the search.</td>
                      </tr>
                    ) : (
                      visibleRemovedEnrollments.map((row) => (
                        <tr
                          key={`${row.enrollmentId}-removed`}
                          className="cursor-pointer hover:bg-red-100/50"
                          onClick={() => {
                            setSelectedStudent(row);
                            setMoveGroupId("");
                          }}
                        >
                          <td className="px-3 py-2">
                            <p className="font-semibold text-red-950">{row.fullName}</p>
                            <p className="text-[11px] text-red-700/75">ID {row.publicDashboardId || row.enrollmentId}</p>
                          </td>
                          <td className="px-3 py-2">
                            <span className="rounded-md bg-red-100 px-2 py-1 text-[10px] font-bold uppercase text-red-700">
                              {row.status === "banned" ? "Banned" : "Disqualified"}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-red-800/80">{row.disqualificationReason || "-"}</td>
                          <td className="px-3 py-2 text-right">
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setSelectedStudent(row);
                                setMoveGroupId("");
                              }}
                              className="rounded-lg bg-white px-2.5 py-1.5 text-xs font-bold text-red-700 hover:bg-red-100"
                            >
                              Manage
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </div>
      )}
      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : loading ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">Loading…</div>
      ) : data && lessons.length === 0 ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">No lessons found for this group.</div>
      ) : null}

      {data && examLabels.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface">
          <div className="border-b border-foreground/8 px-4 py-3">
            <p className="text-sm font-bold">Exam Results</p>
            <p className="text-xs text-muted-foreground">Taken exam scores stored for this group.</p>
          </div>
          <div className="max-h-72 overflow-auto">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead className="sticky top-0 z-20 bg-muted/40 text-[10px] font-bold uppercase tracking-wider text-muted-foreground shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr>
                  <th className="sticky left-0 z-30 min-w-[200px] border-r border-foreground/8 bg-muted/40 px-3 py-2">Student</th>
                  {examLabels.map((label) => (
                    <th key={label} className="min-w-[92px] border-l border-foreground/8 px-3 py-2 text-center">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-foreground/5">
                {enrollments.map((en) => (
                  <tr key={`${en.enrollmentId}-exams`}>
                    <td className="sticky left-0 z-10 border-r border-foreground/8 bg-surface px-3 py-2 font-semibold">
                      {en.fullName}
                    </td>
                    {examLabels.map((label) => {
                      const score = en.exams?.[label];
                      return (
                        <td key={`${en.enrollmentId}-${label}`} className="border-l border-foreground/5 px-3 py-2 text-center">
                          <span className={`inline-flex min-w-8 justify-center rounded-md px-2 py-1 font-bold ${score !== undefined ? "bg-blue-50 text-blue-700" : "text-foreground/25"}`}>
                            {score !== undefined ? score : "-"}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {data && lessons.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface">
          <div className="max-h-[70dvh] overflow-auto">
            <table className="min-w-full border-collapse text-left text-xs">
              <thead className="sticky top-0 z-30 shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                <tr className="bg-surface">
                  <th rowSpan={2} className="sticky left-0 z-40 min-w-[180px] border-b border-r border-foreground/10 bg-surface px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                    Student
                  </th>
                  <th rowSpan={2} className="sticky left-[180px] z-40 min-w-[48px] border-b border-r border-foreground/10 bg-surface px-2 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                    AAP
                  </th>
                  {lessons.map((lesson) => (
                    <th key={lesson.id} colSpan={2} className="min-w-[104px] border-l border-foreground/10 p-0 text-center align-top">
                      <div
                        title={`${lesson.lessonNumber} - ${lesson.topic}`}
                        className="w-full px-2 py-2"
                      >
                        <span className="block whitespace-nowrap text-[10px] font-semibold leading-tight text-muted-foreground">
                          {lesson.date || lesson.lessonNumber}
                        </span>
                        <span className="block whitespace-nowrap text-[9px] font-semibold text-muted-foreground/70">
                          {lesson.lessonNumber}
                        </span>
                        <span className="mt-1 block whitespace-normal break-words text-[9px] font-normal italic leading-tight text-muted-foreground/70">
                          {lesson.topic || "—"}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
                <tr className="bg-surface">
                  {lessons.map((lesson) => (
                    <>
                      <th key={`${lesson.id}-att`} className="w-[28px] border-b border-t border-l border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70">Att</th>
                      <th key={`${lesson.id}-hw`} className="w-[36px] border-b border-t border-r border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70">HW</th>
                    </>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-foreground/5">
                {enrollments.map((en) => (
                  <tr key={en.enrollmentId} className="hover:bg-foreground/[0.015]">
                    <td className="sticky left-0 z-20 border-r border-foreground/8 bg-surface px-3 py-1 font-semibold text-sm shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                      {en.fullName}
                    </td>
                    <td className="sticky left-[180px] z-20 border-r border-foreground/8 bg-surface px-2 py-1 text-center font-bold text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                      {en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}
                    </td>
                    {lessons.map((lesson) => {
                      const att = (en.attendance[lesson.lessonNumber] || "") as AttValue;
                      const hw = en.homework[lesson.lessonNumber];
                      const isActiveAtt = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "att";
                      const isActiveHw = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "hw";
                      return (
                        <>
                          <td key={`${lesson.id}-att`} className="border-l border-foreground/5 p-0 text-center">
                            <button
                              type="button"
                              onClick={(e) => openCell(e, en.enrollmentId, lesson, "att", hw)}
                              title={`${en.fullName} · ${lesson.lessonNumber} · attendance`}
                              className={`h-[26px] w-[28px] rounded text-[10px] font-bold transition-opacity hover:opacity-75 ${att ? attCls(att) : "text-foreground/20"} ${isActiveAtt ? "ring-1 ring-foreground/40" : ""}`}
                            >
                              {att ? attLabel(att) : "·"}
                            </button>
                          </td>
                          <td key={`${lesson.id}-hw`} className="border-r border-foreground/5 p-0 text-center">
                            <button
                              type="button"
                              onClick={(e) => openCell(e, en.enrollmentId, lesson, "hw", hw)}
                              title={`${en.fullName} · ${lesson.lessonNumber} · homework`}
                              className={`h-[26px] w-[36px] rounded text-[10px] transition-opacity hover:opacity-75 ${hw !== undefined ? "font-bold text-blue-600" : "text-foreground/20"} ${isActiveHw ? "ring-1 ring-foreground/40" : ""}`}
                            >
                              {hw !== undefined ? hw : "·"}
                            </button>
                          </td>
                        </>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedStudent ? (
        <div className="fixed inset-0 z-50 bg-foreground/45" onClick={() => setSelectedStudent(null)}>
          <aside
            className="ml-auto flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate text-base font-bold">{selectedStudent.fullName}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  ID {selectedStudent.publicDashboardId || selectedStudent.enrollmentId} · {selectedStudent.status === "banned" ? "Banned" : selectedStudent.status === "disqualified" ? "Disqualified" : "Active"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedStudent(null)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
                aria-label="Close student actions"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              <div className="grid grid-cols-3 gap-2">
                <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="AAP" value={selectedStudent.averageGrade > 0 ? selectedStudent.averageGrade.toFixed(0) : "-"} />
                <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="Exams" value={Object.keys(selectedStudent.exams || {}).length} />
                <MiniMetric icon={<Users className="h-3.5 w-3.5" />} label="Coins" value={selectedStudent.coins || 0} />
              </div>

              <div className="rounded-xl border border-foreground/8 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Student actions</p>
                <div className="mt-3 grid gap-2">
                  <button
                    type="button"
                    disabled={statusSavingId === selectedStudent.enrollmentId}
                    onClick={() => updateEnrollmentStatus(selectedStudent.enrollmentId, selectedStudent.status === "banned" ? "active" : "banned")}
                    className="inline-flex items-center justify-center rounded-lg border border-foreground/10 px-3 py-2 text-sm font-bold hover:bg-muted disabled:opacity-50"
                  >
                    {statusSavingId === selectedStudent.enrollmentId
                      ? "Saving..."
                      : selectedStudent.status === "banned"
                        ? "Unban student"
                        : "Ban student"}
                  </button>
                  <button
                    type="button"
                    disabled={statusSavingId === selectedStudent.enrollmentId}
                    onClick={() => updateEnrollmentStatus(selectedStudent.enrollmentId, selectedStudent.status === "disqualified" ? "active" : "disqualified")}
                    className={`inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-bold disabled:opacity-50 ${
                      selectedStudent.status === "disqualified"
                        ? "bg-muted text-muted-foreground hover:bg-foreground/10"
                        : "bg-red-50 text-red-700 hover:bg-red-100"
                    }`}
                  >
                    {statusSavingId === selectedStudent.enrollmentId
                      ? "Saving..."
                      : selectedStudent.status === "disqualified"
                        ? "Restore qualification"
                        : "Disqualify"}
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-foreground/8 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Move to another group</p>
                <div className="mt-3 space-y-2">
                  <Select value={moveGroupId} onChange={(event) => setMoveGroupId(event.target.value)}>
                    <option value="">Choose target group</option>
                    {groups
                      .filter((group) => asNumber(group.id) !== groupId)
                      .map((group) => (
                        <option key={asNumber(group.id)} value={asString(group.id)}>
                          {asString(group.name)} · {asString(group.subject_name)} · {asString(group.school_code)}
                        </option>
                      ))}
                  </Select>
                  <button
                    type="button"
                    disabled={!moveGroupId || moveSaving}
                    onClick={() => moveEnrollment(selectedStudent.enrollmentId)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-bold text-primary-foreground disabled:opacity-50"
                  >
                    <Layers className="h-4 w-4" />
                    {moveSaving ? "Moving..." : "Move student"}
                  </button>
                </div>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
      {active && (
        <div
          ref={popRef}
          style={{ position: "fixed", top: popTop, left: popLeft, zIndex: 9999 }}
          className="w-52 rounded-xl border border-foreground/10 bg-surface shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-foreground/8 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-bold">{active.lesson.lessonNumber}</p>
              <p className="truncate text-[10px] text-muted-foreground">{active.lesson.topic}</p>
              {active.lesson.date && <p className="text-[10px] text-muted-foreground">{active.lesson.date}</p>}
            </div>
            <button type="button" onClick={close} className="ml-2 shrink-0 rounded p-0.5 hover:bg-muted">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
          <div className="p-3">
            {active.kind === "att" ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Attendance</p>
                <div className="grid grid-cols-4 gap-1">
                  {(["present", "absent", "justified", ""] as AttValue[]).map((v) => {
                    const lbl = v ? attLabel(v) : "–";
                    const cls = v ? attCls(v) : "bg-muted text-muted-foreground";
                    const currentAtt = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)?.attendance[active.lesson.lessonNumber] ?? "";
                    return (
                      <button
                        key={v}
                        type="button"
                        disabled={saving}
                        onClick={() => saveAtt(v as AttValue)}
                        className={`inline-flex min-h-[40px] items-center justify-center rounded py-1.5 text-xs font-bold transition-opacity disabled:opacity-50 ${cls} ${currentAtt === v ? "ring-2 ring-foreground/30 ring-offset-1" : ""}`}
                      >
                        {lbl}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Homework Score</p>
                {(() => {
                  const curHw = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)?.homework[active.lesson.lessonNumber];
                  return curHw !== undefined ? (
                    <p className="text-[10px] text-muted-foreground">Current: <span className="font-bold text-foreground">{curHw}</span></p>
                  ) : null;
                })()}
                <div className="flex gap-2">
                  <input
                    autoFocus
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    value={hwInput}
                    onChange={(e) => setHwInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveHw()}
                    placeholder="0–100"
                    className="w-full rounded-lg border border-foreground/10 bg-background px-2 py-1.5 text-sm outline-none focus:border-foreground/30"
                  />
                  <button
                    type="button"
                    disabled={saving || hwInput === ""}
                    onClick={saveHw}
                    className="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

function SchedulePanel({ state }: { state: any }) {
  const props = state.props || {};
  const csrf: string = asString(props.csrfToken);
  const isTeacherMode = asString(state.adminMode).toLowerCase() === "teacher";
  const groups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const teachers = Array.isArray(props.adminTeachers) ? props.adminTeachers : [];
  const initialSchedules = Array.isArray(props.adminAcademicSchedules) ? props.adminAcademicSchedules : [];
  const initialSessions = Array.isArray(props.adminAcademicSessions) ? props.adminAcademicSessions : [];
  const initialLessons = Array.isArray(props.adminAcademicLessons) ? props.adminAcademicLessons : [];
  const [schedules, setSchedules] = useState<ScheduleRow[]>(initialSchedules as ScheduleRow[]);
  const [sessions, setSessions] = useState<SessionRow[]>(initialSessions as SessionRow[]);
  const [lessons, setLessons] = useState<LessonHistoryRow[]>(initialLessons as LessonHistoryRow[]);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const today = isoDate(new Date());
  const [form, setForm] = useState({
    groupId: asString(groups[0]?.id),
    teacherId: "",
    title: "",
    weekdays: ["1", "3"],
    startTime: "17:00",
    endTime: "18:30",
    startDate: today,
    endDate: isoDate(addDays(new Date(), 60)),
    room: "",
    onlineUrl: "",
  });

  useEffect(() => {
    setSchedules(initialSchedules as ScheduleRow[]);
    setSessions(initialSessions as SessionRow[]);
    setLessons(initialLessons as LessonHistoryRow[]);
  }, [props.adminAcademicSchedules, props.adminAcademicSessions, props.adminAcademicLessons]);

  const weekDays = useMemo(() => Array.from({ length: 7 }, (_item, index) => addDays(weekStart, index)), [weekStart]);
  const weekDateSet = useMemo(() => new Set(weekDays.map(isoDate)), [weekDays]);
  const subjectOptions = useMemo(() => {
    const seen = new Set<string>();
    return groups
      .map((group: Record<string, unknown>) => asString(group.subject_name))
      .filter((subject: string) => {
        const key = normalizeSubjectKey(subject);
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .sort((left: string, right: string) => left.localeCompare(right));
  }, [groups]);
  const filteredSessions = useMemo(
    () =>
      sessions.filter((session) => {
        if (!weekDateSet.has(asString(session.session_date))) return false;
        if (subjectFilter !== "all" && !sameSubjectName(session.subject_name, subjectFilter)) return false;
        return true;
      }),
    [sessions, weekDateSet, subjectFilter],
  );
  const recordedLessons = useMemo(
    () =>
      lessons.filter((lesson) => {
        const lessonDate = lessonDateToIso(lesson.lesson_date);
        if (!lessonDate || !weekDateSet.has(lessonDate)) return false;
        if (asString(lesson.lesson_number).startsWith("S")) return false;
        if (subjectFilter !== "all" && !sameSubjectName(lesson.subject_name, subjectFilter)) return false;
        return true;
      }),
    [lessons, weekDateSet, subjectFilter],
  );
  const timedHistoryBlocks = useMemo(
    () =>
      recordedLessons.flatMap((lesson): RawTimetableBlock[] => {
        const inferredTime = scheduleTimeForLesson(lesson, schedules);
        const lessonDate = lessonDateToIso(lesson.lesson_date);
        if (!inferredTime || !lessonDate) return [];
        return [
          {
            id: `lesson-${lesson.id}`,
            group_id: Number(lesson.group_id),
            group_name: asString(lesson.group_name),
            subject_name: asString(lesson.subject_name),
            lesson_number: asString(lesson.lesson_number),
            lesson_topic: asString(lesson.lesson_topic),
            session_date: lessonDate,
            start_time: inferredTime.start_time,
            end_time: inferredTime.end_time,
            status: lessonStatus(lesson),
          },
        ];
      }),
    [recordedLessons, schedules],
  );
  const untimedLessons = useMemo(
    () => recordedLessons.filter((lesson) => !scheduleTimeForLesson(lesson, schedules)),
    [recordedLessons, schedules],
  );
  const scheduledBlocks = useMemo(
    () =>
      filteredSessions.map((session): RawTimetableBlock => {
        const normalizedStatus = asString(session.status).toLowerCase();
        const status = normalizedStatus === "cancelled" || normalizedStatus === "canceled"
          ? "cancelled"
          : normalizedStatus === "completed" || normalizedStatus === "complete" || normalizedStatus === "done" || normalizedStatus === "accomplished"
            ? "completed"
            : "scheduled";
        return {
          id: `session-${session.id}`,
          group_id: Number(session.group_id),
          group_name: asString(session.group_name),
          subject_name: asString(session.subject_name),
          teacher_name: asString(session.teacher_name),
          session_date: asString(session.session_date),
          start_time: asString(session.start_time),
          end_time: asString(session.end_time),
          status,
        };
      }),
    [filteredSessions],
  );
  const timetableBlocks = useMemo(
    () => [...scheduledBlocks, ...timedHistoryBlocks],
    [scheduledBlocks, timedHistoryBlocks],
  );
  const completedLessonCount = recordedLessons.filter((lesson) => lessonStatus(lesson) === "completed").length;
  const cancelledLessonCount = recordedLessons.filter((lesson) => lessonStatus(lesson) === "cancelled").length
    + filteredSessions.filter((session) => ["cancelled", "canceled"].includes(asString(session.status).toLowerCase())).length;
  const activeSchedules = schedules.filter((schedule) => asString(schedule.status) !== "cancelled");
  // Fit the visible hour range to the actual lessons so the grid isn't mostly empty.
  const { displayStartHour, displayEndHour } = useMemo(() => {
    let earliest = Infinity;
    let latest = -Infinity;
    for (const block of timetableBlocks) {
      const start = timeToMinutes(asString(block.start_time));
      const end = timeToMinutes(asString(block.end_time));
      if (Number.isFinite(start)) earliest = Math.min(earliest, start);
      if (Number.isFinite(end)) latest = Math.max(latest, end);
    }
    if (!Number.isFinite(earliest) || !Number.isFinite(latest)) {
      return { displayStartHour: timetableStartHour, displayEndHour: 18 };
    }
    const startHour = Math.max(timetableStartHour, Math.floor(earliest / 60));
    let endHour = Math.min(timetableEndHour, Math.ceil(latest / 60));
    // Keep a sensible minimum span so a day with one short class still reads as a calendar.
    if (endHour - startHour < 6) endHour = Math.min(timetableEndHour, startHour + 6);
    return { displayStartHour: startHour, displayEndHour: endHour };
  }, [timetableBlocks]);
  const hours = Array.from({ length: displayEndHour - displayStartHour + 1 }, (_item, index) => displayStartHour + index);

  function updateField(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function toggleWeekday(day: string) {
    setForm((current) => {
      const selected = new Set(current.weekdays);
      if (selected.has(day)) selected.delete(day);
      else selected.add(day);
      return { ...current, weekdays: Array.from(selected).sort() };
    });
  }

  async function submitSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(routes.adminAcademicScheduleCreate, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          group_id: Number(form.groupId),
          teacher_id: Number(form.teacherId || 0),
          title: form.title,
          weekdays: form.weekdays.map(Number),
          start_time: form.startTime,
          end_time: form.endTime,
          start_date: form.startDate,
          end_date: form.endDate,
          room: form.room,
          online_url: form.onlineUrl,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setError(asString(data.message) || "Could not create schedule.");
        return;
      }
      setSchedules(Array.isArray(data.schedules) ? data.schedules : []);
      setSessions(Array.isArray(data.sessions) ? data.sessions : []);
      if (Array.isArray(data.lessons)) setLessons(data.lessons);
      setMessage(`Schedule created. ${asNumber(data.schedule?.sessionCount)} lesson sessions generated.`);
      setCreateOpen(false);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <ChartCard
        title={isTeacherMode ? "Timetable" : "Academic Timetable"}
        subtitle={`${filteredSessions.length} upcoming sessions · ${completedLessonCount} completed classes · ${cancelledLessonCount} cancelled · ${activeSchedules.length} active schedules`}
        icon={<CalendarDays className="h-4 w-4 text-info" />}
        headerActions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {!isTeacherMode ? (
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setMessage("");
                  setForm((current) => ({
                    ...current,
                    startDate: isoDate(weekStart),
                    endDate: isoDate(addDays(weekStart, 60)),
                  }));
                  setCreateOpen(true);
                }}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground"
              >
                <Plus className="h-3.5 w-3.5" />
                Assign Time
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setWeekStart((current) => addDays(current, -7))}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
              aria-label="Previous week"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setWeekStart(startOfWeek(new Date()))}
              className="h-8 rounded-lg border border-foreground/10 px-3 text-xs font-bold hover:bg-muted"
            >
              This Week
            </button>
            <button
              type="button"
              onClick={() => setWeekStart((current) => addDays(current, 7))}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
              aria-label="Next week"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        }
      >
        {message ? (
          <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
            {message}
          </p>
        ) : null}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm font-bold">
            <Clock className="h-4 w-4 text-muted-foreground" />
            {formatWeekRange(weekStart)}
          </div>
          <Select value={subjectFilter} onChange={(event) => setSubjectFilter(event.target.value)} className="max-w-xs">
            <option value="all">All subjects</option>
            {subjectOptions.map((subject: string) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </Select>
        </div>

        <div className="overflow-x-auto rounded-lg border border-foreground/10 bg-background">
          <div className="min-w-[880px]">
            <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))] border-b border-foreground/10 bg-muted/40">
              <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Time</div>
              {weekDays.map((day, index) => (
                <div key={isoDate(day)} className="border-l border-foreground/10 px-3 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{weekdayLabels[index]}</p>
                  <p className="text-lg font-bold leading-none">{day.getDate()}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))] border-b border-foreground/10 bg-muted/15">
              <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                All-day
              </div>
              {weekDays.map((day) => {
                const dayIso = isoDate(day);
                const dayLessons = untimedLessons.filter((lesson) => lessonDateToIso(lesson.lesson_date) === dayIso);
                const completedCount = dayLessons.filter((lesson) => lessonStatus(lesson) === "completed").length;
                const cancelledCount = dayLessons.filter((lesson) => lessonStatus(lesson) === "cancelled").length;
                const subjectCounts = dayLessons.reduce<Record<string, number>>((acc, lesson) => {
                  const code = subjectCode(lesson.subject_name);
                  acc[code] = (acc[code] || 0) + 1;
                  return acc;
                }, {});
                return (
                  <div key={`${dayIso}-classes`} className="min-h-[58px] border-l border-foreground/10 p-1.5">
                    {dayLessons.length === 0 ? (
                      <p className="pt-3 text-center text-[10px] font-semibold text-muted-foreground/40">—</p>
                    ) : (
                      <div
                        className="space-y-1"
                        title={dayLessons
                          .slice(0, 12)
                          .map((lesson) => `${asString(lesson.group_name)} · ${asString(lesson.lesson_number)} · ${asString(lesson.lesson_topic)}`)
                          .join("\n")}
                      >
                        {completedCount ? (
                          <div className="rounded-md border border-emerald-500/20 bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-800">
                            {completedCount} completed
                          </div>
                        ) : null}
                        {cancelledCount ? (
                          <div className="rounded-md border border-red-500/20 bg-red-50 px-2 py-1 text-[10px] font-bold text-red-800">
                            {cancelledCount} cancelled
                          </div>
                        ) : null}
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(subjectCounts).slice(0, 3).map(([code, count]) => (
                            <span key={code} className="rounded bg-white px-1.5 py-0.5 text-[9px] font-bold text-foreground/60">
                              {code} {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))]">
              <div className="relative h-[720px] border-r border-foreground/10 bg-muted/20">
                {hours.map((hour) => (
                  <div
                    key={hour}
                    className="absolute left-0 right-0 border-t border-foreground/8 px-2 pt-1 text-right text-[11px] font-semibold text-muted-foreground"
                    style={{
                      top: `${((hour - displayStartHour) / (displayEndHour - displayStartHour)) * 100}%`,
                      // Pull the final label above the bottom edge so it isn't clipped.
                      transform: hour === displayEndHour ? "translateY(-100%)" : undefined,
                    }}
                  >
                    {String(hour).padStart(2, "0")}:00
                  </div>
                ))}
              </div>
              {weekDays.map((day) => {
                const dayIso = isoDate(day);
                const daySessions = layoutSessionsForDay(timetableBlocks.filter((session) => asString(session.session_date) === dayIso));
                return (
                  <div key={dayIso} className="relative h-[720px] border-l border-foreground/10">
                    {hours.map((hour) => (
                      <div
                        key={`${dayIso}-${hour}`}
                        className="absolute left-0 right-0 border-t border-foreground/8"
                        style={{ top: `${((hour - displayStartHour) / (displayEndHour - displayStartHour)) * 100}%` }}
                      />
                    ))}
                    {daySessions.map((session) => {
                      const spanMinutes = (displayEndHour - displayStartHour) * 60;
                      // Overlapping classes share a band and stack as full-width rows.
                      const bandTop = ((session.bandStartMin - displayStartHour * 60) / spanMinutes) * 100;
                      const bandHeight = ((session.bandEndMin - session.bandStartMin) / spanMinutes) * 100;
                      const rowHeight = bandHeight / Math.max(1, session.rowCount);
                      const top = bandTop + session.row * rowHeight;
                      // Keep a readable floor for single blocks; stacked rows use their share of the band.
                      const height = session.rowCount > 1 ? rowHeight : Math.max(7, rowHeight);
                      const toneLabel = session.status === "cancelled" ? "Cancelled" : session.status === "completed" ? "Done" : "Scheduled";
                      return (
                        <div
                          key={session.id}
                          className={`absolute overflow-hidden rounded-lg border p-2 text-xs shadow-card ${subjectColorClass(session.subject_name, session.status)}`}
                          style={{
                            top: `${Math.max(0, top)}%`,
                            height: `calc(${Math.max(0, height)}% - 2px)`,
                            left: "4px",
                            right: "4px",
                          }}
                          title={[
                            asString(session.group_name),
                            asString(session.subject_name),
                            formatSessionTime(asString(session.start_time), asString(session.end_time)),
                            asString(session.lesson_number),
                            asString(session.lesson_topic),
                            asString(session.teacher_name),
                          ].filter(Boolean).join(" · ")}
                        >
                          <div className="flex min-w-0 items-start justify-between gap-1">
                            <p className="truncate font-bold leading-tight">{asString(session.group_name)}</p>
                            <span className="shrink-0 rounded bg-white/80 px-1 text-[9px] font-bold text-foreground/55">
                              {subjectCode(session.subject_name)}
                            </span>
                          </div>
                          <p className="truncate text-[11px] font-semibold opacity-90">{formatSessionTime(asString(session.start_time), asString(session.end_time))}</p>
                          <p className="truncate text-[10px] font-bold uppercase tracking-wide opacity-80">{toneLabel}</p>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </ChartCard>

      {createOpen ? (
        <div className="fixed inset-0 z-50 bg-foreground/45" onClick={() => setCreateOpen(false)}>
          <aside
            className="flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div>
                <h3 className="text-base font-bold">Assign Class Time</h3>
                <p className="mt-1 text-xs text-muted-foreground">Creates a schedule rule and places matching past lessons by time.</p>
              </div>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
                aria-label="Close schedule form"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form id="schedule-create-form" onSubmit={submitSchedule} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
              {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
              <label className="block">
                <FieldLabel>Group</FieldLabel>
                <Select value={form.groupId} onChange={(event) => updateField("groupId", event.target.value)} required>
                  {groups.map((group: Record<string, unknown>) => (
                    <option key={asNumber(group.id)} value={asString(group.id)}>
                      {asString(group.name)} · {asString(group.subject_name)} · {asString(group.school_code)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block">
                <FieldLabel>Teacher</FieldLabel>
                <Select value={form.teacherId} onChange={(event) => updateField("teacherId", event.target.value)}>
                  <option value="">No teacher yet</option>
                  {teachers.map((teacher: Record<string, unknown>) => (
                    <option key={asNumber(teacher.id)} value={asString(teacher.id)}>
                      {asString(teacher.full_name)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block">
                <FieldLabel>Title</FieldLabel>
                <TextInput value={form.title} onChange={(event) => updateField("title", event.target.value)} placeholder="Regular class" />
              </label>
              <div>
                <FieldLabel>Days</FieldLabel>
                <div className="grid grid-cols-7 gap-1">
                  {weekdayLabels.map((label, index) => {
                    const value = String(index);
                    const active = form.weekdays.includes(value);
                    return (
                      <button
                        key={label}
                        type="button"
                        onClick={() => toggleWeekday(value)}
                        className={`h-10 rounded-lg text-[11px] font-bold ${active ? "bg-foreground text-background" : "bg-muted text-muted-foreground hover:bg-foreground/10"}`}
                      >
                        {label.slice(0, 2)}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <FieldLabel>Start Time</FieldLabel>
                  <TextInput type="time" value={form.startTime} onChange={(event) => updateField("startTime", event.target.value)} required />
                </label>
                <label className="block">
                  <FieldLabel>End Time</FieldLabel>
                  <TextInput type="time" value={form.endTime} onChange={(event) => updateField("endTime", event.target.value)} required />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <FieldLabel>Start Date</FieldLabel>
                  <TextInput type="date" value={form.startDate} onChange={(event) => updateField("startDate", event.target.value)} required />
                </label>
                <label className="block">
                  <FieldLabel>End Date</FieldLabel>
                  <TextInput type="date" value={form.endDate} onChange={(event) => updateField("endDate", event.target.value)} required />
                </label>
              </div>
              <label className="block">
                <FieldLabel>Room</FieldLabel>
                <TextInput value={form.room} onChange={(event) => updateField("room", event.target.value)} placeholder="Room 2" />
              </label>
              <label className="block">
                <FieldLabel>Online Link</FieldLabel>
                <TextInput value={form.onlineUrl} onChange={(event) => updateField("onlineUrl", event.target.value)} placeholder="https://..." />
              </label>
            </form>
            <div className="border-t border-foreground/8 px-5 py-4">
              <button
                type="submit"
                form="schedule-create-form"
                disabled={submitting || !form.groupId || form.weekdays.length === 0}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                {submitting ? "Saving..." : "Save Time Rule"}
              </button>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}

export default function AcademicPanel({ state, kind }: { state: any; kind: AdminTab }) {
  const props = state.props || {};
  const isTeacherMode = asString(state.adminMode).toLowerCase() === "teacher";
  const schools = Array.isArray(props.adminAcademicSchools) ? props.adminAcademicSchools : [];
  const subjects = Array.isArray(props.adminAcademicSubjects) ? props.adminAcademicSubjects : [];
  const groups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const csrf: string = asString(props.csrfToken);

  const [openGroupId, setOpenGroupId] = useState<number | null>(null);
  const [addGroupOpen, setAddGroupOpen] = useState(false);
  const [groupSearch, setGroupSearch] = useState("");
  const [groupSchool, setGroupSchool] = useState("all");
  const [groupSubject, setGroupSubject] = useState("all");

  const schoolNameByCode = useMemo(() => {
    const result = new Map<string, string>();
    schools.forEach((school: Record<string, unknown>) => {
      const code = asString(school.code);
      if (code) result.set(code, asString(school.name) || code);
    });
    return result;
  }, [schools]);

  const groupSchoolOptions = useMemo(() => {
    const codes = new Set<string>();
    groups.forEach((group: Record<string, unknown>) => {
      const code = asString(group.school_code);
      if (code) codes.add(code);
    });
    return Array.from(codes).sort((a, b) => {
      const left = schoolNameByCode.get(a) || a;
      const right = schoolNameByCode.get(b) || b;
      return left.localeCompare(right);
    });
  }, [groups, schoolNameByCode]);

  const groupSubjectOptions = useMemo(() => {
    const names = new Set<string>();
    groups.forEach((group: Record<string, unknown>) => {
      const name = asString(group.subject_name);
      if (name) names.add(name);
    });
    return Array.from(names).sort((a, b) => a.localeCompare(b));
  }, [groups]);

  const filteredGroups = useMemo(() => {
    const query = groupSearch.trim().toLowerCase();
    return groups.filter((group: Record<string, unknown>) => {
      const name = asString(group.name);
      const subject = asString(group.subject_name);
      const schoolCode = asString(group.school_code);
      const schoolName = schoolNameByCode.get(schoolCode) || schoolCode;
      const matchesQuery =
        !query ||
        `${name} ${subject} ${schoolCode} ${schoolName}`.toLowerCase().includes(query);
      const matchesSchool = groupSchool === "all" || schoolCode === groupSchool;
      const matchesSubject = groupSubject === "all" || subject === groupSubject;
      return matchesQuery && matchesSchool && matchesSubject;
    });
  }, [groups, groupSearch, groupSchool, groupSubject, schoolNameByCode]);

  if (kind === "groups" && openGroupId !== null) {
    return (
      <GroupGradebook
        key={openGroupId}
        groupId={openGroupId}
        csrf={csrf}
        groups={groups}
        onClose={() => setOpenGroupId(null)}
      />
    );
  }

  if (kind === "schedule") {
    return <SchedulePanel state={state} />;
  }

  return (
    <div className="space-y-4">
      {kind === "subjects" ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,380px),1fr]">
          <ChartCard title="Add Subject" icon={<Plus className="h-4 w-4 text-info" />}>
            <form action={routes.adminAcademicSubjectCreate} method="post" className="space-y-3">
              <input type="hidden" name="csrf_token" value={csrf} />
              <label className="block">
                <FieldLabel>School</FieldLabel>
                <Select name="school_code" required>
                  {schools.map((school: Record<string, unknown>) => (
                    <option key={asString(school.code)} value={asString(school.code)}>
                      {asString(school.name)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block">
                <FieldLabel>Subject Name</FieldLabel>
                <TextInput name="subject_name" required placeholder="General English" />
              </label>
              <label className="block">
                <FieldLabel>Code</FieldLabel>
                <TextInput name="subject_code" placeholder="ENG" />
              </label>
              <button className="rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">Save Subject</button>
            </form>
          </ChartCard>
          <ChartCard title="Subjects" subtitle={`${subjects.length} total`}>
            <div className="max-h-[70dvh] overflow-auto">
              <table className="w-full min-w-[620px] text-left">
                <thead className="sticky top-0 z-20 bg-surface text-[10px] font-bold uppercase tracking-wider text-muted-foreground shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                  <tr><th className="px-3 py-2">School</th><th className="px-3 py-2">Subject</th><th className="px-3 py-2">Code</th><th className="px-3 py-2">Short</th></tr>
                </thead>
                <tbody className="divide-y divide-foreground/5">
                  {subjects.map((subject: Record<string, unknown>) => (
                    <tr key={asNumber(subject.id)}><td className="px-3 py-2 text-xs">{asString(subject.school_name)}</td><td className="px-3 py-2 text-sm font-semibold">{asString(subject.name)}</td><td className="px-3 py-2 text-xs">{asString(subject.code)}</td><td className="px-3 py-2 text-xs">{asString(subject.short_name)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </div>
      ) : null}

      {kind === "groups" && openGroupId === null ? (
        <>
          {addGroupOpen && !isTeacherMode ? (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
              onClick={() => setAddGroupOpen(false)}
            >
              <div
                className="w-full max-w-lg overflow-hidden rounded-xl bg-surface shadow-card-hover"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
                  <h3 className="text-sm font-bold">Add Group</h3>
                  <button
                    type="button"
                    onClick={() => setAddGroupOpen(false)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <form action={routes.adminAcademicGroupCreate} method="post" className="space-y-3 px-4 py-4">
                  <input type="hidden" name="csrf_token" value={csrf} />
                  <label className="block">
                    <FieldLabel>School</FieldLabel>
                    <Select name="school_code" required>
                      {schools.map((school: Record<string, unknown>) => (
                        <option key={asString(school.code)} value={asString(school.code)}>
                          {asString(school.name)}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="block">
                    <FieldLabel>Subject</FieldLabel>
                    <Select name="subject_id" required>
                      {subjects.map((subject: Record<string, unknown>) => (
                        <option key={asNumber(subject.id)} value={asNumber(subject.id)}>
                          {asString(subject.school_name)} · {asString(subject.name)}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <FieldLabel>Group Name</FieldLabel>
                      <TextInput name="group_name" required placeholder="7D" />
                    </label>
                    <label className="block">
                      <FieldLabel>Code</FieldLabel>
                      <TextInput name="group_code" placeholder="7D-Math" />
                    </label>
                  </div>
                  <div className="flex justify-end gap-2 border-t border-foreground/8 pt-3">
                    <button
                      type="button"
                      onClick={() => setAddGroupOpen(false)}
                      className="rounded-lg bg-muted px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10"
                    >
                      Cancel
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">
                      <Plus className="h-4 w-4" />
                      Save Group
                    </button>
                  </div>
                </form>
              </div>
            </div>
          ) : null}

            <ChartCard
              title="Groups"
              subtitle={`${filteredGroups.length} shown · ${groups.length} total`}
              icon={<Layers className="h-4 w-4 text-info" />}
              headerActions={isTeacherMode ? null :
                <button
                  type="button"
                  onClick={() => setAddGroupOpen(true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground"
                >
                  <Plus className="h-4 w-4" />
                  Add Group
                </button>
              }
            >
              <div className="mb-3 grid gap-2 lg:grid-cols-[minmax(220px,1fr),180px,220px]">
                <label className="relative block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="search"
                    value={groupSearch}
                    onChange={(event) => setGroupSearch(event.target.value)}
                    placeholder="Search groups"
                    className="h-10 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
                  />
                </label>
                <Select value={groupSchool} onChange={(event) => setGroupSchool(event.target.value)}>
                  <option value="all">All schools</option>
                  {groupSchoolOptions.map((code) => (
                    <option key={code} value={code}>
                      {schoolNameByCode.get(code) || code}
                    </option>
                  ))}
                </Select>
                <Select value={groupSubject} onChange={(event) => setGroupSubject(event.target.value)}>
                  <option value="all">All subjects</option>
                  {groupSubjectOptions.map((subject) => (
                    <option key={subject} value={subject}>
                      {subject}
                    </option>
                  ))}
                </Select>
              </div>

              {filteredGroups.length === 0 ? (
                <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                  <p className="text-sm font-bold">No groups found</p>
                  <p className="mt-1 text-xs text-muted-foreground">Try a different search or filter.</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                  {filteredGroups.map((group: Record<string, unknown>) => {
                    const id = asNumber(group.id);
                    const name = asString(group.name);
                    const subjectName = asString(group.subject_name);
                    const schoolCode = asString(group.school_code);
                    const schoolName = schoolNameByCode.get(schoolCode) || schoolCode;
                    const studentsCount = asNumber(group.students_count);
                    const disqualifiedCount = asNumber(group.disqualified_count);
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setOpenGroupId(id)}
                        className="group flex aspect-square min-h-0 flex-col rounded-lg border border-foreground/10 bg-background p-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 sm:p-4"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span
                            className={`h-9 w-9 shrink-0 rounded-lg ${subjectSwatch(subjectName)} sm:h-10 sm:w-10`}
                            aria-hidden="true"
                          />
                          <Pill>{schoolCode || "school"}</Pill>
                        </div>

                        <div className="min-w-0 flex-1 py-3">
                          <span className="block truncate text-lg font-bold leading-tight sm:text-xl">{name}</span>
                          <span className="mt-1 block truncate text-xs text-muted-foreground">
                            {subjectName || "No subject"}
                          </span>
                          <span className="mt-0.5 block truncate text-[11px] text-muted-foreground/80">
                            {schoolName}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                          <Pill>{studentsCount} active</Pill>
                          {disqualifiedCount > 0 ? <Pill>{disqualifiedCount} disqualified</Pill> : null}
                        </div>

                        <div className="mt-2 flex items-center justify-end border-t border-foreground/8 pt-2">
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-primary">
                            Gradebook
                            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </ChartCard>
        </>
      ) : null}

    </div>
  );
}
