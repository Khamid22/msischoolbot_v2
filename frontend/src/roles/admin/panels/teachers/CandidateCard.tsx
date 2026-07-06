import { useState } from "react";
import { CheckCircle2, SlidersHorizontal } from "lucide-react";
import { asNumber, asString } from "../../shared";
import { Candidate, statusLabels, candidateStatusOptions, latestCandidateEvent, formatCandidateEvent, formatCandidateEventNote } from "./shared";
import { StageButton } from "./controls";

export function CandidateCard({
  candidate,
  busy,
  onAction,
}: {
  candidate: Candidate;
  busy: boolean;
  onAction: (
    candidateId: number,
    fields: Record<string, string>,
    opts?: { confirmMessage?: string },
  ) => void;
}) {
  const status = asString(candidate.status) || "new";
  const id = asNumber(candidate.id);
  const latestEvent = latestCandidateEvent(candidate);
  const candidateName = asString(candidate.full_name) || "this candidate";
  const latestEventAuthor = latestEvent ? asString(latestEvent.created_by) : "";
  const latestEventNote = latestEvent ? formatCandidateEventNote(latestEvent.notes) : "";
  const [score, setScore] = useState("");
  const [stage, setStage] = useState(status);
  const [editingStage, setEditingStage] = useState(false);

  function advance(fields: Record<string, string>, confirmMessage?: string) {
    onAction(id, fields, confirmMessage ? { confirmMessage } : undefined);
  }

  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-foreground/8 bg-surface p-2.5 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold" title={asString(candidate.full_name)}>
            {asString(candidate.full_name)}
          </p>
          <p className="truncate text-xs text-muted-foreground">{asString(candidate.subject) || "Subject not set"}</p>
        </div>
        <div className="flex min-w-0 shrink-0 items-start gap-1">
          <span className="max-w-[5.75rem] truncate rounded-md bg-muted px-2 py-1 text-[10px] font-bold text-muted-foreground">
            {statusLabels[status] || status}
          </span>
          <button
            type="button"
            onClick={() => setEditingStage((open) => !open)}
            disabled={busy}
            aria-label="Correct stage"
            title="Correct stage"
            className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-50"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {(asString(candidate.phone) || asString(candidate.telegram_username) || asString(candidate.source)) ? (
        <div className="mt-2 grid gap-0.5 text-[11px] leading-4 text-muted-foreground">
          {asString(candidate.phone) ? <span>{asString(candidate.phone)}</span> : null}
          {asString(candidate.telegram_username) ? <span>{asString(candidate.telegram_username)}</span> : null}
          {asString(candidate.source) ? <span>Source: {asString(candidate.source)}</span> : null}
        </div>
      ) : null}

      {latestEvent ? (
        <div className="mt-2 rounded-md bg-background px-2.5 py-1.5 text-[11px] text-muted-foreground">
          <span className="font-bold text-foreground">{formatCandidateEvent(latestEvent.result)}</span>
          {latestEventAuthor ? <span> · by {latestEventAuthor}</span> : null}
          {latestEvent.score !== null && latestEvent.score !== undefined ? (
            <span> · Score {asString(latestEvent.score)}</span>
          ) : null}
          {latestEventNote ? <p className="mt-1 leading-4">{latestEventNote}</p> : null}
        </div>
      ) : null}

      {editingStage ? (
        <div className="mt-3 rounded-lg border border-foreground/8 bg-background p-2">
          <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
            Correct Stage
          </span>
          <div className="grid grid-cols-[minmax(0,1fr)_4.5rem] gap-2">
            <select
              value={stage}
              onChange={(event) => setStage(event.target.value)}
              className="h-8 rounded-lg border border-foreground/10 bg-surface px-2 text-xs font-semibold outline-none"
            >
              {candidateStatusOptions.map((option) => (
                <option key={option} value={option}>
                  {statusLabels[option] || option}
                </option>
              ))}
            </select>
            <StageButton
              label="Set"
              tone="muted"
              disabled={busy}
              onClick={() => {
                setEditingStage(false);
                advance({
                  candidate_status: stage,
                  candidate_event_type: "manual_correction",
                  candidate_result: "stage_corrected",
                  candidate_event_notes: `Stage manually set to ${statusLabels[stage] || stage}.`,
                });
              }}
            />
          </div>
        </div>
      ) : null}

      <div className="mt-2.5 grid gap-2">
        {status === "new" ? (
          <StageButton
            label="Move to Interview"
            disabled={busy}
            onClick={() =>
              advance({
                candidate_status: "interview",
                candidate_event_type: "interview",
                candidate_result: "scheduled",
              })
            }
          />
        ) : null}

        {status === "interview" ? (
          <div className="grid grid-cols-2 gap-2">
            <StageButton
              label="Pass"
              disabled={busy}
              onClick={() =>
                advance({
                  candidate_status: "math_test",
                  candidate_event_type: "interview",
                  candidate_result: "passed",
                })
              }
            />
            <StageButton
              label="Reject"
              tone="danger"
              disabled={busy}
              onClick={() =>
                advance(
                  {
                    candidate_status: "rejected",
                    candidate_event_type: "interview",
                    candidate_result: "rejected",
                  },
                  `Reject ${candidateName}?`,
                )
              }
            />
          </div>
        ) : null}

        {status === "math_test" ? (
          <div className="grid gap-2">
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={score}
              onChange={(event) => setScore(event.target.value)}
              placeholder="Test score (optional)"
              className="h-8 min-w-0 rounded-lg border border-foreground/10 bg-surface px-2 text-xs outline-none"
            />
            <div className="grid grid-cols-2 gap-2">
              <StageButton
                label="Pass Test"
                disabled={busy}
                onClick={() =>
                  advance({
                    candidate_status: "training_ready",
                    candidate_event_type: "math_test",
                    candidate_result: "passed",
                    candidate_score: score,
                  })
                }
              />
              <StageButton
                label="Reject"
                tone="danger"
                disabled={busy}
                onClick={() =>
                  advance(
                    {
                      candidate_status: "rejected",
                      candidate_event_type: "math_test",
                      candidate_result: "rejected",
                      candidate_score: score,
                    },
                    `Reject ${candidateName}?`,
                  )
                }
              />
            </div>
          </div>
        ) : null}

        {status === "training_ready" ? (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Ready for practice
          </div>
        ) : null}
      </div>
    </div>
  );
}
