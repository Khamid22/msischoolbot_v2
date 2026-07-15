import { ArrowLeft, KeyRound, Menu, X } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { isTelegramMiniApp } from "@/shared/lib/telegram";
import { RoleMobileNav } from "@/shared/ui/RoleMobileNav";
import { RoleSidebar, type WorkspaceBackLink } from "@/shared/ui/RoleSidebar";
import { routes } from "@/shared/lib/routes";
import { uiLayers } from "@/shared/ui/layers";
import { mobileNavItemsFrom, type RoleNavItem } from "@/shared/ui/roleNav";
import { initialsFromLogin } from "@/shared/ui/RoleSidebar";
import { useBodyScrollLock } from "@/shared/ui/useBodyScrollLock";

export type MobileNavigationMode = "auto" | "bottom" | "drawer";
export type DesktopSidebarMode = "fixed" | "collapsible";
export type DesktopSidebarInitialState = "expanded" | "collapsed" | "adaptive";

export interface RoleWorkspaceShellProps<Key extends string = string> {
  authLogin?: string;
  csrfToken?: string;
  active: Key;
  homeHref: string;
  /** Desktop sidebar items. Mobile items derive from these unless overridden. */
  navItems: ReadonlyArray<RoleNavItem<Key>>;
  /** Override the derived mobile set, e.g. to drop desktop-only entries. */
  mobileNavItems?: ReadonlyArray<RoleNavItem<Key>>;
  roleLabel: string;
  sectionLabel: string;
  workspaceLabel: string;
  workspaceDescription?: string;
  navLabel?: string;
  mobileNavLabel?: string;
  initialsFallback?: string;
  brandLabel?: string;
  logoutAction?: string;
  maxWidthClass?: string;
  sectionClassName?: string;
  mobileNavigationMode?: MobileNavigationMode;
  desktopSidebarMode?: DesktopSidebarMode;
  desktopSidebarInitialState?: DesktopSidebarInitialState;
  desktopSidebarStorageKey?: string;
  workspaceBackLink?: WorkspaceBackLink;
  profileHref?: string;
  children: ReactNode;
}

function storedSidebarPreference(storageKey?: string) {
  if (!storageKey || typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(storageKey);
    if (value === "collapsed") return true;
    if (value === "expanded") return false;
  } catch {
    return null;
  }
  return null;
}

function initialSidebarCollapsed(initialState: DesktopSidebarInitialState, storageKey?: string) {
  const stored = storedSidebarPreference(storageKey);
  if (stored !== null) return stored;
  if (initialState === "collapsed") return true;
  if (initialState === "expanded") return false;
  return typeof window !== "undefined" ? window.innerWidth < 1600 : false;
}

/**
 * Role-agnostic workspace chrome: desktop sidebar (RoleSidebar), mobile
 * navigation, and a safe-area-padded main column. In auto mode, Telegram Mini
 * App phones keep the fixed bottom nav while normal mobile browsers use a
 * hamburger drawer. Role workspaces supply nav items and labels; no role logic
 * lives here.
 */
