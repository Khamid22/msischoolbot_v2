import type { ReactNode } from "react";
import { RoleMobileNav } from "@/shared/ui/RoleMobileNav";
import { RoleSidebar } from "@/shared/ui/RoleSidebar";
import { mobileNavItemsFrom, type RoleNavItem } from "@/shared/ui/roleNav";

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
  children: ReactNode;
}

/**
 * Role-agnostic workspace chrome: desktop sidebar (RoleSidebar), mobile
 * bottom nav (RoleMobileNav), and a safe-area-padded main column whose bottom
 * padding keeps content clear of the fixed mobile nav. Role workspaces supply
 * nav items and labels; no role logic lives here.
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
  workspaceLabel,
  workspaceDescription,
  navLabel,
  mobileNavLabel,
  initialsFallback,
  brandLabel,
  logoutAction,
  maxWidthClass = "max-w-7xl",
  sectionClassName = "gap-5",
  children,
}: RoleWorkspaceShellProps<Key>) {
  const mobileItems = mobileNavItems ?? mobileNavItemsFrom(navItems);

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
        workspaceLabel={workspaceLabel}
        workspaceDescription={workspaceDescription}
        initialsFallback={initialsFallback}
        brandLabel={brandLabel}
        logoutAction={logoutAction}
      />

      <main className="min-h-[var(--tg-viewport-height)] px-3 pb-[calc(var(--app-bottom-inset)+6.25rem)] pt-[calc(var(--app-top-inset)+1rem)] sm:px-5 lg:ml-64 lg:px-8 lg:pb-8 lg:pt-6">
        <section className={`mx-auto flex w-full ${maxWidthClass} flex-col ${sectionClassName}`}>
          {children}
        </section>
      </main>

      <RoleMobileNav
        active={active}
        items={mobileItems}
        label={mobileNavLabel || `${roleLabel} mobile navigation`}
      />
    </div>
  );
}
