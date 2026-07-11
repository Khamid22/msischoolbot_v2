import { Component, Suspense, lazy, useEffect, type ComponentType } from "react";
import { readBootstrap } from "@/shared/lib/bootstrap";
import { clearStaleRolePreviewStorage } from "@/shared/lib/staleUiState";
import { getTelegramStartParam, initTelegramViewport } from "@/shared/lib/telegram";

const bootstrap = readBootstrap();

const pageMap = {
  login: lazy(() => import("@/features/accounts/pages/Login")),
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
  "academic-director-announcements": lazy(() => import("@/features/academic_workspace/AcademicDepartmentWorkspace")),
  "head-of-departments-home": lazy(() => import("@/workspaces/head_of_departments/pages/Home")),
  "head-of-departments-academy": lazy(() => import("@/workspaces/head_of_departments/pages/TeacherAcademy")),
  "head-of-departments-timetable": lazy(() => import("@/features/academic_workspace/AcademicDepartmentWorkspace")),
  "head-of-departments-announcements": lazy(() => import("@/features/academic_workspace/AcademicDepartmentWorkspace")),
  "account-security": lazy(() => import("@/features/accounts/pages/AccountSecurity")),
  unauthorized: lazy(() => import("@/features/accounts/pages/Unauthorized")),
  "internal-edit-student": lazy(() => import("@/features/student_records/EditStudentProfile")),
  "student-chat": lazy(() => import("@/workspaces/student/pages/Chat")),
  "student-office-hours": lazy(() => import("@/workspaces/student/pages/OfficeHours")),
  "student-not-found": lazy(() => import("@/workspaces/student/pages/StudentNotFound")),
} as const;

const ResolvedPage = (pageMap[bootstrap.page] || pageMap["student-not-found"]) as ComponentType<
  Record<string, unknown>
>;

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

  useStudentActivityHeartbeat(bootstrap.page, bootstrap.props);

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
        <ResolvedPage {...bootstrap.props} />
      </Suspense>
    </AppErrorBoundary>
  );
};

export default App;
