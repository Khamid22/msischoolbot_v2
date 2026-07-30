import {
  Activity,
  BellRing,
  CircleAlert,
  Clock3,
  ListChecks,
  ReceiptText,
  ShieldAlert,
} from "lucide-react";
import type { BillingAutomationStatus } from "@/features/customer-support/model";
import {
  formatDate,
  secondaryButton,
} from "@/features/customer-support/shared/ui";

export function AutomationStatusPanel({
  status,
  loading,
  error,
  onRetry,
}: {
  status: BillingAutomationStatus | undefined;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
}) {
  if (loading) {
    return (
      <div
        className="h-14 animate-pulse rounded-xl border border-border bg-muted motion-reduce:animate-none"
        role="status"
        aria-label="Loading billing automation status"
      />
    );
  }
  if (error || !status) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
        <div>
          <p className="text-sm font-black text-destructive">Automation status unavailable</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {error?.message || "The worker and notification report could not be loaded."}
          </p>
        </div>
        <button type="button" className={secondaryButton} onClick={onRetry}>
          Try again
        </button>
      </div>
    );
  }
  const stateTone = status.workerState === "healthy"
    ? "bg-emerald-100 text-emerald-800"
    : status.workerState === "stalled"
      ? "bg-destructive/10 text-destructive"
      : "bg-amber-100 text-amber-800";
  const metrics = [
    {
      label: "Due billing profiles",
      value: `${status.currentlyDueBillingProfiles} / ${status.activeBillingProfiles}`,
      icon: Clock3,
    },
    {
      label: "Telegram coverage",
      value: `${status.linkedTelegramRecipients} linked · ${status.unlinkedTelegramRecipients} unlinked`,
      icon: BellRing,
    },
    {
      label: "Delivery exceptions",
      value: `${status.pendingNotificationDeliveries} pending · ${status.failedNotificationDeliveries} failed`,
      icon: CircleAlert,
    },
    {
      label: "Payment controls",
      value: `${status.openInvoicesWithoutEnforcement} unscheduled · ${status.activePaymentOnlyHolds} holds`,
      icon: ShieldAlert,
    },
    {
      label: "Open invoices",
      value: `${status.openInvoices} awaiting settlement`,
      icon: ReceiptText,
    },
    {
      label: "Finance jobs",
      value: `${status.pendingFinanceJobs} pending or running`,
      icon: ListChecks,
    },
  ];

  return (
    <details className="group rounded-xl border border-border bg-card shadow-sm">
      <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30">
        <div>
          <h2
            id="billing-automation-title"
            className="flex items-center gap-2 text-sm font-black text-foreground"
          >
            <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
            Billing automation
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Updated {formatDate(status.generatedAt, true)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-xs font-semibold text-muted-foreground sm:inline">
            {status.openInvoices} open · {status.activePaymentOnlyHolds} holds ·{" "}
            {status.failedNotificationDeliveries} failed
          </span>
          <span
            className={`rounded-full px-2.5 py-1 text-[0.6875rem] font-black uppercase ${stateTone}`}
          >
            Worker {status.workerState.replace(/_/g, " ")}
          </span>
        </div>
      </summary>
      <div className="border-t border-border px-4 pb-4">
      <dl className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-lg bg-muted/60 p-3">
            <dt className="flex items-center gap-1.5 text-[0.625rem] font-black uppercase text-muted-foreground">
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {label}
            </dt>
            <dd className="mt-1 text-xs font-black text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs font-semibold text-muted-foreground">
        Last successful worker activity:{" "}
        {status.lastSuccessfulFinanceWorkerAt
          ? formatDate(status.lastSuccessfulFinanceWorkerAt, true)
          : "none recorded"}
      </p>
      </div>
    </details>
  );
}
