import { ArrowLeft, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState, type FocusEvent } from "react";
import { routes } from "@/shared/lib/routes";
import { uiLayers } from "@/shared/ui/layers";
import type { RoleNavItem } from "@/shared/ui/roleNav";

export type WorkspaceBackLink = { href: string; label: string };
const SIDEBAR_COLLAPSE_DELAY_MS = 140;

export function initialsFromLogin(login: string, fallback: string) {
  const cleaned = login.trim();
  if (!cleaned) return fallback;
  const letters = cleaned.replace(/[^a-z]/gi, "").slice(0, 2).toUpperCase();
  return letters || fallback;
}

export interface RoleSidebarProps<Key extends string = string> {
  authLogin?: string;
  active: Key;
  homeHref: string;
  navItems: ReadonlyArray<RoleNavItem<Key>>;
  navLabel: string;
  roleLabel: string;
  sectionLabel: string;
  initialsFallback?: string;
  brandLabel?: string;
  collapsible?: boolean;
  workspaceBackLink?: WorkspaceBackLink;
  profileHref?: string;
}

/** Shared desktop role navigation with an opt-in hover/focus compact mode. */
export function RoleSidebar<Key extends string = string>({
  authLogin,
  active,
  homeHref,
  navItems,
  navLabel,
  roleLabel,
  sectionLabel,
  initialsFallback = "MS",
  brandLabel = "MSI School",
  collapsible = false,
  workspaceBackLink,
  profileHref,
}: RoleSidebarProps<Key>) {
  const login = authLogin || roleLabel;
  const [hoverCapable, setHoverCapable] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  });
  const [pointerInside, setPointerInside] = useState(false);
  const [focusInside, setFocusInside] = useState(false);
  const collapseTimerRef = useRef<number | null>(null);
  const compact = collapsible && hoverCapable && !pointerInside && !focusInside;
  const widthClass = collapsible
    ? compact
      ? "w-[var(--workspace-sidebar-compact-width)]"
      : "w-[var(--workspace-sidebar-collapsible-width)]"
    : "w-[var(--workspace-sidebar-width)]";
  const navItemClass = compact ? "justify-center px-0" : "gap-2 px-2.5 pl-3";
  const activeGroupKey = navItems.find((item) => item.key === active && item.children?.length)?.key ?? null;
  const [openGroupKey, setOpenGroupKey] = useState<Key | null>(activeGroupKey);

  useEffect(() => {
    setOpenGroupKey(activeGroupKey);
  }, [activeGroupKey]);

  useEffect(() => {
    if (!collapsible) return;
    const hoverMedia = window.matchMedia("(hover: hover) and (pointer: fine)");
    const updateHoverCapability = () => setHoverCapable(hoverMedia.matches);
    updateHoverCapability();
    hoverMedia.addEventListener("change", updateHoverCapability);
    return () => hoverMedia.removeEventListener("change", updateHoverCapability);
  }, [collapsible]);

  useEffect(() => () => {
    if (collapseTimerRef.current !== null) {
      window.clearTimeout(collapseTimerRef.current);
    }
  }, []);

  const cancelScheduledCollapse = () => {
    if (collapseTimerRef.current === null) return;
    window.clearTimeout(collapseTimerRef.current);
    collapseTimerRef.current = null;
  };

  const handlePointerEnter = () => {
    cancelScheduledCollapse();
    setPointerInside(true);
  };

  const handlePointerLeave = () => {
    cancelScheduledCollapse();
    collapseTimerRef.current = window.setTimeout(() => {
      setPointerInside(false);
      collapseTimerRef.current = null;
    }, SIDEBAR_COLLAPSE_DELAY_MS);
  };

  const handleBlurCapture = (event: FocusEvent<HTMLElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setFocusInside(false);
    }
  };

  return (
    <aside
      className={`fixed inset-y-0 left-0 ${uiLayers.sidebar} hidden ${widthClass} flex-col overflow-x-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width,box-shadow] duration-200 ease-out lg:flex motion-reduce:transition-none ${
        collapsible && !compact ? "shadow-2xl" : ""
      }`}
      data-sidebar-collapsed={compact ? "true" : "false"}
      onPointerEnter={collapsible ? handlePointerEnter : undefined}
      onPointerLeave={collapsible ? handlePointerLeave : undefined}
      onFocusCapture={collapsible ? () => setFocusInside(true) : undefined}
      onBlurCapture={collapsible ? handleBlurCapture : undefined}
    >
      <div className="border-b border-white/10 px-2 py-3">
        <div className="flex items-center gap-2">
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
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        {workspaceBackLink ? (
          <a
            href={workspaceBackLink.href}
            title={compact ? workspaceBackLink.label : undefined}
            aria-label={compact ? workspaceBackLink.label : undefined}
            className={`mb-3 flex min-h-11 w-full items-center rounded-lg text-[0.8125rem] font-semibold text-slate-300 transition-colors hover:bg-sidebar-accent hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${navItemClass}`}
          >
            <ArrowLeft className="h-4 w-4 shrink-0" />
            {!compact ? <span className="min-w-0 truncate">{workspaceBackLink.label}</span> : null}
          </a>
        ) : null}
        <nav aria-label={navLabel}>
          <div className="space-y-1">
            {!compact ? (
              <p className="px-2 pb-1 text-[0.625rem] font-bold uppercase tracking-wider text-slate-400">
                {sectionLabel}
              </p>
            ) : null}
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = active === item.key;
              const childIsActive = Boolean(item.children?.some((child) => child.active));
              const hasChildren = Boolean(item.children?.length);
              const groupIsOpen = hasChildren && openGroupKey === item.key && !compact;
              const childGroupId = `role-nav-${String(item.key)}-children`;
              const itemClasses = `relative flex min-h-11 w-full items-center rounded-lg text-left text-[0.8125rem] font-semibold transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 motion-reduce:transition-none ${navItemClass} ${
                isActive || groupIsOpen
                  ? childIsActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              }`;
              return (
                <div key={item.key}>
                  {hasChildren && !compact ? (
                    <button
                      type="button"
                      onClick={() => setOpenGroupKey((current) => current === item.key ? null : item.key)}
                      aria-expanded={groupIsOpen}
                      aria-controls={childGroupId}
                      className={itemClasses}
                    >
                      {isActive ? <span aria-hidden="true" className="absolute left-1 top-1/2 h-4 w-1 -translate-y-1/2 rounded-full bg-white/80" /> : null}
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="min-w-0 truncate">{item.label}</span>
                      {item.badge ? <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-400 px-1 text-[0.625rem] font-bold text-slate-950" aria-label={`${item.badge} unread`}>{item.badge > 99 ? "99+" : item.badge}</span> : null}
                      <ChevronDown aria-hidden="true" className={`h-4 w-4 shrink-0 transition-transform duration-200 motion-reduce:transition-none ${groupIsOpen ? "rotate-180" : ""}`} />
                    </button>
                  ) : (
                    <a
                      href={item.href}
                      onClick={() => setOpenGroupKey(null)}
                      aria-current={isActive ? "page" : undefined}
                      aria-label={compact ? item.label : undefined}
                      title={compact ? item.label : undefined}
                      className={itemClasses}
                    >
                      {isActive ? <span aria-hidden="true" className={`absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded-full bg-white/80 ${compact ? "left-0" : "left-1"}`} /> : null}
                      <Icon className="h-4 w-4 shrink-0" />
                      {!compact ? <span className="min-w-0 truncate">{item.label}</span> : null}
                      {item.badge ? <span className={`${compact ? "absolute right-0.5 top-0.5" : "ml-auto"} flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-400 px-1 text-[0.625rem] font-bold text-slate-950`} aria-label={`${item.badge} unread`}>{item.badge > 99 ? "99+" : item.badge}</span> : null}
                    </a>
                  )}
                  {!compact && item.children?.length ? (
                    <div
                      id={childGroupId}
                      className={`grid transition-[grid-template-rows,opacity,margin] duration-200 ease-out motion-reduce:transition-none ${groupIsOpen ? "mt-1 grid-rows-[1fr] opacity-100" : "pointer-events-none mt-0 grid-rows-[0fr] opacity-0"}`}
                      aria-hidden={!groupIsOpen}
                    >
                      <div className="overflow-hidden">
                        <div role="group" className="ml-5 space-y-1 border-l border-white/15 pl-2" aria-label={`${item.label} pages`}>
                          {item.children.map((child) => {
                            const ChildIcon = child.icon;
                            return (
                              <a
                                key={child.key}
                                href={child.href}
                                tabIndex={groupIsOpen ? 0 : -1}
                                aria-current={child.active ? "page" : undefined}
                                className={`flex min-h-11 items-center gap-2 rounded-lg px-2.5 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${child.active ? "bg-sidebar-primary text-sidebar-primary-foreground" : "text-slate-300 hover:bg-sidebar-accent hover:text-white"}`}
                              >
                                {ChildIcon ? <ChildIcon className="h-3.5 w-3.5 shrink-0" /> : null}
                                <span className="min-w-0 truncate">{child.label}</span>
                                {child.badge ? <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-400 px-1 text-[0.625rem] font-bold text-slate-950" aria-label={`${child.badge} unread`}>{child.badge > 99 ? "99+" : child.badge}</span> : null}
                              </a>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </nav>
      </div>

      <div className="border-t border-white/10 p-2">
        <div className={`flex rounded-lg ${compact ? "items-center justify-center py-1" : "items-center px-1 py-2"}`}>
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
        </div>
      </div>
    </aside>
  );
}
