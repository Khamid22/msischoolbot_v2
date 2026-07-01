import { lazy } from "react";
import type { ComponentType } from "react";

const SupportStudents = lazy(() => import("./SupportStudents"));
const SupportParents = lazy(() => import("./SupportParents"));
const SupportPayments = lazy(() => import("./SupportPayments"));
const SupportComplaints = lazy(() => import("./SupportComplaints"));

// Tab key → Customer Support component (admin mode key "sales"). The support
// sidebar is intentionally limited to tickets, lookup, parent contact, and payments.
export const supportPanels: Record<string, ComponentType<{ state: any }>> = {
  students: SupportStudents,
  parents: SupportParents,
  payments: SupportPayments,
  complaints: SupportComplaints,
};

export { SupportStudents, SupportParents, SupportPayments, SupportComplaints };
