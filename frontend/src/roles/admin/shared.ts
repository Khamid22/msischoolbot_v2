import { FormEvent } from "react";

export type AdminTab =
  | "overview"
  | "students"
  | "parents"
  | "teachers"
  | "subjects"
  | "groups"
  | "schedule"
  | "announcements"
  | "resources"
  | "payments"
  | "complaints"
  | "career_growth"
  | "candidates"
  | "contact"
  | "chat"
  | "student_dashboard"
  | "student_profile"
  | "student_resources"
  | "student_chat"
  | "student_rating"
  | "student_aap"
  | "student_ar"
  | "student_office_hours"
  | "curriculum"
  | "gradebook"
  | "office_hours";
export type OverviewGrade = "7" | "8";
export type AdminMode = "admin" | "ceo" | "hr" | "sales" | "teacher" | "student" | "parent" | "academic_director";

export interface ResourceUploadState {
  active: boolean;
  percent: number;
  message: string;
  error: boolean;
}

export interface AdminPageProps {
  authLogin?: string;
  authError?: string;
  adminMode?: AdminMode;
  adminNotice?: string;
  adminPanel?: AdminTab;
  adminSchool?: string;
  adminStudents?: Array<Record<string, unknown>>;
  adminParents?: Array<Record<string, unknown>>;
  adminParentChildren?: Array<Record<string, unknown>>;
  adminTeachers?: Array<Record<string, unknown>>;
  adminTeacherCandidates?: Array<Record<string, unknown>>;
  adminComplaints?: Array<Record<string, unknown>>;
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
  adminAcademicSchools?: Array<Record<string, unknown>>;
  adminAcademicSubjects?: Array<Record<string, unknown>>;
  adminAcademicGroups?: Array<Record<string, unknown>>;
  adminAcademicEnrollments?: Array<Record<string, unknown>>;
  adminAcademicLessons?: Array<Record<string, unknown>>;
  adminAcademicSchedules?: Array<Record<string, unknown>>;
  adminAcademicSessions?: Array<Record<string, unknown>>;
  adminAnnouncements?: Array<Record<string, unknown>>;
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
  { key: "parents", label: "Parents" },
  { key: "teachers", label: "Teachers" },
  { key: "subjects", label: "Subjects" },
  { key: "groups", label: "Groups" },
  { key: "schedule", label: "Schedule" },
  { key: "announcements", label: "Announcements" },
  { key: "resources", label: "Resources" },
  { key: "payments", label: "Payments" },
  { key: "complaints", label: "Complaints" },
  { key: "career_growth", label: "Career Growth" },
  { key: "candidates", label: "Candidates" },
  { key: "contact", label: "Contact" },
  { key: "chat", label: "Chat" },
  { key: "student_dashboard", label: "Academic Dashboard" },
  { key: "student_profile", label: "Profile" },
  { key: "student_resources", label: "Resources" },
  { key: "student_chat", label: "Chat" },
  { key: "student_rating", label: "Rating" },
  { key: "student_aap", label: "AAP" },
  { key: "student_ar", label: "AR" },
  { key: "student_office_hours", label: "Office Hours" },
  { key: "curriculum", label: "Curriculum" },
  { key: "gradebook", label: "Gradebook" },
  { key: "office_hours", label: "Office Hours" },
];

export const adminModeProfiles: Record<
  AdminMode,
  {
    label: string;
    shortLabel: string;
    description: string;
    tabs: AdminTab[];
  }
> = {
  admin: {
    label: "Admin",
    shortLabel: "Admin",
    description: "Full developer and owner access.",
    tabs: ["overview", "students", "parents", "teachers", "subjects", "groups", "schedule", "announcements", "resources", "payments", "complaints", "chat"],
  },
  ceo: {
    label: "CEO",
    shortLabel: "CEO",
    description: "Performance, schools, staff, and decisions.",
    tabs: ["overview", "groups", "payments", "complaints"],
  },
  hr: {
    label: "HR Manager",
    shortLabel: "HR",
    description: "Hiring pipeline and teacher records.",
    tabs: ["candidates", "teachers"],
  },
  sales: {
    label: "Customer Support",
    shortLabel: "Support",
    description: "Students, parent communication, payments, and follow-up.",
    tabs: ["complaints", "students", "parents", "payments"],
  },
  teacher: {
    label: "Teacher",
    shortLabel: "Teacher",
    description: "Assigned groups, students, timetable, and career progress.",
    tabs: ["overview", "students", "groups", "schedule", "career_growth", "announcements"],
  },
  student: {
    label: "Student",
    shortLabel: "Student",
    description: "Student dashboard, progress, resources, and communication.",
    tabs: ["student_dashboard", "student_profile", "student_resources", "student_chat", "student_rating", "student_aap", "student_ar", "student_office_hours"],
  },
  parent: {
    label: "Parent",
    shortLabel: "Parent",
    description: "Student progress, announcements, payments, and support.",
    tabs: ["overview", "announcements", "payments", "contact"],
  },
  academic_director: {
    label: "Academic Director",
    shortLabel: "Acad Dir",
    description: "Teachers, groups, curriculum, timetable, quality, and student risk.",
    tabs: ["teachers", "groups", "schedule", "curriculum", "gradebook", "office_hours", "career_growth"],
  },
};

