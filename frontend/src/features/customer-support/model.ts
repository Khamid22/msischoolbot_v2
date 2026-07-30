export type SupportRecordKind = "student" | "parent";
export type SupportWorkspaceView = "dashboard" | "admissions" | "payments" | "parents" | "students" | "teachers" | "tickets";
export type SupportRecordStatus = "active" | "disabled" | "archived";
export type SupportLanguage = "uz" | "ru" | "en";

export type AdmissionStatus =
  | "draft"
  | "contract_sent"
  | "contract_submitted"
  | "awaiting_payment"
  | "active"
  | "cancelled"
  | "expired"
  | "payment_review";
export type AdmissionContractStatus =
  | "draft"
  | "sent"
  | "submitted"
  | "accepted"
  | "rejected"
  | "superseded";
export type AdmissionInvoiceStatus =
  | "draft"
  | "issued"
  | "partially_paid"
  | "paid"
  | "overdue"
  | "voided";

export type AdmissionGroupOption = {
  groupId: number;
  schoolId: number;
  schoolName: string;
  groupName: string;
  subjectId: number;
  subjectName: string;
};

export type AdmissionGroup = {
  groupId: number;
  groupName: string;
  subjectId: number;
  subjectName: string;
  monthlyAmountMinor: number;
};

export type AdmissionContract = {
  contractId: number;
  version: number;
  status: AdmissionContractStatus;
  originalFileName: string;
  originalMimeType: string;
  originalSizeBytes: number;
  signedFileName: string;
  signedMimeType: string;
  signedSizeBytes: number | null;
  submittedAt: string | null;
  reviewedAt: string | null;
  rejectionReason: string;
};

export type AdmissionInvoicePayment = {
  paymentId: number;
  source: "payme" | "manual";
  method: string;
  amountMinor: number;
  currency: string;
  status: string;
  reference: string;
  reason: string;
  paidAt: string;
};

export type AdmissionInvoice = {
  invoiceId: number;
  invoiceNumber: string;
  invoiceKind: "first" | "monthly" | "manual";
  billingPeriod: string;
  currency: string;
  totalMinor: number;
  paidMinor: number;
  balanceMinor: number;
  status: AdmissionInvoiceStatus;
  dueDate: string;
  issuedAt: string | null;
  paidAt: string | null;
  version: number;
  lines: Array<{
    lineId: number;
    groupId: number | null;
    subjectId: number | null;
    description: string;
    amountMinor: number;
  }>;
  payments: AdmissionInvoicePayment[];
};

export type AdmissionAuditEvent = {
  eventId: number;
  eventType: string;
  entityType: string;
  entityId: number;
  detailSummary: string;
  actorStaffId: number | null;
  createdAt: string;
};

export type AdmissionSummary = {
  admissionId: number;
  schoolId: number;
  schoolName: string;
  studentFullName: string;
  parentFullName: string;
  parentPhone: string;
  status: AdmissionStatus;
  contractStatus: AdmissionContractStatus | null;
  firstInvoiceStatus: AdmissionInvoiceStatus | null;
  firstDueDate: string;
  updatedAt: string;
};

export type AdmissionPage = {
  items: AdmissionSummary[];
  total: number;
};

export type AdmissionDetail = {
  admissionId: number;
  schoolId: number;
  schoolName: string;
  studentFullName: string;
  studentPhone: string;
  parentFullName: string;
  parentPhone: string;
  parentTelegramUsername: string;
  preferredLanguage: "uz" | "ru";
  serviceStartDate: string | null;
  firstDueDate: string;
  billingDay: number;
  currency: string;
  status: AdmissionStatus;
  version: number;
  activatedStudentId: number | null;
  activatedParentId: number | null;
  activatedAt: string | null;
  cancellationReason: string;
  groups: AdmissionGroup[];
  contract: AdmissionContract | null;
  invoices: AdmissionInvoice[];
  auditEvents: AdmissionAuditEvent[];
  createdAt: string;
  updatedAt: string;
};

export type AdmissionCreated = {
  admission: AdmissionDetail;
  admissionLink: {
    accessToken: string;
    expiresAt: string;
  };
  publicUrl: string;
};

export type AdmissionInvoiceQueueItem = {
  invoiceId: number;
  invoiceNumber: string;
  admissionId: number | null;
  studentId: number | null;
  studentRowId: number | null;
  schoolId: number;
  schoolName: string;
  studentName: string;
  studentCode: string;
  parentName: string;
  invoiceKind: string;
  origin: "admission" | "student_billing" | "legacy_migration" | string;
  billingPeriod: string;
  currency: string;
  totalMinor: number;
  paidMinor: number;
  balanceMinor: number;
  status: AdmissionInvoiceStatus;
  dueDate: string;
  issuedAt: string | null;
  paidAt: string | null;
  enforcementState: "scheduled" | "countdown" | "held" | "cleared" | "cancelled" | null;
  countdownStartedAt: string | null;
  paymentDeadlineAt: string | null;
  version: number;
};

export type AdmissionInvoiceQueue = {
  items: AdmissionInvoiceQueueItem[];
  total: number;
  nextCursor?: string | null;
};

