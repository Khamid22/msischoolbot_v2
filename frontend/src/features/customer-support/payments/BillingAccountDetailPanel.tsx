import { CalendarClock, ExternalLink, ReceiptText, X } from "lucide-react";
import type { FormEvent } from "react";
import type {
  BillingAccountDetail,
  BillingCycle,
  BillingCycleInvoiceCandidate,
  BillingCycleReview,
} from "@/features/customer-support/model";
import {
  BillingScheduleEditor,
  DeadlineCountdown,
} from "@/features/customer-support/payments/BillingScheduleEditor";
import {
  formatDate,
  inputClass,
  Label,
  money,
  primaryButton,
  secondaryButton,
} from "@/features/customer-support/shared/ui";

type Props = {
  account: BillingAccountDetail | undefined;
  loading: boolean;
  error: Error | null;
  saving: boolean;
  scheduleError: Error | null;
  cycleError: Error | null;
  onClose: () => void;
  onRetry: () => void;
  onSaveSchedule: (
    event: FormEvent<HTMLFormElement>,
    account: BillingAccountDetail,
  ) => void;
  onOpenInvoice: (invoiceId: number) => void;
  onReviewInvoice: (
    event: FormEvent<HTMLFormElement>,
    cycle: BillingCycle,
    candidate: BillingCycleInvoiceCandidate,
  ) => void;
  onReverseReview: (
    event: FormEvent<HTMLFormElement>,
    review: BillingCycleReview,
  ) => void;
};

