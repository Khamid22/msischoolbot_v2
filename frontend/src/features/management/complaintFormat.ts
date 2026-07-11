import { asString } from "@/features/managementTypes";

// Shared complaint/ticket formatting. Used by ComplaintsPanel (the Customer
// Support / Admin helpdesk) and CeoComplaints (the read-only CEO overview) so
// the status vocabulary stays identical across roles. Status keys mirror the
// backend: new / in_progress / escalated / resolved.

export type ThreadMessage = {
  id?: number;
  author_role?: string;
  author_login?: string;
  body?: string;
  created_at?: string;
};

const categoryLabels: Record<string, string> = {
  complaint: "Complaint",
  direct_contact: "Direct Contact",
  payment: "Payment",
  teacher: "Teacher",
  lesson_quality: "Lesson Quality",
  schedule: "Schedule",
  attendance: "Attendance",
  technical: "Technical",
  account: "Account",
  other: "Complaint",
};

export function complaintStatus(value: unknown) {
  const status = asString(value).toLowerCase();
  if (status === "in_progress" || status === "escalated" || status === "resolved") return status;
  return "new";
}

export function statusLabel(value: unknown) {
  const status = complaintStatus(value);
  if (status === "in_progress") return "In Progress";
  if (status === "escalated") return "Escalated";
  if (status === "resolved") return "Resolved";
  return "New";
}

export function statusClass(value: unknown) {
  const status = complaintStatus(value);
  if (status === "resolved") return "border-emerald-100 bg-emerald-50 text-emerald-700";
  if (status === "escalated") return "border-rose-100 bg-rose-50 text-rose-700";
  if (status === "in_progress") return "border-sky-100 bg-sky-50 text-sky-700";
  return "border-amber-100 bg-amber-50 text-amber-700";
}

export function formatDate(value: unknown) {
  const raw = asString(value);
  if (!raw) return "";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(parsed));
}

export function formatDateTime(value: unknown) {
  const raw = asString(value);
  if (!raw) return "";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(parsed));
}

export function categoryLabel(value: unknown) {
  const key = asString(value).toLowerCase();
  return categoryLabels[key] || "Complaint";
}

export function complaintTitle(complaint: Record<string, unknown>) {
  return asString(complaint.topic) || categoryLabel(complaint.category);
}

export function parentLabel(complaint: Record<string, unknown>) {
  return asString(complaint.parent_display) || asString(complaint.parent_login) || "Parent";
}

export function lastUpdated(complaint: Record<string, unknown>) {
  return asString(complaint.updated_at) || asString(complaint.created_at);
}

export function matchesQuery(complaint: Record<string, unknown>, query: string) {
  if (!query) return true;
  const haystack = [
    complaintTitle(complaint),
    parentLabel(complaint),
    asString(complaint.student_name),
    asString(complaint.message),
    asString(complaint.assigned_to),
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}
