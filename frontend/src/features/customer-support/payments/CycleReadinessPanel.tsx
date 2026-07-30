import { BellRing, CalendarClock, ChevronRight, CircleAlert, ShieldAlert } from "lucide-react";
import type { BillingCycleReadiness } from "@/features/customer-support/model";
import { formatDate, money, secondaryButton } from "@/features/customer-support/shared/ui";

export function CycleReadinessPanel({
  readiness,
  loading,
  error,
  onRetry,
  onOpenAccount,
}: {
  readiness: BillingCycleReadiness | undefined;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
  onOpenAccount: (studentId: number) => void;
}) {
  if (loading) {
    return <div className="h-14 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />;
  }
  if (error || !readiness) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-3">
        <p className="text-sm font-bold text-destructive">
          {error?.message || "Billing-cycle readiness could not be loaded."}
        </p>
        <button type="button" className={secondaryButton} onClick={onRetry}>Retry</button>
      </div>
    );
  }
  const attentionCycles = readiness.cycles.filter((cycle) => (
    cycle.state === "review_required" || cycle.state === "scheduled"
  ));
  return (
    <details className="rounded-xl border border-border bg-card shadow-sm">
      <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-black">
            <CalendarClock className="h-4 w-4 text-primary" />
            Billing-cycle readiness
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {readiness.reviewRequiredCycles} need review · {readiness.readyToIssueCycles} ready to issue
          </p>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[0.6875rem] font-black uppercase ${
          readiness.reviewRequiredCycles ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-800"
        }`}>
          {readiness.reviewRequiredCycles ? "Review required" : "Ready"}
        </span>
      </summary>
      <div className="space-y-3 border-t border-border p-4">
        <dl className="grid gap-2 sm:grid-cols-3">
          <ReadinessMetric icon={CircleAlert} label="Review" value={readiness.reviewRequiredCycles} />
          <ReadinessMetric icon={ShieldAlert} label="Potential holds" value={readiness.potentialHoldCount} />
          <ReadinessMetric
            icon={BellRing}
            label="Telegram coverage"
            value={`${readiness.linkedTelegramRecipients} linked · ${readiness.unlinkedTelegramRecipients} unlinked`}
          />
        </dl>
        {attentionCycles.length ? (
          <div className="divide-y divide-border rounded-lg border border-border">
            {attentionCycles.map((cycle) => (
              <button
                key={cycle.cycleId}
                type="button"
                onClick={() => onOpenAccount(cycle.studentId)}
                className="flex min-h-14 w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-black">{cycle.studentName}</span>
                  <span className="block text-xs text-muted-foreground">
                    {formatDate(cycle.billingPeriod)} · {cycle.state.replace(/_/g, " ")}
                  </span>
                </span>
                <span className="flex items-center gap-2 text-xs font-black">
                  {money(cycle.remainingMinor / 100, cycle.currency)}
                  <ChevronRight className="h-4 w-4" />
                </span>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No billing cycles currently require action.</p>
        )}
      </div>
    </details>
  );
}

function ReadinessMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof CircleAlert;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg bg-muted/60 p-3">
      <dt className="flex items-center gap-1.5 text-[0.625rem] font-black uppercase text-muted-foreground">
        <Icon className="h-3.5 w-3.5" /> {label}
      </dt>
      <dd className="mt-1 text-xs font-black">{value}</dd>
    </div>
  );
}
