// Shared constants, types, pure helpers, and small UI atoms for the academic panels.
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { BarChart3 as BarChartIcon, Filter, Table2 } from "lucide-react";
import { motion } from "@/shared/lib/motion";
import { asString, normalizeSubjectKey } from "@/features/managementTypes";

export const monthLabels = [
  { value: "01", label: "January" },
  { value: "02", label: "February" },
  { value: "03", label: "March" },
  { value: "04", label: "April" },
  { value: "05", label: "May" },
  { value: "06", label: "June" },
  { value: "07", label: "July" },
  { value: "08", label: "August" },
  { value: "09", label: "September" },
  { value: "10", label: "October" },
  { value: "11", label: "November" },
  { value: "12", label: "December" },
];

export const GRADEBOOK_STUDENT_COL_WIDTH = 165;
export const GRADEBOOK_AAP_COL_WIDTH = 38;
export const GRADEBOOK_ATT_COL_WIDTH = 30;
export const GRADEBOOK_HW_COL_WIDTH = 36;
export const GRADEBOOK_LESSON_COL_WIDTH = GRADEBOOK_ATT_COL_WIDTH + GRADEBOOK_HW_COL_WIDTH;
export const EXAM_TABLE_STUDENT_COL_WIDTH = 220;
export const EXAM_TABLE_SCORE_COL_WIDTH = 126;
export const EXAM_TABLE_MIN_WIDTH = 720;

export type PeriodParts = {
  month: string;
  year: string;
};

export type AxisTickProps = {
  x?: number;
  y?: number;
  payload?: {
    value?: unknown;
  };
};

export type ExamTypeOption = {
  key: string;
  label: string;
  labels: string[];
};

export function parsePeriodDate(value: unknown): PeriodParts | null {
  const text = String(value || "").trim();
  if (!text) return null;
  const slash = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);
  if (slash) {
    return {
      month: slash[2].padStart(2, "0"),
      year: slash[3].length === 2 ? `20${slash[3]}` : slash[3],
    };
  }
  const iso = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (iso) {
    return {
      month: iso[2].padStart(2, "0"),
      year: iso[1],
    };
  }
  return null;
}

export function matchesPeriod(value: unknown, month: string, year: string) {
  if (month === "all" && year === "all") return true;
  const parts = parsePeriodDate(value);
  if (!parts) return false;
  return (month === "all" || parts.month === month) && (year === "all" || parts.year === year);
}

export function collectPeriodOptions(values: unknown[]) {
  const months = new Set<string>();
  const years = new Set<string>();
  values.forEach((value) => {
    const parts = parsePeriodDate(value);
    if (!parts) return;
    months.add(parts.month);
    years.add(parts.year);
  });
  return {
    months: [...months].sort((a, b) => Number(a) - Number(b)),
    years: [...years].sort((a, b) => Number(b) - Number(a)),
  };
}

export function examTypeKey(label: unknown) {
  const text = asString(label).replace(/\s+/g, " ").trim();
  if (!text) return "";
  const compact = text.replace(/[\s_-]+/g, "").toUpperCase();
  const compactMatch = compact.match(/^(HFT|HT|ET)(\d+)$/);
  if (compactMatch) {
    const prefix = compactMatch[1] === "ET" ? "ET" : "HT";
    return `${prefix}${compactMatch[2]}`;
  }
  const lower = text.toLowerCase();
  const numberMatch = lower.match(/(?:test|term)\s*(\d+)/i) || lower.match(/(\d+)/);
  const number = numberMatch?.[1] || "";
  if (!number) return text;
  if (lower.includes("end")) return `ET${number}`;
  if (lower.includes("half") || lower.includes("ht")) return `HT${number}`;
  return text;
}

export function examTypeOrderValue(key: string) {
  const match = key.match(/^(HT|ET)(\d+)$/);
  if (!match) return Number.MAX_SAFE_INTEGER;
  const number = Number(match[2]);
  const phase = match[1] === "HT" ? 0 : 1;
  return number * 10 + phase;
}

