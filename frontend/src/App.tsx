import { Suspense, lazy, useEffect, useState } from "react";
import { useTelegramSafeArea } from "./hooks/useTelegramSafeArea";
import { readBootstrap } from "./lib/bootstrap";

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
  "student-not-found": lazy(() => import("./pages/StudentNotFound")),
} as const;

const ResolvedPage = pageMap[bootstrap.page] || pageMap["student-not-found"];

function AppContent() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[100dvh] items-center justify-center bg-background px-4">
          <div className="rounded-2xl bg-surface px-4 py-3 text-sm font-semibold text-muted-foreground shadow-card">
            Loading...
          </div>
        </div>
      }
    >
      <ResolvedPage {...bootstrap.props} />
    </Suspense>
  );
}

const App = () => {
  useTelegramSafeArea();
  const [isBootstrapped, setIsBootstrapped] = useState(false);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;

    try {
      webApp?.expand();
    } catch (_error) {
      // Ignore Telegram viewport expansion failures outside supported clients.
    }

    try {
      webApp?.ready();
    } catch (_error) {
      // Ignore Telegram ready failures outside supported clients.
    }

    setIsBootstrapped(true);
  }, []);

  if (!isBootstrapped) {
    return null;
  }

  return <AppContent />;
};

export default App;
