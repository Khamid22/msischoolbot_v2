import { LogOut } from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { uiLayers } from "@/shared/ui/layers";
import type { RoleNavItem } from "@/shared/ui/roleNav";

export function initialsFromLogin(login: string, fallback: string) {
  const cleaned = login.trim();
  if (!cleaned) return fallback;
  const letters = cleaned.replace(/[^a-z]/gi, "").slice(0, 2).toUpperCase();
  return letters || fallback;
}

export interface RoleSidebarProps<Key extends string = string> {
  authLogin?: string;
  csrfToken?: string;
  active: Key;
  homeHref: string;
  navItems: ReadonlyArray<RoleNavItem<Key>>;
  navLabel: string;
  roleLabel: string;
  sectionLabel: string;
  workspaceLabel: string;
  workspaceDescription?: string;
  initialsFallback?: string;
  brandLabel?: string;
  logoutAction?: string;
}

/**
 * Desktop workspace sidebar shared by every role: dark navy panel, fixed
 * 16rem width, workspace summary, real anchor nav links with active state,
 * and an account footer with logout. Hidden below the `lg` breakpoint —
 * pair with RoleMobileNav.
 */
export function RoleSidebar<Key extends string = string>({
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
  initialsFallback = "MS",
  brandLabel = "MSI School",
  logoutAction = routes.logout,
}: RoleSidebarProps<Key>) {
  const login = authLogin || roleLabel;

  return (
    <aside
      className={`fixed inset-y-0 left-0 ${uiLayers.sidebar} hidden w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex`}
    >
      <div className="border-b border-white/10 px-3 py-3">
        <a
          href={homeHref}
          className="flex min-w-0 items-center gap-2.5 rounded-lg text-left transition-colors hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 font-bold text-white ring-1 ring-white/10">
            {brandLabel.charAt(0) || "M"}
          </div>
          <div className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold text-white">{brandLabel}</span>
            <span className="block truncate text-xs text-slate-300">{roleLabel}</span>
          </div>
        </a>
        <div className="mt-3">
          <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Workspace
          </span>
          <div className="flex min-h-9 items-center rounded-lg border border-white/12 bg-white/10 px-2 py-1.5 text-xs font-bold leading-4 text-white">
            {workspaceLabel}
          </div>
          {workspaceDescription ? (
            <span className="mt-1 block text-[11px] leading-4 text-slate-400">
              {workspaceDescription}
            </span>
          ) : null}
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
                  className={`relative flex min-h-10 w-full items-center gap-2.5 rounded-lg px-2.5 py-2 pl-3 text-left text-[13px] font-semibold transition-all duration-150 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 motion-reduce:transition-none motion-reduce:active:scale-100 ${
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  }`}
                >
                  {isActive ? (
                    <span
                      aria-hidden="true"
                      className="absolute left-1 top-1/2 h-5 w-1 -translate-y-1/2 rounded-full bg-white/80"
                    />
                  ) : null}
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
          <form action={logoutAction} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
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
