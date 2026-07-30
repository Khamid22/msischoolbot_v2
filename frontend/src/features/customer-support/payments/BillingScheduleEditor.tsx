import {
  CalendarClock,
  ChevronDown,
  Loader2,
  PauseCircle,
} from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import type { BillingAccountDetail } from "@/features/customer-support/model";
import {
  inputClass,
  Label,
  primaryButton,
  secondaryButton,
} from "@/features/customer-support/shared/ui";

type Props = {
  account: BillingAccountDetail;
  saving: boolean;
  error: Error | null;
  onSaveSchedule: (
    event: FormEvent<HTMLFormElement>,
    account: BillingAccountDetail,
  ) => void;
};

export function BillingScheduleEditor({
  account,
  saving,
  error,
  onSaveSchedule,
}: Props) {
  const [pricingMode, setPricingMode] = useState(account.pricingMode || "per_subject");
  const [showApplyChoice, setShowApplyChoice] = useState(false);
  const prices = new Map(
    account.subjectPrices.map((price) => [price.subjectId, price.amountMinor]),
  );
  const subjects = Array.from(
    new Map(
      account.enrollmentOptions.map((option) => [option.subjectId, option]),
    ).values(),
  );
  const hasCurrentInvoice = account.billingCycles.some((cycle) => (
    Boolean(cycle.invoiceId) && cycle.state === "invoiced"
  ));
  const requiresApplyChoice = account.scheduleStatus !== "missing"
    && (hasCurrentInvoice || !account.canApplyCurrentCycle);

  return (
    <form
      className="rounded-lg border border-border p-4"
      onSubmit={(event) => {
        setShowApplyChoice(false);
        onSaveSchedule(event, account);
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-black text-foreground">Billing schedule</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Configure once. Future monthly invoices use this schedule automatically.
          </p>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.625rem] font-black uppercase text-primary">
          {account.scheduleStatus}
        </span>
      </div>

      {error ? (
        <p role="alert" className="mt-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">
          {error.message}
        </p>
      ) : null}

      <div className="mt-4">
        <Label htmlFor="account-billing-day">Monthly billing day</Label>
        <input
          id="account-billing-day"
          name="billingDay"
          type="number"
          min="1"
          max="28"
          required
          defaultValue={account.billingDay || 1}
          className={inputClass}
        />
        <p className="mt-1 text-xs text-muted-foreground">
          Recurring payment deadline: 00:05 Asia/Tashkent on this day.
        </p>
      </div>

      <fieldset className="mt-4">
        <legend className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
          Monthly pricing
        </legend>
        <div className="mt-1 grid grid-cols-2 gap-2">
          {[
            ["total", "Total monthly"],
            ["per_subject", "Per subject"],
          ].map(([value, label]) => (
            <label
              key={value}
              className={`flex min-h-11 cursor-pointer items-center justify-center rounded-lg border px-3 text-center text-sm font-black ${
                pricingMode === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-muted-foreground hover:bg-muted"
              }`}
            >
              <input
                type="radio"
                name="pricingMode"
                value={value}
                checked={pricingMode === value}
                onChange={() => setPricingMode(value as "total" | "per_subject")}
                className="sr-only"
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      {pricingMode === "total" ? (
        <div className="mt-4 rounded-lg border border-border p-3">
          <Label htmlFor="account-total-amount">Total monthly amount (UZS)</Label>
          <input
            id="account-total-amount"
            name="totalAmount"
            type="number"
            min="1"
            step="1"
            required
            defaultValue={
              account.totalAmountMinor
                ? account.totalAmountMinor / 100
                : account.monthlyAmountMinor
                  ? account.monthlyAmountMinor / 100
                  : ""
            }
            className={inputClass}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Covers all {subjects.length} currently enrolled subjects and later enrollments.
          </p>
        </div>
      ) : (
        <div className="mt-4 space-y-2">
          {subjects.map((subject) => (
            <div
              key={subject.subjectId}
              className="grid items-end gap-2 rounded-lg border border-border p-3 sm:grid-cols-[minmax(0,1fr)_10rem]"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-foreground">
                  {subject.subjectName}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {account.enrollmentOptions
                    .filter((option) => option.subjectId === subject.subjectId)
                    .map((option) => option.groupName)
                    .join(", ")}
                </p>
              </div>
              <div>
                <Label htmlFor={`subject-amount-${subject.subjectId}`}>Monthly UZS</Label>
                <input
                  id={`subject-amount-${subject.subjectId}`}
                  name={`subjectAmount-${subject.subjectId}`}
                  type="number"
                  min="1"
                  step="1"
                  required
                  defaultValue={
                    prices.has(subject.subjectId)
                      ? Number(prices.get(subject.subjectId)) / 100
                      : ""
                  }
                  className={inputClass}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {!subjects.length ? (
        <p className="mt-3 text-sm font-bold text-destructive">
          This student needs an active subject enrollment before billing can be configured.
        </p>
      ) : null}

      {account.pricingRequiredSubjects.length ? (
        <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm font-bold text-amber-950">
          Pricing is required for {account.pricingRequiredSubjects
            .map((subject) => subject.subjectName)
            .join(", ")} before the next invoice can be issued.
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {requiresApplyChoice ? (
          <button
            type="button"
            disabled={saving || !subjects.length}
            onClick={() => setShowApplyChoice(true)}
            className={primaryButton}
          >
            <SaveIcon saving={saving} />
            Update schedule
          </button>
        ) : (
          <button
            type="submit"
            data-apply-to="current_cycle"
            disabled={saving || !subjects.length}
            className={primaryButton}
          >
            <SaveIcon saving={saving} />
            {account.scheduleStatus === "missing" ? "Start billing" : "Save schedule"}
          </button>
        )}
        <ScheduleActions account={account} saving={saving} />
      </div>

      {showApplyChoice ? (
        <ApplyChoice
          account={account}
          saving={saving}
          onCancel={() => setShowApplyChoice(false)}
        />
      ) : null}
    </form>
  );
}

function SaveIcon({ saving }: { saving: boolean }) {
  return saving
    ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
    : <CalendarClock className="h-4 w-4" />;
}

function ScheduleActions({
  account,
  saving,
}: {
  account: BillingAccountDetail;
  saving: boolean;
}) {
  return (
    <details className="relative">
      <summary className={`${secondaryButton} cursor-pointer list-none`}>
        <PauseCircle className="h-4 w-4" />
        Schedule actions
        <ChevronDown className="h-4 w-4" />
      </summary>
      <div className="absolute left-0 top-[calc(100%+0.375rem)] z-20 min-w-44 rounded-lg border border-border bg-card p-2 shadow-card-hover">
        <button
          type="submit"
          name="status"
          value={account.scheduleStatus === "active" ? "paused" : "active"}
          disabled={saving}
          className="min-h-11 w-full rounded-md px-3 text-left text-sm font-black hover:bg-muted"
        >
          {account.scheduleStatus === "active" ? "Pause schedule" : "Resume schedule"}
        </button>
        <button
          type="submit"
          name="status"
          value="ended"
          disabled={saving}
          className="min-h-11 w-full rounded-md px-3 text-left text-sm font-black text-destructive hover:bg-destructive/5"
        >
          End schedule
        </button>
      </div>
    </details>
  );
}

function ApplyChoice({
  account,
  saving,
  onCancel,
}: {
  account: BillingAccountDetail;
  saving: boolean;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-foreground/40 p-4">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="schedule-apply-title"
        className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-card-hover"
      >
        <h4 id="schedule-apply-title" className="text-lg font-black">
          When should this change apply?
        </h4>
        <p className="mt-1 text-sm text-muted-foreground">
          The current invoice is preserved unless you explicitly replace it.
        </p>
        {!account.canApplyCurrentCycle && account.currentCycleEditBlockReason ? (
          <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm font-bold text-amber-950">
            {account.currentCycleEditBlockReason}
          </p>
        ) : null}
        <div className="mt-4 grid gap-2">
          <button
            type="submit"
            data-apply-to="current_cycle"
            disabled={saving || !account.canApplyCurrentCycle}
            className={primaryButton}
          >
            Apply now and restart 48 hours
          </button>
          <button
            type="submit"
            data-apply-to="next_cycle"
            disabled={saving}
            className={secondaryButton}
          >
            Apply from next cycle
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="min-h-11 rounded-lg px-3 text-sm font-black text-muted-foreground hover:bg-muted"
          >
            Cancel
          </button>
        </div>
      </section>
    </div>
  );
}

export function DeadlineCountdown({ deadlineAt }: { deadlineAt: string }) {
  const remaining = () => Math.max(
    0,
    Math.ceil((Date.parse(deadlineAt) - Date.now()) / 1_000),
  );
  const [seconds, setSeconds] = useState(remaining);
  useEffect(() => {
    const timer = window.setInterval(() => setSeconds(remaining()), 1_000);
    return () => window.clearInterval(timer);
  }, [deadlineAt]);
  const hours = Math.floor(seconds / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  const rest = seconds % 60;
  return (
    <p className="mt-2 inline-flex rounded-md bg-foreground px-2 py-1 font-mono text-xs font-black tabular-nums text-background">
      {seconds > 0
        ? [hours, minutes, rest].map((value) => String(value).padStart(2, "0")).join(":")
        : "Payment deadline reached"}
    </p>
  );
}
