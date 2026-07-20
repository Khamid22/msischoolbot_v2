import { apiRoutes } from "../api/routes.ts";

type GradebookQuery = { lessonLimit?: number; cursor?: string; direction?: string; anchorDate?: string; month?: string; section?: string };
type GradebookTrendsQuery = { through: string; months?: number };

const gradebookUrl = (base: string, groupId: number | string, query: GradebookQuery = {}) => {
  const params = new URLSearchParams({ group_id: String(groupId) });
  if (query.lessonLimit) params.set("lesson_limit", String(query.lessonLimit));
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.direction) params.set("direction", query.direction);
  if (query.anchorDate) params.set("anchor_date", query.anchorDate);
  if (query.month) params.set("month", query.month);
  if (query.section) params.set("section", query.section);
  return `${base}?${params.toString()}`;
};

const gradebookTrendsUrl = (base: string, groupId: number | string, query: GradebookTrendsQuery) => {
  const params = new URLSearchParams({ through: query.through });
  if (query.months) params.set("months", String(query.months));
  return `${base}/${groupId}/gradebook-trends?${params.toString()}`;
};

export const routes = {
  home: "/",
  login: "/login",
  logout: "/logout",
  search: "/search",
  accountSecurity: "/account/security",
  changePassword: "/account/security",
  dashboard: (studentId: number | string) => `/dashboard/${studentId}`,
  resources: (studentId: number | string) => `/dashboard/${studentId}/resources`,
  rating: (studentId: number | string) => `/dashboard/${studentId}/rating-board`,
  aap: (studentId: number | string) => `/dashboard/${studentId}/aap-lessons`,
  ar: (studentId: number | string) => `/dashboard/${studentId}/ar-lessons`,
  chat: (studentId: number | string) => `/dashboard/${studentId}/chat`,
  academicDirectorOverview: "/academic-director",
  academicDirectorTeacherAcademy: "/academic-director/teacher-academy",
  academicDirectorHeadOfDepartments: "/academic-director/head-of-departments",
  academicDirectorGroups: "/academic-director/groups",
  academicDirectorSubjects: "/academic-director/subjects",
  academicDirectorTimetable: "/academic-director/timetable",
  academicDirectorAnnouncements: "/academic-director/announcements",
  academicDirectorRecruitment: "/academic-director/recruitment",
  academicDirectorProfile: "/academic-director/profile",
  academicDirectorHeadOfDepartmentCreate: apiRoutes.academicDirectorHeadOfDepartmentCreate,
  academicDirectorHeadOfDepartmentPasswordReset: apiRoutes.academicDirectorHeadOfDepartmentPasswordReset,
  academicDirectorTeacherPasswordReset: apiRoutes.academicDirectorTeacherPasswordReset,
  academicDirectorTeacherAcademyCreate: apiRoutes.academicDirectorTeacherAcademyCreate,
  academicDirectorTeacherAcademyAssignmentUpdate: apiRoutes.academicDirectorTeacherAcademyAssignmentUpdate,
  academicDirectorTeacherAcademyAssessmentCreate: apiRoutes.academicDirectorTeacherAcademyAssessmentCreate,
  academicDirectorTeacherAcademyAssessmentDelete: apiRoutes.academicDirectorTeacherAcademyAssessmentDelete,
  academicDirectorTeacherAcademyStatusUpdate: apiRoutes.academicDirectorTeacherAcademyStatusUpdate,
  academicDirectorTeacherAcademyLessonsSync: apiRoutes.academicDirectorTeacherAcademyLessonsSync,
  academicDirectorTeacherAcademyPromote: apiRoutes.academicDirectorTeacherAcademyPromote,
  headOfDepartmentOverview: "/head-of-departments",
  headOfDepartmentTeacherAcademy: "/head-of-departments/teacher-academy",
  headOfDepartmentTimetable: "/head-of-departments/timetable",
  headOfDepartmentAnnouncements: "/head-of-departments/announcements",
  headOfDepartmentRecruitment: "/head-of-departments/recruitment",
  headOfDepartmentProfile: "/head-of-departments/profile",
  ceoRecruitment: "/ceo/recruitment",
  headOfDepartmentTeacherAcademyAssignmentUpdate: apiRoutes.headOfDepartmentTeacherAcademyAssignmentUpdate,
  headOfDepartmentTeacherAcademyAssessmentCreate: apiRoutes.headOfDepartmentTeacherAcademyAssessmentCreate,
  headOfDepartmentTeacherAcademyAssessmentDelete: apiRoutes.headOfDepartmentTeacherAcademyAssessmentDelete,
  headOfDepartmentTeacherAcademyStatusUpdate: apiRoutes.headOfDepartmentTeacherAcademyStatusUpdate,
  headOfDepartmentTeacherAcademyLessonsSync: apiRoutes.headOfDepartmentTeacherAcademyLessonsSync,
  academicDirectorAcademicSchoolCreate: apiRoutes.academicDirectorAcademicSchoolCreate,
  academicDirectorAcademicCalendarClosuresApi: apiRoutes.academicDirectorAcademicCalendarClosuresApi,
  academicDirectorAcademicCalendarClosurePreview: apiRoutes.academicDirectorAcademicCalendarClosurePreview,
  academicDirectorAcademicCalendarClosureCreate: apiRoutes.academicDirectorAcademicCalendarClosureCreate,
  academicDirectorAcademicCalendarClosureUnlock: apiRoutes.academicDirectorAcademicCalendarClosureUnlock,
  academicDirectorAcademicGroupCreate: apiRoutes.academicDirectorAcademicGroupCreate,
  academicDirectorAcademicContextApi: apiRoutes.academicDirectorAcademicContextApi,
  academicDirectorAcademicGroupsApi: apiRoutes.academicDirectorAcademicGroupsApi,
  academicDirectorAcademicProgramsApi: apiRoutes.academicDirectorAcademicProgramsApi,
  academicDirectorAcademicProgramItemsApi: apiRoutes.academicDirectorAcademicProgramItemsApi,
  academicDirectorAcademicTimetableApi: apiRoutes.academicDirectorAcademicTimetableApi,
  academicDirectorAcademicGroupTimetableApi: apiRoutes.academicDirectorAcademicGroupTimetableApi,
  academicDirectorAcademicGroupApi: apiRoutes.academicDirectorAcademicGroupApi,
  academicDirectorAcademicGroupSummaryApi: apiRoutes.academicDirectorAcademicGroupSummaryApi,
  academicDirectorAcademicScheduleCreate: apiRoutes.academicDirectorAcademicScheduleCreate,
  academicDirectorAcademicGroupSchedule: apiRoutes.academicDirectorAcademicGroupSchedule,
  academicDirectorAcademicGroupStudents: apiRoutes.academicDirectorAcademicGroupStudents,
  academicDirectorAcademicGradebookApi: apiRoutes.academicDirectorAcademicGradebookApi,
  academicDirectorAcademicGradebookTrendsApi: apiRoutes.academicDirectorAcademicGradebookTrendsApi,
  academicDirectorAcademicAttendanceApi: apiRoutes.academicDirectorAcademicAttendanceApi,
  academicDirectorAcademicHomeworkApi: apiRoutes.academicDirectorAcademicHomeworkApi,
  academicDirectorAcademicExamApi: apiRoutes.academicDirectorAcademicExamApi,
  academicDirectorAcademicLessonApi: apiRoutes.academicDirectorAcademicLessonApi,
  academicDirectorAcademicLessonCancelApi: apiRoutes.academicDirectorAcademicLessonCancelApi,
  academicDirectorAcademicLessonRecoverApi: apiRoutes.academicDirectorAcademicLessonRecoverApi,
  academicDirectorAcademicEnrollmentStatusApi: apiRoutes.academicDirectorAcademicEnrollmentStatusApi,
  academicDirectorAcademicEnrollmentGroupApi: apiRoutes.academicDirectorAcademicEnrollmentGroupApi,
  academicManagementSchoolCreate: apiRoutes.academicDirectorAcademicSchoolCreate,
  academicManagementSchoolCreateApi: apiRoutes.academicDirectorAcademicSchoolCreate,
  academicManagementGroupCreate: apiRoutes.academicDirectorAcademicGroupCreate,
  academicManagementGroupCreateApi: apiRoutes.academicDirectorAcademicGroupCreate,
  academicManagementContextApi: apiRoutes.academicDirectorAcademicContextApi,
  academicManagementGroupsApi: apiRoutes.academicDirectorAcademicGroupsApi,
  academicManagementProgramsApi: apiRoutes.academicDirectorAcademicProgramsApi,
  academicManagementProgramItemsApi: apiRoutes.academicDirectorAcademicProgramItemsApi,
  academicManagementTimetableApi: apiRoutes.academicDirectorAcademicTimetableApi,
  academicManagementGroupTimetableApi: apiRoutes.academicDirectorAcademicGroupTimetableApi,
  academicManagementCalendarClosuresApi: apiRoutes.academicDirectorAcademicCalendarClosuresApi,
  academicManagementCalendarClosurePreview: apiRoutes.academicDirectorAcademicCalendarClosurePreview,
  academicManagementCalendarClosureCreate: apiRoutes.academicDirectorAcademicCalendarClosureCreate,
  academicManagementCalendarClosureUnlock: apiRoutes.academicDirectorAcademicCalendarClosureUnlock,
  academicManagementGroupApi: apiRoutes.academicDirectorAcademicGroupApi,
  academicManagementGroupSummaryApi: apiRoutes.academicDirectorAcademicGroupSummaryApi,
  academicManagementScheduleCreate: apiRoutes.academicDirectorAcademicScheduleCreate,
  academicManagementGroupSchedule: apiRoutes.academicDirectorAcademicGroupSchedule,
  academicManagementGroupStudents: apiRoutes.academicDirectorAcademicGroupStudents,
  academicManagementGradebookApi: apiRoutes.academicDirectorAcademicGradebookApi,
  academicManagementGradebookTrendsApi: apiRoutes.academicDirectorAcademicGradebookTrendsApi,
  academicManagementAttendanceApi: apiRoutes.academicDirectorAcademicAttendanceApi,
  academicManagementHomeworkApi: apiRoutes.academicDirectorAcademicHomeworkApi,
  academicManagementExamApi: apiRoutes.academicDirectorAcademicExamApi,
  academicManagementLessonApi: apiRoutes.academicDirectorAcademicLessonApi,
  academicManagementLessonCancelApi: apiRoutes.academicDirectorAcademicLessonCancelApi,
  academicManagementLessonRecoverApi: apiRoutes.academicDirectorAcademicLessonRecoverApi,
  academicManagementEnrollmentStatusApi: apiRoutes.academicDirectorAcademicEnrollmentStatusApi,
  academicManagementEnrollmentGroupApi: apiRoutes.academicDirectorAcademicEnrollmentGroupApi,
  parentStudentDashboard: (studentRowId: number | string) => `/parent/dashboard/${studentRowId}`,
};
