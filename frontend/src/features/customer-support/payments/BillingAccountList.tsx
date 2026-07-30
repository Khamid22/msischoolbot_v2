import { CalendarClock, ChevronRight } from "lucide-react";
import type { BillingAccountSummary } from "@/features/customer-support/model";
import { formatDate, money } from "@/features/customer-support/shared/ui";

function accountKey(account: BillingAccountSummary) {
  return `${account.accountType}:${account.accountId}`;
}

function balanceLabel(account: BillingAccountSummary) {
  if (!account.outstandingBalances.length) return "—";
  return account.outstandingBalances
    .map((balance) => money(balance.balanceMinor / 100, balance.currency))
    .join(" · ");
}

function attentionLabel(account: BillingAccountSummary) {
  if (account.attentionFlags.includes("payment_only")) return "Payment-only";
  if (account.attentionFlags.includes("overdue")) return "Overdue";
  if (account.attentionFlags.includes("due_without_invoice")) return "Invoice due";
  if (account.attentionFlags.includes("missing_schedule")) return "Schedule missing";
  if (account.attentionFlags.includes("enforcement_missing")) return "Timer missing";
  return "No exception";
}

function BillingAccountCard({
  account,
  isSelected,
  onSelect,
}: {
  account: BillingAccountSummary;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`grid min-h-28 w-full grid-cols-[1fr_auto] gap-3 px-4 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none ${
        isSelected ? "bg-primary/5" : "hover:bg-muted/60"
      }`}
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-black text-foreground">
          {account.studentName}
        </span>
        <span className="block truncate text-xs font-semibold text-muted-foreground">
          {[account.parentName, account.schoolName].filter(Boolean).join(" · ")}
        </span>
        <span className="mt-2 block text-xs font-bold text-foreground">
          {account.scheduleStatus === "missing"
            ? "No billing schedule"
            : `Day ${account.billingDay} · ${money(
              account.monthlyAmountMinor / 100,
              account.currency,
            )}/month`}
        </span>
        <span className="mt-1 block text-xs font-semibold text-muted-foreground">
          Outstanding {balanceLabel(account)}
        </span>
      </span>
      <span className="flex flex-col items-end gap-2">
        <span className={`rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${
          account.attentionFlags.length
            ? "bg-amber-100 text-amber-900"
            : "bg-emerald-100 text-emerald-800"
        }`}>
          {attentionLabel(account)}
        </span>
        <ChevronRight className="mt-auto h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </span>
    </button>
  );
}

export function BillingAccountList({
  loading,
  accounts,
  total,
  selectedKey,
  hasNextPage,
  loadingMore,
  onSelect,
  onLoadMore,
}: {
  loading: boolean;
  accounts: BillingAccountSummary[];
  total: number;
  selectedKey: string | null;
  hasNextPage: boolean;
  loadingMore: boolean;
  onSelect: (account: BillingAccountSummary) => void;
  onLoadMore: () => void;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <header className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-black text-foreground">Billing accounts</h2>
        <p className="text-xs font-semibold text-muted-foreground">{total} accounts</p>
      </header>
      {loading ? (
        <div className="space-y-2 p-4" role="status" aria-label="Loading billing accounts">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
          ))}
        </div>
      ) : (
        <>
          <div className="divide-y divide-border xl:hidden">
            {accounts.map((account) => (
              <BillingAccountCard
                key={accountKey(account)}
                account={account}
                isSelected={selectedKey === accountKey(account)}
                onSelect={() => onSelect(account)}
              />
            ))}
          </div>
          <div className="hidden overflow-x-auto xl:block">
            <table className="w-full min-w-[74rem] border-collapse text-left text-xs">
              <thead className="bg-muted/60 text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
                <tr>
                  {[
                    "Student",
                    "Parent / School",
                    "Billing schedule",
                    "Monthly charge",
                    "Latest invoice",
                    "Outstanding",
                    "Access / Attention",
                  ].map((heading) => (
                    <th key={heading} scope="col" className="px-3 py-3">{heading}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {accounts.map((account) => {
                  const key = accountKey(account);
                  return (
                    <tr
                      key={key}
                      className={selectedKey === key ? "bg-primary/5" : "hover:bg-muted/40"}
                    >
                      <td className="p-0">
                        <button
                          type="button"
                          onClick={() => onSelect(account)}
                          className="min-h-14 w-full px-3 py-3 text-left font-black text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40"
                        >
                          {account.studentName}
                          <span className="block font-mono text-[0.625rem] text-muted-foreground">
                            {account.studentCode || account.accountType}
                          </span>
                        </button>
                      </td>
                      <td className="px-3 py-3 font-semibold text-muted-foreground">
                        {account.parentName || "No linked parent"}
                        <span className="block">{account.schoolName}</span>
                      </td>
                      <td className="px-3 py-3 font-bold">
                        {account.scheduleStatus === "missing"
                          ? "Missing"
                          : `Day ${account.billingDay} · ${account.scheduleStatus}`}
                        {account.effectiveDate ? (
                          <span className="block font-semibold text-muted-foreground">
                            From {formatDate(account.effectiveDate)}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-3 font-black">
                        {money(account.monthlyAmountMinor / 100, account.currency)}
                      </td>
                      <td className="px-3 py-3 font-semibold">
                        {account.latestInvoice?.invoiceNumber || "No invoice"}
                        {account.latestInvoice ? (
                          <span className="block text-muted-foreground">
                            {account.latestInvoice.status.replace(/_/g, " ")}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-3 font-black">{balanceLabel(account)}</td>
                      <td className="px-3 py-3">
                        <span className={`rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${
                          account.attentionFlags.length
                            ? "bg-amber-100 text-amber-900"
                            : "bg-emerald-100 text-emerald-800"
                        }`}>
                          {attentionLabel(account)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
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
                {loadingMore ? "Loading…" : "Load more accounts"}
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

export function BillingAccountEmptyGraphic() {
  return <CalendarClock className="h-5 w-5" />;
}
