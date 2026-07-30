import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { getSupport, sendSupport } from "@/features/customer-support/api";
import type {
  AdmissionInvoiceQueue,
  BillingAccountDetail,
  BillingAccountPage,
  BillingAccountSummary,
  BillingAutomationStatus,
  BillingCycle,
  BillingCycleInvoiceCandidate,
  BillingCycleReadiness,
  BillingCycleReview,
  BillingProfile,
  SupportContext,
  UnifiedInvoiceDetail,
} from "@/features/customer-support/model";
import { AutomationStatusPanel } from "@/features/customer-support/payments/AutomationStatusPanel";
import { BillingAccountDetailPanel } from "@/features/customer-support/payments/BillingAccountDetailPanel";
import { BillingAccountList } from "@/features/customer-support/payments/BillingAccountList";
import { CycleReadinessPanel } from "@/features/customer-support/payments/CycleReadinessPanel";
import { InvoiceDetailPanel } from "@/features/customer-support/payments/InvoiceDetailPanel";
import { InvoiceList } from "@/features/customer-support/payments/InvoiceList";
import {
  type AccountFilters,
  type InvoiceFilters,
  PaymentFilters,
  type PaymentView,
} from "@/features/customer-support/payments/PaymentFilters";
import {
  DEFAULT_ACCOUNT_FILTERS,
  DEFAULT_INVOICE_FILTERS,
  billingAccountKey,
  readPaymentLocation,
} from "@/features/customer-support/payments/paymentLocation";
import {
  PaymentCollectionFallback,
  PaymentViewButton,
} from "@/features/customer-support/payments/PaymentWorkspaceChrome";
import {
  MasterDetailLayout,
  resolveMasterDetailCollectionState,
} from "@/features/customer-support/shared/MasterDetailLayout";
import { secondaryButton } from "@/features/customer-support/shared/ui";
import { PageHeader } from "@/shared/ui/PageHeader";

const PAYMENT_PAGE_SIZE = 25;

