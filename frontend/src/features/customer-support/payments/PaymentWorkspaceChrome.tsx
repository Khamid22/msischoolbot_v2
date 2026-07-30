import { CreditCard } from "lucide-react";
import type { ReactNode } from "react";
import { BillingAccountEmptyGraphic } from "@/features/customer-support/payments/BillingAccountList";
import type { PaymentView } from "@/features/customer-support/payments/PaymentFilters";
import { secondaryButton } from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";

export function PaymentViewButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`min-h-11 rounded-md px-4 text-sm font-black focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
        active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
}

export function PaymentCollectionFallback({
  view,
  state,
  error,
  retry,
  reset,
}: {
  view: PaymentView;
  state: "loading" | "error" | "empty" | "ready";
  error: Error | null;
  retry: () => void;
  reset: () => void;
}) {
  if (state === "loading") {
    return (
      <div
        className="h-72 animate-pulse rounded-xl border border-border bg-muted motion-reduce:animate-none"
        role="status"
      />
    );
  }
  return (
    <EmptyState
      title={state === "error"
        ? `${view === "accounts" ? "Billing accounts" : "Invoices"} could not be loaded`
        : `No ${view === "accounts" ? "billing accounts" : "invoices"} found`}
      detail={state === "error"
        ? error?.message || "Try again."
        : view === "accounts"
          ? "Active students and pending admissions will appear here, even before an invoice exists."
          : "Generated admission and student invoices will appear in this ledger."}
      icon={view === "accounts"
        ? <BillingAccountEmptyGraphic />
        : <CreditCard className="h-5 w-5" />}
      action={(
        <button
          type="button"
          className={secondaryButton}
          onClick={state === "error" ? retry : reset}
        >
          {state === "error" ? "Try again" : "Reset filters"}
        </button>
      )}
    />
  );
}
