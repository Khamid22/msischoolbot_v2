// Shared types, constants, and pure helpers for the Overview panel.
import { School, Users } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asString, getStudentCode, getStudentRowId } from "../../shared";

export type ZoneKey = "red" | "yellow" | "green";

export type MonthlyGroupRow = {
  label: string;
  students: number;
  current: number | null;
  previous: number | null;
  delta: number | null;
  ar: number | null;
  monthly_ar: number | null;
  display_ar: number | null;
  zone: string;
};

export type ExamClassOption = { shortName: string; label: string; average: number | null; rows: Array<{ label: string; average: number | null }> };
export type GraphMetric = "academic" | "exam";
export type GraphLineSeries = {
  key: string;
  dataKey: string;
  name: string;
  yAxisId: "aap" | "score";
  color: string;
};
export type AcademicBarRow = {
  label: string;
  aapAverage: number | null;
  arAverage: number | null;
  sortAverage: number | null;
};
export type MonthOption = {
  index: number;
  key: string;
  label: string;
  month: number;
  year: number;
  academicYear: string;
  academicYearLabel: string;
};

export type Candidate = Record<string, unknown>;

export const TEACHER_TAB_STORAGE_KEY = "msi.admin.teacherTab";
export const TEACHER_TRAINING_FILTER_STORAGE_KEY = "msi.admin.teacherTrainingFilter";
export const TEACHER_DETAIL_CANDIDATE_STORAGE_KEY = "msi.admin.teacherDetailCandidateId";

