import { useMemo, useState, type ReactNode } from "react";
import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  BookOpen,
  Clock3,
  CreditCard,
  GraduationCap,
  MessageSquare,
  School,
  Trophy,
  Users,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, findPreferredMathSubject } from "../shared";

type ZoneKey = "red" | "yellow" | "green";

type MonthlyGroupRow = {
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

type ExamClassOption = { shortName: string; label: string; average: number | null; rows: Array<{ label: string; average: number | null }> };
type MonthOption = {
  index: number;
  key: string;
  label: string;
  month: number;
  year: number;
  academicYear: string;
  academicYearLabel: string;
};

type Candidate = Record<string, unknown>;

const TEACHER_TAB_STORAGE_KEY = "msi.admin.teacherTab";
const TEACHER_TRAINING_FILTER_STORAGE_KEY = "msi.admin.teacherTrainingFilter";
const TEACHER_DETAIL_CANDIDATE_STORAGE_KEY = "msi.admin.teacherDetailCandidateId";

const candidateStatusLabels: Record<string, string> = {
  new: "New",
  interview: "Interview",
  math_test: "Math Test",
  training_ready: "Training",
  training_passed: "Review",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const lineColors = ["#8b5cf6", "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#14b8a6", "#ec4899", "#64748b"];

const zoneStyles: Record<ZoneKey, { soft: string; text: string; ring: string; dot: string }> = {
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

function metricAverage(values: Array<number | null>): number | null {
  const nums = values.filter((v): v is number => v != null);
  if (!nums.length) return null;
  return Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10;
}

function academicMonthOption(row: Record<string, unknown>, index: number): MonthOption | null {
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

function previousAcademicValue(
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

function deltaClass(delta: number | null): string {
  if (delta == null) return "text-muted-foreground";
  if (delta > 0) return "text-success";
  if (delta < 0) return "text-destructive";
  return "text-muted-foreground";
}

function deltaLabel(delta: number | null): string {
  if (delta == null) return "No previous data";
  if (delta > 0) return `▲ ${delta.toFixed(1)}`;
  if (delta < 0) return `▼ ${Math.abs(delta).toFixed(1)}`;
  return "No change";
}

function zoneForGroup(aap: number | null): string {
  if (aap == null) return "No data";
  if (aap >= 7) return "Green";
  if (aap >= 5) return "Yellow";
  return "Red";
}

function Indicator({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad" | "info";
}) {
  const toneClass = {
    neutral: "border-border bg-surface text-foreground",
    info: "border-sky-200 bg-surface text-sky-800",
    good: "border-emerald-200 bg-surface text-emerald-800",
    warn: "border-amber-200 bg-surface text-amber-800",
    bad: "border-rose-200 bg-surface text-rose-800",
  }[tone];
  return (
    <div className={`min-w-0 rounded-lg border px-3 py-2 ${toneClass}`}>
      <p className="truncate text-[10px] font-bold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 truncate text-xl font-bold leading-none text-current">{value}</p>
      {detail ? <p className="mt-1 truncate text-[11px] font-semibold text-muted-foreground">{detail}</p> : null}
    </div>
  );
}

function latestCandidateEvent(candidate: Candidate) {
  const events = Array.isArray(candidate.events) ? candidate.events : [];
  return events[0] as Record<string, unknown> | undefined;
}

function candidateEvents(candidate: Candidate) {
  return (Array.isArray(candidate.events) ? candidate.events : []) as Array<Record<string, unknown>>;
}

function closedCandidateStage(candidate: Candidate) {
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

function parseIsoMillis(value: unknown): number | null {
  const normalized = asString(value);
  if (!normalized) return null;
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function daysSinceIso(value: unknown): number | null {
  const parsed = parseIsoMillis(value);
  if (parsed == null) return null;
  return Math.max(0, Math.floor((Date.now() - parsed) / 86_400_000));
}

function candidateLastTouchedAt(candidate: Candidate): string {
  return (
    asString(latestCandidateEvent(candidate)?.created_at) ||
    asString(candidate.updated_at) ||
    asString(candidate.created_at)
  );
}

function candidateAgeDays(candidate: Candidate): number | null {
  return daysSinceIso(candidateLastTouchedAt(candidate));
}

function candidateEventLabel(event: Record<string, unknown>) {
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

function relativeDaysLabel(days: number | null) {
  if (days == null) return "No timestamp";
  if (days === 0) return "Today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

function openTeacherCandidateView(
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

function ClosedCandidatesOverviewCard({
  candidates,
  onOpenRejected,
}: {
  candidates: Candidate[];
  onOpenRejected: () => void;
}) {
  const closedCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return ["rejected", "withdrawn"].includes(status);
  });

  if (!closedCandidates.length) {
    return null;
  }

  const stageGroups = [
    { key: "interview", label: "Interview", tone: "bg-amber-500" },
    { key: "math_test", label: "Math Test", tone: "bg-sky-500" },
    { key: "training", label: "Training / Final", tone: "bg-violet-500" },
    { key: "withdrawn", label: "Withdrawn", tone: "bg-slate-500" },
    { key: "other", label: "Other", tone: "bg-zinc-500" },
  ]
    .map((stage) => ({
      ...stage,
      candidates: closedCandidates.filter((candidate) => closedCandidateStage(candidate) === stage.key),
    }))
    .filter((stage) => stage.candidates.length);

  return (
    <ChartCard
      title="Closed Candidates"
      subtitle="Where hiring candidates are dropping out"
      icon={<X className="h-4 w-4 text-info" />}
      headerActions={
        <button
          type="button"
          onClick={onOpenRejected}
          className="inline-flex h-8 items-center rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold text-foreground hover:bg-muted"
        >
          Open Rejected Queue
        </button>
      }
    >
      <div className="rounded-lg border border-foreground/8 bg-background p-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold text-muted-foreground">Failure distribution</p>
          <span className="text-[11px] font-semibold text-muted-foreground">{closedCandidates.length} total</span>
        </div>
        <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-muted">
          {stageGroups.map((stage) => {
            const percent = Math.round((stage.candidates.length / closedCandidates.length) * 100);
            return (
              <button
                key={`${stage.key}-bar`}
                type="button"
                onClick={onOpenRejected}
                className={`${stage.tone} h-full transition-opacity hover:opacity-85`}
                style={{ width: `${percent}%` }}
                title={`${stage.label}: ${stage.candidates.length}`}
              />
            );
          })}
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {stageGroups.map((stage) => {
            const percent = Math.round((stage.candidates.length / closedCandidates.length) * 100);
            return (
              <div key={stage.key} className="rounded-lg border border-foreground/8 bg-surface p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${stage.tone}`} />
                      <span className="text-sm font-bold">{stage.label}</span>
                    </div>
                    <p className="mt-1 text-[11px] font-semibold text-muted-foreground">
                      {percent}% of closed candidates
                    </p>
                  </div>
                  <span className="text-sm font-bold">{stage.candidates.length}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {stage.candidates.map((candidate) => (
                    <button
                      type="button"
                      key={asNumber(candidate.id)}
                      onClick={onOpenRejected}
                      className="rounded-md bg-background px-2 py-1 text-[11px] font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    >
                      {asString(candidate.full_name)}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </ChartCard>
  );
}

function HrAttentionCard({
  urgentItems,
  onOpenItem,
}: {
  urgentItems: Array<{
    candidateId: number;
    fullName: string;
    title: string;
    detail: string;
    tone: "bad" | "warn" | "info";
    tab: "hiring" | "training";
    filter?: "in_training" | "passed" | "rejected";
  }>;
  onOpenItem: (item: {
    candidateId: number;
    tab: "hiring" | "training";
    filter?: "in_training" | "passed" | "rejected";
  }) => void;
}) {
  return (
    <ChartCard title="Attention Needed" subtitle="Candidates that likely need action today" icon={<Clock3 className="h-4 w-4 text-info" />}>
      {urgentItems.length ? (
        <div className="grid min-h-[22rem] content-start gap-2">
          {urgentItems.map((item) => {
            const toneClass =
              item.tone === "bad"
                ? "border-rose-200 bg-rose-50"
                : item.tone === "warn"
                  ? "border-amber-200 bg-amber-50"
                  : "border-sky-200 bg-sky-50";
            return (
              <button
                key={`${item.candidateId}-${item.title}`}
                type="button"
                onClick={() => onOpenItem(item)}
                className={`rounded-lg border px-3 py-3 text-left transition-colors hover:bg-muted ${toneClass}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold">{item.fullName}</p>
                    <p className="mt-1 text-xs font-semibold text-foreground/80">{item.title}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">{item.detail}</p>
                  </div>
                  <span className="rounded-md bg-background px-2 py-1 text-[10px] font-bold text-muted-foreground">
                    Open
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex min-h-[22rem] items-center justify-center rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
          <p className="text-sm font-bold">No urgent hiring blockers right now.</p>
        </div>
      )}
    </ChartCard>
  );
}

function ZonesDrawer({
  zoneRows,
  activeTab,
  onTabChange,
  onClose,
}: {
  zoneRows: Record<ZoneKey, Array<Record<string, unknown>>>;
  activeTab: ZoneKey;
  onTabChange: (tab: ZoneKey) => void;
  onClose: () => void;
}) {
  const tabs: { key: ZoneKey; label: string; icon: ReactNode; color: string }[] = [
    { key: "green",  label: "Green",  icon: <Trophy className="h-3.5 w-3.5" />,         color: "text-success" },
    { key: "yellow", label: "Yellow", icon: <AlertTriangle className="h-3.5 w-3.5" />,  color: "text-warning" },
    { key: "red",    label: "Red",    icon: <AlertCircle className="h-3.5 w-3.5" />,    color: "text-destructive" },
  ];
  const rows = zoneRows[activeTab];
  const activeColor = tabs.find((t) => t.key === activeTab)?.color ?? "";

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[24rem] flex-col border-l border-foreground/10 bg-surface shadow-xl sm:w-96">
      <div className="flex shrink-0 items-center justify-between border-b border-foreground/8 px-5 py-3.5">
        <p className="text-sm font-bold">Performance Zones</p>
        <button type="button" onClick={onClose} className="rounded-md p-1 hover:bg-foreground/5">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex shrink-0 gap-0.5 border-b border-foreground/8 px-4 pt-2">
        {tabs.map(({ key, label, icon, color }) => {
          const count = zoneRows[key].length;
          const isActive = key === activeTab;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onTabChange(key)}
              className={`flex items-center gap-1.5 rounded-t-md px-3 py-2 text-xs font-semibold transition-colors ${
                isActive
                  ? `border border-b-0 border-foreground/10 bg-background ${color}`
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>{icon}</span>
              {label}
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${isActive ? "bg-foreground/8" : "bg-foreground/5"}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto">
        {rows.length ? (
          <table className="w-full text-left">
            <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/8">
                {["Group", "Subject", "AAP", "AR"].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-foreground/5 hover:bg-foreground/2">
                  <td className="px-4 py-2.5 text-xs font-semibold">{asString(row.group_name)}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{asString(row.subject_name)}</td>
                  <td className={`px-4 py-2.5 text-xs font-bold ${activeColor}`}>
                    {row.aap == null ? "-" : asNumber(row.aap).toFixed(1)}
                  </td>
                  <td className="px-4 py-2.5 text-xs">
                    {row.ar == null ? "-" : `${asNumber(row.ar).toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="px-4 py-6 text-sm text-muted-foreground">No groups in this zone.</p>
        )}
      </div>
    </div>
  );
}

function RoleMetric({
  label,
  value,
  detail,
  icon,
  tone = "bg-surface",
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
  tone?: string;
}) {
  return (
    <div className={`rounded-lg border border-foreground/8 px-3 py-3 shadow-card ${tone}`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{label}</span>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-background text-foreground">{icon}</span>
      </div>
      <p className="text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
    </div>
  );
}

function roleStudentRows(state: any) {
  return Array.isArray(state.filteredStudents)
    ? (state.filteredStudents as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminStudents)
      ? (state.props.adminStudents as Array<Record<string, unknown>>)
      : [];
}

function supportComplaintRows(state: any) {
  return Array.isArray(state.complaints)
    ? (state.complaints as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminComplaints)
      ? (state.props.adminComplaints as Array<Record<string, unknown>>)
      : [];
}

function supportComplaintStatus(value: unknown) {
  const status = asString(value).toLowerCase();
  if (status === "in_progress" || status === "escalated" || status === "resolved") return status;
  return "new";
}

function supportComplaintCategory(value: unknown) {
  const category = asString(value).toLowerCase();
  if (category === "direct_contact") return "Direct Contact";
  if (category === "complaint" || category === "other") return "Complaint";
  if (category === "lesson_quality") return "Lesson Quality";
  return category ? category.charAt(0).toUpperCase() + category.slice(1) : "Complaint";
}

function supportComplaintTitle(complaint: Record<string, unknown>) {
  return asString(complaint.topic) || supportComplaintCategory(complaint.category);
}

function paymentSummaryFor(child: Record<string, unknown>) {
  return child.payment_summary && typeof child.payment_summary === "object"
    ? (child.payment_summary as Record<string, unknown>)
    : {};
}

function moneyValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
}

function formatMoney(value: unknown, currency = "UZS") {
  const amount = moneyValue(value);
  if (amount <= 0) return `0 ${currency}`;
  return `${Math.round(amount).toLocaleString("en-US")} ${currency}`;
}

function supportPaymentFollowUps(state: any) {
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
          studentId: asNumber(child.id),
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

function studentDashboardCards({
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
            const id = asNumber(student.id);
            return (
              <a
                key={id || asString(student.student_id)}
                href={routes.adminStudentDashboard(id, currentSchool)}
                className="rounded-lg border border-foreground/8 bg-background px-3 py-3 transition-colors hover:bg-muted"
              >
                <p className="truncate text-sm font-bold">{asString(student.full_name) || "Student"}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {asString(student.student_id) || `ID ${id}`} · {asString(student.school_name) || "School"}
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

function RoleOverviewPanel({ state }: { state: any }) {
  const mode = asString(state.adminMode).toLowerCase();
  const students = roleStudentRows(state);
  const teachers = Array.isArray(state.teachers) ? (state.teachers as Array<Record<string, unknown>>) : [];
  const candidates = Array.isArray(state.props?.adminTeacherCandidates)
    ? (state.props.adminTeacherCandidates as Array<Record<string, unknown>>)
    : [];
  const resources = Array.isArray(state.resourcesList) ? (state.resourcesList as Array<Record<string, unknown>>) : [];
  const announcements = Array.isArray(state.props?.adminAnnouncements)
    ? (state.props.adminAnnouncements as Array<Record<string, unknown>>)
    : [];
  const groups = Array.isArray(state.props?.adminAcademicGroups)
    ? (state.props.adminAcademicGroups as Array<Record<string, unknown>>)
    : [];
  const currentSchool = asString(state.currentSchool) || "all";
  const activeStudents = students.filter((student) => asString(student.last_seen_at)).length;
  const activePipelineCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return !["rejected", "withdrawn", "hired"].includes(status);
  });
  const closedCandidates = candidates.filter((candidate) => {
    const status = asString(candidate.status) || "new";
    return ["rejected", "withdrawn"].includes(status);
  });
  const hiredCandidates = candidates.filter((candidate) => asString(candidate.status) === "hired");
  const inTraining = candidates.filter((candidate) => asString(candidate.status) === "training_ready").length;
  const awaitingDecision = candidates.filter((candidate) => asString(candidate.status) === "training_passed").length;
  const newCandidates = candidates.filter((candidate) => asString(candidate.status) === "new").length;
  const interviewCandidates = candidates.filter((candidate) => asString(candidate.status) === "interview").length;
  const mathTestCandidates = candidates.filter((candidate) => asString(candidate.status) === "math_test").length;
  const hiresThisMonth = hiredCandidates.filter((candidate) => {
    const parsed = parseIsoMillis(candidateLastTouchedAt(candidate));
    if (parsed == null) return false;
    const date = new Date(parsed);
    const now = new Date();
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
  }).length;
  const closedDecisionCount = closedCandidates.length + hiredCandidates.length;
  const rejectionRate = closedDecisionCount ? Math.round((closedCandidates.length / closedDecisionCount) * 100) : 0;

  const urgentItems = activePipelineCandidates
    .map((candidate) => {
      const status = asString(candidate.status) || "new";
      const ageDays = candidateAgeDays(candidate);
      const evaluations = candidateEvents(candidate).filter((event) => asString(event.event_type) === "training_evaluation");
      if (status === "training_passed" && (ageDays ?? 0) >= 3) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Final decision overdue",
          detail: `${relativeDaysLabel(ageDays)} since sent for final review`,
          tone: "bad" as const,
          priority: 5,
          tab: "training" as const,
          filter: "passed" as const,
        };
      }
      if (status === "training_ready" && !evaluations.length && (ageDays ?? 0) >= 2) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Training needs first evaluation",
          detail: `${relativeDaysLabel(ageDays)} in training with no lesson review`,
          tone: "bad" as const,
          priority: 4,
          tab: "training" as const,
          filter: "in_training" as const,
        };
      }
      if (status === "training_ready" && (ageDays ?? 0) >= 5) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Training looks stalled",
          detail: `${relativeDaysLabel(ageDays)} since the last training activity`,
          tone: "warn" as const,
          priority: 3,
          tab: "training" as const,
          filter: "in_training" as const,
        };
      }
      if (status === "math_test" && (ageDays ?? 0) >= 2) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Math test pending follow-up",
          detail: `${relativeDaysLabel(ageDays)} waiting in the test stage`,
          tone: "warn" as const,
          priority: 2,
          tab: "hiring" as const,
        };
      }
      if (status === "interview" && (ageDays ?? 0) >= 2) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Interview queue is aging",
          detail: `${relativeDaysLabel(ageDays)} in interview stage`,
          tone: "info" as const,
          priority: 1,
          tab: "hiring" as const,
        };
      }
      if (status === "new" && (ageDays ?? 0) >= 1) {
        return {
          candidateId: asNumber(candidate.id),
          fullName: asString(candidate.full_name) || "Candidate",
          title: "Needs first screening",
          detail: `${relativeDaysLabel(ageDays)} since application was added`,
          tone: "info" as const,
          priority: 0,
          tab: "hiring" as const,
        };
      }
      return null;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null)
    .sort((left, right) => {
      if (left.priority !== right.priority) return right.priority - left.priority;
      return right.candidateId - left.candidateId;
    })
    .slice(0, 4);

  const pipelineSnapshotStages = [
    { key: "new", label: "New", count: newCandidates, tone: "bg-sky-500", tab: "hiring" as const },
    {
      key: "interview_test",
      label: "Interview / Test",
      count: interviewCandidates + mathTestCandidates,
      tone: "bg-amber-500",
      tab: "hiring" as const,
    },
    {
      key: "training_ready",
      label: "Training",
      count: inTraining,
      tone: "bg-emerald-500",
      tab: "training" as const,
      filter: "in_training" as const,
    },
    {
      key: "training_passed",
      label: "Review",
      count: awaitingDecision,
      tone: "bg-violet-500",
      tab: "training" as const,
      filter: "passed" as const,
    },
  ];
  const openPipelineTotal = Math.max(
    1,
    pipelineSnapshotStages.reduce((sum, stage) => sum + stage.count, 0),
  );

  function openRejectedQueue() {
    openTeacherCandidateView(state.switchAdminTab, {
      tab: "training",
      filter: "rejected",
    });
  }

  if (mode === "student" || mode === "parent") {
    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-3">
          <RoleMetric label="Students" value={students.length} detail="dashboard access" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
          <RoleMetric label="Resources" value={resources.length} detail="available learning materials" icon={<BookOpen className="h-4 w-4" />} tone="bg-emerald-50" />
          <RoleMetric label="Announcements" value={announcements.length} detail="school updates" icon={<AlertCircle className="h-4 w-4" />} tone="bg-amber-50" />
        </div>
        {studentDashboardCards({
          students,
          currentSchool,
          title: mode === "parent" ? "Student Dashboard" : "My Dashboard",
          emptyText: "No student dashboard is available yet.",
        })}
      </div>
    );
  }

  if (mode === "hr") {
    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <RoleMetric label="New" value={newCandidates} detail="fresh applications" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
          <RoleMetric label="Training" value={inTraining} detail="trainees in lessons" icon={<GraduationCap className="h-4 w-4" />} tone="bg-emerald-50" />
          <RoleMetric label="Review" value={awaitingDecision} detail="awaiting final decision" icon={<Trophy className="h-4 w-4" />} tone="bg-violet-50" />
          <RoleMetric label="Overdue" value={urgentItems.length} detail="need attention now" icon={<Clock3 className="h-4 w-4" />} tone={urgentItems.length ? "bg-rose-50" : "bg-slate-50"} />
        </div>
        <div className="grid items-stretch gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <HrAttentionCard
            urgentItems={urgentItems}
            onOpenItem={(item) =>
              openTeacherCandidateView(state.switchAdminTab, {
                tab: item.tab,
                filter: item.filter,
                candidateId: item.candidateId,
              })
            }
          />
          <ChartCard title="Pipeline Snapshot" subtitle="Open queue only" icon={<BarChart3 className="h-4 w-4 text-info" />}>
            <div className="flex min-h-[22rem] flex-col rounded-lg border border-foreground/8 bg-background p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold text-muted-foreground">Stage distribution</p>
                <span className="text-[11px] font-semibold text-muted-foreground">
                  {activePipelineCandidates.length} open
                </span>
              </div>
              <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-muted">
                {pipelineSnapshotStages.map((stage) => {
                  const percent = Math.round((stage.count / openPipelineTotal) * 100);
                  return (
                    <button
                      key={`${stage.key}-snapshot`}
                      type="button"
                      onClick={() => openTeacherCandidateView(state.switchAdminTab, stage)}
                      className={`${stage.tone} h-full transition-opacity hover:opacity-85`}
                      style={{ width: `${percent}%` }}
                      title={`${stage.label}: ${stage.count}`}
                    />
                  );
                })}
              </div>
              <div className="mt-4 space-y-2">
                {pipelineSnapshotStages.map((stage) => {
                  const percent = Math.round((stage.count / openPipelineTotal) * 100);
                  return (
                    <button
                      key={stage.key}
                      type="button"
                      onClick={() => openTeacherCandidateView(state.switchAdminTab, stage)}
                      className="flex w-full items-center gap-3 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-surface"
                    >
                      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${stage.tone}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm font-bold">{stage.label}</span>
                          <span className="text-base font-bold tabular-nums">{stage.count}</span>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">{percent}% of open queue</p>
                      </div>
                    </button>
                  );
                })}
              </div>
              <div className="mt-auto grid gap-2 border-t border-foreground/8 pt-3 sm:grid-cols-3">
                {[
                  {
                    label: "Open",
                    value: activePipelineCandidates.length,
                    detail: "not yet closed",
                    tone: "text-sky-700",
                  },
                  {
                    label: "Hired",
                    value: hiresThisMonth,
                    detail: "this month",
                    tone: "text-emerald-700",
                  },
                  {
                    label: "Reject Rate",
                    value: `${rejectionRate}%`,
                    detail: `${closedDecisionCount} resolved`,
                    tone:
                      rejectionRate >= 60
                        ? "text-rose-700"
                        : rejectionRate >= 35
                          ? "text-amber-700"
                          : "text-emerald-700",
                  },
                ].map((item) => (
                  <div key={item.label} className="rounded-md bg-surface px-3 py-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{item.label}</p>
                    <div className="mt-1 flex items-end justify-between gap-2">
                      <p className={`text-lg font-bold leading-none ${item.tone}`}>{item.value}</p>
                      <p className="text-[11px] font-semibold text-muted-foreground">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>
        </div>
        <ClosedCandidatesOverviewCard candidates={candidates} onOpenRejected={openRejectedQueue} />
      </div>
    );
  }

  if (mode === "sales") {
    const complaints = supportComplaintRows(state);
    const newComplaints = complaints.filter((item) => supportComplaintStatus(item.status) === "new");
    const escalatedComplaints = complaints.filter((item) => supportComplaintStatus(item.status) === "escalated");
    const openComplaints = complaints.filter((item) => supportComplaintStatus(item.status) !== "resolved");
    const paymentFollowUps = supportPaymentFollowUps(state);
    const unresolvedPaymentTotal = paymentFollowUps.reduce((sum, item) => sum + item.total, 0);
    return (
      <div className="space-y-3">
        <div className="grid gap-2 md:grid-cols-4">
          <button type="button" onClick={() => state.switchAdminTab("complaints")} className="text-left">
            <RoleMetric label="New Complaints" value={newComplaints.length} detail="need first reply" icon={<AlertCircle className="h-4 w-4" />} tone="bg-amber-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("complaints")} className="text-left">
            <RoleMetric label="Escalated" value={escalatedComplaints.length} detail="CEO attention" icon={<AlertTriangle className="h-4 w-4" />} tone="bg-rose-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("payments")} className="text-left">
            <RoleMetric label="Unresolved Payments" value={paymentFollowUps.length} detail={formatMoney(unresolvedPaymentTotal)} icon={<CreditCard className="h-4 w-4" />} tone="bg-sky-50" />
          </button>
          <button type="button" onClick={() => state.switchAdminTab("chat")} className="text-left">
            <RoleMetric label="Chats" value="Open" detail="parent conversations" icon={<MessageSquare className="h-4 w-4" />} tone="bg-violet-50" />
          </button>
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <ChartCard title="Complaint Queue" subtitle={`${openComplaints.length} open`} icon={<MessageSquare className="h-4 w-4 text-info" />}>
            {openComplaints.length ? (
              <div className="space-y-2">
                {openComplaints.slice(0, 5).map((complaint) => (
                  <button
                    key={asNumber(complaint.id)}
                    type="button"
                    onClick={() => state.switchAdminTab("complaints")}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-3 text-left transition-colors hover:bg-muted"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-bold">{supportComplaintTitle(complaint)}</p>
                      <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold">
                        {supportComplaintStatus(complaint.status) === "escalated" ? "Escalated" : supportComplaintStatus(complaint.status) === "in_progress" ? "In Progress" : "New"}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {asString(complaint.parent_login) || "Parent"} · {asString(complaint.student_name) || "Student"} · {supportComplaintCategory(complaint.category)}
                    </p>
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-foreground/75">{asString(complaint.message)}</p>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold">No open complaints right now.</p>
              </div>
            )}
          </ChartCard>

          <ChartCard title="Payment Follow-Up" subtitle={`${paymentFollowUps.length} families`} icon={<CreditCard className="h-4 w-4 text-info" />}>
            {paymentFollowUps.length ? (
              <div className="space-y-2">
                {paymentFollowUps.map((item) => (
                  <button
                    key={`${item.parent}-${item.studentId}`}
                    type="button"
                    onClick={() => state.switchAdminTab("payments")}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-3 text-left transition-colors hover:bg-muted"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold">{item.parent}</p>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{item.child}</p>
                      </div>
                      <p className="shrink-0 text-sm font-bold">{formatMoney(item.total, item.currency)}</p>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                <p className="text-sm font-bold">No unresolved payments right now.</p>
              </div>
            )}
          </ChartCard>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-2 md:grid-cols-4">
        <RoleMetric label="My Students" value={students.length} detail="visible student records" icon={<Users className="h-4 w-4" />} tone="bg-sky-50" />
        <RoleMetric label="Groups" value={groups.length} detail="class groups" icon={<School className="h-4 w-4" />} tone="bg-emerald-50" />
        <RoleMetric label="Resources" value={resources.length} detail="teaching materials" icon={<BookOpen className="h-4 w-4" />} tone="bg-amber-50" />
        <RoleMetric label="Announcements" value={announcements.length} detail="class updates" icon={<AlertCircle className="h-4 w-4" />} tone="bg-violet-50" />
      </div>
      {studentDashboardCards({
        students,
        currentSchool,
        title: "Class Student Dashboards",
        emptyText: "No students are assigned to this teacher view yet.",
      })}
    </div>
  );
}

function SchoolOverviewPanel({ state }: { state: any }) {
  const {
    quickStats,
    selectedOverviewSchool,
    setSelectedOverviewSchool,
    setSelectedSehriyoGrade,
    subjectInfo,
    setSelectedSubjectName,
    availableSubjectSchools,
    selectedSubjectName,
    schoolSubjectRows,
    selectedSubjectRow,
    availableOverviewGrades,
    activeOverviewGrade,
    selectedGroupRows,
    filteredExamSeries,
    filteredMonthlyArSeries,
    monthlyChartData,
    monthlySeries,
    props,
  } = state;

  const [selectedExam, setSelectedExam] = useState("");
  const [selectedTrendMonth, setSelectedTrendMonth] = useState("all");
  const [selectedAcademicYear, setSelectedAcademicYear] = useState("");
  const [graphMetric, setGraphMetric] = useState<"aap" | "attendance" | "exam">("aap");
  const [zonesOpen, setZonesOpen] = useState(false);
  const [zonesTab, setZonesTab] = useState<ZoneKey>("green");

  const monthOptions = useMemo<MonthOption[]>(
    () =>
      monthlyChartData
        .map((row: Record<string, unknown>, index: number) => academicMonthOption(row, index))
        .filter((option: MonthOption | null): option is MonthOption => option !== null),
    [monthlyChartData],
  );
  const academicYearOptions = useMemo(() => {
    const years = new Map<string, { key: string; label: string; startYear: number }>();
    for (const month of monthOptions) {
      const startYear = Number(month.academicYear);
      if (!years.has(month.academicYear)) {
        years.set(month.academicYear, {
          key: month.academicYear,
          label: month.academicYearLabel,
          startYear: Number.isFinite(startYear) ? startYear : -1,
        });
      }
    }
    return Array.from(years.values()).sort((left, right) => right.startYear - left.startYear);
  }, [monthOptions]);
  const selectedAcademicYearKey =
    selectedAcademicYear && academicYearOptions.some((year) => year.key === selectedAcademicYear)
      ? selectedAcademicYear
      : academicYearOptions[0]?.key || "";
  const selectedAcademicYearLabel =
    academicYearOptions.find((year) => year.key === selectedAcademicYearKey)?.label || "Academic Year";
  const visibleMonthOptions = selectedAcademicYearKey
    ? monthOptions.filter((month) => month.academicYear === selectedAcademicYearKey)
    : monthOptions;

  const activeMonth =
    (selectedTrendMonth !== "all"
      ? visibleMonthOptions.find((m: MonthOption) => m.key === selectedTrendMonth)
      : null) ||
    visibleMonthOptions[visibleMonthOptions.length - 1];

  const monthlyRows = useMemo(() => {
    if (!activeMonth) return [];
    return monthlySeries
      .map((seriesRow: Record<string, unknown>) => {
        const label = asString(seriesRow.label);
        const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
        const currentRaw = values[activeMonth.index];
        const current = currentRaw == null || !Number.isFinite(Number(currentRaw)) ? null : Number(currentRaw);
        const previous = previousAcademicValue(values, visibleMonthOptions, activeMonth);
        const groupRow = selectedGroupRows.find((row: Record<string, unknown>) => asString(row.label) === label);
        const delta = current != null && previous != null ? current - previous : null;
        const arSeriesRow = (filteredMonthlyArSeries as Array<Record<string, unknown>>).find(
          (row) => asString(row.label) === label,
        );
        const arValues = Array.isArray(arSeriesRow?.values) ? (arSeriesRow.values as unknown[]) : [];
        const arRaw = arValues[activeMonth.index];
        const monthly_ar = arRaw == null || !Number.isFinite(Number(arRaw)) ? null : Number(arRaw);
        const overall_ar = groupRow?.avg_ar == null ? null : asNumber(groupRow.avg_ar);
        return {
          label,
          students: asNumber(groupRow?.students_count),
          current,
          previous,
          delta,
          ar: overall_ar,
          monthly_ar,
          display_ar: monthly_ar ?? overall_ar,
          zone: zoneForGroup(current),
        };
      })
      .sort((left: MonthlyGroupRow, right: MonthlyGroupRow) => {
        return (left.current ?? -1) - (right.current ?? -1);
      });
  }, [activeMonth, monthlySeries, selectedGroupRows, filteredMonthlyArSeries, visibleMonthOptions]);

  const monthAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.current));
  const previousAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.previous));
  const monthDelta = monthAverage != null && previousAverage != null ? monthAverage - previousAverage : null;
  const groupsWithData = monthlyRows.filter((row: MonthlyGroupRow) => row.current != null).length;
  const weakestRows = monthlyRows.filter((row: MonthlyGroupRow) => row.current != null).slice(0, 3);
  const monthArAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.monthly_ar));
  const prevMonthArAverage = useMemo(() => {
    if (!activeMonth) return null;
    const prevValues = (filteredMonthlyArSeries as Array<Record<string, unknown>>).map((seriesRow) => {
      const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      return previousAcademicValue(values, visibleMonthOptions, activeMonth);
    });
    return metricAverage(prevValues);
  }, [activeMonth, filteredMonthlyArSeries, visibleMonthOptions]);
  const monthArDelta = monthArAverage != null && prevMonthArAverage != null ? monthArAverage - prevMonthArAverage : null;

  const zoneRows = {
    red:    Array.isArray(props.adminGroupZones?.red)    ? props.adminGroupZones.red    : [],
    yellow: Array.isArray(props.adminGroupZones?.yellow) ? props.adminGroupZones.yellow : [],
    green:  Array.isArray(props.adminGroupZones?.green)  ? props.adminGroupZones.green  : [],
  } as Record<ZoneKey, Array<Record<string, unknown>>>;

  const examLabels = Array.isArray(selectedSubjectRow?.exam_labels)
    ? (selectedSubjectRow.exam_labels as unknown[]).map((label) => asString(label)).filter(Boolean)
    : [];
  const examSeries = filteredExamSeries as Array<Record<string, unknown>>;
  const EXAM_SHORT: Record<string, string> = {
    "Half-term Test 1": "HFT1",
    "End-of-term Test 1": "ET1",
    "Half-term Test 2": "HFT2",
    "End-of-term Test 2": "ET2",
    "Half-term Test 3": "HFT3",
    "End-of-term Test 3": "ET3",
    "Half-term Test 4": "HFT4",
  };
  const EXAM_ORDER = ["HFT1", "ET1", "HFT2", "ET2", "HFT3", "ET3", "HFT4"];
  const shortExamName = (label: string) => {
    const normalized = label.replace(/\s+/g, " ").trim();
    const compact = normalized.replace(/[\s_-]+/g, "").toUpperCase();
    if (/^HFT\d+$/.test(compact) || /^ET\d+$/.test(compact)) return compact;
    return EXAM_SHORT[normalized] ?? normalized;
  };
  const examAverageBuckets = new Map<string, { labels: string[]; values: number[]; classValues: Map<string, number[]> }>();
  examLabels.forEach((examLabel, index) => {
    const shortName = shortExamName(examLabel);
    const bucket = examAverageBuckets.get(shortName) ?? { labels: [], values: [], classValues: new Map<string, number[]>() };
    if (!bucket.labels.includes(examLabel)) bucket.labels.push(examLabel);
    examSeries.forEach((seriesRow) => {
      const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      const value = rawValues[index];
      if (value != null && Number.isFinite(Number(value))) {
        const numericValue = Number(value);
        const classLabel = asString(seriesRow.label);
        bucket.values.push(numericValue);
        if (classLabel) {
          const classValues = bucket.classValues.get(classLabel) ?? [];
          classValues.push(numericValue);
          bucket.classValues.set(classLabel, classValues);
        }
      }
    });
    examAverageBuckets.set(shortName, bucket);
  });
  const examClassOptions: ExamClassOption[] = Array.from(examAverageBuckets.entries()).map(([shortName, bucket]) => ({
    label: bucket.labels.join(" / "),
    shortName,
    average: metricAverage(bucket.values),
    rows: Array.from(bucket.classValues.entries())
      .map(([label, values]) => ({ label, average: metricAverage(values) }))
      .filter((row) => row.average != null)
      .sort((a, b) => (a.average ?? -1) - (b.average ?? -1)),
  })).sort((a, b) => {
    const ai = EXAM_ORDER.indexOf(a.shortName || "");
    const bi = EXAM_ORDER.indexOf(b.shortName || "");
    if (ai === -1 && bi === -1) return (a.shortName || a.label).localeCompare(b.shortName || b.label);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
  const examView = selectedExam || "all";
  const activeExamOption =
    examView === "all"
      ? null
      : examClassOptions.find((option) => option.shortName === examView) ||
        examClassOptions[examClassOptions.length - 1];
  const examSelectValue = examView === "all" ? "all" : activeExamOption?.shortName || "all";
  const examClassLineData = examClassOptions.map((option) => {
    const row: Record<string, string | number | null> = {
      label: option.label,
      shortName: option.shortName,
    };
    option.rows.forEach((classRow) => {
      row[classRow.label] = classRow.average;
    });
    return row;
  });
  const examClassLineLabels = Array.from(
    new Set(examClassOptions.flatMap((option) => option.rows.map((row) => row.label))),
  );

  const activeTrendMonth =
    selectedTrendMonth === "all"
      ? null
      : visibleMonthOptions.find((month: MonthOption) => month.key === selectedTrendMonth) ||
        visibleMonthOptions[visibleMonthOptions.length - 1];
  const trendMonthRows = activeTrendMonth
    ? monthlySeries
        .map((seriesRow: Record<string, unknown>) => {
          const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
          const value = rawValues[activeTrendMonth.index];
          return {
            label: asString(seriesRow.label),
            average: value == null || !Number.isFinite(Number(value)) ? null : Number(value),
          };
        })
        .filter(
          (row: { label: string; average: number | null }) =>
            row.label && row.average != null,
        )
        .sort(
          (
            a: { label: string; average: number | null },
            b: { label: string; average: number | null },
          ) => (a.average ?? -1) - (b.average ?? -1),
        )
    : [];
  const monthlyClassLineData = visibleMonthOptions.map((monthOption: MonthOption) => {
    const point: Record<string, string | number | null> = {
      label: monthOption.label,
    };
    monthlySeries.forEach((seriesRow: Record<string, unknown>) => {
      const classLabel = asString(seriesRow.label);
      const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      const value = rawValues[monthOption.index];
      if (classLabel) {
        point[classLabel] = value == null || !Number.isFinite(Number(value)) ? null : Number(value);
      }
    });
    return point;
  });
  const monthlyClassLineLabels = (monthlySeries as Array<Record<string, unknown>>)
    .map((seriesRow) => asString(seriesRow.label))
    .filter(Boolean);
  const attendanceClassLineData = visibleMonthOptions.map((monthOption: MonthOption) => {
    const point: Record<string, string | number | null> = {
      label: monthOption.label,
    };
    (filteredMonthlyArSeries as Array<Record<string, unknown>>).forEach((seriesRow) => {
      const classLabel = asString(seriesRow.label);
      const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      const value = rawValues[monthOption.index];
      if (classLabel) {
        point[classLabel] = value == null || !Number.isFinite(Number(value)) ? null : Number(value);
      }
    });
    return point;
  });
  const attendanceClassLineLabels = (filteredMonthlyArSeries as Array<Record<string, unknown>>)
    .map((seriesRow) => asString(seriesRow.label))
    .filter(Boolean);
  const attendanceMonthRows = activeTrendMonth
    ? (filteredMonthlyArSeries as Array<Record<string, unknown>>)
        .map((seriesRow) => {
          const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
          const value = rawValues[activeTrendMonth.index];
          return {
            label: asString(seriesRow.label),
            average: value == null || !Number.isFinite(Number(value)) ? null : Number(value),
          };
        })
        .filter((row) => row.label && row.average != null)
        .sort((a, b) => (a.average ?? -1) - (b.average ?? -1))
    : [];
  const graphViewValue = graphMetric === "exam" ? examSelectValue : selectedTrendMonth;
  const graphLineData =
    graphMetric === "exam"
      ? examClassLineData
      : graphMetric === "attendance"
        ? attendanceClassLineData
        : monthlyClassLineData;
  const graphLineLabels =
    graphMetric === "exam"
      ? examClassLineLabels
      : graphMetric === "attendance"
        ? attendanceClassLineLabels
        : monthlyClassLineLabels;
  const graphBarRows =
    graphMetric === "exam"
      ? activeExamOption?.rows || []
      : graphMetric === "attendance"
        ? attendanceMonthRows
        : trendMonthRows;
  const graphIsAll = graphViewValue === "all";
  const graphDomain: [number, number] = graphMetric === "attendance" ? [0, 100] : [0, 9];
  const graphStroke = graphMetric === "exam" ? "#8b5cf6" : graphMetric === "attendance" ? "#10b981" : "#2563eb";
  const graphGridStroke = graphMetric === "exam" ? "#ede9fe" : graphMetric === "attendance" ? "#ccfbf1" : "#dbeafe";
  const graphBorderClass =
    graphMetric === "exam"
      ? "border-violet-100 bg-gradient-to-br from-white via-violet-50/70 to-sky-50/60"
      : graphMetric === "attendance"
        ? "border-emerald-100 bg-gradient-to-br from-white via-emerald-50/70 to-cyan-50/60"
        : "border-sky-100 bg-gradient-to-br from-sky-50 via-white to-emerald-50";
  const graphTitle =
    graphMetric === "exam"
      ? graphIsAll
        ? "Class scores across all exams."
        : "Class averages for the selected exam."
      : graphMetric === "attendance"
        ? graphIsAll
          ? "Class attendance across all months."
          : "Class attendance for the selected month."
        : graphIsAll
          ? "Class AAP across all months."
          : "Class AAP for the selected month.";
  const graphValueLabel = graphMetric === "attendance" ? "Attendance" : graphMetric === "exam" ? "Exam score" : "AAP";
  const formatGraphValue = (value: unknown) => {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "-";
    return graphMetric === "attendance" ? `${numericValue.toFixed(1)}%` : numericValue.toFixed(1);
  };
  const criticalRows = monthlyRows
    .filter((row: MonthlyGroupRow) => row.current != null && row.current < 5)
    .slice(0, 3);
  const watchRows = monthlyRows
    .filter((row: MonthlyGroupRow) => row.current != null && row.current >= 5 && row.current < 7)
    .slice(0, 3);
  const attendanceRiskRows = monthlyRows
    .filter((row: MonthlyGroupRow) => row.display_ar != null && row.display_ar < 70)
    .sort((left: MonthlyGroupRow, right: MonthlyGroupRow) => (left.display_ar ?? 999) - (right.display_ar ?? 999))
    .slice(0, 3);
  const fallingTrendRows = monthlyRows
    .filter((row: MonthlyGroupRow) => row.delta != null && row.delta < 0)
    .sort((left: MonthlyGroupRow, right: MonthlyGroupRow) => (left.delta ?? 0) - (right.delta ?? 0))
    .slice(0, 3);

  return (
    <div className="space-y-3">
      {zonesOpen && (
        <ZonesDrawer
          zoneRows={zoneRows}
          activeTab={zonesTab}
          onTabChange={setZonesTab}
          onClose={() => setZonesOpen(false)}
        />
      )}

      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 shadow-card">
        {[
          { label: "Students", value: asNumber(quickStats.total_students), icon: <Users className="h-3.5 w-3.5" />, color: "bg-slate-100 text-slate-800 border border-border" },
          { label: "Schools", value: asNumber(quickStats.total_schools), icon: <School className="h-3.5 w-3.5" />, color: "bg-slate-100 text-slate-800 border border-border" },
          { label: "Teachers", value: asNumber(quickStats.total_teachers), icon: <GraduationCap className="h-3.5 w-3.5" />, color: "bg-slate-100 text-slate-800 border border-border" },
          { label: "Subjects", value: asNumber(quickStats.total_subjects), icon: <BookOpen className="h-3.5 w-3.5" />, color: "bg-slate-100 text-slate-800 border border-border" },
        ].map((item) => (
          <span key={item.label} className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold ${item.color}`}>
            {item.icon}
            <span className="font-bold text-current">{item.value}</span>
            {item.label}
          </span>
        ))}
      </div>

      <ChartCard
        title="Subject Performance"
        icon={<BarChart3 className="h-4 w-4 text-info" />}
        headerActions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedOverviewSchool}
              onChange={(event) => {
                const nextSchool = event.target.value;
                setSelectedOverviewSchool(nextSchool);
                setSelectedSehriyoGrade("");
                setSelectedExam("");
                setSelectedAcademicYear("");
                setSelectedTrendMonth("all");
                const nextRows = subjectInfo.filter(
                  (row: Record<string, unknown>) => asString(row.school_key).toLowerCase() === nextSchool,
                );
                setSelectedSubjectName(
                  findPreferredMathSubject(nextRows.map((row: Record<string, unknown>) => asString(row.subject_name))),
                );
              }}
              className="min-w-0 max-w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-xs font-medium outline-none sm:min-w-36"
            >
              {availableSubjectSchools.map((option: { code: string; label: string }) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={selectedSubjectName}
              onChange={(event) => {
                setSelectedSubjectName(event.target.value);
                setSelectedSehriyoGrade("");
                setSelectedExam("");
                setSelectedAcademicYear("");
                setSelectedTrendMonth("all");
              }}
              className="min-w-0 max-w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-xs font-medium outline-none sm:min-w-52"
            >
              {schoolSubjectRows.map((row: Record<string, unknown>) => (
                <option key={asString(row.subject_name)} value={asString(row.subject_name)}>
                  {asString(row.subject_name)}
                </option>
              ))}
            </select>
          </div>
        }
      >
        {selectedSubjectRow ? (
          <div className="space-y-3">
            <div className="grid gap-2 md:grid-cols-4">
              <Indicator
                label="AAP"
                value={monthAverage == null ? "-" : monthAverage.toFixed(1)}
                tone={monthAverage == null ? "neutral" : monthAverage >= 7 ? "good" : monthAverage >= 5 ? "warn" : "bad"}
                detail={
                  monthAverage == null
                    ? "No data"
                    : monthDelta == null
                      ? "No previous data"
                      : `${deltaLabel(monthDelta)} from previous`
                }
              />
              <Indicator
                label="Attendance"
                value={monthArAverage == null ? "-" : `${monthArAverage.toFixed(1)}%`}
                tone={monthArAverage == null ? "neutral" : monthArAverage >= 85 ? "good" : monthArAverage >= 70 ? "warn" : "bad"}
                detail={
                  monthArAverage == null
                    ? "No attendance data"
                    : monthArDelta == null
                      ? "No previous data"
                      : `${deltaLabel(monthArDelta)} from previous`
                }
              />
              <Indicator
                label="Groups"
                value={`${groupsWithData}/${monthlyRows.length}`}
                tone="info"
                detail="with data"
              />
              <Indicator
                label="Needs Attention"
                value={zoneRows.red.length + zoneRows.yellow.length}
                tone={zoneRows.red.length ? "bad" : zoneRows.yellow.length ? "warn" : "good"}
                detail={weakestRows.length ? `${weakestRows[0].label} lowest` : "No flagged groups"}
              />
            </div>

            <div className={`rounded-xl border p-3 ${graphBorderClass}`}>
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold">Performance Graph</p>
                  <p className="text-xs text-muted-foreground">{graphTitle}</p>
                </div>
                <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
                  <select
                    value={graphMetric}
                    onChange={(event) => {
                      const nextMetric = event.target.value as "aap" | "attendance" | "exam";
                      setGraphMetric(nextMetric);
                      if (nextMetric === "exam") {
                        setSelectedExam("");
                      } else {
                        setSelectedTrendMonth("all");
                      }
                    }}
                    className="h-8 min-w-24 rounded-md border border-foreground/10 bg-white/85 px-2 text-xs font-bold text-foreground outline-none"
                  >
                    <option value="aap">AAP</option>
                    <option value="attendance">Attendance</option>
                    <option value="exam">Exam</option>
                  </select>
                  {Array.isArray(availableOverviewGrades) && availableOverviewGrades.length > 1 ? (
                    <select
                      value={activeOverviewGrade || availableOverviewGrades[0]}
                      onChange={(event) => {
                        setSelectedSehriyoGrade(event.target.value as "7" | "8");
                        setSelectedExam("");
                        setSelectedAcademicYear("");
                        setSelectedTrendMonth("all");
                      }}
                      className="h-8 min-w-24 rounded-md border border-foreground/10 bg-white/85 px-2 text-xs font-bold text-foreground outline-none"
                      aria-label="Class"
                    >
                      {availableOverviewGrades.map((grade: "7" | "8") => (
                        <option key={grade} value={grade}>
                          Grade {grade}
                        </option>
                      ))}
                    </select>
                  ) : null}
                  {graphMetric === "exam" ? (
                    <select
                      value={examSelectValue}
                      onChange={(event) => setSelectedExam(event.target.value)}
                      className="h-8 min-w-24 rounded-md border border-violet-200 bg-white/85 px-2 text-xs font-bold text-violet-700 outline-none"
                    >
                      <option value="all">All</option>
                      {examClassOptions.map((option) => (
                        <option key={option.shortName} value={option.shortName}>
                          {option.shortName}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <>
                      {academicYearOptions.length > 1 ? (
                        <select
                          value={selectedAcademicYearKey}
                          onChange={(event) => {
                            setSelectedAcademicYear(event.target.value);
                            setSelectedTrendMonth("all");
                          }}
                          className="h-8 min-w-28 rounded-md border border-sky-200 bg-white/85 px-2 text-xs font-bold text-sky-700 outline-none"
                          aria-label="Academic year"
                        >
                          {academicYearOptions.map((year) => (
                            <option key={year.key} value={year.key}>
                              {year.label}
                            </option>
                          ))}
                        </select>
                      ) : null}
                      <select
                        value={
                          selectedTrendMonth === "all" ||
                          visibleMonthOptions.some((month) => month.key === selectedTrendMonth)
                            ? selectedTrendMonth
                            : "all"
                        }
                        onChange={(event) => setSelectedTrendMonth(event.target.value)}
                        className="h-8 min-w-32 rounded-md border border-sky-200 bg-white/85 px-2 text-xs font-bold text-sky-700 outline-none"
                        aria-label="Month"
                      >
                        <option value="all">All {selectedAcademicYearLabel}</option>
                        {visibleMonthOptions.map((month: MonthOption) => (
                          <option key={month.key || month.index} value={month.key}>
                            {month.label}
                          </option>
                        ))}
                      </select>
                    </>
                  )}
                </div>
              </div>

              {graphIsAll && graphLineLabels.length ? (
                <div className="h-[18rem] sm:h-[20rem] xl:h-[21rem]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={graphLineData} margin={{ top: 10, right: 12, left: -6, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke={graphGridStroke} strokeDasharray="4 4" />
                      <XAxis dataKey={graphMetric === "exam" ? "shortName" : "label"} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis domain={graphDomain} tick={{ fontSize: 10 }} width={36} tickMargin={4} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: "rgba(255,255,255,0.96)", border: `1px solid ${graphGridStroke}`, borderRadius: 10, boxShadow: "0 10px 24px rgba(15, 23, 42, 0.10)", fontSize: 12 }}
                        formatter={(value, name) => [formatGraphValue(value), asString(name)]}
                        labelFormatter={(label) =>
                          graphMetric === "exam"
                            ? examClassOptions.find((point) => point.shortName === label)?.label || asString(label)
                            : asString(label)
                        }
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      {graphLineLabels.map((label, index) => {
                        const color = lineColors[index % lineColors.length];
                        return (
                          <Line
                            key={label}
                            type="monotone"
                            dataKey={label}
                            name={label}
                            stroke={color}
                            strokeWidth={2.5}
                            dot={{ r: 2.5, fill: color, strokeWidth: 0 }}
                            activeDot={{ r: 4, strokeWidth: 0 }}
                            connectNulls
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : graphBarRows.length ? (
                <div className="h-[18rem] sm:h-[20rem] xl:h-[21rem]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={graphBarRows} margin={{ top: 18, right: 12, left: -6, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke={graphGridStroke} strokeDasharray="4 4" />
                      <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} axisLine={false} tickLine={false} />
                      <YAxis domain={graphDomain} tick={{ fontSize: 10 }} width={36} tickMargin={4} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: "rgba(255,255,255,0.96)", border: `1px solid ${graphGridStroke}`, borderRadius: 10, boxShadow: "0 10px 24px rgba(15, 23, 42, 0.10)", fontSize: 12 }}
                        formatter={(value) => [formatGraphValue(value), graphValueLabel]}
                        labelFormatter={(label) => asString(label)}
                      />
                      <Bar dataKey="average" name={graphValueLabel} fill={graphStroke} radius={[6, 6, 0, 0]} maxBarSize={48}>
                        <LabelList dataKey="average" position="top" fontSize={9} fill={graphStroke} formatter={(value: number) => formatGraphValue(value)} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-[18rem] items-center justify-center rounded-lg border border-dashed border-foreground/15 bg-white/60 text-sm text-muted-foreground sm:h-[20rem] xl:h-[21rem]">
                  No graph data for this selection yet.
                </div>
              )}
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-card">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-bold">Action Queue</p>
                  <p className="text-xs text-muted-foreground">A quick read on what needs follow-up.</p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setZonesTab(zoneRows.red.length ? "red" : zoneRows.yellow.length ? "yellow" : "green");
                    setZonesOpen(true);
                  }}
                  className="h-8 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold text-foreground hover:bg-muted"
                >
                  View Zones
                </button>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-lg border border-rose-100 bg-rose-50/70 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-rose-700">Critical Performance</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-rose-700">{zoneRows.red.length}</span>
                  </div>
                  {criticalRows.length ? (
                    <div className="space-y-1.5">
                      {criticalRows.map((row: MonthlyGroupRow) => (
                        <div key={row.label} className="flex items-center justify-between gap-2 rounded-md bg-white/80 px-2 py-1.5 text-xs">
                          <span className="truncate font-bold">{row.label}</span>
                          <span className="shrink-0 font-bold text-rose-700">{row.current?.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs leading-5 text-rose-700/75">No selected groups below 5.0 AAP.</p>
                  )}
                </div>

                <div className="rounded-lg border border-amber-100 bg-amber-50/70 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-amber-700">Watchlist</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-amber-700">{zoneRows.yellow.length}</span>
                  </div>
                  {watchRows.length ? (
                    <div className="space-y-1.5">
                      {watchRows.map((row: MonthlyGroupRow) => (
                        <div key={row.label} className="flex items-center justify-between gap-2 rounded-md bg-white/80 px-2 py-1.5 text-xs">
                          <span className="truncate font-bold">{row.label}</span>
                          <span className="shrink-0 font-bold text-amber-700">{row.current?.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs leading-5 text-amber-700/75">No selected groups in the 5.0-6.9 range.</p>
                  )}
                </div>

                <div className="rounded-lg border border-sky-100 bg-sky-50/70 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-sky-700">Attendance Risk</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-sky-700">{attendanceRiskRows.length}</span>
                  </div>
                  {attendanceRiskRows.length ? (
                    <div className="space-y-1.5">
                      {attendanceRiskRows.map((row: MonthlyGroupRow) => (
                        <div key={row.label} className="flex items-center justify-between gap-2 rounded-md bg-white/80 px-2 py-1.5 text-xs">
                          <span className="truncate font-bold">{row.label}</span>
                          <span className="shrink-0 font-bold text-sky-700">{row.display_ar?.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs leading-5 text-sky-700/75">No selected groups below 70% attendance.</p>
                  )}
                </div>

                <div className="rounded-lg border border-violet-100 bg-violet-50/70 p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-violet-700">Falling Trend</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-violet-700">{fallingTrendRows.length}</span>
                  </div>
                  {fallingTrendRows.length ? (
                    <div className="space-y-1.5">
                      {fallingTrendRows.map((row: MonthlyGroupRow) => (
                        <div key={row.label} className="flex items-center justify-between gap-2 rounded-md bg-white/80 px-2 py-1.5 text-xs">
                          <span className="truncate font-bold">{row.label}</span>
                          <span className="shrink-0 font-bold text-violet-700">{deltaLabel(row.delta)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs leading-5 text-violet-700/75">No selected groups dropped from the previous month.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No subject statistics available.</p>
        )}
      </ChartCard>
    </div>
  );
}

export default function OverviewPanel({ state }: { state: any }) {
  if (!["admin", "ceo"].includes(asString(state.adminMode).toLowerCase())) {
    return <RoleOverviewPanel state={state} />;
  }
  return <SchoolOverviewPanel state={state} />;
}
