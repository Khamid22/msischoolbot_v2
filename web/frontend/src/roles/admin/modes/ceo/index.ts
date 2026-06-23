import { lazy } from "react";
import type { ComponentType } from "react";

const CeoHome = lazy(() => import("./CeoHome"));
const CeoGroups = lazy(() => import("./CeoGroups"));
const CeoComplaints = lazy(() => import("./CeoComplaints"));

// Tab key → CEO-specific component. The CEO sidebar is intentionally summary
// focused; only the tabs exposed in adminModeProfiles.ceo can be reached.
export const ceoPanels: Record<string, ComponentType<{ state: any }>> = {
  overview: CeoHome,
  groups: CeoGroups,
  complaints: CeoComplaints,
};

export { CeoHome, CeoGroups, CeoComplaints };
