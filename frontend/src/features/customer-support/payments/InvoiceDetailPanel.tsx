import {
  Ban,
  Clock3,
  CreditCard,
  Loader2,
  ReceiptText,
  RotateCcw,
  X,
} from "lucide-react";
import type { FormEvent } from "react";
import type { UnifiedInvoiceDetail } from "@/features/customer-support/model";
import {
  formatDate,
  inputClass,
  Label,
  money,
  primaryButton,
  secondaryButton,
} from "@/features/customer-support/shared/ui";

const OPEN_INVOICE_STATUSES = new Set(["issued", "partially_paid", "overdue"]);

type InvoiceDetailPanelProps = {
  invoice: UnifiedInvoiceDetail | undefined;
  loading: boolean;
  error: Error | null;
  saving: boolean;
  mutationError: Error | null;
  onClose: () => void;
  onRetry: () => void;
  onRecordPayment: (
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
  ) => void;
  onReversePayment: (
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
    paymentId: number,
  ) => void;
  onVoidInvoice: (
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
  ) => void;
};

export function InvoiceDetailPanel({
  invoice,
  loading,
  error,
  saving,
  mutationError,
  onClose,
  onRetry,
  onRecordPayment,
  onReversePayment,
  onVoidInvoice,
}: InvoiceDetailPanelProps) {
  if (loading) {
    return (
      <div
        className="min-h-80 animate-pulse rounded-xl border border-border bg-muted motion-reduce:animate-none"
        role="status"
      />
    );
  }
  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-destructive/30 bg-destructive/5 p-5"
      >
        <p className="text-sm font-bold text-destructive">{error.message}</p>
        <button type="button" className={`${secondaryButton} mt-3`} onClick={onRetry}>
          Try again
        </button>
      </div>
    );
  }
  if (!invoice) {
    return (
      <div className="grid min-h-80 place-items-center rounded-xl border border-dashed border-border bg-card p-8 text-center">
        <div>
          <ReceiptText className="mx-auto h-8 w-8 text-muted-foreground" />
          <h2 className="mt-3 font-black text-foreground">Select an invoice</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Review balances, settlements, and audit-safe corrections.
          </p>
        </div>
      </div>
    );
  }
  const canAcceptPayment = (
    OPEN_INVOICE_STATUSES.has(invoice.status) && invoice.balanceMinor > 0
  );
  const nowLocal = new Date(
    Date.now() - new Date().getTimezoneOffset() * 60_000,
  ).toISOString().slice(0, 16);

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b border-border p-4">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-black text-foreground">
            {invoice.studentName}
          </h2>
          <p className="font-mono text-xs font-bold text-muted-foreground">
            {invoice.invoiceNumber}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className={secondaryButton}
          aria-label="Close invoice detail"
        >
          <X className="h-4 w-4" />
        </button>
      </header>
      <div className="space-y-5 p-4">
        <InvoiceSummary invoice={invoice} />
        {mutationError ? (
          <p
            role="alert"
            className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive"
          >
            {mutationError.message}
          </p>
        ) : null}
        {canAcceptPayment ? (
          <ManualPaymentForm
            invoice={invoice}
            nowLocal={nowLocal}
            saving={saving}
            onSubmit={onRecordPayment}
          />
        ) : null}
        <NotificationTimeline invoice={invoice} />
        <SettlementHistory
          invoice={invoice}
          saving={saving}
          onReversePayment={onReversePayment}
        />
        {invoice.paidMinor === 0 && invoice.status !== "voided" ? (
          <form
            className="flex flex-col gap-2 border-t border-border pt-4 sm:flex-row"
            onSubmit={(event) => onVoidInvoice(event, invoice)}
          >
            <input
              name="reason"
              required
              minLength={2}
              placeholder="Reason for voiding invoice"
              className={inputClass}
            />
            <button type="submit" disabled={saving} className={secondaryButton}>
              <Ban className="h-4 w-4" /> Void invoice
            </button>
          </form>
        ) : null}
      </div>
    </section>
  );
}

