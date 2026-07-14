import { ArrowLeft, KeyRound, LogOut, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { uiLayers } from "@/shared/ui/layers";
import type { RoleNavItem } from "@/shared/ui/roleNav";

export type WorkspaceBackLink = { href: string; label: string };

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
  initialsFallback?: string;
  brandLabel?: string;
  logoutAction?: string;
  collapsible?: boolean;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  workspaceBackLink?: WorkspaceBackLink;
  profileHref?: string;
}

/** Shared desktop role navigation with an opt-in compact mode. */
export function RoleSidebar<Key extends string = string>({
  authLogin,
  csrfToken,
  active,
  homeHref,
  navItems,
  navLabel,
  roleLabel,
  sectionLabel,
  initialsFallback = "MS",
  brandLabel = "MSI School",
  logoutAction = routes.logout,
  collapsible = false,
  collapsed = false,
  onToggleCollapsed,
  workspaceBackLink,
  profileHref,
}: RoleSidebarProps<Key>) {
  const login = authLogin || roleLabel;
  const compact = collapsible && collapsed;
  const widthClass = collapsible ? (compact ? "w-[4.5rem]" : "w-56") : "w-64";
  const navItemClass = compact ? "justify-center px-0" : "gap-2 px-2.5 pl-3";

  return (
    <aside
      className={`fixed inset-y-0 left-0 ${uiLayers.sidebar} hidden ${widthClass} flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex motion-reduce:transition-none`}
      data-sidebar-collapsed={compact ? "true" : "false"}
    >
      <div className="border-b border-white/10 px-2 py-3">
        <div className={`flex items-center gap-2 ${compact ? "flex-col" : "justify-between"}`}>
          <a
            href={homeHref}
            title={compact ? `${brandLabel} · ${roleLabel}` : undefined}
            aria-label={compact ? `${brandLabel} ${roleLabel}` : undefined}
            className={`flex min-h-11 min-w-0 items-center rounded-lg text-left transition-colors hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${compact ? "h-11 w-11 justify-center" : "flex-1 gap-2.5"}`}
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 font-bold text-white ring-1 ring-white/10">
              {brandLabel.charAt(0) || "M"}
            </div>
            {!compact ? (
              <div className="min-w-0 leading-tight">
                <span className="block truncate text-sm font-semibold text-white">{brandLabel}</span>
                <span className="block truncate text-xs text-slate-300">{roleLabel}</span>
              </div>
            ) : null}
          </a>
          {collapsible ? (
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-300 transition-colors hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
              aria-label={compact ? "Expand recruitment sidebar" : "Collapse recruitment sidebar"}
              aria-expanded={!compact}
              title={compact ? "Expand sidebar" : "Collapse sidebar"}
            >
              {compact ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        {workspaceBackLink ? (
          <a
            href={workspaceBackLink.href}
            title={compact ? workspaceBackLink.label : undefined}
            aria-label={compact ? workspaceBackLink.label : undefined}
            className={`mb-3 flex min-h-11 w-full items-center rounded-lg text-[13px] font-semibold text-slate-300 transition-colors hover:bg-sidebar-accent hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${navItemClass}`}
          >
            <ArrowLeft className="h-4 w-4 shrink-0" />
            {!compact ? <span className="min-w-0 truncate">{workspaceBackLink.label}</span> : null}
          </a>
        ) : null}
        <nav aria-label={navLabel}>
          <div className="space-y-1">
            {!compact ? (
              <p className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {sectionLabel}
              </p>
            ) : null}
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = active === item.key;
              return (
                <a
                  key={item.key}
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  aria-label={compact ? item.label : undefined}
                  title={compact ? item.label : undefined}
                  className={`relative flex min-h-11 w-full items-center rounded-lg text-left text-[13px] font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 motion-reduce:transition-none ${navItemClass} ${
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  }`}
                >
                  {isActive ? (
                    <span
                      aria-hidden="true"
                      className={`absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded-full bg-white/80 ${compact ? "left-0" : "left-1"}`}
                    />
                  ) : null}
                  <Icon className="h-4 w-4 shrink-0" />
                  {!compact ? <span className="min-w-0 truncate">{item.label}</span> : null}
                </a>
              );
            })}
          </div>
        </nav>
      </div>

      <div className="border-t border-white/10 p-2">
        <div className={`flex rounded-lg ${compact ? "flex-col items-center gap-1 py-1" : "items-center gap-2 px-1 py-2"}`}>
          <a
            href={profileHref || routes.accountSecurity}
            className={`flex min-h-11 min-w-0 items-center rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${compact ? "h-11 w-11 justify-center" : "flex-1 gap-2"}`}
            aria-label={compact ? "Recruitment profile" : undefined}
            title={compact ? "Recruitment profile" : undefined}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
              {initialsFromLogin(login, initialsFallback)}
            </div>
            {!compact ? (
              <div className="min-w-0 flex-1 leading-tight">
                <span className="block truncate text-sm font-medium text-white">{login}</span>
                <span className="block truncate text-xs text-slate-400">{roleLabel}</span>
              </div>
            ) : null}
          </a>
          <a
            href={routes.accountSecurity}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
            aria-label="Account security"
            title="Account security"
          >
            <KeyRound className="h-4 w-4" />
          </a>
          <form action={logoutAction} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
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
