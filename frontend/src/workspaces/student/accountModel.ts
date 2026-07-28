export type StudentPayment = {
  paymentId: number;
  invoiceId: number | null;
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

export type StudentPaymentsPayload = { items: StudentPayment[] };

export type StudentInvoiceCheckout = {
  checkoutUrl: string;
  merchantId: string;
  invoiceId: number;
  amountMinor: number;
  currency: string;
  callbackUrl: string;
};

export type StudentTicketMessage = {
  messageId: number;
  authorType: string;
  authorName: string;
  body: string;
  createdAt: string;
};

export type StudentTicket = {
  ticketId: number;
  studentId: number | null;
  studentName: string;
  studentCode: string;
  schoolName: string;
  category: string;
  topic: string;
  status: "new" | "in_progress" | "escalated" | "resolved";
  createdAt: string;
  updatedAt: string;
  resolvedAt: string;
  messages: StudentTicketMessage[];
};

export type StudentTicketsPayload = { items: StudentTicket[] };

export type StudentAccountProps = {
  authLogin?: string;
  csrfToken?: string;
  logoutUrl?: string;
};
