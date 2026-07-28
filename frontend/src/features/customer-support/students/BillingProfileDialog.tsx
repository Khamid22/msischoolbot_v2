import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Loader2 } from "lucide-react";
import type { FormEvent } from "react";
import { getSupport, sendSupport } from "@/features/customer-support/api";
import type {
  BillingProfile,
  StudentEnrollment,
} from "@/features/customer-support/model";
import {
  inputClass,
  Label,
  primaryButton,
  secondaryButton,
} from "@/features/customer-support/shared/ui";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

export function BillingProfileDialog({
  studentId,
  activeEnrollments,
  csrfToken,
  onClose,
  onSaved,
}: {
  studentId: number;
  activeEnrollments: StudentEnrollment[];
  csrfToken: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["customer-support", "billing-profile", studentId],
    queryFn: ({ signal }) => getSupport<BillingProfile | null>(
      `/payments/students/${studentId}/billing-profile`,
      signal,
    ),
  });
  const mutation = useMutation({
    mutationFn: (body: object) => sendSupport<BillingProfile>(
      `/payments/students/${studentId}/billing-profile`,
      "PUT",
      body,
      csrfToken,
    ),
    onSuccess: (profile) => {
      queryClient.setQueryData(
        ["customer-support", "billing-profile", studentId],
        profile,
      );
      onSaved();
      onClose();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const items = activeEnrollments
      .filter((enrollment) => data.get(`enabled-${enrollment.group_id}`) === "on")
      .map((enrollment) => ({
        groupId: enrollment.group_id,
        amount: Number(data.get(`amount-${enrollment.group_id}`)),
        description: String(
          data.get(`description-${enrollment.group_id}`) || enrollment.subject_name,
        ).trim(),
      }));
    mutation.mutate({
      billingDay: Number(data.get("billingDay")),
      startsOn: String(data.get("startsOn") || ""),
      status: String(data.get("status") || "active"),
      expectedVersion: query.data?.version,
      items,
    });
  }

  const today = new Date(
    Date.now() - new Date().getTimezoneOffset() * 60_000,
  ).toISOString().slice(0, 10);
  const existingByGroup = new Map(
    (query.data?.items || []).map((item) => [item.groupId, item]),
  );

  return (
    <Modal
      title="Recurring billing"
      subtitle="Set the monthly UZS amount for each active group. The worker issues one invoice per billing period."
      onClose={onClose}
      size="lg"
      mobileMode="fullscreen"
    >
      {query.isLoading ? (
        <ModalBody>
          <div className="space-y-3" role="status" aria-label="Loading billing profile">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-16 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
            ))}
          </div>
        </ModalBody>
      ) : query.isError ? (
        <ModalBody>
          <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm font-bold text-destructive">
            {query.error instanceof Error ? query.error.message : "Billing profile could not be loaded."}
          </p>
        </ModalBody>
      ) : (
        <form onSubmit={submit} className="contents">
          <ModalBody>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <Label htmlFor="billing-day">Billing day</Label>
                <input
                  id="billing-day"
                  name="billingDay"
                  type="number"
                  min="1"
                  max="28"
                  required
                  defaultValue={query.data?.billingDay || 1}
                  className={inputClass}
                />
              </div>
              <div>
                <Label htmlFor="billing-start">Starts on</Label>
                <input
                  id="billing-start"
                  name="startsOn"
                  type="date"
                  required
                  defaultValue={query.data?.startsOn || today}
                  className={inputClass}
                />
              </div>
              <div>
                <Label htmlFor="billing-status">Status</Label>
                <select
                  id="billing-status"
                  name="status"
                  defaultValue={query.data?.status || "active"}
                  className={inputClass}
                >
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="ended">Ended</option>
                </select>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {activeEnrollments.map((enrollment) => {
                const existing = existingByGroup.get(enrollment.group_id);
                return (
                  <fieldset
                    key={enrollment.group_id}
                    className="rounded-lg border border-border p-3"
                  >
                    <label className="flex min-h-11 cursor-pointer items-center gap-3 font-black text-foreground">
                      <input
                        type="checkbox"
                        name={`enabled-${enrollment.group_id}`}
                        defaultChecked={Boolean(existing)}
                        className="h-4 w-4 accent-primary"
                      />
                      {enrollment.subject_name} · {enrollment.group_name}
                    </label>
                    <div className="mt-2 grid gap-3 sm:grid-cols-2">
                      <div>
                        <Label htmlFor={`billing-amount-${enrollment.group_id}`}>
                          Monthly amount in UZS
                        </Label>
                        <input
                          id={`billing-amount-${enrollment.group_id}`}
                          name={`amount-${enrollment.group_id}`}
                          type="number"
                          min="1"
                          step="1"
                          defaultValue={existing ? existing.amountMinor / 100 : ""}
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <Label htmlFor={`billing-description-${enrollment.group_id}`}>
                          Invoice line
                        </Label>
                        <input
                          id={`billing-description-${enrollment.group_id}`}
                          name={`description-${enrollment.group_id}`}
                          defaultValue={existing?.description || enrollment.subject_name}
                          maxLength={200}
                          className={inputClass}
                        />
                      </div>
                    </div>
                  </fieldset>
                );
              })}
            </div>
            {!activeEnrollments.length ? (
              <p className="mt-4 text-sm font-bold text-destructive">
                Add an active academic enrollment before configuring billing.
              </p>
            ) : null}
            {mutation.isError ? (
              <p role="alert" className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">
                {mutation.error instanceof Error ? mutation.error.message : "Billing profile could not be saved."}
              </p>
            ) : null}
          </ModalBody>
          <ModalFooter>
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button type="button" className={secondaryButton} onClick={onClose}>
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending || !activeEnrollments.length}
                className={primaryButton}
              >
                {mutation.isPending
                  ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                  : <CalendarClock className="h-4 w-4" />}
                Save billing schedule
              </button>
            </div>
          </ModalFooter>
        </form>
      )}
    </Modal>
  );
}
