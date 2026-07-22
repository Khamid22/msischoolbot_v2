import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { BookOpenCheck, CalendarClock, CheckCircle2, ClipboardCheck, Copy, Eye, KeyRound, RefreshCw, Trash2, Trophy, UsersRound, XCircle } from "lucide-react";

import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { IconButton } from "@/shared/ui/IconButton";
import { MetricCard } from "@/shared/ui/MetricCard";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { asNumber, asString } from "@/shared/lib/workspace";
import { formatUzs, semesterStages, suggestedLessonRate, teacherCategories } from "@/features/people/teachers/model";
import {
  academyAssessments as typedAcademyAssessments,
  academyAssignments as typedAcademyAssignments,
  academyTeacherProgress,
  type AcademyAssessment,
  type AcademyAssignment,
  type AcademyOptionRow,
  type AcademyTeacher,
  type ActiveTeacher,
  type GeneratedCredentials,
  type TeacherAcademyMode,
} from "@/features/teacher-academy/model";

export type TeacherAcademyPanelState = {
  managementMode: TeacherAcademyMode;
  currentSchool: string;
  teachers: ActiveTeacher[];
  setTeachers: (rows: ActiveTeacher[]) => void;
  academyTeachers: AcademyTeacher[];
  setAcademyTeachers: (rows: AcademyTeacher[]) => void;
  filteredGroupOptions: Array<{ name: string }>;
  props: {
    csrfToken?: string;
    authRole?: string;
    managementMode?: TeacherAcademyMode;
    managementTeachers?: ActiveTeacher[];
    academicManagementSubjects?: AcademyOptionRow[];
    academicManagementCurriculumPrograms?: AcademyOptionRow[];
    academicManagementCurriculumItems?: AcademyOptionRow[];
  };
};
export type TeacherPasswordResetCredentials = {
  login?: string;
  temporary_password?: string;
  display_name?: string;
  must_change_password?: boolean;
  updated_at?: string;
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

export function decisionLabel(value: unknown) {
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

// The Teacher Academy stores session/assessment datetimes as school-local wall
// clock (Asia/Tashkent) that lands in the DB labelled +00 on the UTC server. We
// pin every display and input to that same wall clock so times never shift with
// the viewer's browser or the Railway server timezone.
const SCHOOL_TIME_ZONE = "Asia/Tashkent";
const HAS_TZ_OFFSET = /[zZ]|[+-]\d\d:?\d\d$/;

/** Normalize a stored datetime to a UTC-labelled instant so its wall-clock digits are stable. */
export function parseSchoolInstant(raw: string) {
  const normalized = HAS_TZ_OFFSET.test(raw) ? raw : `${raw.replace(" ", "T")}Z`;
  return Date.parse(normalized);
}

export function dateLabel(value: unknown) {
  const raw = asString(value).trim();
  if (!raw) return "-";
  const parsed = parseSchoolInstant(raw);
  if (!Number.isFinite(parsed)) return raw.replace("T", " ").slice(0, 16);
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(parsed));
}

/** Stored datetime -> "YYYY-MM-DDTHH:mm" for a datetime-local input, preserving the school wall clock. */
function storedToInputValue(value: unknown) {
  const raw = asString(value).trim();
  if (!raw) return "";
  const parsed = parseSchoolInstant(raw);
  if (!Number.isFinite(parsed)) return raw.slice(0, 16).replace(" ", "T");
  return new Date(parsed).toISOString().slice(0, 16);
}

/** Current time as school-local wall clock ("YYYY-MM-DDTHH:mm"), independent of the assessor's browser. */
function nowSchoolInputValue() {
  // "sv-SE" formats as "YYYY-MM-DD HH:mm:ss"; pin it to the school timezone.
  const stamp = new Date().toLocaleString("sv-SE", { timeZone: SCHOOL_TIME_ZONE });
  return stamp.slice(0, 16).replace(" ", "T");
}

function teacherProgress(teacher: AcademyTeacher) {
  return academyTeacherProgress(teacher);
}

export function academyAssignments(teacher: AcademyTeacher) {
  return typedAcademyAssignments(teacher);
}

export function academyAssessments(teacher: AcademyTeacher) {
  return typedAcademyAssessments(teacher);
}

/** The saved assessment report for a given assignment, or null if not assessed. */
export function assessmentForAssignment(teacher: AcademyTeacher, assignment: AcademyAssignment | null | undefined) {
  const assignmentId = asNumber(assignment?.id);
  if (!assignmentId) return null;
  return (
    academyAssessments(teacher).find(
      (assessment) => asNumber(assessment.lesson_assignment_id) === assignmentId,
    ) || null
  );
}

/** Badge tone for an assessment decision: passes are success, needs-improvement is a warning. */
export function decisionTone(value: unknown): "success" | "warning" | "danger" {
  const decision = asString(value);
  if (decision === "rejected") return "danger";
  if (decision === "needs_improvement" || decision === "reassign_lesson") return "warning";
  return "success";
}

/** Saved per-criterion remark for a report, looked up by rubric short code (e.g. "TGC"). */
function criteriaRemark(report: AcademyAssessment | undefined, code: string) {
  const feedback = report?.section_feedback;
  const entry = feedback?.marking_criteria?.[code.toLowerCase()];
  return asString(entry?.remarks);
}

export function assignmentTitle(assignment: AcademyAssignment) {
  const sequence = asNumber(assignment.sequence_no);
  const lessonNumber = asString(assignment.lesson_number) || (sequence ? `Lesson ${sequence}` : "Lesson");
  const topic = asString(assignment.lesson_topic);
  return topic ? `${lessonNumber} · ${topic}` : lessonNumber;
}

export function assignmentIsScheduled(assignment: AcademyAssignment | null | undefined) {
  return Boolean(asString(assignment?.session_datetime));
}

/** Decisions that count as a passed lesson (the only ones that advance progress). */
const PASSED_DECISIONS = new Set(["passed", "ready_for_final_evaluation", "approved_for_active_teacher"]);

export function isPassedReport(report: AcademyAssessment | null | undefined) {
  return Boolean(report) && PASSED_DECISIONS.has(asString(report?.decision));
}

/** A failed lesson that has been given a new session date/time since it was last assessed. */
export function rescheduledSinceFail(assignment: AcademyAssignment, report: AcademyAssessment | null | undefined) {
  if (!report || isPassedReport(report)) return false;
  const session = asString(assignment.session_datetime);
  if (!session) return false;
  const sessionAt = parseSchoolInstant(session);
  const assessedAt = parseSchoolInstant(asString(report.assessment_datetime));
  return Number.isFinite(sessionAt) && (!Number.isFinite(assessedAt) || sessionAt > assessedAt);
}

export function nextAcademyAssignment(teacher: AcademyTeacher) {
  const progress = teacherProgress(teacher);
  const assignments = academyAssignments(teacher);
  // Only passed lessons are "done" — a failed lesson stays next until it passes.
  const passedAssignmentIds = new Set(
    academyAssessments(teacher)
      .filter((assessment) => PASSED_DECISIONS.has(asString(assessment.decision)))
      .map((assessment) => asNumber(assessment.lesson_assignment_id))
      .filter(Boolean),
  );
  return (
    progress.nextAssignment ||
    assignments.find((assignment) => {
      const status = asString(assignment.status);
      return !passedAssignmentIds.has(asNumber(assignment.id)) && !["passed", "cancelled"].includes(status);
    }) ||
    null
  );
}

function assignmentById(assignments: AcademyAssignment[], assignmentId: number) {
  return assignments.find((item) => asNumber(item.id) === assignmentId) || assignments[0] || null;
}

function subjectOptionsFromState(state: TeacherAcademyPanelState) {
  const subjects = Array.isArray(state.props?.academicManagementSubjects)
    ? state.props.academicManagementSubjects
    : [];
  const programs = Array.isArray(state.props?.academicManagementCurriculumPrograms)
    ? state.props.academicManagementCurriculumPrograms
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

export function NewHeadOfDepartmentModal({
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: TeacherAcademyPanelState;
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

export function NewAcademyTeacherModal({
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  state: TeacherAcademyPanelState;
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
  const programs = Array.isArray(state.props?.academicManagementCurriculumPrograms)
    ? state.props.academicManagementCurriculumPrograms
    : [];
  const curriculumItems = Array.isArray(state.props?.academicManagementCurriculumItems)
    ? state.props.academicManagementCurriculumItems
    : [];
  const teachers = Array.isArray(state.teachers) ? state.teachers : [];
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
  const lessonDetail = (lesson: AcademyOptionRow) =>
    asString(lesson.specification_points) || asString(lesson.book_pages) || "No lesson details yet.";
  const lessonCode = (lesson: AcademyOptionRow) =>
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
                  className={`min-h-10 rounded-lg border px-2 text-left text-[0.6875rem] font-black transition-colors motion-reduce:transition-none ${
                    active
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : complete
                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                        : "border-foreground/10 bg-background text-muted-foreground"
                  }`}
                  aria-current={active ? "step" : undefined}
                >
                  <span className="block text-[0.625rem] uppercase tracking-wide">Step {item.step}</span>
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
                    <p className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">{label}</p>
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

export function AssignmentModal({
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
  const initialDateTime = storedToInputValue(selectedAssignment?.session_datetime);
  const [sessionDate, setSessionDate] = useState(initialDateTime.slice(0, 10));
  const [sessionTime, setSessionTime] = useState(initialDateTime.slice(11, 16));
  const controlClass = "h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm font-semibold outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10";

  function handleAssignmentChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const nextAssignment = assignmentById(assignments, asNumber(event.target.value));
    setSelectedAssignmentId(asNumber(nextAssignment?.id));
    const nextDateTime = storedToInputValue(nextAssignment?.session_datetime);
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
              <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary">Teacher name</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
              <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary">Assigned lesson</p>
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

export function AssessmentModal({
  teacher,
  assignment,
  initialReport,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  assignment: AcademyAssignment;
  initialReport?: AcademyAssessment;
  submitting: boolean;
  error: string;
  onSubmit: (teacherId: number, fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  const isEditing = Boolean(initialReport);
  const formRef = useRef<HTMLFormElement>(null);
  // Correcting a passed report keeps its original school-local timestamp; a fresh
  // assessment or a re-assessment of a failed lesson stamps the school "now" so the
  // recorded time is correct regardless of the assessor's browser timezone.
  const [assessmentStamp] = useState(() =>
    isEditing && isPassedReport(initialReport) ? storedToInputValue(initialReport?.assessment_datetime) : nowSchoolInputValue(),
  );
  const [scores, setScores] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      rubric.map((item) => {
        const saved = initialReport?.scores && typeof initialReport.scores === "object"
          ? asNumber(initialReport.scores[item.key])
          : 0;
        return [item.key, saved > 0 ? String(saved) : "7"];
      }),
    ),
  );
  const [confirmDecision, setConfirmDecision] = useState<"passed" | "needs_improvement" | null>(null);
  const weighted = rubric.reduce((sum, item) => {
    const value = Number(scores[item.key]);
    return sum + (Number.isFinite(value) ? value : 0) * item.weight;
  }, 0);
  const remarksClass = "min-h-10 w-full resize-none overflow-hidden rounded-lg border border-foreground/10 bg-background px-3 py-2.5 text-sm outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-4 focus:ring-primary/10";

  // Grow prefilled textareas to fit their saved content on open (they otherwise
  // stay a single clipped row until the evaluator types).
  useEffect(() => {
    formRef.current?.querySelectorAll("textarea").forEach((element) => {
      element.style.height = "auto";
      element.style.height = `${element.scrollHeight}px`;
    });
  }, []);

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
    fields.assessment_datetime = assessmentStamp;
    // The evaluator is always the teacher's department head (subject HOD).
    fields.evaluator_id = String(asNumber(teacher.department_head_id) || "");
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
              <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary">Teacher name</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{asString(teacher.full_name) || "Academy teacher"}</p>
              <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asString(teacher.subject) || "Subject not set"}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary">Assigned lesson</p>
              <p className="mt-1 line-clamp-2 text-sm font-black text-foreground">{assignmentTitle(assignment)}</p>
            </div>
            <div className="min-w-0">
              <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary">Date</p>
              <p className="mt-1 truncate text-sm font-black text-foreground">{dateLabel(assessmentStamp)}</p>
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
                    <span className="flex h-8 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-[0.6875rem] font-black text-primary">
                      {item.code}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">{item.label}</p>
                      <p className="text-[0.6875rem] font-semibold text-muted-foreground">{Math.round(item.weight * 100)}% weight</p>
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
                    defaultValue={criteriaRemark(initialReport, item.code)}
                    onInput={autoGrowTextarea}
                    placeholder="Remarks"
                    aria-label={`${item.label} remarks`}
                    className={remarksClass}
                  />
                </div>
              ))}
            </div>
          </section>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block">
              <FieldLabel>Strengths</FieldLabel>
              <textarea name="strengths" rows={3} defaultValue={asString(initialReport?.strengths)} onInput={autoGrowTextarea} placeholder="What went well?" className={remarksClass} />
            </label>
            <label className="block">
              <FieldLabel>Areas for Improvement</FieldLabel>
              <textarea name="areas_for_improvement" rows={3} defaultValue={asString(initialReport?.areas_for_improvement)} onInput={autoGrowTextarea} placeholder="What should improve next?" className={remarksClass} />
            </label>
            <label className="block">
              <FieldLabel>Final Recommendation</FieldLabel>
              <textarea name="final_recommendation" rows={3} defaultValue={asString(initialReport?.final_recommendation)} onInput={autoGrowTextarea} placeholder="Overall recommendation" className={remarksClass} />
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

export function PromoteModal({
  teacher,
  state,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  state: TeacherAcademyPanelState;
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
            <span className="mt-1 block text-[0.6875rem] font-semibold text-muted-foreground">Suggested: {formatUzs(suggestedRate) || "set manually"}</span>
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
  lessons: AcademyOptionRow[];
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
          <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary/80">
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
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[0.625rem] font-black uppercase tracking-wide text-primary">
                        Assessed
                      </span>
                    ) : null}
                  </span>
                  {asString(lesson.specification_points) ? (
                    <span className="mt-0.5 line-clamp-2 block text-[0.6875rem] leading-4 text-muted-foreground">
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

export function AcademyDetailModal({
  teacher,
  state,
  submitting,
  error,
  onClose,
  onAssess,
  onReview,
  onReschedule,
  onDeleteAssessment,
  onPromote,
  onSyncLessons,
  canEditLessons,
  canAssess,
  canSchedule,
  canDeleteAssessment,
  canPromote,
}: {
  teacher: AcademyTeacher;
  state: TeacherAcademyPanelState;
  submitting: boolean;
  error: string;
  onClose: () => void;
  onAssess: (assignment: AcademyAssignment) => void;
  onReview: (assignment: AcademyAssignment, report: AcademyAssessment) => void;
  onReschedule: (assignment: AcademyAssignment) => void;
  onDeleteAssessment: (assessment: AcademyAssessment) => void;
  onPromote: () => void;
  onSyncLessons: (selectedIds: number[]) => Promise<boolean>;
  canEditLessons: boolean;
  canAssess: boolean;
  canSchedule: boolean;
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
    const items = Array.isArray(state.props?.academicManagementCurriculumItems)
      ? state.props.academicManagementCurriculumItems
      : [];
    const programId = asNumber(teacher.subject_program_id);
    return items
      .filter((item) => {
        const itemProgramId = asNumber(item.program_id || item.programId);
        const itemType = asString(item.item_type || item.itemType).toLowerCase();
        return itemProgramId === programId && itemType === "lesson";
      })
      .sort((left, right) => asNumber(left.item_order || left.itemOrder) - asNumber(right.item_order || right.itemOrder));
  }, [state.props?.academicManagementCurriculumItems, teacher.subject_program_id]);

  const latestAssessmentByAssignment = useMemo(() => {
    const map = new Map<number, AcademyAssessment>();
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
          {metric("Progress", `${progress.passed}/${progress.target}`, "passed lessons")}
          {metric("Assessed", progress.assessed, "lessons evaluated")}
          {metric("Average", progress.average == null ? "-" : progress.average.toFixed(2), "weighted score")}
          {metric("Latest", progress.latest == null ? "-" : progress.latest.toFixed(2), "last report")}
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <div className="rounded-xl border border-primary/10 bg-primary/5 p-3">
            <p className="text-[0.625rem] font-black uppercase tracking-wide text-primary">
              {login ? "Account ready" : "Account pending"}
            </p>
            <p className="mt-1 truncate font-mono text-sm font-black text-foreground">
              {login || "Login is being provisioned"}
            </p>
            {login ? (
              <p className="mt-1 text-[0.6875rem] font-semibold text-muted-foreground">
                Temporary password equals the login and can be changed in Account Security.
              </p>
            ) : null}
          </div>
          <div className="rounded-xl border border-foreground/10 bg-muted/40 p-3">
            <p className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">
              Training configuration
            </p>
            <p className="mt-1 text-sm font-black text-foreground">
              {asNumber(teacher.subject_program_id) ? "Curriculum assigned" : "Curriculum not assigned"}
            </p>
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
                          <p className="mt-0.5 text-[0.6875rem] text-muted-foreground">
                            {dateLabel(report ? report.assessment_datetime : assignment.session_datetime)} · {asString(teacher.department_head_name) || asString(assignment.evaluator_name) || "No evaluator"} · {asString(assignment.status)}
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
                                className="inline-flex items-center gap-1 rounded-md border border-foreground/10 bg-background px-2.5 py-1 text-[0.6875rem] font-bold text-foreground hover:bg-muted"
                              >
                                <Eye className="h-3.5 w-3.5" />
                                Review
                              </button>
                              {!isPassedReport(report) && rescheduledSinceFail(assignment, report) && canAssess ? (
                                <button type="button" onClick={() => onReview(assignment, report)} className="inline-flex items-center gap-1 rounded-md bg-foreground px-2.5 py-1 text-[0.6875rem] font-bold text-background">
                                  <ClipboardCheck className="h-3.5 w-3.5" />
                                  Re-assess
                                </button>
                              ) : !isPassedReport(report) && canSchedule ? (
                                <button type="button" onClick={() => onReschedule(assignment)} className="inline-flex items-center gap-1 rounded-md bg-foreground px-2.5 py-1 text-[0.6875rem] font-bold text-background">
                                  <CalendarClock className="h-3.5 w-3.5" />
                                  Re-schedule
                                </button>
                              ) : null}
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
                            <button type="button" onClick={() => onAssess(assignment)} className="rounded-md bg-foreground px-2.5 py-1 text-[0.6875rem] font-bold text-background">
                              Assess
                            </button>
                          ) : null}
                        </div>
                      </div>
                      {report ? (
                        <p className="mt-1 text-[0.6875rem] font-bold">
                          {decisionLabel(report.decision)}
                          <span className="font-semibold text-muted-foreground"> · {dateLabel(report.assessment_datetime)} · {asString(teacher.department_head_name) || asString(report.evaluator_name) || "Evaluator not set"}</span>
                        </p>
                      ) : null}
                      {report && (asString(report.areas_for_improvement) || asString(report.strengths)) ? (
                        <p className="mt-1 line-clamp-2 text-[0.6875rem] leading-4 text-muted-foreground">
                          {asString(report.areas_for_improvement) || asString(report.strengths)}
                        </p>
                      ) : !report && asString(assignment.specification_points) ? (
                        <p className="mt-1 line-clamp-2 text-[0.6875rem] leading-4 text-muted-foreground">{asString(assignment.specification_points)}</p>
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

export function ActiveTeacherAccountModal({
  teacher,
  resetting,
  resetError,
  resetCredentials,
  onResetPassword,
  onCopy,
  onClose,
}: {
  teacher: ActiveTeacher;
  resetting: boolean;
  resetError: string;
  resetCredentials: TeacherPasswordResetCredentials | null;
  onResetPassword: () => void;
  onCopy: (value: string, label: string) => void;
  onClose: () => void;
}) {
  const [confirmingReset, setConfirmingReset] = useState(false);
  const login = asString(teacher.login || teacher.teacher_code);
  const status = asString(teacher.status || teacher.teacher_status || teacher.academy_status) || "Active";
  const fields: Array<[string, string]> = [
    ["Name", asString(teacher.full_name) || "Teacher"],
    ["Account Login", login || "Not set"],
    ["Role", "Teacher"],
    ["Subject", asString(teacher.subjects || teacher.subject) || "Not assigned"],
    ["Group", asString(teacher.assigned_group || teacher.group_name || teacher.group) || "Not assigned"],
    ["Status", status],
  ];

  return (
    <Modal
      title={asString(teacher.full_name) || "Teacher account"}
      subtitle="Teacher account"
      onClose={onClose}
      size="lg"
      closeOnOutsideClick={!resetCredentials}
    >
      <ModalBody>
        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          {fields.map(([label, value]) => (
            <div key={label} className="min-w-0 rounded-lg border border-border bg-background px-3 py-2">
              <dt className="text-[0.625rem] font-bold uppercase tracking-wide text-muted-foreground">{label}</dt>
              <dd className="mt-0.5 break-words font-black text-foreground">
                {label === "Status" ? <StatusBadge status={value} className="text-[0.625rem]" /> : value}
              </dd>
            </div>
          ))}
        </dl>

        <section className="mt-4 rounded-xl border border-border bg-muted/60 p-3" aria-labelledby="teacher-password-access-title">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <KeyRound className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 id="teacher-password-access-title" className="text-sm font-black text-foreground">Password access</h3>
              <p className="mt-0.5 text-xs font-semibold leading-5 text-muted-foreground">
                The current password is protected and cannot be viewed. Resetting sets the password back to the teacher's login; they can change it later in their profile.
              </p>
            </div>
          </div>

          {resetCredentials ? (
            <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3" aria-live="polite">
              <p className="text-xs font-black text-emerald-900">Password reset — same as the login</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-emerald-200 bg-white px-3 py-2">
                  <p className="text-[0.625rem] font-bold uppercase tracking-wide text-emerald-800">Login</p>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <p className="min-w-0 break-all font-mono text-sm font-black text-foreground">{asString(resetCredentials.login)}</p>
                    <IconButton label="Copy teacher login" onClick={() => onCopy(asString(resetCredentials.login), "Teacher login")}>
                      <Copy className="h-4 w-4" />
                    </IconButton>
                  </div>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-white px-3 py-2">
                  <p className="text-[0.625rem] font-bold uppercase tracking-wide text-emerald-800">Password</p>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <p className="min-w-0 break-all font-mono text-sm font-black text-foreground">{asString(resetCredentials.temporary_password)}</p>
                    <IconButton label="Copy password" onClick={() => onCopy(asString(resetCredentials.temporary_password), "Password")}>
                      <Copy className="h-4 w-4" />
                    </IconButton>
                  </div>
                </div>
              </div>
              <p className="mt-2 text-xs font-semibold leading-5 text-emerald-800">
                The teacher can sign in with these now and change the password anytime in their profile.
              </p>
            </div>
          ) : confirmingReset ? (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-xs font-black text-amber-900">Reset this teacher password?</p>
              <p className="mt-1 text-xs font-semibold leading-5 text-amber-800">
                This sets the password back to the teacher's login and signs them out of other sessions.
              </p>
              <div className="mt-3 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setConfirmingReset(false)}
                  disabled={resetting}
                  className="inline-flex min-h-10 items-center justify-center rounded-lg border border-border bg-background px-3 text-xs font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30 disabled:opacity-60"
                >
                  Keep current password
                </button>
                <button
                  type="button"
                  onClick={onResetPassword}
                  disabled={resetting || !login}
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-wait disabled:opacity-60"
                >
                  <RefreshCw className={`h-4 w-4 ${resetting ? "animate-spin" : ""}`} aria-hidden="true" />
                  {resetting ? "Resetting..." : "Reset to login"}
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingReset(true)}
              disabled={!login}
              className="mt-3 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-primary/20 bg-background px-3 text-sm font-black text-primary transition-colors duration-150 hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none sm:w-auto"
            >
              <KeyRound className="h-4 w-4" aria-hidden="true" />
              Reset password
            </button>
          )}

          {resetError ? (
            <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive" role="alert">
              {resetError}
            </p>
          ) : null}
        </section>
      </ModalBody>
    </Modal>
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

export function AssignCurriculumModal({
  teacher,
  programs,
  curriculumItems,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  teacher: AcademyTeacher;
  programs: AcademyOptionRow[];
  curriculumItems: AcademyOptionRow[];
  submitting: boolean;
  error: string;
  onSubmit: (programId: number, lessonIds: number[]) => void;
  onClose: () => void;
}) {
  const initialProgramId = asNumber(teacher.subject_program_id);
  const [programId, setProgramId] = useState(initialProgramId);
  const [lessonIds, setLessonIds] = useState<number[]>(() =>
    academyAssignments(teacher)
      .map((assignment) => asNumber(assignment.curriculum_item_id))
      .filter(Boolean),
  );
  const lessons = useMemo(
    () =>
      curriculumItems
        .filter(
          (item) =>
            asNumber(item.program_id || item.programId) === programId
            && asString(item.item_type || item.itemType).toLowerCase() === "lesson",
        )
        .sort(
          (left, right) =>
            asNumber(left.item_order || left.itemOrder)
            - asNumber(right.item_order || right.itemOrder),
        ),
    [curriculumItems, programId],
  );

  return (
    <Modal
      title={initialProgramId ? "Edit curriculum" : "Assign curriculum"}
      subtitle={asString(teacher.full_name)}
      onClose={onClose}
      size="md"
      initialFocusSelector="#academy-curriculum-program"
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (programId && lessonIds.length) onSubmit(programId, lessonIds);
        }}
      >
        <ModalBody className="space-y-4">
          <label className="block">
            <FieldLabel>Subject curriculum</FieldLabel>
            <select
              id="academy-curriculum-program"
              value={programId || ""}
              onChange={(event) => {
                setProgramId(asNumber(event.target.value));
                setLessonIds([]);
              }}
              className="min-h-11 w-full rounded-lg border border-foreground/15 bg-surface px-3 text-sm font-semibold outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select curriculum</option>
              {programs.map((program) => (
                <option key={asNumber(program.id)} value={asNumber(program.id)}>
                  {asString(program.program_name || program.name || program.subject_name)}
                </option>
              ))}
            </select>
          </label>

          <fieldset>
            <legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Academy lessons
            </legend>
            <div className="miniapp-scroll mt-2 max-h-[42dvh] space-y-1 overflow-y-auto rounded-lg border border-foreground/10 p-2">
              {lessons.length ? lessons.map((lesson) => {
                const lessonId = asNumber(lesson.id);
                const checked = lessonIds.includes(lessonId);
                return (
                  <label
                    key={lessonId}
                    className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 hover:bg-muted"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setLessonIds((current) =>
                          checked
                            ? current.filter((id) => id !== lessonId)
                            : [...current, lessonId],
                        )
                      }
                      className="h-4 w-4 rounded border-foreground/20 text-primary focus:ring-primary"
                    />
                    <span className="min-w-0 text-sm font-semibold">
                      {asString(lesson.lesson_number || lesson.lessonNumber)}
                      {" · "}
                      {asString(lesson.title)}
                    </span>
                  </label>
                );
              }) : (
                <p className="px-2 py-4 text-sm text-muted-foreground">
                  {programId ? "No lessons found for this curriculum." : "Select a curriculum first."}
                </p>
              )}
            </div>
          </fieldset>

          {error ? (
            <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">
              {error}
            </p>
          ) : null}
        </ModalBody>
        <ModalActions
          onClose={onClose}
          submitting={submitting}
          submitLabel={initialProgramId ? "Save curriculum" : "Assign curriculum"}
          disabled={!programId || !lessonIds.length}
        />
      </form>
    </Modal>
  );
}
