import { useState, type FormEvent, type ReactNode } from "react";
import {
  BarChart3,
  CalendarDays,
  CreditCard,
  Eye,
  Mail,
  Megaphone,
  Phone,
  UserRound,
} from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { withEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, formatLastSeen, getStudentCode, getStudentRowId, sortSubjectsMathFirst } from "../../admin/shared";

type ParentSection = "overview" | "announcements" | "payments" | "contact";

const parentAnnouncementAudiences = new Set(["all", "students", "parents", "year10", "year11"]);
const complaintCategoryLabels: Record<string, string> = {
  complaint: "Complaint",
  direct_contact: "Direct Contact",
  payment: "Payment",
  teacher: "Teacher",
  lesson_quality: "Lesson Quality",
  schedule: "Schedule",
  attendance: "Attendance",
  technical: "Technical",
  account: "Account",
  other: "Complaint",
};

function subjectList(value: unknown) {
  return sortSubjectsMathFirst(
    asString(value)
      .split(",")
      .map((item) => subjectDisplayName(item))
      .filter(Boolean),
  );
}

function normalizeSubject(value: unknown) {
  return asString(value).toLowerCase().replace(/\s+/g, " ");
}

function subjectDisplayName(value: unknown) {
  const raw = asString(value);
  const normalized = normalizeSubject(raw);
  if (["m", "math", "mathematics", "igcse math a", "igcse mathematics a"].includes(normalized)) {
    return "Math";
  }
  if (["eng", "english", "general english"].includes(normalized)) {
    return "English";
  }
  if (["chem", "chm", "chemistry"].includes(normalized)) {
    return "Chemistry";
  }
  if (["bio", "biology"].includes(normalized)) {
    return "Biology";
  }
  if (["phy", "physics"].includes(normalized)) {
    return "Physics";
  }
  return raw;
}

function subjectKey(value: unknown) {
  return normalizeSubject(subjectDisplayName(value));
}

function initialsFor(name: unknown) {
  const parts = asString(name).split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "ST"
  );
}

function formatDate(value: unknown) {
  const raw = asString(value);
  if (!raw) return "";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(new Date(parsed));
}

function complaintStatus(value: unknown) {
  const status = asString(value).toLowerCase();
  if (status === "in_progress" || status === "escalated" || status === "resolved") return status;
  return "new";
}

function complaintStatusLabel(value: unknown) {
  const status = complaintStatus(value);
  if (status === "in_progress") return "In Progress";
  if (status === "escalated") return "Escalated";
  if (status === "resolved") return "Resolved";
  return "New";
}

function complaintStatusClass(value: unknown) {
  const status = complaintStatus(value);
  if (status === "resolved") return "border-emerald-100 bg-emerald-50 text-emerald-700";
  if (status === "escalated") return "border-rose-100 bg-rose-50 text-rose-700";
  if (status === "in_progress") return "border-sky-100 bg-sky-50 text-sky-700";
  return "border-amber-100 bg-amber-50 text-amber-700";
}

function complaintCategoryLabel(value: unknown) {
  const key = asString(value).toLowerCase();
  return complaintCategoryLabels[key] || "Complaint";
}

function normalizeSection(value: unknown): ParentSection {
  const section = asString(value).toLowerCase();
  if (section === "announcements" || section === "payments" || section === "contact") {
    return section;
  }
  return "overview";
}

function linkedChildren(parent: Record<string, unknown> | undefined) {
  return Array.isArray(parent?.children)
    ? (parent.children as Array<Record<string, unknown>>)
    : [];
}

function academicIndicators(child: Record<string, unknown> | undefined) {
  return Array.isArray(child?.academic_indicators)
    ? (child.academic_indicators as Array<Record<string, unknown>>)
    : [];
}

function recentLessonsFor(child: Record<string, unknown> | undefined) {
  return Array.isArray(child?.recent_lessons)
    ? (child.recent_lessons as Array<Record<string, unknown>>)
    : [];
}

function complaintRowsForParent(complaints: unknown, parentId: number) {
  if (!Array.isArray(complaints) || parentId <= 0) return [];
  return (complaints as Array<Record<string, unknown>>)
    .filter((complaint) => asNumber(complaint.parent_admin_id) === parentId)
    .sort((left, right) => asNumber(right.id) - asNumber(left.id));
}

