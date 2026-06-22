import { lazy } from "react";
import type { ComponentType } from "react";

const CeoHome = lazy(() => import("./CeoHome"));
const CeoGroups = lazy(() => import("./CeoGroups"));
const CeoStudents = lazy(() => import("./CeoStudents"));

// Tab key → CEO-specific component. Tabs not listed here fall back to the default
// admin panel in Admin.tsx, so CEO keeps full access to the standard panels.
export const ceoPanels: Record<string, ComponentType<{ state: any }>> = {
  overview: CeoHome,
  groups: CeoGroups,
  students: CeoStudents,
};

export { CeoHome, CeoGroups, CeoStudents };
