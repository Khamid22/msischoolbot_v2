import { useState } from "react";
import { X } from "lucide-react";
import { asNumber, asString } from "../../shared";
import { Candidate, Teacher, teacherCategories, semesterStages, suggestedLessonRate, formatUzs, trainingMeta } from "./shared";

export function PromoteModal({
  candidate,
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  candidate: Candidate;
  state: any;
  submitting: boolean;
  error: string;
  onSubmit: (candidateId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const availableSubjectSchools: Array<{ code: string; label: string }> = state.availableSubjectSchools || [];
  const groupOptions: Array<{ name: string; school_codes: string[] }> = state.groupOptions || [];
  const [school, setSchool] = useState(availableSubjectSchools[0]?.code || "");
  const training = trainingMeta(candidate);
  const [category, setCategory] = useState("junior");
  const [semesterStage, setSemesterStage] = useState("1-2");
  const [performanceScore, setPerformanceScore] = useState(training.average ? String(training.average) : "7");
  const suggestedRate = suggestedLessonRate(category, semesterStage, performanceScore);
  const groups = groupOptions.filter(
    (group) => !school || !group.school_codes.length || group.school_codes.includes(school),
  );

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    onSubmit(asNumber(candidate.id), {
      teacher_assigned_school: school,
      teacher_assigned_group: asString(data.get("teacher_assigned_group")),
      teacher_pay_rate: asString(data.get("teacher_pay_rate")),
      teacher_category: category,
      teacher_semester_stage: semesterStage,
      teacher_performance_score: performanceScore,
      teacher_supervised_lessons: asString(data.get("teacher_supervised_lessons")),
      teacher_igcse_evidence: asString(data.get("teacher_igcse_evidence")),
      teacher_promotion_notes: asString(data.get("teacher_promotion_notes")),
    });
  }

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center bg-foreground/60 p-4">
      <div className="flex w-full max-w-md flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">Promote to Active Teacher</h3>
            <p className="text-xs text-muted-foreground">{asString(candidate.full_name)} · assign a group and rate.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-4 py-4">
          <div className="grid gap-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">School</span>
              <select
                value={school}
                onChange={(event) => setSchool(event.target.value)}
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select school
                </option>
                {availableSubjectSchools.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Group</span>
              <select
                name="teacher_assigned_group"
                required
                defaultValue=""
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select group
                </option>
                {groups.map((group) => (
                  <option key={group.name} value={group.name}>
                    {group.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pay Rate</span>
              <input
                type="number"
                name="teacher_pay_rate"
                step="0.01"
                min="0"
                defaultValue={suggestedRate || ""}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Rank</span>
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                {teacherCategories.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Semester Stage</span>
              <select
                value={semesterStage}
                onChange={(event) => setSemesterStage(event.target.value)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                {semesterStages.map((stage) => (
                  <option key={stage} value={stage}>
                    {stage}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Score</span>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={performanceScore}
                onChange={(event) => setPerformanceScore(event.target.value)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Supervised Lessons</span>
              <input
                type="number"
                name="teacher_supervised_lessons"
                min="0"
                step="1"
                defaultValue={String(training.lessonCount || 0)}
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2.5">
              <span className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Suggested Rate</span>
              <span className="mt-1 block text-sm font-bold">{formatUzs(suggestedRate)}</span>
            </div>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">IGCSE Evidence</span>
              <textarea
                name="teacher_igcse_evidence"
                rows={2}
                className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Promotion Notes</span>
              <textarea
                name="teacher_promotion_notes"
                rows={2}
                className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
          </div>
          {error ? (
            <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
          ) : null}
          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60"
            >
              {submitting ? "Promoting..." : "Promote"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

