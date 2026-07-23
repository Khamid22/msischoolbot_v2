import { Check, CircleDollarSign, Edit3, Plus, RefreshCw, XCircle } from "lucide-react";
import type { PaymentRecord, StudentDetail } from "@/features/customer-support/model";
import { dangerButton, DetailSection, formatDate, money, secondaryButton } from "@/features/customer-support/shared/ui";
import { StatusBadge } from "@/shared/ui/StatusBadge";

export function StudentPaymentsSection({
  detail,
  onAdd,
  onEdit,
  onSettle,
  onVoid,
}: {
  detail: StudentDetail;
  onAdd: () => void;
  onEdit: (payment: PaymentRecord) => void;
  onSettle: (payment: PaymentRecord, paid: boolean) => void;
  onVoid: (payment: PaymentRecord) => void;
}) {
  const { items, totals, currency } = detail.payments;
  return (
    <DetailSection
      title="Payments"
      icon={<CircleDollarSign className="h-4 w-4" aria-hidden="true" />}
      action={(
        <button type="button" onClick={onAdd} className={secondaryButton}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add payment
        </button>
      )}
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(["paid", "due", "debt", "upcoming"] as const).map((key) => (
          <div key={key} className="rounded-lg bg-muted px-3 py-2">
            <p className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">{key}</p>
            <p className="mt-1 break-words text-sm font-black tabular-nums text-foreground">{money(totals[key] || 0, currency)}</p>
          </div>
        ))}
      </div>
      {items.length ? (
        <div className="mt-4 space-y-2">
          {items.map((payment) => {
            const voided = payment.state === "voided";
            return (
              <article key={payment.id} className={`rounded-lg border p-3 ${voided ? "border-border bg-muted/60" : "border-border bg-background"}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-black text-foreground">{payment.subject || "Subject"} · {payment.month_label || "Payment"}</p>
                    <p className="mt-1 text-xs font-semibold text-muted-foreground">
                      Due {formatDate(payment.due_date)} · {money(payment.amount, payment.currency || currency)}
                    </p>
                    {voided && payment.void_reason ? <p className="mt-1 text-xs font-bold text-destructive">Voided: {payment.void_reason}</p> : null}
                  </div>
                  <StatusBadge status={payment.state} className="text-[0.625rem]" />
                </div>
                {!voided ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button type="button" className={secondaryButton} onClick={() => onEdit(payment)}>
                      <Edit3 className="h-4 w-4" aria-hidden="true" />
                      Edit
                    </button>
                    <button type="button" className={secondaryButton} onClick={() => onSettle(payment, payment.state !== "paid")}>
                      {payment.state === "paid"
                        ? <RefreshCw className="h-4 w-4" aria-hidden="true" />
                        : <Check className="h-4 w-4" aria-hidden="true" />}
                      {payment.state === "paid" ? "Mark unpaid" : "Mark paid"}
                    </button>
                    <button type="button" className={dangerButton} onClick={() => onVoid(payment)}>
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      Void
                    </button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <p className="mt-4 text-sm font-semibold text-muted-foreground">No payment records.</p>
      )}
    </DetailSection>
  );
}
