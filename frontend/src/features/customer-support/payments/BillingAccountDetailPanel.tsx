import { CalendarClock, ExternalLink, Loader2, ReceiptText, X } from "lucide-react";
import type { FormEvent } from "react";
import type { BillingAccountDetail } from "@/features/customer-support/model";
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
  mutationError: Error | null;
  onClose: () => void;
  onRetry: () => void;
  onSaveSchedule: (
    event: FormEvent<HTMLFormElement>,
    account: BillingAccountDetail,
  ) => void;
  onOpenInvoice: (invoiceId: number) => void;
};

export function BillingAccountDetailPanel({
  account,
  loading,
  error,
  saving,
  mutationError,
  onClose,
  onRetry,
  onSaveSchedule,
  onOpenInvoice,
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
  const currentItems = new Map(account.scheduleItems.map((item) => [item.groupId, item]));
  const today = new Date(
    Date.now() - new Date().getTimezoneOffset() * 60_000,
  ).toISOString().slice(0, 10);

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b border-border p-4">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-black text-foreground">{account.studentName}</h2>
          <p className="text-xs font-bold text-muted-foreground">
            {account.parentName || "No linked parent"} · {account.schoolName}
          </p>
        </div>
        <button type="button" className={secondaryButton} onClick={onClose} aria-label="Close billing account detail">
          <X className="h-4 w-4" />
        </button>
      </header>
      <div className="space-y-5 p-4">
        <dl className="grid grid-cols-2 gap-2">
          {[
            ["Schedule", account.scheduleStatus],
            ["Monthly", money(account.monthlyAmountMinor / 100, account.currency)],
            ["Open invoices", String(account.openInvoiceCount)],
            ["Telegram", `${account.linkedTelegramRecipients} linked · ${account.unlinkedTelegramRecipients} unlinked`],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-muted/60 p-3">
              <dt className="text-[0.625rem] font-black uppercase text-muted-foreground">{label}</dt>
              <dd className="mt-1 break-words text-sm font-black text-foreground">{value}</dd>
            </div>
          ))}
        </dl>

        {mutationError ? (
          <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">
            {mutationError.message}
          </p>
        ) : null}

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
          <form
            className="rounded-lg border border-border p-4"
            onSubmit={(event) => onSaveSchedule(event, account)}
          >
            <h3 className="font-black text-foreground">Billing schedule</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              One monthly amount per active academic group.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div>
                <Label htmlFor="account-billing-day">Billing day</Label>
                <input id="account-billing-day" name="billingDay" type="number" min="1" max="28" required defaultValue={account.billingDay || 1} className={inputClass} />
              </div>
              <div>
                <Label htmlFor="account-billing-start">Starts on</Label>
                <input id="account-billing-start" name="startsOn" type="date" required defaultValue={account.effectiveDate || today} className={inputClass} />
              </div>
              <div>
                <Label htmlFor="account-billing-status">Status</Label>
                <select id="account-billing-status" name="status" defaultValue={account.scheduleStatus === "missing" ? "active" : account.scheduleStatus} className={inputClass}>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="ended">Ended</option>
                </select>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {account.enrollmentOptions.map((option) => {
                const existing = currentItems.get(option.groupId);
                return (
                  <fieldset key={option.groupId} className="rounded-lg border border-border p-3">
                    <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-black">
                      <input type="checkbox" name={`enabled-${option.groupId}`} defaultChecked={Boolean(existing)} className="h-4 w-4 accent-primary" />
                      {option.subjectName} · {option.groupName}
                    </label>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div>
                        <Label htmlFor={`account-amount-${option.groupId}`}>Monthly UZS</Label>
                        <input id={`account-amount-${option.groupId}`} name={`amount-${option.groupId}`} type="number" min="1" step="1" defaultValue={existing ? existing.amountMinor / 100 : ""} className={inputClass} />
                      </div>
                      <div>
                        <Label htmlFor={`account-description-${option.groupId}`}>Invoice line</Label>
                        <input id={`account-description-${option.groupId}`} name={`description-${option.groupId}`} maxLength={200} defaultValue={existing?.description || option.subjectName} className={inputClass} />
                      </div>
                    </div>
                  </fieldset>
                );
              })}
            </div>
            {!account.enrollmentOptions.length ? (
              <p className="mt-3 text-sm font-bold text-destructive">
                This student needs an active group enrollment before billing can be configured.
              </p>
            ) : null}
            <button type="submit" disabled={saving || !account.enrollmentOptions.length} className={`${primaryButton} mt-4`}>
              {saving
                ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                : <CalendarClock className="h-4 w-4" />}
              Save schedule
            </button>
          </form>
        )}

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
                  <span className="block font-mono text-xs font-black">{invoice.invoiceNumber}</span>
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
      </div>
    </section>
  );
}
