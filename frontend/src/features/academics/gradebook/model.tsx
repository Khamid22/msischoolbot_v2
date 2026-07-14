import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { BarChart3 as BarChartIcon, Filter, Table2 } from "lucide-react";
import { motion } from "@/shared/lib/motion";
import { asString, normalizeSubjectKey } from "@/shared/lib/workspace";
import type { ScheduleRow } from "../timetable/model";

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
  hasAcademicRecords?: boolean;
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
  calendarClosures?: Array<{
    id: number;
    title: string;
    startDate: string;
    endDate: string;
    scope: "school" | "group";
  }>;
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
      hasClosure?: boolean;
      isLocked?: boolean;
      closureTitles?: string[];
      closureScopes?: Array<"school" | "group">;
      protectedRecordCount?: number;
    }>;
  };
};

export type AcademicTrendMonth = {
  month: string;
  label: string;
  avgAAP: number | null;
  avgAR: number | null;
  avgPerformance: number | null;
  lessonCount: number;
  studentsWithData: number;
  homeworkRecordCount: number;
  attendanceRecordCount: number;
  hasClosure?: boolean;
  closureTitles?: string[];
};

export type AcademicTrendsData = {
  range: {
    from: string;
    through: string;
    months: number;
  };
  items: AcademicTrendMonth[];
};



export type ActiveCell = {
  enrollmentId: number;
  lesson: Lesson;
  kind: "att" | "hw";
  anchorRect: DOMRect;
};

export const ATT_VALUES = ["present", "absent", "justified"] as const;
export type AttValue = (typeof ATT_VALUES)[number] | "";
