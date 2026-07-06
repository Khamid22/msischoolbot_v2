// Pure navigation logic for the teacher cabinet, kept free of React/icon
// imports so it can run under `node --test` like scheduleMath.ts.

export type TeacherTabKey = "home" | "reports" | "timetable" | "career" | "updates" | "profile";

/** Which cabinet the teacher sees: academy trainees vs active teachers. */
export type TeacherCabinetMode = "academy" | "active";

/** Academy teacher bottom navigation: Home, Lessons, Updates, Profile. */
export const teacherMobileTabKeys: readonly TeacherTabKey[] = ["home", "reports", "updates", "profile"];

/** Active teacher bottom navigation: Home, Reports, Timetable, Profile. */
export const activeTeacherMobileTabKeys: readonly TeacherTabKey[] = ["home", "reports", "timetable", "profile"];

export function mobileTabKeysFor(mode: TeacherCabinetMode): readonly TeacherTabKey[] {
  return mode === "active" ? activeTeacherMobileTabKeys : teacherMobileTabKeys;
}

/**
 * Which bottom-nav item should light up for a given active tab.
 * Career maps to Profile (career content lives inside the profile view on
 * mobile). Tabs without a bottom-nav item in the current mode highlight
 * nothing (academy has no Timetable item; active has no Updates item).
 */
export function bottomNavActiveKey(activeTab: TeacherTabKey, mode: TeacherCabinetMode = "academy"): TeacherTabKey | null {
  const keys = mobileTabKeysFor(mode);
  if (keys.includes(activeTab)) return activeTab;
  if (activeTab === "career") return "profile";
  return null;
}
