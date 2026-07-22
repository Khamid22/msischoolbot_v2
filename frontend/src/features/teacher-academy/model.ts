export type TeacherAcademyMode = "academic_director" | "head_of_department";

export type TeacherAcademyView =
  | "teacher_academy"
  | "active_teachers";

export type TeacherAcademySort = "average_score" | "lessons" | "date";

export type AcademyStatusTone = "success" | "warning" | "danger" | "info";

export interface AcademyAssignment {
  id: number;
  academy_teacher_id?: number;
  sequence_no?: number;
  subject_program_id?: number;
  curriculum_item_id?: number;
  lesson_number?: string;
  lesson_topic?: string;
  assignment_type?: string;
  deadline_date?: string;
  session_datetime?: string;
  evaluator_id?: number;
  evaluator_name?: string;
  focus_areas?: string[];
  notes_to_trainee?: string;
  status?: string;
  specification_points?: string;
  book_pages?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AcademyAssessment {
  id: number;
  academy_teacher_id?: number;
  lesson_assignment_id?: number;
  assessment_type?: string;
  lesson_number?: string;
  lesson_topic?: string;
  evaluator_id?: number;
  evaluator_name?: string;
  assessment_datetime?: string;
  session_type?: string;
  class_label?: string;
  section_feedback?: {
    marking_criteria?: Record<string, { remarks?: string }>;
    [key: string]: unknown;
  };
  scores?: Record<string, number>;
  weighted_overall_score?: number;
  strengths?: string;
  areas_for_improvement?: string;
  final_recommendation?: string;
  decision?: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AcademyProgress {
  assigned_count?: number;
  assessed_count?: number;
  passed_count?: number;
  average_score?: number | null;
  latest_score?: number | null;
  target_lessons?: number;
  next_assignment?: AcademyAssignment | null;
}

export interface AcademyTeacher {
  id: number;
  user_id?: number;
  full_name?: string;
  subject_id?: number;
  subject_program_id?: number;
  subject?: string;
  subject_program_name?: string;
  position?: string;
  employment_type?: string;
  telegram_username?: string;
  phone?: string;
  email?: string;
  academy_status?: string;
  academy_start_date?: string;
  mentor_id?: number;
  mentor_name?: string;
  department_head_id?: number;
  department_head_name?: string;
  notes?: string;
  login?: string;
  account_teacher_id?: number;
  telegram_user_id?: number;
  promoted_teacher_id?: number;
  recruitment_candidate_id?: number;
  account_onboarding_status?: string;
  created_at?: string;
  updated_at?: string;
  assignments?: AcademyAssignment[];
  assessments?: AcademyAssessment[];
  progress?: AcademyProgress;
}

export interface ActiveTeacher {
  id: number;
  full_name?: string;
  subject?: string;
  subject_name?: string;
  position?: string;
  employment_type?: string;
  teacher_employment_type?: string;
  status?: string;
  teacher_status?: string;
  activated_at?: string;
  created_at?: string;
  updated_at?: string;
  account_teacher_id?: number;
  promoted_teacher_id?: number;
  login?: string;
  teacher_code?: string;
  academy_status?: string;
  subjects?: string;
  assigned_group?: string;
  group_name?: string;
  group?: string;
}

export interface AcademyOptionRow {
  id?: number;
  name?: string;
  label?: string;
  group_name?: string;
  subject?: string;
  subject_id?: number;
  subjectId?: number;
  subject_name?: string;
  subjectName?: string;
  program_id?: number;
  programId?: number;
  program_name?: string;
  lesson_count?: number;
  specification_code?: string;
  curriculum_item_id?: number;
  item_type?: string;
  itemType?: string;
  item_order?: number;
  itemOrder?: number;
  lesson_number?: string;
  lessonNumber?: string;
  lesson_topic?: string;
  title?: string;
  sequence_no?: number;
  specification_points?: string;
  book_pages?: string;
  status?: string;
}

export interface GeneratedCredentials {
  role?: string;
  login?: string;
  teacher_code?: string;
  temporary_password?: string;
  display_name?: string;
  subject_name?: string;
}

export interface TeacherAcademyStats {
  total: number;
  ready: number;
  weightedAverage: number | null;
}

function finiteNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function academyAssignments(teacher: AcademyTeacher): AcademyAssignment[] {
  return Array.isArray(teacher.assignments) ? teacher.assignments : [];
}

export function academyAssessments(teacher: AcademyTeacher): AcademyAssessment[] {
  return Array.isArray(teacher.assessments) ? teacher.assessments : [];
}

export function academyTeacherProgress(teacher: AcademyTeacher) {
  const assigned = finiteNumber(teacher.progress?.assigned_count)
    ?? academyAssignments(teacher).length;
  const target = finiteNumber(teacher.progress?.target_lessons) ?? assigned;
  const assessed = finiteNumber(teacher.progress?.assessed_count) ?? 0;
  const passed = finiteNumber(teacher.progress?.passed_count) ?? 0;
  const average = finiteNumber(teacher.progress?.average_score);

  return {
    assigned: Math.max(0, assigned),
    target: Math.max(0, target),
    assessed: Math.max(0, assessed),
    passed: Math.max(0, passed),
    average,
    latest: finiteNumber(teacher.progress?.latest_score),
    nextAssignment: teacher.progress?.next_assignment ?? null,
  };
}

export function calculateTeacherAcademyStats(
  teachers: AcademyTeacher[],
): TeacherAcademyStats {
  let weightedScoreTotal = 0;
  let assessmentCount = 0;

  teachers.forEach((teacher) => {
    const assessmentScores = academyAssessments(teacher)
      .map((assessment) => finiteNumber(assessment.weighted_overall_score))
      .filter((score): score is number => score !== null);

    if (assessmentScores.length) {
      weightedScoreTotal += assessmentScores.reduce((sum, score) => sum + score, 0);
      assessmentCount += assessmentScores.length;
      return;
    }

    const progress = academyTeacherProgress(teacher);
    if (progress.average !== null && progress.assessed > 0) {
      weightedScoreTotal += progress.average * progress.assessed;
      assessmentCount += progress.assessed;
    }
  });

  return {
    total: teachers.length,
    ready: teachers.filter(
      (teacher) => teacher.academy_status === "ready_for_active_teacher",
    ).length,
    weightedAverage: assessmentCount
      ? weightedScoreTotal / assessmentCount
      : null,
  };
}

export function academyStatusPresentation(statusValue: string | undefined): {
  label: string;
  tone: AcademyStatusTone;
} {
  const status = String(statusValue || "in_training").trim().toLowerCase();
  const labels: Record<string, string> = {
    new_academy_teacher: "Not started",
    in_training: "In training",
    ready_for_evaluation: "Ready for evaluation",
    needs_improvement: "Needs improvement",
    ready_for_active_teacher: "Ready for active teacher",
    approved: "Approved",
    rejected: "Rejected",
    on_hold: "On hold",
  };
  const tone: AcademyStatusTone =
    status === "ready_for_active_teacher" || status === "approved"
      ? "success"
      : status === "needs_improvement" || status === "on_hold"
        ? "warning"
        : status === "rejected"
          ? "danger"
          : "info";
  return {
    label: labels[status] || status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
    tone,
  };
}

export function academyViewFromSearch(
  search: string,
  mode: TeacherAcademyMode,
): TeacherAcademyView {
  const requested = new URLSearchParams(search).get("academy_view");
  if (requested === "active_teachers" && mode === "academic_director") return requested;
  return "teacher_academy";
}

export function academyRosterPageSize(width: number): number {
  if (width < 768) return 5;
  if (width < 1280) return 6;
  return 12;
}

export function filterAndSortAcademyTeachers(
  teachers: AcademyTeacher[],
  filters: {
    search: string;
    subjectId: string;
    sort: TeacherAcademySort;
  },
): AcademyTeacher[] {
  const query = filters.search.trim().toLocaleLowerCase();
  const subjectId = Number(filters.subjectId || 0);
  return teachers
    .filter((teacher) => {
      if (subjectId && Number(teacher.subject_id || 0) !== subjectId) return false;
      if (!query) return true;
      return [teacher.full_name, teacher.position, teacher.subject]
        .some((value) => String(value || "").toLocaleLowerCase().includes(query));
    })
    .sort((left, right) => {
      const leftProgress = academyTeacherProgress(left);
      const rightProgress = academyTeacherProgress(right);
      if (filters.sort === "lessons") {
        return rightProgress.passed - leftProgress.passed
          || String(left.full_name || "").localeCompare(String(right.full_name || ""));
      }
      if (filters.sort === "date") {
        const leftDate = Date.parse(String(left.academy_start_date || left.created_at || ""));
        const rightDate = Date.parse(String(right.academy_start_date || right.created_at || ""));
        const leftTimestamp = Number.isFinite(leftDate) ? leftDate : Number.NEGATIVE_INFINITY;
        const rightTimestamp = Number.isFinite(rightDate) ? rightDate : Number.NEGATIVE_INFINITY;
        return rightTimestamp - leftTimestamp
          || String(left.full_name || "").localeCompare(String(right.full_name || ""));
      }
      if (leftProgress.average === null && rightProgress.average === null) {
        return String(left.full_name || "").localeCompare(String(right.full_name || ""));
      }
      if (leftProgress.average === null) return 1;
      if (rightProgress.average === null) return -1;
      return rightProgress.average - leftProgress.average
        || String(left.full_name || "").localeCompare(String(right.full_name || ""));
    });
}
