import { useState } from "react";
import { X } from "lucide-react";
import { asString } from "../../shared";
import { Teacher, teacherCategories, semesterStages, suggestedLessonRate, formatUzs } from "./shared";

export function TeacherAssignmentModal({
  state,
  isEdit,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: any;
  isEdit: boolean;
  submitting: boolean;
  error: string;
  onSubmit: (fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const {
    teacherEdit,
    props,
    teacherMode,
    setTeacherMode,
    teacherSchool,
    setTeacherSchool,
    availableSubjectSchools,
    filteredTeacherOptions,
    filteredGroupOptions,
  } = state;
  const [category, setCategory] = useState(asString(teacherEdit?.category) || "junior");
  const [semesterStage, setSemesterStage] = useState(asString(teacherEdit?.semester_stage) || "1-2");
  const [performanceScore, setPerformanceScore] = useState(asString(teacherEdit?.performance_score) || "7");
  const suggestedRate = suggestedLessonRate(category, semesterStage, performanceScore);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    onSubmit(fields);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4">
      <div className="flex max-h-[88dvh] w-full max-w-xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">{isEdit ? "Edit Teacher" : "Assign Teacher"}</h3>
            <p className="text-xs text-muted-foreground">Create or assign a teacher to a group.</p>
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

        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto px-4 py-4">
          <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
          <input type="hidden" name="teacher_mode" value={teacherMode} />

          <div className="mb-4 inline-flex rounded-lg border-2 border-foreground/10 bg-background p-0.5">
            <button
              type="button"
              onClick={() => setTeacherMode("select")}
              className={`h-8 rounded-md px-3 text-xs font-bold ${
                teacherMode === "select"
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              Existing
            </button>
            <button
              type="button"
              onClick={() => setTeacherMode("add")}
              className={`h-8 rounded-md px-3 text-xs font-bold ${
                teacherMode === "add"
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              New
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                School
              </span>
              <select
                name="teacher_assigned_school"
                value={teacherSchool}
                onChange={(event) => setTeacherSchool(event.target.value)}
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select school
                </option>
                {availableSubjectSchools.map((option: { code: string; label: string }) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Group
              </span>
              <select
                name="teacher_assigned_group"
                defaultValue={teacherEdit ? asString(teacherEdit.assigned_group) : ""}
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              >
                <option value="" disabled>
                  Select group
                </option>
                {filteredGroupOptions.map((option: { name: string }) => (
                  <option key={option.name} value={option.name}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {teacherMode === "select" ? (
              <label className="block sm:col-span-2">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Teacher
                </span>
                <select
                  name="teacher_selected_name"
                  defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                  required
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                >
                  <option value="" disabled>
                    Select from existing teachers
                  </option>
                  {filteredTeacherOptions.map((option: { name: string }) => (
                    <option key={option.name} value={option.name}>
                      {option.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Full Name
                  </span>
                  <input
                    type="text"
                    name="teacher_full_name"
                    defaultValue={teacherEdit ? asString(teacherEdit.full_name) : ""}
                    className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                  />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Pay Rate
                  </span>
                  <input
                    type="number"
                    name="teacher_pay_rate"
                    step="0.01"
                    min="0"
                    defaultValue={teacherEdit ? asString(teacherEdit.pay_rate) : ""}
                    className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                  />
                </label>
              </>
            )}
          </div>

          <div className="mt-4 border-t border-foreground/8 pt-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Rank
                </span>
                <select
                  name="teacher_category"
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
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Semester Stage
                </span>
                <select
                  name="teacher_semester_stage"
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
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Score
                </span>
                <input
                  type="number"
                  name="teacher_performance_score"
                  min="0"
                  max="10"
                  step="0.1"
                  value={performanceScore}
                  onChange={(event) => setPerformanceScore(event.target.value)}
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Supervised Lessons
                </span>
                <input
                  type="number"
                  name="teacher_supervised_lessons"
                  min="0"
                  step="1"
                  defaultValue={teacherEdit ? asString(teacherEdit.supervised_lessons) : "0"}
                  className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
              <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2.5 sm:col-span-2">
                <span className="block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Suggested Lesson Rate
                </span>
                <span className="mt-1 block text-sm font-bold">
                  {formatUzs(suggestedRate) || "Set score and rank"}
                </span>
              </div>
              <label className="block sm:col-span-3">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  IGCSE Evidence
                </span>
                <textarea
                  name="teacher_igcse_evidence"
                  rows={2}
                  defaultValue={teacherEdit ? asString(teacherEdit.igcse_evidence) : ""}
                  placeholder="Certification, Pearson Edexcel experience, exam-material evidence..."
                  className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
              <label className="block sm:col-span-3">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Promotion Notes
                </span>
                <textarea
                  name="teacher_promotion_notes"
                  rows={2}
                  defaultValue={teacherEdit ? asString(teacherEdit.promotion_notes) : ""}
                  placeholder="Approval notes from Academic Director, Head of Centre, or Subject Lead."
                  className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
                />
              </label>
            </div>
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
              {submitting ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