function paymentSummaryFor(child: Record<string, unknown> | undefined) {
  return child?.payment_summary && typeof child.payment_summary === "object"
    ? (child.payment_summary as Record<string, unknown>)
    : {};
}

function paymentRows(summary: Record<string, unknown>, key: string) {
  return Array.isArray(summary[key]) ? (summary[key] as Array<Record<string, unknown>>) : [];
}

function numberValue(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(asString(value));
  return Number.isFinite(parsed) ? parsed : null;
}

function moneyValue(value: unknown) {
  const parsed = numberValue(value);
  return parsed == null ? 0 : Math.max(0, parsed);
}

function formatMoney(value: unknown, currency = "UZS") {
  const amount = moneyValue(value);
  if (amount <= 0) return `0 ${currency}`;
  return `${Math.round(amount).toLocaleString("en-US")} ${currency}`;
}

function programCompletionFor(child: Record<string, unknown> | undefined) {
  const summary = paymentSummaryFor(child);
  const summaryRate = numberValue(summary.program_completion_rate);
  if (summaryRate != null) return Math.max(0, Math.min(100, Math.round(summaryRate)));

  const indicators = academicIndicators(child);
  const rates = indicators
    .map((indicator) => numberValue(indicator.program_completion_rate))
    .filter((value): value is number => value != null && value > 0);
  if (!rates.length) return 0;
  return Math.max(0, Math.min(100, Math.round(rates.reduce((sum, value) => sum + value, 0) / rates.length)));
}

function aggregatePaymentOverview(students: Array<Record<string, unknown>>) {
  const totals = students.reduce<{
    debt: number;
    due: number;
    upcoming: number;
    paid: number;
    completion: number;
  }>(
    (acc, child) => {
      const summary = paymentSummaryFor(child);
      acc.debt += moneyValue(summary.debt_total);
      acc.due += moneyValue(summary.due_total);
      acc.upcoming += moneyValue(summary.upcoming_total);
      acc.paid += moneyValue(summary.paid_total);
      acc.completion += programCompletionFor(child);
      return acc;
    },
    { debt: 0, due: 0, upcoming: 0, paid: 0, completion: 0 },
  );
  return {
    ...totals,
    averageCompletion: students.length ? Math.round(totals.completion / students.length) : 0,
  };
}

function formatAcademicValue(value: unknown, suffix = "") {
  const numericValue = numberValue(value);
  if (numericValue == null) return "-";
  const rounded = Math.round(numericValue * 10) / 10;
  const display = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${display}${suffix}`;
}

function rowSubjectName(row: Record<string, unknown>) {
  return (
    asString(row.subject_display_name) ||
    subjectDisplayName(asString(row.subject_name) || asString(row.subject_short))
  );
}

function rowSubjectKey(row: Record<string, unknown>) {
  return subjectKey(rowSubjectName(row)) || asString(row.subject_key);
}

function childSubjectOptions(
  child: Record<string, unknown> | undefined,
  indicators: Array<Record<string, unknown>>,
) {
  const options: Array<{ key: string; label: string }> = [];
  const add = (value: unknown) => {
    const label = subjectDisplayName(value);
    const key = subjectKey(label);
    if (!label || !key || options.some((option) => option.key === key)) return;
    options.push({ key, label });
  };
  indicators.forEach((indicator) => add(rowSubjectName(indicator)));
  subjectList(child?.subjects).forEach(add);
  const orderedLabels = sortSubjectsMathFirst(options.map((option) => option.label));
  return options.sort((a, b) => orderedLabels.indexOf(a.label) - orderedLabels.indexOf(b.label));
}

function ActionLink({
  href,
  label,
  icon,
}: {
  href: string;
  label: string;
  icon: ReactNode;
}) {
  return (
    <a
      href={withEmbedMode(href)}
      className="inline-flex h-9 items-center gap-2 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold text-foreground transition-colors hover:bg-muted"
    >
      {icon}
      {label}
    </a>
  );
}

function ChildSelector({
  students,
  selectedChildId,
  onSelect,
}: {
  students: Array<Record<string, unknown>>;
  selectedChildId: number;
  onSelect: (studentRowId: number) => void;
}) {
  if (students.length <= 1) return null;

  return (
    <div className="flex snap-x snap-mandatory gap-2 overflow-x-auto pb-1">
      {students.map((student) => {
        const studentRowId = getStudentRowId(student);
        const studentCode = getStudentCode(student);
        const isSelected = studentRowId === selectedChildId;
        return (
          <button
            key={studentRowId || studentCode}
            type="button"
            onClick={() => onSelect(studentRowId)}
            className={`inline-flex min-w-[13rem] snap-start items-center gap-2 rounded-lg border px-3 py-2 text-left transition-colors ${
              isSelected
                ? "border-foreground bg-foreground text-background"
                : "border-foreground/10 bg-surface text-foreground hover:bg-muted"
            }`}
          >
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${isSelected ? "bg-background/15" : "bg-muted"}`}>
              {initialsFor(student.full_name)}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-xs font-bold">{asString(student.full_name) || "Student"}</span>
              <span className={`block truncate text-[11px] ${isSelected ? "text-background/70" : "text-muted-foreground"}`}>
                Code {studentCode || "-"}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
      <p className="text-sm font-bold">{label}</p>
    </div>
  );
}

