import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Clock3, CreditCard, Loader2, ReceiptText, RotateCcw, Search, X } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
import { getSupport, sendSupport } from "@/features/customer-support/api";
import type {
  AdmissionInvoiceQueue,
  AdmissionInvoiceQueueItem,
  UnifiedInvoiceDetail,
} from "@/features/customer-support/model";
import {
  formatDate,
  inputClass,
  Label,
  money,
  primaryButton,
  secondaryButton,
} from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";

const OPEN_INVOICE_STATUSES = new Set(["issued", "partially_paid", "overdue"]);

export function PaymentsPage({ csrfToken }: { csrfToken: string }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [origin, setOrigin] = useState("all");
  const [enforcement, setEnforcement] = useState("all");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(null);
  const query = useQuery({
    queryKey: ["customer-support", "payments", search, status, origin, enforcement],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({
        q: search,
        status,
        origin,
        enforcement,
        limit: "100",
      });
      return getSupport<AdmissionInvoiceQueue>(`/payments/invoices?${params}`, signal);
    },
  });
  const detailQuery = useQuery({
    queryKey: ["customer-support", "invoice", selectedInvoiceId],
    queryFn: ({ signal }) => getSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${selectedInvoiceId}`,
      signal,
    ),
    enabled: selectedInvoiceId !== null,
  });
  const mutation = useMutation({
    mutationFn: (operation: () => Promise<UnifiedInvoiceDetail>) => operation(),
    onSuccess: (invoice) => {
      queryClient.setQueryData(["customer-support", "invoice", invoice.invoiceId], invoice);
      void queryClient.invalidateQueries({ queryKey: ["customer-support", "payments"] });
      void queryClient.invalidateQueries({ queryKey: ["customer-support", "dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["customer-support", "student"] });
    },
  });

  function recordPayment(event: FormEvent<HTMLFormElement>, invoice: UnifiedInvoiceDetail) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const paidAt = String(data.get("paidAt") || "");
    mutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${invoice.invoiceId}/manual-payments`,
      "POST",
      {
        amount: Number(data.get("amount")),
        method: String(data.get("method") || "cash"),
        paidAt: new Date(paidAt).toISOString(),
        reference: String(data.get("reference") || "").trim(),
        reason: String(data.get("reason") || "").trim(),
        expectedVersion: invoice.version,
      },
      csrfToken,
    ));
  }

  function reversePayment(
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
    paymentId: number,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoice-payments/${paymentId}/reversal`,
      "POST",
      {
        expectedInvoiceVersion: invoice.version,
        reason: String(data.get("reason") || "").trim(),
      },
      csrfToken,
    ));
  }

  function voidInvoice(event: FormEvent<HTMLFormElement>, invoice: UnifiedInvoiceDetail) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${invoice.invoiceId}/void`,
      "POST",
      {
        expectedVersion: invoice.version,
        reason: String(data.get("reason") || "").trim(),
      },
      csrfToken,
    ));
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Payments"
        subtitle="One invoice ledger for current students, admissions, manual settlements, and Payme."
        badge={(
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase text-primary">
            Invoice ledger
          </span>
        )}
      />
      <div className="grid gap-3 rounded-xl border border-border bg-card p-3 shadow-sm lg:grid-cols-[1fr_11rem_12rem_12rem]">
        <label className="relative">
          <span className="sr-only">Search invoices</span>
          <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
          <input
            className={`${inputClass} pl-10`}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Invoice, student, parent, or code"
          />
        </label>
        <select
          className={inputClass}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          aria-label="Invoice status"
        >
          <option value="all">All statuses</option>
          {["issued", "partially_paid", "overdue", "paid", "voided"].map((value) => (
            <option key={value} value={value}>{value.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select
          className={inputClass}
          value={enforcement}
          onChange={(event) => setEnforcement(event.target.value)}
          aria-label="Billing access state"
        >
          <option value="all">All access states</option>
          <option value="countdown">48-hour countdown</option>
          <option value="held">Payment-only</option>
          <option value="cleared">Access restored</option>
          <option value="not_scheduled">Not scheduled</option>
        </select>
        <select
          className={inputClass}
          value={origin}
          onChange={(event) => setOrigin(event.target.value)}
          aria-label="Invoice origin"
        >
          <option value="all">All students</option>
          <option value="student_billing">Current students</option>
          <option value="admission">Admissions</option>
          <option value="legacy_migration">Migrated records</option>
        </select>
      </div>

      {query.isError ? (
        <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm font-bold text-destructive">
          {query.error instanceof Error ? query.error.message : "Invoices could not be loaded."}
        </p>
      ) : null}

      <div className="grid min-h-[32rem] gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(28rem,0.95fr)]">
        <InvoiceList
          loading={query.isLoading}
          invoices={query.data?.items || []}
          total={query.data?.total || 0}
          selectedInvoiceId={selectedInvoiceId}
          onSelect={setSelectedInvoiceId}
        />
        <InvoiceDetailPanel
          invoice={detailQuery.data}
          loading={detailQuery.isLoading}
          error={detailQuery.error}
          saving={mutation.isPending}
          mutationError={mutation.error}
          onClose={() => setSelectedInvoiceId(null)}
          onRecordPayment={recordPayment}
          onReversePayment={reversePayment}
          onVoidInvoice={voidInvoice}
        />
      </div>
    </div>
  );
}

function InvoiceList({
  loading,
  invoices,
  total,
  selectedInvoiceId,
  onSelect,
}: {
  loading: boolean;
  invoices: AdmissionInvoiceQueueItem[];
  total: number;
  selectedInvoiceId: number | null;
  onSelect: (invoiceId: number) => void;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <header className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-black text-foreground">Invoices</h2>
        <p className="text-xs font-semibold text-muted-foreground">{total} records</p>
      </header>
      {loading ? (
        <div className="space-y-2 p-4" role="status">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
          ))}
        </div>
      ) : invoices.length ? (
        <div className="divide-y divide-border">
          {invoices.map((invoice) => (
            <button
              key={invoice.invoiceId}
              type="button"
              onClick={() => onSelect(invoice.invoiceId)}
              className={`grid min-h-24 w-full gap-2 px-4 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none sm:grid-cols-[1fr_auto] ${
                selectedInvoiceId === invoice.invoiceId ? "bg-primary/5" : "hover:bg-muted/60"
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-foreground">{invoice.studentName}</p>
                <p className="truncate text-xs font-semibold text-muted-foreground">
                  {[invoice.parentName, invoice.schoolName].filter(Boolean).join(" · ")}
                </p>
                <p className="mt-2 font-mono text-[0.6875rem] font-black text-foreground">
                  {invoice.invoiceNumber}
                </p>
              </div>
              <div className="sm:text-right">
                <p className="text-sm font-black text-foreground">
                  {money(invoice.balanceMinor / 100, invoice.currency)}
                </p>
                <p className="text-xs font-semibold text-muted-foreground">
                  Due {formatDate(invoice.dueDate)}
                </p>
                <span className="mt-1 inline-flex rounded-full bg-muted px-2 py-1 text-[0.625rem] font-black uppercase text-muted-foreground">
                  {invoice.status.replace(/_/g, " ")}
                </span>
                {invoice.enforcementState ? (
                  <span className={`ml-1 mt-1 inline-flex rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${
                    invoice.enforcementState === "held"
                      ? "bg-destructive/10 text-destructive"
                      : invoice.enforcementState === "countdown"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-primary/10 text-primary"
                  }`}>
                    {invoice.enforcementState === "held"
                      ? "payment only"
                      : invoice.enforcementState.replace(/_/g, " ")}
                  </span>
                ) : null}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="p-5">
          <EmptyState
            title="No invoices found"
            detail="Current-student and admission invoices will appear in this shared ledger."
            icon={<CreditCard className="h-5 w-5" />}
          />
        </div>
      )}
    </section>
  );
}

function InvoiceDetailPanel({
  invoice,
  loading,
  error,
  saving,
  mutationError,
  onClose,
  onRecordPayment,
  onReversePayment,
  onVoidInvoice,
}: {
  invoice: UnifiedInvoiceDetail | undefined;
  loading: boolean;
  error: Error | null;
  saving: boolean;
  mutationError: Error | null;
  onClose: () => void;
  onRecordPayment: (event: FormEvent<HTMLFormElement>, invoice: UnifiedInvoiceDetail) => void;
  onReversePayment: (
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
    paymentId: number,
  ) => void;
  onVoidInvoice: (event: FormEvent<HTMLFormElement>, invoice: UnifiedInvoiceDetail) => void;
}) {
  if (loading) {
    return <div className="min-h-80 animate-pulse rounded-xl border border-border bg-muted motion-reduce:animate-none" role="status" />;
  }
  if (error) {
    return <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-5 text-sm font-bold text-destructive">{error.message}</p>;
  }
  if (!invoice) {
    return (
      <div className="grid min-h-80 place-items-center rounded-xl border border-dashed border-border bg-card p-8 text-center">
        <div>
          <ReceiptText className="mx-auto h-8 w-8 text-muted-foreground" />
          <h2 className="mt-3 font-black text-foreground">Select an invoice</h2>
          <p className="mt-1 text-sm text-muted-foreground">Review balances, settlements, and audit-safe corrections.</p>
        </div>
      </div>
    );
  }
  const canAcceptPayment = OPEN_INVOICE_STATUSES.has(invoice.status) && invoice.balanceMinor > 0;
  const nowLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b border-border p-4">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-black text-foreground">{invoice.studentName}</h2>
          <p className="font-mono text-xs font-bold text-muted-foreground">{invoice.invoiceNumber}</p>
        </div>
        <button type="button" onClick={onClose} className={secondaryButton} aria-label="Close invoice detail">
          <X className="h-4 w-4" />
        </button>
      </header>
      <div className="space-y-5 p-4">
        <dl className="grid grid-cols-2 gap-2">
          {[
            ["Total", money(invoice.totalMinor / 100, invoice.currency)],
            ["Balance", money(invoice.balanceMinor / 100, invoice.currency)],
            ["Status", invoice.status.replace(/_/g, " ")],
            ["Due", formatDate(invoice.dueDate)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-muted/60 p-3">
              <dt className="text-[0.625rem] font-black uppercase text-muted-foreground">{label}</dt>
              <dd className="mt-1 break-words text-sm font-black text-foreground">{value}</dd>
            </div>
          ))}
        </dl>
        {invoice.enforcementState && invoice.paymentDeadlineAt ? (
          <div className={`flex items-start gap-3 rounded-lg border p-3 ${
            invoice.enforcementState === "held"
              ? "border-destructive/30 bg-destructive/5"
              : "border-amber-300 bg-amber-50"
          }`}>
            <Clock3 className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <div>
              <p className="text-sm font-black">
                {invoice.enforcementState === "held"
                  ? "Household is in payment-only mode"
                  : "48-hour payment countdown"}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Deadline {formatDate(invoice.paymentDeadlineAt, true)}
              </p>
            </div>
          </div>
        ) : null}

        {mutationError ? (
          <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">
            {mutationError.message}
          </p>
        ) : null}

        {canAcceptPayment ? (
          <form className="space-y-3 rounded-lg border border-border p-3" onSubmit={(event) => onRecordPayment(event, invoice)}>
            <h3 className="text-sm font-black text-foreground">Record manual payment</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="ledger-payment-amount">Amount in UZS</Label>
                <input id="ledger-payment-amount" name="amount" type="number" min="0.01" step="0.01" max={invoice.balanceMinor / 100} defaultValue={invoice.balanceMinor / 100} required className={inputClass} />
              </div>
              <div>
                <Label htmlFor="ledger-payment-method">Method</Label>
                <select id="ledger-payment-method" name="method" className={inputClass}>
                  <option value="cash">Cash</option>
                  <option value="bank_transfer">Bank transfer</option>
                  <option value="card_terminal">Card terminal</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <Label htmlFor="ledger-payment-date">Paid at</Label>
                <input id="ledger-payment-date" name="paidAt" type="datetime-local" defaultValue={nowLocal} required className={inputClass} />
              </div>
              <div>
                <Label htmlFor="ledger-payment-reference">Receipt or reference</Label>
                <input id="ledger-payment-reference" name="reference" required className={inputClass} />
              </div>
            </div>
            <div>
              <Label htmlFor="ledger-payment-reason">Reason</Label>
              <input id="ledger-payment-reason" name="reason" required minLength={2} className={inputClass} />
            </div>
            <button type="submit" disabled={saving} className={primaryButton}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <CreditCard className="h-4 w-4" />}
              Record payment
            </button>
          </form>
        ) : null}

        <section>
          <h3 className="text-sm font-black text-foreground">Settlement history</h3>
          <div className="mt-2 space-y-2">
            {invoice.payments.length ? invoice.payments.map((payment) => (
              <article key={payment.paymentId} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-black text-foreground">{money(payment.amountMinor / 100, payment.currency)}</p>
                    <p className="text-xs text-muted-foreground">{payment.method.replace(/_/g, " ")} · {formatDate(payment.paidAt, true)}</p>
                    <p className="mt-1 text-xs font-semibold text-muted-foreground">{payment.reference}</p>
                  </div>
                  <span className="rounded-full bg-muted px-2 py-1 text-[0.625rem] font-black uppercase text-muted-foreground">{payment.status}</span>
                </div>
                {payment.source === "manual" && payment.status === "completed" ? (
                  <form className="mt-3 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => onReversePayment(event, invoice, payment.paymentId)}>
                    <input name="reason" required minLength={2} placeholder="Reversal reason" className={inputClass} />
                    <button type="submit" disabled={saving} className={secondaryButton}>
                      <RotateCcw className="h-4 w-4" /> Reverse
                    </button>
                  </form>
                ) : null}
              </article>
            )) : <p className="text-sm text-muted-foreground">No settlement has been recorded.</p>}
          </div>
        </section>

        {invoice.paidMinor === 0 && invoice.status !== "voided" ? (
          <form className="flex flex-col gap-2 border-t border-border pt-4 sm:flex-row" onSubmit={(event) => onVoidInvoice(event, invoice)}>
            <input name="reason" required minLength={2} placeholder="Reason for voiding invoice" className={inputClass} />
            <button type="submit" disabled={saving} className={secondaryButton}>
              <Ban className="h-4 w-4" /> Void invoice
            </button>
          </form>
        ) : null}
      </div>
    </section>
  );
}
