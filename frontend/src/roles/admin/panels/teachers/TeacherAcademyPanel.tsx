import { useMemo, useState } from "react";
import { BookOpenCheck, CalendarClock, CheckCircle2, ClipboardCheck, Eye, GraduationCap, Plus, Trophy, X, XCircle } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "../../shared";
import { formatUzs, postForm, semesterStages, suggestedLessonRate, teacherCategories, ToastTone } from "./shared";

type AcademyTeacher = Record<string, unknown>;
type AcademyAssignment = Record<string, unknown>;

const TARGET_LESSONS = 12;

const focusAreas = [
  "Teacher Guidance Compliance",
  "Timing Adherence",
  "Resource Familiarity",
  "English Fluency",
  "Confidence & Delivery",
  "Engagement Technique",
  "Questioning Techniques",
  "Whole-class Example Management",
];

const rubric = [
  { code: "TGC", key: "teacher_guidance_compliance_score", remarksKey: "teacher_guidance_compliance_remarks", label: "Teacher Guidance Compliance", weight: 0.25 },
  { code: "TA", key: "timing_adherence_score", remarksKey: "timing_adherence_remarks", label: "Timing Adherence", weight: 0.2 },
  { code: "RF", key: "resource_familiarity_score", remarksKey: "resource_familiarity_remarks", label: "Resource Familiarity", weight: 0.15 },
  { code: "EF", key: "english_fluency_score", remarksKey: "english_fluency_remarks", label: "English Fluency", weight: 0.15 },
  { code: "CON", key: "confidence_delivery_score", remarksKey: "confidence_delivery_remarks", label: "Confidence & Delivery", weight: 0.1 },
  { code: "SE", key: "engagement_technique_score", remarksKey: "engagement_technique_remarks", label: "Student Engagement", weight: 0.15 },
];

function statusLabel(value: unknown) {
  const labels: Record<string, string> = {
    new_academy_teacher: "New Academy Teacher",
    in_training: "In Training",
    ready_for_evaluation: "Ready for Evaluation",
    needs_improvement: "Needs Improvement",
    ready_for_active_teacher: "Ready for Active Teacher",
    approved: "Approved",
    rejected: "Rejected",
    on_hold: "On Hold",
  };
  return labels[asString(value)] || asString(value) || "In Training";
}

function decisionLabel(value: unknown) {
  const labels: Record<string, string> = {
    passed: "Passed",
    needs_improvement: "Needs Improvement",
    reassign_lesson: "Reassign Lesson",
    ready_for_final_evaluation: "Ready for Final Evaluation",
    approved_for_active_teacher: "Approved for Active Teacher",
    rejected: "Rejected",
  };
  return labels[asString(value)] || asString(value) || "-";
}

function dateLabel(value: unknown) {
  const raw = asString(value);
  if (!raw) return "-";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw.replace("T", " ").slice(0, 16);
  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(parsed));
}

function toDateTimeLocal(value: unknown) {
  const raw = asString(value);
  if (!raw) return "";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw.slice(0, 16).replace(" ", "T");
  const date = new Date(parsed);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function teacherProgress(teacher: AcademyTeacher) {
  const progress = teacher.progress && typeof teacher.progress === "object" ? teacher.progress as Record<string, unknown> : {};
  return {
    assigned: asNumber(progress.assigned_count),
    assessed: asNumber(progress.assessed_count),
    passed: asNumber(progress.passed_count),
    target: asNumber(progress.target_lessons) || TARGET_LESSONS,
    average: progress.average_score == null ? null : Number(progress.average_score),
    latest: progress.latest_score == null ? null : Number(progress.latest_score),
    nextAssignment: progress.next_assignment && typeof progress.next_assignment === "object"
      ? progress.next_assignment as AcademyAssignment
      : null,
  };
}

function academyAssignments(teacher: AcademyTeacher) {
  return Array.isArray(teacher.assignments) ? teacher.assignments as AcademyAssignment[] : [];
}

function academyAssessments(teacher: AcademyTeacher) {
  return Array.isArray(teacher.assessments) ? teacher.assessments as Record<string, unknown>[] : [];
}

function metric(label: string, value: string | number, detail: string) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2.5">
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-[11px] text-muted-foreground">{detail}</p>
    </div>
  );
}

