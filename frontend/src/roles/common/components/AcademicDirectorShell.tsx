import {
  BookOpenCheck,
  CalendarDays,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Megaphone,
  ShieldCheck,
  User,
  UsersRound,
} from "lucide-react";
import type { ReactNode } from "react";
import { routes } from "@/shared/lib/routes";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";
import {
  activeNavKeyFromPath,
  mobileNavItemsFrom,
  normalizeNavPathname,
  type RoleNavItem,
} from "@/shared/ui/roleNav";

export type AcademicDirectorNavKey =
  | "overview"
  | "academy"
  | "departments"
  | "timetable"
  | "announcements"
  | "profile";
export type HeadOfDepartmentNavKey =
  | "overview"
  | "academy"
  | "timetable"
  | "announcements"
  | "profile";

export const academicDirectorDesktopNavItems: ReadonlyArray<RoleNavItem<AcademicDirectorNavKey>> = [
  {
    key: "overview",
    label: "Overview",
    href: routes.academicDirectorOverview,
    icon: LayoutDashboard,
  },
  {
    key: "academy",
    label: "Teacher Academy",
    mobileLabel: "Academy",
    href: routes.academicDirectorTeacherAcademy,
    icon: GraduationCap,
  },
  {
    key: "departments",
    label: "Head of Departments",
    href: routes.academicDirectorHeadOfDepartments,
    icon: UsersRound,
  },
  {
    key: "timetable",
    label: "Timetable",
    mobileLabel: "Schedule",
    href: routes.academicDirectorTimetable,
    icon: CalendarDays,
  },
  {
    key: "announcements",
    label: "Announcements",
    mobileLabel: "News",
    href: routes.academicDirectorAnnouncements,
    icon: Megaphone,
  },
  {
    key: "profile",
    label: "Profile",
    href: routes.academicDirectorProfile,
    icon: User,
  },
];

export const academicDirectorMobileNavItems: ReadonlyArray<RoleNavItem<AcademicDirectorNavKey>> =
  mobileNavItemsFrom(academicDirectorDesktopNavItems, ["departments"]);

export const headOfDepartmentDesktopNavItems: ReadonlyArray<RoleNavItem<HeadOfDepartmentNavKey>> = [
  {
    key: "overview",
    label: "Overview",
    href: routes.headOfDepartmentOverview,
    icon: LayoutDashboard,
  },
  {
    key: "academy",
    label: "Teacher Academy",
    mobileLabel: "Academy",
    href: routes.headOfDepartmentTeacherAcademy,
    icon: GraduationCap,
  },
  {
    key: "timetable",
    label: "Timetable",
    mobileLabel: "Schedule",
    href: routes.headOfDepartmentTimetable,
    icon: CalendarDays,
  },
  {
    key: "announcements",
    label: "Announcements",
    mobileLabel: "News",
    href: routes.headOfDepartmentAnnouncements,
    icon: Megaphone,
  },
  {
    key: "profile",
    label: "Profile",
    href: routes.headOfDepartmentProfile,
    icon: User,
  },
];

export const headOfDepartmentMobileNavItems: ReadonlyArray<RoleNavItem<HeadOfDepartmentNavKey>> =
  mobileNavItemsFrom(headOfDepartmentDesktopNavItems);

export function academicDirectorActiveNavFromPath(pathname: string, hash = ""): AcademicDirectorNavKey {
  if (hash === "#academic-director-profile" || normalizeNavPathname(pathname) === routes.academicDirectorProfile) {
    return "profile";
  }
  return activeNavKeyFromPath(academicDirectorDesktopNavItems, pathname, "overview");
}

export function headOfDepartmentActiveNavFromPath(pathname: string, hash = ""): HeadOfDepartmentNavKey {
  if (hash === "#head-of-department-profile" || normalizeNavPathname(pathname) === routes.headOfDepartmentProfile) {
    return "profile";
  }
  return activeNavKeyFromPath(headOfDepartmentDesktopNavItems, pathname, "overview");
}