export const candidateStatusLabels: Record<string, string> = {
  new: "New",
  interview: "Interview",
  math_test: "Math Test",
  training_ready: "Training",
  training_passed: "Review",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const lineColors = ["#8b5cf6", "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#14b8a6", "#ec4899", "#64748b"];
export const scoreAxisTicks = [1, 2, 3, 4, 5, 6, 7, 8, 9];
export const groupNameCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

export function safeSvgId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function numericGraphValue(value: unknown): number | null {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

export function averageGraphValue(values: unknown[]): number | null {
  const nums = values
    .map((value) => numericGraphValue(value))
    .filter((value): value is number => value != null);
  if (!nums.length) return null;
  return nums.reduce((sum, value) => sum + value, 0) / nums.length;
}

export function normalizedAcademicAverage(aapValues: unknown[], arValues: unknown[]): number | null {
  const normalized = [
    ...aapValues
      .map((value) => numericGraphValue(value))
      .filter((value): value is number => value != null)
      .map((value) => value / 9),
    ...arValues
      .map((value) => numericGraphValue(value))
      .filter((value): value is number => value != null)
      .map((value) => value / 100),
  ];
  if (!normalized.length) return null;
  return normalized.reduce((sum, value) => sum + value, 0) / normalized.length;
}

export function compareAverageRowsDesc<T extends { label: string; average: number | null }>(left: T, right: T): number {
  const leftAverage = left.average ?? Number.NEGATIVE_INFINITY;
  const rightAverage = right.average ?? Number.NEGATIVE_INFINITY;
  if (leftAverage !== rightAverage) return rightAverage - leftAverage;
  return groupNameCollator.compare(right.label, left.label);
}

export function compareAcademicRowsDesc<T extends { label: string; sortAverage: number | null }>(left: T, right: T): number {
  const leftAverage = left.sortAverage ?? Number.NEGATIVE_INFINITY;
  const rightAverage = right.sortAverage ?? Number.NEGATIVE_INFINITY;
  if (leftAverage !== rightAverage) return rightAverage - leftAverage;
  return groupNameCollator.compare(right.label, left.label);
}

export function compareZoneGroupRowsDesc(left: Record<string, unknown>, right: Record<string, unknown>): number {
  const groupCompare = groupNameCollator.compare(asString(right.group_name), asString(left.group_name));
  if (groupCompare !== 0) return groupCompare;
  return groupNameCollator.compare(asString(right.subject_name), asString(left.subject_name));
}

export function lineRowAverage(row: Record<string, unknown>, labels: string[]): number | null {
  return averageGraphValue(labels.map((label) => row[label]));
}

export function compareLineRowsDesc(labels: string[]) {
  return (left: Record<string, unknown>, right: Record<string, unknown>) => {
    const leftAverage = lineRowAverage(left, labels) ?? Number.NEGATIVE_INFINITY;
    const rightAverage = lineRowAverage(right, labels) ?? Number.NEGATIVE_INFINITY;
    if (leftAverage !== rightAverage) return rightAverage - leftAverage;
    const leftLabel = asString(left.shortName) || asString(left.label);
    const rightLabel = asString(right.shortName) || asString(right.label);
    return groupNameCollator.compare(rightLabel, leftLabel);
  };
}

export function compareLineLabelsDesc(data: Array<Record<string, unknown>>) {
  return (left: string, right: string) => {
    const leftAverage = averageGraphValue(data.map((row) => row[left])) ?? Number.NEGATIVE_INFINITY;
    const rightAverage = averageGraphValue(data.map((row) => row[right])) ?? Number.NEGATIVE_INFINITY;
    if (leftAverage !== rightAverage) return rightAverage - leftAverage;
    return groupNameCollator.compare(right, left);
  };
}

export const zoneStyles: Record<ZoneKey, { soft: string; text: string; ring: string; dot: string }> = {
  red: {
    soft: "bg-rose-50",
    text: "text-rose-700",
    ring: "border-rose-200",
    dot: "bg-rose-500",
  },
  yellow: {
    soft: "bg-amber-50",
    text: "text-amber-700",
    ring: "border-amber-200",
    dot: "bg-amber-500",
  },
  green: {
    soft: "bg-emerald-50",
    text: "text-emerald-700",
    ring: "border-emerald-200",
    dot: "bg-emerald-500",
  },
};

export function metricAverage(values: Array<number | null>): number | null {
  const nums = values.filter((v): v is number => v != null);
  if (!nums.length) return null;
  return Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10;
}

export function academicMonthOption(row: Record<string, unknown>, index: number): MonthOption | null {
  const key = asString(row.month);
  const label = asString(row.monthLabel) || key;
  const match = key.match(/^(\d{4})-(\d{1,2})$/);
  if (!match) {
    return {
      index,
      key,
      label,
      month: 0,
      year: 0,
      academicYear: "unknown",
      academicYearLabel: "Other",
    };
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month)) return null;
  if (month < 1 || month > 12) return null;
  if (month >= 6 && month <= 8) return null;

  const academicYearStart = month >= 9 ? year : year - 1;
  return {
    index,
    key,
    label,
    month,
    year,
    academicYear: String(academicYearStart),
    academicYearLabel: `${academicYearStart}-${String((academicYearStart + 1) % 100).padStart(2, "0")}`,
  };
}

export function previousAcademicValue(
  values: unknown[],
  monthOptions: MonthOption[],
  activeMonth: MonthOption,
): number | null {
  const activePosition = monthOptions.findIndex((month) => month.key === activeMonth.key);
  for (let i = activePosition - 1; i >= 0; i--) {
    const value = values[monthOptions[i].index];
    if (value != null && Number.isFinite(Number(value))) return Number(value);
  }
  return null;
}

export function deltaClass(delta: number | null): string {
  if (delta == null) return "text-muted-foreground";
  if (delta > 0) return "text-success";
  if (delta < 0) return "text-destructive";
  return "text-muted-foreground";
}

export function deltaLabel(delta: number | null): string {
  if (delta == null) return "No previous data";
  if (delta > 0) return `▲ ${delta.toFixed(1)}`;
  if (delta < 0) return `▼ ${Math.abs(delta).toFixed(1)}`;
  return "No change";
}

export function zoneForGroup(aap: number | null): string {
  if (aap == null) return "No data";
  if (aap >= 7) return "Green";
  if (aap >= 5) return "Yellow";
  return "Red";
}


export function latestCandidateEvent(candidate: Candidate) {
  const events = Array.isArray(candidate.events) ? candidate.events : [];
  return events[0] as Record<string, unknown> | undefined;
}

export function candidateEvents(candidate: Candidate) {
  return (Array.isArray(candidate.events) ? candidate.events : []) as Array<Record<string, unknown>>;
}

export function closedCandidateStage(candidate: Candidate) {
  const status = asString(candidate.status);
  if (status === "withdrawn") {
    return "withdrawn";
  }

  const rejectionEvent =
    candidateEvents(candidate).find((event) => {
      const result = asString(event.result).toLowerCase();
      return result.includes("reject") || result === "withdrawn";
    }) || latestCandidateEvent(candidate);
  const eventType = asString(rejectionEvent?.event_type).toLowerCase();
  const result = asString(rejectionEvent?.result).toLowerCase();

  if (eventType === "interview") return "interview";
  if (eventType === "math_test") return "math_test";
  if (
    eventType === "training_evaluation" ||
    eventType === "training_complete" ||
    eventType === "final_decision" ||
    result.includes("training")
  ) {
    return "training";
  }
  return "other";
}

export function parseIsoMillis(value: unknown): number | null {
  const normalized = asString(value);
  if (!normalized) return null;
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function daysSinceIso(value: unknown): number | null {
  const parsed = parseIsoMillis(value);
  if (parsed == null) return null;
  return Math.max(0, Math.floor((Date.now() - parsed) / 86_400_000));
}

export function candidateLastTouchedAt(candidate: Candidate): string {
  return (
    asString(latestCandidateEvent(candidate)?.created_at) ||
    asString(candidate.updated_at) ||
    asString(candidate.created_at)
  );
}

export function candidateAgeDays(candidate: Candidate): number | null {
  return daysSinceIso(candidateLastTouchedAt(candidate));
}

export function candidateEventLabel(event: Record<string, unknown>) {
  const eventType = asString(event.event_type).toLowerCase();
  const result = asString(event.result).toLowerCase();
  if (result === "scheduled") return "Interview scheduled";
  if (result === "passed") return "Passed";
  if (result === "rejected") return "Rejected";
  if (result === "awaiting_decision") return "Sent for final decision";
  if (result === "hired") return "Hired";
  if (result === "training_rejected") return "Rejected after training";
  if (result === "returned_to_training") return "Returned to training";
  if (result === "reopened") return "Reopened";
  if (result === "withdrawn") return "Withdrawn";
  if (eventType === "training_evaluation") return "Training evaluated";
  if (eventType === "created") return "Candidate added";
  return asString(event.result) || asString(event.event_type) || "Updated";
}

export function relativeDaysLabel(days: number | null) {
  if (days == null) return "No timestamp";
  if (days === 0) return "Today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

export function openTeacherCandidateView(
  switchAdminTab: (tab: "teachers") => void,
  {
    tab,
    filter,
    candidateId,
  }: {
    tab: "hiring" | "training" | "active";
    filter?: "in_training" | "passed" | "rejected";
    candidateId?: number;
  },
) {
  try {
    window.sessionStorage.setItem(TEACHER_TAB_STORAGE_KEY, tab);
    if (filter) {
      window.sessionStorage.setItem(TEACHER_TRAINING_FILTER_STORAGE_KEY, filter);
    }
    if (candidateId) {
      window.sessionStorage.setItem(TEACHER_DETAIL_CANDIDATE_STORAGE_KEY, String(candidateId));
    }
  } catch {
  }
  switchAdminTab("teachers");
}


export function roleStudentRows(state: any) {
  return Array.isArray(state.filteredStudents)
    ? (state.filteredStudents as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminStudents)
      ? (state.props.adminStudents as Array<Record<string, unknown>>)
      : [];
}

export function supportComplaintRows(state: any) {
  return Array.isArray(state.complaints)
    ? (state.complaints as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminComplaints)
      ? (state.props.adminComplaints as Array<Record<string, unknown>>)
      : [];
}

export function supportComplaintStatus(value: unknown) {
  const status = asString(value).toLowerCase();
  if (status === "in_progress" || status === "escalated" || status === "resolved") return status;
  return "new";
}

export function supportComplaintCategory(value: unknown) {
  const category = asString(value).toLowerCase();
  if (category === "direct_contact") return "Direct Contact";
  if (category === "complaint" || category === "other") return "Complaint";
  if (category === "lesson_quality") return "Lesson Quality";
  return category ? category.charAt(0).toUpperCase() + category.slice(1) : "Complaint";
}

export function supportComplaintTitle(complaint: Record<string, unknown>) {
  return asString(complaint.topic) || supportComplaintCategory(complaint.category);
}

export function paymentSummaryFor(child: Record<string, unknown>) {
  return child.payment_summary && typeof child.payment_summary === "object"
    ? (child.payment_summary as Record<string, unknown>)
    : {};
}

export function moneyValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
}

export function formatMoney(value: unknown, currency = "UZS") {
  const amount = moneyValue(value);
  if (amount <= 0) return `0 ${currency}`;
  return `${Math.round(amount).toLocaleString("en-US")} ${currency}`;
}

export function supportPaymentFollowUps(state: any) {
  const parents = Array.isArray(state.parentAccounts)
    ? (state.parentAccounts as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminParents)
      ? (state.props.adminParents as Array<Record<string, unknown>>)
      : [];
  return parents
    .flatMap((parent) => {
      const children = Array.isArray(parent.children)
        ? (parent.children as Array<Record<string, unknown>>)
        : [];
      return children.map((child) => {
        const summary = paymentSummaryFor(child);
        const debt = moneyValue(summary.debt_total);
        const due = moneyValue(summary.due_total);
        return {
          parent: asString(parent.login) || "Parent",
          child: asString(child.full_name) || "Student",
          studentRowId: getStudentRowId(child),
          currency: asString(summary.currency) || "UZS",
          debt,
          due,
          total: debt + due,
        };
      });
    })
    .filter((row) => row.total > 0)
    .sort((left, right) => right.total - left.total)
    .slice(0, 5);
}

export function studentDashboardCards({
  students,
  currentSchool,
  title,
  emptyText,
}: {
  students: Array<Record<string, unknown>>;
  currentSchool: string;
  title: string;
  emptyText: string;
}) {
  const visible = students.slice(0, 6);
  return (
    <ChartCard title={title} subtitle={`${students.length} student${students.length === 1 ? "" : "s"}`} icon={<Users className="h-4 w-4 text-info" />}>
      {visible.length ? (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((student) => {
            const studentRowId = getStudentRowId(student);
            const studentCode = getStudentCode(student);
            return (
              <a
                key={studentRowId || studentCode}
                href={routes.adminStudentPanel(studentRowId, currentSchool)}
                className="rounded-lg border border-foreground/8 bg-background px-3 py-3 transition-colors hover:bg-muted"
              >
                <p className="truncate text-sm font-bold">{asString(student.full_name) || "Student"}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  Code {studentCode || "-"} · {asString(student.school_name) || "School"}
                </p>
                <p className="mt-2 text-[11px] font-bold text-info">Open dashboard</p>
              </a>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
          <p className="text-sm font-bold">{emptyText}</p>
        </div>
      )}
    </ChartCard>
  );
}

