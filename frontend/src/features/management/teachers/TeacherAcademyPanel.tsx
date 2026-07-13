import { useMemo, useRef, useState } from "react";
import { BookOpenCheck, CalendarClock, CheckCircle2, ClipboardCheck, Copy, Eye, GraduationCap, Plus, Trash2, Trophy, UsersRound, XCircle } from "lucide-react";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ChartCard } from "@/shared/ui/ChartCard";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { EmptyState } from "@/shared/ui/EmptyState";
import { IconButton } from "@/shared/ui/IconButton";
import { MetricCard } from "@/shared/ui/MetricCard";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { MobileCardList } from "@/shared/ui/MobileCardList";
import { ProgressBar } from "@/shared/ui/ProgressBar";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "@/features/managementTypes";
import { formatUzs, postForm, semesterStages, suggestedLessonRate, teacherCategories, ToastTone } from "./shared";

type AcademyTeacher = Record<string, unknown>;
type AcademyAssignment = Record<string, unknown>;
type GeneratedCredentials = Record<string, unknown>;
type TeacherAcademyActionRoutes = {
  create: string;
  assignmentUpdate: (assignmentId: number | string) => string;
  assessmentCreate: (academyTeacherId: number | string) => string;
  assessmentDelete: (academyTeacherId: number | string, assessmentId: number | string) => string;
  statusUpdate: (academyTeacherId: number | string) => string;
  lessonsSync: (academyTeacherId: number | string) => string;
  promote?: (academyTeacherId: number | string) => string;
  delete?: (academyTeacherId: number | string) => string;
};

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
    in_training: "In Academy",
    ready_for_evaluation: "Ready for Evaluation",
    needs_improvement: "Needs Improvement",
    ready_for_active_teacher: "Ready for Active Teacher",
    approved: "Approved",
    rejected: "Rejected",
    on_hold: "On Hold",
  };
  return labels[asString(value)] || asString(value) || "In Academy";
}

