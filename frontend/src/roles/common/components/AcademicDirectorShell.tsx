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
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { routes } from "@/shared/lib/routes";

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

type NavItem<Key extends string> = {
  key: Key;
  label: string;
  mobileLabel?: string;
  href: string;
  icon: LucideIcon;
};

export const academicDirectorDesktopNavItems: ReadonlyArray<NavItem<AcademicDirectorNavKey>> = [
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
    href: routes.academicDirectorTimetable,
    icon: CalendarDays,
  },
  {
    key: "announcements",
    label: "Announcements",
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

export const academicDirectorMobileNavItems: ReadonlyArray<NavItem<AcademicDirectorNavKey>> = academicDirectorDesktopNavItems
  .filter((item) => item.key !== "departments")
  .map((item) => ({
    ...item,
    label: item.mobileLabel || item.label,
  }));

export const headOfDepartmentDesktopNavItems: ReadonlyArray<NavItem<HeadOfDepartmentNavKey>> = [
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
    href: routes.headOfDepartmentTimetable,
    icon: CalendarDays,
  },
  {
    key: "announcements",
    label: "Announcements",
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

export const headOfDepartmentMobileNavItems: ReadonlyArray<NavItem<HeadOfDepartmentNavKey>> = headOfDepartmentDesktopNavItems
  .map((item) => ({
    ...item,
    label: item.mobileLabel || item.label,
  }));

function initialsFromLogin(login: string, fallback: string) {
  const cleaned = login.trim();
  if (!cleaned) return fallback;
  const letters = cleaned.replace(/[^a-z]/gi, "").slice(0, 2).toUpperCase();
  return letters || fallback;
}

function normalizePathname(pathname: string) {
  const withoutQuery = String(pathname || "").split("?")[0] || "/";
  return withoutQuery.replace(/\/+$/, "") || "/";
}

export function academicDirectorActiveNavFromPath(pathname: string, hash = ""): AcademicDirectorNavKey {
  const path = normalizePathname(pathname);
  if (hash === "#academic-director-profile" || path === routes.academicDirectorProfile) return "profile";
  if (path === routes.academicDirectorTeacherAcademy) return "academy";
  if (path === routes.academicDirectorHeadOfDepartments) return "departments";
  if (path === routes.academicDirectorTimetable) return "timetable";
  if (path === routes.academicDirectorAnnouncements) return "announcements";
  return "overview";
}

export function headOfDepartmentActiveNavFromPath(pathname: string, hash = ""): HeadOfDepartmentNavKey {
  const path = normalizePathname(pathname);
  if (hash === "#head-of-department-profile" || path === routes.headOfDepartmentProfile) return "profile";
  if (path === routes.headOfDepartmentTeacherAcademy) return "academy";
  if (path === routes.headOfDepartmentTimetable) return "timetable";
  if (path === routes.headOfDepartmentAnnouncements) return "announcements";
  return "overview";
}

function RoleSidebar<Key extends string>({
  authLogin,
  csrfToken,
  active,
  homeHref,
  navItems,
  navLabel,
  roleLabel,
  sectionLabel,
  workspaceLabel,
  workspaceDescription,
  initialsFallback,
}: {
  authLogin?: string;
  csrfToken?: string;
  active: Key;
  homeHref: string;
  navItems: ReadonlyArray<NavItem<Key>>;
  navLabel: string;
  roleLabel: string;
  sectionLabel: string;
  workspaceLabel: string;
  workspaceDescription: string;
  initialsFallback: string;
}) {
  const login = authLogin || roleLabel;

  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex">
      <div className="border-b border-white/10 px-3 py-3">
        <a href={homeHref} className="flex min-w-0 items-center gap-2.5 rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 font-bold text-white ring-1 ring-white/10">
            M
          </div>
          <div className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold text-white">MSI School</span>
            <span className="block truncate text-xs text-slate-300">{roleLabel}</span>
          </div>
        </a>
        <div className="mt-3">
          <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Workspace
          </span>
          <div className="flex h-9 items-center rounded-lg border border-white/12 bg-white/10 px-2 text-xs font-bold text-white">
            {workspaceLabel}
          </div>
          <span className="mt-1 block text-[11px] leading-4 text-slate-400">
            {workspaceDescription}
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        <nav className="space-y-2" aria-label={navLabel}>
          <div className="space-y-0.5">
            <p className="px-2 pb-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {sectionLabel}
            </p>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = active === item.key;
              return (
                <a
                  key={item.key}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] font-semibold transition-all duration-150 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 motion-reduce:active:scale-100 ${
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="min-w-0 truncate">{item.label}</span>
                </a>
              );
            })}
          </div>
        </nav>
      </div>

      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
            {initialsFromLogin(login, initialsFallback)}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-sm font-medium text-white">{login}</span>
            <span className="block truncate text-xs text-slate-400">{roleLabel}</span>
          </div>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}

export function AcademicDirectorSidebar({
  authLogin,
  csrfToken,
  active = "overview",
}: {
  authLogin?: string;
  csrfToken?: string;
  active?: AcademicDirectorNavKey;
}) {
  return (
    <RoleSidebar
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={routes.academicDirectorOverview}
      navItems={academicDirectorDesktopNavItems}
      navLabel="Academic Director navigation"
      roleLabel="Academic Director"
      sectionLabel="Academic"
      workspaceLabel="Full Academic Access"
      workspaceDescription="Groups, teachers, subjects, progress, and Teacher Academy."
      initialsFallback="AD"
    />
  );
}

