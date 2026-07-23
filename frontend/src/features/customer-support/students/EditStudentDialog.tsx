import { Check, Loader2 } from "lucide-react";
import type { FormEvent } from "react";
import type { StudentProfile, SupportSchool } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export type EditStudentValues = {
  fullName: string;
  schoolId: number;
  phone: string;
  photoUrl: string;
  profileDescription: string;
  status: string;
};

export function EditStudentDialog({
  profile,
  schools,
  saving,
  onClose,
  onSubmit,
}: {
  profile: StudentProfile;
  schools: SupportSchool[];
  saving: boolean;
  onClose: () => void;
  onSubmit: (values: EditStudentValues) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit({
      fullName: String(data.get("fullName") || "").trim(),
      schoolId: Number(data.get("schoolId")),
      phone: String(data.get("phone") || "").trim(),
      photoUrl: String(data.get("photoUrl") || "").trim(),
      profileDescription: String(data.get("profileDescription") || "").trim(),
      status: String(data.get("status") || "active"),
    });
  }

  return (
    <Modal title="Edit student profile" onClose={onClose} size="md" mobileMode="fullscreen">
      <form onSubmit={submit} className="contents">
        <ModalBody>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-student-name">Full name</Label>
              <input id="edit-student-name" name="fullName" required defaultValue={profile.full_name} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="edit-student-school">School</Label>
              <select id="edit-student-school" name="schoolId" defaultValue={profile.school_id} className={inputClass}>
                {schools.map((school) => <option key={school.id} value={school.id}>{school.school_name}</option>)}
              </select>
              <p className="mt-1 text-xs font-semibold text-muted-foreground">School changes are blocked while active enrollments exist.</p>
            </div>
            <div>
              <Label htmlFor="edit-student-phone">Phone</Label>
              <input id="edit-student-phone" name="phone" type="tel" defaultValue={profile.phone} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="edit-student-photo">Photo URL</Label>
              <input id="edit-student-photo" name="photoUrl" type="url" defaultValue={profile.photo_url} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="edit-student-status">Access status</Label>
              <select id="edit-student-status" name="status" defaultValue={profile.status} className={inputClass}>
                <option value="active">Active</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
            <div>
              <Label htmlFor="edit-student-description">Profile description</Label>
              <textarea id="edit-student-description" name="profileDescription" defaultValue={profile.profile_description} rows={4} className={`${inputClass} py-3`} />
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