function InvoiceSummary({ invoice }: { invoice: UnifiedInvoiceDetail }) {
  return (
    <>
      <dl className="grid grid-cols-2 gap-2">
        {[
          ["Total", money(invoice.totalMinor / 100, invoice.currency)],
          ["Balance", money(invoice.balanceMinor / 100, invoice.currency)],
          ["Status", invoice.status.replace(/_/g, " ")],
          ["Due", formatDate(invoice.dueDate)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg bg-muted/60 p-3">
            <dt className="text-[0.625rem] font-black uppercase text-muted-foreground">
              {label}
            </dt>
            <dd className="mt-1 break-words text-sm font-black text-foreground">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {invoice.enforcementState && invoice.paymentDeadlineAt ? (
        <div
          className={`flex items-start gap-3 rounded-lg border p-3 ${
            invoice.enforcementState === "held"
              ? "border-destructive/30 bg-destructive/5"
              : "border-amber-300 bg-amber-50"
          }`}
        >
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
      {invoice.billingCycle ? (
        <div className="rounded-lg border border-border p-3">
          <p className="text-sm font-black">Recurring billing allocation</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatDate(invoice.billingCycle.billingPeriod)} ·{" "}
            {money(invoice.billingCycle.allocatedMinor / 100, invoice.billingCycle.currency)}
            {" "}reviewed ·{" "}
            {money(invoice.billingCycle.remainingMinor / 100, invoice.billingCycle.currency)}
            {" "}invoiced
          </p>
        </div>
      ) : null}
    </>
  );
}

function ManualPaymentForm({
  invoice,
  nowLocal,
  saving,
  onSubmit,
}: {
  invoice: UnifiedInvoiceDetail;
  nowLocal: string;
  saving: boolean;
  onSubmit: InvoiceDetailPanelProps["onRecordPayment"];
}) {
  return (
    <form
      className="space-y-3 rounded-lg border border-border p-3"
      onSubmit={(event) => onSubmit(event, invoice)}
    >
      <h3 className="text-sm font-black text-foreground">Record manual payment</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="ledger-payment-amount">Amount in UZS</Label>
          <input
            id="ledger-payment-amount"
            name="amount"
            type="number"
            min="0.01"
            step="0.01"
            max={invoice.balanceMinor / 100}
            defaultValue={invoice.balanceMinor / 100}
            required
            className={inputClass}
          />
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
          <input
            id="ledger-payment-date"
            name="paidAt"
            type="datetime-local"
            defaultValue={nowLocal}
            required
            className={inputClass}
          />
        </div>
        <div>
          <Label htmlFor="ledger-payment-reference">Receipt or reference</Label>
          <input
            id="ledger-payment-reference"
            name="reference"
            required
            className={inputClass}
          />
        </div>
      </div>
      <div>
        <Label htmlFor="ledger-payment-reason">Reason</Label>
        <input
          id="ledger-payment-reason"
          name="reason"
          required
          minLength={2}
          className={inputClass}
        />
      </div>
      <button type="submit" disabled={saving} className={primaryButton}>
        {saving ? (
          <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
        ) : (
          <CreditCard className="h-4 w-4" />
        )}
        Record payment
      </button>
    </form>
  );
}

function NotificationTimeline({ invoice }: { invoice: UnifiedInvoiceDetail }) {
  return (
    <section>
      <h3 className="text-sm font-black text-foreground">Notification timeline</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Delivery totals are shown without exposing Telegram identifiers.
      </p>
      <ol className="mt-3 space-y-2">
        {invoice.notificationTimeline.length ? (
          invoice.notificationTimeline.map((entry) => {
            const statusTone = entry.status === "sent"
              ? "bg-emerald-100 text-emerald-800"
              : entry.status === "failed"
                ? "bg-destructive/10 text-destructive"
                : entry.status === "pending"
                  ? "bg-sky-100 text-sky-800"
                  : "bg-muted text-muted-foreground";
            return (
              <li key={entry.stage} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-black text-foreground">
                      {entry.stage.replace(/_/g, " ")}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {formatDate(entry.scheduledFor, true)}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${statusTone}`}
                  >
                    {entry.status}
                  </span>
                </div>
                {entry.recipientCount ? (
                  <p className="mt-2 text-xs font-semibold text-muted-foreground">
                    {entry.recipientCount} recipients · {entry.sentCount} sent ·{" "}
                    {entry.pendingCount} pending · {entry.skippedCount} skipped ·{" "}
                    {entry.failedCount} failed
                  </p>
                ) : null}
              </li>
            );
          })
        ) : (
          <li className="rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground">
            No enforcement schedule exists for this invoice.
          </li>
        )}
      </ol>
    </section>
  );
}

function SettlementHistory({
  invoice,
  saving,
  onReversePayment,
}: {
  invoice: UnifiedInvoiceDetail;
  saving: boolean;
  onReversePayment: InvoiceDetailPanelProps["onReversePayment"];
}) {
  return (
    <section>
      <h3 className="text-sm font-black text-foreground">Settlement history</h3>
      <div className="mt-2 space-y-2">
        {invoice.payments.length ? (
          invoice.payments.map((payment) => (
            <article
              key={payment.paymentId}
              className="rounded-lg border border-border p-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-black text-foreground">
                    {money(payment.amountMinor / 100, payment.currency)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {payment.method.replace(/_/g, " ")} ·{" "}
                    {formatDate(payment.paidAt, true)}
                  </p>
                  <p className="mt-1 text-xs font-semibold text-muted-foreground">
                    {payment.reference}
                  </p>
                </div>
                <span className="rounded-full bg-muted px-2 py-1 text-[0.625rem] font-black uppercase text-muted-foreground">
                  {payment.status}
                </span>
              </div>
              {payment.source === "manual" && payment.status === "completed" ? (
                <form
                  className="mt-3 flex flex-col gap-2 sm:flex-row"
                  onSubmit={(event) => onReversePayment(
                    event,
                    invoice,
                    payment.paymentId,
                  )}
                >
                  <input
                    name="reason"
                    required
                    minLength={2}
                    placeholder="Reversal reason"
                    className={inputClass}
                  />
                  <button
                    type="submit"
                    disabled={saving}
                    className={secondaryButton}
                  >
                    <RotateCcw className="h-4 w-4" /> Reverse
                  </button>
                </form>
              ) : null}
            </article>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">
            No settlement has been recorded.
          </p>
        )}
      </div>
    </section>
  );
}
