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
  hasNextPage = false,
  loadingMore = false,
  onSelect,
  onLoadMore = () => undefined,
}: {
  loading: boolean;
  invoices: AdmissionInvoiceQueueItem[];
  total: number;
  selectedInvoiceId: number | null;
  hasNextPage?: boolean;
  loadingMore?: boolean;
  onSelect: (invoiceId: number) => void;
  onLoadMore?: () => void;
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
        <>
        <div className="divide-y divide-border xl:hidden">
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
        <div className="hidden overflow-x-auto xl:block">
          <table className="w-full min-w-[76rem] border-collapse text-left text-xs">
            <thead className="bg-muted/60 text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
              <tr>
                {[
                  "Invoice", "Student / Parent", "Billing period", "Total",
                  "Paid", "Balance", "Due date", "Status", "Access",
                ].map((heading) => (
                  <th key={heading} scope="col" className="px-3 py-3">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {invoices.map((invoice) => (
                <tr
                  key={invoice.invoiceId}
                  className={selectedInvoiceId === invoice.invoiceId
                    ? "bg-primary/5"
                    : "hover:bg-muted/40"}
                >
                  <td className="p-0">
                    <button
                      type="button"
                      onClick={() => onSelect(invoice.invoiceId)}
                      className="min-h-14 w-full px-3 py-3 text-left font-mono font-black focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40"
                    >
                      {invoice.invoiceNumber}
                    </button>
                  </td>
                  <td className="px-3 py-3 font-black">
                    {invoice.studentName}
                    <span className="block font-semibold text-muted-foreground">
                      {invoice.parentName || "No parent"}
                    </span>
                  </td>
                  <td className="px-3 py-3">{formatDate(invoice.billingPeriod)}</td>
                  <td className="px-3 py-3 font-black">{money(invoice.totalMinor / 100, invoice.currency)}</td>
                  <td className="px-3 py-3">{money(invoice.paidMinor / 100, invoice.currency)}</td>
                  <td className="px-3 py-3 font-black">{money(invoice.balanceMinor / 100, invoice.currency)}</td>
                  <td className="px-3 py-3">{formatDate(invoice.dueDate)}</td>
                  <td className="px-3 py-3 font-black uppercase">{invoice.status.replace(/_/g, " ")}</td>
                  <td className="px-3 py-3 font-black uppercase">
                    {invoice.enforcementState === "held"
                      ? "Payment-only"
                      : invoice.enforcementState?.replace(/_/g, " ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {hasNextPage ? (
          <div className="border-t border-border p-3">
            <button
              type="button"
              onClick={onLoadMore}
              disabled={loadingMore}
              className="min-h-11 w-full rounded-lg border border-border px-3 text-sm font-black hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50"
            >
              {loadingMore ? "Loading…" : "Load more invoices"}
            </button>
          </div>
        ) : null}
        </>
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
