import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { BookOpenCheck, CalendarClock, ClipboardCheck, Copy, KeyRound, Trash2, Trophy } from "lucide-react";
import type { ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "@/shared/lib/workspace";
import { postForm, type ToastTone } from "@/features/people/teachers/model";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import {
  TeacherAcademyRoster,
  type TeacherRosterItem,
  useCanonicalTeacherRosterTotals,
} from "@/features/teacher-academy/TeacherAcademyRoster";
import { TeacherAcademyDashboard } from "@/features/teacher-academy/TeacherAcademyDashboard";
import { ScopedTeacherAcademyRoster } from "@/features/teacher-academy/ScopedTeacherAcademyRoster";
import {
  ActiveTeacherAccountModal,
  AcademyDetailModal,
  AssessmentModal,
  AssignCurriculumModal,
  AssignmentModal,
  NewAcademyTeacherModal,
  NewHeadOfDepartmentModal,
  PromoteModal,
  academyAssessments,
  academyAssignments,
  assignmentIsScheduled,
  nextAcademyAssignment,
  type TeacherAcademyPanelState,
  type TeacherPasswordResetCredentials,
} from "@/features/teacher-academy/TeacherAcademyWorkflowModals";
import {
  academyViewFromSearch,
  calculateTeacherAcademyStats,
  type AcademyAssessment,
  type AcademyAssignment,
  type AcademyOptionRow,
  type AcademyTeacher,
  type ActiveTeacher,
  type GeneratedCredentials,
  type TeacherAcademyMode,
  type TeacherAcademyView,
} from "@/features/teacher-academy/model";

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

function teacherAcademyActionRoutes(managementMode: string, authRole: string): TeacherAcademyActionRoutes {
  const roleMode = authRole || managementMode;
  if (roleMode === "academic_director" || managementMode === "academic_director") {
    return {
      create: routes.academicDirectorTeacherAcademyCreate,
      assignmentUpdate: routes.academicDirectorTeacherAcademyAssignmentUpdate,
      assessmentCreate: routes.academicDirectorTeacherAcademyAssessmentCreate,
      assessmentDelete: routes.academicDirectorTeacherAcademyAssessmentDelete,
      statusUpdate: routes.academicDirectorTeacherAcademyStatusUpdate,
      lessonsSync: routes.academicDirectorTeacherAcademyLessonsSync,
      promote: routes.academicDirectorTeacherAcademyPromote,
    };
  }
  if (roleMode === "head_of_department" || managementMode === "head_of_department") {
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


export interface TeacherAcademyPanelProps {
  mode: TeacherAcademyMode;
  authRole?: string;
  csrfToken?: string;
  teachers: ActiveTeacher[];
  academyTeachers: AcademyTeacher[];
  groupOptions: Array<{ name: string }>;
  subjects: AcademyOptionRow[];
  curriculumPrograms: AcademyOptionRow[];
  curriculumItems: AcademyOptionRow[];
  onAcademyChange: (rows: AcademyTeacher[]) => void;
  onTeachersChange: (rows: ActiveTeacher[]) => void;
  showToast: (message: string, tone?: ToastTone) => void;
}

export function TeacherAcademyPanel({
  mode,
  authRole,
  csrfToken,
  teachers,
  academyTeachers,
  groupOptions,
  subjects,
  curriculumPrograms,
  curriculumItems,
  onAcademyChange,
  onTeachersChange,
  showToast,
}: TeacherAcademyPanelProps) {
  const state = useMemo<TeacherAcademyPanelState>(() => ({
    managementMode: mode,
    currentSchool: "all",
    teachers,
    setTeachers: onTeachersChange,
    academyTeachers,
    setAcademyTeachers: onAcademyChange,
    filteredGroupOptions: groupOptions,
    props: {
      csrfToken,
      authRole: authRole || mode,
      managementMode: mode,
      managementTeachers: teachers,
      academicManagementSubjects: subjects,
      academicManagementCurriculumPrograms: curriculumPrograms,
      academicManagementCurriculumItems: curriculumItems,
    },
  }), [academyTeachers, authRole, csrfToken, curriculumItems, curriculumPrograms, groupOptions, mode, onAcademyChange, onTeachersChange, subjects, teachers]);
  const csrf = asString(csrfToken);
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [hodOpen, setHodOpen] = useState(false);
  const [credentials, setCredentials] = useState<GeneratedCredentials | null>(null);
  const [detailTeacher, setDetailTeacher] = useState<AcademyTeacher | null>(null);
  const [scheduleTarget, setScheduleTarget] = useState<{ teacher: AcademyTeacher; assignment: AcademyAssignment } | null>(null);
  const [assessmentTarget, setAssessmentTarget] = useState<{ teacher: AcademyTeacher; assignment: AcademyAssignment } | null>(null);
  const [reportTarget, setReportTarget] = useState<{ teacher: AcademyTeacher; assignment: AcademyAssignment; report: AcademyAssessment } | null>(null);
  const [promoteTeacher, setPromoteTeacher] = useState<AcademyTeacher | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AcademyTeacher | null>(null);
  const [assessmentDeleteTarget, setAssessmentDeleteTarget] = useState<{ teacher: AcademyTeacher; assessment: AcademyAssessment } | null>(null);
  const [curriculumTarget, setCurriculumTarget] = useState<AcademyTeacher | null>(null);
  const [activeTeacherAccount, setActiveTeacherAccount] = useState<ActiveTeacher | null>(null);
  const [teacherPasswordResetting, setTeacherPasswordResetting] = useState(false);
  const [teacherPasswordResetError, setTeacherPasswordResetError] = useState("");
  const [teacherPasswordResetCredentials, setTeacherPasswordResetCredentials] = useState<TeacherPasswordResetCredentials | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState<TeacherAcademyView>(() => (
    academyViewFromSearch(typeof window === "undefined" ? "" : window.location.search, mode)
  ));

  useEffect(() => {
    if (mode === "head_of_department" && activeView === "active_teachers") {
      setActiveView("teacher_academy");
      return;
    }
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("academy_view", activeView);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }, [activeView, mode]);

  const stats = useMemo(() => calculateTeacherAcademyStats(academyTeachers), [academyTeachers]);

  function applyPayload(data: { academy?: AcademyTeacher[]; teachers?: ActiveTeacher[]; message?: string }) {
    if (Array.isArray(data.academy)) {
      onAcademyChange(data.academy as AcademyTeacher[]);
      if (detailTeacher) {
        const updated = (data.academy as AcademyTeacher[]).find((teacher) => asNumber(teacher.id) === asNumber(detailTeacher.id));
        setDetailTeacher(updated || null);
      }
    }
    if (Array.isArray(data.teachers)) {
      onTeachersChange(data.teachers);
    }
    void queryClient.invalidateQueries({ queryKey: ["recruitment", "teachers"] });
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
    applyPayload(data as { academy?: AcademyTeacher[]; teachers?: ActiveTeacher[]; message?: string });
    showToast(asString(data.message) || successMessage);
    return data;
  }

  async function onboardRecruitmentAcademyTeacher(
    teacher: AcademyTeacher,
    programId: number,
    lessonIds: number[],
  ) {
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/recruitment/academy-intakes/${asNumber(teacher.id)}/onboard`, {
        method: "POST",
        credentials: "same-origin",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ subject_program_id: programId, curriculum_item_ids: lessonIds }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, payload)) {
        const message = apiErrorMessage(payload, "Could not complete Academy onboarding.");
        setError(message);
        showToast(message, "danger");
        return;
      }
      const data = apiData<{ message?: string; credentials?: GeneratedCredentials }>(payload);
      const generated = data.credentials || {};
      setCredentials(asString(generated.temporary_password) ? generated : null);
      onAcademyChange(academyTeachers.map((row) => asNumber(row.id) === asNumber(teacher.id) ? {
        ...row,
        account_onboarding_status: "complete",
        academy_status: "in_training",
        subject_program_id: programId,
        login: asString(generated.login),
      } : row));
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "teachers"] });
      setCurriculumTarget(null);
      showToast(asString(data.message) || "Curriculum assigned.");
    } catch {
      showToast("Network error. Please try again.", "danger");
    } finally {
      setSubmitting(false);
    }
  }

  const managementMode = mode;
  const normalizedAuthRole = asString(authRole || mode).toLowerCase();
  const academyApi = useMemo(() => teacherAcademyActionRoutes(managementMode, normalizedAuthRole), [managementMode, normalizedAuthRole]);
  const canCreateHeadOfDepartment = managementMode === "academic_director" || normalizedAuthRole === "academic_director";
  const canCreateAcademyTeacher = Boolean(academyApi.create) && managementMode !== "head_of_department" && normalizedAuthRole !== "head_of_department";
  const canScheduleAcademyLesson = Boolean(academyApi.assignmentUpdate(0));
  const canAssessAcademyLesson = Boolean(academyApi.assessmentCreate(0));
  const canEditAcademyLessons = Boolean(academyApi.lessonsSync(0));
  const canDeleteAssessmentReport = Boolean(academyApi.assessmentDelete(0, 0));
  const canPromoteAcademyTeacher = Boolean(academyApi.promote) && managementMode !== "head_of_department" && normalizedAuthRole !== "head_of_department";
  const canDeleteAcademyTeacher = Boolean(academyApi.delete) && managementMode !== "head_of_department" && normalizedAuthRole !== "head_of_department";
  const isAcademicDirectorMode = managementMode === "academic_director" || normalizedAuthRole === "academic_director";
  const isHeadOfDepartmentMode = managementMode === "head_of_department" || normalizedAuthRole === "head_of_department";
  const canOnboardRecruitmentTeacher = isAcademicDirectorMode || isHeadOfDepartmentMode;

  // Highest performers first: rank by weighted average score, teachers without a
  // score last, then a stable name tiebreak.
  const activeTeachers = useMemo(() => {
    const rows = Array.isArray(teachers) ? teachers : [];
    return rows.filter((teacher) => {
      const employmentType = asString(teacher.employment_type || teacher.teacher_employment_type).toLowerCase();
      const status = asString(teacher.status || teacher.teacher_status || "active").toLowerCase();
      return employmentType !== "academy" && !["inactive", "deleted", "archived"].includes(status);
    });
  }, [teachers]);
  const academyRosterRefreshToken = useMemo(
    () => academyTeachers
      .map((teacher) => [
        asNumber(teacher.id),
        asString(teacher.updated_at),
        academyAssessments(teacher).length,
      ].join(":"))
      .join("|"),
    [academyTeachers],
  );
  const activeRosterRefreshToken = useMemo(
    () => activeTeachers
      .map((teacher) => `${asNumber(teacher.id)}:${asString(teacher.updated_at)}`)
      .join("|"),
    [activeTeachers],
  );
  const directorRosterTotals = useCanonicalTeacherRosterTotals(
    `${academyRosterRefreshToken}::${activeRosterRefreshToken}`,
    isAcademicDirectorMode,
  );
  const dashboardStats = useMemo(() => ({
    ...stats,
    total: isAcademicDirectorMode && !directorRosterTotals.isLoading
      ? directorRosterTotals.teacher_academy
      : stats.total,
  }), [directorRosterTotals.isLoading, directorRosterTotals.teacher_academy, isAcademicDirectorMode, stats]);
  const openCanonicalRosterTeacher = (teacher: TeacherRosterItem) => {
    if (teacher.kind === "active_teacher") {
      const active = activeTeachers.find((row) => asNumber(row.id) === teacher.record_id);
      if (active) {
        openActiveTeacherAccount(active);
        return;
      }
      showToast("The active teacher details are not available in this workspace yet.", "danger");
      return;
    }
    const academy = academyTeachers.find((row) => asNumber(row.id) === teacher.record_id);
    if (academy) {
      setDetailTeacher(academy);
      return;
    }
    showToast("The Teacher Academy details could not be loaded. Refresh and try again.", "danger");
  };
  function copyLogin(login: string) {
    const normalizedLogin = login.trim();
    if (!normalizedLogin) return;
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(normalizedLogin).catch(() => {});
    }
    showToast("Teacher login copied.");
  }

  function openActiveTeacherAccount(teacher: ActiveTeacher) {
    setTeacherPasswordResetError("");
    setTeacherPasswordResetCredentials(null);
    setTeacherPasswordResetting(false);
    setActiveTeacherAccount(teacher);
  }

  function closeActiveTeacherAccount() {
    setActiveTeacherAccount(null);
    setTeacherPasswordResetError("");
    setTeacherPasswordResetCredentials(null);
    setTeacherPasswordResetting(false);
  }

  async function resetActiveTeacherPassword() {
    const teacherId = asNumber(
      activeTeacherAccount?.account_teacher_id
      || activeTeacherAccount?.promoted_teacher_id
      || activeTeacherAccount?.id,
    );
    if (!teacherId) {
      setTeacherPasswordResetError("Reload this teacher account before resetting its password.");
      return;
    }
    setTeacherPasswordResetting(true);
    setTeacherPasswordResetError("");
    const { ok, data } = await postForm(
      routes.academicDirectorTeacherPasswordReset(teacherId),
      {},
      csrf,
    );
    setTeacherPasswordResetting(false);
    if (!ok) {
      setTeacherPasswordResetError(
        asString(data.message) || asString(data.detail) || "Unable to reset the teacher password.",
      );
      return;
    }
    const reset = data as TeacherPasswordResetCredentials;
    if (!asString(reset.temporary_password)) {
      setTeacherPasswordResetError("The password was reset, but no temporary password was returned. Please try again.");
      return;
    }
    setTeacherPasswordResetCredentials(reset);
    showToast("Password reset to the teacher's login.", "success");
  }

  function copyTeacherCredential(value: string, label: string) {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText && value) {
      void navigator.clipboard.writeText(value).catch(() => {});
      showToast(`${label} copied.`);
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

  function actionsForAcademyTeacher(teacher: AcademyTeacher): ActionMenuItem[] {
    const actions: ActionMenuItem[] = [];
    const nextAssignment = nextAcademyAssignment(teacher);
    const scheduled = assignmentIsScheduled(nextAssignment);

    if (canOnboardRecruitmentTeacher) {
      actions.push({
        key: "curriculum",
        label: asNumber(teacher.subject_program_id) ? "Edit curriculum" : "Assign curriculum",
        icon: <BookOpenCheck className="h-4 w-4" />,
        onClick: () => {
          setError("");
          setCurriculumTarget(teacher);
        },
      });
    }
    if (nextAssignment && canScheduleAcademyLesson) {
      actions.push({
        key: "schedule",
        label: scheduled ? "Reschedule next lesson" : "Schedule next lesson",
        icon: <CalendarClock className="h-4 w-4" />,
        onClick: () => setScheduleTarget({ teacher, assignment: nextAssignment }),
      });
    }
    if (nextAssignment && canAssessAcademyLesson) {
      actions.push({
        key: "assess",
        label: "Assess next lesson",
        icon: <ClipboardCheck className="h-4 w-4" />,
        onClick: () => setAssessmentTarget({ teacher, assignment: nextAssignment }),
      });
    }
    if (asString(teacher.login)) {
      actions.push({
        key: "copy-login",
        label: "Copy login",
        icon: <Copy className="h-4 w-4" />,
        onClick: () => copyLogin(asString(teacher.login)),
      });
    }
    if (isAcademicDirectorMode && asNumber(teacher.account_teacher_id || teacher.promoted_teacher_id)) {
      actions.push({
        key: "account",
        label: "Account access",
        icon: <KeyRound className="h-4 w-4" />,
        onClick: () => openActiveTeacherAccount(teacher),
      });
    }
    if (canPromoteAcademyTeacher && teacher.academy_status === "ready_for_active_teacher") {
      actions.push(
        { separator: true, key: "promote-separator" },
        {
          key: "promote",
          label: "Promote to Active Teacher",
          icon: <Trophy className="h-4 w-4" />,
          onClick: () => openPromote(teacher),
        },
      );
    }
    if (canDeleteAcademyTeacher) {
      actions.push(
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
    return actions;
  }

  return (
    <>
      {activeTeacherAccount ? (
        <ActiveTeacherAccountModal
          teacher={activeTeacherAccount}
          resetting={teacherPasswordResetting}
          resetError={teacherPasswordResetError}
          resetCredentials={teacherPasswordResetCredentials}
          onResetPassword={resetActiveTeacherPassword}
          onCopy={copyTeacherCredential}
          onClose={closeActiveTeacherAccount}
        />
      ) : null}
      {curriculumTarget ? (
        <AssignCurriculumModal
          teacher={curriculumTarget}
          programs={
            Array.isArray(state.props?.academicManagementCurriculumPrograms)
              ? state.props.academicManagementCurriculumPrograms
              : []
          }
          curriculumItems={
            Array.isArray(state.props?.academicManagementCurriculumItems)
              ? state.props.academicManagementCurriculumItems
              : []
          }
          submitting={submitting}
          error={error}
          onSubmit={(programId, lessonIds) => {
            void onboardRecruitmentAcademyTeacher(
              curriculumTarget,
              programId,
              lessonIds,
            );
          }}
          onClose={() => {
            if (!submitting) {
              setError("");
              setCurriculumTarget(null);
            }
          }}
        />
      ) : null}
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
          onAssess={(nextAssignment) => {
            setError("");
            setAssessmentTarget({ teacher: detailTeacher, assignment: nextAssignment });
          }}
          onReview={(assignment, report) => {
            setError("");
            setReportTarget({ teacher: detailTeacher, assignment, report });
          }}
          onReschedule={(assignment) => {
            setError("");
            setScheduleTarget({ teacher: detailTeacher, assignment });
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
          canSchedule={canScheduleAcademyLesson}
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
        <AssessmentModal
          teacher={reportTarget.teacher}
          assignment={reportTarget.assignment}
          initialReport={reportTarget.report}
          submitting={submitting}
          error={error}
          onSubmit={async (teacherId, fields) => {
            if (await submit(academyApi.assessmentCreate(teacherId), fields, "Assessment updated.")) {
              setReportTarget(null);
            }
          }}
          onClose={() => {
            setError("");
            setReportTarget(null);
          }}
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

      <div className="space-y-2">
        <TeacherAcademyDashboard
          mode={mode}
          stats={dashboardStats}
          activeTeacherCount={directorRosterTotals.active_teacher}
          view={activeView}
          onViewChange={setActiveView}
          onCreateHeadOfDepartment={canCreateHeadOfDepartment ? () => {
            setError("");
            setHodOpen(true);
          } : undefined}
          onCreateAcademyTeacher={canCreateAcademyTeacher ? () => {
            setError("");
            setCreateOpen(true);
          } : undefined}
        />

        {credentials ? (
          <section aria-live="polite" className="rounded-2xl border border-success/30 bg-success/10 p-4 text-foreground shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-black uppercase tracking-wide text-success">Generated credentials</p>
                <p className="mt-1 text-sm font-bold">
                  {asString(credentials.display_name) || "New account"} · {asString(credentials.subject_name) || asString(credentials.role)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setCredentials(null)}
                className="inline-flex min-h-11 items-center justify-center rounded-xl px-3 text-sm font-black text-success hover:bg-success/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-success/35"
              >
                Dismiss
              </button>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {[
                ["Login", asString(credentials.login) || asString(credentials.teacher_code)],
                ["Temporary password", asString(credentials.temporary_password)],
              ].map(([label, value]) => (
                <div key={label} className="flex min-w-0 items-center justify-between gap-2 rounded-xl border border-success/20 bg-card p-3">
                  <div className="min-w-0">
                    <p className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">{label}</p>
                    <p className="mt-1 truncate font-mono text-sm font-black text-foreground">{value || "Not returned"}</p>
                  </div>
                  {value ? (
                    <button
                      type="button"
                      onClick={() => copyTeacherCredential(value, label)}
                      className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
                      aria-label={`Copy ${label.toLowerCase()}`}
                    >
                      <Copy className="h-4 w-4" aria-hidden="true" />
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section
          id={`academy-panel-${activeView}`}
          role={isAcademicDirectorMode ? "tabpanel" : "region"}
          aria-labelledby={isAcademicDirectorMode ? `academy-tab-${activeView}` : undefined}
          aria-label={isAcademicDirectorMode ? undefined : "Teacher Academy roster"}
          tabIndex={0}
          className="min-w-0 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
        >
          {isAcademicDirectorMode ? (
            <TeacherAcademyRoster
              key={activeView}
              kind={activeView === "active_teachers" ? "active_teacher" : "teacher_academy"}
              refreshToken={activeView === "active_teachers" ? activeRosterRefreshToken : academyRosterRefreshToken}
              onOpenTeacher={openCanonicalRosterTeacher}
              onRemoved={(teacher) => {
                onAcademyChange(academyTeachers.filter((row) => asNumber(row.id) !== teacher.record_id));
                if (asNumber(detailTeacher?.id) === teacher.record_id) setDetailTeacher(null);
              }}
              onAnnouncement={(message, tone) => showToast(message, tone === "error" ? "danger" : "success")}
            />
          ) : (
            <ScopedTeacherAcademyRoster
              teachers={academyTeachers}
              subjects={subjects}
              onOpenTeacher={setDetailTeacher}
              actionsForTeacher={actionsForAcademyTeacher}
            />
          )}
        </section>
      </div>

    </>
  );
}
