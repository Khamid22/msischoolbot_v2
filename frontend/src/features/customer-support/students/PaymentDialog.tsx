import { CreditCard, Loader2 } from "lucide-react";
import type { FormEvent } from "react";
import type { PaymentRecord, StudentEnrollment } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export type PaymentValues = {
  subjectId?: number;
  monthLabel: string;
  amount: number;
  currency: string;
  dueDate: string;
  paidAt?: string;
  notes: string;
};

export function PaymentDialog({
  payment,
  activeSubjects,
  saving,
  onClose,
  onSubmit,
}: {
  payment?: PaymentRecord;
  activeSubjects: StudentEnrollment[];
  saving: boolean;
  onClose: () => void;
  onSubmit: (values: PaymentValues) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit({
      subjectId: payment ? undefined : Number(data.get("subjectId")),
      monthLabel: String(data.get("monthLabel") || "").trim(),
      amount: Number(data.get("amount")),
      currency: String(data.get("currency") || "UZS").trim().toUpperCase(),
      dueDate: String(data.get("dueDate") || ""),
      paidAt: payment ? undefined : String(data.get("paidAt") || ""),
      notes: String(data.get("notes") || "").trim(),
    });
  }

  return (
    <Modal
      title={payment ? "Edit payment" : "Add payment"}
      subtitle="All financial changes are written to the audit history."
      onClose={onClose}
      size="md"
      mobileMode="fullscreen"
    >
      <form onSubmit={submit} className="contents">
        <ModalBody>
          <div className="space-y-4">
            {!payment ? (
              <div>
                <Label htmlFor="payment-subject">Subject</Label>
                <select id="payment-subject" name="subjectId" required className={inputClass} defaultValue="">
                  <option value="" disabled>Select active subject</option>
                  {activeSubjects.map((subject) => (
                    <option key={subject.subject_id} value={subject.subject_id}>{subject.subject_name} · {subject.group_name}</option>
                  ))}
                </select>
                {!activeSubjects.length ? (
                  <p className="mt-1 text-xs font-bold text-destructive">Payment cannot be added until Academic Department enrolls this student.</p>
                ) : null}
              </div>
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="payment-month">Label / month</Label>
                <input id="payment-month" name="monthLabel" defaultValue={payment?.month_label} className={inputClass} />
              </div>
              <div>
                <Label htmlFor="payment-amount">Amount</Label>
                <input id="payment-amount" name="amount" type="number" min="0.01" step="0.01" required defaultValue={payment?.amount} className={inputClass} />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="payment-currency">Currency</Label>
                <input id="payment-currency" name="currency" minLength={3} maxLength={3} required defaultValue={payment?.currency || "UZS"} className={inputClass} />
              </div>
              <div>
                <Label htmlFor="payment-due">Due date</Label>
                <input id="payment-due" name="dueDate" type="date" defaultValue={payment?.due_date?.slice(0, 10)} className={inputClass} />
              </div>
            </div>
            {!payment ? (
              <div>
                <Label htmlFor="payment-paid">Paid date (optional)</Label>
                <input id="payment-paid" name="paidAt" type="date" className={inputClass} />
              </div>
            ) : null}
            <div>
              <Label htmlFor="payment-notes">Notes</Label>
              <textarea id="payment-notes" name="notes" rows={4} defaultValue={payment?.notes} className={`${inputClass} py-3`} />
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButton} onClick={onClose}>Cancel</button>
            <button type="submit" disabled={saving || (!payment && !activeSubjects.length)} className={primaryButton}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <CreditCard className="h-4 w-4" />}
              {payment ? "Save payment" : "Add payment"}
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}
