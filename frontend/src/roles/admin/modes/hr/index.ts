import { lazy } from "react";
import type { ComponentType } from "react";

const HrTeachers = lazy(() => import("./HrTeachers"));
const HrCandidates = lazy(() => import("./HrCandidates"));

// Tab key → HR Manager component. HR is limited to hiring and teacher records;
// academic career-growth decisions live under Academic Director.
export const hrPanels: Record<string, ComponentType<{ state: any }>> = {
  teachers: HrTeachers,
  candidates: HrCandidates,
};

export { HrTeachers, HrCandidates };
