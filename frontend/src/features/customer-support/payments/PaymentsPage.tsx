import { useQuery } from "@tanstack/react-query";
import { CreditCard, Search } from "lucide-react";
import { useState } from "react";
import { getSupport } from "@/features/customer-support/api";
import type { AdmissionInvoiceQueue } from "@/features/customer-support/model";
import { formatDate, inputClass, money } from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";

export function PaymentsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const query = useQuery({
    queryKey: ["customer-support", "payments", search, status],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ q: search, status, limit: "100" });
      return getSupport<AdmissionInvoiceQueue>(`/payments/invoices?${params}`, signal);
    },
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Payments"
        subtitle="Review first and recurring invoices without mixing currencies or rewriting paid records."
        badge={<span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase text-primary">Invoice ledger</span>}
      />
      <div className="grid gap-3 rounded-xl border border-border bg-card p-3 shadow-sm md:grid-cols-[1fr_13rem]">
        <label className="relative">
          <span className="sr-only">Search invoices</span>
          <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
          <input className={`${inputClass} pl-10`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Invoice, student, parent, or phone" />
        </label>
        <select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Invoice status">
          <option value="all">All statuses</option>
          {["issued", "partially_paid", "overdue", "paid", "voided"].map((value) => <option key={value} value={value}>{value.replace(/_/g, " ")}</option>)}
        </select>
      </div>
      {query.isError ? (
        <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm font-bold text-destructive">
          {query.error instanceof Error ? query.error.message : "Invoices could not be loaded."}
        </p>
      ) : null}
      <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="text-sm font-black text-foreground">Invoices</h2>
            <p className="text-xs font-semibold text-muted-foreground">{query.data?.total || 0} records</p>
          </div>
        </header>
        {query.isLoading ? (
          <div className="space-y-2 p-4" role="status">{[1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />)}</div>
        ) : query.data?.items.length ? (
          <div className="divide-y divide-border">
            {query.data.items.map((invoice) => (
              <a
                key={invoice.invoiceId}
                href={`/customer-support/admissions?admissionId=${invoice.admissionId}`}
                className="grid min-h-20 gap-2 px-4 py-3 transition-colors hover:bg-muted/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none md:grid-cols-[1.1fr_1fr_auto_auto]"
              >
                <div>
                  <p className="text-sm font-black text-foreground">{invoice.studentFullName}</p>
                  <p className="text-xs font-semibold text-muted-foreground">{invoice.parentFullName} · {invoice.schoolName}</p>
                </div>
                <div>
                  <p className="font-mono text-xs font-black text-foreground">{invoice.invoiceNumber}</p>
                  <p className="text-xs font-semibold text-muted-foreground">Due {formatDate(invoice.dueDate)}</p>
                </div>
                <div className="md:text-right">
                  <p className="text-sm font-black text-foreground">{money(invoice.balanceMinor / 100, invoice.currency)}</p>
                  <p className="text-xs font-semibold text-muted-foreground">balance</p>
                </div>
                <span className="self-center justify-self-start rounded-full bg-muted px-2.5 py-1 text-[0.625rem] font-black uppercase text-muted-foreground md:justify-self-end">
                  {invoice.status.replace(/_/g, " ")}
                </span>
              </a>
            ))}
          </div>
        ) : (
          <div className="p-5">
            <EmptyState title="No invoices found" detail="Invoices appear after an accepted admission contract." icon={<CreditCard className="h-5 w-5" />} />
          </div>
        )}
      </section>
    </div>
  );
}
