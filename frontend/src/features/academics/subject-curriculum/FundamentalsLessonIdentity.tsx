import type { ReactNode } from "react";
import type { CurriculumLessonDraft, LessonGuidanceDocument } from "./model";

export const lessonEditorInputClass =
  "h-10 w-full rounded-lg border border-border bg-background px-3 text-sm font-semibold outline-none focus:border-primary focus:ring-2 focus:ring-primary/15";

export function LessonEditorField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label>
      <span className="mb-1 block text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {children}
      {hint ? (
        <span className="mt-1 block text-xs text-muted-foreground">{hint}</span>
      ) : null}
    </label>
  );
}

export function FundamentalsLessonIdentity({
  draft,
  onDraftChange,
}: {
  draft: CurriculumLessonDraft;
  onDraftChange: (draft: CurriculumLessonDraft) => void;
}) {
  const guidance = draft.guidance;
  const updateGuidance = (next: Partial<LessonGuidanceDocument>) => {
    onDraftChange({ ...draft, guidance: { ...guidance, ...next } });
  };

  return (
    <section className="rounded-xl border border-border bg-surface p-4 shadow-card">
      <div className="mb-4">
        <p className="text-xs font-black uppercase tracking-[0.14em] text-primary">
          Lesson identity
        </p>
        <h3 className="mt-1 text-base font-black">What will the teacher open?</h3>
      </div>
      <div className="space-y-3">
        <LessonEditorField label="Lesson title">
          <input
            required
            value={draft.title}
            onChange={(event) =>
              onDraftChange({ ...draft, title: event.target.value })
            }
            placeholder="Fundamentals I"
            className={lessonEditorInputClass}
          />
        </LessonEditorField>
        <LessonEditorField
          label="Overview"
          hint="A short explanation shown in the guidance header."
        >
          <textarea
            value={guidance.overview}
            onChange={(event) => updateGuidance({ overview: event.target.value })}
            rows={3}
            placeholder="Foundational groundwork for complete beginners..."
            className={`${lessonEditorInputClass} h-auto resize-y py-2 leading-6`}
          />
        </LessonEditorField>
        <div className="grid gap-3 sm:grid-cols-[1fr_12rem]">
          <LessonEditorField label="Tags" hint="Separate tags with commas.">
            <input
              value={guidance.tags.join(", ")}
              onChange={(event) =>
                updateGuidance({
                  tags: event.target.value
                    .split(",")
                    .map((tag) => tag.trim())
                    .filter(Boolean)
                    .slice(0, 8),
                })
              }
              placeholder="Present Simple, Complete beginners"
              className={lessonEditorInputClass}
            />
          </LessonEditorField>
          <LessonEditorField label="Total minutes">
            <input
              type="number"
              min={0}
              max={480}
              value={guidance.durationMinutes || ""}
              onChange={(event) =>
                updateGuidance({
                  durationMinutes: Number(event.target.value) || 0,
                })
              }
              placeholder="65"
              className={lessonEditorInputClass}
            />
          </LessonEditorField>
        </div>
      </div>
    </section>
  );
}
