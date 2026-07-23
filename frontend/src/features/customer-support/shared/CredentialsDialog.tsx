import { Copy, KeyRound, Send } from "lucide-react";
import type { ParentInviteResult, StudentCredentials } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type CredentialsDialogProps =
  | {
      mode: "credentials";
      title: string;
      credentials: StudentCredentials;
      invite?: never;
      onCopy: (value: string, label: string) => void;
      onClose: () => void;
    }
  | {
      mode: "invite";
      title: string;
      credentials?: never;
      invite: ParentInviteResult;
      onCopy: (value: string, label: string) => void;
      onClose: () => void;
    };

function CopyField({
  id,
  label,
  value,
  onCopy,
}: {
  id: string;
  label: string;
  value: string;
  onCopy: (value: string, label: string) => void;
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <div className="flex gap-2">
        <input id={id} readOnly value={value} className={`${inputClass} min-w-0 font-mono text-sm`} />
        <button type="button" className={secondaryButton} onClick={() => onCopy(value, label)} aria-label={`Copy ${label.toLowerCase()}`}>
          <Copy className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

export function CredentialsDialog(props: CredentialsDialogProps) {
  const isInvite = props.mode === "invite";
  return (
    <Modal
      title={props.title}
      subtitle={isInvite ? "Share one of these links with the parent." : "Sensitive access details are shown only in this window."}
      onClose={props.onClose}
      size="sm"
      closeOnOutsideClick={false}
      mobileMode="fullscreen"
    >
      <ModalBody>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-amber-900">
            {isInvite ? <Send className="h-4 w-4" aria-hidden="true" /> : <KeyRound className="h-4 w-4" aria-hidden="true" />}
            Shown once
          </p>
          <div className="mt-3 space-y-3">
            {props.mode === "invite" ? (
              <>
                {props.invite.telegramInviteUrl ? (
                  <CopyField id="telegram-parent-invite" label="Telegram invitation URL" value={props.invite.telegramInviteUrl} onCopy={props.onCopy} />
                ) : null}
                <CopyField id="web-parent-invite" label={props.invite.telegramInviteUrl ? "Web invitation fallback" : "Web invitation URL"} value={props.invite.webInviteUrl || props.invite.inviteUrl} onCopy={props.onCopy} />
              </>
            ) : (
              <>
                <CopyField id="generated-login" label="Login" value={props.credentials.login} onCopy={props.onCopy} />
                <CopyField id="generated-password" label="Temporary password" value={props.credentials.temporaryPassword} onCopy={props.onCopy} />
                <p className="text-xs font-semibold leading-5 text-amber-950">
                  Existing sessions have been invalidated. The student must change this temporary password after signing in. No previous password is displayed.
                </p>
              </>
            )}
          </div>
        </div>
      </ModalBody>
      <ModalFooter>
        <button type="button" className={`${primaryButton} w-full`} onClick={props.onClose}>
          I have saved it
        </button>
      </ModalFooter>
    </Modal>
  );
}
