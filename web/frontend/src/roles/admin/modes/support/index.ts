import { lazy } from "react";
import type { ComponentType } from "react";

const SupportHome = lazy(() => import("./SupportHome"));
const SupportStudents = lazy(() => import("./SupportStudents"));
const SupportParents = lazy(() => import("./SupportParents"));
const SupportPayments = lazy(() => import("./SupportPayments"));
const SupportComplaints = lazy(() => import("./SupportComplaints"));

// Tab key → Customer Support component (admin mode key "sales"). Tabs not listed
// here (e.g. announcements, groups, chat) fall back to the default admin panel.
export const supportPanels: Record<string, ComponentType<{ state: any }>> = {
  overview: SupportHome,
  students: SupportStudents,
  parents: SupportParents,
  payments: SupportPayments,
  complaints: SupportComplaints,
};

export { SupportHome, SupportStudents, SupportParents, SupportPayments, SupportComplaints };
