import type { LucideIcon } from "lucide-react";

/**
 * Navigation item consumed by RoleSidebar / RoleMobileNav / RoleWorkspaceShell.
 * Role workspaces declare their own item arrays and pass them in — the shell
 * components hold no role-specific logic.
 */
export type RoleNavItem<Key extends string = string> = {
  key: Key;
  /** Desktop sidebar label, e.g. "Teacher Academy". */
  label: string;
  /** Short label for the mobile bottom nav, e.g. "Academy". Falls back to `label`. */
  mobileLabel?: string;
  href: string;
  icon: LucideIcon;
  /** Optional unread/work-item count rendered as a compact accessible badge. */
  badge?: number;
};

/**
 * Derive mobile bottom-nav items from the desktop set: swap in the short
 * mobile labels and optionally drop items that don't fit on a phone.
 * Generic over any item shape with key/label so icon-free nav configs
 * (testable under node) and full RoleNavItems both work.
 */
export function mobileNavItemsFrom<T extends { key: string; label: string; mobileLabel?: string }>(
  items: ReadonlyArray<T>,
  excludeKeys: ReadonlyArray<T["key"]> = [],
): T[] {
  return items
    .filter((item) => !excludeKeys.includes(item.key))
    .map((item) => ({ ...item, label: item.mobileLabel || item.label }));
}

export function normalizeNavPathname(pathname: string): string {
  const withoutQuery = String(pathname || "").split("?")[0] || "/";
  return withoutQuery.replace(/\/+$/, "") || "/";
}

/**
 * Resolve which nav item is active for the current URL. Longest href wins so
 * "/role/sub" matches its own item rather than the "/role" overview.
 */
export function activeNavKeyFromPath<Key extends string>(
  items: ReadonlyArray<{ key: Key; href: string }>,
  pathname: string,
  fallback: Key,
): Key {
  const path = normalizeNavPathname(pathname);
  const match = [...items]
    .sort((a, b) => b.href.length - a.href.length)
    .find((item) => normalizeNavPathname(item.href) === path);
  return match ? match.key : fallback;
}
