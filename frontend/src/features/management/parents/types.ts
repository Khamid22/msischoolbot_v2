import { asNumber, asString } from "@/features/managementTypes";

export type ParentRow = Record<string, unknown>;

export type LinkFilter = "all" | "linked" | "unlinked";
export type ContactFilter = "all" | "phone" | "no_phone" | "tg" | "no_tg";
export type AccountFilter = "all" | "active" | "disabled" | "invite";
export type TicketFilter = "all" | "open" | "none";

export interface ParentFilters {
  search: string;
  link: LinkFilter;
  contact: ContactFilter;
  account: AccountFilter;
  groupClass: string; // "all" or a class/group name
  tickets: TicketFilter;
}

export const defaultParentFilters: ParentFilters = {
  search: "",
  link: "all",
  contact: "all",
  account: "all",
  groupClass: "all",
  tickets: "all",
};

export function parentChildren(parent: ParentRow | undefined): ParentRow[] {
  return Array.isArray(parent?.children) ? (parent!.children as ParentRow[]) : [];
}

export function parentAccountId(parent: ParentRow | undefined): number {
  const candidates = [
    parent?.parent_account_id,
    parent?.parent_admin_id,
    parent?.parent_id,
    parent?.account_id,
    parent?.id,
  ];

  for (const value of candidates) {
    const direct = asNumber(value);
    if (direct > 0) return direct;

    const text = asString(value);
    const match = text.match(/(?:^|[-_])(\d+)$/);
    if (match) {
      const parsed = Number(match[1]);
      if (Number.isFinite(parsed) && parsed > 0) return parsed;
    }
  }

  return 0;
}

export function isInviteSource(parent: ParentRow): boolean {
  return asString(parent.source) === "invite" || asNumber(parent.id) < 0;
}

export function parentDisplayName(parent: ParentRow): string {
  return (
    asString(parent.display_name) ||
    asString(parent.displayName) ||
    asString(parent.login) ||
    "Parent"
  );
}

export function parentLogin(parent: ParentRow): string {
  return asString(parent.login);
}

/** Login should only be shown when it adds information beyond the display name. */
export function shouldShowLogin(parent: ParentRow): boolean {
  const name = (asString(parent.display_name) || asString(parent.displayName)).trim().toLowerCase();
  const login = parentLogin(parent).trim().toLowerCase();
  if (!login) return false;
  if (!name) return false; // name already falls back to the login
  return name !== login;
}

export function parentPhone(parent: ParentRow): string {
  return asString(parent.phone);
}

export function parentTelegram(parent: ParentRow): string {
  return asString(parent.telegram_username) || asString(parent.telegramUsername);
}

export function telegramConnected(parent: ParentRow): boolean {
  return parent.telegram_user_id != null && asNumber(parent.telegram_user_id) > 0;
}

export function isDisabled(parent: ParentRow): boolean {
  return Boolean(parent.disabled) || asString(parent.status) === "disabled";
}

export function isLinked(parent: ParentRow): boolean {
  return parentChildren(parent).length > 0;
}

export function missingPhone(parent: ParentRow): boolean {
  return !parentPhone(parent);
}

export function missingContact(parent: ParentRow): boolean {
  // No phone AND no Telegram connection = no reliable way to reach the family.
  return missingPhone(parent) && !telegramConnected(parent);
}

export function openTicketCount(parent: ParentRow): number {
  return asNumber(parent.open_ticket_count);
}

export function parentInitials(value: string): string {
  const parts = value.split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "PA"
  );
}

export function childClassName(child: ParentRow): string {
  return asString(child.class_name);
}

export function childGroupLabel(child: ParentRow): string {
  return childClassName(child) || asString(child.school_name);
}

/** All distinct class/group labels across every parent's linked students. */
export function collectGroupOptions(parents: ParentRow[]): string[] {
  const labels = new Set<string>();
  for (const parent of parents) {
    for (const child of parentChildren(parent)) {
      const label = childGroupLabel(child);
      if (label) labels.add(label);
    }
  }
  return Array.from(labels).sort((a, b) => a.localeCompare(b));
}

export function countActiveFilters(filters: ParentFilters): number {
  let count = 0;
  if (filters.link !== "all") count += 1;
  if (filters.contact !== "all") count += 1;
  if (filters.account !== "all") count += 1;
  if (filters.groupClass !== "all") count += 1;
  if (filters.tickets !== "all") count += 1;
  if (filters.search.trim()) count += 1;
  return count;
}

function matchesSearch(parent: ParentRow, query: string): boolean {
  if (!query) return true;
  const haystack: string[] = [
    parentDisplayName(parent),
    parentLogin(parent),
    parentPhone(parent),
    parentTelegram(parent),
    asString(parent.email),
  ];
  for (const child of parentChildren(parent)) {
    haystack.push(asString(child.full_name));
    haystack.push(asString(child.student_code) || asString(child.student_id));
  }
  return haystack.some((value) => value.toLowerCase().includes(query));
}

function matchesContact(parent: ParentRow, contact: ContactFilter): boolean {
  switch (contact) {
    case "phone":
      return !missingPhone(parent);
    case "no_phone":
      return missingPhone(parent);
    case "tg":
      return telegramConnected(parent);
    case "no_tg":
      return !telegramConnected(parent);
    default:
      return true;
  }
}

function matchesAccount(parent: ParentRow, account: AccountFilter): boolean {
  switch (account) {
    case "active":
      return !isDisabled(parent) && !isInviteSource(parent);
    case "disabled":
      return isDisabled(parent);
    case "invite":
      return isInviteSource(parent);
    default:
      return true;
  }
}

export function filterParents(parents: ParentRow[], filters: ParentFilters): ParentRow[] {
  const query = filters.search.trim().toLowerCase();
  return parents.filter((parent) => {
    if (!matchesSearch(parent, query)) return false;

    if (filters.link === "linked" && !isLinked(parent)) return false;
    if (filters.link === "unlinked" && isLinked(parent)) return false;

    if (!matchesContact(parent, filters.contact)) return false;
    if (!matchesAccount(parent, filters.account)) return false;

    if (filters.tickets === "open" && openTicketCount(parent) <= 0) return false;
    if (filters.tickets === "none" && openTicketCount(parent) > 0) return false;

    if (filters.groupClass !== "all") {
      const inGroup = parentChildren(parent).some(
        (child) => childGroupLabel(child) === filters.groupClass,
      );
      if (!inGroup) return false;
    }

    return true;
  });
}
