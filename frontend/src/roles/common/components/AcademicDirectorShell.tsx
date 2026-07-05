import {
  BookOpenCheck,
  GraduationCap,
  Home,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  User,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { routes } from "@/shared/lib/routes";

export type AcademicDirectorNavKey = "home" | "academy" | "profile";

const academicDirectorHome = "/academic-director";
const academicDirectorAcademy = "/academic-director/teacher-academy";
const academicDirectorProfile = "/academic-director#academic-director-profile";

const navItems: Array<{
  key: AcademicDirectorNavKey;
  label: string;
  href: string;
  icon: LucideIcon;
}> = [
  {
    key: "home",
    label: "Dashboard",
    href: academicDirectorHome,
    icon: LayoutDashboard,
  },
  {
    key: "academy",
    label: "Teacher Academy",
    href: academicDirectorAcademy,
    icon: GraduationCap,
  },
  {
    key: "profile",
    label: "Profile",
    href: academicDirectorProfile,
    icon: User,
  },
];

const mobileNavItems: Array<{
  key: AcademicDirectorNavKey;
  label: string;
  href: string;
  icon: LucideIcon;
}> = [
  { key: "home", label: "Home", href: academicDirectorHome, icon: Home },
  { key: "academy", label: "Academy", href: academicDirectorAcademy, icon: GraduationCap },
  { key: "profile", label: "Profile", href: academicDirectorProfile, icon: User },
];

function initialsFromLogin(login: string) {
  const cleaned = login.trim();
  if (!cleaned) return "AD";
  const letters = cleaned.replace(/[^a-z]/gi, "").slice(0, 2).toUpperCase();
  return letters || "AD";
}

export function AcademicDirectorSidebar({
  authLogin,
  csrfToken,
  active = "home",
}: {
  authLogin?: string;
  csrfToken?: string;
  active?: AcademicDirectorNavKey;
}) {
  const login = authLogin || "Academic Director";

  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex">
      <div className="border-b border-white/10 px-3 py-3">
        <a href={academicDirectorHome} className="flex min-w-0 items-center gap-2.5 rounded-lg text-left">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 font-bold text-white ring-1 ring-white/10">
            M
          </div>
          <div className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold text-white">MSI School</span>
            <span className="block truncate text-xs text-slate-300">Academic Director</span>
          </div>
        </a>
        <div className="mt-3">
          <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Workspace
          </span>
          <div className="flex h-9 items-center rounded-lg border border-white/12 bg-white/10 px-2 text-xs font-bold text-white">
            Full Academic Access
          </div>
          <span className="mt-1 block text-[11px] leading-4 text-slate-400">
            Groups, teachers, subjects, progress, and Teacher Academy.
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        <nav className="space-y-2" aria-label="Academic Director navigation">
          <div className="space-y-0.5">
            <p className="px-2 pb-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Academic
            </p>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = active === item.key;
              return (
                <a
                  key={item.key}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] font-semibold transition-all active:scale-[0.98] duration-150 motion-reduce:active:scale-100 ${
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </a>
              );
            })}
          </div>

          <div className="space-y-0.5">
            <p className="px-2 pb-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Departments
            </p>
            <button
              type="button"
              disabled
              className="flex w-full cursor-not-allowed items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] font-semibold text-slate-500"
            >
              <UsersRound className="h-4 w-4 shrink-0" />
              <span className="min-w-0 flex-1">Head of Departments</span>
              <span className="rounded-full border border-white/10 px-1.5 py-0.5 text-[10px] text-slate-400">
                Soon
              </span>
            </button>
          </div>
        </nav>
      </div>

      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
            {initialsFromLogin(login)}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-sm font-medium text-white">{login}</span>
            <span className="block truncate text-xs text-slate-400">Academic Director</span>
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

export function AcademicDirectorMobileNav({
  active = "home",
}: {
  active?: AcademicDirectorNavKey;
}) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface/95 px-3 pt-2 shadow-card backdrop-blur lg:hidden"
      style={{ paddingBottom: "calc(var(--app-bottom-inset) + 0.5rem)" }}
      aria-label="Academic Director mobile navigation"
    >
      <div className="mx-auto grid max-w-md grid-cols-3 gap-1">
        {mobileNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          return (
            <a
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-2 py-1 text-[11px] font-bold transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </a>
          );
        })}
      </div>
    </nav>
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
          href={academicDirectorAcademy}
          className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-xl bg-white px-4 py-2 text-sm font-black text-primary shadow-sm hover:bg-white/90"
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
