export const apiRoutes = {
  academicDirectorHeadOfDepartmentCreate: "/api/v1/academic-director/head-of-departments",
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
  academicDirectorAcademicSchoolCreate: "/api/v1/academic-director/academic/schools",
  academicDirectorAcademicGroupCreate: "/api/v1/academic-director/academic/groups",
  academicDirectorAcademicGroupApi: (groupId: number | string) =>
    `/api/v1/academic-director/academic/groups/${groupId}`,
  academicDirectorAcademicScheduleCreate: "/api/v1/academic-director/academic/schedules",
  academicDirectorAcademicGradebookApi: (groupId: number | string) =>
    `/api/v1/academic-director/academic/gradebook?group_id=${groupId}`,
  academicDirectorAcademicAttendanceApi: "/api/v1/academic-director/academic/attendance",
  academicDirectorAcademicHomeworkApi: "/api/v1/academic-director/academic/homework",
  academicDirectorAcademicExamApi: "/api/v1/academic-director/academic/exams",
  academicDirectorAcademicLessonApi: (lessonSessionId: number | string) =>
    `/api/v1/academic-director/academic/lessons/${lessonSessionId}`,
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
