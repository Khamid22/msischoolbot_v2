export type ParentLanguage = "ru" | "uz";
export type ParentNavKey = "home" | "updates" | "children" | "payments" | "support";

export type AcademicIndicator = {
  enrollmentId: number;
  subjectName: string;
  subjectDisplayName: string;
  subjectShort: string;
  groupName: string;
  aap: number;
  attendanceRate: number;
  examPerformance: number;
  totalCoins: number;
  completedLessons: number;
  totalLessons: number;
  completionRate: number;
  updatedAt: string;
};

export type ParentLesson = {
  date: string;
  subjectName: string;
  subjectDisplayName: string;
  groupName: string;
  lessonNumber: string;
  topic: string;
  attendanceStatus: string;
};

export type PaymentSummary = {
  currency: string;
  debtTotal: number;
  dueTotal: number;
  upcomingTotal: number;
  paidTotal: number;
};

export type ParentChild = {
  studentRowId: number;
  studentCode: string;
  fullName: string;
  schoolName: string;
  className: string;
  photoUrl: string;
  subjects: string[];
  academicIndicators: AcademicIndicator[];
  recentLessons: ParentLesson[];
  paymentSummary: PaymentSummary;
  dashboardUrl: string;
};

export type ParentAnnouncement = {
  announcementId: number;
  title: string;
  body: string;
  priority: string;
  isPinned: boolean;
  publishedAt: string;
};

export type ParentPayment = {
  paymentId: number;
  invoiceId: number | null;
  studentRowId: number;
  subject: string;
  month: string;
  amount: number;
  currency: string;
  status: string;
  state: "debt" | "due" | "upcoming" | "paid" | "voided";
  dueDate: string;
  paidAt: string;
  notes: string;
  balance: number;
  canPayOnline: boolean;
};

export type ParentBillingSchedule = {
  cycleId: number;
  studentRowId: number | null;
  studentName: string;
  studentCode: string;
  billingPeriod: string;
  issueAt: string;
  deadlineAt: string;
  expectedMinor: number;
  allocatedMinor: number;
  remainingMinor: number;
  currency: string;
  state: "scheduled" | "review_required" | "invoiced" | "satisfied" | "cancelled";
  invoiceId: number | null;
  invoiceNumber: string;
  reviewRequired: boolean;
};

export type ParentInvoiceCheckout = {
  checkoutUrl: string;
  merchantId: string;
  invoiceId: number;
  amountMinor: number;
  currency: string;
  callbackUrl: string;
};

export type TicketMessage = {
  messageId: number;
  authorType: string;
  authorName: string;
  body: string;
  createdAt: string;
};

export type ParentTicket = {
  ticketId: number;
  parentId: number;
  studentRowId: number;
  studentName: string;
  studentCode: string;
  schoolId: number;
  schoolName: string;
  category: string;
  topic: string;
  status: "new" | "in_progress" | "escalated" | "resolved";
  assignedStaffId: number | null;
  assignedStaffName: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt: string;
  messages: TicketMessage[];
};

export type ParentPreference = {
  parentId: number;
  displayName: string;
  preferredLanguage: ParentLanguage;
};

export type ParentOverview = {
  children: ParentChild[];
  latestUpdates: ParentAnnouncement[];
  paymentSummary: PaymentSummary;
  openTicketCount: number;
  averageAttendanceRate: number | null;
  averageCompletionRate: number | null;
  preference: ParentPreference | null;
};

export type ChildrenPayload = { items: ParentChild[] };
export type UpdatesPayload = { items: ParentAnnouncement[] };
export type PaymentsPayload = {
  items: ParentPayment[];
  summary: PaymentSummary;
  schedules: ParentBillingSchedule[];
};
export type TicketsPayload = { items: ParentTicket[] };

export type ParentBootstrapProps = {
  authLogin?: string;
  csrfToken?: string;
  logoutUrl?: string;
  view?: string;
  selectedStudentId?: number | null;
  selectedTicketId?: number | null;
  preferredLanguage?: string;
};