function MobileBottomNav<Key extends string>({
  active,
  items,
  label,
}: {
  active: Key;
  items: ReadonlyArray<NavItem<Key>>;
  label: string;
}) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface/95 px-2 pt-2 shadow-card backdrop-blur lg:hidden"
      style={{
        paddingBottom: "max(0.5rem, var(--app-bottom-inset))",
        paddingLeft: "calc(var(--app-left-inset) + 0.5rem)",
        paddingRight: "calc(var(--app-right-inset) + 0.5rem)",
      }}
      aria-label={label}
    >
      <div
        className="mx-auto grid max-w-lg gap-1"
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      >
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          return (
            <a
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-1.5 py-1 text-center text-[10.5px] font-bold leading-tight transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="max-w-full truncate">{item.label}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}

export function AcademicDirectorMobileNav({
  active = "overview",
}: {
  active?: AcademicDirectorNavKey;
}) {
  return (
    <MobileBottomNav
      active={active}
      items={academicDirectorMobileNavItems}
      label="Academic Director mobile navigation"
    />
  );
}

export function HeadOfDepartmentSidebar({
  authLogin,
  csrfToken,
  active = "overview",
}: {
  authLogin?: string;
  csrfToken?: string;
  active?: HeadOfDepartmentNavKey;
}) {
  return (
    <RoleSidebar
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      homeHref={routes.headOfDepartmentOverview}
      navItems={headOfDepartmentDesktopNavItems}
      navLabel="Head of Department navigation"
      roleLabel="Head of Department"
      sectionLabel="Department"
      workspaceLabel="Subject-scoped access"
      workspaceDescription="Manage Teacher Academy teachers within your subject scope."
      initialsFallback="HD"
    />
  );
}

export function HeadOfDepartmentMobileNav({
  active = "overview",
}: {
  active?: HeadOfDepartmentNavKey;
}) {
  return (
    <MobileBottomNav
      active={active}
      items={headOfDepartmentMobileNavItems}
      label="Head of Department mobile navigation"
    />
  );
}

function AcademicRolePageShell<Key extends string>({
  authLogin,
  csrfToken,
  active,
  sidebar,
  mobileNav,
  children,
  maxWidthClass = "max-w-7xl",
  sectionClassName = "gap-5",
}: {
  authLogin?: string;
  csrfToken?: string;
  active: Key;
  sidebar: (props: { authLogin?: string; csrfToken?: string; active: Key }) => ReactNode;
  mobileNav: (props: { active: Key }) => ReactNode;
  children: ReactNode;
  maxWidthClass?: string;
  sectionClassName?: string;
}) {
  return (
    <div className="min-h-[var(--tg-viewport-height)] bg-background text-foreground">
      {sidebar({ authLogin, csrfToken, active })}

      <main className="min-h-[var(--tg-viewport-height)] px-3 pb-[calc(var(--app-bottom-inset)+6.25rem)] pt-[calc(var(--app-top-inset)+1rem)] sm:px-5 lg:ml-64 lg:px-8 lg:pb-8 lg:pt-6">
        <section className={`mx-auto flex w-full ${maxWidthClass} flex-col ${sectionClassName}`}>
          {children}
        </section>
      </main>

      {mobileNav({ active })}
    </div>
  );
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
    <AcademicRolePageShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      sidebar={AcademicDirectorSidebar}
      mobileNav={AcademicDirectorMobileNav}
      maxWidthClass={maxWidthClass}
      sectionClassName={sectionClassName}
    >
      {children}
    </AcademicRolePageShell>
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
    <AcademicRolePageShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active={active}
      sidebar={HeadOfDepartmentSidebar}
      mobileNav={HeadOfDepartmentMobileNav}
      maxWidthClass={maxWidthClass}
      sectionClassName={sectionClassName}
    >
      {children}
    </AcademicRolePageShell>
  );
}

export function HeadOfDepartmentTeacherAcademyCta() {
  return (
    <section className="rounded-2xl border border-primary/20 bg-primary px-5 py-4 text-primary-foreground shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15">
            <BookOpenCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-black">Teacher Academy</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-primary-foreground/80">
              Schedule lessons and review assessments for academy teachers in your subject.
            </p>
          </div>
        </div>
        <a
          href={routes.headOfDepartmentTeacherAcademy}
          className="inline-flex min-h-11 w-full shrink-0 items-center justify-center rounded-xl bg-white px-4 py-2 text-sm font-black text-primary shadow-sm hover:bg-white/90 sm:w-auto"
        >
          Open Teacher Academy
        </a>
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
    <section
      id="head-of-department-profile"
      className="rounded-2xl border border-border bg-surface p-5 shadow-card scroll-mt-6"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Profile</p>
            <h2 className="mt-1 text-lg font-black text-foreground">{authLogin || "Head of Department"}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Role: Head of Department. Subject-scoped Teacher Academy access for scheduling,
              assessment, and teacher progress review.
            </p>
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

export function AcademicDirectorTeacherAcademyCta() {
  return (
    <section className="rounded-2xl border border-primary/20 bg-primary px-5 py-4 text-primary-foreground shadow-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15">
            <BookOpenCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-black">Teacher Academy</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-primary-foreground/80">
              Register academy teachers, assign lessons, schedule observations, and review reports.
            </p>
          </div>
        </div>
        <a
          href={routes.academicDirectorTeacherAcademy}
          className="inline-flex min-h-11 w-full shrink-0 items-center justify-center rounded-xl bg-white px-4 py-2 text-sm font-black text-primary shadow-sm hover:bg-white/90 sm:w-auto"
        >
          Open Teacher Academy
        </a>
      </div>
    </section>
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
    <section
      id="academic-director-profile"
      className="rounded-2xl border border-border bg-surface p-5 shadow-card scroll-mt-6"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Profile</p>
            <h2 className="mt-1 text-lg font-black text-foreground">{authLogin || "Academic Director"}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Role: Academic Director. Full academic access for groups, teachers, subjects,
              attendance, progress, and Teacher Academy operations.
            </p>
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
