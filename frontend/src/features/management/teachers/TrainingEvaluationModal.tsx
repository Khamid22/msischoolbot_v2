import { useState } from "react";
import { X } from "lucide-react";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/features/managementTypes";
import { Candidate, TRAINING_TARGET_LESSONS, trainingRubric, trainingScoreScale, trainingEvaluationEvents } from "./shared";

export function TrainingEvaluationModal({
  candidate,
  editingEvent,
  busy,
  onClose,
  onSave,
}: {
  candidate: Candidate;
  editingEvent?: Record<string, unknown> | null;
  busy: boolean;
  onClose: () => void;
  onSave: (candidateId: number, eventId: number | null, fields: Record<string, string>) => void;
}) {
  const editDetail = (editingEvent && typeof editingEvent.detail === "object" ? editingEvent.detail : {}) as Record<string, unknown>;
  const editScores = (editDetail.scores && typeof editDetail.scores === "object" ? editDetail.scores : {}) as Record<string, unknown>;
  const editComments = (editDetail.comments && typeof editDetail.comments === "object" ? editDetail.comments : {}) as Record<string, unknown>;
  const lessonNumber = editingEvent
    ? Number(editDetail.lesson) || 0
    : trainingEvaluationEvents(candidate).length + 1;
  const [scores, setScores] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      trainingRubric.map((item) => [
        item.key,
        editingEvent && editScores[item.key] !== undefined ? String(editScores[item.key]) : "7",
      ]),
    ),
  );
  const scoreValues = trainingRubric
    .map((item) => Number(scores[item.key]))
    .filter((value) => Number.isFinite(value));
  const average = scoreValues.length
    ? Math.round((scoreValues.reduce((sum, value) => sum + value, 0) / scoreValues.length) * 10) / 10
    : 0;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const outcome = asString(data.get("training_outcome")) || "accepted";
    const comments: Record<string, string> = {};
    const criteriaScores: Record<string, number> = {};
    trainingRubric.forEach((item) => {
      const numeric = Number(scores[item.key]);
      if (Number.isFinite(numeric)) {
        criteriaScores[item.key] = numeric;
      }
      const comment = asString(data.get(`comment_${item.key}`));
      if (comment) {
        comments[item.key] = comment;
      }
    });
    const detail = {
      lesson: lessonNumber,
      target: TRAINING_TARGET_LESSONS,
      date: asString(data.get("training_date")),
      evaluator: asString(data.get("training_evaluator")),
      class: asString(data.get("training_class")),
      type: asString(data.get("training_type")),
      topic: asString(data.get("training_topic")),
      outcome,
      average,
      scores: criteriaScores,
      comments,
      strengths: asString(data.get("training_strengths")),
      problems: asString(data.get("training_problems")),
      next_action: asString(data.get("training_next_action")),
    };
    const rubricText = trainingRubric
      .map((item) => {
        const comment = asString(data.get(`comment_${item.key}`));
        return `${item.key} (${item.label}): ${scores[item.key] || "-"}${comment ? ` - ${comment}` : ""}`;
      })
      .join("\n");
    const notes = [
      `Lesson: ${lessonNumber}/${TRAINING_TARGET_LESSONS}`,
      `Outcome: ${outcome === "accepted" ? "Accepted" : "Redo"}`,
      `Lesson date: ${asString(data.get("training_date")) || "-"}`,
      `Evaluator: ${asString(data.get("training_evaluator")) || "-"}`,
      `Class: ${asString(data.get("training_class")) || "-"}`,
      `Type: ${asString(data.get("training_type")) || "-"}`,
      `Topic: ${asString(data.get("training_topic")) || "-"}`,
      `Criteria:\n${rubricText}`,
      `Strengths: ${asString(data.get("training_strengths")) || "-"}`,
      `Problems: ${asString(data.get("training_problems")) || "-"}`,
      `Next action: ${asString(data.get("training_next_action")) || "-"}`,
    ].join("\n");

    const fields: Record<string, string> = {
      candidate_result: outcome,
      candidate_score: String(average),
      candidate_event_notes: notes,
      candidate_event_detail: JSON.stringify(detail),
    };
    if (!editingEvent) {
      fields.candidate_status = "training_ready";
      fields.candidate_event_type = "training_evaluation";
    }
    onSave(asNumber(candidate.id), editingEvent ? asNumber(editingEvent.id) : null, fields);
    onClose();
  }

  const panelRef = useDismissibleLayer<HTMLDivElement>({ onDismiss: onClose });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" role="presentation">
      <div ref={panelRef} className="flex max-h-[90dvh] w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover" role="dialog" aria-modal="true" aria-labelledby="training-evaluation-title">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 id="training-evaluation-title" className="text-sm font-bold">{editingEvent ? "Edit Evaluation" : "Practice Evaluation"}</h3>
            <p className="text-xs text-muted-foreground">
              {asString(candidate.full_name)} · lesson {lessonNumber}/{TRAINING_TARGET_LESSONS} · average {average.toFixed(1)}/10
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Close evaluation dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto px-4 py-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Date</span>
              <input name="training_date" type="date" defaultValue={asString(editDetail.date)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evaluator</span>
              <input name="training_evaluator" type="text" defaultValue={asString(editDetail.evaluator)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Class</span>
              <input name="training_class" type="text" defaultValue={asString(editDetail.class)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Type</span>
              <select name="training_type" defaultValue={asString(editDetail.type) || "demo"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
                <option value="demo">Demo</option>
                <option value="shadow">Shadow</option>
                <option value="trial">Trial Lesson</option>
                <option value="real_class">Real Class</option>
              </select>
            </label>
            <label className="block sm:col-span-2 lg:col-span-4">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Topic</span>
              <input name="training_topic" type="text" defaultValue={asString(editDetail.topic)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {trainingRubric.map((item) => (
              <div key={item.key} className="rounded-lg border border-foreground/8 bg-background p-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <span className="block text-[11px] font-bold text-foreground">
                      {item.key} · {item.label}
                    </span>
                    <p className="mt-0.5 text-[10px] leading-4 text-muted-foreground">{item.detail}</p>
                  </div>
                  <input
                    aria-label={`${item.label} score`}
                    type="number"
                    min="0"
                    max="10"
                    step="0.5"
                    value={scores[item.key] || ""}
                    onChange={(event) => setScores((current) => ({ ...current, [item.key]: event.target.value }))}
                    className="h-8 w-16 shrink-0 rounded-lg border border-foreground/10 bg-surface px-2 text-xs font-bold outline-none"
                  />
                </div>
                <textarea
                  name={`comment_${item.key}`}
                  rows={2}
                  defaultValue={asString(editComments[item.key])}
                  placeholder="Comment for this criterion"
                  className="mt-2 w-full resize-none rounded-lg border border-foreground/10 bg-surface px-2 py-1.5 text-xs outline-none"
                />
              </div>
            ))}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Lesson Outcome</span>
              <select name="training_outcome" defaultValue={asString(editDetail.outcome) || "accepted"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
                <option value="accepted">Accepted</option>
                <option value="redo">Redo</option>
              </select>
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Next Action</span>
              <input name="training_next_action" type="text" defaultValue={asString(editDetail.next_action)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block sm:col-span-3">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Strengths</span>
              <textarea name="training_strengths" rows={2} defaultValue={asString(editDetail.strengths)} className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
            <label className="block sm:col-span-3">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Problems</span>
              <textarea name="training_problems" rows={2} defaultValue={asString(editDetail.problems)} className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
            </label>
          </div>

          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button type="button" onClick={onClose} className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted">
              Cancel
            </button>
            <button type="submit" disabled={busy} className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60">
              {editingEvent ? "Update Evaluation" : "Save Evaluation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


export function RubricModal({ onClose }: { onClose: () => void }) {
  useDismissibleLayer({ onDismiss: onClose, dismissOnOutsidePointer: false });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" onClick={onClose} role="presentation">
      <div
        className="flex max-h-[85dvh] w-full max-w-lg flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="training-rubric-title"
      >
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 id="training-rubric-title" className="text-sm font-bold">How a trial lesson is graded</h3>
            <p className="text-xs text-muted-foreground">Each lesson is scored on six practical areas.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Close grading guide"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto px-4 py-4">
          <div className="mb-3 flex flex-wrap gap-1.5">
            {trainingScoreScale.map((step) => (
              <span key={step.score} className={`rounded-md px-2 py-1 text-[10px] font-bold ${step.tone}`}>
                {step.score} · {step.label}
              </span>
            ))}
          </div>
          <div className="grid gap-2">
            {trainingRubric.map((criteria) => (
              <div key={criteria.key} className="rounded-md border border-foreground/8 bg-background px-3 py-2">
                <p className="text-xs font-bold">
                  {criteria.key} · {criteria.label}
                </p>
                <p className="mt-0.5 text-[11px] leading-4 text-muted-foreground">{criteria.detail}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-muted-foreground">
            Trainees usually need {TRAINING_TARGET_LESSONS} lessons before a final decision. The overall lesson score is the
            average of the six areas.
          </p>
        </div>
      </div>
    </div>
  );
}
