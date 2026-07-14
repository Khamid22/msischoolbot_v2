import { Component, Suspense, lazy, useEffect, useState, type ComponentType } from "react";
import { parseBootstrapDocument, readBootstrap, type ReactBootstrap } from "@/shared/lib/bootstrap";
import { clearStaleRolePreviewStorage } from "@/shared/lib/staleUiState";
import { getTelegramStartParam, initTelegramViewport } from "@/shared/lib/telegram";

const bootstrap = readBootstrap();

const pageMap = {
  login: lazy(() => import("@/features/identity/pages/Login")),
  "student-home": lazy(() => import("@/workspaces/student/pages/Home")),
  "student-dashboard": lazy(() => import("@/workspaces/student/pages/Dashboard")),
  "student-resources": lazy(() => import("@/workspaces/student/pages/Resources")),
  "student-rating": lazy(() => import("@/workspaces/student/pages/Rating")),
  "student-aap": lazy(() => import("@/workspaces/student/pages/AAP")),
  "student-ar": lazy(() => import("@/workspaces/student/pages/AR")),
  "internal-operations-home": lazy(() => import("@/internal_operations/pages/InternalOperations")),
  "parent-home": lazy(() => import("@/workspaces/parent/pages/ParentHome")),
  "ceo-home": lazy(() => import("@/workspaces/ceo/pages/Home")),
  "hr-manager-home": lazy(() => import("@/workspaces/hr_manager/pages/Home")),
  "customer-support-home": lazy(() => import("@/workspaces/customer_support/pages/Home")),
  "academic-director-home": lazy(() => import("@/workspaces/academic_director/pages/Home")),
  "academic-director-academy": lazy(() => import("@/workspaces/academic_director/pages/TeacherAcademy")),
  "academic-director-head-of-departments": lazy(() => import("@/workspaces/academic_director/pages/HeadOfDepartments")),
  "academic-director-groups": lazy(() => import("@/workspaces/academic_director/pages/AcademicWorkspace")),
  "academic-director-subjects": lazy(() => import("@/workspaces/academic_director/pages/AcademicWorkspace")),
  "academic-director-timetable": lazy(() => import("@/workspaces/academic_director/pages/AcademicWorkspace")),
  "academic-director-announcements": lazy(() => import("@/workspaces/academic_shared/AcademicDepartmentWorkspace")),
  "head-of-departments-home": lazy(() => import("@/workspaces/head_of_departments/pages/Home")),
  "head-of-departments-academy": lazy(() => import("@/workspaces/head_of_departments/pages/TeacherAcademy")),
  "head-of-departments-timetable": lazy(() => import("@/workspaces/academic_shared/AcademicDepartmentWorkspace")),
  "head-of-departments-announcements": lazy(() => import("@/workspaces/academic_shared/AcademicDepartmentWorkspace")),
  "teacher-home": lazy(() => import("@/workspaces/teacher/pages/Home")),
  "account-security": lazy(() => import("@/features/identity/pages/AccountSecurity")),
  unauthorized: lazy(() => import("@/features/identity/pages/Unauthorized")),
  "internal-edit-student": lazy(() => import("@/features/people/students/EditStudentProfile")),
  "student-chat": lazy(() => import("@/workspaces/student/pages/Chat")),
  "student-office-hours": lazy(() => import("@/workspaces/student/pages/OfficeHours")),
  "student-not-found": lazy(() => import("@/workspaces/student/pages/StudentNotFound")),
} as const;

function isWorkspacePath(pathname: string) {
  return pathname === "/academic-director" || pathname.startsWith("/academic-director/") ||
    pathname === "/head-of-departments" || pathname.startsWith("/head-of-departments/");
}

