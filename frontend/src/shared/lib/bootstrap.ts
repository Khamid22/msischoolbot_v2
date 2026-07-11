export type ReactPageName =
  | "login"
  | "student-home"
  | "student-dashboard"
  | "student-chat"
  | "student-resources"
  | "student-rating"
  | "student-aap"
  | "student-ar"
  | "student-office-hours"
  | "internal-operations-home"
  | "internal-edit-student"
  | "parent-home"
  | "ceo-home"
  | "hr-manager-home"
  | "customer-support-home"
  | "academic-director-home"
  | "academic-director-academy"
  | "academic-director-head-of-departments"
  | "academic-director-groups"
  | "academic-director-subjects"
  | "academic-director-timetable"
  | "academic-director-announcements"
  | "head-of-departments-home"
  | "head-of-departments-academy"
  | "head-of-departments-timetable"
  | "head-of-departments-announcements"
  | "account-security"
  | "unauthorized"
  | "student-not-found";

export interface ReactBootstrap {
  page: ReactPageName;
  props: Record<string, unknown>;
}

const REACT_PAGES = new Set<ReactPageName>([
  "login",
  "student-home",
  "student-dashboard",
  "student-chat",
  "student-resources",
  "student-rating",
  "student-aap",
  "student-ar",
  "student-office-hours",
  "internal-operations-home",
  "internal-edit-student",
  "parent-home",
  "ceo-home",
  "hr-manager-home",
  "customer-support-home",
  "academic-director-home",
  "academic-director-academy",
  "academic-director-head-of-departments",
  "academic-director-groups",
  "academic-director-subjects",
  "academic-director-timetable",
  "academic-director-announcements",
  "head-of-departments-home",
  "head-of-departments-academy",
  "head-of-departments-timetable",
  "head-of-departments-announcements",
  "account-security",
  "unauthorized",
  "student-not-found",
]);

function inferPageFromPath(pathname: string): ReactPageName | null {
  if (/^\/dashboard\/\d+\/chat\/?$/.test(pathname)) {
    return "student-chat";
  }
  if (/^\/dashboard\/\d+\/ar-lessons\/?$/.test(pathname)) {
    return "student-ar";
  }
  if (/^\/dashboard\/\d+\/aap-lessons\/?$/.test(pathname)) {
    return "student-aap";
  }
  if (/^\/dashboard\/\d+\/rating-board\/?$/.test(pathname)) {
    return "student-rating";
  }
  if (/^\/dashboard\/\d+\/resources\/?$/.test(pathname)) {
    return "student-resources";
  }
  if (/^\/dashboard\/\d+\/office-hours\/?$/.test(pathname)) {
    return "student-office-hours";
  }
  if (/^\/dashboard\/\d+\/?$/.test(pathname)) {
    return "student-dashboard";
  }
  return null;
}

function normalizePageName(page: unknown): ReactPageName | null {
  const rawPage = typeof page === "string" ? page.trim() : "";
  if (!rawPage) {
    return null;
  }
  if (REACT_PAGES.has(rawPage as ReactPageName)) {
    return rawPage as ReactPageName;
  }

  const aliases: Record<string, ReactPageName> = {
    "admin-home": "internal-operations-home",
    "admin-edit-student": "internal-edit-student",
    "hr-home": "hr-manager-home",
    "support-home": "customer-support-home",
    "head-of-department-home": "head-of-departments-home",
    "head-of-department-academy": "head-of-departments-academy",
    "head-of-department-timetable": "head-of-departments-timetable",
    "head-of-department-announcements": "head-of-departments-announcements",
    "chat": "student-chat",
    "student-chat-room": "student-chat",
    "student-ar-lessons": "student-ar",
    "student-aap-lessons": "student-aap",
    "ar-lessons": "student-ar",
    "aap-lessons": "student-aap",
    "office-hours": "student-office-hours",
    "student-office-hours": "student-office-hours",
  };

  return aliases[rawPage] || null;
}

declare global {
  interface Window {
    __MSI_BOOTSTRAP__?: ReactBootstrap;
  }
}

function parseBootstrapScript(): ReactBootstrap | null {
  const node = document.getElementById("msi-react-bootstrap");
  if (!node) {
    return null;
  }

  try {
    const parsed = JSON.parse(node.textContent || "");
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed as ReactBootstrap;
  } catch (_error) {
    return null;
  }
}

export function readBootstrap(): ReactBootstrap {
  const parsed = window.__MSI_BOOTSTRAP__ || parseBootstrapScript();
  const inferredPage = inferPageFromPath(window.location.pathname);
  if (!parsed) {
    return {
      page: inferredPage || "student-not-found",
      props: {
        message: "React bootstrap payload is missing.",
      },
    };
  }

  const normalizedPage = normalizePageName(parsed.page) || inferredPage || "student-not-found";
  const normalized = {
    ...parsed,
    page: normalizedPage,
  };

  window.__MSI_BOOTSTRAP__ = normalized;
  return normalized;
}
