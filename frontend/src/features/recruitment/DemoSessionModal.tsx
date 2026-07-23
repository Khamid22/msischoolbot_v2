import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Play,
  RotateCcw,
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

const demoCriteria = [
  { key: "english_fluency", label: "English fluency" },
  { key: "lesson_structure", label: "Lesson structure" },
  { key: "board_skills", label: "Board skills" },
  { key: "student_engagement", label: "Student engagement" },
  { key: "confidence_delivery", label: "Confidence & delivery" },
] as const;

type DemoScoreKey = (typeof demoCriteria)[number]["key"];
type DemoCompletion = {
  result: "passed" | "failed";
  rejectionReason?: string;
  reasonDetail?: string;
};

const demoFailureReasons = [
  {
    value: "insufficient_subject_knowledge",
    label: "Insufficient subject knowledge",
  },
  { value: "insufficient_experience", label: "Insufficient experience" },
  { value: "other", label: "Other" },
] as const;

function emptyDemoScores(): Record<DemoScoreKey, string> {
  return {
    english_fluency: "",
    lesson_structure: "",
    board_skills: "",
    student_engagement: "",
    confidence_delivery: "",
  };
}

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
  const [confirmUndoStart, setConfirmUndoStart] = useState(false);
  const [confirmFail, setConfirmFail] = useState(false);
  const [scores, setScores] = useState<Record<DemoScoreKey, string>>(
    emptyDemoScores,
  );
  const [rejectionReason, setRejectionReason] = useState("");
  const [reasonDetail, setReasonDetail] = useState("");
  const supplemental = candidate.status === "teacher_academy";

  useEffect(() => {
    setSession(appointment);
    setConfirmStart(false);
    setConfirmUndoStart(false);
    setConfirmFail(false);
    setScores(emptyDemoScores());
    setRejectionReason("");
    setReasonDetail("");
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
    mutationFn: ({
      result,
      rejectionReason: selectedRejectionReason = "",
      reasonDetail: selectedReasonDetail = "",
    }: DemoCompletion) =>
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
            criteria_scores: demoCriteria.map((criterion) => ({
              criterion: criterion.label,
              score: Number(scores[criterion.key]),
              maximum_score: 10,
            })),
            result,
            rejection_reason: selectedRejectionReason,
            reason_detail: selectedReasonDetail,
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
  const undoStart = useMutation({
    mutationFn: () =>
      recruitmentRequest<SessionResponse>(
        `${RECRUITMENT_API}/candidates/${candidate.id}/appointments/${session.id}/undo-start`,
        {
          method: "POST",
          body: jsonBody({ expected_version: session.version }),
        },
      ),
    onSuccess: (result) => {
      onAnnouncement(
        result.message || "Demo lesson returned to its original schedule.",
      );
      void queryClient.invalidateQueries({ queryKey: ["recruitment"] });
      onClose();
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const pending = start.isPending || complete.isPending || undoStart.isPending;
  const inProgress = session.status === "in_progress";
  const numericScores = demoCriteria.map((criterion) =>
    Number(scores[criterion.key]),
  );
  const scoresValid = demoCriteria.every((criterion, index) => {
    const value = scores[criterion.key];
    const numeric = numericScores[index];
    return value !== "" && Number.isFinite(numeric) && numeric >= 0 && numeric <= 10;
  });
  const averageScore = scoresValid
    ? numericScores.reduce((total, score) => total + score, 0) /
      numericScores.length
    : null;
  const failReady =
    scoresValid &&
    (supplemental ||
      (Boolean(rejectionReason) &&
        (rejectionReason !== "other" || Boolean(reasonDetail.trim()))));

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
            <span className="text-[0.625rem] font-semibold uppercase text-muted-foreground">
              {inProgress ? "Actual start" : "Scheduled"}
            </span>
            <strong className="mt-1 block text-sm">
              {dateTimeLabel(
                inProgress ? session.started_at : session.starts_at,
              )}
            </strong>
          </div>
          <div>
            <span className="text-[0.625rem] font-semibold uppercase text-muted-foreground">
              Format
            </span>
            <strong className="mt-1 block break-words text-sm">
              {session.appointment_format || "Not set"}
            </strong>
          </div>
          {session.topic ? (
            <div className="sm:col-span-2">
              <span className="text-[0.625rem] font-semibold uppercase text-muted-foreground">
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
          <>
            <fieldset
              aria-describedby={`demo-score-help-${session.id}`}
              className="rounded-xl border border-border p-3"
            >
              <legend className="px-1 text-sm font-semibold">
                Demo lesson scores
              </legend>
              <p
                id={`demo-score-help-${session.id}`}
                className="text-xs leading-5 text-muted-foreground"
              >
                Score every criterion from 0 to 10. The final Pass or Fail
                decision remains manual.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {demoCriteria.map((criterion, index) => (
                  <label
                    key={criterion.key}
                    htmlFor={`demo-${session.id}-${criterion.key}`}
                    className={`text-xs font-semibold ${
                      index === demoCriteria.length - 1 ? "sm:col-span-2" : ""
                    }`}
                  >
                    {criterion.label}
                    <span className="ml-1 font-normal text-muted-foreground">
                      (required)
                    </span>
                    <input
                      id={`demo-${session.id}-${criterion.key}`}
                      autoFocus={index === 0}
                      type="number"
                      min={0}
                      max={10}
                      step="0.1"
                      inputMode="decimal"
                      required
                      value={scores[criterion.key]}
                      onChange={(event) =>
                        setScores((current) => ({
                          ...current,
                          [criterion.key]: event.target.value,
                        }))
                      }
                      className={`${fieldClass} mt-1`}
                    />
                  </label>
                ))}
              </div>
              <div
                aria-live="polite"
                className={`mt-3 rounded-lg px-3 py-2 text-xs font-semibold ${
                  averageScore === null
                    ? "bg-muted text-muted-foreground"
                    : "bg-primary/10 text-primary"
                }`}
              >
                {averageScore === null
                  ? "Complete all five scores to enable the decision."
                  : `Average score: ${averageScore.toFixed(1)} / 10`}
              </div>
            </fieldset>
            <label className="text-xs font-semibold">
              Evaluator notes
              <textarea
                ref={notesRef}
                className={`${fieldClass} mt-1 min-h-24`}
              />
            </label>
          </>
        )}

        {confirmFail ? (
          <div
            role="alert"
            className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          >
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
            {!supplemental ? (
              <div className="mt-3 grid gap-3 text-foreground">
                <label className="text-xs font-semibold">
                  Rejection reason
                  <select
                    autoFocus
                    required
                    value={rejectionReason}
                    onChange={(event) => {
                      setRejectionReason(event.target.value);
                      if (event.target.value !== "other") setReasonDetail("");
                    }}
                    className={`${fieldClass} mt-1`}
                  >
                    <option value="">Select a reason</option>
                    {demoFailureReasons.map((reason) => (
                      <option key={reason.value} value={reason.value}>
                        {reason.label}
                      </option>
                    ))}
                  </select>
                </label>
                {rejectionReason === "other" ? (
                  <label className="text-xs font-semibold">
                    Explanation
                    <textarea
                      required
                      value={reasonDetail}
                      onChange={(event) => setReasonDetail(event.target.value)}
                      className={`${fieldClass} mt-1 min-h-20`}
                    />
                  </label>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {confirmUndoStart ? (
          <div
            role="alert"
            className="rounded-xl border border-amber-400/50 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/20 dark:text-amber-100"
          >
            <p className="flex items-center gap-2 font-semibold">
              <RotateCcw className="h-4 w-4" />
              Cancel this demo start?
            </p>
            <p className="mt-1 text-xs leading-5">
              No result will be recorded. The demo will return to Scheduled at
              {" "}{dateTimeLabel(session.pre_start_starts_at)}, and it can be
              rescheduled normally.
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
        ) : confirmUndoStart ? (
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className={secondaryButtonClass}
              disabled={pending}
              onClick={() => setConfirmUndoStart(false)}
            >
              Keep active
            </button>
            <button
              type="button"
              className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-amber-500 bg-amber-50 px-3 text-sm font-semibold text-amber-950 transition-colors hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-amber-950/20 dark:text-amber-100"
              disabled={pending}
              onClick={() => undoStart.mutate()}
            >
              {undoStart.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              Restore schedule
            </button>
          </div>
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
              disabled={pending || !failReady}
              onClick={() =>
                complete.mutate({
                  result: "failed",
                  rejectionReason: supplemental ? "" : rejectionReason,
                  reasonDetail: supplemental ? "" : reasonDetail.trim(),
                })
              }
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
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-amber-400/60 px-3 text-sm font-semibold text-amber-800 dark:text-amber-200"
                disabled={pending || !session.can_undo_start}
                title={session.can_undo_start ? undefined : "The original schedule is unavailable."}
                onClick={() => setConfirmUndoStart(true)}
              >
                <RotateCcw className="h-4 w-4" />
                Cancel start
              </button>
              <button
                type="button"
                className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-destructive/40 px-3 text-sm font-semibold text-destructive"
                disabled={pending || !scoresValid}
                onClick={() => setConfirmFail(true)}
              >
                <XCircle className="h-4 w-4" />
                Fail
              </button>
            </div>
            <button
              type="button"
              className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-emerald-700 px-3 text-sm font-semibold text-white"
              disabled={pending || !scoresValid}
              onClick={() => complete.mutate({ result: "passed" })}
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