export function BillingAccountDetailPanel({
  account,
  loading,
  error,
  saving,
  scheduleError,
  cycleError,
  onClose,
  onRetry,
  onSaveSchedule,
  onOpenInvoice,
  onReviewInvoice,
  onReverseReview,
}: Props) {
  if (loading) {
    return (
      <div className="min-h-80 animate-pulse rounded-xl border border-border bg-muted motion-reduce:animate-none" role="status" />
    );
  }
  if (error) {
    return (
      <div role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-5">
        <p className="text-sm font-bold text-destructive">{error.message}</p>
        <button type="button" className={`${secondaryButton} mt-3`} onClick={onRetry}>
          Try again
        </button>
      </div>
    );
  }
  if (!account) {
    return (
      <div className="grid min-h-80 place-items-center rounded-xl border border-dashed border-border bg-card p-8 text-center">
        <div>
          <CalendarClock className="mx-auto h-8 w-8 text-muted-foreground" />
          <h2 className="mt-3 font-black text-foreground">Select a billing account</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Review its schedule, invoices, Telegram coverage, and access state.
          </p>
        </div>
      </div>
    );
  }
  const visibleCycles = [...account.billingCycles]
    .filter((cycle) => cycle.state !== "superseded")
    .sort((left, right) => right.billingPeriod.localeCompare(left.billingPeriod))
    .slice(0, 1);

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b border-border p-4">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-black text-foreground">
            {account.studentName}
          </h2>
          <p className="text-xs font-bold text-muted-foreground">
            {account.parentName || "No linked parent"} · {account.schoolName}
          </p>
        </div>
        <button
          type="button"
          className={secondaryButton}
          onClick={onClose}
          aria-label="Close billing account detail"
        >
          <X className="h-4 w-4" />
        </button>
      </header>
      <div className="space-y-5 p-4">
        <dl className="grid grid-cols-2 gap-2">
          {[
            ["Schedule", account.scheduleStatus],
            ["Monthly", money(account.monthlyAmountMinor / 100, account.currency)],
            ["Open invoices", String(account.openInvoiceCount)],
            [
              "Telegram",
              `${account.linkedTelegramRecipients} linked · ${account.unlinkedTelegramRecipients} unlinked`,
            ],
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

        {account.accountType === "admission" ? (
          <div className="rounded-lg border border-border p-4">
            <h3 className="font-black text-foreground">Admission billing schedule</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Admission schedules are read-only here and remain owned by Admissions.
            </p>
            <a
              href={`/customer-support/admissions?admissionId=${account.accountId}`}
              className={`${secondaryButton} mt-3 inline-flex`}
            >
              Open admission <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        ) : (
          <BillingScheduleEditor
            key={`${account.accountId}-${account.scheduleVersion ?? "new"}`}
            account={account}
            saving={saving}
            error={scheduleError}
            onSaveSchedule={onSaveSchedule}
          />
        )}

        {account.accountType === "student" ? (
          <CurrentBilling
            cycles={visibleCycles}
            saving={saving}
            error={cycleError}
            onReviewInvoice={onReviewInvoice}
            onReverseReview={onReverseReview}
          />
        ) : null}

        <InvoiceHistory account={account} onOpenInvoice={onOpenInvoice} />
      </div>
    </section>
  );
}

function CurrentBilling({
  cycles,
  saving,
  error,
  onReviewInvoice,
  onReverseReview,
}: {
  cycles: BillingCycle[];
  saving: boolean;
  error: Error | null;
  onReviewInvoice: Props["onReviewInvoice"];
  onReverseReview: Props["onReverseReview"];
}) {
  return (
    <div>
      <h3 className="flex items-center gap-2 font-black text-foreground">
        <CalendarClock className="h-4 w-4 text-primary" /> Current billing
      </h3>
      {error ? (
        <p role="alert" className="mt-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">
          {error.message}
        </p>
      ) : null}
      <div className="mt-2 space-y-3">
        {cycles.length ? cycles.map((cycle) => (
          <CycleCard
            key={cycle.cycleId}
            cycle={cycle}
            saving={saving}
            onReviewInvoice={onReviewInvoice}
            onReverseReview={onReverseReview}
          />
        )) : (
          <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            Saving this schedule creates the first invoice and starts its 48-hour deadline.
          </p>
        )}
      </div>
    </div>
  );
}

function CycleCard({
  cycle,
  saving,
  onReviewInvoice,
  onReverseReview,
}: {
  cycle: BillingCycle;
  saving: boolean;
  onReviewInvoice: Props["onReviewInvoice"];
  onReverseReview: Props["onReverseReview"];
}) {
  return (
    <section className="rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-black">{formatDate(cycle.billingPeriod)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Deadline {formatDate(cycle.deadlineAt, true)}
          </p>
          {cycle.invoiceId && cycle.state === "invoiced" ? (
            <DeadlineCountdown deadlineAt={cycle.deadlineAt} />
          ) : null}
        </div>
        <span className={`rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${
          cycle.state === "review_required"
            ? "bg-amber-100 text-amber-900"
            : cycle.state === "satisfied"
              ? "bg-emerald-100 text-emerald-800"
              : "bg-primary/10 text-primary"
        }`}>
          {cycle.state.replace(/_/g, " ")}
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2">
        {[
          ["Expected", cycle.expectedMinor],
          ["Allocated", cycle.allocatedMinor],
          ["Remaining", cycle.remainingMinor],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md bg-muted/60 p-2">
            <dt className="text-[0.5625rem] font-black uppercase text-muted-foreground">
              {label}
            </dt>
            <dd className="mt-1 break-words text-xs font-black">
              {money(Number(value) / 100, cycle.currency)}
            </dd>
          </div>
        ))}
      </dl>
      {cycle.reviewCandidates.map((candidate) => (
        <ReviewCandidate
          key={candidate.invoiceId}
          cycle={cycle}
          candidate={candidate}
          saving={saving}
          onReviewInvoice={onReviewInvoice}
        />
      ))}
      {cycle.reviews.map((review) => (
        <ReviewResult
          key={review.reviewId}
          cycle={cycle}
          review={review}
          saving={saving}
          onReverseReview={onReverseReview}
        />
      ))}
    </section>
  );
}

function ReviewCandidate({
  cycle,
  candidate,
  saving,
  onReviewInvoice,
}: {
  cycle: BillingCycle;
  candidate: BillingCycleInvoiceCandidate;
  saving: boolean;
  onReviewInvoice: Props["onReviewInvoice"];
}) {
  return (
    <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3">
      <p className="text-sm font-black text-amber-950">
        Review paid invoice {candidate.invoiceNumber}
      </p>
      <p className="mt-1 text-xs text-amber-900">
        {money(candidate.availableMinor / 100, candidate.currency)} is available.
        Applying it prevents a duplicate monthly invoice.
      </p>
      <form
        className="mt-3 grid gap-2"
        onSubmit={(event) => onReviewInvoice(event, cycle, candidate)}
      >
        <div>
          <Label htmlFor={`cycle-allocation-${cycle.cycleId}-${candidate.invoiceId}`}>
            Amount to apply
          </Label>
          <input
            id={`cycle-allocation-${cycle.cycleId}-${candidate.invoiceId}`}
            name="amount"
            type="number"
            min="1"
            max={Math.min(candidate.availableMinor, cycle.remainingMinor) / 100}
            defaultValue={Math.min(candidate.availableMinor, cycle.remainingMinor) / 100}
            required
            className={inputClass}
          />
        </div>
        <div>
          <Label htmlFor={`cycle-reason-${cycle.cycleId}-${candidate.invoiceId}`}>
            Review reason
          </Label>
          <input
            id={`cycle-reason-${cycle.cycleId}-${candidate.invoiceId}`}
            name="reason"
            minLength={2}
            defaultValue="Apply completed payment to this billing cycle."
            required
            className={inputClass}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="submit" name="decision" value="apply" disabled={saving} className={primaryButton}>
            Apply payment
          </button>
          <button type="submit" name="decision" value="exclude" disabled={saving} className={secondaryButton}>
            Exclude from cycle
          </button>
        </div>
      </form>
    </div>
  );
}

function ReviewResult({
  cycle,
  review,
  saving,
  onReverseReview,
}: {
  cycle: BillingCycle;
  review: BillingCycleReview;
  saving: boolean;
  onReverseReview: Props["onReverseReview"];
}) {
  return (
    <div className="mt-3 rounded-lg bg-muted/60 p-3">
      <p className="text-xs font-black">
        {review.invoiceNumber} · {review.decision} ·{" "}
        {money(review.allocatedMinor / 100, cycle.currency)}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{review.reason}</p>
      {review.status === "active" && !cycle.invoiceId ? (
        <form
          className="mt-2 flex gap-2"
          onSubmit={(event) => onReverseReview(event, review)}
        >
          <input
            name="reason"
            aria-label="Reversal reason"
            minLength={2}
            placeholder="Correction reason"
            required
            className={inputClass}
          />
          <button type="submit" disabled={saving} className={secondaryButton}>
            Reverse
          </button>
        </form>
      ) : null}
    </div>
  );
}

function InvoiceHistory({
  account,
  onOpenInvoice,
}: {
  account: BillingAccountDetail;
  onOpenInvoice: (invoiceId: number) => void;
}) {
  return (
    <div>
      <h3 className="flex items-center gap-2 font-black text-foreground">
        <ReceiptText className="h-4 w-4 text-primary" /> Invoice history
      </h3>
      <div className="mt-2 divide-y divide-border rounded-lg border border-border">
        {account.invoices.length ? account.invoices.map((invoice) => (
          <button
            key={invoice.invoiceId}
            type="button"
            onClick={() => onOpenInvoice(invoice.invoiceId)}
            className="flex min-h-14 w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30"
          >
            <span>
              <span className="block font-mono text-xs font-black">
                {invoice.invoiceNumber}
              </span>
              <span className="block text-xs text-muted-foreground">
                {formatDate(invoice.billingPeriod)} · {invoice.status.replace(/_/g, " ")}
              </span>
            </span>
            <span className="text-sm font-black">
              {money(invoice.balanceMinor / 100, invoice.currency)}
            </span>
          </button>
        )) : (
          <p className="p-4 text-sm text-muted-foreground">
            No invoices have been generated for this account.
          </p>
        )}
      </div>
    </div>
  );
}
