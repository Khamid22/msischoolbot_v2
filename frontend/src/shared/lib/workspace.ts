import { FormEvent } from "react";

export type AcademicPanelKind =
  | "subjects"
  | "groups"
  | "schedule"
  | "curriculum"
  | "gradebook";
export type OverviewGrade = "7" | "8";

export function asString(value: unknown) {
  return String(value || "").trim();
}

export function normalizeSubjectKey(value: unknown) {
  return asString(value)
    .toLowerCase()
    .replace(/\s+/g, " ");
}

export function isMathSubject(value: unknown) {
  const normalized = normalizeSubjectKey(value);
  return (
    normalized === "igcse mathematics a" ||
    normalized === "igcse math a" ||
    normalized === "mathematics" ||
    normalized === "math"
  );
}

function subjectPriorityTuple(value: unknown): [number, string] {
  const normalized = normalizeSubjectKey(value);
  if (isMathSubject(normalized)) {
    return [0, normalized];
  }
  if (normalized === "general english" || normalized === "english") {
    return [1, normalized];
  }
  if (normalized === "chemistry") {
    return [2, normalized];
  }
  if (normalized === "biology") {
    return [3, normalized];
  }
  if (normalized === "physics") {
    return [4, normalized];
  }
  return [999, normalized];
}

export function compareSubjectsMathFirst(left: unknown, right: unknown) {
  const leftKey = subjectPriorityTuple(left);
  const rightKey = subjectPriorityTuple(right);
  if (leftKey[0] !== rightKey[0]) {
    return leftKey[0] - rightKey[0];
  }
  return leftKey[1].localeCompare(rightKey[1]);
}

export function sortSubjectsMathFirst(subjects: string[]) {
  return [...subjects].sort(compareSubjectsMathFirst);
}

export function findPreferredMathSubject(subjects: string[]) {
  const prioritized = sortSubjectsMathFirst(subjects.filter(Boolean));
  return prioritized[0] || "";
}

export function asNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function getStudentRowId(student: Record<string, unknown> | null | undefined) {
  return asNumber(student?.studentRowId ?? student?.student_row_id ?? student?.id);
}

export function getStudentCode(student: Record<string, unknown> | null | undefined) {
  return asString(student?.studentCode ?? student?.student_code ?? student?.student_id);
}

export function getPublicDashboardId(student: Record<string, unknown> | null | undefined) {
  return asNumber(student?.publicDashboardId ?? student?.public_dashboard_id ?? student?.enrollment_id);
}

export function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asString(item))
    .filter(Boolean);
}

export function asPositiveNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

/**
 * Parse a stored timestamp as UTC. Activity timestamps are written as UTC, but
 * not every row carries an explicit `Z`/offset — a naive string like
 * "2026-06-26 10:00:00" would otherwise be read as *local* time and show the
 * wrong "last seen". When no timezone is present we treat the value as UTC.
 */
export function parseTimestampUtc(value: unknown): number {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw) return NaN;
  if (/([zZ]|[+-]\d{2}:?\d{2})$/.test(raw)) {
    return Date.parse(raw);
  }
  const normalized = `${raw.replace(" ", "T")}Z`;
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : Date.parse(raw);
}

export function formatLastSeen(value: unknown): { label: string; online: boolean } {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw) return { label: "Never", online: false };

  const ts = parseTimestampUtc(raw);
  if (!Number.isFinite(ts)) return { label: "Never", online: false };

  const diffSec = Math.floor((Date.now() - ts) / 1000);
  if (diffSec < 0) return { label: "Just now", online: true };
  if (diffSec < 300) return { label: "Online", online: true };
  if (diffSec < 3600) return { label: `${Math.floor(diffSec / 60)}m ago`, online: false };
  if (diffSec < 86400) return { label: `${Math.floor(diffSec / 3600)}h ago`, online: false };
  return { label: `${Math.floor(diffSec / 86400)}d ago`, online: false };
}

export function gradeFromGroupLabel(label: unknown): OverviewGrade | "" {
  const match = asString(label).match(/^([78])/);
  if (!match) {
    return "";
  }
  return match[1] as OverviewGrade;
}

export function availableGradesForRow(
  row: Record<string, unknown> | null | undefined
): OverviewGrade[] {
  const grades = new Set<OverviewGrade>();
  const groups = Array.isArray(row?.groups)
    ? (row.groups as Array<Record<string, unknown>>)
    : [];
  const monthlySeries = Array.isArray(row?.monthly_series)
    ? (row.monthly_series as Array<Record<string, unknown>>)
    : [];
  const examSeries = Array.isArray(row?.exam_series)
    ? (row.exam_series as Array<Record<string, unknown>>)
    : [];

  for (const groupRow of groups) {
    const grade = gradeFromGroupLabel(groupRow?.label);
    if (grade) {
      grades.add(grade);
    }
  }

  for (const seriesRow of monthlySeries) {
    const grade = gradeFromGroupLabel(seriesRow?.label);
    if (grade) {
      grades.add(grade);
    }
  }

  for (const seriesRow of examSeries) {
    const grade = gradeFromGroupLabel(seriesRow?.label);
    if (grade) {
      grades.add(grade);
    }
  }

  return (["7", "8"] as OverviewGrade[]).filter((grade) => grades.has(grade));
}

export function filterGroupsByGrade(
  groups: Array<Record<string, unknown>>,
  grade: OverviewGrade | ""
) {
  if (!grade) {
    return groups;
  }
  return groups.filter((groupRow) => gradeFromGroupLabel(groupRow?.label) === grade);
}

export function filterMonthlySeriesByGrade(
  monthlySeries: Array<Record<string, unknown>>,
  grade: OverviewGrade | ""
) {
  if (!grade) {
    return monthlySeries;
  }
  return monthlySeries.filter(
    (seriesRow) => gradeFromGroupLabel(seriesRow?.label) === grade
  );
}

export function trimEmptyMonthlyMonths(
  months: string[],
  monthlySeries: Array<Record<string, unknown>>
) {
  if (!months.length || !monthlySeries.length) {
    return {
      months,
      series: monthlySeries,
    };
  }

  const keepIndexes = months.map((_month, monthIndex) =>
    monthlySeries.some((seriesRow) => {
      const values = Array.isArray(seriesRow?.values) ? (seriesRow.values as unknown[]) : [];
      return asPositiveNumber(values[monthIndex]) !== null;
    })
  );
  const hasAnyMonths = keepIndexes.some(Boolean);

  return {
    months: hasAnyMonths
      ? months.filter((_month, monthIndex) => keepIndexes[monthIndex])
      : [],
    series: monthlySeries.map((seriesRow) => {
      const values = Array.isArray(seriesRow?.values) ? (seriesRow.values as unknown[]) : [];
      return {
        ...seriesRow,
        values: hasAnyMonths
          ? values.filter((_value, monthIndex) => keepIndexes[monthIndex])
          : [],
      };
    }),
  };
}

export function formatMonthKeyLabel(monthKey: string) {
  const match = asString(monthKey).match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return asString(monthKey);
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) {
    return asString(monthKey);
  }

  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "numeric",
    }).format(new Date(year, month - 1, 1));
  } catch (_error) {
    return asString(monthKey);
  }
}

export function submitConfirm(event: FormEvent<HTMLFormElement>, message: string) {
  if (!window.confirm(message)) {
    event.preventDefault();
  }
}
