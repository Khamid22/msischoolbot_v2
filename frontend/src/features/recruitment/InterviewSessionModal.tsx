import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Play,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import {
  dateTimeLabel,
  type RecruitmentAppointment,
  type RecruitmentCandidate,
  type RecruitmentOptions,
} from "@/features/recruitment/model";
import {
  RECRUITMENT_API,
  buttonClass,
  fieldClass,
  queryError,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";

type SessionResponse = {
  message: string;
  candidate?: RecruitmentCandidate;
  appointment?: RecruitmentAppointment | null;
};

function interviewValues(form: HTMLFormElement | null) {
  const data = new FormData(form || undefined);
  const optionalId = (name: string) => {
    const value = String(data.get(name) || "");
    return value ? Number(value) : null;
  };
  return {
    english_level_option_id: optionalId("english_level_option_id"),
    education_background: String(data.get("education_background") || ""),
    teaching_experience_option_id: optionalId(
      "teaching_experience_option_id",
    ),
    interests_hobbies: String(data.get("interests_hobbies") || ""),
    motivation_expectations: String(
      data.get("motivation_expectations") || "",
    ),
  };
}

export function InterviewSessionModal({
  candidate,
  appointment,
  options,
  open,
  onClose,
  onAnnouncement,
}: {
  candidate: RecruitmentCandidate;
  appointment: RecruitmentAppointment;
  options?: RecruitmentOptions;
  open: boolean;
  onClose: () => void;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLFormElement>(null);
  const [session, setSession] = useState(appointment);
  const [confirmStart, setConfirmStart] = useState(false);
  const [confirmFail, setConfirmFail] = useState(false);
  const [failReason, setFailReason] = useState("");
  const supplemental = candidate.status === "teacher_academy";

  useEffect(() => {
    setSession(appointment);
    setConfirmStart(false);
    setConfirmFail(false);
    setFailReason("");
  }, [appointment]);

  const start = useMutation({
    mutationFn: () =>
      recruitmentRequest<SessionResponse>(
        `${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${session.id}/start`,
        {
          method: "POST",
          body: jsonBody({ expected_version: session.version }),
        },
      ),
    onSuccess: (result) => {
      if (result.appointment) setSession(result.appointment);
      setConfirmStart(false);
      onAnnouncement(result.message || "Interview started.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const complete = useMutation({
    mutationFn: ({
      result,
      reasonDetail,
    }: {
      result: "passed" | "failed";
      reasonDetail?: string;
    }) =>
      recruitmentRequest<SessionResponse>(
        `${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${session.id}/complete-interview`,
        {
          method: "POST",
          body: jsonBody({
            expected_version: session.version,
            result,
            reason_detail: reasonDetail || "",
            ...interviewValues(formRef.current),
          }),
        },
      ),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Interview completed.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
      onClose();
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const pending = start.isPending || complete.isPending;
  const inProgress = session.status === "in_progress";
  const englishOptions =
    options?.option_categories.english_level || [];
  const teachingOptions =
    options?.option_categories.teaching_experience || [];

  return (
    <Modal
      open={open}
      onClose={() => {
        if (!pending) onClose();
      }}
      title={inProgress ? "Conduct job interview" : "Job interview"}
      subtitle={candidate.full_name}
      size="lg"
      closeOnEscape={!pending}
      closeOnOutsideClick={!pending}
    >
      <form
        ref={formRef}
        className="flex min-h-0 flex-1 flex-col"
        onSubmit={(event) => {
          event.preventDefault();
          complete.mutate({ result: "passed" });
        }}
      >
        <ModalBody className="space-y-4">
          <section className="grid gap-2 rounded-xl border border-border bg-muted/35 p-3 sm:grid-cols-2">
            <div>
              <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                {inProgress ? "Actual start" : "Scheduled"}
              </span>
              <strong className="mt-1 block text-sm">
                {dateTimeLabel(
                  inProgress ? session.started_at : session.starts_at,
                )}
              </strong>
            </div>
            <div>
              <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                Format
              </span>
              <strong className="mt-1 block break-words text-sm">
                {session.appointment_format || "Not set"}
              </strong>
            </div>
            {session.location_or_link ? (
              <div className="sm:col-span-2">
                <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                  Room or link
                </span>
                <strong className="mt-1 block break-all text-sm">
                  {session.location_or_link}
                </strong>
              </div>
            ) : null}
          </section>

          {!inProgress ? (
            confirmStart ? (
              <div
                role="alert"
                className="rounded-xl border border-amber-400/50 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/20 dark:text-amber-100"
              >
                <p className="flex items-center gap-2 font-semibold">
                  <AlertTriangle className="h-4 w-4" />
                  Start interview now?
                </p>
                <p className="mt-1 text-xs leading-5">
                  The scheduled date and time will be overwritten with the
                  current Asia/Tashkent time.
                </p>
              </div>
            ) : (
              <p className="rounded-xl border border-border bg-muted/35 p-3 text-sm text-muted-foreground">
                HR may start this interview at any time.
              </p>
            )
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs font-semibold">
                English level
                <select
                  name="english_level_option_id"
                  defaultValue={candidate.english_level_option_id || ""}
                  className={`${fieldClass} mt-1`}
                >
                  <option value="">Not set</option>
                  {englishOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-semibold">
                Teaching experience
                <select
                  name="teaching_experience_option_id"
                  defaultValue={
                    candidate.teaching_experience_option_id || ""
                  }
                  className={`${fieldClass} mt-1`}
                >
                  <option value="">Not set</option>
                  {teachingOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-semibold sm:col-span-2">
                Education background
                <textarea
                  autoFocus
                  name="education_background"
                  defaultValue={candidate.education_background || ""}
                  className={`${fieldClass} mt-1 min-h-20`}
                />
              </label>
              <label className="text-xs font-semibold">
                Interests
                <textarea
                  name="interests_hobbies"
                  defaultValue={candidate.interests_hobbies || ""}
                  className={`${fieldClass} mt-1 min-h-20`}
                />
              </label>
              <label className="text-xs font-semibold">
                Motivation
                <textarea
                  name="motivation_expectations"
                  defaultValue={candidate.motivation_expectations || ""}
                  className={`${fieldClass} mt-1 min-h-20`}
                />
              </label>
            </div>
          )}

          {confirmFail ? (
            <div
              role="alert"
              className="space-y-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
            >
              <p className="flex items-center gap-2 font-semibold">
                <AlertTriangle className="h-4 w-4" />
                {supplemental
                  ? "Record a failed supplemental interview?"
                  : `Reject ${candidate.full_name}?`}
              </p>
              <p className="text-xs leading-5">
                {supplemental
                  ? "This result is added to Academy history and does not change Academy status."
                  : "Failing this interview rejects the candidate and cancels remaining appointments."}
              </p>
              {!supplemental ? (
                <label className="block text-xs font-semibold text-foreground">
                  Reason for rejection
                  <textarea
                    autoFocus
                    required
                    value={failReason}
                    onChange={(event) => setFailReason(event.target.value)}
                    className={`${fieldClass} mt-1 min-h-20`}
                    placeholder="Why is this candidate being rejected?"
                  />
                </label>
              ) : null}
            </div>
          ) : null}
        </ModalBody>
        <ModalFooter>
          {!inProgress ? (
            confirmStart ? (
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  disabled={pending}
                  onClick={() => setConfirmStart(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className={buttonClass}
                  disabled={pending}
                  onClick={() => start.mutate()}
                >
                  {start.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  Proceed
                </button>
              </div>
            ) : (
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={onClose}
                >
                  Close
                </button>
                <button
                  type="button"
                  className={buttonClass}
                  onClick={() => setConfirmStart(true)}
                >
                  <Play className="h-4 w-4" />
                  Start interview
                </button>
              </div>
            )
          ) : confirmFail ? (
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className={secondaryButtonClass}
                onClick={() => setConfirmFail(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-destructive px-3 text-sm font-semibold text-destructive-foreground disabled:cursor-not-allowed disabled:opacity-50"
                disabled={
                  pending || (!supplemental && !failReason.trim())
                }
                onClick={() =>
                  complete.mutate({
                    result: "failed",
                    reasonDetail: failReason.trim(),
                  })
                }
              >
                {complete.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                {supplemental ? "Save failed result" : "Reject candidate"}
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-destructive/40 px-3 text-sm font-semibold text-destructive"
                disabled={pending}
                onClick={() => setConfirmFail(true)}
              >
                <XCircle className="h-4 w-4" />
                Fail
              </button>
              <button
                type="submit"
                className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-emerald-700 px-3 text-sm font-semibold text-white"
                disabled={pending}
              >
                {complete.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                Pass
              </button>
            </div>
          )}
        </ModalFooter>
      </form>
    </Modal>
  );
}
