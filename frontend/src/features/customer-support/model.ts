export type SupportRecordKind = "student" | "parent";
export type SupportWorkspaceView = "dashboard" | "payments" | "parents" | "students" | "tickets";
export type SupportRecordStatus = "active" | "disabled" | "archived";
export type SupportLanguage = "uz" | "ru" | "en";

export type SupportSchool = {
  id: number;
  school_key: string;
  school_name: string;
};

export type SupportRecordSummary = {
  kind: SupportRecordKind;
  id: number;
  display_name: string;
  secondary: string;
  phone?: string;
  telegram_username?: string;
  status: string;
  school_id?: number;
  school_name: string;
  version: number;
  outstanding: number;
  linked_count: number;
};

export type StudentProfile = {
  id: number;
  legacy_student_row_id?: number;
  student_code: string;
  full_name: string;
  school_id: number;
  school_name: string;
  school_key?: string;
  phone?: string;
  photo_url?: string;
  profile_description?: string;
  telegram_username?: string;
  status: string;
  version: number;
  login?: string;
  account_id?: number;
  account_status?: string;
  must_change_password?: boolean;
  last_login_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ParentProfile = {
  id: number;
  display_name: string;
  phone?: string;
  telegram_user_id?: number;
  telegram_username?: string;
  preferred_language: SupportLanguage | string;
  status: string;
  version: number;
  account_id?: number;
  account_status?: string;
  last_login_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type StudentEnrollment = {
  id: number;
  status: string;
  joined_at?: string;
  left_at?: string | null;
  group_id: number;
  group_name: string;
  subject_id: number;
  subject_name: string;
  homework_average: number;
  exam_average: number;
  present_count?: number;
  absent_count?: number;
  justified_count?: number;
  attendanceRate: number;
};

export type ParentStudentLink = {
  id: number;
  student_code: string;
  full_name: string;
  status: string;
  school_id: number;
  school_name: string;
  relationship?: string;
  linked_at?: string;
  outstanding: number;
};

export type StudentParentLink = {
  id: number;
  display_name: string;
  phone?: string;
  telegram_username?: string;
  preferred_language?: string;
  status: string;
  version: number;
  relationship?: string;
  linked_at?: string;
};

export type ParentInviteSummary = {
  id: number;
  status: "pending" | "consumed" | "expired" | "revoked" | string;
  created_at: string;
  expires_at?: string | null;
  used_at?: string | null;
  used_count: number;
  max_uses: number;
  used_by_parent_id?: number | null;
  used_by_parent_name?: string;
};

export type PaymentState = "paid" | "due" | "debt" | "upcoming" | "voided";

export type PaymentRecord = {
  id: number;
  student_id: number;
  group_id?: number;
  subject_id?: number;
  subject?: string;
  month_label?: string;
  amount: number;
  currency: string;
  status: string;
  state: PaymentState | string;
  due_date?: string | null;
  paid_at?: string | null;
  notes?: string;
  version: number;
  voided_at?: string | null;
  void_reason?: string;
  created_at?: string;
  updated_at?: string;
};

export type PaymentTotals = {
  paid: number;
  due: number;
  debt: number;
  upcoming: number;
};

export type PaymentPayload = {
  items: PaymentRecord[];
  totals: PaymentTotals;
  currency: string;
};

export type SupportAuditEvent = {
  id: number;
  eventType: string;
  entityType: string;
  actor: string;
  details?: unknown;
  createdAt: string;
};

export type StudentDetail = {
  kind: "student";
  profile: StudentProfile;
  academic: StudentEnrollment[];
  parents: StudentParentLink[];
  parentInvites: ParentInviteSummary[];
  payments: PaymentPayload;
  activity: SupportAuditEvent[];
};

export type ParentDetail = {
  kind: "parent";
  profile: ParentProfile;
  children: ParentStudentLink[];
  hiddenChildCount: number;
  activity: SupportAuditEvent[];
};

export type SupportDetail = StudentDetail | ParentDetail;

export type SupportDetailByKind = {
  student: StudentDetail;
  parent: ParentDetail;
};

export type SupportContext = {
  schools: SupportSchool[];
  allSchools: boolean;
  recordTypes: Array<"all" | SupportRecordKind>;
  statuses: Array<"all" | SupportRecordStatus>;
  languages: SupportLanguage[];
  permissions: {
    manageStudents: boolean;
    manageParents: boolean;
    managePayments: boolean;
    manageAcademicPlacement: boolean;
  };
};

export type SearchPayload = {
  items: SupportRecordSummary[];
  nextCursor?: string | null;
  hasMore: boolean;
};

export type StudentCredentials = {
  login: string;
  temporaryPassword: string;
  mustChangePassword: boolean;
};

export type StudentMutationResult = {
  record: StudentDetail;
  credentials: StudentCredentials;
};

export type ParentInviteResult = {
  inviteCode: string;
  studentId: number;
  inviteUrl: string;
  telegramInviteUrl?: string;
  webInviteUrl: string;
};

export type ActiveDependency = {
  group_id?: number;
  group_name?: string;
  subject_name?: string;
};

export type SupportApiErrorDetails = {
  currentVersion?: number;
  groups?: ActiveDependency[];
};

export type SupportErrorCode =
  | "record_not_found"
  | "school_scope_denied"
  | "version_conflict"
  | "active_dependencies"
  | "customer_support_error"
  | string;
