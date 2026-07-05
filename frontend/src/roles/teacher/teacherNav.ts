// Pure navigation logic for the teacher cabinet, kept free of React/icon
// imports so it can run under `node --test` like scheduleMath.ts.

export type TeacherTabKey = "home" | "reports" | "timetable" | "career" | "updates" | "profile";

/** Order of the mobile bottom navigation: Home, Lessons, Updates, Profile. */
export const teacherMobileTabKeys: readonly TeacherTabKey[] = ["home", "reports", "updates", "profile"];

/**
 * Which bottom-nav item should light up for a given active tab.
 * Career maps to Profile (career content lives inside the profile view on
 * mobile); Timetable has no bottom-nav item, so nothing is highlighted.
 */
export function bottomNavActiveKey(activeTab: TeacherTabKey): TeacherTabKey | null {
  if (teacherMobileTabKeys.includes(activeTab)) return activeTab;
  if (activeTab === "career") return "profile";
  return null;
}