export function AcademicDirectorPageShell({
  authLogin,
  csrfToken,
  active,
  children,
  maxWidthClass,
  sectionClassName,
}: {
  authLogin?: string;
  csrfToken?: string;
  active: AcademicDirectorNavKey;
  children: ReactNode;
  maxWidthClass?: string;
  sectionClassName?: string;
}) {
  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={routes.academicDirectorOverview}
      navItems={academicDirectorDesktopNavItems}
      mobileNavItems={academicDirectorMobileNavItems}
      roleLabel="Academic Director"
      navLabel="Academic Director navigation"
      mobileNavLabel="Academic Director mobile navigation"
      sectionLabel="Academic"
      workspaceLabel="Full Academic Access"
      workspaceDescription="Groups, teachers, subjects, progress, and Teacher Academy."
      initialsFallback="AD"
      maxWidthClass={maxWidthClass}
      sectionClassName={sectionClassName}
    >
      {children}
    </RoleWorkspaceShell>
  );
}

export function HeadOfDepartmentPageShell({
  authLogin,
  csrfToken,
  active,
  children,
  maxWidthClass,
  sectionClassName,
}: {
  authLogin?: string;
  csrfToken?: string;
  active: HeadOfDepartmentNavKey;
  children: ReactNode;
  maxWidthClass?: string;
  sectionClassName?: string;
}) {
  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={routes.headOfDepartmentOverview}
      navItems={headOfDepartmentDesktopNavItems}
      mobileNavItems={headOfDepartmentMobileNavItems}
      roleLabel="Head of Department"
      navLabel="Head of Department navigation"
      mobileNavLabel="Head of Department mobile navigation"
      sectionLabel="Department"
      workspaceLabel="Subject-scoped access"
      workspaceDescription="Manage Teacher Academy teachers within your subject scope."
      initialsFallback="HD"
      maxWidthClass={maxWidthClass}
      sectionClassName={sectionClassName}
    >
      {children}
    </RoleWorkspaceShell>
  );
}

function TeacherAcademyCta({ href, description }: { href: string; description: string }) {
  return (
    <section className="rounded-2xl border border-primary/20 bg-primary px-5 py-4 text-primary-foreground shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15">
            <BookOpenCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-black">Teacher Academy</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-primary-foreground/80">{description}</p>
          </div>
        </div>
        <a
          href={href}
          className="inline-flex min-h-11 w-full shrink-0 items-center justify-center rounded-xl bg-white px-4 py-2 text-sm font-black text-primary shadow-sm hover:bg-white/90 sm:w-auto"
        >
          Open Teacher Academy
        </a>
      </div>
    </section>
  );
}

export function HeadOfDepartmentTeacherAcademyCta() {
  return (
    <TeacherAcademyCta
      href={routes.headOfDepartmentTeacherAcademy}
      description="Schedule lessons and review assessments for academy teachers in your subject."
    />
  );
}

export function AcademicDirectorTeacherAcademyCta() {
  return (
    <TeacherAcademyCta
      href={routes.academicDirectorTeacherAcademy}
      description="Register academy teachers, assign lessons, schedule observations, and review reports."
    />
  );
}

function RoleProfileSection({
  sectionId,
  heading,
  description,
  csrfToken,
}: {
  sectionId: string;
  heading: string;
  description: string;
  csrfToken?: string;
}) {
  return (
    <section id={sectionId} className="rounded-2xl border border-border bg-surface p-5 shadow-card scroll-mt-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Profile</p>
            <h2 className="mt-1 text-lg font-black text-foreground">{heading}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
          </div>
        </div>
        <form action={routes.logout} method="post" className="shrink-0">
          <input type="hidden" name="csrf_token" value={csrfToken || ""} />
          <button
            type="submit"
            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 py-2 text-sm font-black text-foreground hover:bg-muted md:w-auto"
          >
            <LogOut className="h-4 w-4 text-destructive" />
            Logout
          </button>
        </form>
      </div>
    </section>
  );
}

export function HeadOfDepartmentProfileSection({
  authLogin,
  csrfToken,
}: {
  authLogin?: string;
  csrfToken?: string;
}) {
  return (
    <RoleProfileSection
      sectionId="head-of-department-profile"
      heading={authLogin || "Head of Department"}
      description="Role: Head of Department. Subject-scoped Teacher Academy access for scheduling, assessment, and teacher progress review."
      csrfToken={csrfToken}
    />
  );
}

export function AcademicDirectorProfileSection({
  authLogin,
  csrfToken,
}: {
  authLogin?: string;
  csrfToken?: string;
}) {
  return (
    <RoleProfileSection
      sectionId="academic-director-profile"
      heading={authLogin || "Academic Director"}
      description="Role: Academic Director. Full academic access for groups, teachers, subjects, attendance, progress, and Teacher Academy operations."
      csrfToken={csrfToken}
    />
  );
}
