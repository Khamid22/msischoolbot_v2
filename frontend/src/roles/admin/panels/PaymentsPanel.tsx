import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Check, CreditCard, Plus, Search, Trash2, Undo2, UserRound } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, getStudentCode, getStudentRowId, sortSubjectsMathFirst } from "../shared";

type PaymentRow = Record<string, unknown>;
type FamilyTotals = {
  debt: number;
  due: number;
  upcoming: number;
  paid: number;
  currency: string;
};

// Display labels for every derived state a row can show in the ledger.
const paymentStatuses = [
  { value: "paid", label: "Paid" },
  { value: "due", label: "Due" },
  { value: "debt", label: "Debt" },
  { value: "upcoming", label: "Upcoming" },
];

// At creation Customer Support only records facts: an unpaid charge (its
// due/debt/upcoming state is derived from the due date) or an already-paid one.
const creationStatuses = [
  { value: "due", label: "Unpaid" },
  { value: "paid", label: "Paid" },
];

function moneyValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
}

function formatMoney(value: unknown, currency = "UZS") {
  const amount = moneyValue(value);
  if (amount <= 0) return `0 ${currency}`;
  return `${Math.round(amount).toLocaleString("en-US")} ${currency}`;
}

function formatDate(value: unknown) {
  const raw = asString(value);
  if (!raw) return "-";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(parsed));
}

function statusLabel(value: unknown) {
  const status = asString(value).toLowerCase();
  return paymentStatuses.find((item) => item.value === status)?.label || "Due";
}

function statusClass(value: unknown) {
  const status = asString(value).toLowerCase();
  if (status === "paid") return "border-emerald-100 bg-emerald-50 text-emerald-700";
  if (status === "debt") return "border-rose-100 bg-rose-50 text-rose-700";
  if (status === "upcoming") return "border-sky-100 bg-sky-50 text-sky-700";
  return "border-amber-100 bg-amber-50 text-amber-700";
}

function initialsFor(value: unknown) {
  const parts = asString(value).split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "PA"
  );
}

function parentChildren(parent: Record<string, unknown> | undefined) {
  return Array.isArray(parent?.children)
    ? (parent!.children as Array<Record<string, unknown>>)
    : [];
}

function paymentSummaryFor(child: Record<string, unknown> | undefined) {
  return child?.payment_summary && typeof child.payment_summary === "object"
    ? (child.payment_summary as Record<string, unknown>)
    : {};
}

