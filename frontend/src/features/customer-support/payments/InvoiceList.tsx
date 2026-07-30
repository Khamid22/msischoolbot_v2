import { CreditCard } from "lucide-react";
import type { AdmissionInvoiceQueueItem } from "@/features/customer-support/model";
import {
  formatDate,
  money,
} from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";

export function InvoiceList({
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
            <div
              key={item}
              className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none"
            />
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
                selectedInvoiceId === invoice.invoiceId
                  ? "bg-primary/5"
                  : "hover:bg-muted/60"
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-foreground">
                  {invoice.studentName}
                </p>
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
                  <span
                    className={`ml-1 mt-1 inline-flex rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${
                      invoice.enforcementState === "held"
                        ? "bg-destructive/10 text-destructive"
                        : invoice.enforcementState === "countdown"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-primary/10 text-primary"
                    }`}
                  >
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