function NewAcademyTeacherModal({
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: any;
  submitting: boolean;
  error: string;
  onSubmit: (fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const programs = Array.isArray(state.props?.adminAcademicCurriculumPrograms)
    ? state.props.adminAcademicCurriculumPrograms as Array<Record<string, unknown>>
    : [];
  const teachers = Array.isArray(state.teachers) ? state.teachers as Array<Record<string, unknown>> : [];

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
    <ModalShell title="New Academy Teacher" subtitle="Create a trainee and assign 12 curriculum lessons." onClose={onClose}>
      <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <FieldLabel>Full Name</FieldLabel>
            <input name="academy_full_name" required className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Subject Curriculum</FieldLabel>
            <select name="academy_subject_program_id" required defaultValue="" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              <option value="" disabled>Select curriculum</option>
              {programs.map((program) => (
                <option key={asNumber(program.id)} value={asNumber(program.id)}>
                  {asString(program.subject_name)} · {asNumber(program.lesson_count)} lessons
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <FieldLabel>Telegram</FieldLabel>
            <input name="academy_telegram_username" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" placeholder="@username" />
          </label>
          <label className="block">
            <FieldLabel>Phone</FieldLabel>
            <input name="academy_phone" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Email</FieldLabel>
            <input name="academy_email" type="email" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Start Date</FieldLabel>
            <input name="academy_start_date" type="date" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Mentor</FieldLabel>
            <select name="academy_mentor_id" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" defaultValue="">
              <option value="">Not assigned</option>
              {teachers.map((teacher) => (
                <option key={asNumber(teacher.id)} value={asNumber(teacher.id)}>
                  {asString(teacher.full_name)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <FieldLabel>Department Head</FieldLabel>
            <select name="academy_department_head_id" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" defaultValue="">
              <option value="">Not assigned</option>
              {teachers.map((teacher) => (
                <option key={asNumber(teacher.id)} value={asNumber(teacher.id)}>
                  {asString(teacher.full_name)}
                </option>
              ))}
            </select>
          </label>
          <input type="hidden" name="academy_position" value="Trainee Teacher" />
          <input type="hidden" name="academy_employment_type" value="academy" />
          <label className="block sm:col-span-2">
            <FieldLabel>Notes</FieldLabel>
            <textarea name="academy_notes" rows={3} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none resize-none" />
          </label>
        </div>
        {error ? <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Create Training Pack" />
      </form>
    </ModalShell>
  );
}

function AssignmentModal({
  state,
  assignment,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: any;
  assignment: AcademyAssignment;
  submitting: boolean;
  error: string;
  onSubmit: (assignmentId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const teachers = Array.isArray(state.teachers) ? state.teachers as Array<Record<string, unknown>> : [];
  const [selectedFocus, setSelectedFocus] = useState<string[]>(
    Array.isArray(assignment.focus_areas) ? assignment.focus_areas.map(asString).filter(Boolean) : [],
  );

  function toggleFocus(value: string) {
    setSelectedFocus((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    fields.focus_areas = selectedFocus.join(",");
    onSubmit(asNumber(assignment.id), fields);
  }

  return (
    <ModalShell title="Schedule Training Lesson" subtitle={`${asString(assignment.lesson_number)} · ${asString(assignment.lesson_topic)}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <FieldLabel>Assignment Type</FieldLabel>
            <select name="assignment_type" defaultValue={asString(assignment.assignment_type) || "full_practice_lesson"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              <option value="preparation_only">Preparation only</option>
              <option value="partial_practice">Partial practice</option>
              <option value="full_practice_lesson">Full practice lesson</option>
              <option value="final_evaluation">Final evaluation</option>
              <option value="reteach_after_feedback">Reteach after feedback</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Status</FieldLabel>
            <select name="assignment_status" defaultValue={asString(assignment.status) || "assigned"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              <option value="assigned">Assigned</option>
              <option value="ready">Ready</option>
              <option value="assessed">Assessed</option>
              <option value="passed">Passed</option>
              <option value="needs_improvement">Needs improvement</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Deadline</FieldLabel>
            <input name="deadline_date" type="date" defaultValue={asString(assignment.deadline_date)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Session Date/Time</FieldLabel>
            <input name="session_datetime" type="datetime-local" defaultValue={toDateTimeLocal(assignment.session_datetime)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block sm:col-span-2">
            <FieldLabel>Evaluator</FieldLabel>
            <select name="evaluator_id" defaultValue={asString(assignment.evaluator_id)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              <option value="">Not assigned</option>
              {teachers.map((teacher) => (
                <option key={asNumber(teacher.id)} value={asNumber(teacher.id)}>
                  {asString(teacher.full_name)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div>
          <FieldLabel>Focus Areas</FieldLabel>
          <div className="mt-1 grid gap-1.5 sm:grid-cols-2">
            {focusAreas.map((area) => (
              <label key={area} className="flex items-center gap-2 rounded-lg border border-foreground/8 bg-background px-2.5 py-2 text-xs font-semibold">
                <input type="checkbox" checked={selectedFocus.includes(area)} onChange={() => toggleFocus(area)} />
                {area}
              </label>
            ))}
          </div>
        </div>
        <label className="block">
          <FieldLabel>Notes to Trainee</FieldLabel>
          <textarea name="notes_to_trainee" rows={3} defaultValue={asString(assignment.notes_to_trainee)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none resize-none" />
        </label>
        {error ? <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Save Lesson" />
      </form>
    </ModalShell>
  );
}

function AssessmentModal({
  teacher,
  assignment,
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  assignment: AcademyAssignment;
  state: any;
  submitting: boolean;
  error: string;
  onSubmit: (teacherId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const teachers = Array.isArray(state.teachers) ? state.teachers as Array<Record<string, unknown>> : [];
  const [scores, setScores] = useState<Record<string, string>>(
    Object.fromEntries(rubric.map((item) => [item.key, "7"])),
  );
  const weighted = rubric.reduce((sum, item) => {
    const value = Number(scores[item.key]);
    return sum + (Number.isFinite(value) ? value : 0) * item.weight;
  }, 0);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const decision = submitter?.value === "rejected" ? "rejected" : "passed";
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    rubric.forEach((item) => {
      fields[item.key] = scores[item.key] || "0";
      fields[item.remarksKey] = fields[item.remarksKey] || "";
    });
    fields.lesson_assignment_id = String(asNumber(assignment.id));
    fields.class_label = "";
    fields.decision = decision;
    onSubmit(asNumber(teacher.id), fields);
  }

  return (
    <ModalShell title="Assessment Report" subtitle={`${asString(teacher.full_name)} · ${asString(assignment.lesson_number)} · score ${weighted.toFixed(2)}`} onClose={onClose} wide>
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="block">
              <FieldLabel>Assessment Type</FieldLabel>
              <select name="assessment_type" defaultValue="academy_practice_lesson" className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10">
                <option value="demo_lesson">Demo lesson</option>
                <option value="academy_practice_lesson">Academy practice lesson</option>
                <option value="final_academy_evaluation">Final academy evaluation</option>
              </select>
            </label>
            <label className="block">
              <FieldLabel>Session Type</FieldLabel>
              <select name="session_type" defaultValue="training_simulation" className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10">
                <option value="training_simulation">Training simulation</option>
                <option value="practice_with_class">Practice with class</option>
                <option value="final_evaluation">Final evaluation</option>
              </select>
            </label>
            <label className="block">
              <FieldLabel>Date/Time</FieldLabel>
              <input name="assessment_datetime" type="datetime-local" defaultValue={toDateTimeLocal(assignment.session_datetime)} className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
            </label>
            <label className="block">
              <FieldLabel>Assigned Academic Director</FieldLabel>
              <select name="evaluator_id" defaultValue={asString(assignment.evaluator_id)} className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10">
                <option value="">Not assigned</option>
                {teachers.map((item) => (
                  <option key={asNumber(item.id)} value={asNumber(item.id)}>
                    {asString(item.full_name)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <section className="overflow-hidden rounded-2xl border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 bg-muted/35 px-4 py-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Marking Criteria</p>
                <p className="text-sm font-semibold text-foreground">{asString(assignment.lesson_topic) || "Training lesson"}</p>
              </div>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
                Score {weighted.toFixed(2)}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] table-fixed text-left">
                <thead>
                  <tr className="border-b border-foreground/8 bg-surface/80">
                    <th className="w-[18rem] px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Criteria</th>
                    <th className="w-32 px-3 py-2.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Score</th>
                    <th className="px-3 py-2.5 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {rubric.map((item) => (
                    <tr key={item.key} className="border-b border-foreground/6 last:border-b-0 transition-colors hover:bg-muted/35">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-9 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-xs font-black text-primary">
                            {item.code}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-bold">{item.label}</p>
                            <p className="text-[11px] font-semibold text-muted-foreground">{Math.round(item.weight * 100)}% weight</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <input
                          type="number"
                          min="1"
                          max="10"
                          step="0.1"
                          value={scores[item.key] || ""}
                          onChange={(event) => setScores((current) => ({ ...current, [item.key]: event.target.value }))}
                          className="h-10 w-full rounded-xl border border-foreground/10 bg-surface px-3 text-center text-sm font-black text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
                        />
                      </td>
                      <td className="px-3 py-3">
                        <input
                          name={item.remarksKey}
                          className="h-10 w-full rounded-xl border border-foreground/10 bg-surface px-3 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10"
                          placeholder="Remarks"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        </div>
        <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t border-foreground/8 bg-surface/95 px-4 py-3 backdrop-blur">
          <button type="button" onClick={onClose} className="inline-flex h-10 items-center justify-center rounded-xl border border-foreground/10 bg-background px-4 text-sm font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
            Cancel
          </button>
          <button type="submit" value="rejected" disabled={submitting} className="inline-flex h-10 items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/10 px-4 text-sm font-bold text-destructive transition hover:bg-destructive/15 active:scale-[0.98] disabled:opacity-60 motion-reduce:transition-none motion-reduce:active:scale-100">
            <XCircle className="h-4 w-4" />
            {submitting ? "Saving..." : "Fail"}
          </button>
          <button type="submit" value="passed" disabled={submitting} className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground shadow-sm transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] disabled:opacity-60 motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
            <CheckCircle2 className="h-4 w-4" />
            {submitting ? "Saving..." : "Success"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

function PromoteModal({
  teacher,
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  state: any;
  submitting: boolean;
  error: string;
  onSubmit: (teacherId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const [category, setCategory] = useState("junior");
  const [semesterStage, setSemesterStage] = useState("1-2");
  const [performanceScore, setPerformanceScore] = useState(String(teacherProgress(teacher).average || 7));
  const suggestedRate = suggestedLessonRate(category, semesterStage, performanceScore);
  const groups = Array.isArray(state.filteredGroupOptions) ? state.filteredGroupOptions as Array<{ name: string }> : [];

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    fields.teacher_category = category;
    fields.teacher_semester_stage = semesterStage;
    fields.teacher_performance_score = performanceScore;
    onSubmit(asNumber(teacher.id), fields);
  }

  return (
    <ModalShell title="Promote to Active Teacher" subtitle={asString(teacher.full_name)} onClose={onClose}>
      <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        <label className="block">
          <FieldLabel>Assign Real Group</FieldLabel>
          <select name="teacher_assigned_group" required className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
            <option value="" disabled>Select group</option>
            {groups.map((group) => (
              <option key={group.name} value={group.name}>{group.name}</option>
            ))}
          </select>
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <FieldLabel>Rank</FieldLabel>
            <select value={category} onChange={(event) => setCategory(event.target.value)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              {teacherCategories.map((option) => (
                <option key={option.key} value={option.key}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <FieldLabel>Semester Stage</FieldLabel>
            <select value={semesterStage} onChange={(event) => setSemesterStage(event.target.value)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              {semesterStages.map((stage) => <option key={stage} value={stage}>{stage}</option>)}
            </select>
          </label>
          <label className="block">
            <FieldLabel>Score</FieldLabel>
            <input type="number" min="0" max="10" step="0.1" value={performanceScore} onChange={(event) => setPerformanceScore(event.target.value)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
        </div>
        <label className="block">
          <FieldLabel>Pay Rate</FieldLabel>
          <input name="teacher_pay_rate" type="number" min="0" step="0.01" defaultValue={String(suggestedRate || 0)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          <span className="mt-1 block text-[11px] font-semibold text-muted-foreground">Suggested: {formatUzs(suggestedRate) || "set manually"}</span>
        </label>
        <label className="block">
          <FieldLabel>Promotion Notes</FieldLabel>
          <textarea name="teacher_promotion_notes" rows={3} defaultValue="Promoted from Teacher Academy." className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none resize-none" />
        </label>
        {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Promote" />
      </form>
    </ModalShell>
  );
}

function AcademyDetailModal({
  teacher,
  onClose,
  onPreview,
  onSchedule,
  onAssess,
  onPromote,
}: {
  teacher: AcademyTeacher;
  onClose: () => void;
  onPreview: () => void;
  onSchedule: (assignment: AcademyAssignment) => void;
  onAssess: (assignment: AcademyAssignment) => void;
  onPromote: () => void;
}) {
  const assignments = academyAssignments(teacher);
  const assessments = academyAssessments(teacher);
  const progress = teacherProgress(teacher);
  return (
    <ModalShell title={asString(teacher.full_name)} subtitle={`${asString(teacher.subject)} · ${statusLabel(teacher.academy_status)}`} onClose={onClose} wide>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <div className="grid gap-2 sm:grid-cols-4">
          {metric("Progress", `${progress.assessed}/${progress.target}`, "assessed lessons")}
          {metric("Passed", progress.passed, "lessons accepted")}
          {metric("Average", progress.average == null ? "-" : progress.average.toFixed(2), "weighted score")}
          {metric("Latest", progress.latest == null ? "-" : progress.latest.toFixed(2), "last report")}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <section>
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">12-Lesson Training Pack</p>
              <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                <button type="button" onClick={onPreview} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-3 text-xs font-bold text-primary hover:bg-primary/10">
                  <Eye className="h-3.5 w-3.5" />
                  Preview as Teacher
                </button>
                {asString(teacher.academy_status) === "ready_for_active_teacher" ? (
                  <button type="button" onClick={onPromote} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground">
                    <Trophy className="h-3.5 w-3.5" />
                    Promote
                  </button>
                ) : null}
              </div>
            </div>
            <div className="max-h-[52dvh] overflow-auto rounded-lg border border-foreground/8">
              {assignments.map((assignment) => (
                <div key={asNumber(assignment.id)} className="border-b border-foreground/6 bg-background px-3 py-2.5 last:border-b-0">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-bold">{asNumber(assignment.sequence_no)}. {asString(assignment.lesson_number)} · {asString(assignment.lesson_topic)}</p>
                      <p className="mt-0.5 text-[11px] text-muted-foreground">
                        {dateLabel(assignment.session_datetime)} · {asString(assignment.evaluator_name) || "No evaluator"} · {asString(assignment.status)}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-1.5">
                      <button type="button" onClick={() => onSchedule(assignment)} className="rounded-md border border-foreground/10 px-2 py-1 text-[11px] font-bold hover:bg-muted">Schedule</button>
                      <button type="button" onClick={() => onAssess(assignment)} className="rounded-md bg-foreground px-2 py-1 text-[11px] font-bold text-background">Assess</button>
                    </div>
                  </div>
                  {asString(assignment.specification_points) ? (
                    <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{asString(assignment.specification_points)}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </section>
          <section>
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">Assessment Reports</p>
            <div className="max-h-[52dvh] space-y-2 overflow-auto">
              {assessments.length ? assessments.slice().reverse().map((assessment) => (
                <div key={asNumber(assessment.id)} className="rounded-lg border border-foreground/8 bg-background p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold">{asString(assessment.lesson_number)} · {asString(assessment.lesson_topic)}</p>
                      <p className="text-[11px] text-muted-foreground">{dateLabel(assessment.assessment_datetime)} · {asString(assessment.evaluator_name) || "Evaluator not set"}</p>
                    </div>
                    <span className="rounded-md bg-primary/10 px-2 py-1 text-xs font-bold text-primary">{Number(assessment.weighted_overall_score || 0).toFixed(2)}</span>
                  </div>
                  <p className="mt-2 text-xs font-bold">{decisionLabel(assessment.decision)}</p>
                  <p className="mt-1 line-clamp-3 text-xs leading-5 text-muted-foreground">{asString(assessment.areas_for_improvement) || asString(assessment.final_recommendation) || "No notes."}</p>
                </div>
              )) : (
                <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-8 text-center">
                  <p className="text-sm font-bold text-muted-foreground">No assessment reports yet.</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </ModalShell>
  );
}

function ModalShell({
  title,
  subtitle,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/55 p-3 backdrop-blur-[2px] animate-in fade-in duration-150 motion-reduce:animate-none sm:p-4">
      <div className={`flex max-h-[calc(100dvh-1.5rem)] w-full flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover animate-in zoom-in-95 slide-in-from-bottom-2 duration-150 motion-reduce:animate-none ${wide ? "max-w-6xl" : "max-w-2xl"}`}>
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-bold">{title}</h3>
            {subtitle ? <p className="truncate text-xs text-muted-foreground">{subtitle}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">{children}</span>;
}

function ModalActions({ onClose, submitting, submitLabel }: { onClose: () => void; submitting: boolean; submitLabel: string }) {
  return (
    <div className="sticky bottom-0 -mx-4 mt-2 flex justify-end gap-2 border-t border-foreground/8 bg-surface px-4 py-3">
      <button type="button" onClick={onClose} className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted">
        Cancel
      </button>
      <button type="submit" disabled={submitting} className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60">
        {submitting ? "Saving..." : submitLabel}
      </button>
    </div>
  );
}

export function TeacherAcademyPanel({
  state,
  academyTeachers,
  onAcademyChange,
  onTeachersChange,
  showToast,
}: {
  state: any;
  academyTeachers: AcademyTeacher[];
  onAcademyChange: (rows: AcademyTeacher[]) => void;
  onTeachersChange: (rows: Array<Record<string, unknown>>) => void;
  showToast: (message: string, tone?: ToastTone) => void;
}) {
  const csrf = asString(state.props?.csrfToken);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailTeacher, setDetailTeacher] = useState<AcademyTeacher | null>(null);
  const [assignment, setAssignment] = useState<AcademyAssignment | null>(null);
  const [assessmentTarget, setAssessmentTarget] = useState<{ teacher: AcademyTeacher; assignment: AcademyAssignment } | null>(null);
  const [promoteTeacher, setPromoteTeacher] = useState<AcademyTeacher | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const stats = useMemo(() => {
    const inTraining = academyTeachers.filter((teacher) => ["in_training", "needs_improvement", "ready_for_evaluation"].includes(asString(teacher.academy_status))).length;
    const ready = academyTeachers.filter((teacher) => asString(teacher.academy_status) === "ready_for_active_teacher").length;
    const scores = academyTeachers
      .map((teacher) => teacherProgress(teacher).average)
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
    return {
      total: academyTeachers.length,
      inTraining,
      ready,
      average: scores.length ? scores.reduce((sum, score) => sum + score, 0) / scores.length : null,
    };
  }, [academyTeachers]);

  function applyPayload(data: Record<string, unknown>) {
    if (Array.isArray(data.academy)) {
      onAcademyChange(data.academy as AcademyTeacher[]);
      if (detailTeacher) {
        const updated = (data.academy as AcademyTeacher[]).find((teacher) => asNumber(teacher.id) === asNumber(detailTeacher.id));
        if (updated) setDetailTeacher(updated);
      }
    }
    if (Array.isArray(data.teachers)) {
      onTeachersChange(data.teachers as Array<Record<string, unknown>>);
    }
  }

  async function submit(url: string, fields: Record<string, string>, successMessage: string) {
    setSubmitting(true);
    setError("");
    const { ok, data } = await postForm(url, fields, csrf);
    setSubmitting(false);
    if (!ok) {
      const message = asString(data.message) || "Could not save.";
      setError(message);
      showToast(message, "danger");
      return false;
    }
    applyPayload(data);
    showToast(asString(data.message) || successMessage);
    return true;
  }

  const sortedTeachers = [...academyTeachers].sort((left, right) => {
    const leftReady = asString(left.academy_status) === "ready_for_active_teacher" ? 1 : 0;
    const rightReady = asString(right.academy_status) === "ready_for_active_teacher" ? 1 : 0;
    if (leftReady !== rightReady) return rightReady - leftReady;
    return asString(right.updated_at).localeCompare(asString(left.updated_at));
  });

  function previewAsTeacher(teacher: AcademyTeacher) {
    const previewKey = `academy:${asNumber(teacher.id)}`;
    if (typeof state.selectTeacherPreview === "function") {
      state.selectTeacherPreview(previewKey);
    } else {
      try {
        window.localStorage.setItem("msi_teacher_preview_key", previewKey);
        window.localStorage.removeItem("msi_teacher_preview_id");
      } catch {
      }
    }
    if (typeof state.switchAdminMode === "function") {
      state.switchAdminMode("teacher");
    }
  }

  return (
    <>
      {createOpen ? (
        <NewAcademyTeacherModal
          state={state}
          submitting={submitting}
          error={error}
          onSubmit={async (fields) => {
            if (await submit(routes.adminTeacherAcademyCreate, fields, "Academy teacher created.")) {
              setCreateOpen(false);
            }
          }}
          onClose={() => {
            setError("");
            setCreateOpen(false);
          }}
        />
      ) : null}
      {assignment ? (
        <AssignmentModal
          state={state}
          assignment={assignment}
          submitting={submitting}
          error={error}
          onSubmit={async (assignmentId, fields) => {
            if (await submit(routes.adminTeacherAcademyAssignment(assignmentId), fields, "Training lesson updated.")) {
              setAssignment(null);
            }
          }}
          onClose={() => {
            setError("");
            setAssignment(null);
          }}
        />
      ) : null}
      {assessmentTarget ? (
        <AssessmentModal
          teacher={assessmentTarget.teacher}
          assignment={assessmentTarget.assignment}
          state={state}
          submitting={submitting}
          error={error}
          onSubmit={async (teacherId, fields) => {
            if (await submit(routes.adminTeacherAcademyAssessment(teacherId), fields, "Assessment saved.")) {
              setAssessmentTarget(null);
            }
          }}
          onClose={() => {
            setError("");
            setAssessmentTarget(null);
          }}
        />
      ) : null}
      {promoteTeacher ? (
        <PromoteModal
          teacher={promoteTeacher}
          state={state}
          submitting={submitting}
          error={error}
          onSubmit={async (teacherId, fields) => {
            if (await submit(routes.adminTeacherAcademyPromote(teacherId), fields, "Teacher promoted.")) {
              setPromoteTeacher(null);
              setDetailTeacher(null);
            }
          }}
          onClose={() => {
            setError("");
            setPromoteTeacher(null);
          }}
        />
      ) : null}
      {detailTeacher ? (
        <AcademyDetailModal
          teacher={detailTeacher}
          onClose={() => setDetailTeacher(null)}
          onPreview={() => previewAsTeacher(detailTeacher)}
          onSchedule={(nextAssignment) => {
            setError("");
            setAssignment(nextAssignment);
          }}
          onAssess={(nextAssignment) => {
            setError("");
            setAssessmentTarget({ teacher: detailTeacher, assignment: nextAssignment });
          }}
          onPromote={() => {
            setError("");
            setPromoteTeacher(detailTeacher);
          }}
        />
      ) : null}

      <ChartCard
        title="Teacher Academy"
        subtitle="New teachers training on 12 curriculum-guided lessons"
        icon={<GraduationCap className="h-4 w-4 text-info" />}
        className="flex min-h-0 flex-1 flex-col"
        bodyClassName="flex min-h-0 flex-1 flex-col"
        headerActions={
          <button
            type="button"
            onClick={() => {
              setError("");
              setCreateOpen(true);
            }}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-bold text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            New Academy Teacher
          </button>
        }
      >
        <div className="mb-3 grid shrink-0 gap-2 sm:grid-cols-4">
          {metric("Academy Teachers", stats.total, "training records")}
          {metric("In Training", stats.inTraining, "active training paths")}
          {metric("Ready", stats.ready, "promotion review")}
          {metric("Avg Score", stats.average == null ? "-" : stats.average.toFixed(2), "weighted average")}
        </div>
        <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
          {sortedTeachers.length ? (
            <div className="max-h-[calc(100dvh-20rem)] overflow-auto">
              <table className="w-full min-w-[1020px] table-fixed border-collapse text-left">
                <colgroup>
                  <col className="w-[22%]" />
                  <col className="w-[12%]" />
                  <col className="w-[14%]" />
                  <col className="w-[13%]" />
                  <col className="w-[16%]" />
                  <col className="w-[11%]" />
                  <col className="w-[6%]" />
                  <col className="w-[18rem]" />
                </colgroup>
                <thead className="sticky top-0 z-10 bg-surface/95 shadow-[0_1px_0_hsl(var(--foreground)/0.08)] backdrop-blur">
                  <tr>
                    {["Teacher", "Status", "Subject", "Progress", "Next lesson", "Director", "Avg", "Actions"].map((heading) => (
                      <th
                        key={heading}
                        className="px-3 py-2.5 text-[10px] font-black uppercase tracking-wider text-muted-foreground"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-foreground/6 bg-background">
                  {sortedTeachers.map((teacher, index) => {
                    const progress = teacherProgress(teacher);
                    const nextAssignment = progress.nextAssignment || academyAssignments(teacher)[0] || null;
                    const percent = progress.target ? Math.min(100, Math.round((progress.assessed / progress.target) * 100)) : 0;
                    const status = asString(teacher.academy_status);
                    return (
                      <tr
                        key={asNumber(teacher.id)}
                        className="group animate-in fade-in slide-in-from-bottom-1 transition-colors duration-150 hover:bg-muted/35 motion-reduce:animate-none"
                        style={{ animationDelay: `${index * 35}ms` }}
                      >
                        <td className="px-3 py-3 align-middle">
                          <button type="button" onClick={() => setDetailTeacher(teacher)} className="flex min-w-0 items-center gap-2 text-left">
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-xs font-black text-primary">
                              {asString(teacher.full_name).slice(0, 1).toUpperCase() || "T"}
                            </span>
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-black text-primary group-hover:underline">{asString(teacher.full_name)}</span>
                              <span className="mt-0.5 block truncate text-[11px] font-semibold text-muted-foreground">{asString(teacher.login) || "Academy trainee"}</span>
                            </span>
                          </button>
                        </td>
                        <td className="px-3 py-3 align-middle">
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${
                            status === "ready_for_active_teacher"
                              ? "bg-success/10 text-success"
                              : status === "needs_improvement"
                                ? "bg-warning/15 text-warning"
                                : status === "rejected"
                                  ? "bg-destructive/10 text-destructive"
                                  : "bg-info/10 text-info"
                          }`}>
                            {statusLabel(teacher.academy_status)}
                          </span>
                        </td>
                        <td className="px-3 py-3 align-middle">
                          <p className="line-clamp-2 text-xs font-bold leading-snug">{asString(teacher.subject) || "Subject not set"}</p>
                        </td>
                        <td className="px-3 py-3 align-middle">
                          <div className="min-w-0">
                            <div className="mb-1 flex items-center justify-between gap-2">
                              <span className="text-[11px] font-black">{progress.assessed}/{progress.target}</span>
                              <span className="text-[10px] font-bold text-muted-foreground">{percent}%</span>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                              <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${percent}%` }} />
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-3 align-middle">
                          {nextAssignment ? (
                            <div className="min-w-0">
                              <p className="truncate text-xs font-black">{asString(nextAssignment.lesson_number) || `Lesson ${asNumber(nextAssignment.sequence_no)}`}</p>
                              <p className="line-clamp-2 text-[11px] leading-snug text-muted-foreground">{asString(nextAssignment.lesson_topic)}</p>
                            </div>
                          ) : (
                            <span className="text-xs font-semibold text-muted-foreground">No pending lesson</span>
                          )}
                        </td>
                        <td className="px-3 py-3 align-middle">
                          <p className="line-clamp-2 text-xs font-semibold leading-snug text-muted-foreground">
                            {asString(nextAssignment?.evaluator_name) || "Not assigned"}
                          </p>
                        </td>
                        <td className="px-3 py-3 align-middle">
                          <span className="text-sm font-black">{progress.average == null ? "-" : progress.average.toFixed(2)}</span>
                        </td>
                        <td className="px-3 py-3 align-middle">
                          <div className="flex flex-wrap justify-end gap-1.5">
                            <button type="button" onClick={() => previewAsTeacher(teacher)} className="inline-flex h-8 items-center gap-1 rounded-lg border border-primary/20 bg-primary/5 px-2.5 text-[11px] font-bold text-primary transition hover:bg-primary/10 active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
                              <Eye className="h-3.5 w-3.5" />
                              Preview
                            </button>
                            {nextAssignment ? (
                              <>
                                <button type="button" onClick={() => setAssignment(nextAssignment)} className="inline-flex h-8 items-center gap-1 rounded-lg border border-foreground/10 bg-background px-2.5 text-[11px] font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
                                  <CalendarClock className="h-3.5 w-3.5" />
                                  Assign
                                </button>
                                <button type="button" onClick={() => setAssessmentTarget({ teacher, assignment: nextAssignment })} className="inline-flex h-8 items-center gap-1 rounded-lg bg-foreground px-2.5 text-[11px] font-bold text-background transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                  <ClipboardCheck className="h-3.5 w-3.5" />
                                  Assess
                                </button>
                              </>
                            ) : null}
                            {status === "ready_for_active_teacher" ? (
                              <button type="button" onClick={() => setPromoteTeacher(teacher)} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-2.5 text-[11px] font-bold text-primary-foreground transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                <Trophy className="h-3.5 w-3.5" />
                                Promote
                              </button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex min-h-[22rem] flex-1 flex-col items-center justify-center px-3 py-10 text-center">
              <BookOpenCheck className="mx-auto h-5 w-5 text-muted-foreground" />
              <p className="mt-2 text-sm font-bold">No academy teachers yet.</p>
              <p className="mt-1 text-xs text-muted-foreground">Create a trainee to assign 12 curriculum lessons automatically.</p>
            </div>
          )}
        </div>
      </ChartCard>
    </>
  );
}
