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

export function DemoSessionModal({
  candidate,
  appointment,
  open,
  onClose,
  onAnnouncement,
}: {
  candidate: RecruitmentCandidate;
  appointment: RecruitmentAppointment;
  open: boolean;
  onClose: () => void;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
}) {
  const queryClient = useQueryClient();
  const notesRef = useRef<HTMLTextAreaElement>(null);
  const [session, setSession] = useState(appointment);
  const [confirmStart, setConfirmStart] = useState(false);
  const [confirmFail, setConfirmFail] = useState(false);
  const supplemental = candidate.status === "teacher_academy";

  useEffect(() => {
    setSession(appointment);
    setConfirmStart(false);
    setConfirmFail(false);
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
      onAnnouncement(result.message || "Demo lesson started.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const complete = useMutation({
    mutationFn: (result: "passed" | "failed") =>
      recruitmentRequest<SessionResponse>(
        `${RECRUITMENT_API}/candidates/${candidate.id}/demo-lessons`,
        {
          method: "POST",
          body: jsonBody({
            appointment_id: session.id,
            expected_version: session.version,
            subject_id: candidate.subject_id || null,
            subject_label: candidate.subject || "",
            topic: session.topic || "",
            overview: notesRef.current?.value || "",
            criteria_scores: [],
            result,
          }),
        },
      ),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Demo lesson completed.");
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
      onClose();
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const pending = start.isPending || complete.isPending;
  const inProgress = session.status === "in_progress";

  return (
    <Modal
      open={open}
      onClose={() => {
        if (!pending) onClose();
      }}
      title={inProgress ? "Evaluate demo lesson" : "Demo lesson"}
      subtitle={candidate.full_name}
      size="md"
      closeOnEscape={!pending}
      closeOnOutsideClick={!pending}
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
          {session.topic ? (
            <div className="sm:col-span-2">
              <span className="text-[10px] font-semibold uppercase text-muted-foreground">
                Topic
              </span>
              <strong className="mt-1 block break-words text-sm">
                {session.topic}
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
                Start demo lesson now?
              </p>
              <p className="mt-1 text-xs leading-5">
                The scheduled date and time will be overwritten with the
                current Asia/Tashkent time.
              </p>
            </div>
          ) : (
            <p className="rounded-xl border border-border bg-muted/35 p-3 text-sm text-muted-foreground">
              The assigned evaluator may start this demo lesson at any time.
            </p>
          )
        ) : (
          <label className="text-xs font-semibold">
            Evaluator notes
            <textarea
              ref={notesRef}
              autoFocus
              className={`${fieldClass} mt-1 min-h-28`}
            />
          </label>
        )}

        {confirmFail ? (
          <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            <p className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              {supplemental
                ? "Record a failed supplemental demo?"
                : "Fail this demo lesson?"}
            </p>
            <p className="mt-1 text-xs leading-5">
              {supplemental
                ? "This updates Academy history only and does not change Academy status."
                : "The candidate will be rejected automatically."}
            </p>
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
                Start demo
              </button>
            </div>
          )
        ) : confirmFail ? (
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={() => setConfirmFail(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-destructive px-3 text-sm font-semibold text-destructive-foreground"
              disabled={pending}
              onClick={() => complete.mutate("failed")}
            >
              {complete.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              Save failed result
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
              type="button"
              className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-emerald-700 px-3 text-sm font-semibold text-white"
              disabled={pending}
              onClick={() => complete.mutate("passed")}
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
    </Modal>
  );
}
