import { lazy } from "react";
import type { ComponentType } from "react";

const HrHome = lazy(() => import("./HrHome"));
const HrTeachers = lazy(() => import("./HrTeachers"));
const HrCandidates = lazy(() => import("./HrCandidates"));
const HrCareerGrowth = lazy(() => import("./HrCareerGrowth"));

// Tab key → HR Manager component. Tabs not listed here (announcements, resources)
// fall back to the default admin panel.
export const hrPanels: Record<string, ComponentType<{ state: any }>> = {
  overview: HrHome,
  teachers: HrTeachers,
  candidates: HrCandidates,
  career_growth: HrCareerGrowth,
};

export { HrHome, HrTeachers, HrCandidates, HrCareerGrowth };
