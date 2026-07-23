import { Loader2, Plus } from "lucide-react";
import type { FormEvent } from "react";
import type { SupportSchool } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export type CreateStudentValues = {
  fullName: string;
  schoolId: number;
  phone: string;
  photoUrl: string;
  profileDescription: string;
};

export function CreateStudentDialog({
  schools,
  defaultSchoolId,
  saving,
  onClose,
  onSubmit,
}: {
  schools: SupportSchool[];
  defaultSchoolId: string;
  saving: boolean;
  onClose: () => void;
  onSubmit: (values: CreateStudentValues) => void;
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
    });
  }

  return (
    <Modal
      title="Create student"
      subtitle="Creates the canonical student and login without changing Academic enrollment."
      onClose={onClose}
      size="md"
      mobileMode="fullscreen"
    >
      <form onSubmit={submit} className="contents">
        <ModalBody>
          <div className="space-y-4">
            <div>
              <Label htmlFor="create-student-name">Full name</Label>
              <input id="create-student-name" name="fullName" required minLength={2} className={inputClass} autoFocus />
            </div>
            <div>
              <Label htmlFor="create-student-school">School</Label>
              <select id="create-student-school" name="schoolId" required className={inputClass} defaultValue={defaultSchoolId}>
                <option value="" disabled>Select school</option>
                {schools.map((school) => <option key={school.id} value={school.id}>{school.school_name}</option>)}
              </select>
            </div>
            <div>
              <Label htmlFor="create-student-phone">Phone</Label>
              <input id="create-student-phone" name="phone" type="tel" className={inputClass} />
            </div>
            <div>
              <Label htmlFor="create-student-photo">Photo URL</Label>
              <input id="create-student-photo" name="photoUrl" type="url" className={inputClass} />
            </div>
            <div>
              <Label htmlFor="create-student-description">Profile description</Label>
              <textarea id="create-student-description" name="profileDescription" rows={4} className={`${inputClass} py-3`} />
            </div>
            <p className="rounded-lg bg-primary/8 p-3 text-xs font-semibold leading-5 text-foreground">
              Academic subjects and groups are intentionally assigned by Academic Department after account creation.
            </p>
          </div>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButton} onClick={onClose}>Cancel</button>
            <button type="submit" disabled={saving} className={primaryButton}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Plus className="h-4 w-4" />}
              Create student
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}
