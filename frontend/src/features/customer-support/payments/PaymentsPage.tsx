import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CreditCard, Search } from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { getSupport, sendSupport } from "@/features/customer-support/api";
import type {
  AdmissionInvoiceQueue,
  BillingAutomationStatus,
  UnifiedInvoiceDetail,
} from "@/features/customer-support/model";
import { AutomationStatusPanel } from "@/features/customer-support/payments/AutomationStatusPanel";
import { InvoiceDetailPanel } from "@/features/customer-support/payments/InvoiceDetailPanel";
import { InvoiceList } from "@/features/customer-support/payments/InvoiceList";
import {
  MasterDetailLayout,
  resolveMasterDetailCollectionState,
} from "@/features/customer-support/shared/MasterDetailLayout";
import {
  inputClass,
  secondaryButton,
} from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";

function readSelectedInvoiceId(): number | null {
  return Number(
    new URLSearchParams(window.location.search).get("invoiceId") || 0,
  ) || null;
}

export function PaymentsPage({ csrfToken }: { csrfToken: string }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [origin, setOrigin] = useState("all");
  const [enforcement, setEnforcement] = useState("all");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(
    readSelectedInvoiceId,
  );
  const query = useQuery({
    queryKey: ["customer-support", "payments", search, status, origin, enforcement],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({
        q: search,
        status,
        origin,
        enforcement,
        limit: "100",
      });
      return getSupport<AdmissionInvoiceQueue>(`/payments/invoices?${params}`, signal);
    },
  });
  const detailQuery = useQuery({
    queryKey: ["customer-support", "invoice", selectedInvoiceId],
    queryFn: ({ signal }) => getSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${selectedInvoiceId}`,
      signal,
    ),
    enabled: selectedInvoiceId !== null,
  });
  const automationQuery = useQuery({
    queryKey: ["customer-support", "payments", "automation-status"],
    queryFn: ({ signal }) => getSupport<BillingAutomationStatus>(
      "/payments/automation-status",
      signal,
    ),
    refetchInterval: 60_000,
  });
  const mutation = useMutation({
    mutationFn: (operation: () => Promise<UnifiedInvoiceDetail>) => operation(),
    onSuccess: (invoice) => {
      queryClient.setQueryData(
        ["customer-support", "invoice", invoice.invoiceId],
        invoice,
      );
      void queryClient.invalidateQueries({ queryKey: ["customer-support", "payments"] });
      void queryClient.invalidateQueries({ queryKey: ["customer-support", "dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["customer-support", "student"] });
    },
  });
  const invoices = query.data?.items || [];
  const collectionState = resolveMasterDetailCollectionState({
    isLoading: query.isLoading,
    isError: query.isError,
    itemCount: invoices.length,
  });

  useEffect(() => {
    const onPopState = () => setSelectedInvoiceId(readSelectedInvoiceId());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function selectInvoice(invoiceId: number | null, push = true) {
    setSelectedInvoiceId(invoiceId);
    const params = new URLSearchParams(window.location.search);
    if (invoiceId) params.set("invoiceId", String(invoiceId));
    else params.delete("invoiceId");
    window.history[push ? "pushState" : "replaceState"](
      push ? { ...window.history.state, invoiceDetail: true } : window.history.state,
      "",
      `${window.location.pathname}${params.size ? `?${params}` : ""}`,
    );
  }

  function closeInvoice() {
    if (window.history.state?.invoiceDetail) {
      window.history.back();
      return;
    }
    selectInvoice(null, false);
  }

  function recordPayment(
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${invoice.invoiceId}/manual-payments`,
      "POST",
      {
        amount: Number(data.get("amount")),
        method: String(data.get("method") || "cash"),
        paidAt: new Date(String(data.get("paidAt") || "")).toISOString(),
        reference: String(data.get("reference") || "").trim(),
        reason: String(data.get("reason") || "").trim(),
        expectedVersion: invoice.version,
      },
      csrfToken,
    ));
  }

  function reversePayment(
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
    paymentId: number,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoice-payments/${paymentId}/reversal`,
      "POST",
      {
        expectedInvoiceVersion: invoice.version,
        reason: String(data.get("reason") || "").trim(),
      },
      csrfToken,
    ));
  }

  function voidInvoice(
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${invoice.invoiceId}/void`,
      "POST",
      {
        expectedVersion: invoice.version,
        reason: String(data.get("reason") || "").trim(),
      },
      csrfToken,
    ));
  }

  function resetFilters() {
    setSearch("");
    setStatus("all");
    setOrigin("all");
    setEnforcement("all");
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Payments"
        subtitle="One invoice ledger for current students, admissions, manual settlements, and Payme."
        badge={(
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase text-primary">
            Invoice ledger
          </span>
        )}
      />
      <div className="grid gap-3 rounded-xl border border-border bg-card p-3 shadow-sm lg:grid-cols-[1fr_11rem_12rem_12rem]">
        <label className="relative">
          <span className="sr-only">Search invoices</span>
          <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
          <input
            className={`${inputClass} pl-10`}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Invoice, student, parent, or code"
          />
        </label>
        <select
          className={inputClass}
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          aria-label="Invoice status"
        >
          <option value="all">All statuses</option>
          {["issued", "partially_paid", "overdue", "paid", "voided"].map((value) => (
            <option key={value} value={value}>{value.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select
          className={inputClass}
          value={enforcement}
          onChange={(event) => setEnforcement(event.target.value)}
          aria-label="Billing access state"
        >
          <option value="all">All access states</option>
          <option value="countdown">48-hour countdown</option>
          <option value="held">Payment-only</option>
          <option value="cleared">Access restored</option>
          <option value="not_scheduled">Not scheduled</option>
        </select>
        <select
          className={inputClass}
          value={origin}
          onChange={(event) => setOrigin(event.target.value)}
          aria-label="Invoice origin"
        >
          <option value="all">All students</option>
          <option value="student_billing">Current students</option>
          <option value="admission">Admissions</option>
          <option value="legacy_migration">Migrated records</option>
        </select>
      </div>

      <AutomationStatusPanel
        status={automationQuery.data}
        loading={automationQuery.isLoading}
        error={automationQuery.error}
        onRetry={() => void automationQuery.refetch()}
      />

      <MasterDetailLayout
        collectionState={collectionState}
        isDetailOpen={selectedInvoiceId !== null}
        desktopColumnsClassName="lg:grid-cols-[minmax(0,1.05fr)_minmax(28rem,0.95fr)]"
        fallback={collectionState === "loading" ? (
          <InvoiceList
            loading
            invoices={[]}
            total={0}
            selectedInvoiceId={null}
            onSelect={(invoiceId) => selectInvoice(invoiceId)}
          />
        ) : (
          <EmptyState
            title={collectionState === "error"
              ? "Invoices could not be loaded"
              : "No invoices found"}
            detail={collectionState === "error"
              ? (query.error instanceof Error ? query.error.message : "Try again.")
              : "Current-student and admission invoices will appear in this shared ledger."}
            icon={<CreditCard className="h-5 w-5" />}
            action={(
              <button
                type="button"
                className={secondaryButton}
                onClick={() => {
                  if (collectionState === "error") {
                    void query.refetch();
                    return;
                  }
                  resetFilters();
                }}
              >
                {collectionState === "error" ? "Try again" : "Reset filters"}
              </button>
            )}
          />
        )}
        collection={(
          <InvoiceList
            loading={query.isLoading}
            invoices={invoices}
            total={query.data?.total || 0}
            selectedInvoiceId={selectedInvoiceId}
            onSelect={(invoiceId) => selectInvoice(invoiceId)}
          />
        )}
        detail={(
          <div className="min-w-0">
            {selectedInvoiceId ? (
              <button
                type="button"
                onClick={closeInvoice}
                className={`${secondaryButton} mb-3 lg:hidden`}
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Back to invoices
              </button>
            ) : null}
            <InvoiceDetailPanel
              invoice={detailQuery.data}
              loading={detailQuery.isLoading}
              error={detailQuery.error}
              saving={mutation.isPending}
              mutationError={mutation.error}
              onClose={closeInvoice}
              onRetry={() => void detailQuery.refetch()}
              onRecordPayment={recordPayment}
              onReversePayment={reversePayment}
              onVoidInvoice={voidInvoice}
            />
          </div>
        )}
      />
    </div>
  );
}
