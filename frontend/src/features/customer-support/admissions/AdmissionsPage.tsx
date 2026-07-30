import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ClipboardCheck, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { getSupport, sendSupport, sendSupportForm } from "@/features/customer-support/api";
import { AdmissionDetailPanel } from "@/features/customer-support/admissions/AdmissionDetailPanel";
import { AdmissionWizard, type CreateAdmissionValues } from "@/features/customer-support/admissions/AdmissionWizard";
import type { AdmissionCreated, AdmissionDetail, AdmissionGroupOption, AdmissionPage } from "@/features/customer-support/model";
import {
  MasterDetailLayout,
  resolveMasterDetailCollectionState,
} from "@/features/customer-support/shared/MasterDetailLayout";
import {
  formatDate,
  inputClass,
  primaryButton,
  secondaryButton,
} from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";

export function AdmissionsPage({
  csrfToken,
}: {
  authLogin: string;
  title: string;
  description: string;
  csrfToken: string;
}) {
  const queryClient = useQueryClient();
  const initialAdmissionId = Number(new URLSearchParams(window.location.search).get("admissionId") || 0);
  const [selectedId, setSelectedId] = useState(initialAdmissionId);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [showWizard, setShowWizard] = useState(false);
  const [publicUrl, setPublicUrl] = useState("");
  const [error, setError] = useState("");

  const listQuery = useQuery({
    queryKey: ["customer-support", "admissions", search, status],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ q: search, status, limit: "100" });
      return getSupport<AdmissionPage>(`/admissions?${params}`, signal);
    },
  });
  const groupsQuery = useQuery({
    queryKey: ["customer-support", "admission-groups"],
    queryFn: ({ signal }) => getSupport<AdmissionGroupOption[]>("/admissions/groups", signal),
  });
  const detailQuery = useQuery({
    queryKey: ["customer-support", "admission", selectedId],
    queryFn: ({ signal }) => getSupport<AdmissionDetail>(`/admissions/${selectedId}`, signal),
    enabled: selectedId > 0,
  });

  useEffect(() => {
    const onPopState = () => {
      const admissionId = Number(
        new URLSearchParams(window.location.search).get("admissionId") || 0,
      );
      setSelectedId(admissionId);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function selectAdmission(admissionId: number, push = true) {
    setSelectedId(admissionId);
    const params = new URLSearchParams(window.location.search);
    if (admissionId) params.set("admissionId", String(admissionId));
    else params.delete("admissionId");
    window.history[push ? "pushState" : "replaceState"](
      push ? { ...window.history.state, admissionDetail: true } : window.history.state,
      "",
      `${window.location.pathname}${params.size ? `?${params}` : ""}`,
    );
  }

  function closeAdmission() {
    if (window.history.state?.admissionDetail) {
      window.history.back();
      return;
    }
    selectAdmission(0, false);
  }

  const refresh = async (admission?: AdmissionDetail) => {
    if (admission) queryClient.setQueryData(["customer-support", "admission", admission.admissionId], admission);
    await queryClient.invalidateQueries({ queryKey: ["customer-support", "admissions"] });
    await queryClient.invalidateQueries({ queryKey: ["customer-support", "payments"] });
  };
  const mutation = useMutation({
    mutationFn: async (operation: () => Promise<AdmissionDetail | AdmissionCreated | { admission: AdmissionDetail; publicUrl: string }>) => operation(),
    onSuccess: async (result) => {
      setError("");
      const admission = "admissionId" in result ? result : result.admission;
      if ("publicUrl" in result) setPublicUrl(result.publicUrl);
      selectAdmission(admission.admissionId, false);
      setShowWizard(false);
      await refresh(admission);
    },
    onError: (failure) => setError(failure instanceof Error ? failure.message : "The admission could not be updated."),
  });

  function create(values: CreateAdmissionValues) {
    mutation.mutate(() => sendSupport<AdmissionCreated>("/admissions", "POST", values, csrfToken));
  }

  const admission = detailQuery.data;
  const admissions = listQuery.data?.items || [];
  const collectionState = resolveMasterDetailCollectionState({
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    itemCount: admissions.length,
  });
  return (
    <div className="space-y-4">
      <PageHeader
        title="Admissions"
        subtitle="Prepare the contract and first invoice before creating active academic users."
        badge={<span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase text-primary">Customer Support</span>}
        actions={(
          <button type="button" className={primaryButton} onClick={() => setShowWizard(true)}>
            <Plus className="h-4 w-4" /> New admission
          </button>
        )}
      />
      <div className="grid gap-3 rounded-xl border border-border bg-card p-3 shadow-sm md:grid-cols-[1fr_13rem]">
        <label className="relative">
          <span className="sr-only">Search admissions</span>
          <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
          <input className={`${inputClass} pl-10`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Student, parent, or phone" />
        </label>
        <select className={inputClass} value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Admission status">
          <option value="all">All statuses</option>
          {["draft", "contract_sent", "contract_submitted", "awaiting_payment", "active", "payment_review", "cancelled"].map((value) => (
            <option key={value} value={value}>{value.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>
      {error ? <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">{error}</p> : null}
      <MasterDetailLayout
        collectionState={collectionState}
        isDetailOpen={selectedId > 0}
        desktopColumnsClassName="lg:grid-cols-[minmax(18rem,0.65fr)_minmax(0,1.5fr)]"
        fallback={collectionState === "loading" ? (
          <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <header className="border-b border-border px-4 py-3">
              <h2 className="text-sm font-black text-foreground">Admission queue</h2>
              <p className="text-xs font-semibold text-muted-foreground">Loading…</p>
            </header>
            <div className="space-y-2 p-3" role="status">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
              ))}
            </div>
          </section>
        ) : (
          <EmptyState
            title={collectionState === "error"
              ? "Admissions could not be loaded"
              : "No admissions found"}
            detail={collectionState === "error"
              ? (listQuery.error instanceof Error ? listQuery.error.message : "Try again.")
              : "Create a prospective admission or reset the filters."}
            icon={<ClipboardCheck className="h-5 w-5" />}
            action={(
              <button
                type="button"
                className={collectionState === "error" ? secondaryButton : primaryButton}
                onClick={() => {
                  if (collectionState === "error") {
                    void listQuery.refetch();
                    return;
                  }
                  if (search || status !== "all") {
                    setSearch("");
                    setStatus("all");
                    return;
                  }
                  setShowWizard(true);
                }}
              >
                {collectionState === "error"
                  ? "Try again"
                  : search || status !== "all"
                    ? "Reset filters"
                    : "New admission"}
              </button>
            )}
          />
        )}
        collection={(
        <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <header className="border-b border-border px-4 py-3">
            <h2 className="text-sm font-black text-foreground">Admission queue</h2>
            <p className="text-xs font-semibold text-muted-foreground">{listQuery.data?.total || 0} records</p>
          </header>
          <div className="max-h-[70vh] overflow-y-auto">
            {listQuery.isLoading ? (
              <div className="space-y-2 p-3" role="status">{[1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />)}</div>
            ) : admissions.length ? admissions.map((item) => (
              <button
                key={item.admissionId}
                type="button"
                onClick={() => selectAdmission(item.admissionId)}
                className={`w-full border-b border-border px-4 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none ${selectedId === item.admissionId ? "bg-primary/8" : "hover:bg-muted/60"}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-black text-foreground">{item.studentFullName}</p>
                    <p className="truncate text-xs font-semibold text-muted-foreground">{item.parentFullName} · {item.schoolName}</p>
                  </div>
                  <span className="rounded-full bg-muted px-2 py-1 text-[0.625rem] font-black uppercase text-muted-foreground">{item.status.replace(/_/g, " ")}</span>
                </div>
                <p className="mt-2 text-xs font-semibold text-muted-foreground">First due {formatDate(item.firstDueDate)}</p>
              </button>
            )) : (
              <div className="p-4"><EmptyState title="No admissions found" detail="Create a prospective admission or change the filters." icon={<ClipboardCheck className="h-5 w-5" />} /></div>
            )}
          </div>
        </section>
        )}
        detail={(
        <section className="min-w-0">
          {selectedId ? (
            <button
              type="button"
              onClick={closeAdmission}
              className={`${secondaryButton} mb-3 lg:hidden`}
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to admissions
            </button>
          ) : null}
          {detailQuery.isLoading ? (
            <div className="h-80 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" role="status" />
          ) : detailQuery.isError ? (
            <EmptyState
              title="Admission could not be loaded"
              detail={detailQuery.error instanceof Error ? detailQuery.error.message : "Try again."}
              icon={<ClipboardCheck className="h-5 w-5" />}
              action={(
                <button type="button" className={secondaryButton} onClick={() => void detailQuery.refetch()}>
                  Try again
                </button>
              )}
            />
          ) : admission ? (
            <AdmissionDetailPanel
              admission={admission}
              publicUrl={publicUrl}
              saving={mutation.isPending}
              onUploadContract={(file) => {
                const data = new FormData();
                data.set("document", file);
                mutation.mutate(() => sendSupportForm<AdmissionDetail>(`/admissions/${admission.admissionId}/contract`, data, csrfToken));
              }}
              onSend={() => mutation.mutate(() => sendSupport<{ admission: AdmissionDetail; publicUrl: string }>(`/admissions/${admission.admissionId}/send`, "POST", {}, csrfToken))}
              onReview={(accepted, reason) => mutation.mutate(() => sendSupport<AdmissionDetail>(`/admissions/${admission.admissionId}/contract/review`, "POST", { accepted, reason }, csrfToken))}
              onManualPayment={(invoiceId, values) => mutation.mutate(() => sendSupport<AdmissionDetail>(`/admissions/invoices/${invoiceId}/manual-payment`, "POST", values, csrfToken))}
              onAddPaidInvoice={(values) => mutation.mutate(() => sendSupport<AdmissionDetail>(`/admissions/${admission.admissionId}/paid-invoice`, "POST", values, csrfToken))}
            />
          ) : (
            <EmptyState title="Select an admission" detail="Open a prospective student to review the contract, invoice, and activation state." icon={<ClipboardCheck className="h-5 w-5" />} />
          )}
        </section>
        )}
      />
      {showWizard ? (
        <AdmissionWizard
          groupOptions={groupsQuery.data || []}
          saving={mutation.isPending}
          onClose={() => setShowWizard(false)}
          onSubmit={create}
        />
      ) : null}
    </div>
  );
}