export function RoleWorkspaceShell<Key extends string = string>({
  authLogin,
  csrfToken,
  active,
  homeHref,
  navItems,
  mobileNavItems,
  roleLabel,
  sectionLabel,
  navLabel,
  mobileNavLabel,
  initialsFallback,
  brandLabel,
  logoutAction,
  maxWidthClass = "max-w-7xl",
  sectionClassName = "gap-5",
  mobileNavigationMode = "auto",
  desktopSidebarMode = "fixed",
  desktopSidebarInitialState = "expanded",
  desktopSidebarStorageKey,
  workspaceBackLink,
  profileHref,
  children,
}: RoleWorkspaceShellProps<Key>) {
  const mobileItems = mobileNavItems ?? mobileNavItemsFrom(navItems);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const desktopSidebarCollapsible = desktopSidebarMode === "collapsible";
  const [desktopSidebarPreferenceSet, setDesktopSidebarPreferenceSet] = useState(
    () => storedSidebarPreference(desktopSidebarStorageKey) !== null,
  );
  const [desktopSidebarCollapsed, setDesktopSidebarCollapsed] = useState(
    () => desktopSidebarCollapsible && initialSidebarCollapsed(desktopSidebarInitialState, desktopSidebarStorageKey),
  );
  const shouldUseBottomNav = useMemo(() => {
    if (mobileNavigationMode === "bottom") return true;
    if (mobileNavigationMode === "drawer") return false;
    return isTelegramMiniApp();
  }, [mobileNavigationMode]);
  const shouldUseDrawer = !shouldUseBottomNav;
  const login = authLogin || roleLabel;
  const resolvedLogoutAction = logoutAction || routes.logout;

  useBodyScrollLock(drawerOpen);

  useEffect(() => {
    if (!drawerOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDrawerOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [drawerOpen]);

  useEffect(() => {
    if (!shouldUseDrawer && drawerOpen) {
      setDrawerOpen(false);
    }
  }, [drawerOpen, shouldUseDrawer]);

  useEffect(() => {
    if (!desktopSidebarCollapsible || desktopSidebarInitialState !== "adaptive" || desktopSidebarPreferenceSet) return;
    const applyAdaptiveState = () => setDesktopSidebarCollapsed(window.innerWidth < 1600);
    applyAdaptiveState();
    window.addEventListener("resize", applyAdaptiveState);
    return () => window.removeEventListener("resize", applyAdaptiveState);
  }, [desktopSidebarCollapsible, desktopSidebarInitialState, desktopSidebarPreferenceSet]);

  const toggleDesktopSidebar = () => {
    setDesktopSidebarCollapsed((current) => {
      const next = !current;
      if (desktopSidebarStorageKey) {
        try {
          window.localStorage.setItem(desktopSidebarStorageKey, next ? "collapsed" : "expanded");
        } catch {
          // Storage can be unavailable in strict/private browser contexts.
        }
      }
      return next;
    });
    setDesktopSidebarPreferenceSet(true);
  };

  const desktopMarginClass = desktopSidebarCollapsible
    ? desktopSidebarCollapsed
      ? "lg:ml-[4.5rem]"
      : "lg:ml-56"
    : "lg:ml-64";

  return (
    <div className="min-h-[var(--tg-viewport-height)] bg-background text-foreground">
      <RoleSidebar
        authLogin={authLogin}
        csrfToken={csrfToken}
        active={active}
        homeHref={homeHref}
        navItems={navItems}
        navLabel={navLabel || `${roleLabel} navigation`}
        roleLabel={roleLabel}
        sectionLabel={sectionLabel}
        initialsFallback={initialsFallback}
        brandLabel={brandLabel}
        logoutAction={logoutAction}
        collapsible={desktopSidebarCollapsible}
        collapsed={desktopSidebarCollapsed}
        onToggleCollapsed={toggleDesktopSidebar}
        workspaceBackLink={workspaceBackLink}
        profileHref={profileHref}
      />

      <main
        className={`min-h-[var(--tg-viewport-height)] px-3 pt-[calc(var(--app-top-inset)+1rem)] transition-[margin] duration-200 sm:px-5 lg:px-8 lg:pb-8 lg:pt-6 motion-reduce:transition-none ${desktopMarginClass} ${
          shouldUseBottomNav
            ? "pb-[calc(var(--app-bottom-inset)+6.25rem)]"
            : "pb-[calc(var(--app-bottom-inset)+1.25rem)]"
        }`}
      >
        {shouldUseDrawer ? (
          <div className="sticky top-[calc(var(--app-top-inset)+0.5rem)] z-30 mb-3 flex items-center gap-3 rounded-lg border border-border/80 bg-card/95 px-3 py-2 shadow-card backdrop-blur lg:hidden">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-border bg-background text-foreground shadow-sm transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              aria-label={`Open ${roleLabel} navigation`}
              aria-expanded={drawerOpen}
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-black text-foreground">{roleLabel}</p>
            </div>
          </div>
        ) : null}
        <section className={`mx-auto flex w-full ${maxWidthClass} flex-col ${sectionClassName}`}>
          {children}
        </section>
      </main>

      {shouldUseBottomNav ? (
        <RoleMobileNav
          active={active}
          items={mobileItems}
          label={mobileNavLabel || `${roleLabel} mobile navigation`}
        />
      ) : null}

      {shouldUseDrawer ? (
        <div className={`lg:hidden ${drawerOpen ? "" : "pointer-events-none"}`} aria-hidden={!drawerOpen}>
          <button
            type="button"
            className={`fixed inset-0 ${uiLayers.overlay} bg-foreground/60 transition-opacity duration-200 motion-reduce:transition-none ${
              drawerOpen ? "opacity-100" : "opacity-0"
            }`}
            onClick={() => setDrawerOpen(false)}
            aria-label="Close navigation drawer backdrop"
          />
          <aside
            className={`fixed inset-y-0 left-0 ${uiLayers.overlay} flex w-[min(20rem,calc(100vw-2rem))] flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-2xl transition-transform duration-200 motion-reduce:transition-none ${
              drawerOpen ? "translate-x-0" : "-translate-x-full"
            }`}
            style={{
              paddingTop: "var(--app-top-inset)",
              paddingBottom: "var(--app-bottom-inset)",
            }}
            role="dialog"
            aria-modal="true"
            aria-label={mobileNavLabel || `${roleLabel} mobile navigation drawer`}
          >
            <div className="flex items-center justify-between gap-3 border-b border-white/10 px-3 py-3">
              <a
                href={homeHref}
                onClick={() => setDrawerOpen(false)}
                className="flex min-h-11 min-w-0 items-center gap-2.5 rounded-lg text-left transition-colors hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 font-bold text-white ring-1 ring-white/10">
                  {(brandLabel || "MSI School").charAt(0) || "M"}
                </div>
                <div className="min-w-0 leading-tight">
                  <span className="block truncate text-sm font-semibold text-white">{brandLabel || "MSI School"}</span>
                  <span className="block truncate text-xs text-slate-300">{roleLabel}</span>
                </div>
              </a>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-300 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                aria-label="Close navigation drawer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
              <nav className="space-y-2" aria-label={mobileNavLabel || `${roleLabel} mobile navigation`}>
                {workspaceBackLink ? (
                  <a
                    href={workspaceBackLink.href}
                    onClick={() => setDrawerOpen(false)}
                    className="flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold text-slate-300 hover:bg-sidebar-accent hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    <span>{workspaceBackLink.label}</span>
                  </a>
                ) : null}
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
                      onClick={() => setDrawerOpen(false)}
                      aria-current={isActive ? "page" : undefined}
                      className={`relative flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2 pl-4 text-left text-sm font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 motion-reduce:transition-none ${
                        isActive
                          ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      }`}
                    >
                      {isActive ? (
                        <span
                          aria-hidden="true"
                          className="absolute left-1.5 top-1/2 h-5 w-1 -translate-y-1/2 rounded-full bg-white/80"
                        />
                      ) : null}
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="min-w-0 truncate">{item.label}</span>
                      {item.badge ? <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-400 px-1 text-[10px] font-bold text-slate-950" aria-label={`${item.badge} unread`}>{item.badge > 99 ? "99+" : item.badge}</span> : null}
                    </a>
                  );
                })}
              </nav>
            </div>

            <div className="border-t border-white/10 p-3">
              <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
                <a href={profileHref || routes.accountSecurity} onClick={() => setDrawerOpen(false)} className="flex min-h-11 min-w-0 flex-1 items-center gap-2.5 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
                    {initialsFromLogin(login, initialsFallback || "MS")}
                  </div>
                  <div className="min-w-0 flex-1 leading-tight">
                    <span className="block truncate text-sm font-medium text-white">{login}</span>
                    <span className="block truncate text-xs text-slate-400">{roleLabel}</span>
                  </div>
                </a>
                <a
                  href={routes.accountSecurity}
                  onClick={() => setDrawerOpen(false)}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-white/10 text-slate-300 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                  aria-label="Account security"
                >
                  <KeyRound className="h-4 w-4" />
                </a>
                <form action={resolvedLogoutAction} method="post" className="shrink-0">
                  <input type="hidden" name="csrf_token" value={csrfToken || ""} />
                  <button
                    type="submit"
                    className="min-h-11 rounded-lg border border-white/10 px-3 py-2 text-xs font-black text-slate-300 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                  >
                    Logout
                  </button>
                </form>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
