import { CreditCard, Loader2 } from "lucide-react";
import { type FormEvent, useState } from "react";
import type { StudentEnrollment } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export type PaymentValues = {
  subjectId?: number;
  monthLabel: string;
  amount: number;
  currency: string;
  dueDate: string;
  paidAt?: string;
  method?: "cash" | "bank_transfer" | "card_terminal" | "other";
  reference?: string;
  reason?: string;
  notes: string;
};

export function PaymentDialog({
  activeSubjects,
  saving,
  onClose,
  onSubmit,
}: {
  activeSubjects: StudentEnrollment[];
  saving: boolean;
  onClose: () => void;
  onSubmit: (values: PaymentValues) => void;
}) {
  const [isAlreadyPaid, setIsAlreadyPaid] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit({
      subjectId: Number(data.get("subjectId")),
      monthLabel: String(data.get("monthLabel") || "").trim(),
      amount: Number(data.get("amount")),
      currency: String(data.get("currency") || "UZS").trim().toUpperCase(),
      dueDate: String(data.get("dueDate") || ""),
      paidAt: isAlreadyPaid ? String(data.get("paidAt") || "") : "",
      method: isAlreadyPaid
        ? String(data.get("method") || "") as PaymentValues["method"]
        : undefined,
      reference: isAlreadyPaid ? String(data.get("reference") || "").trim() : undefined,
      reason: isAlreadyPaid ? String(data.get("reason") || "").trim() : undefined,
      notes: String(data.get("notes") || "").trim(),
    });
  }

  return (
    <Modal
      title="Add invoice"
      subtitle="Create an unpaid invoice or record an external payment atomically."
      onClose={onClose}
      size="md"
      mobileMode="fullscreen"
    >
      <form onSubmit={submit} className="contents">
        <ModalBody>
          <div className="space-y-4">
            <div>
              <Label htmlFor="payment-subject">Subject</Label>
              <select id="payment-subject" name="subjectId" required className={inputClass} defaultValue="">
                <option value="" disabled>Select active subject</option>
                {activeSubjects.map((subject) => (
                  <option key={`${subject.group_id}-${subject.subject_id}`} value={subject.subject_id}>
                    {subject.subject_name} · {subject.group_name}
                  </option>
                ))}
              </select>
              {!activeSubjects.length ? (
                <p className="mt-1 text-xs font-bold text-destructive">An invoice requires an active academic enrollment.</p>
              ) : null}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="payment-month">Label / month</Label>
                <input id="payment-month" name="monthLabel" required placeholder="August tuition" className={inputClass} />
              </div>
              <div>
                <Label htmlFor="payment-amount">Amount</Label>
                <input id="payment-amount" name="amount" type="number" min="1" step="1" required className={inputClass} />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="payment-currency">Currency</Label>
                <input id="payment-currency" name="currency" value="UZS" readOnly className={inputClass} />
              </div>
              <div>
                <Label htmlFor="payment-due">Due date</Label>
                <input id="payment-due" name="dueDate" type="date" required className={inputClass} />
              </div>
            </div>
            <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border border-border bg-muted/35 px-3 py-2 text-sm font-bold text-foreground">
              <input
                type="checkbox"
                checked={isAlreadyPaid}
                onChange={(event) => setIsAlreadyPaid(event.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              This invoice was already paid outside Payme
            </label>
            {isAlreadyPaid ? (
              <div className="space-y-4 rounded-lg border border-border bg-muted/25 p-3">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <Label htmlFor="payment-paid">Paid date</Label>
                    <input id="payment-paid" name="paidAt" type="date" required className={inputClass} />
                  </div>
                  <div>
                    <Label htmlFor="payment-method">Payment method</Label>
                    <select id="payment-method" name="method" required className={inputClass} defaultValue="">
                      <option value="" disabled>Select method</option>
                      <option value="cash">Cash</option>
                      <option value="bank_transfer">Bank transfer</option>
                      <option value="card_terminal">Card terminal</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="payment-reference">Receipt / reference</Label>
                  <input id="payment-reference" name="reference" required maxLength={200} className={inputClass} />
                </div>
                <div>
                  <Label htmlFor="payment-reason">Reason</Label>
                  <textarea id="payment-reason" name="reason" required minLength={2} rows={2} className={`${inputClass} py-3`} />
                </div>
              </div>
            ) : null}
            <div>
              <Label htmlFor="payment-notes">Notes</Label>
              <textarea id="payment-notes" name="notes" rows={3} className={`${inputClass} py-3`} />
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButton} onClick={onClose}>Cancel</button>
            <button type="submit" disabled={saving || !activeSubjects.length} className={primaryButton}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <CreditCard className="h-4 w-4" />}
              {isAlreadyPaid ? "Add paid invoice" : "Issue invoice"}
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}