export function PaymentsPage({ csrfToken }: { csrfToken: string }) {
  const initial = readPaymentLocation();
  const queryClient = useQueryClient();
  const [view, setView] = useState<PaymentView>(initial.view);
  const [searchInput, setSearchInput] = useState(initial.search);
  const [search, setSearch] = useState(initial.search);
  const [accountFilters, setAccountFilters] = useState(initial.accountFilters);
  const [invoiceFilters, setInvoiceFilters] = useState(initial.invoiceFilters);
  const [selectedAccountType, setSelectedAccountType] = useState(initial.selectedAccountType);
  const [selectedAccountId, setSelectedAccountId] = useState(initial.selectedAccountId);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(initial.selectedInvoiceId);

  const context = useQuery({
    queryKey: ["customer-support", "context"],
    queryFn: ({ signal }) => getSupport<SupportContext>("/context", signal),
  });
  const accountsQuery = useInfiniteQuery({
    queryKey: ["customer-support", "payments", "accounts", search, accountFilters],
    initialPageParam: "",
    enabled: view === "accounts",
    queryFn: ({ signal, pageParam }) => {
      const params = new URLSearchParams({
        limit: String(PAYMENT_PAGE_SIZE),
        accountType: accountFilters.accountType,
        scheduleStatus: accountFilters.scheduleStatus,
        attention: accountFilters.attention,
        access: accountFilters.access,
      });
      if (search) params.set("q", search);
      if (accountFilters.schoolId) params.set("schoolId", accountFilters.schoolId);
      if (pageParam) params.set("cursor", pageParam);
      return getSupport<BillingAccountPage>(`/payments/billing-accounts?${params}`, signal);
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor || undefined,
  });
  const invoicesQuery = useInfiniteQuery({
    queryKey: ["customer-support", "payments", "invoices", search, invoiceFilters],
    initialPageParam: "",
    enabled: view === "invoices",
    queryFn: ({ signal, pageParam }) => {
      const params = new URLSearchParams({
        limit: String(PAYMENT_PAGE_SIZE),
        status: invoiceFilters.status,
        origin: invoiceFilters.origin,
        enforcement: invoiceFilters.access,
      });
      if (search) params.set("q", search);
      if (invoiceFilters.schoolId) params.set("schoolId", invoiceFilters.schoolId);
      if (invoiceFilters.billingPeriod) {
        params.set("billingPeriod", `${invoiceFilters.billingPeriod}-01`);
      }
      if (pageParam) params.set("cursor", pageParam);
      return getSupport<AdmissionInvoiceQueue>(`/payments/invoices?${params}`, signal);
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor || undefined,
  });
  const accountDetail = useQuery({
    queryKey: [
      "customer-support",
      "billing-account",
      selectedAccountType,
      selectedAccountId,
    ],
    queryFn: ({ signal }) => getSupport<BillingAccountDetail>(
      `/payments/billing-accounts/${selectedAccountType}/${selectedAccountId}`,
      signal,
    ),
    enabled: view === "accounts"
      && selectedAccountType !== null
      && selectedAccountId !== null,
  });
  const invoiceDetail = useQuery({
    queryKey: ["customer-support", "invoice", selectedInvoiceId],
    queryFn: ({ signal }) => getSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${selectedInvoiceId}`,
      signal,
    ),
    enabled: view === "invoices" && selectedInvoiceId !== null,
  });
  const automationQuery = useQuery({
    queryKey: ["customer-support", "payments", "automation-status"],
    queryFn: ({ signal }) => getSupport<BillingAutomationStatus>(
      "/payments/automation-status",
      signal,
    ),
    refetchInterval: 60_000,
  });
  const readinessQuery = useQuery({
    queryKey: ["customer-support", "payments", "billing-cycle-readiness"],
    queryFn: ({ signal }) => getSupport<BillingCycleReadiness>(
      "/payments/billing-cycles/readiness",
      signal,
    ),
    refetchInterval: 60_000,
  });

  const invoiceMutation = useMutation({
    mutationFn: (operation: () => Promise<UnifiedInvoiceDetail>) => operation(),
    onSuccess: (invoice) => {
      queryClient.setQueryData(
        ["customer-support", "invoice", invoice.invoiceId],
        invoice,
      );
      void invalidatePayments(queryClient);
    },
  });
  const scheduleMutation = useMutation({
    mutationFn: ({
      studentId,
      body,
    }: {
      studentId: number;
      body: object;
    }) => sendSupport<BillingProfile>(
      `/payments/students/${studentId}/billing-profile`,
      "PUT",
      body,
      csrfToken,
    ),
    onSuccess: () => {
      void invalidatePayments(queryClient);
      void accountDetail.refetch();
    },
  });
  const cycleMutation = useMutation({
    mutationFn: (operation: () => Promise<BillingCycle>) => operation(),
    onSuccess: () => {
      void invalidatePayments(queryClient);
      void readinessQuery.refetch();
      void accountDetail.refetch();
    },
  });

  const accounts = accountsQuery.data?.pages.flatMap((page) => page.items) || [];
  const invoices = invoicesQuery.data?.pages.flatMap((page) => page.items) || [];
  const accountCollectionState = resolveMasterDetailCollectionState({
    isLoading: accountsQuery.isLoading,
    isError: accountsQuery.isError,
    itemCount: accounts.length,
  });
  const invoiceCollectionState = resolveMasterDetailCollectionState({
    isLoading: invoicesQuery.isLoading,
    isError: invoicesQuery.isError,
    itemCount: invoices.length,
  });

  useEffect(() => {
    const onPopState = () => {
      const location = readPaymentLocation();
      setView(location.view);
      setSearch(location.search);
      setSearchInput(location.search);
      setAccountFilters(location.accountFilters);
      setInvoiceFilters(location.invoiceFilters);
      setSelectedAccountType(location.selectedAccountType);
      setSelectedAccountId(location.selectedAccountId);
      setSelectedInvoiceId(location.selectedInvoiceId);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("view", view);
    if (search) params.set("q", search);
    const filters = view === "accounts" ? accountFilters : invoiceFilters;
    if (filters.schoolId) params.set("schoolId", filters.schoolId);
    if (view === "accounts") {
      if (accountFilters.accountType !== "all") params.set("type", accountFilters.accountType);
      if (accountFilters.scheduleStatus !== "all") params.set("scheduleStatus", accountFilters.scheduleStatus);
      if (accountFilters.attention !== "all") params.set("attention", accountFilters.attention);
      if (accountFilters.access !== "all") params.set("access", accountFilters.access);
      if (selectedAccountType && selectedAccountId) {
        params.set("accountType", selectedAccountType);
        params.set("accountId", String(selectedAccountId));
      }
    } else {
      if (invoiceFilters.status !== "all") params.set("status", invoiceFilters.status);
      if (invoiceFilters.origin !== "all") params.set("origin", invoiceFilters.origin);
      if (invoiceFilters.billingPeriod) params.set("billingPeriod", invoiceFilters.billingPeriod);
      if (invoiceFilters.access !== "all") params.set("access", invoiceFilters.access);
      if (selectedInvoiceId) params.set("invoiceId", String(selectedInvoiceId));
    }
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}?${params}`,
    );
  }, [
    accountFilters,
    invoiceFilters,
    search,
    selectedAccountId,
    selectedAccountType,
    selectedInvoiceId,
    view,
  ]);

  function switchView(nextView: PaymentView) {
    setView(nextView);
    setSearch("");
    setSearchInput("");
    if (nextView === "accounts") setSelectedInvoiceId(null);
    else {
      setSelectedAccountType(null);
      setSelectedAccountId(null);
    }
  }

  function selectAccount(account: BillingAccountSummary) {
    setSelectedAccountType(account.accountType);
    setSelectedAccountId(account.accountId);
    window.history.pushState(
      { ...window.history.state, billingAccountDetail: true },
      "",
      window.location.href,
    );
  }

  function selectInvoice(invoiceId: number) {
    setSelectedInvoiceId(invoiceId);
    window.history.pushState(
      { ...window.history.state, invoiceDetail: true },
      "",
      window.location.href,
    );
  }

  function closeDetail() {
    const stateKey = view === "accounts" ? "billingAccountDetail" : "invoiceDetail";
    if (window.history.state?.[stateKey]) {
      window.history.back();
      return;
    }
    if (view === "accounts") {
      setSelectedAccountType(null);
      setSelectedAccountId(null);
    } else {
      setSelectedInvoiceId(null);
    }
  }

  function openAccountInvoice(invoiceId: number) {
    setView("invoices");
    setSelectedAccountType(null);
    setSelectedAccountId(null);
    setSelectedInvoiceId(invoiceId);
  }

  function openBillingAccount(studentId: number) {
    setView("accounts");
    setSelectedInvoiceId(null);
    setSelectedAccountType("student");
    setSelectedAccountId(studentId);
  }

  function saveSchedule(
    event: FormEvent<HTMLFormElement>,
    account: BillingAccountDetail,
  ) {
    event.preventDefault();
    if (!account.studentId) return;
    const data = new FormData(event.currentTarget);
    const items = account.enrollmentOptions
      .filter((option) => data.get(`enabled-${option.groupId}`) === "on")
      .map((option) => ({
        groupId: option.groupId,
        amount: Number(data.get(`amount-${option.groupId}`)),
        description: String(
          data.get(`description-${option.groupId}`) || option.subjectName,
        ).trim(),
      }));
    scheduleMutation.mutate({
      studentId: account.studentId,
      body: {
        billingDay: Number(data.get("billingDay")),
        startsOn: String(data.get("startsOn") || ""),
        status: String(data.get("status") || "active"),
        expectedVersion: account.scheduleVersion,
        items,
      },
    });
  }

  function recordPayment(
    event: FormEvent<HTMLFormElement>,
    invoice: UnifiedInvoiceDetail,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    invoiceMutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
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
    invoiceMutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
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
    invoiceMutation.mutate(() => sendSupport<UnifiedInvoiceDetail>(
      `/payments/invoices/${invoice.invoiceId}/void`,
      "POST",
      {
        expectedVersion: invoice.version,
        reason: String(data.get("reason") || "").trim(),
      },
      csrfToken,
    ));
  }

  function reviewCycleInvoice(
    event: FormEvent<HTMLFormElement>,
    cycle: BillingCycle,
    candidate: BillingCycleInvoiceCandidate,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const decision = submitter?.value === "exclude" ? "exclude" : "apply";
    cycleMutation.mutate(() => sendSupport<BillingCycle>(
      `/payments/billing-cycles/${cycle.cycleId}/invoice-review`,
      "POST",
      {
        invoiceId: candidate.invoiceId,
        decision,
        amount: decision === "apply" ? Number(data.get("amount")) : 0,
        reason: String(data.get("reason") || "").trim(),
        expectedCycleVersion: cycle.version,
      },
      csrfToken,
    ));
  }

  function reverseCycleReview(
    event: FormEvent<HTMLFormElement>,
    review: BillingCycleReview,
  ) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    cycleMutation.mutate(() => sendSupport<BillingCycle>(
      `/payments/billing-cycle-reviews/${review.reviewId}/reversal`,
      "POST",
      {
        expectedVersion: review.version,
        reason: String(data.get("reason") || "").trim(),
      },
      csrfToken,
    ));
  }

  const collectionState = view === "accounts"
    ? accountCollectionState
    : invoiceCollectionState;
  const isDetailOpen = view === "accounts"
    ? selectedAccountId !== null
    : selectedInvoiceId !== null;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Payments"
        subtitle="Manage billing schedules, invoices, settlements, and payment access."
        badge={(
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase text-primary">
            Billing operations
          </span>
        )}
      />
      <div className="inline-flex rounded-lg border border-border bg-card p-1 shadow-sm" role="tablist" aria-label="Payment view">
        <PaymentViewButton active={view === "accounts"} onClick={() => switchView("accounts")}>
          Billing Accounts
        </PaymentViewButton>
        <PaymentViewButton active={view === "invoices"} onClick={() => switchView("invoices")}>
          Invoices
        </PaymentViewButton>
      </div>
      <PaymentFilters
        view={view}
        searchInput={searchInput}
        schools={context.data?.schools || []}
        accountFilters={accountFilters}
        invoiceFilters={invoiceFilters}
        onSearchInputChange={setSearchInput}
        onSearch={() => {
          setSearch(searchInput.trim());
          setSelectedAccountType(null);
          setSelectedAccountId(null);
          setSelectedInvoiceId(null);
        }}
        onAccountFiltersChange={(filters) => {
          setAccountFilters(filters);
          setSelectedAccountType(null);
          setSelectedAccountId(null);
        }}
        onInvoiceFiltersChange={(filters) => {
          setInvoiceFilters(filters);
          setSelectedInvoiceId(null);
        }}
      />
      <AutomationStatusPanel
        status={automationQuery.data}
        loading={automationQuery.isLoading}
        error={automationQuery.error}
        onRetry={() => void automationQuery.refetch()}
      />
      <CycleReadinessPanel
        readiness={readinessQuery.data}
        loading={readinessQuery.isLoading}
        error={readinessQuery.error}
        onRetry={() => void readinessQuery.refetch()}
        onOpenAccount={openBillingAccount}
      />
      <MasterDetailLayout
        collectionState={collectionState}
        isDetailOpen={isDetailOpen}
        desktopColumnsClassName="lg:grid-cols-[minmax(0,1.08fr)_minmax(28rem,0.92fr)]"
        fallback={<PaymentCollectionFallback
          view={view}
          state={collectionState}
          error={view === "accounts" ? accountsQuery.error : invoicesQuery.error}
          retry={() => {
            if (view === "accounts") void accountsQuery.refetch();
            else void invoicesQuery.refetch();
          }}
          reset={() => {
            setSearch("");
            setSearchInput("");
            if (view === "accounts") setAccountFilters(DEFAULT_ACCOUNT_FILTERS);
            else setInvoiceFilters(DEFAULT_INVOICE_FILTERS);
          }}
        />}
        collection={view === "accounts" ? (
          <BillingAccountList
            loading={accountsQuery.isLoading}
            accounts={accounts}
            total={accountsQuery.data?.pages[0]?.total || 0}
            selectedKey={billingAccountKey(selectedAccountType, selectedAccountId)}
            hasNextPage={Boolean(accountsQuery.hasNextPage)}
            loadingMore={accountsQuery.isFetchingNextPage}
            onSelect={selectAccount}
            onLoadMore={() => void accountsQuery.fetchNextPage()}
          />
        ) : (
          <InvoiceList
            loading={invoicesQuery.isLoading}
            invoices={invoices}
            total={invoicesQuery.data?.pages[0]?.total || 0}
            selectedInvoiceId={selectedInvoiceId}
            hasNextPage={Boolean(invoicesQuery.hasNextPage)}
            loadingMore={invoicesQuery.isFetchingNextPage}
            onSelect={selectInvoice}
            onLoadMore={() => void invoicesQuery.fetchNextPage()}
          />
        )}
        detail={(
          <div className="min-w-0">
            {isDetailOpen ? (
              <button type="button" onClick={closeDetail} className={`${secondaryButton} mb-3 lg:hidden`}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Back to {view === "accounts" ? "accounts" : "invoices"}
              </button>
            ) : null}
            {view === "accounts" ? (
              <BillingAccountDetailPanel
                account={accountDetail.data}
                loading={accountDetail.isLoading}
                error={accountDetail.error}
                saving={scheduleMutation.isPending || cycleMutation.isPending}
                mutationError={scheduleMutation.error || cycleMutation.error}
                onClose={closeDetail}
                onRetry={() => void accountDetail.refetch()}
                onSaveSchedule={saveSchedule}
                onOpenInvoice={openAccountInvoice}
                onReviewInvoice={reviewCycleInvoice}
                onReverseReview={reverseCycleReview}
              />
            ) : (
              <InvoiceDetailPanel
                invoice={invoiceDetail.data}
                loading={invoiceDetail.isLoading}
                error={invoiceDetail.error}
                saving={invoiceMutation.isPending}
                mutationError={invoiceMutation.error}
                onClose={closeDetail}
                onRetry={() => void invoiceDetail.refetch()}
                onRecordPayment={recordPayment}
                onReversePayment={reversePayment}
                onVoidInvoice={voidInvoice}
              />
            )}
          </div>
        )}
      />
    </div>
  );
}

async function invalidatePayments(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["customer-support", "payments"] }),
    queryClient.invalidateQueries({ queryKey: ["customer-support", "billing-account"] }),
    queryClient.invalidateQueries({ queryKey: ["customer-support", "dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["customer-support", "student"] }),
  ]);
}