export type BillingAccountType = "student" | "admission";
export type BillingScheduleStatus = "missing" | "active" | "paused" | "ended";
export type BillingAttentionFlag =
  | "payment_only"
  | "overdue"
  | "due_without_invoice"
  | "missing_schedule"
  | "enforcement_missing";

export type CurrencyBalance = {
  currency: string;
  balanceMinor: number;
};

export type BillingAccountLatestInvoice = {
  invoiceId: number;
  invoiceNumber: string;
  billingPeriod: string;
  status: AdmissionInvoiceStatus;
  dueDate: string;
};

export type BillingAccountSummary = {
  accountType: BillingAccountType;
  accountId: number;
  studentId: number | null;
  admissionId: number | null;
  studentName: string;
  studentCode: string;
  parentName: string;
  schoolId: number;
  schoolName: string;
  lifecycleStatus: string;
  scheduleStatus: BillingScheduleStatus;
  billingDay: number | null;
  effectiveDate: string | null;
  currency: string;
  monthlyAmountMinor: number;
  billableItemCount: number;
  latestInvoice: BillingAccountLatestInvoice | null;
  openInvoiceCount: number;
  overdueInvoiceCount: number;
  outstandingBalances: CurrencyBalance[];
  enforcementState: AdmissionInvoiceQueueItem["enforcementState"];
  attentionFlags: BillingAttentionFlag[];
  scheduleVersion: number | null;
};

export type BillingAccountPage = {
  items: BillingAccountSummary[];
  total: number;
  nextCursor: string | null;
};

export type BillingAccountScheduleItem = {
  groupId: number;
  groupName: string;
  subjectId: number;
  subjectName: string;
  description: string;
  amountMinor: number;
};

export type BillingEnrollmentOption = {
  groupId: number;
  groupName: string;
  subjectId: number;
  subjectName: string;
};

export type BillingAccountDetail = BillingAccountSummary & {
  scheduleItems: BillingAccountScheduleItem[];
  enrollmentOptions: BillingEnrollmentOption[];
  invoices: AdmissionInvoiceQueueItem[];
  linkedTelegramRecipients: number;
  unlinkedTelegramRecipients: number;
};

export type InvoiceLine = {
  lineId: number;
  groupId: number | null;
  subjectId: number | null;
  description: string;
  amountMinor: number;
};

export type InvoiceSettlement = {
  paymentId: number;
  source: "manual" | "payme";
  method: string;
  amountMinor: number;
  currency: string;
  status: string;
  reference: string;
  reason: string;
  paidAt: string;
  reversedAt: string | null;
  reversalReason: string;
};

export type UnifiedInvoiceDetail = AdmissionInvoiceQueueItem & {
  lines: InvoiceLine[];
  payments: InvoiceSettlement[];
  notificationTimeline: BillingNotificationTimelineEntry[];
  voidReason: string;
};

export type BillingNotificationTimelineEntry = {
  stage: "initial" | "twenty_four_hours" | "six_hours" | "held" | "restored";
  scheduledFor: string;
  status: "scheduled" | "pending" | "sent" | "skipped" | "failed" | "cancelled";
  recipientCount: number;
  pendingCount: number;
  sentCount: number;
  skippedCount: number;
  failedCount: number;
};

export type BillingAutomationStatus = {
  generatedAt: string;
  effectiveSchoolIds: number[];
  allSchools: boolean;
  activeBillingProfiles: number;
  currentlyDueBillingProfiles: number;
  openInvoices: number;
  openInvoicesWithoutEnforcement: number;
  linkedTelegramRecipients: number;
  unlinkedTelegramRecipients: number;
  pendingNotificationDeliveries: number;
  failedNotificationDeliveries: number;
  activePaymentOnlyHolds: number;
  pendingFinanceJobs: number;
  workerState: "healthy" | "stalled" | "not_started";
  lastSuccessfulFinanceWorkerAt: string | null;
};

export type BillingProfileItem = {
  itemId: number;
  groupId: number;
  groupName: string;
  subjectId: number;
  subjectName: string;
  description: string;
  amountMinor: number;
  activeFrom: string;
  activeUntil: string | null;
  status: "active" | "cancelled";
  cancelledAt: string | null;
  cancellationReason: string;
};

export type BillingProfile = {
  profileId: number;
  studentId: number;
  schoolId: number;
  billingParentId: number | null;
  billingDay: number;
  currency: string;
  startsOn: string;
  endsOn: string | null;
  status: "active" | "paused" | "ended";
  version: number;
  items: BillingProfileItem[];
};

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

export type SupportTicketStatus = "new" | "in_progress" | "escalated" | "resolved";
export type SupportTicketPriority = "low" | "normal" | "high" | "urgent";
export type SupportTicketSlaState =
  | "on_track"
  | "due_soon"
  | "breached"
  | "paused"
  | "met"
  | "not_applicable";

