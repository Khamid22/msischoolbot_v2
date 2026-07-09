// Pure navigation config for the Academic Director and Head of Department
// workspaces, kept free of React/icon imports so it can run under
// `node --test` like teacherNav.ts. AcademicDirectorShell.tsx attaches the
// icons and feeds these into RoleWorkspaceShell.
import { routes } from "../../../shared/lib/routes.ts";
import {
  activeNavKeyFromPath,
  mobileNavItemsFrom,
  normalizeNavPathname,
} from "../../../shared/ui/roleNav.ts";

export type AcademicDirectorNavKey =
  | "overview"
  | "academy"
  | "departments"
  | "groups"
  | "subjects"
  | "timetable"
  | "announcements"
  | "profile";
export type HeadOfDepartmentNavKey =
  | "overview"
  | "academy"
  | "timetable"
  | "announcements"
  | "profile";

export type AcademicNavConfigItem<Key extends string> = {
  key: Key;
  label: string;
  mobileLabel?: string;
  href: string;
};

export const academicDirectorNavConfig: ReadonlyArray<AcademicNavConfigItem<AcademicDirectorNavKey>> = [
  { key: "overview", label: "Overview", href: routes.academicDirectorOverview },
  { key: "academy", label: "Teacher Academy", mobileLabel: "Academy", href: routes.academicDirectorTeacherAcademy },
  { key: "departments", label: "Head of Departments", href: routes.academicDirectorHeadOfDepartments },
  { key: "groups", label: "Groups", href: routes.academicDirectorGroups },
  { key: "subjects", label: "Subjects", href: routes.academicDirectorSubjects },
  { key: "timetable", label: "Academic Timetable", mobileLabel: "Schedule", href: routes.academicDirectorTimetable },
  { key: "announcements", label: "Announcements", mobileLabel: "News", href: routes.academicDirectorAnnouncements },
  { key: "profile", label: "Profile", href: routes.academicDirectorProfile },
];

/** Phone set: Overview, Academy, Groups, Schedule, Profile (wide admin-only items are desktop-first). */
export const academicDirectorMobileNavConfig: ReadonlyArray<AcademicNavConfigItem<AcademicDirectorNavKey>> =
  mobileNavItemsFrom(academicDirectorNavConfig, ["departments", "subjects", "announcements"]);

export const headOfDepartmentNavConfig: ReadonlyArray<AcademicNavConfigItem<HeadOfDepartmentNavKey>> = [
  { key: "overview", label: "Overview", href: routes.headOfDepartmentOverview },
  { key: "academy", label: "Teacher Academy", mobileLabel: "Academy", href: routes.headOfDepartmentTeacherAcademy },
  { key: "timetable", label: "Timetable", mobileLabel: "Schedule", href: routes.headOfDepartmentTimetable },
  { key: "announcements", label: "Announcements", mobileLabel: "News", href: routes.headOfDepartmentAnnouncements },
  { key: "profile", label: "Profile", href: routes.headOfDepartmentProfile },
];

export const headOfDepartmentMobileNavConfig: ReadonlyArray<AcademicNavConfigItem<HeadOfDepartmentNavKey>> =
  mobileNavItemsFrom(headOfDepartmentNavConfig);

export function academicDirectorActiveNavFromPath(pathname: string, _hash = ""): AcademicDirectorNavKey {
  if (normalizeNavPathname(pathname) === routes.academicDirectorProfile) {
    return "profile";
  }
  return activeNavKeyFromPath(academicDirectorNavConfig, pathname, "overview");
}

export function headOfDepartmentActiveNavFromPath(pathname: string, _hash = ""): HeadOfDepartmentNavKey {
  if (normalizeNavPathname(pathname) === routes.headOfDepartmentProfile) {
    return "profile";
  }
  return activeNavKeyFromPath(headOfDepartmentNavConfig, pathname, "overview");
}