function AcademicMetric({
  label,
  value,
  suffix,
  tone,
}: {
  label: string;
  value: unknown;
  suffix?: string;
  tone: string;
}) {
  return (
    <div className={`min-h-[4.25rem] rounded-lg border px-3 py-2 ${tone}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-xl font-bold leading-none">{formatAcademicValue(value, suffix)}</p>
    </div>
  );
}

function AcademicIndicators({
  indicators,
}: {
  indicators: Array<Record<string, unknown>>;
}) {
  if (!indicators.length) {
    return <EmptyState label="No AAP, AR, or EP data is available yet." />;
  }

  return (
    <div className="space-y-3">
      {indicators.map((indicator) => {
        const groupName = asString(indicator.group_name);
        return (
          <div key={`${asString(indicator.enrollment_id)}-${groupName}`} className="space-y-2">
            {groupName ? <p className="text-xs font-semibold text-muted-foreground">{groupName}</p> : null}
            <div className="grid grid-cols-3 gap-2">
              <AcademicMetric label="AAP" value={indicator.aap} tone="border-sky-100 bg-sky-50 text-sky-950" />
              <AcademicMetric label="AR" value={indicator.ar} suffix="%" tone="border-emerald-100 bg-emerald-50 text-emerald-950" />
              <AcademicMetric label="EP" value={indicator.ep} tone="border-amber-100 bg-amber-50 text-amber-950" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function attendanceBadge(status: unknown) {
  const normalized = normalizeSubject(status);
  if (normalized === "present") {
    return {
      label: "Attended",
      className: "border-emerald-100 bg-emerald-50 text-emerald-700",
    };
  }
  if (normalized === "absent") {
    return {
      label: "Not attended",
      className: "border-rose-100 bg-rose-50 text-rose-700",
    };
  }
  if (normalized === "justified" || normalized === "justified absent") {
    return {
      label: "Justified",
      className: "border-amber-100 bg-amber-50 text-amber-700",
    };
  }
  return {
    label: "No status",
    className: "border-foreground/10 bg-muted text-muted-foreground",
  };
}

function ChildSummary({
  child,
  currentSchool,
  subjectOptions,
  activeSubjectKey,
  selectedIndicators,
  onSelectSubject,
}: {
  child: Record<string, unknown> | undefined;
  currentSchool: string;
  subjectOptions: Array<{ key: string; label: string }>;
  activeSubjectKey: string;
  selectedIndicators: Array<Record<string, unknown>>;
  onSelectSubject: (key: string) => void;
}) {
  if (!child) {
    return <EmptyState label="No child record is connected yet." />;
  }

  const studentRowId = getStudentRowId(child);
  const studentCode = getStudentCode(child);
  const seen = formatLastSeen(child.last_seen_at);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-muted text-sm font-bold">
            {initialsFor(child.full_name)}
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-lg font-bold">{asString(child.full_name) || "Student"}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Code {studentCode || "-"} · {asString(child.school_name) || "School"}
            </p>
            <p className={`mt-2 text-xs font-semibold ${seen.online ? "text-emerald-700" : "text-muted-foreground"}`}>
              {seen.label}
            </p>
          </div>
        </div>
        {studentRowId ? (
          <ActionLink
            href={routes.adminStudentPanel(studentRowId, currentSchool)}
            label="View Dashboard"
            icon={<Eye className="h-3.5 w-3.5" />}
          />
        ) : null}
      </div>

      <div>
        <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Subjects</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {subjectOptions.length ? (
            subjectOptions.map((subject) => (
              <button
                key={subject.key}
                type="button"
                onClick={() => onSelectSubject(subject.key)}
                className={`rounded-md border px-2 py-1 text-[11px] font-bold transition-colors ${
                  activeSubjectKey === subject.key
                    ? "border-foreground bg-foreground text-background"
                    : "border-foreground/10 bg-muted text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
                }`}
              >
                {subject.label}
              </button>
            ))
          ) : (
            <span className="text-sm text-muted-foreground">No subjects are linked yet.</span>
          )}
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-info" />
          <p className="text-sm font-bold">Academic Performance</p>
        </div>
        <AcademicIndicators indicators={selectedIndicators} />
      </div>
    </div>
  );
}

function RecentLessonsSection({
  lessons,
}: {
  lessons: Array<Record<string, unknown>>;
}) {
  if (!lessons.length) {
    return <EmptyState label="No recent lessons are recorded yet." />;
  }

  return (
    <div>
      <div className="space-y-2 sm:hidden">
        {lessons.map((lesson, index) => (
          (() => {
            const badge = attendanceBadge(lesson.attendance_status);
            return (
          <article
            key={`${asString(lesson.date)}-${asString(lesson.subject_name)}-${index}`}
            className="rounded-lg border border-foreground/10 bg-background p-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-bold">{formatDate(lesson.date) || "Date"}</p>
              <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground">
                {rowSubjectName(lesson) || "Subject"}
              </span>
            </div>
            <p className="mt-2 text-sm font-semibold leading-5">
              {asString(lesson.topic) || asString(lesson.lesson_number) || "Topic unavailable"}
            </p>
            <span className={`mt-3 inline-flex rounded-md border px-2 py-1 text-[11px] font-bold ${badge.className}`}>
              {badge.label}
            </span>
          </article>
            );
          })()
        ))}
      </div>

      <div className="hidden overflow-x-auto rounded-lg border border-foreground/10 sm:block">
        <table className="w-full min-w-[34rem] text-left">
          <thead className="bg-muted/60">
            <tr>
              {["Date", "Subject", "Topic", "Attendance"].map((heading) => (
                <th
                  key={heading}
                  className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-muted-foreground"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lessons.map((lesson, index) => {
              const badge = attendanceBadge(lesson.attendance_status);
              return (
                <tr
                  key={`${asString(lesson.date)}-${asString(lesson.subject_name)}-${index}`}
                  className="border-t border-foreground/5"
                >
                  <td className="whitespace-nowrap px-3 py-3 text-xs font-semibold">
                    {formatDate(lesson.date) || "Date"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-xs text-muted-foreground">
                    {rowSubjectName(lesson) || "Subject"}
                  </td>
                  <td className="px-3 py-3 text-xs font-medium leading-5">
                    {asString(lesson.topic) || asString(lesson.lesson_number) || "Topic unavailable"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3">
                    <span className={`inline-flex rounded-md border px-2 py-1 text-[11px] font-bold ${badge.className}`}>
                      {badge.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UpdatesSection({
  announcements,
}: {
  announcements: Array<Record<string, unknown>>;
}) {
  if (!announcements.length) {
    return <EmptyState label="No parent updates are published yet." />;
  }

  return (
    <div className="space-y-2">
      {announcements.map((item) => {
        const priority = asString(item.priority);
        const tone =
          priority === "urgent"
            ? "border-rose-200 bg-rose-50"
            : priority === "important"
              ? "border-amber-200 bg-amber-50"
              : "border-foreground/10 bg-background";
        return (
          <article key={asNumber(item.id)} className={`rounded-lg border p-3 ${tone}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h4 className="truncate text-sm font-bold">{asString(item.title) || "Update"}</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDate(item.publishedAt || item.updatedAt || item.createdAt)}
                </p>
              </div>
              {Boolean(item.pinned) ? (
                <span className="rounded-md bg-surface px-2 py-1 text-[11px] font-bold">Pinned</span>
              ) : null}
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground/80">{asString(item.body)}</p>
          </article>
        );
      })}
    </div>
  );
}

