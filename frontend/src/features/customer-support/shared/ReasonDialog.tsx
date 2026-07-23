import { AlertTriangle, Check, Loader2 } from "lucide-react";
import type { FormEvent } from "react";
import { dangerButton, inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export function ReasonDialog({
  title,
  saving,
  constructive = false,
  onClose,
  onSubmit,
}: {
  title: string;
  saving: boolean;
  constructive?: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const reason = String(new FormData(event.currentTarget).get("reason") || "").trim();
    if (reason) onSubmit(reason);
  }

  return (
    <Modal title={title} subtitle="This action is audited and requires a reason." onClose={onClose} size="sm" mobileMode="fullscreen">
      <form onSubmit={submit} className="contents">
        <ModalBody>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold leading-6 text-amber-900">
            <AlertTriangle className="mr-2 inline h-4 w-4" aria-hidden="true" />
            Confirm the selected record and explain why this change is needed.
          </div>
          <div className="mt-4">
            <Label htmlFor="support-action-reason">Reason</Label>
            <textarea id="support-action-reason" name="reason" required minLength={2} rows={4} className={`${inputClass} py-3`} autoFocus />
          </div>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className={secondaryButton}>Cancel</button>
            <button type="submit" disabled={saving} className={constructive ? primaryButton : dangerButton}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Check className="h-4 w-4" />}
              Proceed
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}