function subjectsList(child: Record<string, unknown> | undefined) {
  // Prefer live enrollment data (academic_indicators) over the legacy `subjects`
  // text column, which is often stale/incomplete (e.g. only "Math").
  const indicators = Array.isArray(child?.academic_indicators)
    ? (child!.academic_indicators as Array<Record<string, unknown>>)
    : [];
  const fromEnrollments = indicators
    .map((ind) => asString(ind.subject_display_name) || asString(ind.subject_name))
    .filter(Boolean);
  const source = fromEnrollments.length
    ? fromEnrollments
    : asString(child?.subjects)
        .split(/[,;]+/)
        .map((item) => item.trim())
        .filter(Boolean);

  const seen = new Set<string>();
  const unique = source.filter((subject) => {
    const key = subject.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return sortSubjectsMathFirst(unique);
}

function courseProgress(child: Record<string, unknown> | undefined) {
  const summary = paymentSummaryFor(child);
  const rate = Math.max(0, Math.min(100, Math.round(moneyValue(summary.program_completion_rate))));
  const completed = Math.round(moneyValue(summary.program_completed_lessons));
  const total = Math.round(moneyValue(summary.program_total_lessons)) || 180;
  return { rate, completed, total };
}

// Family-level totals are summed across the parent's children so Customer
// Support can immediately see whether a family owes anything.
function familyTotals(parent: Record<string, unknown> | undefined) {
  return parentChildren(parent).reduce<FamilyTotals>(
    (acc, child) => {
      const summary = paymentSummaryFor(child);
      acc.debt += moneyValue(summary.debt_total);
      acc.due += moneyValue(summary.due_total);
      acc.upcoming += moneyValue(summary.upcoming_total);
      acc.paid += moneyValue(summary.paid_total);
      const currency = asString(summary.currency);
      if (currency) acc.currency = currency;
      return acc;
    },
    { debt: 0, due: 0, upcoming: 0, paid: 0, currency: "UZS" },
  );
}

// Preserve program/course progress fields (computed server-side with academic
// data) while refreshing the money buckets from a ledger mutation response.
function mergePaymentSummary(
  child: Record<string, unknown>,
  summary: Record<string, unknown>,
) {
  const current = paymentSummaryFor(child);
  return {
    ...child,
    payment_summary: {
      ...current,
      ...summary,
      program_completion_rate:
        current.program_completion_rate ?? summary.program_completion_rate ?? 0,
      program_completed_lessons:
        current.program_completed_lessons ?? summary.program_completed_lessons ?? 0,
      program_total_lessons:
        current.program_total_lessons ?? summary.program_total_lessons ?? 0,
    },
  };
}

function SummaryTile({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail?: string;
  tone: string;
}) {
  return (
    <div className={`rounded-lg border border-foreground/10 p-3 ${tone}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-bold leading-none">{value}</p>
      {detail ? <p className="mt-1.5 text-[11px] text-muted-foreground">{detail}</p> : null}
    </div>
  );
}

export default function PaymentsPanel({ state }: { state: any }) {
  const csrf = asString(state.props?.csrfToken);
  const parents = Array.isArray(state.parentAccounts)
    ? (state.parentAccounts as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminParents)
      ? (state.props.adminParents as Array<Record<string, unknown>>)
      : [];

  const [selectedParentId, setSelectedParentId] = useState(
    () => asNumber(state.activeParentId) || asNumber(parents[0]?.id),
  );
  const [selectedChildId, setSelectedChildId] = useState(0);
  const [query, setQuery] = useState("");
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    subject: "",
    month: "",
    amount: "",
    currency: "UZS",
    status: "due",
    due_date: "",
    paid_at: "",
    notes: "",
  });

  const selectedParent =
    parents.find((parent) => asNumber(parent.id) === selectedParentId) || parents[0];
  const selectedParentResolvedId = asNumber(selectedParent?.id);
  const children = parentChildren(selectedParent);
  const selectedChild =
    children.find((child) => getStudentRowId(child) === selectedChildId) || children[0];
  const selectedChildResolvedId = getStudentRowId(selectedChild);

  const visibleParents = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return parents;
    return parents.filter((parent) => {
      if (asString(parent.login).toLowerCase().includes(normalized)) return true;
      return parentChildren(parent).some((child) =>
        [asString(child.full_name), getStudentCode(child)]
          .join(" ")
          .toLowerCase()
          .includes(normalized),
      );
    });
  }, [parents, query]);

  function selectParent(parentId: number) {
    setSelectedParentId(parentId);
    setSelectedChildId(0);
    if (typeof state.setActiveParentId === "function") {
      state.setActiveParentId(parentId);
    }
  }

  // Keep the focused child's refreshed money buckets in the shared parent
  // accounts so the family tiles and left-column debt badges stay live.
  function syncChildSummary(childId: number, nextSummary: Record<string, unknown>) {
    if (typeof state.setParentAccounts === "function") {
      state.setParentAccounts((current: Array<Record<string, unknown>>) =>
        current.map((parent) => ({
          ...parent,
          children: parentChildren(parent).map((child) =>
            getStudentRowId(child) === childId ? mergePaymentSummary(child, nextSummary) : child,
          ),
        })),
      );
    }
    if (typeof state.setParentChildren === "function") {
      state.setParentChildren((current: Array<Record<string, unknown>>) =>
        current.map((child) =>
          getStudentRowId(child) === childId ? mergePaymentSummary(child, nextSummary) : child,
        ),
      );
    }
  }

  function applyResult(childId: number, json: Record<string, unknown>) {
    const nextPayments = Array.isArray(json.payments) ? (json.payments as PaymentRow[]) : [];
    const nextSummary =
      json.summary && typeof json.summary === "object"
        ? (json.summary as Record<string, unknown>)
        : {};
    setPayments(nextPayments);
    setSummary(nextSummary);
    syncChildSummary(childId, nextSummary);
  }

  async function loadPayments(childId: number) {
    if (!childId) {
      setPayments([]);
      setSummary({});
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await fetch(routes.adminStudentPaymentsApi(childId), {
        cache: "no-store",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to load payments.");
        return;
      }
      applyResult(childId, json);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setForm((current) => ({ ...current, subject: "" }));
    void loadPayments(selectedChildResolvedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedChildResolvedId]);

  async function savePayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const childId = selectedChildResolvedId;
    if (!childId || saving) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(routes.adminStudentPaymentsApi(childId), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(form),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to save payment.");
        return;
      }
      applyResult(childId, json);
      setForm({
        subject: "",
        month: "",
        amount: "",
        currency: "UZS",
        status: "due",
        due_date: "",
        paid_at: "",
        notes: "",
      });
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function markPaid(row: PaymentRow, paid: boolean) {
    const paymentId = asNumber(row.id);
    if (!paymentId || saving) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(routes.adminStudentPaymentApi(paymentId), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ paid }),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to update payment.");
        return;
      }
      applyResult(asNumber(json.student_row_id) || selectedChildResolvedId, json);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function deletePayment(row: PaymentRow) {
    const paymentId = asNumber(row.id);
    if (!paymentId || saving) return;
    if (!window.confirm("Delete this payment record?")) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(routes.adminStudentPaymentApi(paymentId), {
        method: "DELETE",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to delete payment.");
        return;
      }
      applyResult(asNumber(json.student_row_id) || selectedChildResolvedId, json);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const totals = familyTotals(selectedParent);
  const familyCurrency = totals.currency || "UZS";
  const ledgerCurrency = asString(summary.currency) || familyCurrency;
  const subjects = subjectsList(selectedChild);
  const progress = courseProgress(selectedChild);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg border border-foreground/8 bg-white p-3 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <UserRound className="h-4 w-4 text-info" />
            <h2 className="text-base font-bold">Payments</h2>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Parent accounts, linked students, debts, and payment records.
          </p>
        </div>
        <label className="relative block w-full lg:max-w-xl">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search parents, students, or student codes"
            className="h-10 w-full rounded-lg border border-foreground/10 bg-surface pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
          />
        </label>
      </div>

      <ChartCard
        title="Parents"
        subtitle={`Showing ${visibleParents.length} of ${parents.length} account${parents.length === 1 ? "" : "s"}`}
        icon={<UserRound className="h-4 w-4 text-info" />}
      >
        <div className="miniapp-table-scroll rounded-lg border border-foreground/10">
          <table className="w-full min-w-[48rem] text-left">
            <thead className="bg-muted/60">
              <tr>
                {["Parent", "Linked Students", "Family Debt", "Due", "Paid", "Action"].map((heading) => (
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
              {visibleParents.length ? (
                visibleParents.map((parent) => {
                  const parentId = asNumber(parent.id);
                  const active = parentId === selectedParentResolvedId;
                  const count = parentChildren(parent).length;
                  const parentTotals = familyTotals(parent);
                  const currency = parentTotals.currency || "UZS";
                  return (
                    <tr
                      key={parentId}
                      className={`border-t border-foreground/5 transition-colors ${
                        active ? "bg-primary/5" : "hover:bg-muted/50"
                      }`}
                    >
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold text-foreground">
                            {initialsFor(parent.login)}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-bold">{asString(parent.login)}</p>
                            <p className="truncate text-xs text-muted-foreground">Parent account</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-sm font-semibold text-muted-foreground">
                        {count} {count === 1 ? "student" : "students"}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-sm font-bold text-rose-700">
                        {formatMoney(parentTotals.debt, currency)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-sm font-semibold text-amber-700">
                        {formatMoney(parentTotals.due, currency)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-sm font-semibold text-emerald-700">
                        {formatMoney(parentTotals.paid, currency)}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => selectParent(parentId)}
                          className={`inline-flex h-8 items-center rounded-lg px-3 text-xs font-bold ${
                            active
                              ? "bg-primary text-primary-foreground"
                              : "border border-foreground/10 bg-background text-foreground hover:bg-muted"
                          }`}
                        >
                          {active ? "Selected" : "View"}
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="px-3 py-10 text-center text-sm font-bold text-muted-foreground">
                    {query ? "No parents match your search." : "No parent accounts yet."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ChartCard>

      <ChartCard
        title={selectedParent ? asString(selectedParent.login) : "Payments"}
        subtitle={
          selectedParent
            ? `${children.length} linked ${children.length === 1 ? "student" : "students"}`
            : "Select a parent"
        }
        icon={<CreditCard className="h-4 w-4 text-info" />}
      >
        <div className="space-y-4">
          {error ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
              {error}
            </div>
          ) : null}

          {!selectedParent ? (
            <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-10 text-center text-sm font-bold text-muted-foreground">
              Select a parent to manage payments.
            </p>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SummaryTile label="Family Debt" value={formatMoney(totals.debt, familyCurrency)} detail="Across all children" tone="bg-rose-50" />
                <SummaryTile label="Due" value={formatMoney(totals.due, familyCurrency)} detail="Need payment now" tone="bg-amber-50" />
                <SummaryTile label="Upcoming" value={formatMoney(totals.upcoming, familyCurrency)} detail="Scheduled ahead" tone="bg-sky-50" />
                <SummaryTile label="Paid" value={formatMoney(totals.paid, familyCurrency)} detail="Recorded payments" tone="bg-emerald-50" />
              </div>

              {!children.length ? (
                <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-8 text-center text-sm font-bold text-muted-foreground">
                  No students are linked to this parent yet. Link students in the Parents tab.
                </p>
              ) : (
                <>
                  <div className="flex flex-wrap gap-2">
                    {children.map((child) => {
                      const childId = getStudentRowId(child);
                      const active = childId === selectedChildResolvedId;
                      const childDebt = moneyValue(paymentSummaryFor(child).debt_total);
                      return (
                        <button
                          key={childId}
                          type="button"
                          onClick={() => setSelectedChildId(childId)}
                          className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm font-bold transition-colors ${
                            active
                              ? "border-foreground/20 bg-foreground text-background"
                              : "border-foreground/10 bg-background hover:bg-muted"
                          }`}
                        >
                          <span className="truncate">{asString(child.full_name) || "Student"}</span>
                          {childDebt > 0 ? (
                            <span
                              className={`rounded-md px-1.5 py-0.5 text-[10px] ${
                                active ? "bg-background/20 text-background" : "bg-rose-50 text-rose-700"
                              }`}
                            >
                              {formatMoney(childDebt, asString(paymentSummaryFor(child).currency) || "UZS")}
                            </span>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                  <div className="rounded-lg border border-foreground/10 bg-background p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold">
                          {asString(selectedChild?.full_name) || "Student"}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          Code {getStudentCode(selectedChild) || "-"} ·{" "}
                          {asString(selectedChild?.school_name) || "School"}
                        </p>
                      </div>
                      <span className="text-xs font-bold text-muted-foreground">
                        Course {progress.rate}% · {progress.completed}/{progress.total} lessons
                      </span>
                    </div>
                    {subjects.length ? (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {subjects.map((subject) => (
                          <span
                            key={subject}
                            className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-semibold text-foreground"
                          >
                            {subject}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <SummaryTile label="Paid" value={formatMoney(summary.paid_total, ledgerCurrency)} tone="bg-emerald-50" />
                    <SummaryTile label="Debt" value={formatMoney(summary.debt_total, ledgerCurrency)} tone="bg-rose-50" />
                    <SummaryTile label="Due" value={formatMoney(summary.due_total, ledgerCurrency)} tone="bg-amber-50" />
                    <SummaryTile label="Upcoming" value={formatMoney(summary.upcoming_total, ledgerCurrency)} tone="bg-sky-50" />
                  </div>
                  <form onSubmit={savePayment} className="rounded-lg border border-foreground/10 bg-background p-3">
                    <div className="grid gap-3 md:grid-cols-7">
                      <label className="md:col-span-2">
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Subject
                        </span>
                        <select
                          value={form.subject}
                          onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))}
                          disabled={!subjects.length}
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-bold outline-none focus:border-foreground/30 disabled:opacity-50"
                        >
                          <option value="">{subjects.length ? "Select subject" : "No subjects"}</option>
                          {subjects.map((subject) => (
                            <option key={subject} value={subject}>
                              {subject}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="md:col-span-1">
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Month
                        </span>
                        <input
                          value={form.month}
                          onChange={(event) => setForm((current) => ({ ...current, month: event.target.value }))}
                          placeholder="June 2026"
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label className="md:col-span-1">
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Amount
                        </span>
                        <input
                          value={form.amount}
                          onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
                          inputMode="decimal"
                          placeholder="0"
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label className="md:col-span-1">
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Status
                        </span>
                        <select
                          value={form.status}
                          onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-bold outline-none focus:border-foreground/30"
                        >
                          {creationStatuses.map((status) => (
                            <option key={status.value} value={status.value}>
                              {status.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="md:col-span-1">
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Due
                        </span>
                        <input
                          type="date"
                          value={form.due_date}
                          onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value }))}
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label className="md:col-span-1">
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Paid
                        </span>
                        <input
                          type="date"
                          value={form.paid_at}
                          onChange={(event) => setForm((current) => ({ ...current, paid_at: event.target.value }))}
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                    </div>

                    <div className="mt-3 flex flex-col gap-3 md:flex-row">
                      <input
                        value={form.notes}
                        onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                        placeholder="Notes"
                        className="h-10 min-w-0 flex-1 rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                      />
                      <button
                        type="submit"
                        disabled={saving || loading || !selectedChildResolvedId || !form.subject.trim() || !form.amount.trim()}
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-50"
                      >
                        <Plus className="h-4 w-4" />
                        Add Record
                      </button>
                    </div>
                  </form>
                  <div className="miniapp-table-scroll rounded-lg border border-foreground/10">
                    <table className="w-full min-w-[48rem] text-left">
                      <thead className="bg-muted/60">
                        <tr>
                          {["Subject", "Month", "Amount", "Status", "Due", "Paid", "Notes", ""].map((heading) => (
                            <th
                              key={heading || "actions"}
                              className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-muted-foreground"
                            >
                              {heading}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {payments.length ? (
                          payments.map((row) => (
                            <tr key={asNumber(row.id)} className="border-t border-foreground/5">
                              <td className="px-3 py-3 text-xs font-bold">{asString(row.subject) || "-"}</td>
                              <td className="px-3 py-3 text-xs font-semibold">{asString(row.month) || "Payment"}</td>
                              <td className="whitespace-nowrap px-3 py-3 text-xs text-muted-foreground">
                                {formatMoney(row.amount, asString(row.currency) || ledgerCurrency)}
                              </td>
                              <td className="px-3 py-3">
                                <span className={`inline-flex rounded-md border px-2 py-1 text-[11px] font-bold ${statusClass(row.state ?? row.status)}`}>
                                  {statusLabel(row.state ?? row.status)}
                                </span>
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-xs text-muted-foreground">{formatDate(row.due_date)}</td>
                              <td className="whitespace-nowrap px-3 py-3 text-xs text-muted-foreground">{formatDate(row.paid_at)}</td>
                              <td className="px-3 py-3 text-xs text-muted-foreground">{asString(row.notes) || "-"}</td>
                              <td className="px-3 py-3">
                                <div className="flex items-center justify-end gap-1.5">
                                  {asString(row.state ?? row.status).toLowerCase() === "paid" ? (
                                    <button
                                      type="button"
                                      onClick={() => markPaid(row, false)}
                                      disabled={saving}
                                      className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 px-2.5 text-xs font-bold text-muted-foreground hover:bg-muted disabled:opacity-50"
                                      aria-label="Mark payment as unpaid"
                                    >
                                      <Undo2 className="h-3.5 w-3.5" />
                                      Unpay
                                    </button>
                                  ) : (
                                    <button
                                      type="button"
                                      onClick={() => markPaid(row, true)}
                                      disabled={saving}
                                      className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 text-xs font-bold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                                      aria-label="Mark payment as paid"
                                    >
                                      <Check className="h-3.5 w-3.5" />
                                      Mark paid
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => deletePayment(row)}
                                    disabled={saving}
                                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted disabled:opacity-50"
                                    aria-label="Delete payment record"
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="px-3 py-10 text-center text-sm font-bold text-muted-foreground">
                              {loading ? "Loading payments..." : "No payment records yet."}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </ChartCard>
    </div>
  );
}
