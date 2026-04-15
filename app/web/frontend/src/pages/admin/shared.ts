import { FormEvent } from "react";

export type AdminTab = "overview" | "students" | "teachers" | "resources" | "chat";
export type OverviewGrade = "7" | "8";

export interface ResourceUploadState {
  active: boolean;
  percent: number;
  message: string;
  error: boolean;
}

export interface AdminPageProps {
  authLogin?: string;
  authError?: string;
  adminNotice?: string;
  adminPanel?: AdminTab;
  adminSchool?: string;
  adminStudents?: Array<Record<string, unknown>>;
  adminTeachers?: Array<Record<string, unknown>>;
  adminTeacherOptions?: Array<{ name: string; school_codes: string[] }>;
  adminGroupOptions?: Array<{ name: string; school_codes: string[] }>;
  adminTeacherEdit?: Record<string, unknown> | null;
  adminTeacherEditSchool?: string;
  adminSchoolOptions?: Array<{ code: string; label: string }>;
  adminQuickStats?: Record<string, number>;
  adminSchoolInfo?: Array<Record<string, unknown>>;
  adminSubjectInfo?: Array<Record<string, unknown>>;
  adminGroupZones?: {
    green?: Array<Record<string, unknown>>;
    yellow?: Array<Record<string, unknown>>;
    red?: Array<Record<string, unknown>>;
  };
  adminResourceTypes?: Array<Record<string, unknown>>;
  adminResourceActiveTypes?: Array<Record<string, unknown>>;
  adminResources?: Array<Record<string, unknown>>;
  adminResourceSubjectOptions?: string[];
  adminResourceUploadEnabled?: boolean;
  csrfToken?: string;
}

export type ChatMsg = {
  id: number;
  room: string;
  authorName: string;
  authorStudentId: string;
  body: string;
  isDeleted: boolean;
  editedAt: string | null;
  createdAt: string;
};

export type BlockedUser = {
  studentId: string;
  blockedBy: string;
  blockedAt: string;
  reason: string;
};

export const tabs: { key: AdminTab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "students", label: "Students" },
  { key: "teachers", label: "Teachers" },
  { key: "resources", label: "Resources" },
  { key: "chat", label: "Chat" },
];

// Keep all admin pages on one semantic top inset variable.
const _appTopInset = "var(--app-top-inset)";
export const adminHeaderPadTop = _appTopInset;
export const adminMainPadTop = `calc(${_appTopInset} + 3.5rem)`;
export const adminStickyTop = `calc(${_appTopInset} + 4.5rem)`;

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

export function formatLastSeen(value: unknown): { label: string; online: boolean } {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw) return { label: "Never", online: false };

  const ts = Date.parse(raw);
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

export function createUploadId() {
  const randomPart =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().replace(/-/g, "")
      : `${Date.now()}${Math.random().toString(36).slice(2, 12)}`;
  return `upload-${randomPart}`.slice(0, 64);
}

export function buildUploadWebSocketUrl(uploadId: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/resource-upload/${encodeURIComponent(uploadId)}`;
}

export function normalizeAdminTab(value: unknown): AdminTab {
  const normalized = asString(value).toLowerCase();
  if (
    normalized === "students" ||
    normalized === "teachers" ||
    normalized === "resources" ||
    normalized === "chat"
  ) {
    return normalized;
  }
  return "overview";
}

export function buildAdminTabUrl(tab: AdminTab, school: string) {
  const params = new URLSearchParams();
  params.set("panel", tab);
  params.set("school", school || "all");
  return `/?${params.toString()}`;
}