function PaymentMetric({
  label,
  value,
  detail,
  tone = "bg-background",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: string;
}) {
  return (
    <div className={`rounded-lg border border-foreground/10 p-3 ${tone}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function ProgressLine({ value }: { value: number }) {
  const bounded = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
      <div className="h-full rounded-full bg-foreground" style={{ width: `${bounded}%` }} />
    </div>
  );
}

function PaymentRowsTable({
  rows,
  emptyLabel,
}: {
  rows: Array<Record<string, unknown>>;
  emptyLabel: string;
}) {
  if (!rows.length) {
    return <EmptyState label={emptyLabel} />;
  }

  return (
    <div className="miniapp-table-scroll rounded-lg border border-foreground/10">
      <table className="w-full min-w-[38rem] text-left">
        <thead className="bg-muted/60">
          <tr>
            {["Month", "Amount", "Status", "Date"].map((heading) => (
              <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${asString(row.month || row.title)}-${index}`} className="border-t border-foreground/5">
              <td className="px-3 py-3 text-xs font-semibold">{asString(row.month || row.title || row.label) || "Payment"}</td>
              <td className="px-3 py-3 text-xs text-muted-foreground">{formatMoney(row.amount, asString(row.currency) || "UZS")}</td>
              <td className="px-3 py-3 text-xs font-semibold">{asString(row.status) || "Recorded"}</td>
              <td className="px-3 py-3 text-xs text-muted-foreground">
                {formatDate(row.paid_at || row.due_date || row.date) || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PaymentQueue({
  title,
  rows,
  emptyLabel,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
  emptyLabel: string;
}) {
  return (
    <div className="rounded-lg border border-foreground/10 bg-background p-3">
      <p className="text-sm font-bold">{title}</p>
      {rows.length ? (
        <div className="mt-3 space-y-2">
          {rows.map((row, index) => (
            <div key={`${title}-${index}`} className="flex items-center justify-between gap-3 rounded-md bg-muted px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-xs font-bold">{asString(row.month || row.title || row.label) || "Payment"}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{formatDate(row.due_date || row.date) || "No date"}</p>
              </div>
              <p className="shrink-0 text-xs font-bold">{formatMoney(row.amount, asString(row.currency) || "UZS")}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 rounded-md border border-dashed border-foreground/15 px-3 py-5 text-center text-xs font-bold text-muted-foreground">
          {emptyLabel}
        </p>
      )}
    </div>
  );
}

function PaymentsSection({
  students,
  selectedChild,
  selectedChildId,
  onSelectChild,
}: {
  students: Array<Record<string, unknown>>;
  selectedChild: Record<string, unknown> | undefined;
  selectedChildId: number;
  onSelectChild: (studentRowId: number) => void;
}) {
  const overview = aggregatePaymentOverview(students);
  const selectedSummary = paymentSummaryFor(selectedChild);
  const selectedCurrency = asString(selectedSummary.currency) || "UZS";
  const historyRows = paymentRows(selectedSummary, "monthly_history");
  const debtRows = paymentRows(selectedSummary, "debts");
  const dueRows = paymentRows(selectedSummary, "due_payments");
  const upcomingRows = paymentRows(selectedSummary, "upcoming_payments");
  const completion = programCompletionFor(selectedChild);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <PaymentMetric label="Family debt" value={formatMoney(overview.debt)} detail="Across all children" tone="bg-rose-50" />
        <PaymentMetric label="Due payments" value={formatMoney(overview.due)} detail="Need payment now" tone="bg-amber-50" />
        <PaymentMetric label="Upcoming" value={formatMoney(overview.upcoming)} detail="Scheduled ahead" tone="bg-sky-50" />
        <PaymentMetric label="Program" value={`${overview.averageCompletion}%`} detail="Average completion" tone="bg-emerald-50" />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {students.map((child) => {
          const childId = getStudentRowId(child);
          const studentCode = getStudentCode(child);
          const summary = paymentSummaryFor(child);
          const childCompletion = programCompletionFor(child);
          const isSelected = childId === selectedChildId;
          return (
            <button
              key={childId || studentCode}
              type="button"
              onClick={() => onSelectChild(childId)}
              className={`rounded-lg border bg-background p-3 text-left transition-colors ${
                isSelected ? "border-foreground/35" : "border-foreground/10 hover:bg-muted/50"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold">{asString(child.full_name) || "Student"}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Code {studentCode || "-"}</p>
                </div>
                <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold">{childCompletion}%</span>
              </div>
              <ProgressLine value={childCompletion} />
              <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
                <span className="rounded-md bg-muted px-2 py-1 font-bold">Debt {formatMoney(summary.debt_total, asString(summary.currency) || "UZS")}</span>
                <span className="rounded-md bg-muted px-2 py-1 font-bold">Due {formatMoney(summary.due_total, asString(summary.currency) || "UZS")}</span>
                <span className="rounded-md bg-muted px-2 py-1 font-bold">Next {formatMoney(summary.upcoming_total, asString(summary.currency) || "UZS")}</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="rounded-lg border border-foreground/10 bg-background p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Selected child statement</p>
            <h3 className="mt-1 truncate text-base font-bold">{asString(selectedChild?.full_name) || "Student"}</h3>
          </div>
          <div className="w-full sm:w-56">
            <div className="flex items-center justify-between text-xs font-bold">
              <span>Program completion</span>
              <span>{completion}%</span>
            </div>
            <ProgressLine value={completion} />
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <PaymentMetric label="Debt" value={formatMoney(selectedSummary.debt_total, selectedCurrency)} detail="Outstanding balance" />
          <PaymentMetric label="Due" value={formatMoney(selectedSummary.due_total, selectedCurrency)} detail="Due now" />
          <PaymentMetric label="Upcoming" value={formatMoney(selectedSummary.upcoming_total, selectedCurrency)} detail="Next scheduled" />
          <PaymentMetric label="Paid" value={formatMoney(selectedSummary.paid_total, selectedCurrency)} detail="Recorded payments" />
        </div>

        <div className="mt-4">
          <h4 className="text-sm font-bold">Monthly Payment History</h4>
          <div className="mt-2">
            <PaymentRowsTable rows={historyRows} emptyLabel="No monthly payment history is recorded yet." />
          </div>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <PaymentQueue title="Debts" rows={debtRows} emptyLabel="No debts recorded." />
          <PaymentQueue title="Due Payments" rows={dueRows} emptyLabel="No due payments recorded." />
          <PaymentQueue title="Upcoming Payments" rows={upcomingRows} emptyLabel="No upcoming payments recorded." />
        </div>
      </div>
    </div>
  );
}

type ContactMode = "complaint" | "direct_contact";

function ContactSection({
  csrf,
  parentId,
  complaints,
  onComplaintCreated,
}: {
  csrf: string;
  parentId: number;
  complaints: Array<Record<string, unknown>>;
  onComplaintCreated: (complaint: Record<string, unknown>) => void;
}) {
  const [composerMode, setComposerMode] = useState<ContactMode | null>(null);
  const [topic, setTopic] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const isDirectContact = composerMode === "direct_contact";

  function openComposer(mode: ContactMode) {
    setComposerMode(mode);
    setError("");
    setTopic("");
    setMessage("");
  }

  async function submitComplaint(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!parentId || !composerMode || saving) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(routes.adminComplaintsApi, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          parent_admin_id: parentId,
          category: composerMode,
          topic,
          message,
        }),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to send complaint.");
        return;
      }
      if (json.complaint && typeof json.complaint === "object") {
        onComplaintCreated(json.complaint as Record<string, unknown>);
      }
      setComposerMode(null);
      setTopic("");
      setMessage("");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-2">
          <Megaphone className="h-4 w-4 text-info" />
          <div>
            <h3 className="text-sm font-bold">Your Complaints</h3>
            <p className="text-xs text-muted-foreground">{complaints.length} submitted</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => openComposer("complaint")}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-foreground/10 bg-surface px-3 text-xs font-bold shadow-sm hover:bg-muted"
          >
            <Mail className="h-3.5 w-3.5" />
            New Complaint
          </button>
          <button
            type="button"
            onClick={() => openComposer("direct_contact")}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground shadow-sm"
          >
            <Phone className="h-3.5 w-3.5" />
            Direct Contact
          </button>
        </div>
      </div>

      {error ? (
        <div className="mt-3 rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
          {error}
        </div>
      ) : null}

      {composerMode ? (
        <form onSubmit={submitComplaint} className="rounded-lg border border-foreground/10 bg-background p-4 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="text-base font-bold">{isDirectContact ? "Direct Contact" : "New Complaint"}</h4>
              <p className="text-xs text-muted-foreground">Topic and message are enough.</p>
            </div>
            <button
              type="button"
              onClick={() => setComposerMode(null)}
              className="h-8 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-bold hover:bg-muted"
            >
              Cancel
            </button>
          </div>

          <div className="mt-4 space-y-3">
            <label className="block">
              <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                Topic
              </span>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="h-11 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-bold outline-none focus:border-foreground/30"
                placeholder={isDirectContact ? "Example: Please contact me about payment" : "Example: Lesson concern"}
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                Message
              </span>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={4}
                className="w-full resize-none rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
                placeholder={isDirectContact ? "Write how Customer Support should help..." : "Write what happened..."}
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={saving || !parentId || topic.trim().length < 2 || message.trim().length < 5}
            className="mt-3 inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-50"
          >
            {isDirectContact ? <Phone className="h-4 w-4" /> : <Mail className="h-4 w-4" />}
            {saving ? "Sending..." : isDirectContact ? "Send Direct Contact" : "Send Complaint"}
          </button>
        </form>
      ) : null}

      <div className="space-y-2">
        {complaints.length ? (
          complaints.map((complaint) => {
            const title = asString(complaint.topic) || complaintCategoryLabel(complaint.category);
            return (
              <article key={asNumber(complaint.id)} className="rounded-lg border border-foreground/10 bg-background p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-bold">{title}</p>
                      <span className="rounded-md bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground">
                        {complaintCategoryLabel(complaint.category)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{formatDate(complaint.created_at)}</p>
                  </div>
                  <span className={`rounded-md border px-2 py-1 text-[11px] font-bold ${complaintStatusClass(complaint.status)}`}>
                    {complaintStatusLabel(complaint.status)}
                  </span>
                </div>
                <p className="mt-3 line-clamp-3 text-sm leading-6 text-foreground/80">{asString(complaint.message)}</p>
                {asString(complaint.reply) ? (
                  <div className="mt-3 rounded-md bg-background px-3 py-2 text-xs leading-5 text-muted-foreground">
                    <span className="font-bold text-foreground">Reply: </span>
                    {asString(complaint.reply)}
                  </div>
                ) : null}
              </article>
            );
          })
        ) : (
          <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-10 text-center">
            <p className="text-sm font-bold">No complaints submitted yet.</p>
            <p className="mt-1 text-xs text-muted-foreground">Use New Complaint or Direct Contact when you need support.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ParentDashboard({ state }: { state: any }) {
  const currentSchool = asString(state.currentSchool) || "all";
  const section = normalizeSection(state.activeTab);
  const activeParentId = asNumber(state.activeParentId);
  const parentAccounts = Array.isArray(state.parentAccounts)
    ? (state.parentAccounts as Array<Record<string, unknown>>)
    : [];
  const activeParent =
    parentAccounts.find((parent) => asNumber(parent.id) === activeParentId) ||
    parentAccounts[0];
  const activeParentResolvedId = asNumber(activeParent?.id);
  const students = activeParent
    ? linkedChildren(activeParent)
    : Array.isArray(state.parentChildren)
      ? (state.parentChildren as Array<Record<string, unknown>>)
      : Array.isArray(state.props?.adminParentChildren)
        ? (state.props.adminParentChildren as Array<Record<string, unknown>>)
        : [];
  const announcements = Array.isArray(state.props?.adminAnnouncements)
    ? (state.props.adminAnnouncements as Array<Record<string, unknown>>)
        .filter((item) => asString(item.status) === "published")
      .filter((item) => parentAnnouncementAudiences.has(asString(item.audience) || "all"))
    : [];
  const parentComplaints = complaintRowsForParent(
    Array.isArray(state.complaints) ? state.complaints : state.props?.adminComplaints,
    activeParentResolvedId,
  );

  const [selectedChildId, setSelectedChildId] = useState(() => getStudentRowId(students[0]));
  const [selectedSubjectKey, setSelectedSubjectKey] = useState("");
  const selectedChild =
    students.find((student) => getStudentRowId(student) === selectedChildId) || students[0];
  const selectedChildIdResolved = getStudentRowId(selectedChild);
  const latestUpdates = announcements.slice(0, 3);
  const childIndicators = academicIndicators(selectedChild);
  const subjectOptions = childSubjectOptions(selectedChild, childIndicators);
  const activeSubjectKey = subjectOptions.some((subject) => subject.key === selectedSubjectKey)
    ? selectedSubjectKey
    : subjectOptions[0]?.key || "";
  const selectedIndicators = activeSubjectKey
    ? childIndicators.filter((indicator) => rowSubjectKey(indicator) === activeSubjectKey)
    : childIndicators;
  const recentLessons = recentLessonsFor(selectedChild);
  const selectedLessonsAll = activeSubjectKey
    ? recentLessons.filter((lesson) => rowSubjectKey(lesson) === activeSubjectKey)
    : recentLessons;
  const selectedLessons = selectedLessonsAll.slice(0, 3);

  function selectChild(studentRowId: number) {
    if (studentRowId > 0) {
      setSelectedChildId(studentRowId);
      setSelectedSubjectKey("");
    }
  }

  function addComplaint(complaint: Record<string, unknown>) {
    if (typeof state.setComplaints === "function") {
      state.setComplaints((current: Array<Record<string, unknown>>) => [complaint, ...current]);
    }
  }

  return (
    <div className="space-y-4">
      {section === "overview" ? (
        <ChildSelector
          students={students}
          selectedChildId={selectedChildIdResolved}
          onSelect={selectChild}
        />
      ) : null}

      {section === "announcements" ? (
        <ChartCard title="Updates" subtitle={`${announcements.length} published`} icon={<Megaphone className="h-4 w-4 text-info" />}>
          <UpdatesSection announcements={announcements} />
        </ChartCard>
      ) : null}

      {section === "payments" ? (
        <ChartCard title="Payments" subtitle="Customer Support managed" icon={<CreditCard className="h-4 w-4 text-info" />}>
          <PaymentsSection
            students={students}
            selectedChild={selectedChild}
            selectedChildId={selectedChildIdResolved}
            onSelectChild={selectChild}
          />
        </ChartCard>
      ) : null}

      {section === "contact" ? (
        <ChartCard title="Support" subtitle="Complaints and replies" icon={<Phone className="h-4 w-4 text-info" />}>
          <ContactSection
            csrf={asString(state.props?.csrfToken)}
            parentId={activeParentResolvedId}
            complaints={parentComplaints}
            onComplaintCreated={addComplaint}
          />
        </ChartCard>
      ) : null}

      {section === "overview" ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
          <div className="space-y-4">
            <ChartCard title="Child Snapshot" subtitle="Subjects and performance" icon={<UserRound className="h-4 w-4 text-info" />}>
              <ChildSummary
                child={selectedChild}
                currentSchool={currentSchool}
                subjectOptions={subjectOptions}
                activeSubjectKey={activeSubjectKey}
                selectedIndicators={selectedIndicators}
                onSelectSubject={setSelectedSubjectKey}
              />
            </ChartCard>

            <ChartCard title="Recent Lessons" subtitle={`${selectedLessons.length} shown`} icon={<CalendarDays className="h-4 w-4 text-info" />}>
              <RecentLessonsSection lessons={selectedLessons} />
            </ChartCard>
          </div>

          <ChartCard title="Latest Announcements by the School" subtitle={`${latestUpdates.length} shown`} icon={<Megaphone className="h-4 w-4 text-info" />}>
            <UpdatesSection announcements={latestUpdates} />
          </ChartCard>
        </div>
      ) : null}
    </div>
  );
}