export function collectExamTypeOptions(labels: string[]): ExamTypeOption[] {
  const buckets = new Map<string, ExamTypeOption>();
  labels.forEach((label) => {
    const key = examTypeKey(label) || label;
    const bucket = buckets.get(key) ?? { key, label: key, labels: [] };
    bucket.labels.push(label);
    buckets.set(key, bucket);
  });
  return Array.from(buckets.values()).sort((left, right) => {
    const orderDiff = examTypeOrderValue(left.key) - examTypeOrderValue(right.key);
    if (orderDiff !== 0) return orderDiff;
    return left.key.localeCompare(right.key);
  });
}

export function averageScore(values: Array<number | null | undefined>) {
  const valid = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (!valid.length) return null;
  return Math.round((valid.reduce((sum, value) => sum + value, 0) / valid.length) * 10) / 10;
}

export function chartMinWidth(count: number) {
  return Math.max(680, count * 124);
}

export function formatBarLabel(value: unknown) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return "";
  return Number.isInteger(parsed) ? String(parsed) : parsed.toFixed(1);
}

export function formatPercentLabel(value: unknown) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return "";
  return `${Math.round(parsed)}%`;
}

export function wrapWords(value: unknown, maxChars = 13, maxLines = 3) {
  const text = String(value || "").trim();
  if (!text) return ["—"];
  const words = text.split(/\s+/).flatMap((word) => {
    if (word.length <= maxChars) return [word];
    const chunks: string[] = [];
    for (let index = 0; index < word.length; index += maxChars) {
      chunks.push(word.slice(index, index + maxChars));
    }
    return chunks;
  });
  const lines: string[] = [];
  words.forEach((word) => {
    const current = lines[lines.length - 1] || "";
    if (!current) {
      lines.push(word);
      return;
    }
    if (`${current} ${word}`.length <= maxChars) {
      lines[lines.length - 1] = `${current} ${word}`;
      return;
    }
    lines.push(word);
  });
  if (lines.length <= maxLines) return lines;
  const visible = lines.slice(0, maxLines);
  visible[maxLines - 1] = `${visible[maxLines - 1].slice(0, Math.max(1, maxChars - 1))}…`;
  return visible;
}

