import { Pencil, Trash2, X } from "lucide-react";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/shared/lib/workspace";
import { Candidate, Teacher, TRAINING_TARGET_LESSONS, statusLabels, formatCandidateEventNote, trainingMeta, criterionAverages } from "@/features/people/teachers/model";
import { StageButton } from "@/shared/ui/RecordControls";

export function CandidateDetailModal({
  candidate,
  busy,
  onClose,
  onAddEvaluation,
  onAction,
  onPromote,
  onEditEvent,
  onDeleteEvent,
}: {
  candidate: Candidate;
  busy: boolean;
  onClose: () => void;
  onAddEvaluation: () => void;
  onAction: (candidateId: number, fields: Record<string, string>, opts?: { confirmMessage?: string }) => void;
  onPromote: () => void;
  onEditEvent: (event: Record<string, unknown>) => void;
  onDeleteEvent: (eventId: number) => void;
}) {
  const id = asNumber(candidate.id);
  const name = asString(candidate.full_name) || "Candidate";
  const meta = trainingMeta(candidate);
  const perCriterion = criterionAverages(meta.history);
  const isPassed = meta.status === "training_passed";
  const isRejected = ["rejected", "withdrawn"].includes(meta.status);
  const isHired = meta.status === "hired";
  useDismissibleLayer({ onDismiss: onClose, dismissOnOutsidePointer: false });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={onClose} role="presentation">
      <div
        className="flex max-h-[90dvh] w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-detail-title"
      >
        <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 id="candidate-detail-title" className="truncate text-sm font-bold">{name}</h3>
              <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold ${
                isHired
                  ? "bg-sky-50 text-sky-700"
                  : isPassed
                    ? "bg-emerald-50 text-emerald-700"
                    : isRejected
                      ? "bg-destructive/10 text-destructive"
                      : "bg-muted text-muted-foreground"
              }`}>
                {statusLabels[meta.status] || meta.status}
              </span>
            </div>
            <p className="truncate text-xs text-muted-foreground">{asString(candidate.subject) || "Subject not set"}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <div className="rounded-lg border border-foreground/8 bg-background p-3">
            <div className="flex items-center justify-between gap-3 text-xs font-bold">
              <span>{meta.lessonCount}/{TRAINING_TARGET_LESSONS} accepted lessons</span>
              <span>{meta.average ? `${meta.average.toFixed(1)}/10 avg` : "No score yet"}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: `${meta.progress}%` }} />
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {meta.sinceLast !== null ? (
                <span className="rounded-md bg-surface px-2 py-1 text-[10px] font-semibold text-muted-foreground">
                  Last evaluated {meta.sinceLast === 0 ? "today" : `${meta.sinceLast}d ago`}
                </span>
              ) : null}
              {meta.readyToPass ? (
                <span className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">Ready to pass</span>
              ) : null}
              {meta.stale ? (
                <span className="rounded-md bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700">Stalled</span>
              ) : null}
            </div>
          </div>
          {meta.lessonCount ? (
            <div className="mt-3 rounded-lg border border-foreground/8 bg-background p-3">
              <p className="mb-2 text-xs font-bold">Criteria averages</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {perCriterion.map((item) => (
                  <div key={item.key} className="flex items-center gap-2">
                    <span className="w-10 shrink-0 text-[10px] font-bold text-muted-foreground">{item.key}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${item.avg !== null ? Math.min(100, (item.avg / 10) * 100) : 0}%` }}
                      />
                    </div>
                    <span className="w-8 shrink-0 text-right text-[10px] font-bold">{item.avg !== null ? item.avg.toFixed(1) : "—"}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          <div className="mt-3">
            <p className="mb-2 text-xs font-bold">Evaluation history</p>
            {meta.history.length ? (
              <div className="grid gap-2">
                {meta.history.map((event, index) => {
                  const note = formatCandidateEventNote(event.notes);
                  const detail = (event.detail && typeof event.detail === "object" ? event.detail : {}) as Record<string, unknown>;
                  const outcome = asString(detail.outcome);
                  return (
                    <div key={`${asNumber(event.id)}-${index}`} className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
                      <div className="flex items-center justify-between gap-2 text-[11px]">
                        <span className="flex items-center gap-1.5 font-bold text-foreground">
                          Lesson {asNumber(detail.lesson) || meta.history.length - index}
                          {outcome ? (
                            <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                              outcome === "accepted" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                            }`}>
                              {outcome === "accepted" ? "Accepted" : "Redo"}
                            </span>
                          ) : null}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-muted-foreground">
                            {event.score !== null && event.score !== undefined ? `${asString(event.score)}/10` : "—"}
                            {asString(event.created_at) ? ` · ${asString(event.created_at).slice(0, 10)}` : ""}
                          </span>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => onEditEvent(event)}
                            className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-50"
                            aria-label="Edit evaluation"
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => onDeleteEvent(asNumber(event.id))}
                            className="flex h-6 w-6 items-center justify-center rounded-md text-destructive hover:bg-destructive/10 disabled:opacity-50"
                            aria-label="Delete evaluation"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                      {asString(event.created_by) ? (
                        <p className="mt-0.5 text-[10px] text-muted-foreground">by {asString(event.created_by)}</p>
                      ) : null}
                      {note ? <p className="mt-1 whitespace-pre-wrap text-[11px] leading-4 text-muted-foreground">{note}</p> : null}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-foreground/15 bg-background px-3 py-5 text-center text-xs text-muted-foreground">
                No evaluations recorded yet.
              </p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2 border-t border-foreground/8 px-4 py-3">
          {isRejected ? (
            <>
              <StageButton
                label="Reopen Hiring"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "interview",
                      candidate_event_type: "redeem",
                      candidate_result: "reopened",
                      candidate_event_notes: "Candidate reopened for hiring review.",
                    },
                    { confirmMessage: `Reopen ${name} for hiring review?` },
                  )
                }
              />
              <StageButton
                label="Send to Practice"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "training_ready",
                      candidate_event_type: "redeem",
                      candidate_result: "reopened",
                      candidate_event_notes: "Candidate restored to practice.",
                    },
                    { confirmMessage: `Restore ${name} to practice?` },
                  )
                }
              />
            </>
          ) : isHired ? (
            <span className="text-xs font-semibold text-muted-foreground">Now an active teacher.</span>
          ) : isPassed ? (
            // Awaiting the head of department's final decision.
            <>
              <StageButton
                label="Back to Practice"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(id, {
                    candidate_status: "training_ready",
                    candidate_event_type: "review",
                    candidate_result: "returned_to_training",
                    candidate_event_notes: "Returned to practice for more lessons.",
                  })
                }
              />
              <StageButton
                label="Reject"
                tone="danger"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "rejected",
                      candidate_event_type: "final_decision",
                      candidate_result: "training_rejected",
                      candidate_event_notes: "Not approved for hire after practice.",
                    },
                    { confirmMessage: `Reject ${name} after practice?` },
                  )
                }
              />
              <StageButton label="Promote to Teacher" disabled={busy} onClick={onPromote} />
            </>
          ) : (
            <>
              <StageButton label="Add Evaluation" disabled={busy} onClick={onAddEvaluation} />
              <StageButton
                label="Mark Practice Complete"
                tone="muted"
                disabled={busy}
                onClick={() =>
                  onAction(
                    id,
                    {
                      candidate_status: "training_passed",
                      candidate_event_type: "training_complete",
                      candidate_result: "awaiting_decision",
                      candidate_event_notes: "Practice complete - sent to the head of department for a decision.",
                    },
                    { confirmMessage: `Send ${name} to the head for a final decision?` },
                  )
                }
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
