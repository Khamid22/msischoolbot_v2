import { Check, ClipboardCopy, Download, FileCheck2, Loader2, Send, Upload, WalletCards, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { AdmissionDetail } from "@/features/customer-support/model";
import { DetailSection, Field, formatDate, inputClass, Label, money, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";

function minorMoney(value: number, currency = "UZS") {
  return money(value / 100, currency);
}

export function AdmissionDetailPanel({
  admission,
  publicUrl,
  saving,
  onUploadContract,
  onSend,
  onReview,
  onManualPayment,
  onAddPaidInvoice,
}: {
  admission: AdmissionDetail;
  publicUrl: string;
  saving: boolean;
  onUploadContract: (file: File) => void;
  onSend: () => void;
  onReview: (accepted: boolean, reason: string) => void;
  onManualPayment: (invoiceId: number, values: {
    amountMinor: number;
    method: string;
    paidAt: string;
    reference: string;
    reason: string;
    expectedVersion: number;
  }) => void;
  onAddPaidInvoice: (values: {
    dueDate: string;
    billingPeriod: string;
    method: string;
    paidAt: string;
    reference: string;
    reason: string;
  }) => void;
}) {
  const [rejectionReason, setRejectionReason] = useState("");
  const firstInvoice = admission.invoices.find((invoice) => invoice.invoiceKind === "first");

  function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = new FormData(event.currentTarget).get("document");
    if (file instanceof File && file.size > 0) onUploadContract(file);
  }

  function recordPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!firstInvoice) return;
    const data = new FormData(event.currentTarget);
    onManualPayment(firstInvoice.invoiceId, {
      amountMinor: Math.round(Number(data.get("amount") || 0) * 100),
      method: String(data.get("method") || "cash"),
      paidAt: new Date(String(data.get("paidAt") || "")).toISOString(),
      reference: String(data.get("reference") || "").trim(),
      reason: String(data.get("reason") || "").trim(),
      expectedVersion: firstInvoice.version,
    });
  }

  function addPaidInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const billingMonth = String(data.get("billingPeriod") || "");
    onAddPaidInvoice({
      dueDate: String(data.get("dueDate") || ""),
      billingPeriod: `${billingMonth}-01`,
      method: String(data.get("method") || "cash"),
      paidAt: new Date(String(data.get("paidAt") || "")).toISOString(),
      reference: String(data.get("reference") || "").trim(),
      reason: String(data.get("reason") || "").trim(),
    });
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-black uppercase tracking-wide text-primary">{admission.schoolName}</p>
            <h2 className="mt-1 text-xl font-black text-foreground">{admission.studentFullName}</h2>
            <p className="mt-1 text-sm font-semibold text-muted-foreground">
              {admission.parentFullName} · {admission.parentPhone}
            </p>
          </div>
          <span className="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-black uppercase tracking-wide text-primary">
            {admission.status.replace(/_/g, " ")}
          </span>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <Field label="First due date" value={formatDate(admission.firstDueDate)} />
          <Field label="Billing day" value={`Day ${admission.billingDay}`} />
          <Field label="Contract" value={admission.contract?.status.replace(/_/g, " ") || "Not uploaded"} />
          <Field label="Activation" value={admission.activatedAt ? formatDate(admission.activatedAt, true) : "Pending"} />
        </div>
        {publicUrl ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg bg-muted p-3">
            <code className="min-w-0 flex-1 break-all text-xs font-bold text-foreground">{publicUrl}</code>
            <button
              type="button"
              className={secondaryButton}
              onClick={() => void navigator.clipboard.writeText(new URL(publicUrl, window.location.origin).href)}
            >
              <ClipboardCopy className="h-4 w-4" />
              Copy secure link
            </button>
          </div>
        ) : null}
      </section>

      <DetailSection title="Contract" icon={<FileCheck2 className="h-4 w-4" />}>
        {admission.contract ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <a className={secondaryButton} href={`/api/v1/customer-support/admissions/${admission.admissionId}/contract/download`}>
                <Download className="h-4 w-4" /> School contract
              </a>
              {admission.contract.signedFileName ? (
                <a className={secondaryButton} href={`/api/v1/customer-support/admissions/${admission.admissionId}/contract/download?signed=true`}>
                  <Download className="h-4 w-4" /> Signed copy
                </a>
              ) : null}
              {admission.contract.status === "draft" ? (
                <button type="button" className={primaryButton} onClick={onSend} disabled={saving}>
                  <Send className="h-4 w-4" /> Send secure link
                </button>
              ) : null}
            </div>
            {admission.contract.status === "submitted" ? (
              <div className="rounded-lg border border-border bg-muted/30 p-3">
                <Label htmlFor="contract-rejection-reason">Reason if rejecting</Label>
                <textarea
                  id="contract-rejection-reason"
                  className={`${inputClass} min-h-24 py-3`}
                  value={rejectionReason}
                  onChange={(event) => setRejectionReason(event.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" className={primaryButton} disabled={saving} onClick={() => onReview(true, "")}>
                    <Check className="h-4 w-4" /> Accept and issue invoice
                  </button>
                  <button
                    type="button"
                    className={secondaryButton}
                    disabled={saving || rejectionReason.trim().length < 2}
                    onClick={() => onReview(false, rejectionReason)}
                  >
                    <X className="h-4 w-4" /> Reject
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <form className="flex flex-wrap items-end gap-3" onSubmit={upload}>
            <div className="min-w-[15rem] flex-1">
              <Label htmlFor="school-contract-file">School contract</Label>
              <input id="school-contract-file" name="document" type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" required className={`${inputClass} file:mr-3 file:border-0 file:bg-transparent file:font-bold`} />
            </div>
            <button type="submit" className={primaryButton} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Upload className="h-4 w-4" />}
              Upload contract
            </button>
          </form>
        )}
      </DetailSection>

      <DetailSection title="Groups and billing" icon={<WalletCards className="h-4 w-4" />}>
        <div className="space-y-2">
          {admission.groups.map((group) => (
            <div key={group.groupId} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border p-3">
              <div>
                <p className="text-sm font-black text-foreground">{group.subjectName}</p>
                <p className="text-xs font-semibold text-muted-foreground">{group.groupName}</p>
              </div>
              <p className="text-sm font-black text-foreground">{minorMoney(group.monthlyAmountMinor)}</p>
            </div>
          ))}
        </div>
      </DetailSection>

      <DetailSection title="First invoice" icon={<WalletCards className="h-4 w-4" />}>
        {firstInvoice ? (
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <Field label="Invoice" value={firstInvoice.invoiceNumber} mono />
              <Field label="Total" value={minorMoney(firstInvoice.totalMinor, firstInvoice.currency)} />
              <Field label="Balance" value={minorMoney(firstInvoice.balanceMinor, firstInvoice.currency)} />
              <Field label="Status" value={firstInvoice.status.replace(/_/g, " ")} />
            </div>
            {firstInvoice.balanceMinor > 0 && admission.status === "awaiting_payment" ? (
              <form className="grid gap-3 rounded-lg border border-border bg-muted/30 p-3 md:grid-cols-2" onSubmit={recordPayment}>
                <div>
                  <Label htmlFor="manual-payment-amount">Amount in UZS</Label>
                  <input id="manual-payment-amount" name="amount" type="number" min={1} max={firstInvoice.balanceMinor / 100} defaultValue={firstInvoice.balanceMinor / 100} required className={inputClass} />
                </div>
                <div>
                  <Label htmlFor="manual-payment-method">Method</Label>
                  <select id="manual-payment-method" name="method" className={inputClass}>
                    <option value="cash">Cash</option>
                    <option value="bank_transfer">Bank transfer</option>
                    <option value="card_terminal">Card terminal</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="manual-payment-date">Paid at</Label>
                  <input id="manual-payment-date" name="paidAt" type="datetime-local" required className={inputClass} />
                </div>
                <div>
                  <Label htmlFor="manual-payment-reference">Receipt or reference</Label>
                  <input id="manual-payment-reference" name="reference" required className={inputClass} />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="manual-payment-reason">Reason</Label>
                  <textarea id="manual-payment-reason" name="reason" required minLength={2} className={`${inputClass} min-h-20 py-3`} />
                </div>
                <div className="md:col-span-2">
                  <button type="submit" className={primaryButton} disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Check className="h-4 w-4" />}
                    Record manual payment
                  </button>
                </div>
              </form>
            ) : null}
          </div>
        ) : admission.contract?.status === "accepted" && admission.status === "awaiting_payment" ? (
          <form className="grid gap-3 rounded-lg border border-border bg-muted/30 p-3 md:grid-cols-2" onSubmit={addPaidInvoice}>
            <p className="text-sm font-bold text-muted-foreground md:col-span-2">
              Use this atomic action only when an external first payment arrived before its invoice was entered.
            </p>
            <div>
              <Label htmlFor="paid-invoice-due-date">Invoice due date</Label>
              <input id="paid-invoice-due-date" name="dueDate" type="date" defaultValue={admission.firstDueDate} required className={inputClass} />
            </div>
            <div>
              <Label htmlFor="paid-invoice-period">Billing month</Label>
              <input id="paid-invoice-period" name="billingPeriod" type="month" required className={inputClass} />
            </div>
            <div>
              <Label htmlFor="paid-invoice-method">Payment method</Label>
              <select id="paid-invoice-method" name="method" className={inputClass}>
                <option value="cash">Cash</option>
                <option value="bank_transfer">Bank transfer</option>
                <option value="card_terminal">Card terminal</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <Label htmlFor="paid-invoice-paid-at">Paid at</Label>
              <input id="paid-invoice-paid-at" name="paidAt" type="datetime-local" required className={inputClass} />
            </div>
            <div>
              <Label htmlFor="paid-invoice-reference">Receipt or reference</Label>
              <input id="paid-invoice-reference" name="reference" required className={inputClass} />
            </div>
            <div>
              <Label htmlFor="paid-invoice-reason">Reason</Label>
              <input id="paid-invoice-reason" name="reason" required minLength={2} className={inputClass} />
            </div>
            <div className="md:col-span-2">
              <button type="submit" className={primaryButton} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Check className="h-4 w-4" />}
                Add paid invoice and activate
              </button>
            </div>
          </form>
        ) : (
          <p className="text-sm font-semibold text-muted-foreground">
            The first invoice is issued automatically when Customer Support accepts the signed contract.
          </p>
        )}
      </DetailSection>

      <DetailSection title="Audit history" icon={<ClipboardCopy className="h-4 w-4" />}>
        {admission.auditEvents.length ? (
          <ol className="space-y-2">
            {admission.auditEvents.map((event) => (
              <li key={event.eventId} className="rounded-lg border border-border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-black text-foreground">{event.eventType.replace(/_/g, " ")}</p>
                  <time className="text-xs font-semibold text-muted-foreground" dateTime={event.createdAt}>
                    {formatDate(event.createdAt, true)}
                  </time>
                </div>
                {event.detailSummary ? <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">{event.detailSummary}</p> : null}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm font-semibold text-muted-foreground">No admission events have been recorded yet.</p>
        )}
      </DetailSection>
    </div>
  );
}