export type SupportTicketQueueItem = {
  ticketId: number;
  parentId: number;
  studentId: number | null;
  schoolId: number;
  schoolName: string;
  topic: string;
  category: string;
  status: SupportTicketStatus;
  priority: SupportTicketPriority;
  slaState: SupportTicketSlaState;
  requesterName: string;
  assignedStaffId: number | null;
  assignedStaffName: string;
  replyCount: number;
  firstResponseDueAt: string | null;
  resolutionDueAt: string | null;
  firstRespondedAt: string | null;
  isWaitingOnRequester: boolean;
  createdAt: string;
  updatedAt: string;
};

export type SupportTicketMessage = {
  messageId: number;
  authorType: string;
  authorName: string;
  body: string;
  createdAt: string;
};

export type SupportTicketQueue = {
  items: SupportTicketQueueItem[];
  nextCursor: string | null;
  total: number | null;
  actorStaffId: number | null;
};

export type SupportTicketDetail = {
  ticket: SupportTicketQueueItem;
  messages: SupportTicketMessage[];
};

export type CustomerSupportDashboardSchool = {
  schoolId: number;
  schoolName: string;
};

export type CustomerSupportDashboardMetrics = {
  openTickets: number;
  assignedToMe: number;
  unassignedTickets: number;
  escalatedTickets: number;
  slaBreachedTickets: number;
  waitingOnRequesterTickets: number;
  overduePaymentAccounts: number;
  studentsWithoutActiveParentLink: number;
};

export type CustomerSupportDailyTicketFlow = {
  day: string;
  opened: number;
  resolved: number;
};

export type CustomerSupportTicketAgeBucket = {
  bucket: "under_24h" | "one_to_three_days" | "four_to_seven_days" | "eight_plus_days";
  label: string;
  count: number;
};

export type CustomerSupportTicketCategoryVolume = {
  category: string;
  count: number;
};

export type CustomerSupportSchoolWorkload = {
  schoolId: number;
  schoolName: string;
  openTickets: number;
  unassignedTickets: number;
  slaBreachedTickets: number;
};

export type CustomerSupportDashboardTicket = {
  ticketId: number;
  parentId: number | null;
  studentId: number | null;
  studentRowId: number | null;
  studentCode: string;
  title: string;
  requesterName: string;
  schoolId: number;
  schoolName: string;
  category: string;
  status: SupportTicketStatus;
  priority: SupportTicketPriority;
  slaState: SupportTicketSlaState;
  assignedStaffId: number | null;
  assignedStaffName: string;
  createdAt: string;
  updatedAt: string;
  firstResponseDueAt: string | null;
  resolutionDueAt: string | null;
  isWaitingOnRequester: boolean;
};

export type CustomerSupportCurrencyAmount = {
  currency: string;
  amount: number | string;
  accountCount: number;
};

export type CustomerSupportOverduePayment = {
  paymentId: number;
  studentId: number;
  studentRowId: number | null;
  studentCode: string;
  studentName: string;
  schoolId: number;
  schoolName: string;
  dueDate: string;
  amount: number | string;
  currency: string;
  daysOverdue: number;
};

export type CustomerSupportStudentWithoutParent = {
  studentId: number;
  studentRowId: number | null;
  studentCode: string;
  studentName: string;
  schoolId: number;
  schoolName: string;
};

export type CustomerSupportActivity = {
  activityId: string;
  activityType: "ticket" | "payment";
  eventType: string;
  summary: string;
  schoolId: number;
  schoolName: string;
  entityId: number;
  actorStaffId: number | null;
  actorName: string;
  occurredAt: string;
};

export type CustomerSupportDashboard = {
  generatedAt: string;
  periodDays: 7 | 30 | 90;
  periodStartedAt: string;
  periodEndedAt: string;
  effectiveSchoolIds: number[];
  allSchools: boolean;
  availableSchools: CustomerSupportDashboardSchool[];
  metrics: CustomerSupportDashboardMetrics;
  dailyTicketFlow: CustomerSupportDailyTicketFlow[];
  ticketAgeBuckets: CustomerSupportTicketAgeBucket[];
  ticketCategories: CustomerSupportTicketCategoryVolume[];
  schoolWorkload: CustomerSupportSchoolWorkload[];
  actionRequiredTickets: CustomerSupportDashboardTicket[];
  oldestOpenTickets: CustomerSupportDashboardTicket[];
  paymentExceptions: {
    overdueTotals: CustomerSupportCurrencyAmount[];
    dueSoonTotals: CustomerSupportCurrencyAmount[];
    topOverdueAccounts: CustomerSupportOverduePayment[];
  };
  accountExceptions: {
    studentsWithoutActiveParentLink: CustomerSupportStudentWithoutParent[];
  };
  recentActivity: CustomerSupportActivity[];
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

export type TeacherDirectoryItem = {
  teacherId: number;
  fullName: string;
  login: string;
  phone: string;
  telegramUsername: string;
  accountStatus: string;
  schoolIds: number[];
  schoolNames: string[];
  subjectNames: string[];
  assignedGroupCount: number;
};

export type TeacherDirectoryPage = {
  items: TeacherDirectoryItem[];
  nextCursor?: string | null;
  hasMore: boolean;
  total?: number | null;
};

export type TeacherDetail = {
  teacher: TeacherDirectoryItem;
  assignedGroupNames: string[];
};
