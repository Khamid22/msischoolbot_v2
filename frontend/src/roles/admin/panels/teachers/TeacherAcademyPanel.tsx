import { useMemo, useState } from "react";
import { BookOpenCheck, CalendarClock, CheckCircle2, ClipboardCheck, Copy, Eye, GraduationCap, Plus, Trophy, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "../../shared";
import { formatUzs, postForm, semesterStages, suggestedLessonRate, teacherCategories, ToastTone } from "./shared";

type AcademyTeacher = Record<string, unknown>;
type AcademyAssignment = Record<string, unknown>;
type GeneratedCredentials = Record<string, unknown>;

const focusAreas = [
  "Teacher Guidance",
  "Timing",
  "Resource Familiarity",
  "English Fluency",
  "Confidence",
  "Student Engagement",
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
  const assigned = asNumber(progress.assigned_count) || academyAssignments(teacher).length;
  return {
    assigned,
    assessed: asNumber(progress.assessed_count),
    passed: asNumber(progress.passed_count),
    // The progress target always equals the number of selected assigned
    // lessons — never a fixed 12-lesson pack.
    target: asNumber(progress.target_lessons) || assigned,
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

function assignmentTitle(assignment: AcademyAssignment) {
  const sequence = asNumber(assignment.sequence_no);
  const lessonNumber = asString(assignment.lesson_number) || (sequence ? `Lesson ${sequence}` : "Lesson");
  const topic = asString(assignment.lesson_topic);
  return topic ? `${lessonNumber} · ${topic}` : lessonNumber;
}

function assignmentIsScheduled(assignment: AcademyAssignment | null | undefined) {
  return Boolean(asString(assignment?.session_datetime));
}

function nextAcademyAssignment(teacher: AcademyTeacher) {
  const progress = teacherProgress(teacher);
  const assignments = academyAssignments(teacher);
  const assessedAssignmentIds = new Set(academyAssessments(teacher).map((assessment) => asNumber(assessment.lesson_assignment_id)).filter(Boolean));
  return (
    progress.nextAssignment ||
    assignments.find((assignment) => {
      const status = asString(assignment.status);
      return !assessedAssignmentIds.has(asNumber(assignment.id)) && !["assessed", "passed", "cancelled"].includes(status);
    }) ||
    null
  );
}

function assignmentById(assignments: AcademyAssignment[], assignmentId: number) {
  return assignments.find((item) => asNumber(item.id) === assignmentId) || assignments[0] || null;
}

function subjectOptionsFromState(state: any) {
  const subjects = Array.isArray(state.props?.adminAcademicSubjects)
    ? state.props.adminAcademicSubjects as Array<Record<string, unknown>>
    : [];
  const programs = Array.isArray(state.props?.adminAcademicCurriculumPrograms)
    ? state.props.adminAcademicCurriculumPrograms as Array<Record<string, unknown>>
    : [];
  const byId = new Map<number, string>();
  subjects.forEach((subject) => {
    const id = asNumber(subject.id || subject.subject_id || subject.subjectId);
    const label = asString(subject.name || subject.subject_name || subject.subjectName || subject.subject);
    if (id && label) byId.set(id, label);
  });
  programs.forEach((program) => {
    const id = asNumber(program.subject_id || program.subjectId);
    const label = asString(program.subject_name || program.subjectName || program.subject);
    if (id && label && !byId.has(id)) byId.set(id, label);
  });
  return Array.from(byId.entries())
    .map(([id, label]) => ({ id, label }))
    .sort((left, right) => left.label.localeCompare(right.label));
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

type AnalyticsRow = {
  label: string;
  value: number;
  detail: string;
};

function MiniAnalyticsCard({
  title,
  subtitle,
  rows,
  emptyLabel,
}: {
  title: string;
  subtitle: string;
  rows: AnalyticsRow[];
  emptyLabel: string;
}) {
  return (
    <section className="rounded-xl border border-foreground/8 bg-background px-3 py-3">
      <div className="mb-3">
        <p className="text-xs font-black text-foreground">{title}</p>
        <p className="mt-0.5 text-[11px] font-semibold text-muted-foreground">{subtitle}</p>
      </div>
      {rows.length ? (
        <div className="space-y-2.5">
          {rows.slice(0, 6).map((row) => (
            <div key={row.label}>
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="truncate text-[11px] font-bold text-foreground">{row.label}</span>
                <span className="shrink-0 text-[11px] font-black text-muted-foreground">{row.detail}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${Math.max(0, Math.min(100, row.value))}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-6 text-center text-xs font-semibold text-muted-foreground">
          {emptyLabel}
        </p>
      )}
    </section>
  );
}

function academyAnalyticsRows(academyTeachers: AcademyTeacher[]) {
  const total = academyTeachers.length;
  const statusGroups = [
    {
      label: "In training",
      count: academyTeachers.filter((teacher) =>
        ["new_academy_teacher", "in_training", "ready_for_evaluation"].includes(asString(teacher.academy_status)),
      ).length,
    },
    {
      label: "Ready",
      count: academyTeachers.filter((teacher) => asString(teacher.academy_status) === "ready_for_active_teacher").length,
    },
    {
      label: "Completed",
      count: academyTeachers.filter((teacher) => ["approved", "approved_for_active_teacher"].includes(asString(teacher.academy_status))).length,
    },
    {
      label: "Needs support",
      count: academyTeachers.filter((teacher) => ["needs_improvement", "rejected", "on_hold"].includes(asString(teacher.academy_status))).length,
    },
  ];
  const statusRows = statusGroups
    .filter((item) => item.count > 0)
    .map((item) => ({
      label: item.label,
      value: total ? Math.round((item.count / total) * 100) : 0,
      detail: String(item.count),
    }));

  const scoreBySubject = new Map<string, { sum: number; count: number }>();
  const completionBySubject = new Map<string, { sum: number; count: number }>();
  academyTeachers.forEach((teacher) => {
    const subject = asString(teacher.subject) || "Subject not set";
    const progress = teacherProgress(teacher);
    if (progress.average != null && Number.isFinite(progress.average)) {
      const bucket = scoreBySubject.get(subject) || { sum: 0, count: 0 };
      bucket.sum += progress.average;
      bucket.count += 1;
      scoreBySubject.set(subject, bucket);
    }
    if (progress.target > 0) {
      const bucket = completionBySubject.get(subject) || { sum: 0, count: 0 };
      bucket.sum += Math.min(100, Math.round((progress.assessed / progress.target) * 100));
      bucket.count += 1;
      completionBySubject.set(subject, bucket);
    }
  });
  const subjectScoreRows = Array.from(scoreBySubject.entries())
    .map(([label, bucket]) => {
      const score = bucket.sum / bucket.count;
      return { label, value: score * 10, detail: score.toFixed(1) };
    })
    .sort((left, right) => right.value - left.value);
  const completionRows = Array.from(completionBySubject.entries())
    .map(([label, bucket]) => {
      const percent = Math.round(bucket.sum / bucket.count);
      return { label, value: percent, detail: `${percent}%` };
    })
    .sort((left, right) => right.value - left.value);

  const assessmentRows = academyTeachers
    .flatMap((teacher) =>
      academyAssessments(teacher).map((assessment) => ({
        teacherName: asString(teacher.full_name) || "Teacher",
        lesson: asString(assessment.lesson_number) || "Lesson",
        score: asNumber(assessment.weighted_overall_score),
        date: asString(assessment.assessment_datetime || assessment.created_at || assessment.updated_at),
      })),
    )
    .filter((item) => item.score > 0)
    .sort((left, right) => Date.parse(right.date || "") - Date.parse(left.date || ""))
    .slice(0, 6)
    .reverse()
    .map((item) => ({
      label: `${item.teacherName} · ${item.lesson}`,
      value: item.score * 10,
      detail: item.score.toFixed(1),
    }));

  return {
    statusRows,
    subjectScoreRows,
    completionRows,
    assessmentRows,
  };
}

function NewHeadOfDepartmentModal({
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
  const subjects = subjectOptionsFromState(state);

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
    <ModalShell title="New Head of Department" subtitle="Create subject-scoped Teacher Academy access." onClose={onClose}>
      <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        <label className="block">
          <FieldLabel>Display Name</FieldLabel>
          <input name="hod_display_name" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" placeholder="Head of Math Department" />
        </label>
        <label className="block">
          <FieldLabel>Subject Scope</FieldLabel>
          <select name="hod_subject_id" required defaultValue="" className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
            <option value="" disabled>Select subject</option>
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.label}
              </option>
            ))}
          </select>
        </label>
        <div className="rounded-lg border border-primary/10 bg-primary/5 px-3 py-2 text-xs font-semibold text-primary">
          Login and temporary password will be generated automatically in HOD0001 format.
        </div>
        {error ? <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Create HOD" />
      </form>
    </ModalShell>
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
  const curriculumItems = Array.isArray(state.props?.adminAcademicCurriculumItems)
    ? state.props.adminAcademicCurriculumItems as Array<Record<string, unknown>>
    : [];
  const teachers = Array.isArray(state.teachers) ? state.teachers as Array<Record<string, unknown>> : [];
  const [selectedProgramId, setSelectedProgramId] = useState("");
  const [selectedLessonIds, setSelectedLessonIds] = useState<number[]>([]);
  const [lessonSearch, setLessonSearch] = useState("");
  const [localError, setLocalError] = useState("");

  const selectedProgramLessons = useMemo(
    () =>
      curriculumItems
        .filter((item) => {
          const itemProgramId = asNumber(item.program_id || item.programId);
          const itemType = asString(item.item_type || item.itemType).toLowerCase();
          return itemProgramId === asNumber(selectedProgramId) && itemType === "lesson";
        })
        .sort((left, right) => asNumber(left.item_order || left.itemOrder) - asNumber(right.item_order || right.itemOrder)),
    [curriculumItems, selectedProgramId],
  );
  const filteredProgramLessons = useMemo(() => {
    const query = lessonSearch.trim().toLowerCase();
    if (!query) return selectedProgramLessons;
    return selectedProgramLessons.filter((lesson) =>
      [
        lesson.lesson_number,
        lesson.lessonNumber,
        lesson.title,
        lesson.specification_points,
        lesson.book_pages,
      ]
        .map(asString)
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [lessonSearch, selectedProgramLessons]);

  function handleProgramChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedProgramId(event.target.value);
    setSelectedLessonIds([]);
    setLessonSearch("");
    setLocalError("");
  }

  function toggleLesson(lessonId: number) {
    setLocalError("");
    setSelectedLessonIds((current) =>
      current.includes(lessonId)
        ? current.filter((selectedId) => selectedId !== lessonId)
        : [...current, lessonId],
    );
  }

  function selectAllVisibleLessons() {
    setLocalError("");
    setSelectedLessonIds(filteredProgramLessons.map((lesson) => asNumber(lesson.id)).filter(Boolean));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedLessonIds.length) {
      setLocalError("Select at least 1 Teacher Academy lesson.");
      return;
    }
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    fields.academy_curriculum_item_ids = selectedLessonIds.join(",");
    onSubmit(fields);
  }

  return (
    <ModalShell title="New Academy Teacher" subtitle="Create a trainee and assign selected curriculum lessons." onClose={onClose}>
      <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <FieldLabel>Full Name</FieldLabel>
            <input name="academy_full_name" required className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Subject Curriculum</FieldLabel>
            <select name="academy_subject_program_id" required value={selectedProgramId} onChange={handleProgramChange} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
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
        <section className="rounded-xl border border-foreground/10 bg-background p-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-wide text-foreground">Select Teacher Academy lessons</p>
              <p className="mt-1 text-xs font-semibold text-muted-foreground">Selected {selectedLessonIds.length} lessons</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={selectAllVisibleLessons}
                disabled={!filteredProgramLessons.length}
                className="rounded-lg border border-foreground/10 px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-50"
              >
                Select visible
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedLessonIds([]);
                  setLocalError("");
                }}
                className="rounded-lg border border-foreground/10 px-3 py-1.5 text-xs font-bold hover:bg-muted"
              >
                Clear selection
              </button>
            </div>
          </div>
          <input type="hidden" name="academy_curriculum_item_ids" value={selectedLessonIds.join(",")} />
          <input
            type="search"
            value={lessonSearch}
            onChange={(event) => setLessonSearch(event.target.value)}
            className="mt-3 w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-sm outline-none"
            placeholder="Search lessons or topics"
            disabled={!selectedProgramId}
          />
          <div className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
            {!selectedProgramId ? (
              <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-6 text-center text-sm font-semibold text-muted-foreground">
                Select a subject curriculum to choose lessons.
              </p>
            ) : filteredProgramLessons.length ? (
              filteredProgramLessons.map((lesson) => {
                const lessonId = asNumber(lesson.id);
                const checked = selectedLessonIds.includes(lessonId);
                return (
                  <label
                    key={lessonId}
                    className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors ${
                      checked ? "border-primary/30 bg-primary/5" : "border-foreground/10 bg-surface hover:bg-muted"
                    }`}
                  >
                    <input
                      type="checkbox"
                      name="academy_curriculum_item_ids"
                      value={lessonId}
                      checked={checked}
                      onChange={() => toggleLesson(lessonId)}
                      className="mt-1 h-4 w-4 shrink-0 rounded border-foreground/20"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-black text-foreground">
                        {asString(lesson.lesson_number) || `Lesson ${asNumber(lesson.item_order)}`} · {asString(lesson.title) || "Untitled lesson"}
                      </span>
                      <span className="mt-1 line-clamp-2 block text-xs leading-5 text-muted-foreground">
                        {asString(lesson.specification_points) || asString(lesson.book_pages) || "No lesson details yet."}
                      </span>
                    </span>
                  </label>
                );
              })
            ) : (
              <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-6 text-center text-sm font-semibold text-muted-foreground">
                No lesson topics found for this curriculum.
              </p>
            )}
          </div>
        </section>
        {localError || error ? <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{localError || error}</p> : null}
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Create Academy Teacher" disabled={!selectedLessonIds.length} />
      </form>
    </ModalShell>
  );
}

function AssignmentModal({
  state,
  teacher,
  assignment,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: any;
  teacher: AcademyTeacher;
  assignment: AcademyAssignment;
  submitting: boolean;
  error: string;
  onSubmit: (assignmentId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const teachers = Array.isArray(state.teachers) ? state.teachers as Array<Record<string, unknown>> : [];
  const assignments = academyAssignments(teacher);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState(asNumber(assignment.id) || asNumber(assignments[0]?.id));
  const selectedAssignment = assignmentById(assignments, selectedAssignmentId);
  const [selectedFocus, setSelectedFocus] = useState<string[]>(
    Array.isArray(selectedAssignment?.focus_areas) ? selectedAssignment.focus_areas.map(asString).filter(Boolean) : [],
  );

  function handleAssignmentChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const nextAssignment = assignmentById(assignments, asNumber(event.target.value));
    setSelectedAssignmentId(asNumber(nextAssignment?.id));
    setSelectedFocus(
      Array.isArray(nextAssignment?.focus_areas)
        ? nextAssignment.focus_areas.map(asString).filter(Boolean)
        : [],
    );
  }

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
    fields.assignment_id = String(asNumber(selectedAssignment?.id));
    onSubmit(asNumber(selectedAssignment?.id), fields);
  }

  return (
    <ModalShell title="Schedule Training Lesson" subtitle={selectedAssignment ? assignmentTitle(selectedAssignment) : "Choose an academy lesson"} onClose={onClose}>
      <form onSubmit={handleSubmit} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        <div className="grid gap-2 rounded-xl border border-primary/10 bg-primary/5 p-3 sm:grid-cols-2">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher name</p>
            <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Subject</p>
            <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.subject) || "Subject not set"}</p>
          </div>
        </div>
        <label className="block">
          <FieldLabel>Lesson Assignment</FieldLabel>
          <select
            name="assignment_id"
            required
            value={selectedAssignmentId || ""}
            onChange={handleAssignmentChange}
            className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm font-semibold outline-none"
          >
            <option value="" disabled>Select lesson assignment</option>
            {assignments.map((item) => (
              <option key={asNumber(item.id)} value={asNumber(item.id)}>
                {assignmentTitle(item)}
              </option>
            ))}
          </select>
          {!assignments.length ? (
            <span className="mt-2 block rounded-lg border border-dashed border-foreground/15 px-3 py-3 text-sm font-semibold text-muted-foreground">
              No academy lessons assigned.
            </span>
          ) : null}
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <FieldLabel>Lesson Type</FieldLabel>
            <select key={`type-${selectedAssignmentId}`} name="assignment_type" defaultValue={asString(selectedAssignment?.assignment_type) || "full_practice_lesson"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              <option value="full_practice_lesson">Practice Lesson</option>
              <option value="demo_lesson">Demo Lesson</option>
              <option value="observation">Observation</option>
              <option value="final_evaluation">Final Evaluation</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Status</FieldLabel>
            <select key={`status-${selectedAssignmentId}`} name="assignment_status" defaultValue={asString(selectedAssignment?.status) || "assigned"} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
              <option value="assigned">Assigned</option>
              <option value="ready">Ready</option>
              <option value="assessed">Assessed</option>
              <option value="passed">Passed</option>
              <option value="needs_improvement">Needs improvement</option>
            </select>
          </label>
          <label className="block">
            <FieldLabel>Deadline</FieldLabel>
            <input key={`deadline-${selectedAssignmentId}`} name="deadline_date" type="date" defaultValue={asString(selectedAssignment?.deadline_date)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block">
            <FieldLabel>Session Date/Time</FieldLabel>
            <input key={`session-${selectedAssignmentId}`} name="session_datetime" type="datetime-local" defaultValue={toDateTimeLocal(selectedAssignment?.session_datetime)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none" />
          </label>
          <label className="block sm:col-span-2">
            <FieldLabel>Evaluator</FieldLabel>
            <select key={`evaluator-${selectedAssignmentId}`} name="evaluator_id" defaultValue={asString(selectedAssignment?.evaluator_id)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none">
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
          <textarea key={`notes-${selectedAssignmentId}`} name="notes_to_trainee" rows={3} defaultValue={asString(selectedAssignment?.notes_to_trainee)} className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none resize-none" />
        </label>
        {error ? <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Save Schedule" disabled={!selectedAssignment} />
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
  const assignments = academyAssignments(teacher);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState(asNumber(assignment.id) || asNumber(assignments[0]?.id));
  const selectedAssignment = assignmentById(assignments, selectedAssignmentId);
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
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    rubric.forEach((item) => {
      fields[item.key] = scores[item.key] || "0";
      fields[item.remarksKey] = fields[item.remarksKey] || "";
    });
    fields.lesson_assignment_id = String(asNumber(selectedAssignment?.id));
    fields.decision = fields.decision || "passed";
    onSubmit(asNumber(teacher.id), fields);
  }

  return (
    <ModalShell title="Assessment Report" subtitle={`${asString(teacher.full_name)} · ${selectedAssignment ? assignmentTitle(selectedAssignment) : "Choose lesson"} · score ${weighted.toFixed(2)}`} onClose={onClose} wide>
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
          <div className="grid gap-2 rounded-xl border border-primary/10 bg-primary/5 p-3 sm:grid-cols-2">
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher name</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Subject</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.subject) || "Subject not set"}</p>
            </div>
          </div>
          <label className="block">
            <FieldLabel>Lesson Assignment</FieldLabel>
            <select
              name="lesson_assignment_id"
              required
              value={selectedAssignmentId || ""}
              onChange={(event) => setSelectedAssignmentId(asNumber(event.target.value))}
              className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
            >
              <option value="" disabled>Select lesson assignment</option>
              {assignments.map((item) => (
                <option key={asNumber(item.id)} value={asNumber(item.id)}>
                  {assignmentTitle(item)}
                </option>
              ))}
            </select>
            {!assignments.length ? (
              <span className="mt-2 block rounded-lg border border-dashed border-foreground/15 px-3 py-3 text-sm font-semibold text-muted-foreground">
                No academy lessons assigned.
              </span>
            ) : null}
          </label>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
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
              <input key={`assessment-date-${selectedAssignmentId}`} name="assessment_datetime" type="datetime-local" defaultValue={toDateTimeLocal(selectedAssignment?.session_datetime)} className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
            </label>
            <label className="block">
              <FieldLabel>Assigned Academic Director</FieldLabel>
              <select key={`assessment-evaluator-${selectedAssignmentId}`} name="evaluator_id" defaultValue={asString(selectedAssignment?.evaluator_id)} className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10">
                <option value="">Not assigned</option>
                {teachers.map((item) => (
                  <option key={asNumber(item.id)} value={asNumber(item.id)}>
                    {asString(item.full_name)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <FieldLabel>Class Label</FieldLabel>
              <input name="class_label" placeholder="Group or demo class" className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10" />
            </label>
            <label className="block">
              <FieldLabel>Decision</FieldLabel>
              <select name="decision" defaultValue="passed" className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10">
                <option value="needs_improvement">Needs improvement</option>
                <option value="passed">Passed</option>
                <option value="ready_for_final_evaluation">Ready for final evaluation</option>
                <option value="approved_for_active_teacher">Approved for active teacher</option>
              </select>
            </label>
          </div>

          <section className="overflow-hidden rounded-2xl border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 bg-muted/35 px-4 py-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Marking Criteria</p>
                <p className="text-sm font-semibold text-foreground">{selectedAssignment ? assignmentTitle(selectedAssignment) : "Training lesson"}</p>
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
          <div className="grid gap-3 lg:grid-cols-3">
            <label className="block">
              <FieldLabel>Strengths</FieldLabel>
              <textarea name="strengths" rows={4} className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2.5 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none" placeholder="What went well?" />
            </label>
            <label className="block">
              <FieldLabel>Areas for Improvement</FieldLabel>
              <textarea name="areas_for_improvement" rows={4} className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2.5 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none" placeholder="What should improve next?" />
            </label>
            <label className="block">
              <FieldLabel>Final Recommendation</FieldLabel>
              <textarea name="final_recommendation" rows={4} className="w-full rounded-xl border border-foreground/10 bg-background px-3 py-2.5 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10 resize-none" placeholder="Final academic department note" />
            </label>
          </div>
          {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        </div>
        <div className="sticky bottom-0 flex flex-wrap justify-end gap-2 border-t border-foreground/8 bg-surface/95 px-4 py-3 backdrop-blur">
          <button type="button" onClick={onClose} className="inline-flex h-10 items-center justify-center rounded-xl border border-foreground/10 bg-background px-4 text-sm font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
            Cancel
          </button>
          <button type="submit" disabled={submitting || !selectedAssignment} className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground shadow-sm transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] disabled:opacity-60 motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
            <CheckCircle2 className="h-4 w-4" />
            {submitting ? "Saving..." : "Save assessment"}
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
  allowTeacherPreview,
}: {
  teacher: AcademyTeacher;
  onClose: () => void;
  onPreview: () => void;
  onSchedule: (assignment: AcademyAssignment) => void;
  onAssess: (assignment: AcademyAssignment) => void;
  onPromote: () => void;
  allowTeacherPreview: boolean;
}) {
  const assignments = academyAssignments(teacher);
  const assessments = academyAssessments(teacher);
  const progress = teacherProgress(teacher);
  const login = asString(teacher.login);
  return (
    <ModalShell title={asString(teacher.full_name)} subtitle={`${asString(teacher.subject)} · ${statusLabel(teacher.academy_status)}`} onClose={onClose} wide>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <div className="grid gap-2 sm:grid-cols-4">
          {metric("Progress", `${progress.assessed}/${progress.target}`, "assessed lessons")}
          {metric("Passed", progress.passed, "lessons accepted")}
          {metric("Average", progress.average == null ? "-" : progress.average.toFixed(2), "weighted score")}
          {metric("Latest", progress.latest == null ? "-" : progress.latest.toFixed(2), "last report")}
        </div>
        <div className="mt-3 grid gap-2 rounded-xl border border-primary/10 bg-primary/5 p-3 sm:grid-cols-[1fr_1fr_auto]">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher account login</p>
            <p className="mt-1 truncate font-mono text-sm font-black text-foreground">{login || "Account not created yet"}</p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Default password</p>
            <p className="mt-1 truncate font-mono text-sm font-black text-foreground">{login || "Account not created yet"}</p>
          </div>
          <div className="flex items-center rounded-lg bg-background px-3 py-2 text-[11px] font-bold text-muted-foreground">
            Default password equals login.
          </div>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <section>
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Selected Academy Lessons</p>
              <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                {allowTeacherPreview ? (
                  <button type="button" onClick={onPreview} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-3 text-xs font-bold text-primary hover:bg-primary/10">
                    <Eye className="h-3.5 w-3.5" />
                    Preview as Teacher
                  </button>
                ) : null}
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

function AcademyTeacherCard({
  teacher,
  allowTeacherPreview,
  onPreview,
  onDetail,
  onSchedule,
  onAssess,
  onPromote,
  onCopyLogin,
}: {
  teacher: AcademyTeacher;
  allowTeacherPreview: boolean;
  onPreview: () => void;
  onDetail: () => void;
  onSchedule: (assignment: AcademyAssignment) => void;
  onAssess: (assignment: AcademyAssignment) => void;
  onPromote: () => void;
  onCopyLogin: (login: string) => void;
}) {
  const assignments = academyAssignments(teacher);
  const progress = teacherProgress(teacher);
  const nextAssignment = nextAcademyAssignment(teacher);
  const login = asString(teacher.login);
  const status = asString(teacher.academy_status);
  const percent = progress.target ? Math.min(100, Math.round((progress.assessed / progress.target) * 100)) : 0;
  const scheduled = assignmentIsScheduled(nextAssignment);

  return (
    <article className="rounded-2xl border border-foreground/10 bg-background p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <button type="button" onClick={onDetail} className="min-w-0 flex-1 text-left">
          <h3 className="line-clamp-2 text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</h3>
          <p className="mt-1 line-clamp-1 text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
        </button>
        <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-black uppercase tracking-wide ${
          status === "ready_for_active_teacher"
            ? "bg-success/10 text-success"
            : status === "needs_improvement"
              ? "bg-warning/15 text-warning"
              : status === "rejected"
                ? "bg-destructive/10 text-destructive"
                : "bg-info/10 text-info"
        }`}>
          {statusLabel(status)}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-xl bg-muted/45 px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Progress</p>
          <p className="mt-1 text-sm font-black">{progress.assessed}/{progress.target}</p>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-background">
            <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
          </div>
        </div>
        <div className="rounded-xl bg-muted/45 px-3 py-2">
          <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Average Score</p>
          <p className="mt-1 text-sm font-black">{progress.average == null ? "-" : progress.average.toFixed(2)}</p>
          <p className="mt-1 text-[11px] font-semibold text-muted-foreground">{progress.latest == null ? "No latest score" : `Latest ${progress.latest.toFixed(2)}`}</p>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-foreground/8 bg-surface px-3 py-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Next Lesson</p>
            {nextAssignment ? (
              <>
                <p className="mt-1 line-clamp-2 text-sm font-black">{assignmentTitle(nextAssignment)}</p>
                <p className="mt-1 text-[11px] font-semibold text-muted-foreground">
                  {dateLabel(nextAssignment.session_datetime)} · {asString(nextAssignment.evaluator_name) || "No evaluator"}
                </p>
              </>
            ) : (
              <p className="mt-1 text-sm font-bold text-muted-foreground">
                {assignments.length ? "No pending lesson." : "No academy lessons assigned."}
              </p>
            )}
          </div>
          <CalendarClock className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 rounded-xl bg-muted/45 px-3 py-2">
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Account Login</p>
          <p className="mt-1 truncate font-mono text-sm font-black">{login || "Account not created yet"}</p>
        </div>
        <button
          type="button"
          disabled={!login}
          onClick={() => onCopyLogin(login)}
          className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-foreground/10 bg-background px-2 text-[11px] font-bold disabled:opacity-50"
        >
          <Copy className="h-3.5 w-3.5" />
          Copy
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {nextAssignment ? (
          scheduled ? (
            <>
              <button type="button" onClick={() => onAssess(nextAssignment)} className="inline-flex h-9 flex-1 items-center justify-center gap-1 rounded-lg bg-foreground px-3 text-xs font-black text-background">
                <ClipboardCheck className="h-3.5 w-3.5" />
                Assess
              </button>
              <button type="button" onClick={() => onSchedule(nextAssignment)} className="inline-flex h-9 items-center justify-center gap-1 rounded-lg border border-foreground/10 px-3 text-xs font-black">
                <CalendarClock className="h-3.5 w-3.5" />
                Schedule
              </button>
            </>
          ) : (
            <>
              <button type="button" onClick={() => onSchedule(nextAssignment)} className="inline-flex h-9 flex-1 items-center justify-center gap-1 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground">
                <CalendarClock className="h-3.5 w-3.5" />
                Schedule
              </button>
              <button type="button" onClick={() => onAssess(nextAssignment)} className="inline-flex h-9 items-center justify-center gap-1 rounded-lg border border-foreground/10 px-3 text-xs font-black">
                <ClipboardCheck className="h-3.5 w-3.5" />
                Assess
              </button>
            </>
          )
        ) : null}
        {!nextAssignment && assignments.length ? (
          <button type="button" onClick={onDetail} className="inline-flex h-9 flex-1 items-center justify-center gap-1 rounded-lg bg-foreground px-3 text-xs font-black text-background">
            <Eye className="h-3.5 w-3.5" />
            Review
          </button>
        ) : null}
        <button type="button" onClick={onDetail} className="inline-flex h-9 items-center justify-center rounded-lg border border-foreground/10 px-3 text-xs font-black">
          Details
        </button>
        {allowTeacherPreview ? (
          <button type="button" onClick={onPreview} className="inline-flex h-9 items-center justify-center gap-1 rounded-lg border border-primary/20 bg-primary/5 px-3 text-xs font-black text-primary">
            <Eye className="h-3.5 w-3.5" />
            Preview
          </button>
        ) : null}
        {status === "ready_for_active_teacher" ? (
          <button type="button" onClick={onPromote} className="inline-flex h-9 items-center justify-center gap-1 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground">
            <Trophy className="h-3.5 w-3.5" />
            Promote
          </button>
        ) : null}
      </div>
    </article>
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
  const panelRef = useDismissibleLayer<HTMLDivElement>({
    onDismiss: onClose,
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-foreground/55 p-0 backdrop-blur-[2px] animate-in fade-in duration-150 motion-reduce:animate-none sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        ref={panelRef}
        className={`flex max-h-[92dvh] w-full flex-col overflow-hidden rounded-t-2xl bg-surface shadow-card-hover animate-in slide-in-from-bottom-2 duration-150 motion-reduce:animate-none sm:max-h-[calc(100dvh-1.5rem)] sm:rounded-2xl sm:zoom-in-95 ${wide ? "sm:max-w-6xl" : "sm:max-w-2xl"}`}
      >
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

function ModalActions({
  onClose,
  submitting,
  submitLabel,
  disabled = false,
}: {
  onClose: () => void;
  submitting: boolean;
  submitLabel: string;
  disabled?: boolean;
}) {
  return (
    <div className="sticky bottom-0 -mx-4 mt-2 flex justify-end gap-2 border-t border-foreground/8 bg-surface px-4 py-3">
      <button type="button" onClick={onClose} className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted">
        Cancel
      </button>
      <button type="submit" disabled={submitting || disabled} className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60">
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
  allowTeacherPreview = true,
}: {
  state: any;
  academyTeachers: AcademyTeacher[];
  onAcademyChange: (rows: AcademyTeacher[]) => void;
  onTeachersChange: (rows: Array<Record<string, unknown>>) => void;
  showToast: (message: string, tone?: ToastTone) => void;
  allowTeacherPreview?: boolean;
}) {
  const csrf = asString(state.props?.csrfToken);
  const [createOpen, setCreateOpen] = useState(false);
  const [hodOpen, setHodOpen] = useState(false);
  const [credentials, setCredentials] = useState<GeneratedCredentials | null>(null);
  const [detailTeacher, setDetailTeacher] = useState<AcademyTeacher | null>(null);
  const [scheduleTarget, setScheduleTarget] = useState<{ teacher: AcademyTeacher; assignment: AcademyAssignment } | null>(null);
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
  const analytics = useMemo(() => academyAnalyticsRows(academyTeachers), [academyTeachers]);

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
    return data;
  }

  const adminMode = asString(state.adminMode || state.props?.adminMode).toLowerCase();
  const authRole = asString(state.props?.authRole).toLowerCase();
  const canCreateHeadOfDepartment = adminMode === "academic_director" || authRole === "academic_director";
  const canCreateAcademyTeacher = adminMode !== "head_of_department" && authRole !== "head_of_department";

  const sortedTeachers = [...academyTeachers].sort((left, right) => {
    const leftReady = asString(left.academy_status) === "ready_for_active_teacher" ? 1 : 0;
    const rightReady = asString(right.academy_status) === "ready_for_active_teacher" ? 1 : 0;
    if (leftReady !== rightReady) return rightReady - leftReady;
    return asString(right.updated_at).localeCompare(asString(left.updated_at));
  });

  function copyLogin(login: string) {
    const normalizedLogin = login.trim();
    if (!normalizedLogin) return;
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(normalizedLogin).catch(() => {});
    }
    showToast("Teacher login copied.");
  }

  function previewAsTeacher(teacher: AcademyTeacher) {
    if (!allowTeacherPreview) {
      return;
    }
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
            const result = await submit(routes.adminTeacherAcademyCreate, fields, "Academy teacher created.");
            if (result) {
              if (typeof result === "object" && result.credentials && typeof result.credentials === "object") {
                setCredentials(result.credentials as GeneratedCredentials);
              }
              setCreateOpen(false);
            }
          }}
          onClose={() => {
            setError("");
            setCreateOpen(false);
          }}
        />
      ) : null}
      {hodOpen ? (
        <NewHeadOfDepartmentModal
          state={state}
          submitting={submitting}
          error={error}
          onSubmit={async (fields) => {
            const result = await submit(routes.academicDirectorHeadOfDepartmentCreate, fields, "Head of Department account created.");
            if (result) {
              if (typeof result === "object" && result.credentials && typeof result.credentials === "object") {
                setCredentials(result.credentials as GeneratedCredentials);
              }
              setHodOpen(false);
            }
          }}
          onClose={() => {
            setError("");
            setHodOpen(false);
          }}
        />
      ) : null}
      {scheduleTarget ? (
        <AssignmentModal
          state={state}
          teacher={scheduleTarget.teacher}
          assignment={scheduleTarget.assignment}
          submitting={submitting}
          error={error}
          onSubmit={async (assignmentId, fields) => {
            if (await submit(routes.adminTeacherAcademyAssignment(assignmentId), fields, "Training lesson updated.")) {
              setScheduleTarget(null);
            }
          }}
          onClose={() => {
            setError("");
            setScheduleTarget(null);
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
          allowTeacherPreview={allowTeacherPreview}
          onSchedule={(nextAssignment) => {
            setError("");
            setScheduleTarget({ teacher: detailTeacher, assignment: nextAssignment });
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
        subtitle="New teachers training on selected curriculum-guided lessons"
        icon={<GraduationCap className="h-4 w-4 text-info" />}
        className="flex min-h-0 flex-1 flex-col"
        bodyClassName="flex min-h-0 flex-1 flex-col"
        headerActions={
          <div className="flex flex-wrap justify-end gap-2">
            {canCreateHeadOfDepartment ? (
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setHodOpen(true);
                }}
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-bold text-foreground hover:bg-muted"
              >
                <Plus className="h-4 w-4" />
                New HOD
              </button>
            ) : null}
            {canCreateAcademyTeacher ? (
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
            ) : null}
          </div>
        }
      >
        {credentials ? (
          <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-900">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-black uppercase tracking-wide">Generated credentials</p>
                <p className="mt-1 text-sm font-bold">{asString(credentials.display_name) || "New account"} · {asString(credentials.subject_name) || asString(credentials.role)}</p>
              </div>
              <button type="button" onClick={() => setCredentials(null)} className="rounded-lg px-2 py-1 text-xs font-bold hover:bg-emerald-100">
                Dismiss
              </button>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg bg-white/70 px-3 py-2">
                <p className="text-[10px] font-black uppercase tracking-wide text-emerald-700">Login</p>
                <p className="font-mono text-sm font-black">{asString(credentials.login) || asString(credentials.teacher_code)}</p>
              </div>
              <div className="rounded-lg bg-white/70 px-3 py-2">
                <p className="text-[10px] font-black uppercase tracking-wide text-emerald-700">Temporary password</p>
                <p className="font-mono text-sm font-black">{asString(credentials.temporary_password)}</p>
              </div>
            </div>
          </div>
        ) : null}
        <div className="mb-3 grid shrink-0 gap-2 sm:grid-cols-4">
          {metric("Academy Teachers", stats.total, "training records")}
          {metric("In Training", stats.inTraining, "active training paths")}
          {metric("Ready", stats.ready, "promotion review")}
          {metric("Avg Score", stats.average == null ? "-" : stats.average.toFixed(2), "weighted average")}
        </div>
        <div className="mb-3 grid shrink-0 gap-2 md:grid-cols-2 xl:grid-cols-4">
          <MiniAnalyticsCard
            title="Academy status distribution"
            subtitle="Training, ready, completed, support"
            rows={analytics.statusRows}
            emptyLabel="No academy teachers yet."
          />
          <MiniAnalyticsCard
            title="Average score by subject"
            subtitle="Weighted assessment average"
            rows={analytics.subjectScoreRows}
            emptyLabel="No assessment scores yet."
          />
          <MiniAnalyticsCard
            title="Completion rate by subject"
            subtitle="Assessed lessons over assigned lessons"
            rows={analytics.completionRows}
            emptyLabel="No assigned lessons yet."
          />
          <MiniAnalyticsCard
            title="Recent assessment trend"
            subtitle="Latest reports in sequence"
            rows={analytics.assessmentRows}
            emptyLabel="No assessment trend yet."
          />
        </div>
        <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
          {sortedTeachers.length ? (
            <>
              <div className="space-y-3 p-3 lg:hidden">
                {sortedTeachers.map((teacher) => {
                  return (
                    <AcademyTeacherCard
                      key={asNumber(teacher.id)}
                      teacher={teacher}
                      allowTeacherPreview={allowTeacherPreview}
                      onPreview={() => previewAsTeacher(teacher)}
                      onDetail={() => setDetailTeacher(teacher)}
                      onSchedule={(targetAssignment) => setScheduleTarget({ teacher, assignment: targetAssignment })}
                      onAssess={(targetAssignment) => setAssessmentTarget({ teacher, assignment: targetAssignment })}
                      onPromote={() => setPromoteTeacher(teacher)}
                      onCopyLogin={copyLogin}
                    />
                  );
                })}
              </div>
              <div className="hidden max-h-[calc(100dvh-20rem)] overflow-auto lg:block">
                <table className="w-full min-w-[860px] table-fixed border-collapse text-left">
                  <colgroup>
                    <col className="w-[20%]" />
                    <col className="w-[13%]" />
                    <col className="w-[14%]" />
                    <col className="w-[18%]" />
                    <col className="w-[13%]" />
                    <col className="w-[10%]" />
                    <col className="w-[12%]" />
                  </colgroup>
                  <thead className="sticky top-0 z-10 bg-surface/95 shadow-[0_1px_0_hsl(var(--foreground)/0.08)] backdrop-blur">
                    <tr>
                      {["Teacher", "Subject", "Progress", "Next lesson", "Director / Evaluator", "Avg score", "Actions"].map((heading) => (
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
                      const nextAssignment = nextAcademyAssignment(teacher);
                      const percent = progress.target ? Math.min(100, Math.round((progress.assessed / progress.target) * 100)) : 0;
                      const status = asString(teacher.academy_status);
                      const login = asString(teacher.login);
                      const scheduled = assignmentIsScheduled(nextAssignment);
                      return (
                        <tr
                          key={asNumber(teacher.id)}
                          className="group animate-in fade-in slide-in-from-bottom-1 transition-colors duration-150 hover:bg-muted/35 motion-reduce:animate-none"
                          style={{ animationDelay: `${index * 30}ms` }}
                        >
                          <td className="px-3 py-2.5 align-middle">
                            <div className="flex min-w-0 items-center gap-2 text-left">
                              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-black text-primary">
                                {asString(teacher.full_name).slice(0, 1).toUpperCase() || "T"}
                              </span>
                              <span className="min-w-0">
                                <button type="button" onClick={() => setDetailTeacher(teacher)} className="block max-w-full truncate text-left text-sm font-black text-primary group-hover:underline">
                                  {asString(teacher.full_name)}
                                </button>
                                <span className="mt-1 flex min-w-0 items-center gap-1.5">
                                  <span className="truncate font-mono text-[11px] font-black text-foreground">{login || "Creating..."}</span>
                                  <button
                                    type="button"
                                    disabled={!login}
                                    onClick={() => copyLogin(login)}
                                    className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded border border-foreground/10 bg-surface text-muted-foreground ${login ? "hover:text-foreground" : "opacity-40"}`}
                                    aria-label="Copy teacher login"
                                  >
                                    <Copy className="h-3 w-3" />
                                  </button>
                                </span>
                                <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[9px] font-black uppercase tracking-wide ${
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
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="line-clamp-2 text-xs font-bold text-foreground">{asString(teacher.subject) || "Subject not set"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
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
                          <td className="px-3 py-2.5 align-middle">
                            {nextAssignment ? (
                              <div className="min-w-0">
                                <p className="truncate text-xs font-black">{assignmentTitle(nextAssignment)}</p>
                                <p className="mt-0.5 truncate text-[11px] font-semibold text-muted-foreground">
                                  {dateLabel(nextAssignment.session_datetime)}
                                </p>
                              </div>
                            ) : (
                              <span className="text-xs font-semibold text-muted-foreground">No academy lessons assigned.</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="line-clamp-2 text-xs font-bold text-foreground">
                              {nextAssignment ? asString(nextAssignment.evaluator_name) || "Not assigned" : "Not assigned"}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="text-sm font-black">{progress.average == null ? "-" : progress.average.toFixed(2)}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <div className="flex flex-wrap justify-end gap-1.5">
                              {nextAssignment ? (
                                scheduled ? (
                                  <>
                                    <button type="button" onClick={() => setAssessmentTarget({ teacher, assignment: nextAssignment })} className="inline-flex h-8 items-center gap-1 rounded-lg bg-foreground px-2.5 text-[11px] font-bold text-background transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                      <ClipboardCheck className="h-3.5 w-3.5" />
                                      Assess
                                    </button>
                                    <button type="button" onClick={() => setScheduleTarget({ teacher, assignment: nextAssignment })} className="inline-flex h-8 items-center gap-1 rounded-lg border border-foreground/10 bg-background px-2.5 text-[11px] font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
                                      <CalendarClock className="h-3.5 w-3.5" />
                                      Schedule
                                    </button>
                                  </>
                                ) : (
                                  <>
                                    <button type="button" onClick={() => setScheduleTarget({ teacher, assignment: nextAssignment })} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-2.5 text-[11px] font-bold text-primary-foreground transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                      <CalendarClock className="h-3.5 w-3.5" />
                                      Schedule
                                    </button>
                                    <button type="button" onClick={() => setAssessmentTarget({ teacher, assignment: nextAssignment })} className="inline-flex h-8 items-center gap-1 rounded-lg border border-foreground/10 bg-background px-2.5 text-[11px] font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
                                      <ClipboardCheck className="h-3.5 w-3.5" />
                                      Assess
                                    </button>
                                  </>
                                )
                              ) : null}
                              {!nextAssignment && academyAssignments(teacher).length ? (
                                <button type="button" onClick={() => setDetailTeacher(teacher)} className="inline-flex h-8 items-center gap-1 rounded-lg bg-foreground px-2.5 text-[11px] font-bold text-background transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                  <Eye className="h-3.5 w-3.5" />
                                  Review
                                </button>
                              ) : null}
                              <button type="button" onClick={() => setDetailTeacher(teacher)} className="inline-flex h-8 items-center gap-1 rounded-lg border border-foreground/10 bg-background px-2.5 text-[11px] font-bold transition hover:bg-muted">
                                Details
                              </button>
                              {allowTeacherPreview ? (
                                <button type="button" onClick={() => previewAsTeacher(teacher)} className="inline-flex h-8 items-center gap-1 rounded-lg border border-primary/20 bg-primary/5 px-2.5 text-[11px] font-bold text-primary transition hover:bg-primary/10 active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
                                  <Eye className="h-3.5 w-3.5" />
                                  Preview
                                </button>
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
            </>
          ) : (
            <div className="flex min-h-[22rem] flex-1 flex-col items-center justify-center px-3 py-10 text-center">
              <BookOpenCheck className="mx-auto h-5 w-5 text-muted-foreground" />
              <p className="mt-2 text-sm font-bold">No academy teachers yet.</p>
              <p className="mt-1 text-xs text-muted-foreground">Create a trainee and choose the curriculum lessons for their training pack.</p>
            </div>
          )}
        </div>
      </ChartCard>
    </>
  );
}