function academyStatusTone(value: unknown): "success" | "warning" | "danger" | "info" {
  const status = asString(value);
  if (status === "ready_for_active_teacher" || status === "approved") return "success";
  if (status === "needs_improvement" || status === "on_hold") return "warning";
  if (status === "rejected") return "danger";
  return "info";
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

function initialsFromName(value: unknown) {
  const name = asString(value);
  if (!name) return "T";
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return initials || name.replace(/[^a-z]/gi, "").slice(0, 2).toUpperCase() || "T";
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

/** The saved assessment report for a given assignment, or null if not assessed. */
function assessmentForAssignment(teacher: AcademyTeacher, assignment: AcademyAssignment | null | undefined) {
  const assignmentId = asNumber(assignment?.id);
  if (!assignmentId) return null;
  return (
    academyAssessments(teacher).find(
      (assessment) => asNumber(assessment.lesson_assignment_id) === assignmentId,
    ) || null
  );
}

/** Badge tone for an assessment decision: passes are success, needs-improvement is a warning. */
function decisionTone(value: unknown): "success" | "warning" | "danger" {
  const decision = asString(value);
  if (decision === "rejected") return "danger";
  if (decision === "needs_improvement" || decision === "reassign_lesson") return "warning";
  return "success";
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
  return <MetricCard label={label} value={value} detail={detail} density="compact" className="bg-background" />;
}

function teacherAcademyActionRoutes(adminMode: string, authRole: string): TeacherAcademyActionRoutes {
  const roleMode = authRole || adminMode;
  if (roleMode === "academic_director" || adminMode === "academic_director") {
    return {
      create: routes.academicDirectorTeacherAcademyCreate,
      assignmentUpdate: routes.academicDirectorTeacherAcademyAssignmentUpdate,
      assessmentCreate: routes.academicDirectorTeacherAcademyAssessmentCreate,
      assessmentDelete: routes.academicDirectorTeacherAcademyAssessmentDelete,
      statusUpdate: routes.academicDirectorTeacherAcademyStatusUpdate,
      lessonsSync: routes.academicDirectorTeacherAcademyLessonsSync,
      promote: routes.academicDirectorTeacherAcademyPromote,
      delete: routes.academicDirectorTeacherAcademyDelete,
    };
  }
  if (roleMode === "head_of_department" || adminMode === "head_of_department") {
    return {
      create: "",
      assignmentUpdate: routes.headOfDepartmentTeacherAcademyAssignmentUpdate,
      assessmentCreate: routes.headOfDepartmentTeacherAcademyAssessmentCreate,
      assessmentDelete: routes.headOfDepartmentTeacherAcademyAssessmentDelete,
      statusUpdate: routes.headOfDepartmentTeacherAcademyStatusUpdate,
      lessonsSync: routes.headOfDepartmentTeacherAcademyLessonsSync,
    };
  }
  return {
    create: "",
    assignmentUpdate: () => "",
    assessmentCreate: () => "",
    assessmentDelete: () => "",
    statusUpdate: () => "",
    lessonsSync: () => "",
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
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-3">
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
        </ModalBody>
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
  type WizardStep = 1 | 2 | 3;
  const initialTeacherFields: Record<string, string> = {
    academy_full_name: "",
    academy_subject_program_id: "",
    academy_telegram_username: "",
    academy_phone: "",
    academy_email: "",
    academy_start_date: "",
    academy_mentor_id: "",
    academy_department_head_id: "",
    academy_notes: "",
  };
  const programs = Array.isArray(state.props?.adminAcademicCurriculumPrograms)
    ? state.props.adminAcademicCurriculumPrograms as Array<Record<string, unknown>>
    : [];
  const curriculumItems = Array.isArray(state.props?.adminAcademicCurriculumItems)
    ? state.props.adminAcademicCurriculumItems as Array<Record<string, unknown>>
    : [];
  const teachers = Array.isArray(state.teachers) ? state.teachers as Array<Record<string, unknown>> : [];
  const [wizardStep, setWizardStep] = useState<WizardStep>(1);
  const [teacherFields, setTeacherFields] = useState<Record<string, string>>(initialTeacherFields);
  const [selectedLessonIds, setSelectedLessonIds] = useState<number[]>([]);
  const [lessonSearch, setLessonSearch] = useState("");
  const [localError, setLocalError] = useState("");
  const selectedProgramId = teacherFields.academy_subject_program_id;

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
  const selectedLessons = useMemo(
    () => selectedProgramLessons.filter((lesson) => selectedLessonIds.includes(asNumber(lesson.id))),
    [selectedLessonIds, selectedProgramLessons],
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
  const selectedProgram = programs.find((program) => asNumber(program.id) === asNumber(selectedProgramId));
  const selectedMentor = teachers.find((teacher) => asNumber(teacher.id) === asNumber(teacherFields.academy_mentor_id));
  const selectedDepartmentHead = teachers.find((teacher) => asNumber(teacher.id) === asNumber(teacherFields.academy_department_head_id));

  function updateTeacherField(name: string, value: string) {
    setTeacherFields((current) => ({ ...current, [name]: value }));
    setLocalError("");
    if (name === "academy_subject_program_id") {
      setSelectedLessonIds([]);
      setLessonSearch("");
    }
  }

  function toggleLesson(lessonId: number) {
    setLocalError("");
    setSelectedLessonIds((current) =>
      current.includes(lessonId)
        ? current.filter((selectedId) => selectedId !== lessonId)
        : [...current, lessonId],
    );
  }

  function selectFirstLessons(count: number) {
    setLocalError("");
    setSelectedLessonIds(selectedProgramLessons.slice(0, count).map((lesson) => asNumber(lesson.id)).filter(Boolean));
  }

  function selectVisibleLessons() {
    setLocalError("");
    setSelectedLessonIds(filteredProgramLessons.map((lesson) => asNumber(lesson.id)).filter(Boolean));
  }

  function validateStep(step: WizardStep) {
    if (step === 1) {
      if (!teacherFields.academy_full_name.trim()) {
        setLocalError("Full name is required.");
        return false;
      }
      if (!teacherFields.academy_subject_program_id) {
        setLocalError("Subject curriculum is required.");
        return false;
      }
    }
    if (step === 2 && !selectedLessonIds.length) {
      setLocalError("Select at least 1 Teacher Academy lesson.");
      return false;
    }
    setLocalError("");
    return true;
  }

  function goNext() {
    if (!validateStep(wizardStep)) return;
    setWizardStep((current) => Math.min(3, current + 1) as WizardStep);
  }

  function goBack() {
    setLocalError("");
    setWizardStep((current) => Math.max(1, current - 1) as WizardStep);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (wizardStep !== 3) {
      goNext();
      return;
    }
    if (!validateStep(1) || !validateStep(2)) {
      return;
    }
    const fields: Record<string, string> = {
      ...teacherFields,
      academy_position: "Trainee Teacher",
      academy_employment_type: "academy",
      academy_curriculum_item_ids: selectedLessonIds.join(","),
    };
    onSubmit(fields);
  }

  const inputClass = "w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none focus:border-primary/50";
  const currentError = localError || error;
  const stepLabels = [
    { step: 1 as WizardStep, label: "Teacher Info" },
    { step: 2 as WizardStep, label: "Select Academy Lessons" },
    { step: 3 as WizardStep, label: "Review & Create" },
  ];
  const programLabel = selectedProgram
    ? `${asString(selectedProgram.subject_name)} · ${asNumber(selectedProgram.lesson_count)} lessons`
    : "Not selected";
  const lessonDetail = (lesson: Record<string, unknown>) =>
    asString(lesson.specification_points) || asString(lesson.book_pages) || "No lesson details yet.";
  const lessonCode = (lesson: Record<string, unknown>) =>
    asString(lesson.lesson_number) || asString(lesson.specification_code) || asString(lesson.book_pages) || `Lesson ${asNumber(lesson.item_order)}`;

  return (
    <ModalShell
      title="New Academy Teacher"
      subtitle="Create a trainee and choose the curriculum lessons for their Teacher Academy path."
      onClose={onClose}
      wide
      mobileMode="fullscreen"
    >
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-4">
          <div className="grid grid-cols-3 gap-2" aria-label="New Academy Teacher steps">
            {stepLabels.map((item) => {
              const active = item.step === wizardStep;
              const complete = item.step < wizardStep;
              return (
                <button
                  key={item.step}
                  type="button"
                  onClick={() => {
                    if (item.step <= wizardStep) {
                      setWizardStep(item.step);
                      return;
                    }
                    if (item.step === ((wizardStep + 1) as WizardStep) && validateStep(wizardStep)) {
                      setWizardStep(item.step);
                    }
                  }}
                  className={`min-h-10 rounded-lg border px-2 text-left text-[11px] font-black transition-colors motion-reduce:transition-none ${
                    active
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : complete
                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                        : "border-foreground/10 bg-background text-muted-foreground"
                  }`}
                  aria-current={active ? "step" : undefined}
                >
                  <span className="block text-[10px] uppercase tracking-wide">Step {item.step}</span>
                  <span className="block leading-tight">{item.label}</span>
                </button>
              );
            })}
          </div>

          {wizardStep === 1 ? (
            <section className="space-y-3">
              <div>
                <p className="text-xs font-black uppercase tracking-wide text-foreground">Teacher Info</p>
                <p className="mt-1 text-xs font-semibold text-muted-foreground">Full name and subject curriculum are required.</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <FieldLabel>Full Name</FieldLabel>
                  <input
                    name="academy_full_name"
                    required
                    value={teacherFields.academy_full_name}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <FieldLabel>Subject Curriculum</FieldLabel>
                  <select
                    name="academy_subject_program_id"
                    required
                    value={selectedProgramId}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  >
                    <option value="" disabled>Select curriculum</option>
                    {programs.map((program) => (
                      <option key={asNumber(program.id)} value={asNumber(program.id)}>
                        {asString(program.subject_name)} · {asNumber(program.lesson_count)} lessons
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <FieldLabel>Telegram Username</FieldLabel>
                  <input
                    name="academy_telegram_username"
                    value={teacherFields.academy_telegram_username}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                    placeholder="@username"
                  />
                </label>
                <label className="block">
                  <FieldLabel>Phone</FieldLabel>
                  <input
                    name="academy_phone"
                    value={teacherFields.academy_phone}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <FieldLabel>Email</FieldLabel>
                  <input
                    name="academy_email"
                    type="email"
                    value={teacherFields.academy_email}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <FieldLabel>Start Date</FieldLabel>
                  <input
                    name="academy_start_date"
                    type="date"
                    value={teacherFields.academy_start_date}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  />
                </label>
                <label className="block">
                  <FieldLabel>Mentor</FieldLabel>
                  <select
                    name="academy_mentor_id"
                    value={teacherFields.academy_mentor_id}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  >
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
                  <select
                    name="academy_department_head_id"
                    value={teacherFields.academy_department_head_id}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={inputClass}
                  >
                    <option value="">Not assigned</option>
                    {teachers.map((teacher) => (
                      <option key={asNumber(teacher.id)} value={asNumber(teacher.id)}>
                        {asString(teacher.full_name)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block sm:col-span-2">
                  <FieldLabel>Notes</FieldLabel>
                  <textarea
                    name="academy_notes"
                    rows={3}
                    value={teacherFields.academy_notes}
                    onChange={(event) => updateTeacherField(event.target.name, event.target.value)}
                    className={`${inputClass} resize-none`}
                  />
                </label>
              </div>
            </section>
          ) : null}

          {wizardStep === 2 ? (
            <section className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-black uppercase tracking-wide text-foreground">Select Academy Lessons</p>
                  <p className="mt-1 text-xs font-semibold text-muted-foreground">Selected {selectedLessonIds.length} lessons from {programLabel}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:justify-end">
                  <button type="button" onClick={() => selectFirstLessons(6)} disabled={!selectedProgramLessons.length} className="rounded-lg border border-foreground/10 px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-50">
                    Select first 6
                  </button>
                  <button type="button" onClick={() => selectFirstLessons(12)} disabled={!selectedProgramLessons.length} className="rounded-lg border border-foreground/10 px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-50">
                    Select first 12
                  </button>
                  <button type="button" onClick={selectVisibleLessons} disabled={!filteredProgramLessons.length} className="rounded-lg border border-foreground/10 px-3 py-1.5 text-xs font-bold hover:bg-muted disabled:opacity-50">
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
                className={inputClass}
                placeholder="Search lesson, topic, or specification"
                disabled={!selectedProgramId}
              />
              <div className="space-y-2">
                {!selectedProgramId ? (
                  <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-6 text-center text-sm font-semibold text-muted-foreground">
                    Select a subject curriculum to choose lessons.
                  </p>
                ) : filteredProgramLessons.length ? (
                  filteredProgramLessons.map((lesson) => {
                    const lessonId = asNumber(lesson.id);
                    const checked = selectedLessonIds.includes(lessonId);
                    return (
                      <div
                        key={lessonId}
                        className={`rounded-lg border px-3 py-2.5 transition-colors ${
                          checked ? "border-primary/30 bg-primary/5" : "border-foreground/10 bg-surface"
                        }`}
                      >
                        <label className="flex cursor-pointer items-start gap-3">
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
                              {lessonCode(lesson)} · {asString(lesson.title) || "Untitled lesson"}
                            </span>
                            <span className="mt-1 block text-xs font-bold text-muted-foreground">
                              {asString(lesson.book_pages) || "Specification preview"}
                            </span>
                          </span>
                        </label>
                        <details className="ml-7 mt-2 text-xs leading-5 text-muted-foreground">
                          <summary className="cursor-pointer font-bold text-primary">Show details</summary>
                          <p className="mt-1">{lessonDetail(lesson)}</p>
                        </details>
                      </div>
                    );
                  })
                ) : (
                  <p className="rounded-lg border border-dashed border-foreground/15 px-3 py-6 text-center text-sm font-semibold text-muted-foreground">
                    No lesson topics found for this curriculum.
                  </p>
                )}
              </div>
            </section>
          ) : null}

          {wizardStep === 3 ? (
            <section className="space-y-4">
              <div>
                <p className="text-xs font-black uppercase tracking-wide text-foreground">Review & Create</p>
                <p className="mt-1 text-xs font-semibold text-muted-foreground">Confirm the account details and selected Teacher Academy lesson plan.</p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {[
                  ["Teacher", teacherFields.academy_full_name || "-"],
                  ["Subject Curriculum", programLabel],
                  ["Start Date", teacherFields.academy_start_date || "-"],
                  ["Mentor", asString(selectedMentor?.full_name) || "Not assigned"],
                  ["Department Head", asString(selectedDepartmentHead?.full_name) || "Not assigned"],
                  ["Selected Lessons", String(selectedLessonIds.length)],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-foreground/10 bg-background px-3 py-2">
                    <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">{label}</p>
                    <p className="mt-1 break-words text-sm font-black text-foreground">{value}</p>
                  </div>
                ))}
              </div>
              {!teacherFields.academy_mentor_id || !teacherFields.academy_department_head_id ? (
                <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold leading-5 text-amber-800">
                  Mentor or department head is not assigned yet. Creation is still allowed if the backend accepts it.
                </p>
              ) : null}
              <div className="rounded-xl border border-foreground/10 bg-background p-3">
                <p className="text-xs font-black uppercase tracking-wide text-muted-foreground">First selected lessons</p>
                <ul className="mt-2 space-y-1.5 text-sm font-semibold text-foreground">
                  {selectedLessons.slice(0, 5).map((lesson) => (
                    <li key={asNumber(lesson.id)} className="rounded-lg bg-surface px-3 py-2">
                      {lessonCode(lesson)} · {asString(lesson.title) || "Untitled lesson"}
                    </li>
                  ))}
                </ul>
                {selectedLessons.length > 5 ? (
                  <p className="mt-2 text-xs font-bold text-muted-foreground">+{selectedLessons.length - 5} more selected lessons</p>
                ) : null}
              </div>
            </section>
          ) : null}

          {currentError ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{currentError}</p> : null}
        </ModalBody>
        <ModalFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
          <button type="button" onClick={wizardStep === 1 ? onClose : goBack} className="min-h-10 w-full rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted sm:w-auto">
            {wizardStep === 1 ? "Cancel" : "Back"}
          </button>
          {wizardStep < 3 ? (
            <button type="button" onClick={goNext} className="min-h-10 w-full rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60 sm:w-auto">
              {wizardStep === 1 ? "Next: Select Lessons" : "Next: Review"}
            </button>
          ) : (
            <button type="submit" disabled={submitting || !selectedLessonIds.length} className="min-h-10 w-full rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60 sm:w-auto">
              {submitting ? "Saving..." : "Create Academy Teacher"}
            </button>
          )}
        </ModalFooter>
      </form>
    </ModalShell>
  );
}

function AssignmentModal({
  teacher,
  assignment,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  assignment: AcademyAssignment;
  submitting: boolean;
  error: string;
  onSubmit: (assignmentId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const assignments = academyAssignments(teacher);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState(asNumber(assignment.id) || asNumber(assignments[0]?.id));
  const selectedAssignment = assignmentById(assignments, selectedAssignmentId);
  const initialDateTime = toDateTimeLocal(selectedAssignment?.session_datetime);
  const [sessionDate, setSessionDate] = useState(initialDateTime.slice(0, 10));
  const [sessionTime, setSessionTime] = useState(initialDateTime.slice(11, 16));
  const controlClass = "h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10";

  function handleAssignmentChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const nextAssignment = assignmentById(assignments, asNumber(event.target.value));
    setSelectedAssignmentId(asNumber(nextAssignment?.id));
    const nextDateTime = toDateTimeLocal(nextAssignment?.session_datetime);
    setSessionDate(nextDateTime.slice(0, 10));
    setSessionTime(nextDateTime.slice(11, 16));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAssignment) return;
    // Only the lesson and its date/time are chosen here; the remaining
    // assignment fields are passed through unchanged so the update endpoint
    // does not clear them.
    const focus = Array.isArray(selectedAssignment.focus_areas)
      ? selectedAssignment.focus_areas.map(asString).filter(Boolean)
      : [];
    onSubmit(asNumber(selectedAssignment.id), {
      assignment_id: String(asNumber(selectedAssignment.id)),
      session_datetime: sessionDate && sessionTime ? `${sessionDate}T${sessionTime}` : "",
      assignment_type: asString(selectedAssignment.assignment_type) || "full_practice_lesson",
      deadline_date: asString(selectedAssignment.deadline_date),
      evaluator_id: String(asNumber(selectedAssignment.evaluator_id) || ""),
      focus_areas: focus.join(","),
      notes_to_trainee: asString(selectedAssignment.notes_to_trainee),
      assignment_status: asString(selectedAssignment.status) || "assigned",
    });
  }

  return (
    <ModalShell
      title="Schedule Academy Lesson"
      subtitle={selectedAssignment ? assignmentTitle(selectedAssignment) : "Choose an academy lesson"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-4">
          <section className="grid gap-2 rounded-xl border border-primary/10 bg-primary/5 p-3 sm:grid-cols-2">
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher name</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
              <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Assigned lesson</p>
              <p className="mt-1 line-clamp-2 text-sm font-black text-foreground">
                {selectedAssignment ? assignmentTitle(selectedAssignment) : "Choose an academy lesson"}
              </p>
              <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">
                {asString(selectedAssignment?.session_datetime) ? `Currently ${dateLabel(selectedAssignment?.session_datetime)}` : "Not scheduled yet"}
              </p>
            </div>
          </section>

          <label className="block">
            <FieldLabel>Lesson</FieldLabel>
            <select
              name="assignment_id"
              required
              value={selectedAssignmentId || ""}
              onChange={handleAssignmentChange}
              className={controlClass}
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
              <FieldLabel>Date</FieldLabel>
              <input
                type="date"
                required
                value={sessionDate}
                onChange={(event) => setSessionDate(event.target.value)}
                className={controlClass}
              />
            </label>
            <label className="block">
              <FieldLabel>Time</FieldLabel>
              <input
                type="time"
                required
                value={sessionTime}
                onChange={(event) => setSessionTime(event.target.value)}
                className={controlClass}
              />
            </label>
          </div>

          {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        </ModalBody>
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Save Schedule" disabled={!selectedAssignment} />
      </form>
    </ModalShell>
  );
}

function autoGrowTextarea(event: React.FormEvent<HTMLTextAreaElement>) {
  const element = event.currentTarget;
  element.style.height = "auto";
  element.style.height = `${element.scrollHeight}px`;
}

function AssessmentModal({
  teacher,
  assignment,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  assignment: AcademyAssignment;
  submitting: boolean;
  error: string;
  onSubmit: (teacherId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [assessmentDate] = useState(() => new Date());
  const [scores, setScores] = useState<Record<string, string>>(
    Object.fromEntries(rubric.map((item) => [item.key, "7"])),
  );
  const [confirmDecision, setConfirmDecision] = useState<"passed" | "needs_improvement" | null>(null);
  const weighted = rubric.reduce((sum, item) => {
    const value = Number(scores[item.key]);
    return sum + (Number.isFinite(value) ? value : 0) * item.weight;
  }, 0);
  const remarksClass = "min-h-10 w-full resize-none overflow-hidden rounded-lg border border-foreground/10 bg-background px-3 py-2.5 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10";

  function submitDecision(decision: "passed" | "needs_improvement") {
    const fields: Record<string, string> = {};
    if (formRef.current) {
      new FormData(formRef.current).forEach((value, key) => {
        fields[key] = String(value);
      });
    }
    rubric.forEach((item) => {
      fields[item.key] = scores[item.key] || "0";
      fields[item.remarksKey] = fields[item.remarksKey] || "";
    });
    fields.lesson_assignment_id = String(asNumber(assignment.id));
    fields.assessment_datetime = toDateTimeLocal(assessmentDate.toISOString());
    fields.decision = decision;
    onSubmit(asNumber(teacher.id), fields);
  }

  return (
    <ModalShell
      title="Assessment Report"
      subtitle={`${asString(teacher.full_name)} · ${assignmentTitle(assignment)} · score ${weighted.toFixed(2)}`}
      onClose={onClose}
      wide
      mobileMode="fullscreen"
    >
      <form ref={formRef} onSubmit={(event) => event.preventDefault()} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-4">
          <div className="grid gap-2 rounded-xl border border-primary/10 bg-primary/5 p-3 sm:grid-cols-3">
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher name</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
              <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Assigned lesson</p>
              <p className="mt-1 line-clamp-2 text-sm font-black text-foreground">{assignmentTitle(assignment)}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-wide text-primary">Date</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{dateLabel(assessmentDate.toISOString())}</p>
            </div>
          </div>

          <section className="rounded-xl border border-foreground/10">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 px-4 py-3">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Marking Criteria</p>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
                Score {weighted.toFixed(2)}
              </span>
            </div>
            <div className="divide-y divide-foreground/8">
              {rubric.map((item) => (
                <div key={item.key} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,14rem)_5.5rem_minmax(0,1fr)] sm:items-center">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span className="flex h-8 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-[11px] font-black text-primary">
                      {item.code}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">{item.label}</p>
                      <p className="text-[11px] font-semibold text-muted-foreground">{Math.round(item.weight * 100)}% weight</p>
                    </div>
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    step="0.1"
                    aria-label={`${item.label} score`}
                    value={scores[item.key] || ""}
                    onChange={(event) => setScores((current) => ({ ...current, [item.key]: event.target.value }))}
                    className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-2 text-center text-sm font-black text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
                  />
                  <textarea
                    name={item.remarksKey}
                    rows={1}
                    onInput={autoGrowTextarea}
                    placeholder="Remarks"
                    aria-label={`${item.label} remarks`}
                    className={remarksClass}
                  />
                </div>
              ))}
            </div>
          </section>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <FieldLabel>Strengths</FieldLabel>
              <textarea name="strengths" rows={3} onInput={autoGrowTextarea} placeholder="What went well?" className={remarksClass} />
            </label>
            <label className="block">
              <FieldLabel>Areas for Improvement</FieldLabel>
              <textarea name="areas_for_improvement" rows={3} onInput={autoGrowTextarea} placeholder="What should improve next?" className={remarksClass} />
            </label>
          </div>
          {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
        </ModalBody>
        <ModalFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="inline-flex h-10 w-full items-center justify-center rounded-xl border border-foreground/10 bg-background px-4 text-sm font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100 sm:w-auto">
            Cancel
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => setConfirmDecision("needs_improvement")}
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-destructive/30 bg-background px-5 text-sm font-bold text-destructive transition hover:bg-destructive/10 active:scale-[0.98] disabled:opacity-60 motion-reduce:transition-none motion-reduce:active:scale-100 sm:w-auto"
          >
            <XCircle className="h-4 w-4" />
            Fail
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => setConfirmDecision("passed")}
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-primary-foreground shadow-sm transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] disabled:opacity-60 motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100 sm:w-auto"
          >
            <CheckCircle2 className="h-4 w-4" />
            {submitting ? "Saving..." : "Pass"}
          </button>
        </ModalFooter>
      </form>
      <ConfirmDialog
        open={Boolean(confirmDecision)}
        title={confirmDecision === "passed" ? "Confirm pass?" : "Confirm fail?"}
        message={
          <>
            {asString(teacher.full_name)} · {assignmentTitle(assignment)} · score {weighted.toFixed(2)}.
          </>
        }
        confirmLabel={confirmDecision === "passed" ? "Yes, pass" : "Yes, fail"}
        cancelLabel="No"
        danger={confirmDecision === "needs_improvement"}
        busy={submitting}
        onConfirm={() => {
          const decision = confirmDecision;
          setConfirmDecision(null);
          if (decision) submitDecision(decision);
        }}
        onCancel={() => {
          if (!submitting) setConfirmDecision(null);
        }}
      />
    </ModalShell>
  );
}

function ReportModal({
  teacher,
  assignment,
  report,
  onClose,
}: {
  teacher: AcademyTeacher;
  assignment: AcademyAssignment;
  report: Record<string, unknown>;
  onClose: () => void;
}) {
  const scores = report.scores && typeof report.scores === "object" ? (report.scores as Record<string, unknown>) : {};
  const markingCriteria = (() => {
    const feedback = report.section_feedback && typeof report.section_feedback === "object"
      ? (report.section_feedback as Record<string, unknown>)
      : {};
    const criteria = feedback.marking_criteria;
    return criteria && typeof criteria === "object" ? (criteria as Record<string, unknown>) : {};
  })();
  const remarksFor = (code: string) => {
    const entry = markingCriteria[code.toLowerCase()];
    return entry && typeof entry === "object" ? asString((entry as Record<string, unknown>).remarks) : "";
  };
  const weighted = Number(report.weighted_overall_score || 0);
  const notes: Array<[string, string]> = [
    ["Strengths", asString(report.strengths)],
    ["Areas for Improvement", asString(report.areas_for_improvement)],
    ["Final Recommendation", asString(report.final_recommendation)],
  ];

  return (
    <ModalShell
      title="Assessment Report"
      subtitle={`${asString(teacher.full_name)} · ${assignmentTitle(assignment)} · score ${weighted.toFixed(2)}`}
      onClose={onClose}
      wide
      mobileMode="fullscreen"
    >
      <ModalBody className="space-y-4">
        <div className="grid gap-2 rounded-xl border border-primary/10 bg-primary/5 p-3 sm:grid-cols-4">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Teacher</p>
            <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
            <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Assessed lesson</p>
            <p className="mt-1 line-clamp-2 text-sm font-black text-foreground">{assignmentTitle(assignment)}</p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Evaluator · Date</p>
            <p className="mt-1 truncate text-sm font-black text-foreground">{asString(report.evaluator_name) || "Evaluator not set"}</p>
            <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{dateLabel(report.assessment_datetime)}</p>
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wide text-primary">Decision</p>
            <StatusBadge tone={decisionTone(report.decision)} className="mt-1 text-[10px]">
              {decisionLabel(report.decision)}
            </StatusBadge>
          </div>
        </div>

        <section className="rounded-xl border border-foreground/10">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 px-4 py-3">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Marking Criteria</p>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
              Score {weighted.toFixed(2)}
            </span>
          </div>
          <div className="divide-y divide-foreground/8">
            {rubric.map((item) => {
              const remarks = remarksFor(item.code);
              return (
                <div key={item.key} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,14rem)_5.5rem_minmax(0,1fr)] sm:items-center">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span className="flex h-8 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-[11px] font-black text-primary">
                      {item.code}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">{item.label}</p>
                      <p className="text-[11px] font-semibold text-muted-foreground">{Math.round(item.weight * 100)}% weight</p>
                    </div>
                  </div>
                  <div className="flex h-10 items-center justify-center rounded-lg border border-foreground/10 bg-background text-center text-sm font-black text-primary">
                    {asNumber(scores[item.key]).toFixed(1)}
                  </div>
                  <p className="min-h-10 whitespace-pre-wrap rounded-lg border border-foreground/10 bg-background px-3 py-2.5 text-sm text-foreground">
                    {remarks || <span className="text-muted-foreground/70">No remarks</span>}
                  </p>
                </div>
              );
            })}
          </div>
        </section>

        <div className="grid gap-3 sm:grid-cols-3">
          {notes.map(([label, value]) => (
            <div key={label} className="min-w-0">
              <FieldLabel>{label}</FieldLabel>
              <p className="min-h-10 whitespace-pre-wrap rounded-lg border border-foreground/10 bg-background px-3 py-2.5 text-sm text-foreground">
                {value || <span className="text-muted-foreground/70">—</span>}
              </p>
            </div>
          ))}
        </div>
      </ModalBody>
      <ModalFooter className="flex justify-end">
        <button type="button" onClick={onClose} className="inline-flex h-10 items-center justify-center rounded-xl border border-foreground/10 bg-background px-5 text-sm font-bold transition hover:bg-muted active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100">
          Close
        </button>
      </ModalFooter>
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
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-3">
          <label className="block">
            <FieldLabel>Active Group</FieldLabel>
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
        </ModalBody>
        <ModalActions onClose={onClose} submitting={submitting} submitLabel="Promote" />
      </form>
    </ModalShell>
  );
}

function CurriculumSelectionTab({
  lessons,
  assignedItemIds,
  assessedItemIds,
  canEdit,
  submitting,
  error,
  onSave,
}: {
  lessons: Array<Record<string, unknown>>;
  assignedItemIds: number[];
  assessedItemIds: Set<number>;
  canEdit: boolean;
  submitting: boolean;
  error: string;
  onSave: (selectedIds: number[], removedCount: number, removedAssessedCount: number) => void;
}) {
  const [selectedIds, setSelectedIds] = useState<number[]>(assignedItemIds);
  const [search, setSearch] = useState("");
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const assignedSet = useMemo(() => new Set(assignedItemIds), [assignedItemIds]);
  const filteredLessons = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return lessons;
    return lessons.filter((lesson) =>
      [lesson.lesson_number, lesson.lessonNumber, lesson.title, lesson.specification_points, lesson.book_pages]
        .map(asString)
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [lessons, search]);
  const removedIds = assignedItemIds.filter((itemId) => !selectedSet.has(itemId));
  const addedCount = selectedIds.filter((itemId) => !assignedSet.has(itemId)).length;
  const dirty = addedCount > 0 || removedIds.length > 0;

  function toggleLesson(lessonId: number) {
    if (!canEdit || !lessonId) return;
    setSelectedIds((current) =>
      current.includes(lessonId) ? current.filter((itemId) => itemId !== lessonId) : [...current, lessonId],
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-[auto_1fr_auto] sm:items-center">
        <div className="rounded-lg border border-primary/15 bg-primary/5 px-3 py-2">
          <p className="text-lg font-black leading-6 text-primary">{selectedIds.length}</p>
          <p className="text-[10px] font-black uppercase tracking-wide text-primary/80">
            of {lessons.length} lessons selected
          </p>
        </div>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search lessons..."
          aria-label="Search curriculum lessons"
          className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary"
        />
        {canEdit ? (
          <button
            type="button"
            disabled={!dirty || submitting || !selectedIds.length}
            onClick={() => {
              const removedAssessedCount = removedIds.filter((itemId) => assessedItemIds.has(itemId)).length;
              onSave(selectedIds, removedIds.length, removedAssessedCount);
            }}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Save selection"}
          </button>
        ) : null}
      </div>
      {canEdit && dirty && !selectedIds.length ? (
        <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">
          Select at least 1 Teacher Academy lesson.
        </p>
      ) : null}
      {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
      <div className="max-h-[48dvh] overflow-auto rounded-lg border border-foreground/8">
        {filteredLessons.length ? (
          filteredLessons.map((lesson) => {
            const lessonId = asNumber(lesson.id);
            const checked = selectedSet.has(lessonId);
            const assessed = assessedItemIds.has(lessonId);
            return (
              <label
                key={lessonId}
                className={`flex cursor-pointer items-start gap-3 border-b border-foreground/6 px-3 py-2.5 last:border-b-0 ${
                  checked ? "bg-primary/5" : "bg-background"
                } ${canEdit ? "" : "cursor-default"}`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!canEdit}
                  onChange={() => toggleLesson(lessonId)}
                  className="mt-1 shrink-0"
                />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="text-sm font-bold">
                      {asString(lesson.lesson_number) || `Lesson ${asNumber(lesson.item_order)}`} · {asString(lesson.title)}
                    </span>
                    {assessed ? (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-primary">
                        Assessed
                      </span>
                    ) : null}
                  </span>
                  {asString(lesson.specification_points) ? (
                    <span className="mt-0.5 line-clamp-2 block text-[11px] leading-4 text-muted-foreground">
                      {asString(lesson.specification_points)}
                    </span>
                  ) : null}
                </span>
              </label>
            );
          })
        ) : (
          <p className="px-4 py-8 text-center text-sm font-semibold text-muted-foreground">
            {lessons.length ? "No lessons match your search." : "No curriculum lessons found for this subject."}
          </p>
        )}
      </div>
    </div>
  );
}

function AcademyDetailModal({
  teacher,
  state,
  submitting,
  error,
  onClose,
  onPreview,
  onAssess,
  onReview,
  onDeleteAssessment,
  onPromote,
  onSyncLessons,
  allowTeacherPreview,
  canEditLessons,
  canAssess,
  canDeleteAssessment,
  canPromote,
}: {
  teacher: AcademyTeacher;
  state: any;
  submitting: boolean;
  error: string;
  onClose: () => void;
  onPreview: () => void;
  onAssess: (assignment: AcademyAssignment) => void;
  onReview: (assignment: AcademyAssignment, report: Record<string, unknown>) => void;
  onDeleteAssessment: (assessment: Record<string, unknown>) => void;
  onPromote: () => void;
  onSyncLessons: (selectedIds: number[]) => Promise<boolean>;
  allowTeacherPreview: boolean;
  canEditLessons: boolean;
  canAssess: boolean;
  canDeleteAssessment: boolean;
  canPromote: boolean;
}) {
  const assignments = academyAssignments(teacher);
  const assessments = academyAssessments(teacher);
  const progress = teacherProgress(teacher);
  const login = asString(teacher.login);
  const [activeTab, setActiveTab] = useState<"curriculum" | "lessons">(assignments.length ? "lessons" : "curriculum");
  const [pendingSync, setPendingSync] = useState<{
    selectedIds: number[];
    removedCount: number;
    removedAssessedCount: number;
  } | null>(null);

  const curriculumLessons = useMemo(() => {
    const items = Array.isArray(state.props?.adminAcademicCurriculumItems)
      ? state.props.adminAcademicCurriculumItems as Array<Record<string, unknown>>
      : [];
    const programId = asNumber(teacher.subject_program_id);
    return items
      .filter((item) => {
        const itemProgramId = asNumber(item.program_id || item.programId);
        const itemType = asString(item.item_type || item.itemType).toLowerCase();
        return itemProgramId === programId && itemType === "lesson";
      })
      .sort((left, right) => asNumber(left.item_order || left.itemOrder) - asNumber(right.item_order || right.itemOrder));
  }, [state.props?.adminAcademicCurriculumItems, teacher.subject_program_id]);

  const latestAssessmentByAssignment = useMemo(() => {
    const map = new Map<number, Record<string, unknown>>();
    assessments.forEach((assessment) => {
      const assignmentId = asNumber(assessment.lesson_assignment_id);
      if (assignmentId) map.set(assignmentId, assessment);
    });
    return map;
  }, [assessments]);

  const assignedItemIds = useMemo(
    () => assignments.map((assignment) => asNumber(assignment.curriculum_item_id)).filter(Boolean),
    [assignments],
  );
  const assessedItemIds = useMemo(
    () =>
      new Set(
        assignments
          .filter((assignment) => latestAssessmentByAssignment.has(asNumber(assignment.id)))
          .map((assignment) => asNumber(assignment.curriculum_item_id))
          .filter(Boolean),
      ),
    [assignments, latestAssessmentByAssignment],
  );

  async function saveSelection(selectedIds: number[]) {
    const saved = await onSyncLessons(selectedIds);
    if (saved) setPendingSync(null);
    return saved;
  }

  const tabs = [
    { key: "curriculum" as const, label: "Subject Curriculum" },
    { key: "lessons" as const, label: `Assigned Lessons (${assignments.length})` },
  ];

  return (
    <ModalShell title={asString(teacher.full_name)} subtitle={`${asString(teacher.subject)} · ${statusLabel(teacher.academy_status)}`} onClose={onClose} wide>
      <ModalBody>
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

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <div role="tablist" aria-label="Academy teacher sections" className="grid min-w-[16rem] flex-1 grid-cols-2 gap-1 rounded-lg border border-foreground/10 bg-muted/40 p-1">
            {tabs.map((tab) => {
              const active = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setActiveTab(tab.key)}
                  className={`rounded-md py-2 text-xs font-black transition-colors motion-reduce:transition-none ${
                    active ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
          <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
            {allowTeacherPreview ? (
              <button type="button" onClick={onPreview} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-3 text-xs font-bold text-primary hover:bg-primary/10">
                <Eye className="h-3.5 w-3.5" />
                Preview as Teacher
              </button>
            ) : null}
            {canPromote && asString(teacher.academy_status) === "ready_for_active_teacher" ? (
              <button type="button" onClick={onPromote} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground">
                <Trophy className="h-3.5 w-3.5" />
                Promote
              </button>
            ) : null}
          </div>
        </div>

        <div className="mt-3">
          {activeTab === "curriculum" ? (
            <CurriculumSelectionTab
              key={assignedItemIds.join(",")}
              lessons={curriculumLessons}
              assignedItemIds={assignedItemIds}
              assessedItemIds={assessedItemIds}
              canEdit={canEditLessons}
              submitting={submitting}
              error={error}
              onSave={(selectedIds, removedCount, removedAssessedCount) => {
                if (removedCount > 0) {
                  setPendingSync({ selectedIds, removedCount, removedAssessedCount });
                } else {
                  void saveSelection(selectedIds);
                }
              }}
            />
          ) : (
            <div className="max-h-[52dvh] overflow-auto rounded-lg border border-foreground/8">
              {assignments.length ? (
                assignments.map((assignment) => {
                  const report = latestAssessmentByAssignment.get(asNumber(assignment.id));
                  return (
                    <div key={asNumber(assignment.id)} className="border-b border-foreground/6 bg-background px-3 py-2.5 last:border-b-0">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-bold">{asNumber(assignment.sequence_no)}. {asString(assignment.lesson_number)} · {asString(assignment.lesson_topic)}</p>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {dateLabel(assignment.session_datetime)} · {asString(assignment.evaluator_name) || "No evaluator"} · {asString(assignment.status)}
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-1.5">
                          {report ? (
                            <>
                              <span className="rounded-md bg-primary/10 px-2 py-1 text-xs font-bold text-primary">
                                {Number(report.weighted_overall_score || 0).toFixed(2)}
                              </span>
                              <button
                                type="button"
                                onClick={() => onReview(assignment, report)}
                                className="inline-flex items-center gap-1 rounded-md border border-foreground/10 bg-background px-2.5 py-1 text-[11px] font-bold text-foreground hover:bg-muted"
                              >
                                <Eye className="h-3.5 w-3.5" />
                                Review
                              </button>
                              {canDeleteAssessment ? (
                                <button
                                  type="button"
                                  aria-label="Delete assessment report"
                                  title="Delete report"
                                  onClick={() => onDeleteAssessment(report)}
                                  className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-destructive/20 text-destructive hover:bg-destructive/10"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              ) : null}
                            </>
                          ) : canAssess ? (
                            <button type="button" onClick={() => onAssess(assignment)} className="rounded-md bg-foreground px-2.5 py-1 text-[11px] font-bold text-background">
                              Assess
                            </button>
                          ) : null}
                        </div>
                      </div>
                      {report ? (
                        <p className="mt-1 text-[11px] font-bold">
                          {decisionLabel(report.decision)}
                          <span className="font-semibold text-muted-foreground"> · {dateLabel(report.assessment_datetime)} · {asString(report.evaluator_name) || "Evaluator not set"}</span>
                        </p>
                      ) : null}
                      {report && (asString(report.areas_for_improvement) || asString(report.strengths)) ? (
                        <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-muted-foreground">
                          {asString(report.areas_for_improvement) || asString(report.strengths)}
                        </p>
                      ) : !report && asString(assignment.specification_points) ? (
                        <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{asString(assignment.specification_points)}</p>
                      ) : null}
                    </div>
                  );
                })
              ) : (
                <div className="px-4 py-10 text-center">
                  <p className="text-sm font-bold text-muted-foreground">No lessons assigned yet.</p>
                  <p className="mt-1 text-xs font-semibold text-muted-foreground">Pick lessons in the Subject Curriculum tab.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </ModalBody>
      <ConfirmDialog
        open={Boolean(pendingSync)}
        title="Update selected lessons?"
        message={
          pendingSync?.removedAssessedCount ? (
            <>
              This removes {pendingSync.removedCount} lesson{pendingSync.removedCount === 1 ? "" : "s"} from this academy path,
              including {pendingSync.removedAssessedCount} with assessment reports — those reports will be deleted.
            </>
          ) : (
            <>
              This removes {pendingSync?.removedCount} lesson{pendingSync?.removedCount === 1 ? "" : "s"} from this academy path.
            </>
          )
        }
        confirmLabel="Update lessons"
        danger
        busy={submitting}
        onConfirm={() => {
          if (pendingSync) void saveSelection(pendingSync.selectedIds);
        }}
        onCancel={() => {
          if (!submitting) setPendingSync(null);
        }}
      />
    </ModalShell>
  );
}

function AcademyTeacherCard({
  teacher,
  allowTeacherPreview,
  canSchedule,
  canAssess,
  canPromote,
  canDelete,
  onPreview,
  onDetail,
  onSchedule,
  onAssess,
  onPromote,
  onDelete,
  onCopyLogin,
}: {
  teacher: AcademyTeacher;
  allowTeacherPreview: boolean;
  canSchedule: boolean;
  canAssess: boolean;
  canPromote: boolean;
  canDelete: boolean;
  onPreview: () => void;
  onDetail: () => void;
  onSchedule: (assignment: AcademyAssignment) => void;
  onAssess: (assignment: AcademyAssignment) => void;
  onPromote: () => void;
  onDelete: () => void;
  onCopyLogin: (login: string) => void;
}) {
  const assignments = academyAssignments(teacher);
  const progress = teacherProgress(teacher);
  const nextAssignment = nextAcademyAssignment(teacher);
  const login = asString(teacher.login);
  const status = asString(teacher.academy_status);
  const percent = progress.target ? Math.min(100, Math.round((progress.assessed / progress.target) * 100)) : 0;
  const scheduled = assignmentIsScheduled(nextAssignment);
  const primaryAction = nextAssignment && canAssess
    ? {
        label: "Assess",
        icon: <ClipboardCheck className="h-3.5 w-3.5" />,
        onClick: () => onAssess(nextAssignment),
        className: "bg-foreground text-background",
      }
    : assignments.length
      ? {
          label: "Review",
          icon: <Eye className="h-3.5 w-3.5" />,
          onClick: onDetail,
          className: "bg-foreground text-background",
        }
      : {
          label: "Details",
          icon: <Eye className="h-3.5 w-3.5" />,
          onClick: onDetail,
          className: "bg-foreground text-background",
        };
  const secondaryActions: ActionMenuItem[] = [];
  if (nextAssignment && canSchedule) {
    secondaryActions.push({
      key: "schedule",
      label: scheduled ? "Reschedule" : "Schedule",
      icon: <CalendarClock className="h-4 w-4" />,
      onClick: () => onSchedule(nextAssignment),
    });
  }
  secondaryActions.push({
    key: "details",
    label: "Details",
    icon: <Eye className="h-4 w-4" />,
    onClick: onDetail,
  });
  if (allowTeacherPreview) {
    secondaryActions.push({
      key: "preview",
      label: "Preview",
      icon: <Eye className="h-4 w-4" />,
      onClick: onPreview,
    });
  }
  if (canPromote && status === "ready_for_active_teacher") {
    secondaryActions.push(
      { separator: true, key: "promote-separator" },
      {
        key: "promote",
        label: "Promote",
        icon: <Trophy className="h-4 w-4" />,
        onClick: onPromote,
      },
    );
  }
  if (canDelete) {
    secondaryActions.push(
      { separator: true, key: "delete-separator" },
      {
        key: "delete",
        label: "Delete teacher",
        icon: <Trash2 className="h-4 w-4" />,
        onClick: onDelete,
        danger: true,
      },
    );
  }

  return (
    <article className="rounded-lg border border-foreground/10 bg-background p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <button type="button" onClick={onDetail} className="min-w-0 flex-1 text-left">
          <h3 className="truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</h3>
          <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
        </button>
        <StatusBadge tone={academyStatusTone(status)} className="shrink-0 text-[10px]">
          {statusLabel(status)}
        </StatusBadge>
      </div>

      <div className="mt-3 grid grid-cols-[6.5rem_1fr] gap-3">
        <div className="min-w-0">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Progress</span>
            <span className="text-[10px] font-black text-foreground">{percent}%</span>
          </div>
          <ProgressBar value={percent} className="h-1.5 bg-muted" />
          <p className="mt-1 text-xs font-black text-foreground">{progress.assessed}/{progress.target}</p>
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Next</p>
          <p className="mt-1 truncate text-xs font-black text-foreground">
            {nextAssignment ? assignmentTitle(nextAssignment) : assignments.length ? "No pending lesson" : "No lessons assigned"}
          </p>
          <p className="mt-0.5 truncate text-[11px] font-semibold text-muted-foreground">
            {nextAssignment ? `${dateLabel(nextAssignment.session_datetime)} · ${asString(nextAssignment.evaluator_name) || "No evaluator"}` : `Avg ${progress.average == null ? "-" : progress.average.toFixed(2)}`}
          </p>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2 text-[11px]">
        <span className="min-w-0 flex-1 truncate rounded-md bg-muted px-2 py-1 font-mono font-black text-foreground">
          {login || "Account pending"}
        </span>
        <IconButton
          label="Copy teacher login"
          disabled={!login}
          onClick={() => onCopyLogin(login)}
          className="h-7 w-7 rounded-md"
        >
          <Copy className="h-3.5 w-3.5" />
        </IconButton>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={primaryAction.onClick}
          className={`inline-flex h-9 min-w-0 flex-1 items-center justify-center gap-1 rounded-lg px-3 text-xs font-black transition active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100 ${primaryAction.className}`}
        >
          {primaryAction.icon}
          <span className="truncate">{primaryAction.label}</span>
        </button>
        <ActionMenu items={secondaryActions} label={`Actions for ${asString(teacher.full_name) || "academy teacher"}`} />
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
  mobileMode = "sheet",
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
  mobileMode?: "sheet" | "fullscreen";
}) {
  return (
    <Modal
      title={title}
      subtitle={subtitle}
      onClose={onClose}
      size={wide ? "wide" : "lg"}
      mobileMode={mobileMode}
    >
      {children}
    </Modal>
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
    <ModalFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
      <button type="button" onClick={onClose} className="min-h-10 w-full rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted sm:w-auto">
        Cancel
      </button>
      <button type="submit" disabled={submitting || disabled} className="min-h-10 w-full rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60 sm:w-auto">
        {submitting ? "Saving..." : submitLabel}
      </button>
    </ModalFooter>
  );
}

export function TeacherAcademyPanel({
  state,
  academyTeachers,
  onAcademyChange,
  onTeachersChange,
  showToast,
  allowTeacherPreview = false,
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
  const [reportTarget, setReportTarget] = useState<{ teacher: AcademyTeacher; assignment: AcademyAssignment; report: Record<string, unknown> } | null>(null);
  const [promoteTeacher, setPromoteTeacher] = useState<AcademyTeacher | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AcademyTeacher | null>(null);
  const [assessmentDeleteTarget, setAssessmentDeleteTarget] = useState<{ teacher: AcademyTeacher; assessment: Record<string, unknown> } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [directorAcademyTab, setDirectorAcademyTab] = useState<"teachers" | "lessons">("teachers");
  const [directorTeachersView, setDirectorTeachersView] = useState<"academy" | "active">("academy");

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
        setDetailTeacher(updated || null);
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
  const academyApi = useMemo(() => teacherAcademyActionRoutes(adminMode, authRole), [adminMode, authRole]);
  const canCreateHeadOfDepartment = adminMode === "academic_director" || authRole === "academic_director";
  const canCreateAcademyTeacher = Boolean(academyApi.create) && adminMode !== "head_of_department" && authRole !== "head_of_department";
  const canScheduleAcademyLesson = Boolean(academyApi.assignmentUpdate(0));
  const canAssessAcademyLesson = Boolean(academyApi.assessmentCreate(0));
  const canEditAcademyLessons = Boolean(academyApi.lessonsSync(0));
  const canDeleteAssessmentReport = Boolean(academyApi.assessmentDelete(0, 0));
  const canPromoteAcademyTeacher = Boolean(academyApi.promote) && adminMode !== "head_of_department" && authRole !== "head_of_department";
  const canDeleteAcademyTeacher = Boolean(academyApi.delete) && adminMode !== "head_of_department" && authRole !== "head_of_department";
  const isAcademicDirectorMode = adminMode === "academic_director" || authRole === "academic_director";

  const sortedTeachers = [...academyTeachers].sort((left, right) => {
    const leftReady = asString(left.academy_status) === "ready_for_active_teacher" ? 1 : 0;
    const rightReady = asString(right.academy_status) === "ready_for_active_teacher" ? 1 : 0;
    if (leftReady !== rightReady) return rightReady - leftReady;
    return asString(right.updated_at).localeCompare(asString(left.updated_at));
  });
  const activeTeachers = useMemo(() => {
    const rows = Array.isArray(state.teachers)
      ? state.teachers as Array<Record<string, unknown>>
      : Array.isArray(state.props?.adminTeachers)
        ? state.props.adminTeachers as Array<Record<string, unknown>>
        : [];
    return rows.filter((teacher) => {
      const employmentType = asString(teacher.employment_type || teacher.teacher_employment_type).toLowerCase();
      const status = asString(teacher.status || teacher.teacher_status || "active").toLowerCase();
      return employmentType !== "academy" && !["inactive", "deleted", "archived"].includes(status);
    });
  }, [state.props?.adminTeachers, state.teachers]);
  const appointedLessons = useMemo(
    () =>
      academyTeachers
        .flatMap((teacher) =>
          academyAssignments(teacher).map((assignment) => ({
            key: `${asNumber(teacher.id)}:${asNumber(assignment.id)}`,
            teacher,
            assignment,
          })),
        )
        .sort((left, right) => {
          const leftDate = Date.parse(asString(left.assignment.session_datetime));
          const rightDate = Date.parse(asString(right.assignment.session_datetime));
          const leftHasDate = Number.isFinite(leftDate);
          const rightHasDate = Number.isFinite(rightDate);
          if (leftHasDate && rightHasDate && leftDate !== rightDate) return leftDate - rightDate;
          if (leftHasDate !== rightHasDate) return leftHasDate ? -1 : 1;
          const teacherCompare = asString(left.teacher.full_name).localeCompare(asString(right.teacher.full_name));
          if (teacherCompare !== 0) return teacherCompare;
          return asNumber(left.assignment.sequence_no) - asNumber(right.assignment.sequence_no);
        }),
    [academyTeachers],
  );

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
    if (typeof state.switchWorkspaceMode === "function") {
      state.switchWorkspaceMode("teacher");
    }
  }

  function openPromote(teacher: AcademyTeacher) {
    if (!canPromoteAcademyTeacher) {
      showToast("Promotion is available to Academic Director or Admin.", "danger");
      return;
    }
    setPromoteTeacher(teacher);
  }

  async function confirmDeleteAcademyTeacher() {
    if (!deleteTarget || !academyApi.delete) return;
    const teacherId = asNumber(deleteTarget.id);
    if (!teacherId) {
      showToast("Academy teacher id is missing.", "danger");
      setDeleteTarget(null);
      return;
    }
    const result = await submit(academyApi.delete(teacherId), {}, "Academy teacher deleted.");
    if (result) {
      if (detailTeacher && asNumber(detailTeacher.id) === teacherId) {
        setDetailTeacher(null);
      }
      setDeleteTarget(null);
    }
  }

  async function syncAcademyLessons(teacher: AcademyTeacher, selectedIds: number[]) {
    const teacherId = asNumber(teacher.id);
    if (!teacherId) {
      showToast("Academy teacher id is missing.", "danger");
      return false;
    }
    const result = await submit(
      academyApi.lessonsSync(teacherId),
      { academy_curriculum_item_ids: selectedIds.join(",") },
      "Academy lessons updated.",
    );
    return Boolean(result);
  }

  async function confirmDeleteAssessmentReport() {
    if (!assessmentDeleteTarget) return;
    const teacherId = asNumber(assessmentDeleteTarget.teacher.id);
    const assessmentId = asNumber(assessmentDeleteTarget.assessment.id);
    if (!teacherId || !assessmentId) {
      showToast("Assessment report id is missing.", "danger");
      setAssessmentDeleteTarget(null);
      return;
    }
    const result = await submit(
      academyApi.assessmentDelete(teacherId, assessmentId),
      {},
      "Assessment report deleted.",
    );
    if (result) {
      setAssessmentDeleteTarget(null);
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
            const result = await submit(academyApi.create, fields, "Academy teacher created.");
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
      {detailTeacher && !scheduleTarget && !assessmentTarget && !reportTarget && !promoteTeacher ? (
        <AcademyDetailModal
          teacher={detailTeacher}
          state={state}
          submitting={submitting}
          error={error}
          onClose={() => setDetailTeacher(null)}
          onPreview={() => previewAsTeacher(detailTeacher)}
          allowTeacherPreview={allowTeacherPreview}
          onAssess={(nextAssignment) => {
            setError("");
            setAssessmentTarget({ teacher: detailTeacher, assignment: nextAssignment });
          }}
          onReview={(assignment, report) => {
            setError("");
            setReportTarget({ teacher: detailTeacher, assignment, report });
          }}
          onDeleteAssessment={(assessment) => {
            setError("");
            setAssessmentDeleteTarget({ teacher: detailTeacher, assessment });
          }}
          onPromote={() => {
            setError("");
            openPromote(detailTeacher);
          }}
          onSyncLessons={(selectedIds) => syncAcademyLessons(detailTeacher, selectedIds)}
          canEditLessons={canEditAcademyLessons}
          canAssess={canAssessAcademyLesson}
          canDeleteAssessment={canDeleteAssessmentReport}
          canPromote={canPromoteAcademyTeacher}
        />
      ) : null}
      {scheduleTarget ? (
        <AssignmentModal
          teacher={scheduleTarget.teacher}
          assignment={scheduleTarget.assignment}
          submitting={submitting}
          error={error}
          onSubmit={async (assignmentId, fields) => {
            if (await submit(academyApi.assignmentUpdate(assignmentId), fields, "Academy lesson updated.")) {
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
          submitting={submitting}
          error={error}
          onSubmit={async (teacherId, fields) => {
            if (await submit(academyApi.assessmentCreate(teacherId), fields, "Assessment saved.")) {
              setAssessmentTarget(null);
            }
          }}
          onClose={() => {
            setError("");
            setAssessmentTarget(null);
          }}
        />
      ) : null}
      {reportTarget && !assessmentTarget ? (
        <ReportModal
          teacher={reportTarget.teacher}
          assignment={reportTarget.assignment}
          report={reportTarget.report}
          onClose={() => setReportTarget(null)}
        />
      ) : null}
      {promoteTeacher && academyApi.promote ? (
        <PromoteModal
          teacher={promoteTeacher}
          state={state}
          submitting={submitting}
          error={error}
          onSubmit={async (teacherId, fields) => {
            if (academyApi.promote && await submit(academyApi.promote(teacherId), fields, "Teacher promoted.")) {
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
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete academy teacher?"
        message={
          <>
            This removes the academy teacher record, assigned lessons, assessment reports, and the generated academy-only login.
          </>
        }
        confirmLabel="Delete teacher"
        danger
        busy={submitting}
        onConfirm={confirmDeleteAcademyTeacher}
        onCancel={() => {
          if (!submitting) setDeleteTarget(null);
        }}
      />
      <ConfirmDialog
        open={Boolean(assessmentDeleteTarget)}
        title="Delete assessment report?"
        message={
          <>
            This removes the selected report and recalculates the lesson progress.
          </>
        }
        confirmLabel="Delete report"
        danger
        busy={submitting}
        onConfirm={confirmDeleteAssessmentReport}
        onCancel={() => {
          if (!submitting) setAssessmentDeleteTarget(null);
        }}
      />

      <ChartCard
        title="Teacher Academy"
        subtitle="New teachers in selected Teacher Academy lessons"
        icon={<GraduationCap className="h-4 w-4 text-info" />}
        className="flex min-h-0 flex-1 flex-col"
        bodyClassName="flex min-h-0 flex-1 flex-col"
        headerActions={
          <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:justify-end">
            {canCreateHeadOfDepartment ? (
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setHodOpen(true);
                }}
                className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1.5 rounded-lg border border-foreground/10 bg-surface px-2 py-1.5 text-xs font-black leading-tight text-foreground hover:bg-muted sm:px-3 sm:text-sm"
              >
                <Plus className="h-4 w-4" />
                <span className="truncate">New HOD</span>
              </button>
            ) : null}
            {canCreateAcademyTeacher ? (
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setCreateOpen(true);
                }}
                className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1.5 rounded-lg bg-primary px-2 py-1.5 text-xs font-black leading-tight text-primary-foreground sm:px-3 sm:text-sm"
              >
                <Plus className="h-4 w-4" />
                <span className="truncate sm:hidden">New Teacher</span>
                <span className="hidden truncate sm:inline">New Academy Teacher</span>
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
        <div className="mb-3 grid shrink-0 grid-cols-3 gap-2">
          {metric("In Academy", stats.inTraining, "active academy paths")}
          {metric("Ready", stats.ready, "promotion review")}
          {metric("Avg Score", stats.average == null ? "-" : stats.average.toFixed(2), "weighted average")}
        </div>
        {isAcademicDirectorMode ? (
          <div className="mb-3 space-y-2">
            <div role="tablist" aria-label="Teacher Academy workspace" className="grid grid-cols-2 gap-1 rounded-lg border border-foreground/10 bg-muted/40 p-1">
              {[
                { key: "teachers", label: "Teachers", count: sortedTeachers.length + activeTeachers.length },
                { key: "lessons", label: "Appointed Lessons", count: appointedLessons.length },
              ].map((tab) => {
                const active = directorAcademyTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => setDirectorAcademyTab(tab.key as "teachers" | "lessons")}
                    className={`min-h-9 rounded-md px-3 text-xs font-black transition-colors motion-reduce:transition-none ${
                      active ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {tab.label}
                    <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px]">{tab.count}</span>
                  </button>
                );
              })}
            </div>
            {directorAcademyTab === "teachers" ? (
              <div role="tablist" aria-label="Teacher list type" className="inline-grid grid-cols-2 gap-1 rounded-lg border border-foreground/10 bg-background p-1">
                {[
                  { key: "academy", label: "Teacher Academy", count: sortedTeachers.length },
                  { key: "active", label: "Active Teachers", count: activeTeachers.length },
                ].map((tab) => {
                  const active = directorTeachersView === tab.key;
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      role="tab"
                      aria-selected={active}
                      onClick={() => setDirectorTeachersView(tab.key as "academy" | "active")}
                      className={`min-h-8 rounded-md px-3 text-[11px] font-black transition-colors motion-reduce:transition-none ${
                        active ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                    >
                      {tab.label}
                      <span className="ml-2 opacity-75">{tab.count}</span>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
        ) : null}
        {isAcademicDirectorMode && directorAcademyTab === "lessons" ? (
          <div className="overflow-hidden rounded-lg border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
            {appointedLessons.length ? (
              <>
                <MobileCardList className="p-3">
                  {appointedLessons.map(({ key, teacher, assignment }) => {
                    const report = assessmentForAssignment(teacher, assignment);
                    return (
                    <article key={key} className="rounded-lg border border-foreground/10 bg-background p-3 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="truncate text-sm font-black text-foreground">{assignmentTitle(assignment)}</h3>
                          <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">
                            {asString(teacher.full_name) || "Academy teacher"} · {asString(teacher.subject) || "Subject not set"}
                          </p>
                        </div>
                        {report ? (
                          <StatusBadge tone={decisionTone(report.decision)} className="shrink-0 text-[10px]">
                            {decisionLabel(report.decision)}
                          </StatusBadge>
                        ) : (
                          <StatusBadge tone={assignmentIsScheduled(assignment) ? "success" : "info"} className="shrink-0 text-[10px]">
                            {assignmentIsScheduled(assignment) ? "Scheduled" : "Appointed"}
                          </StatusBadge>
                        )}
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <p className="font-black uppercase tracking-wide text-muted-foreground">Time</p>
                          <p className="mt-0.5 font-bold text-foreground">{dateLabel(assignment.session_datetime)}</p>
                        </div>
                        <div>
                          <p className="font-black uppercase tracking-wide text-muted-foreground">{report ? "Score" : "Evaluator"}</p>
                          <p className="mt-0.5 truncate font-bold text-foreground">
                            {report ? Number(report.weighted_overall_score || 0).toFixed(2) : asString(assignment.evaluator_name) || "Not assigned"}
                          </p>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {report ? (
                          <button type="button" onClick={() => setReportTarget({ teacher, assignment, report })} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-foreground px-3 text-xs font-bold text-background">
                            <Eye className="h-3.5 w-3.5" />
                            Review
                          </button>
                        ) : (
                          <>
                            {canScheduleAcademyLesson ? (
                              <button type="button" onClick={() => setScheduleTarget({ teacher, assignment })} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 px-3 text-xs font-bold hover:bg-muted">
                                <CalendarClock className="h-3.5 w-3.5" />
                                {assignmentIsScheduled(assignment) ? "Reschedule" : "Schedule"}
                              </button>
                            ) : null}
                            {canAssessAcademyLesson ? (
                              <button type="button" onClick={() => setAssessmentTarget({ teacher, assignment })} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-foreground px-3 text-xs font-bold text-background">
                                <ClipboardCheck className="h-3.5 w-3.5" />
                                Assess
                              </button>
                            ) : null}
                          </>
                        )}
                      </div>
                    </article>
                    );
                  })}
                </MobileCardList>
                <ResponsiveTable className="max-h-[calc(100dvh-20rem)] rounded-xl border border-[#DDE4EF] bg-white shadow-sm 2xl:max-h-[48rem]">
                  <table className="w-full min-w-[960px] table-fixed border-collapse text-left">
                    <colgroup>
                      <col className="w-[18%]" />
                      <col className="w-[13%]" />
                      <col className="w-[21%]" />
                      <col className="w-[12%]" />
                      <col className="w-[11%]" />
                      <col className="w-[9%]" />
                      <col className="w-[16%]" />
                    </colgroup>
                    <thead className="sticky top-0 z-10 border-b border-[#DDE4EF] bg-[#F8FAFD]">
                      <tr>
                        {["Teacher", "Subject", "Appointed Lesson", "Time", "Evaluator", "Status", "Actions"].map((heading) => (
                          <th key={heading} className="px-3 py-2.5 text-[10px] font-black uppercase tracking-[0.16em] text-[#64748B]">
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DDE4EF] bg-white">
                      {appointedLessons.map(({ key, teacher, assignment }, index) => (
                        <tr
                          key={key}
                          className="group animate-in fade-in slide-in-from-bottom-1 transition-colors duration-150 hover:bg-[#FAFBFE] motion-reduce:animate-none"
                          style={{ animationDelay: `${index * 20}ms` }}
                        >
                          <td className="px-3 py-2.5 align-middle">
                            <button type="button" onClick={() => setDetailTeacher(teacher)} className="truncate text-left text-sm font-black leading-tight text-[#0F172A] group-hover:underline">
                              {asString(teacher.full_name) || "Academy teacher"}
                            </button>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="line-clamp-2 text-xs font-black text-[#0F172A]">{asString(teacher.subject) || "Subject not set"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <p className="line-clamp-2 text-xs font-black text-[#0F172A]">{assignmentTitle(assignment)}</p>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="block text-xs font-bold text-[#64748B]">{dateLabel(assignment.session_datetime)}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="block truncate text-xs font-bold text-[#64748B]">{asString(assignment.evaluator_name) || "Not assigned"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            {(() => {
                              const report = assessmentForAssignment(teacher, assignment);
                              if (report) {
                                return (
                                  <StatusBadge tone={decisionTone(report.decision)} className="text-[10px]">
                                    {decisionLabel(report.decision)}
                                  </StatusBadge>
                                );
                              }
                              return (
                                <StatusBadge tone={assignmentIsScheduled(assignment) ? "success" : "info"} className="text-[10px]">
                                  {assignmentIsScheduled(assignment) ? "Scheduled" : "Appointed"}
                                </StatusBadge>
                              );
                            })()}
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            {(() => {
                              const report = assessmentForAssignment(teacher, assignment);
                              if (report) {
                                return (
                                  <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
                                    <span className="inline-flex h-8 items-center rounded-lg bg-primary/10 px-2.5 text-[11px] font-black text-primary">
                                      {Number(report.weighted_overall_score || 0).toFixed(2)}
                                    </span>
                                    <button type="button" onClick={() => setReportTarget({ teacher, assignment, report })} className="inline-flex h-8 min-w-[6rem] items-center justify-center gap-1 rounded-lg bg-[#0F172A] px-2.5 text-[11px] font-bold text-white transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                      <Eye className="h-3.5 w-3.5" />
                                      Review
                                    </button>
                                  </div>
                                );
                              }
                              const rowActions: ActionMenuItem[] = [];
                              if (canScheduleAcademyLesson && canAssessAcademyLesson) {
                                rowActions.push({
                                  key: "schedule",
                                  label: assignmentIsScheduled(assignment) ? "Reschedule" : "Schedule",
                                  icon: <CalendarClock className="h-4 w-4" />,
                                  onClick: () => setScheduleTarget({ teacher, assignment }),
                                });
                              }
                              return (
                                <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
                                  {canAssessAcademyLesson ? (
                                    <button type="button" onClick={() => setAssessmentTarget({ teacher, assignment })} className="inline-flex h-8 min-w-[6rem] items-center justify-center gap-1 rounded-lg bg-[#0F172A] px-2.5 text-[11px] font-bold text-white transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                      <ClipboardCheck className="h-3.5 w-3.5" />
                                      Assess
                                    </button>
                                  ) : canScheduleAcademyLesson ? (
                                    <button type="button" onClick={() => setScheduleTarget({ teacher, assignment })} className="inline-flex h-8 min-w-[6rem] items-center justify-center gap-1 rounded-lg bg-[#0F172A] px-2.5 text-[11px] font-bold text-white transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                      <CalendarClock className="h-3.5 w-3.5" />
                                      {assignmentIsScheduled(assignment) ? "Reschedule" : "Schedule"}
                                    </button>
                                  ) : null}
                                  {rowActions.length ? (
                                    <ActionMenu label={`Actions for ${asString(teacher.full_name) || "academy teacher"}`} items={rowActions} />
                                  ) : null}
                                </div>
                              );
                            })()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ResponsiveTable>
              </>
            ) : (
              <EmptyState
                icon={<CalendarClock className="h-6 w-6" />}
                title="No appointed lessons yet."
                detail="Appointed Teacher Academy lessons will appear here after lessons are selected for academy teachers."
                className="min-h-[22rem]"
              />
            )}
          </div>
        ) : isAcademicDirectorMode && directorAcademyTab === "teachers" && directorTeachersView === "active" ? (
          <div className="overflow-hidden rounded-lg border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
            {activeTeachers.length ? (
              <>
                <MobileCardList className="p-3">
                  {activeTeachers.map((teacher, index) => (
                    <article key={asNumber(teacher.id) || asString(teacher.login) || index} className="rounded-lg border border-foreground/10 bg-background p-3 shadow-sm">
                      <div className="flex items-start gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#E8EBF3] text-xs font-black text-[#1E2B72]">
                          {initialsFromName(teacher.full_name)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <h3 className="truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Teacher"}</h3>
                          <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subjects || teacher.subject) || "Subject not set"}</p>
                          <p className="mt-1 truncate font-mono text-[11px] font-bold text-muted-foreground">{asString(teacher.login) || asString(teacher.teacher_code) || "Login not set"}</p>
                        </div>
                      </div>
                    </article>
                  ))}
                </MobileCardList>
                <ResponsiveTable className="max-h-[calc(100dvh-20rem)] rounded-xl border border-[#DDE4EF] bg-white shadow-sm 2xl:max-h-[48rem]">
                  <table className="w-full min-w-[780px] table-fixed border-collapse text-left">
                    <colgroup>
                      <col className="w-[24%]" />
                      <col className="w-[22%]" />
                      <col className="w-[18%]" />
                      <col className="w-[18%]" />
                      <col className="w-[18%]" />
                    </colgroup>
                    <thead className="sticky top-0 z-10 border-b border-[#DDE4EF] bg-[#F8FAFD]">
                      <tr>
                        {["Teacher", "Subject", "Group", "Contact", "Status"].map((heading) => (
                          <th key={heading} className="px-3 py-2.5 text-[10px] font-black uppercase tracking-[0.16em] text-[#64748B]">
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#DDE4EF] bg-white">
                      {activeTeachers.map((teacher, index) => (
                        <tr
                          key={asNumber(teacher.id) || asString(teacher.login) || index}
                          className="group animate-in fade-in slide-in-from-bottom-1 transition-colors duration-150 hover:bg-[#FAFBFE] motion-reduce:animate-none"
                          style={{ animationDelay: `${index * 20}ms` }}
                        >
                          <td className="px-3 py-2.5 align-middle">
                            <div className="flex min-w-0 items-center gap-2">
                              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#E8EBF3] text-xs font-black text-[#1E2B72]">
                                {initialsFromName(teacher.full_name)}
                              </span>
                              <span className="min-w-0">
                                <span className="block truncate text-sm font-black text-[#0F172A]">{asString(teacher.full_name) || "Teacher"}</span>
                                <span className="block truncate font-mono text-[11px] font-bold text-[#64748B]">{asString(teacher.login) || asString(teacher.teacher_code) || "Login not set"}</span>
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="line-clamp-2 text-xs font-black text-[#0F172A]">{asString(teacher.subjects || teacher.subject) || "Subject not set"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="block truncate text-xs font-bold text-[#64748B]">{asString(teacher.assigned_group || teacher.group_name || teacher.group) || "Not assigned"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="block truncate text-xs font-bold text-[#64748B]">{asString(teacher.telegram_username || teacher.phone || teacher.email) || "Not set"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <StatusBadge tone="success" className="text-[10px]">
                              {asString(teacher.status || teacher.teacher_status) || "Active"}
                            </StatusBadge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ResponsiveTable>
              </>
            ) : (
              <EmptyState
                icon={<UsersRound className="h-6 w-6" />}
                title="No active teachers found."
                detail="Active teacher records will appear here when they are available in the academic context."
                className="min-h-[22rem]"
              />
            )}
          </div>
        ) : (
        <div className="overflow-hidden rounded-lg border border-foreground/10 bg-background shadow-sm animate-in fade-in slide-in-from-bottom-1 duration-200 motion-reduce:animate-none">
          {sortedTeachers.length ? (
            <>
              <MobileCardList className="p-3">
                {sortedTeachers.map((teacher) => {
                  return (
                    <AcademyTeacherCard
                      key={asNumber(teacher.id)}
                      teacher={teacher}
                      allowTeacherPreview={allowTeacherPreview}
                      canSchedule={canScheduleAcademyLesson}
                      canAssess={canAssessAcademyLesson}
                      canDelete={canDeleteAcademyTeacher}
                      onPreview={() => previewAsTeacher(teacher)}
                      onDetail={() => setDetailTeacher(teacher)}
                      onSchedule={(targetAssignment) => setScheduleTarget({ teacher, assignment: targetAssignment })}
                      onAssess={(targetAssignment) => setAssessmentTarget({ teacher, assignment: targetAssignment })}
                      onPromote={() => openPromote(teacher)}
                      onDelete={() => {
                        setError("");
                        setDeleteTarget(teacher);
                      }}
                      onCopyLogin={copyLogin}
                      canPromote={canPromoteAcademyTeacher}
                    />
                  );
                })}
              </MobileCardList>
              <ResponsiveTable className="max-h-[calc(100dvh-20rem)] rounded-xl border border-[#DDE4EF] bg-white shadow-sm 2xl:max-h-[48rem]">
                <table className="w-full min-w-[980px] table-fixed border-collapse text-left">
                  <colgroup>
                    <col className="w-[20%]" />
                    <col className="w-[14%]" />
                    <col className="w-[13%]" />
                    <col className="w-[17%]" />
                    <col className="w-[13%]" />
                    <col className="w-[7%]" />
                    <col className="w-[16%]" />
                  </colgroup>
                  <thead className="sticky top-0 z-10 border-b border-[#DDE4EF] bg-[#F8FAFD]">
                    <tr>
                      {["Teacher", "Subject", "Progress", "Next lesson", "Evaluator", "Score", "Actions"].map((heading) => (
                        <th
                          key={heading}
                          className="px-3 py-2.5 text-[10px] font-black uppercase tracking-[0.16em] text-[#64748B]"
                        >
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#DDE4EF] bg-white">
                    {sortedTeachers.map((teacher, index) => {
                      const progress = teacherProgress(teacher);
                      const nextAssignment = nextAcademyAssignment(teacher);
                      const percent = progress.target ? Math.min(100, Math.round((progress.assessed / progress.target) * 100)) : 0;
                      const status = asString(teacher.academy_status);
                      const login = asString(teacher.login);
                      const scheduled = assignmentIsScheduled(nextAssignment);
                      const canUsePrimaryLessonAction = nextAssignment && canAssessAcademyLesson;
                      const rowActions: ActionMenuItem[] = [];
                      if (nextAssignment && canScheduleAcademyLesson) {
                        rowActions.push({
                          key: "schedule",
                          label: scheduled ? "Reschedule" : "Schedule",
                          icon: <CalendarClock className="h-4 w-4" />,
                          onClick: () => setScheduleTarget({ teacher, assignment: nextAssignment }),
                        });
                      }
                      rowActions.push({
                        key: "details",
                        label: "Details",
                        icon: <Eye className="h-4 w-4" />,
                        onClick: () => setDetailTeacher(teacher),
                      });
                      if (allowTeacherPreview) {
                        rowActions.push({
                          key: "preview",
                          label: "Preview",
                          icon: <Eye className="h-4 w-4" />,
                          onClick: () => previewAsTeacher(teacher),
                        });
                      }
                      if (canPromoteAcademyTeacher && status === "ready_for_active_teacher") {
                        rowActions.push(
                          { separator: true, key: "promote-separator" },
                          {
                            key: "promote",
                            label: "Promote",
                            icon: <Trophy className="h-4 w-4" />,
                            onClick: () => openPromote(teacher),
                          },
                        );
                      }
                      if (canDeleteAcademyTeacher) {
                        rowActions.push(
                          { separator: true, key: "delete-separator" },
                          {
                            key: "delete",
                            label: "Delete teacher",
                            icon: <Trash2 className="h-4 w-4" />,
                            onClick: () => {
                              setError("");
                              setDeleteTarget(teacher);
                            },
                            danger: true,
                          },
                        );
                      }
                      return (
                        <tr
                          key={asNumber(teacher.id)}
                          className="group animate-in fade-in slide-in-from-bottom-1 transition-colors duration-150 hover:bg-[#FAFBFE] motion-reduce:animate-none"
                          style={{ animationDelay: `${index * 30}ms` }}
                        >
                          <td className="px-3 py-2.5 align-middle">
                            <div className="flex min-w-0 items-center gap-2 text-left">
                              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#E8EBF3] text-xs font-black text-[#1E2B72]">
                                {initialsFromName(teacher.full_name)}
                              </span>
                              <span className="flex min-w-0 flex-1 items-baseline gap-2">
                                <button
                                  type="button"
                                  onClick={() => setDetailTeacher(teacher)}
                                  className="min-w-0 truncate text-left text-sm font-black leading-tight text-[#0F172A] group-hover:underline"
                                >
                                  {asString(teacher.full_name) || "Academy teacher"}
                                </button>
                                <span className="shrink-0 font-mono text-[11px] font-bold text-[#64748B]">{login || "Creating..."}</span>
                              </span>
                            </div>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="line-clamp-2 text-xs font-black text-[#0F172A]">{asString(teacher.subject) || "Subject not set"}</span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <div className="min-w-0">
                              <div className="mb-1 flex items-center justify-between gap-2">
                                <span className="text-[11px] font-black text-[#0F172A]">{progress.assessed}/{progress.target}</span>
                                <span className="text-[10px] font-bold text-[#64748B]">{percent}%</span>
                              </div>
                              <ProgressBar value={percent} className="h-1.5 bg-[#EEF2F7]" fillClassName="bg-[#3D5AEA]" />
                            </div>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            {nextAssignment ? (
                              <p className="truncate text-xs font-black text-[#0F172A]">{assignmentTitle(nextAssignment)}</p>
                            ) : (
                              <span className="text-xs font-semibold text-[#64748B]">No academy lessons assigned</span>
                            )}
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className="block truncate text-xs font-bold text-[#64748B]">
                              {nextAssignment ? asString(nextAssignment.evaluator_name) || "Not assigned" : "Not assigned"}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <span className={`text-sm font-black tabular-nums ${
                              progress.average != null && progress.average >= 8 ? "text-[#3BC379]" : "text-[#0F172A]"
                            }`}>
                              {progress.average == null ? "-" : progress.average.toFixed(2)}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 align-middle">
                            <div className="flex items-center justify-end gap-1.5 whitespace-nowrap">
                              {canUsePrimaryLessonAction ? (
                                <button
                                  type="button"
                                  onClick={() => setAssessmentTarget({ teacher, assignment: nextAssignment })}
                                  className="inline-flex h-8 min-w-[6rem] items-center justify-center gap-1 rounded-lg bg-[#0F172A] px-2.5 text-[11px] font-bold text-white transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100"
                                >
                                  <ClipboardCheck className="h-3.5 w-3.5" />
                                  Assess
                                </button>
                              ) : academyAssignments(teacher).length ? (
                                <button type="button" onClick={() => setDetailTeacher(teacher)} className="inline-flex h-8 min-w-[6rem] items-center justify-center gap-1 rounded-lg bg-[#0F172A] px-2.5 text-[11px] font-bold text-white transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                  <Eye className="h-3.5 w-3.5" />
                                  Review
                                </button>
                              ) : (
                                <button type="button" onClick={() => setDetailTeacher(teacher)} className="inline-flex h-8 min-w-[6rem] items-center justify-center gap-1 rounded-lg bg-[#0F172A] px-2.5 text-[11px] font-bold text-white transition hover:-translate-y-px hover:shadow-card active:scale-[0.98] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100">
                                  <Eye className="h-3.5 w-3.5" />
                                  Details
                                </button>
                              )}
                              <ActionMenu
                                label={`Actions for ${asString(teacher.full_name) || "academy teacher"}`}
                                items={rowActions}
                              />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </ResponsiveTable>
            </>
          ) : (
            <EmptyState
              icon={<BookOpenCheck className="h-6 w-6" />}
              title="No academy teachers yet."
              detail="Create a trainee and choose the curriculum lessons for their Teacher Academy lesson plan."
              className="min-h-[22rem]"
            />
          )}
        </div>
        )}
      </ChartCard>
    </>
  );
}