export const adminModes: AdminMode[] = ["admin", "ceo", "hr", "sales", "teacher", "student", "academic_director"];

export function normalizeAdminMode(value: unknown): AdminMode {
  const normalized = asString(value).toLowerCase();
  return normalized in adminModeProfiles ? (normalized as AdminMode) : "admin";
}

export function tabsForAdminMode(mode: AdminMode) {
  const allowedTabs = new Set(adminModeProfiles[mode]?.tabs || adminModeProfiles.admin.tabs);
  return tabs
    .filter((tab) => allowedTabs.has(tab.key))
    .map((tab) => {
      if (mode === "hr" && tab.key === "announcements") {
        return { ...tab, label: "Broadcasts" };
      }
      if (mode === "parent") {
        const parentLabels: Partial<Record<AdminTab, string>> = {
          overview: "Home",
          announcements: "Updates",
          contact: "Support",
        };
        return parentLabels[tab.key] ? { ...tab, label: parentLabels[tab.key] as string } : tab;
      }
      if (mode === "teacher") {
        const teacherLabels: Partial<Record<AdminTab, string>> = {
          overview: "Home",
          schedule: "Timetable",
          announcements: "Updates",
        };
        return teacherLabels[tab.key] ? { ...tab, label: teacherLabels[tab.key] as string } : tab;
      }
      return tab;
    });
}

// Sidebar grouping. Tabs are bucketed into labelled sections for the admin
// navigation. This is presentation-only: routes and per-mode permissions still
// come from `tabsForAdminMode` — `groupTabsBySection` only reorganizes the
// already-filtered tabs. Any tab not listed in a section falls into a trailing
// "More" group so nothing is ever hidden.
export interface NavSection {
  label: string;
  keys: AdminTab[];
}

export const navSections: NavSection[] = [
  { label: "Overview", keys: ["overview"] },
  { label: "People", keys: ["students", "parents", "teachers", "candidates"] },
  { label: "Academics", keys: ["subjects", "groups", "schedule", "curriculum", "gradebook", "office_hours", "career_growth"] },
  { label: "Communication", keys: ["announcements", "chat", "complaints", "contact"] },
  { label: "Operations", keys: ["payments", "resources"] },
];

export function groupTabsBySection<T extends { key: string }>(
  visibleTabs: T[],
): Array<{ label: string; tabs: T[] }> {
  const byKey = new Map(visibleTabs.map((tab) => [tab.key, tab] as const));
  const used = new Set<string>();
  const grouped: Array<{ label: string; tabs: T[] }> = [];

  for (const section of navSections) {
    const tabs = section.keys
      .map((key) => byKey.get(key))
      .filter((tab): tab is T => Boolean(tab));
    tabs.forEach((tab) => used.add(tab.key));
    if (tabs.length) {
      grouped.push({ label: section.label, tabs });
    }
  }

  const leftovers = visibleTabs.filter((tab) => !used.has(tab.key));
  if (leftovers.length) {
    grouped.push({ label: "More", tabs: leftovers });
  }

  return grouped;
}

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

export function createUploadId() {
  const randomPart =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID().replace(/-/g, "")
      : `${Date.now()}${Math.random().toString(36).slice(2, 12)}`;
  return `upload-${randomPart}`.slice(0, 64);
}

export function buildUploadProgressUrl(uploadId: string, afterSeq = 0) {
  const params = new URLSearchParams();
  params.set("after_seq", String(Math.max(0, Math.floor(Number(afterSeq) || 0))));
  return `/admin/api/resource-upload-progress/${encodeURIComponent(uploadId)}?${params.toString()}`;
}

const adminTabKeys = new Set<string>(tabs.map((tab) => tab.key));

export function normalizeAdminTab(value: unknown): AdminTab {
  const normalized = asString(value).toLowerCase();
  return adminTabKeys.has(normalized) ? (normalized as AdminTab) : "overview";
}

export function buildAdminTabUrl(tab: AdminTab, school: string, mode?: AdminMode | string) {
  const params = new URLSearchParams();
  params.set("panel", tab);
  params.set("school", school || "all");
  const normalizedMode = asString(mode).toLowerCase();
  if (normalizedMode) {
    params.set("mode", normalizedMode);
  }
  return `/?${params.toString()}`;
}
