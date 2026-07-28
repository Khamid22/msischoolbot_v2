import { Loader2, Plus } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import type { AdmissionGroupOption } from "@/features/customer-support/model";
import { inputClass, Label, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export type CreateAdmissionValues = {
  schoolId: number;
  studentFullName: string;
  studentPhone: string;
  parentFullName: string;
  parentPhone: string;
  parentTelegramUsername: string;
  preferredLanguage: "uz" | "ru";
  serviceStartDate: string | null;
  firstDueDate: string;
  billingDay: number;
  groups: Array<{ groupId: number; monthlyAmountMinor: number }>;
};

export function AdmissionWizard({
  groupOptions,
  saving,
  onClose,
  onSubmit,
}: {
  groupOptions: AdmissionGroupOption[];
  saving: boolean;
  onClose: () => void;
  onSubmit: (values: CreateAdmissionValues) => void;
}) {
  const schools = useMemo(
    () => Array.from(
      new Map(groupOptions.map((group) => [group.schoolId, {
        schoolId: group.schoolId,
        schoolName: group.schoolName,
      }])).values(),
    ),
    [groupOptions],
  );
  const [schoolId, setSchoolId] = useState(schools[0]?.schoolId || 0);
  const visibleGroups = groupOptions.filter((group) => group.schoolId === schoolId);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const selected = visibleGroups.flatMap((group) => {
      if (data.get(`group-${group.groupId}`) !== "on") return [];
      const amountUzs = Number(data.get(`amount-${group.groupId}`) || 0);
      return amountUzs > 0
        ? [{ groupId: group.groupId, monthlyAmountMinor: Math.round(amountUzs * 100) }]
        : [];
    });
    onSubmit({
      schoolId,
      studentFullName: String(data.get("studentFullName") || "").trim(),
      studentPhone: String(data.get("studentPhone") || "").trim(),
      parentFullName: String(data.get("parentFullName") || "").trim(),
      parentPhone: String(data.get("parentPhone") || "").trim(),
      parentTelegramUsername: String(data.get("parentTelegramUsername") || "").trim(),
      preferredLanguage: data.get("preferredLanguage") === "ru" ? "ru" : "uz",
      serviceStartDate: String(data.get("serviceStartDate") || "").trim() || null,
      firstDueDate: String(data.get("firstDueDate") || ""),
      billingDay: Number(data.get("billingDay") || 1),
      groups: selected,
    });
  }

  return (
    <Modal
      title="New admission"
      subtitle="The student remains prospective until the accepted contract and first paid invoice activate enrollment."
      onClose={onClose}
      size="xl"
      mobileMode="fullscreen"
    >
      <form className="contents" onSubmit={submit}>
        <ModalBody>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="admission-student-name">Future student</Label>
              <input id="admission-student-name" name="studentFullName" required minLength={2} className={inputClass} autoFocus />
            </div>
            <div>
              <Label htmlFor="admission-student-phone">Student phone (optional)</Label>
              <input id="admission-student-phone" name="studentPhone" type="tel" className={inputClass} />
            </div>
            <div>
              <Label htmlFor="admission-parent-name">Parent or guardian</Label>
              <input id="admission-parent-name" name="parentFullName" required minLength={2} className={inputClass} />
            </div>
            <div>
              <Label htmlFor="admission-parent-phone">Parent phone</Label>
              <input id="admission-parent-phone" name="parentPhone" required minLength={5} type="tel" className={inputClass} />
            </div>
            <div>
              <Label htmlFor="admission-parent-telegram">Telegram username (optional)</Label>
              <input id="admission-parent-telegram" name="parentTelegramUsername" className={inputClass} placeholder="@username" />
            </div>
            <div>
              <Label htmlFor="admission-language">Parent language</Label>
              <select id="admission-language" name="preferredLanguage" className={inputClass} defaultValue="uz">
                <option value="uz">Uzbek</option>
                <option value="ru">Russian</option>
              </select>
            </div>
            <div>
              <Label htmlFor="admission-school">School</Label>
              <select
                id="admission-school"
                name="schoolId"
                className={inputClass}
                value={schoolId || ""}
                onChange={(event) => setSchoolId(Number(event.target.value))}
                required
              >
                <option value="" disabled>Select school</option>
                {schools.map((school) => (
                  <option key={school.schoolId} value={school.schoolId}>{school.schoolName}</option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="admission-service-start">Service starts</Label>
              <input id="admission-service-start" name="serviceStartDate" type="date" className={inputClass} />
            </div>
            <div>
              <Label htmlFor="admission-first-due">First invoice due</Label>
              <input id="admission-first-due" name="firstDueDate" type="date" required className={inputClass} />
            </div>
            <div>
              <Label htmlFor="admission-billing-day">Monthly billing day</Label>
              <input id="admission-billing-day" name="billingDay" type="number" min={1} max={28} defaultValue={1} required className={inputClass} />
            </div>
          </div>

          <fieldset className="mt-6 rounded-xl border border-border p-4">
            <legend className="px-2 text-sm font-black text-foreground">Groups and monthly amounts</legend>
            <p className="mb-4 text-xs font-semibold leading-5 text-muted-foreground">
              Subjects are derived from the selected groups. Select only one group for each subject. Amounts are entered in UZS.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {visibleGroups.map((group) => (
                <div key={group.groupId} className="rounded-lg border border-border bg-muted/30 p-3">
                  <label className="flex min-h-11 cursor-pointer items-center gap-3 font-bold text-foreground">
                    <input name={`group-${group.groupId}`} type="checkbox" className="h-5 w-5 rounded border-border accent-primary" />
                    <span>
                      <span className="block text-sm">{group.subjectName}</span>
                      <span className="block text-xs font-semibold text-muted-foreground">{group.groupName}</span>
                    </span>
                  </label>
                  <label className="mt-2 block text-xs font-bold text-muted-foreground">
                    Monthly UZS
                    <input
                      name={`amount-${group.groupId}`}
                      type="number"
                      min={1}
                      step={1}
                      className={`${inputClass} mt-1`}
                      placeholder="1,000,000"
                    />
                  </label>
                </div>
              ))}
            </div>
            {!visibleGroups.length ? (
              <p className="rounded-lg bg-muted p-4 text-sm font-semibold text-muted-foreground">
                No active groups are available for this school.
              </p>
            ) : null}
          </fieldset>
        </ModalBody>
        <ModalFooter>
          <div className="flex justify-end gap-2">
            <button type="button" className={secondaryButton} onClick={onClose}>Cancel</button>
            <button type="submit" className={primaryButton} disabled={saving || !visibleGroups.length}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Plus className="h-4 w-4" />}
              Create admission
            </button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
}
