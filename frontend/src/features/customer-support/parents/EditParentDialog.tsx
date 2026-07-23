import { Check, Loader2 } from "lucide-react";
import type { FormEvent } from "react";
import type { ParentProfile, SupportLanguage } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export type EditParentValues = {
  displayName: string;
  phone: string;
  telegramUsername: string;
  preferredLanguage: SupportLanguage;
};

export function EditParentDialog({
  profile,
  saving,
  onClose,
  onSubmit,
}: {
  profile: ParentProfile;
  saving: boolean;
  onClose: () => void;
  onSubmit: (values: EditParentValues) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit({
      displayName: String(data.get("displayName") || "").trim(),
      phone: String(data.get("phone") || "").trim(),
      telegramUsername: String(data.get("telegramUsername") || "").trim().replace(/^@/, ""),
      preferredLanguage: String(data.get("preferredLanguage") || "ru") as SupportLanguage,
    });
  }

  return (
    <Modal title="Edit parent profile" onClose={onClose} size="md" mobileMode="fullscreen">
      <form onSubmit={submit} className="contents">
        <ModalBody>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-parent-name">Full name</Label>
              <input id="edit-parent-name" name="displayName" required minLength={2} defaultValue={profile.display_name} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="edit-parent-phone">Phone</Label>
              <input id="edit-parent-phone" name="phone" type="tel" defaultValue={profile.phone} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="edit-parent-telegram">Telegram username</Label>
              <input id="edit-parent-telegram" name="telegramUsername" defaultValue={profile.telegram_username} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="edit-parent-language">Preferred language</Label>
              <select id="edit-parent-language" name="preferredLanguage" defaultValue={profile.preferred_language || "ru"} className={inputClass}>
                <option value="uz">Uzbek</option>
                <option value="ru">Russian</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className={secondaryButton}>Cancel</button>
            <button type="submit" disabled={saving} className={primaryButton}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Check className="h-4 w-4" />}
              Save changes
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}
