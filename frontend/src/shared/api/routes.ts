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
  academicDirectorTeacherAcademyPromote: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/promote`,
  academicDirectorTeacherAcademyDelete: (academyTeacherId: number | string) =>
    `/api/v1/academic-director/teacher-academy/${academyTeacherId}/delete`,
  headOfDepartmentTeacherAcademyAssignmentUpdate: (assignmentId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/assignments/${assignmentId}`,
  headOfDepartmentTeacherAcademyAssessmentCreate: (academyTeacherId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/assessments`,
  headOfDepartmentTeacherAcademyAssessmentDelete: (academyTeacherId: number | string, assessmentId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/assessments/${assessmentId}/delete`,
  headOfDepartmentTeacherAcademyStatusUpdate: (academyTeacherId: number | string) =>
    `/api/v1/head-of-department/teacher-academy/${academyTeacherId}/status`,
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
