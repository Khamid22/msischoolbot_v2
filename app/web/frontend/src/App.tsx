import { Suspense, lazy } from "react";
import { readBootstrap } from "./lib/bootstrap";
import { useTelegramSafeArea } from "./hooks/useTelegramSafeArea";

const bootstrap = readBootstrap();

const pageMap = {
  login: lazy(() => import("./pages/Login")),
  "student-home": lazy(() => import("./pages/Home")),
  "student-dashboard": lazy(() => import("./pages/Dashboard")),
  "student-resources": lazy(() => import("./pages/Resources")),
  "student-rating": lazy(() => import("./pages/Rating")),
  "student-aap": lazy(() => import("./pages/AAP")),
  "student-ar": lazy(() => import("./pages/AR")),
  "admin-home": lazy(() => import("./pages/Admin")),
  "admin-edit-student": lazy(() => import("./pages/EditStudentProfile")),
  "student-chat": lazy(() => import("./pages/Chat")),
  "student-not-found": lazy(() => import("./pages/StudentNotFound")),
} as const;

const ResolvedPage = pageMap[bootstrap.page] || pageMap["student-not-found"];

const App = () => {
  useTelegramSafeArea();

  return (
    <Suspense
      fallback={
        <div className="flex min-h-[var(--tg-viewport-height)] items-center justify-center bg-background px-4">
          <div className="rounded-2xl bg-surface px-4 py-3 text-sm font-semibold text-muted-foreground shadow-card">
            Loading...
          </div>
        </div>
      }
    >
      <ResolvedPage {...bootstrap.props} />
    </Suspense>
  );
};

export default App;