export function StudentNameTick({ x = 0, y = 0, payload }: AxisTickProps) {
  const lines = wrapWords(payload?.value, 11, 3);
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fill="hsl(var(--muted-foreground))" fontSize={10}>
        {lines.map((line, index) => (
          <tspan key={`${line}-${index}`} x={0} dy={index === 0 ? 12 : 11}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

export function FieldLabel({ children }: { children: string }) {
  return (
    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

export function PeriodFilter({
  month,
  year,
  months,
  years,
  onMonthChange,
  onYearChange,
}: {
  month: string;
  year: string;
  months: string[];
  years: string[];
  onMonthChange: (value: string) => void;
  onYearChange: (value: string) => void;
}) {
  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
      <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground sm:justify-end">
        <Filter className="h-3.5 w-3.5" />
        Filter
      </span>
      <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto">
        <select
          value={month}
          onChange={(event) => onMonthChange(event.target.value)}
          className="h-9 w-full min-w-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-semibold outline-none focus:border-foreground/30 sm:min-w-[8.5rem]"
        >
          <option value="all">All months</option>
          {months.map((value) => (
            <option key={value} value={value}>
              {monthLabels.find((item) => item.value === value)?.label || value}
            </option>
          ))}
        </select>
        <select
          value={year}
          onChange={(event) => onYearChange(event.target.value)}
          className="h-9 w-full min-w-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-semibold outline-none focus:border-foreground/30 sm:min-w-[6.5rem]"
        >
          <option value="all">All years</option>
          {years.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export function ExamTypeFilter({
  value,
  options,
  onChange,
}: {
  value: string;
  options: ExamTypeOption[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
      <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground sm:justify-end">
        <Filter className="h-3.5 w-3.5" />
        Show
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full min-w-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-semibold outline-none focus:border-foreground/30 sm:min-w-[8.5rem]"
      >
        <option value="all">All exams</option>
        {options.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ExamViewSwitcher({
  value,
  onChange,
}: {
  value: "chart" | "table";
  onChange: (value: "chart" | "table") => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-foreground/10 bg-muted/50 p-0.5 shadow-sm">
      {([
        { key: "chart", label: "Chart", icon: <BarChartIcon className="h-3 w-3" /> },
        { key: "table", label: "Table", icon: <Table2 className="h-3 w-3" /> },
      ] as const).map((option) => {
        const active = value === option.key;
        return (
          <button
            key={option.key}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.key)}
            className={`inline-flex min-h-10 items-center gap-1.5 rounded-md px-2 text-[11px] font-bold transition-[transform,background-color,color,box-shadow] duration-200 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:min-h-8 motion-reduce:transition-none motion-reduce:active:scale-100 ${
              active ? "bg-surface text-foreground shadow-card" : "text-muted-foreground hover:bg-surface/70 hover:text-foreground"
            }`}
          >
            {option.icon}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-foreground/10 bg-muted px-2 text-xs font-semibold text-muted-foreground">
      {children}
    </span>
  );
}

export function MiniMetric({
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

export function CompactMetric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-[11px] font-semibold text-muted-foreground">
      {icon}
      <span className="font-bold text-foreground">{value}</span>
      {label}
    </span>
  );
}

export const subjectSwatches = [
  "bg-primary",
  "bg-info",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-violet-500",
] as const;

export function preferredSubjectOrder(value: unknown) {
  const key = normalizeSubjectKey(asString(value));
  if (key.includes("mathematics") || key.includes("math")) return 0;
  if (key.includes("chemistry")) return 1;
  if (key.includes("english")) return 2;
  return 3;
}

export function compareSubjectsByPreferredOrder(left: unknown, right: unknown) {
  const orderDiff = preferredSubjectOrder(left) - preferredSubjectOrder(right);
  if (orderDiff !== 0) return orderDiff;
  return asString(left).localeCompare(asString(right));
}

export function programInitials(value: unknown) {
  const first = asString(value).trim().split(/\s+/)[0] || "";
  return (first.slice(0, 2) || "—").toUpperCase();
}

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

export type Lesson = {
  id: number;
  lessonNumber: string;
  topic: string;
  date: string;
  startTime?: string;
  endTime?: string;
  room?: string;
  order: number;
  status?: string;
  sourceKind?: string;
  hasHomework?: boolean;
  lessonSessionId?: number;
  isCancellation?: boolean;
  cancellationReason?: string;
  exceptionId?: number | null;
  canRecover?: boolean;
};

export type Enrollment = {
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
  attendanceByLessonId?: Record<string, string>;
  homework: Record<string, number>;
  homeworkByLessonId?: Record<string, number>;
  exams?: Record<string, number>;
  examAttempts?: Record<string, string>;
  examDates?: Record<string, string>;
};

export type GradebookData = {
  group: { id: number; name: string; subjectName: string; schoolCode: string; examCount?: number };
  lessons: Lesson[];
  enrollments: Enrollment[];
  examLabels?: string[];
  examDates?: Record<string, string>;
  allEnrollments?: Enrollment[];
  schedule?: ScheduleRow | null;
  pageInfo?: {
    totalLessons: number;
    startIndex: number;
    endIndex: number;
    previousCursor?: string | null;
    nextCursor?: string | null;
    hasPrevious: boolean;
    hasNext: boolean;
    selectedMonth?: string;
    previousMonth?: string | null;
    nextMonth?: string | null;
    monthOptions?: Array<{
      value: string;
      label: string;
      lessonCount: number;
    }>;
  };
};


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

export type ActiveCell = {
  enrollmentId: number;
  lesson: Lesson;
  kind: "att" | "hw";
  anchorRect: DOMRect;
};

export const ATT_VALUES = ["present", "absent", "justified"] as const;
export type AttValue = (typeof ATT_VALUES)[number] | "";