class AppErrorBoundary extends Component<{ children: React.ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, errorInfo: unknown) {
    console.error("MSI React page crashed:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[var(--tg-viewport-height)] items-center justify-center bg-background px-4">
          <div className="max-w-sm rounded-lg border border-border bg-surface p-5 text-center shadow-card">
            <p className="text-sm font-semibold text-foreground">Could not load this page.</p>
            <button
              className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
              onClick={() => window.location.reload()}
              type="button"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function useStudentActivityHeartbeat(page: string, props: Record<string, unknown>) {
  useEffect(() => {
    if (!page.startsWith("student-") || page === "student-not-found") {
      return;
    }

    if (String(props.embedMode || "").trim().toLowerCase() === "admin") {
      return;
    }

    const pingActivity = () => {
      void fetch("/api/v1/student/activity/ping", {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        keepalive: true,
      }).catch(() => {});
    };

    pingActivity();
    const intervalId = window.setInterval(pingActivity, 45000);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        pingActivity();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [page, props.embedMode]);
}

const App = () => {
  const [currentBootstrap, setCurrentBootstrap] = useState<ReactBootstrap>(bootstrap);

  useEffect(() => {
    initTelegramViewport();
    clearStaleRolePreviewStorage(
      bootstrap.props.authRole || bootstrap.props.role || bootstrap.props.adminMode,
    );
    // Send the parent to the invite-link page ONCE per launch. Telegram keeps
    // initDataUnsafe.start_param for the whole mini-app session, so without this
    // guard every reload — including after a parent logs out to sign in as an
    // admin — would re-trigger registration and trap them back in parent mode.
    const startParam = getTelegramStartParam();
    if (startParam.startsWith("parent_")) {
      const handledKey = `msi_parent_link_handled:${startParam}`;
      let alreadyHandled = false;
      try {
        alreadyHandled = window.sessionStorage.getItem(handledKey) === "1";
      } catch {
        alreadyHandled = false;
      }
      const inviteCode = alreadyHandled ? "" : startParam.slice("parent_".length).trim();
      if (inviteCode) {
        try {
          window.sessionStorage.setItem(handledKey, "1");
        } catch {
          /* ignore */
        }
        window.location.replace(`/parent/invite/${encodeURIComponent(inviteCode)}`);
      }
    }
  }, []);

  useEffect(() => {
    if (!isWorkspacePath(window.location.pathname)) return;
    let navigationId = 0;

    const loadPage = async (url: URL, push: boolean) => {
      const requestId = ++navigationId;
      try {
        const response = await fetch(url, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok || response.redirected) {
          window.location.assign(response.url || url.href);
          return;
        }
        const source = await response.text();
        const nextBootstrap = parseBootstrapDocument(source);
        if (!nextBootstrap || requestId !== navigationId) {
          if (!nextBootstrap) window.location.assign(url.href);
          return;
        }
        if (push) window.history.pushState({}, "", url);
        window.__MSI_BOOTSTRAP__ = nextBootstrap;
        setCurrentBootstrap(nextBootstrap);
        window.scrollTo({ top: 0, behavior: "auto" });
      } catch (_error) {
        window.location.assign(url.href);
      }
    };

    const handleClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(target instanceof HTMLAnchorElement) || target.target || target.hasAttribute("download")) return;
      const url = new URL(target.href, window.location.href);
      if (url.origin !== window.location.origin || !isWorkspacePath(url.pathname)) return;
      event.preventDefault();
      if (url.href !== window.location.href) void loadPage(url, true);
    };
    const handlePopState = () => void loadPage(new URL(window.location.href), false);

    document.addEventListener("click", handleClick);
    window.addEventListener("popstate", handlePopState);
    return () => {
      navigationId += 1;
      document.removeEventListener("click", handleClick);
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useStudentActivityHeartbeat(currentBootstrap.page, currentBootstrap.props);

  const ResolvedPage = (pageMap[currentBootstrap.page] || pageMap["student-not-found"]) as ComponentType<
    Record<string, unknown>
  >;

  return (
    <AppErrorBoundary>
      <Suspense
        fallback={
          <div className="flex min-h-[var(--tg-viewport-height)] items-center justify-center bg-background px-4">
            <div className="animate-pulse rounded-lg bg-surface px-4 py-3 text-sm font-semibold text-muted-foreground shadow-card motion-reduce:animate-none">
              Loading...
            </div>
          </div>
        }
      >
        <ResolvedPage {...currentBootstrap.props} />
      </Suspense>
    </AppErrorBoundary>
  );
};

export default App;
