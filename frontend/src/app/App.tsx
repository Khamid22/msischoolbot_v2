import { Component, Suspense, lazy, useEffect, type ComponentType } from "react";
import { readBootstrap } from "@/shared/lib/bootstrap";
import { clearStaleRolePreviewStorage } from "@/shared/lib/staleUiState";
import { getTelegramStartParam, initTelegramViewport } from "@/shared/lib/telegram";

const bootstrap = readBootstrap();

const pageMap = {
  login: lazy(() => import("@/roles/student/pages/Login")),
  "student-home": lazy(() => import("@/roles/student/pages/Home")),
  "student-dashboard": lazy(() => import("@/roles/student/pages/Dashboard")),
  "student-resources": lazy(() => import("@/roles/student/pages/Resources")),
  "student-rating": lazy(() => import("@/roles/student/pages/Rating")),
  "student-aap": lazy(() => import("@/roles/student/pages/AAP")),
  "student-ar": lazy(() => import("@/roles/student/pages/AR")),
  "admin-home": lazy(() => import("@/roles/admin/pages/Admin")),
  "teacher-home": lazy(() => import("@/roles/teacher/pages/TeacherHome")),
  "parent-home": lazy(() => import("@/roles/parent/pages/ParentHome")),
  "ceo-home": lazy(() => import("@/roles/common/pages/RoleHome")),
  "hr-home": lazy(() => import("@/roles/common/pages/RoleHome")),
  "support-home": lazy(() => import("@/roles/common/pages/RoleHome")),
  "academic-director-home": lazy(() => import("@/roles/common/pages/RoleHome")),
  "academic-director-academy": lazy(() => import("@/roles/academic_director/pages/TeacherAcademy")),
  "academic-director-head-of-departments": lazy(() => import("@/roles/academic_director/pages/HeadOfDepartments")),
  "academic-director-timetable": lazy(() => import("@/roles/common/pages/AcademicDepartmentWorkspace")),
  "academic-director-announcements": lazy(() => import("@/roles/common/pages/AcademicDepartmentWorkspace")),
  "head-of-department-home": lazy(() => import("@/roles/common/pages/RoleHome")),
  "head-of-department-academy": lazy(() => import("@/roles/head_of_department/pages/TeacherAcademy")),
  "head-of-department-timetable": lazy(() => import("@/roles/common/pages/AcademicDepartmentWorkspace")),
  "head-of-department-announcements": lazy(() => import("@/roles/common/pages/AcademicDepartmentWorkspace")),
  unauthorized: lazy(() => import("@/roles/common/pages/Unauthorized")),
  "admin-edit-student": lazy(() => import("@/roles/admin/pages/EditStudentProfile")),
  "student-chat": lazy(() => import("@/roles/student/pages/Chat")),
  "student-office-hours": lazy(() => import("@/roles/student/pages/OfficeHours")),
  "student-not-found": lazy(() => import("@/roles/student/pages/StudentNotFound")),
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
      void fetch("/api/activity/ping", {
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
