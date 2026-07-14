type GradebookQuery = { lessonLimit?: number; cursor?: string; direction?: string; anchorDate?: string; month?: string; section?: string };
type GradebookTrendsQuery = { through: string; months?: number };

function gradebookUrl(base: string, groupId: number | string, query: GradebookQuery = {}) {
  const params = new URLSearchParams({ group_id: String(groupId) });
  if (query.lessonLimit) params.set("lesson_limit", String(query.lessonLimit));
  if (query.cursor) params.set("cursor", query.cursor);
  if (query.direction) params.set("direction", query.direction);
  if (query.anchorDate) params.set("anchor_date", query.anchorDate);
  if (query.month) params.set("month", query.month);
  if (query.section) params.set("section", query.section);
  return `${base}?${params.toString()}`;
}

function gradebookTrendsUrl(base: string, groupId: number | string, query: GradebookTrendsQuery) {
  const params = new URLSearchParams({ through: query.through });
  if (query.months) params.set("months", String(query.months));
  return `${base}/${groupId}/gradebook-trends?${params.toString()}`;
}

export const apiRoutes = {
  accountPassword: "/api/v1/auth/password",
  academicDirectorHeadOfDepartmentCreate: "/api/v1/academic-director/head-of-departments",
  academicDirectorHeadOfDepartmentPasswordReset: (accountId: number | string) =>
    `/api/v1/academic-director/head-of-departments/${accountId}/reset-password`,
  academicDirectorTeacherPasswordReset: (teacherId: number | string) =>
    `/api/v1/academic-director/teachers/${teacherId}/reset-password`,
  academicDirectorTeacherAcademyCreate: "/api/v1/academic-director/teacher-academy",
  academicDirectorTeacherAcademyAssignmentUpdate: (assignmentId: number | string) =>
    `/api/v1/academic-director/teacher-academy/assignments/${assignmentId}`,
  academicDirectorTeacherAcademyAssessmentCreate: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/assessments`,
  academicDirectorTeacherAcademyAssessmentDelete: (academyTeacherId: number | string, assessmentId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/assessments/${assessmentId}/delete`,
  academicDirectorTeacherAcademyStatusUpdate: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/status`,
  academicDirectorTeacherAcademyLessonsSync: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/lessons`,
  academicDirectorTeacherAcademyPromote: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/promote`,
  academicDirectorTeacherAcademyDelete: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/delete`,
  academicDirectorAcademicContextApi: "/api/v1/academic-director/academic/context",
  academicDirectorAcademicGroupsApi: (query = "") => `/api/v1/academic-director/academic/groups${query ? `?${query}` : ""}`,
  academicDirectorAcademicProgramsApi: (query = "") => `/api/v1/academic-director/academic/programs${query ? `?${query}` : ""}`,
  academicDirectorAcademicProgramItemsApi: (programId: number | string, query = "") =>
    `/api/v1/academic-director/academic/programs/${programId}/items${query ? `?${query}` : ""}`,
  academicDirectorAcademicTimetableApi: (query: string) => `/api/v1/academic-director/academic/timetable?${query}`,
  academicDirectorAcademicGroupTimetableApi: (groupId: number | string, query: string) =>
    `/api/v1/academic-director/academic/groups/${groupId}/timetable?${query}`,
  academicDirectorAcademicCalendarClosuresApi: (query = "") =>
    `/api/v1/academic-director/academic/calendar-closures${query ? `?${query}` : ""}`,
  academicDirectorAcademicCalendarClosurePreview: "/api/v1/academic-director/academic/calendar-closures/preview",
  academicDirectorAcademicCalendarClosureCreate: "/api/v1/academic-director/academic/calendar-closures",
  academicDirectorAcademicCalendarClosureUnlock: (closureId: number | string) =>
    `/api/v1/academic-director/academic/calendar-closures/${closureId}/unlock`,
  academicDirectorAcademicSchoolCreate: "/api/v1/academic-director/academic/schools",
  academicDirectorAcademicGroupCreate: "/api/v1/academic-director/academic/groups",
  academicDirectorAcademicGroupApi: (groupId: number | string) =>
    `/api/v1/academic-director/academic/groups/${groupId}`,
  academicDirectorAcademicGroupSummaryApi: (groupId: number | string) =>
    `/api/v1/academic-director/academic/groups/${groupId}/summary`,
  academicDirectorAcademicScheduleCreate: "/api/v1/academic-director/academic/schedules",
  academicDirectorAcademicGroupSchedule: (groupId: number | string) => `/api/v1/academic-director/academic/groups/${groupId}/schedule`,
  academicDirectorAcademicGroupStudents: (groupId: number | string) => `/api/v1/academic-director/academic/groups/${groupId}/students`,
  academicDirectorAcademicGradebookApi: (groupId: number | string, query?: GradebookQuery) =>
    gradebookUrl("/api/v1/academic-director/academic/gradebook", groupId, query),
  academicDirectorAcademicGradebookTrendsApi: (groupId: number | string, query: GradebookTrendsQuery) =>
    gradebookTrendsUrl("/api/v1/academic-director/academic/groups", groupId, query),
  academicDirectorAcademicAttendanceApi: "/api/v1/academic-director/academic/attendance",
  academicDirectorAcademicHomeworkApi: "/api/v1/academic-director/academic/homework",
  academicDirectorAcademicExamApi: "/api/v1/academic-director/academic/exams",
  academicDirectorAcademicLessonApi: (lessonSessionId: number | string) =>
    `/api/v1/academic-director/academic/lessons/${lessonSessionId}`,
  academicDirectorAcademicLessonCancelApi: (lessonSessionId: number | string) =>
    `/api/v1/academic-director/academic/lessons/${lessonSessionId}/cancel`,
  academicDirectorAcademicLessonRecoverApi: (lessonSessionId: number | string) =>
    `/api/v1/academic-director/academic/lessons/${lessonSessionId}/recover`,
  academicDirectorAcademicEnrollmentStatusApi: (enrollmentId: number | string) =>
    `/api/v1/academic-director/academic/enrollments/${enrollmentId}/status`,
  academicDirectorAcademicEnrollmentGroupApi: (enrollmentId: number | string) =>
    `/api/v1/academic-director/academic/enrollments/${enrollmentId}/group`,
  headOfDepartmentTeacherAcademyAssignmentUpdate: (assignmentId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/assignments/${assignmentId}`,
  headOfDepartmentTeacherAcademyAssessmentCreate: (academyTeacherId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/assessments`,
  headOfDepartmentTeacherAcademyAssessmentDelete: (academyTeacherId: number | string, assessmentId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/assessments/${assessmentId}/delete`,
  headOfDepartmentTeacherAcademyStatusUpdate: (academyTeacherId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/status`,
  headOfDepartmentTeacherAcademyLessonsSync: (academyTeacherId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/lessons`,
};

export const studentApiRoutes = {
  activityPing: "/api/v1/student/activity/ping",
  chatMessages: "/api/v1/student/chat/messages",
  chatMessage: (id: number | string) => `/api/v1/student/chat/messages/${id}`,
  officeHoursAvailability: "/api/v1/student/office-hours/availability",
  officeHoursBookings: "/api/v1/student/office-hours/bookings",
  officeHoursBooking: (id: number | string) => `/api/v1/student/office-hours/bookings/${id}`,
  resourceComments: (resourceId: number | string) => `/api/v1/student/resources/${resourceId}/comments`,
};
