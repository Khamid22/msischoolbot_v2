import { asString, normalizeSubjectKey } from "@/shared/lib/workspace";

export const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const timetableStartHour = 8;
export const timetableEndHour = 22;

export function dateFromIso(value: string) {
  const [year, month, day] = value.split("-").map((part) => Number(part));
  if (!year || !month || !day) return new Date();
  return new Date(year, month - 1, day);
}

export function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function startOfWeek(date: Date) {
  const next = new Date(date);
  const weekday = (next.getDay() + 6) % 7;
  next.setDate(next.getDate() - weekday);
  next.setHours(0, 0, 0, 0);
  return next;
}

export function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export function formatWeekRange(weekStart: Date) {
  const end = addDays(weekStart, 6);
  const fmt = new Intl.DateTimeFormat("en", { month: "short", day: "numeric" });
  return `${fmt.format(weekStart)} - ${fmt.format(end)}, ${end.getFullYear()}`;
}

export function timeToMinutes(value: string) {
  const [hour, minute] = value.split(":").map((part) => Number(part));
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return timetableStartHour * 60;
  return hour * 60 + minute;
}

export function formatSessionTime(start: string, end: string) {
  return `${start || "--:--"}-${end || "--:--"}`;
}

export function hasUsableLessonDate(value: unknown) {
  const text = asString(value);
  return Boolean(text && /\d/.test(text));
}

export function lessonDateToIso(value: unknown) {
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

export function isCancelledText(value: unknown) {
  const text = asString(value).toLowerCase();
  return text.includes("cancelled") || text.includes("canceled");
}

export function lessonStatus(lesson: LessonHistoryRow) {
  return isCancelledText(lesson.lesson_number) || isCancelledText(lesson.lesson_topic) ? "cancelled" : "completed";
}

export function sessionTone(status: unknown) {
  const normalized = asString(status).toLowerCase();
  if (normalized === "cancelled" || normalized === "canceled") {
    return { label: "Cancelled", className: "border-red-500/35 bg-red-600 text-white" };
  }
  if (normalized === "completed" || normalized === "complete" || normalized === "done" || normalized === "accomplished") {
    return { label: "Completed", className: "border-emerald-500/35 bg-emerald-600 text-white" };
  }
  return { label: "Scheduled", className: "border-foreground/10 bg-foreground text-background" };
}

export function subjectCode(value: unknown) {
  const subject = asString(value).toLowerCase();
  if (subject.includes("math")) return "Math";
  if (subject.includes("english") || subject.includes("eng")) return "Eng";
  if (subject.includes("chem")) return "Chem";
  return asString(value).slice(0, 4) || "Subj";
}

export function subjectColorClass(value: unknown, status: "scheduled" | "completed" | "cancelled") {
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

export function school5LessonTime(lesson: LessonHistoryRow) {
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

export function scheduleWeekdays(value: unknown) {
  return asString(value)
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item >= 0 && item <= 6);
}

export function scheduleTimeForLesson(lesson: LessonHistoryRow, schedules: ScheduleRow[]) {
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

export function sameSubjectName(left: unknown, right: unknown) {
  return normalizeSubjectKey(left) === normalizeSubjectKey(right);
}


export type ScheduleRow = {
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

export type SessionRow = {
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

export type LessonHistoryRow = {
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

export type TimetableSession = SessionRow & {
  lane: number;
  laneCount: number;
};

export type TimetableLessonBlock = {
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
  // Overlap index within a shared time band. The UI can flow these into
  // columns and rows depending on how crowded the band is.
  row: number;
  rowCount: number;
  bandStartMin: number;
  bandEndMin: number;
};

export type RawTimetableBlock = Omit<TimetableLessonBlock, "row" | "rowCount" | "bandStartMin" | "bandEndMin">;

export function layoutSessionsForDay(sessionsForDay: RawTimetableBlock[]): TimetableLessonBlock[] {
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
