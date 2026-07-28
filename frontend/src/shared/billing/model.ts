export type BillingAccessMode = "normal" | "payment_only";
export type BillingHoldTarget =
  | "debtor_student"
  | "linked_parent"
  | "household_student";

export type BillingAccessInvoice = {
  invoiceId: number;
  invoiceNumber: string;
  studentId: number;
  studentRowId: number | null;
  studentName: string;
  studentCode: string;
  totalMinor: number;
  paidMinor: number;
  balanceMinor: number;
  currency: string;
  deadlineAt: string;
  targetType: BillingHoldTarget | null;
  canViewInvoice: boolean;
  canPayOnline: boolean;
};

export type BillingAccessStudent = {
  studentId: number;
  studentName: string;
  studentCode: string;
  targetType: BillingHoldTarget;
};

export type BillingAccessStatus = {
  mode: BillingAccessMode;
  countdownDeadlineAt: string | null;
  remainingSeconds: number;
  blockingInvoiceCount: number;
  invoices: BillingAccessInvoice[];
  affectedStudents: BillingAccessStudent[];
};
