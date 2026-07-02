const adminStudentQuery = (school = "all") =>
  `school=${encodeURIComponent(String(school || "all"))}&embed=admin`;

export const routes = {
  home: "/",
  login: "/login",
  logout: "/logout",
  search: "/search",
  changePassword: "/profile/password",
  dashboard: (studentId: number | string) => `/dashboard/${studentId}`,
  resources: (studentId: number | string) => `/dashboard/${studentId}/resources`,
  rating: (studentId: number | string) => `/dashboard/${studentId}/rating-board`,
  aap: (studentId: number | string) => `/dashboard/${studentId}/aap-lessons`,
  ar: (studentId: number | string) => `/dashboard/${studentId}/ar-lessons`,
  chat: (studentId: number | string) => `/dashboard/${studentId}/chat`,
  adminTeacherCreate: "/admin/teachers",
  adminTeacherUpdate: (teacherId: number | string) => `/admin/teachers/${teacherId}`,
  adminTeacherDelete: (teacherId: number | string) => `/admin/teachers/${teacherId}/delete`,
  adminTeacherEdit: (teacherId: number | string, school = "all", mode = "") =>
    `/?panel=teachers&school=${encodeURIComponent(String(school || "all"))}${
      mode ? `&mode=${encodeURIComponent(String(mode))}` : ""
    }&edit_teacher_id=${encodeURIComponent(String(teacherId))}`,
  adminTeacherCandidateCreate: "/admin/teacher-candidates",
  adminTeacherCandidateStatus: (candidateId: number | string) => `/admin/teacher-candidates/${candidateId}/status`,
  adminTeacherCandidatePromote: (candidateId: number | string) => `/admin/teacher-candidates/${candidateId}/promote`,
  adminTeacherCandidateEventEdit: (candidateId: number | string, eventId: number | string) =>
    `/admin/teacher-candidates/${candidateId}/events/${eventId}/edit`,
  adminTeacherCandidateEventDelete: (candidateId: number | string, eventId: number | string) =>
    `/admin/teacher-candidates/${candidateId}/events/${eventId}/delete`,
  adminTeacherAcademyCreate: "/admin/teacher-academy",
  adminTeacherAcademyAssignment: (assignmentId: number | string) =>
    `/admin/teacher-academy/assignments/${assignmentId}`,
  adminTeacherAcademyAssessment: (academyTeacherId: number | string) =>
    `/admin/teacher-academy/${academyTeacherId}/assessments`,
  adminTeacherAcademyStatus: (academyTeacherId: number | string) =>
    `/admin/teacher-academy/${academyTeacherId}/status`,
  adminTeacherAcademyPromote: (academyTeacherId: number | string) =>
    `/admin/teacher-academy/${academyTeacherId}/promote`,
  adminResourceTypeAdd: "/admin/resources/types/add",
  adminResourceTypeDelete: (typeId: number | string) => `/admin/resources/types/${typeId}/delete`,
  adminResourceTypeRename: (typeId: number | string) => `/admin/resources/types/${typeId}/rename`,
  adminResourceAdd: "/admin/resources/add",
  adminResourceDelete: (resourceId: number | string) => `/admin/resources/${resourceId}/delete`,
  adminResourceEdit: (resourceId: number | string) => `/admin/resources/${resourceId}/edit`,
  adminResourcesApi: "/admin/api/resources",
  adminStudentsApi: "/admin/api/students",
  adminComplaintsApi: "/admin/api/complaints",
  adminComplaintApi: (complaintId: number | string) => `/admin/api/complaints/${complaintId}`,
  adminComplaintReplies: (complaintId: number | string) =>
    `/admin/api/complaints/${complaintId}/replies`,
  adminStudentPaymentsApi: (studentRowId: number | string) => `/admin/api/students/${studentRowId}/payments`,
  adminStudentPaymentApi: (paymentId: number | string) => `/admin/api/student-payments/${paymentId}`,
  adminAcademicSubjectCreate: "/admin/academic/subjects",
  adminAcademicSchoolCreate: "/admin/academic/schools",
  adminAcademicGroupCreate: "/admin/academic/groups",
  adminAcademicGroupApi: (groupId: number | string) => `/admin/api/academic/groups/${groupId}`,
  adminAcademicScheduleCreate: "/admin/api/academic/schedules",
  adminAcademicGradebookApi: (groupId: number | string) => `/admin/api/academic/gradebook?group_id=${groupId}`,
  adminAcademicAttendanceApi: "/admin/api/academic/attendance",
  adminAcademicHomeworkApi: "/admin/api/academic/homework",
  adminAcademicEnrollmentStatusApi: (enrollmentId: number | string) =>
    `/admin/api/academic/enrollments/${enrollmentId}/status`,
  adminAcademicEnrollmentGroupApi: (enrollmentId: number | string) =>
    `/admin/api/academic/enrollments/${enrollmentId}/group`,
  adminAnnouncementsApi: "/admin/api/announcements",
  adminAnnouncementApi: (announcementId: number | string) => `/admin/api/announcements/${announcementId}`,
  adminParentInvite: (studentRowId: number | string) =>
    `/admin/api/students/${studentRowId}/parent-invite`,
  adminParentAccount: (parentAdminId: number | string) => `/admin/parents/${parentAdminId}`,
  adminParentChildrenFor: (parentAdminId: number | string) => `/admin/parents/${parentAdminId}/children`,
  adminParentChildFor: (parentAdminId: number | string, studentRowId: number | string) =>
    `/admin/parents/${parentAdminId}/children/${studentRowId}`,
  adminParentChildren: "/admin/parent-children",
  adminParentChild: (studentRowId: number | string) => `/admin/parent-children/${studentRowId}`,
  parentStudentDashboard: (studentRowId: number | string) => `/parent/dashboard/${studentRowId}`,
  adminStudentProfile: (studentRowId: number | string) => `/admin/students/${studentRowId}`,
  adminStudentPanel: (studentRowId: number | string, school = "all", panel = "student_dashboard") =>
    `/?panel=${encodeURIComponent(String(panel || "student_dashboard"))}&school=${encodeURIComponent(String(school || "all"))}&student=${encodeURIComponent(String(studentRowId))}`,
  adminStudentDashboard: (studentRowId: number | string, school = "all") =>
    `/admin/students/${studentRowId}/dashboard?${adminStudentQuery(school)}`,
  adminStudentDashboardTarget: (studentRowId: number | string, target: string, school = "all") =>
    `/admin/students/${studentRowId}/dashboard/${encodeURIComponent(String(target || "dashboard"))}?${adminStudentQuery(school)}`,
  adminStudentSave: (studentRowId: number | string) => `/admin/students/${studentRowId}/profile`,
};
