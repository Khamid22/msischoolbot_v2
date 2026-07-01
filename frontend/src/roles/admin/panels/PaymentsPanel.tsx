import { useEffect, useMemo, useState, type FormEvent } from "react";
import { CreditCard, Plus, Search, UserRound, X } from "lucide-react";
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

function initialsFor(value: unknown) {
  const parts = asString(value).split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "PA"
  );
}

function parentDisplayName(parent: Record<string, unknown> | undefined) {
  return (
    asString(parent?.full_name) ||
    asString(parent?.display_name) ||
    asString(parent?.name) ||
    asString(parent?.login) ||
    "Parent"
  );
}

function parentPhone(parent: Record<string, unknown> | undefined) {
  const phone = asString(parent?.phone) || asString(parent?.parent_phone);
  const login = asString(parent?.login);
  return phone || (login.startsWith("+") ? login : "");
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

function rowIsPaid(row: PaymentRow) {
  return asString(row.state ?? row.status).toLowerCase() === "paid";
}

function paymentRecordDate(row: PaymentRow) {
  return formatDate(row.paid_at || row.due_date || row.created_at || row.month);
}

function paidAmountFor(row: PaymentRow, currency: string) {
  return rowIsPaid(row) ? formatMoney(row.amount, asString(row.currency) || currency) : "-";
}

function nextPaymentFor(row: PaymentRow, currency: string) {
  if (rowIsPaid(row)) return "-";
  const amount = formatMoney(row.amount, asString(row.currency) || currency);
  const date = formatDate(row.due_date);
  return date === "-" ? amount : `${amount} · ${date}`;
}

function remainingDebtFor(row: PaymentRow, currency: string) {
  const explicit = moneyValue(row.remaining_debt ?? row.debt_remaining);
  if (explicit > 0) return formatMoney(explicit, asString(row.currency) || currency);
  return rowIsPaid(row) ? formatMoney(0, asString(row.currency) || currency) : formatMoney(row.amount, asString(row.currency) || currency);
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
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    subject: "",
    currency: "UZS",
    paid_date: "",
    paid_amount: "",
    next_payment_amount: "",
    next_payment_date: "",
    remaining_debt: "",
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

  function openParentPayments(parentId: number) {
    selectParent(parentId);
    setPaymentModalOpen(true);
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
    const defaultSubject = subjectsList(selectedChild)[0] || "";
    setForm((current) => ({
      ...current,
      subject: defaultSubject,
      paid_date: "",
      paid_amount: "",
      next_payment_amount: "",
      next_payment_date: "",
      remaining_debt: "",
      notes: "",
    }));
    void loadPayments(selectedChildResolvedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedChildResolvedId]);

  async function savePayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const childId = selectedChildResolvedId;
    if (!childId || saving) return;
    const paidAmount = moneyValue(form.paid_amount);
    const nextAmount = moneyValue(form.next_payment_amount);
    const amount = paidAmount > 0 ? paidAmount : nextAmount;
    if (amount <= 0) {
      setError("Enter paid amount or next payment amount.");
      return;
    }
    const status = paidAmount > 0 ? "paid" : "due";
    const notes = [form.notes.trim(), form.remaining_debt.trim() ? `Remaining debt: ${form.remaining_debt.trim()}` : ""]
      .filter(Boolean)
      .join(" · ");
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
        body: JSON.stringify({
          subject: form.subject,
          month: form.paid_date || form.next_payment_date || "Payment",
          amount: String(amount),
          currency: form.currency,
          status,
          due_date: status === "due" ? form.next_payment_date : "",
          paid_at: status === "paid" ? form.paid_date : "",
          notes,
        }),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to save payment.");
        return;
      }
      applyResult(childId, json);
      setForm({
        subject: subjectsList(selectedChild)[0] || "",
        currency: "UZS",
        paid_date: "",
        paid_amount: "",
        next_payment_amount: "",
        next_payment_date: "",
        remaining_debt: "",
        notes: "",
      });
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const overviewTotals = visibleParents.reduce<FamilyTotals>(
    (acc, parent) => {
      const parentTotals = familyTotals(parent);
      acc.debt += parentTotals.debt;
      acc.due += parentTotals.due;
      acc.upcoming += parentTotals.upcoming;
      acc.paid += parentTotals.paid;
      if (parentTotals.currency) acc.currency = parentTotals.currency;
      return acc;
    },
    { debt: 0, due: 0, upcoming: 0, paid: 0, currency: "UZS" },
  );
  const overviewCurrency = overviewTotals.currency || "UZS";
  const ledgerCurrency = asString(summary.currency) || overviewCurrency;

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

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryTile
          label="Total Debt"
          value={formatMoney(overviewTotals.debt, overviewCurrency)}
          detail="Across visible parents"
          tone="bg-rose-50"
        />
        <SummaryTile
          label="Due Now"
          value={formatMoney(overviewTotals.due, overviewCurrency)}
          detail="Needs follow-up"
          tone="bg-amber-50"
        />
        <SummaryTile
          label="Upcoming"
          value={formatMoney(overviewTotals.upcoming, overviewCurrency)}
          detail="Scheduled ahead"
          tone="bg-sky-50"
        />
        <SummaryTile
          label="Paid"
          value={formatMoney(overviewTotals.paid, overviewCurrency)}
          detail="Recorded payments"
          tone="bg-emerald-50"
        />
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
                          onClick={() => openParentPayments(parentId)}
                          className={`inline-flex h-8 items-center rounded-lg px-3 text-xs font-bold ${
                            active
                              ? "bg-primary text-primary-foreground"
                              : "border border-foreground/10 bg-background text-foreground hover:bg-muted"
                          }`}
                        >
                          View
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

      {paymentModalOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-3"
          onClick={() => setPaymentModalOpen(false)}
        >
          <div
            className="max-h-[92dvh] w-full max-w-6xl overflow-y-auto rounded-xl bg-background shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="space-y-4 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <CreditCard className="h-4 w-4 text-info" />
                    <h3 className="text-base font-bold">Payment Records</h3>
                  </div>
                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <p className="min-w-0">
                      <span className="font-bold text-muted-foreground">Parent: </span>
                      <span className="font-bold">{parentDisplayName(selectedParent)}</span>
                    </p>
                    <p className="min-w-0">
                      <span className="font-bold text-muted-foreground">Phone Number: </span>
                      <span className="font-bold">{parentPhone(selectedParent) || "-"}</span>
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setPaymentModalOpen(false)}
                  className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-foreground/10 bg-background hover:bg-muted"
                  aria-label="Close payment details"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {error ? (
                <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
                  {error}
                </div>
              ) : null}

              {!selectedParent ? (
                <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-10 text-center text-sm font-bold text-muted-foreground">
                  Select a parent to manage payments.
                </p>
              ) : !children.length ? (
                <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-8 text-center text-sm font-bold text-muted-foreground">
                  No students are linked to this parent yet. Link students in the Parents tab.
                </p>
              ) : (
                <>
                  <label className="block">
                    <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                      Child
                    </span>
                    <select
                      value={selectedChildResolvedId || ""}
                      onChange={(event) => setSelectedChildId(Number(event.target.value))}
                      className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-bold outline-none focus:border-foreground/30"
                    >
                      {children.map((child) => {
                        const childId = getStudentRowId(child);
                        return (
                          <option key={childId} value={childId}>
                            {asString(child.full_name) || "Student"}
                          </option>
                        );
                      })}
                    </select>
                  </label>

                  <form onSubmit={savePayment} className="rounded-lg border border-foreground/10 bg-white p-3">
                    <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1fr_1fr]">
                      <label>
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Date
                        </span>
                        <input
                          type="date"
                          value={form.paid_date}
                          onChange={(event) => setForm((current) => ({ ...current, paid_date: event.target.value }))}
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label>
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Paid - Amount
                        </span>
                        <input
                          value={form.paid_amount}
                          onChange={(event) => setForm((current) => ({ ...current, paid_amount: event.target.value }))}
                          inputMode="decimal"
                          placeholder="0"
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label>
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Next Payment - Amount
                        </span>
                        <input
                          value={form.next_payment_amount}
                          onChange={(event) => setForm((current) => ({ ...current, next_payment_amount: event.target.value }))}
                          inputMode="decimal"
                          placeholder="0"
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label>
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Next Payment - Date
                        </span>
                        <input
                          type="date"
                          value={form.next_payment_date}
                          onChange={(event) => setForm((current) => ({ ...current, next_payment_date: event.target.value }))}
                          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm outline-none focus:border-foreground/30"
                        />
                      </label>
                      <label>
                        <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Remaining Debt
                        </span>
                        <input
                          value={form.remaining_debt}
                          onChange={(event) => setForm((current) => ({ ...current, remaining_debt: event.target.value }))}
                          inputMode="decimal"
                          placeholder={formatMoney(summary.debt_total, ledgerCurrency)}
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
                        disabled={
                          saving ||
                          loading ||
                          !selectedChildResolvedId ||
                          !form.subject.trim() ||
                          (!form.paid_amount.trim() && !form.next_payment_amount.trim())
                        }
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-50"
                      >
                        <Plus className="h-4 w-4" />
                        Add Payment
                      </button>
                    </div>
                  </form>

                  <div className="miniapp-table-scroll rounded-lg border border-foreground/10 bg-white">
                    <table className="w-full min-w-[48rem] text-left">
                      <thead className="bg-muted/60">
                        <tr>
                          {["Date", "Paid - Amount", "Next Payment - Amount and Date", "Remaining Debt"].map((heading) => (
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
                        {payments.length ? (
                          payments.map((row) => (
                            <tr key={asNumber(row.id)} className="border-t border-foreground/5">
                              <td className="whitespace-nowrap px-3 py-3 text-xs font-semibold">
                                {paymentRecordDate(row)}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-xs font-bold text-emerald-700">
                                {paidAmountFor(row, ledgerCurrency)}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-xs font-semibold text-amber-700">
                                {nextPaymentFor(row, ledgerCurrency)}
                              </td>
                              <td className="whitespace-nowrap px-3 py-3 text-xs font-bold text-rose-700">
                                {remainingDebtFor(row, ledgerCurrency)}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={4} className="px-3 py-10 text-center text-sm font-bold text-muted-foreground">
                              {loading ? "Loading payments..." : "No payment records yet."}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
