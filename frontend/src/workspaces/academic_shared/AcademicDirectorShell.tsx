import {
  BookOpenCheck,
  BookMarked,
  BriefcaseBusiness,
  CalendarDays,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Megaphone,
  ShieldCheck,
  User,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { routes } from "@/shared/lib/routes";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";
import type { RoleNavItem } from "@/shared/ui/roleNav";
import { useRecruitmentUnreadCount } from "@/features/recruitment/RecruitmentNotifications";
import { BrowserReminderPreferencesCard } from "@/features/recruitment/BrowserRecruitmentReminders";
import {
  academicDirectorMobileNavConfig,
  academicDirectorNavConfig,
  headOfDepartmentMobileNavConfig,
  headOfDepartmentNavConfig,
  type AcademicDirectorNavKey,
  type HeadOfDepartmentNavKey,
} from "./academicNav";

export {
  academicDirectorActiveNavFromPath,
  headOfDepartmentActiveNavFromPath,
  type AcademicDirectorNavKey,
  type HeadOfDepartmentNavKey,
} from "./academicNav";

const academicDirectorNavIcons: Record<AcademicDirectorNavKey, LucideIcon> = {
  overview: LayoutDashboard,
  academy: GraduationCap,
  departments: UsersRound,
  groups: UsersRound,
  subjects: BookMarked,
  timetable: CalendarDays,
  announcements: Megaphone,
  recruitment: BriefcaseBusiness,
  profile: User,
};

const headOfDepartmentNavIcons: Record<HeadOfDepartmentNavKey, LucideIcon> = {
  overview: LayoutDashboard,
  academy: GraduationCap,
  timetable: CalendarDays,
  announcements: Megaphone,
  recruitment: BriefcaseBusiness,
  profile: User,
};

function withIcons<Key extends string>(
  config: ReadonlyArray<{ key: Key; label: string; mobileLabel?: string; href: string }>,
  icons: Record<Key, LucideIcon>,
): ReadonlyArray<RoleNavItem<Key>> {
  return config.map((item) => ({ ...item, icon: icons[item.key] }));
}

export const academicDirectorDesktopNavItems: ReadonlyArray<RoleNavItem<AcademicDirectorNavKey>> =
  withIcons(academicDirectorNavConfig, academicDirectorNavIcons);

export const academicDirectorMobileNavItems: ReadonlyArray<RoleNavItem<AcademicDirectorNavKey>> =
  withIcons(academicDirectorMobileNavConfig, academicDirectorNavIcons);

export const headOfDepartmentDesktopNavItems: ReadonlyArray<RoleNavItem<HeadOfDepartmentNavKey>> =
  withIcons(headOfDepartmentNavConfig, headOfDepartmentNavIcons);

export const headOfDepartmentMobileNavItems: ReadonlyArray<RoleNavItem<HeadOfDepartmentNavKey>> =
  withIcons(headOfDepartmentMobileNavConfig, headOfDepartmentNavIcons);

export type AcademicRecruitmentView = "candidates" | "schedule" | "candidate";

function academicDirectorRecruitmentChildren(view?: AcademicRecruitmentView) {
  return [
    {
      key: "recruitment-candidates",
      label: "Candidates",
      href: `${routes.academicDirectorRecruitment}/candidates`,
      icon: UsersRound,
      active: view === "candidates" || view === "candidate",
    },
    {
      key: "recruitment-schedule",
      label: "Schedule",
      href: `${routes.academicDirectorRecruitment}/schedule`,
      icon: CalendarDays,
      active: view === "schedule",
    },
  ];
}

function headOfDepartmentRecruitmentChildren(view?: AcademicRecruitmentView) {
  return [
    {
      key: "recruitment-candidates",
      label: "Candidates",
      href: `${routes.headOfDepartmentRecruitment}/candidates`,
      icon: UsersRound,
      active: view === "candidates" || view === "candidate",
    },
    {
      key: "recruitment-schedule",
      label: "Schedule",
      href: `${routes.headOfDepartmentRecruitment}/schedule`,
      icon: CalendarDays,
      active: view === "schedule",
    },
  ];
}

export function AcademicDirectorPageShell({
  authLogin,
  csrfToken,
  active,
  children,
  maxWidthClass,
  sectionClassName,
  recruitmentView,
}: {
  authLogin?: string;
  csrfToken?: string;
  active: AcademicDirectorNavKey;
  children: ReactNode;
  maxWidthClass?: string;
  sectionClassName?: string;
  recruitmentView?: AcademicRecruitmentView;
}) {
  const unread = useRecruitmentUnreadCount();
  const desktopItems = academicDirectorDesktopNavItems.map((item) => item.key === "recruitment" ? {
    ...item,
    badge: unread,
    children: academicDirectorRecruitmentChildren(recruitmentView),
  } : item);
  const mobileItems = academicDirectorMobileNavItems.map((item) => item.key === "recruitment" ? { ...item, badge: unread } : item);
  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={routes.academicDirectorOverview}
      navItems={desktopItems}
      mobileNavItems={mobileItems}
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
  recruitmentView,
}: {
  authLogin?: string;
  csrfToken?: string;
  active: HeadOfDepartmentNavKey;
  children: ReactNode;
  maxWidthClass?: string;
  sectionClassName?: string;
  recruitmentView?: AcademicRecruitmentView;
}) {
  const unread = useRecruitmentUnreadCount();
  const desktopItems = headOfDepartmentDesktopNavItems.map((item) => item.key === "recruitment" ? {
    ...item,
    badge: unread,
    children: headOfDepartmentRecruitmentChildren(recruitmentView),
  } : item);
  const mobileItems = headOfDepartmentMobileNavItems.map((item) => item.key === "recruitment" ? { ...item, badge: unread } : item);
  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={routes.headOfDepartmentOverview}
      navItems={desktopItems}
      mobileNavItems={mobileItems}
      roleLabel="Head of Departments"
      navLabel="Head of Departments navigation"
      mobileNavLabel="Head of Departments mobile navigation"
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
      description="Register academy teachers, select lessons, schedule observations, and review reports."
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
    <div className="space-y-4">
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
    <BrowserReminderPreferencesCard />
    </div>
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
      heading={authLogin || "Head of Departments"}
      description="Role: Head of Departments. Subject-scoped Teacher Academy access for scheduling, assessment, and teacher progress review."
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
