import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getParent, sendParent } from "@/workspaces/parent/api";
import { ErrorState, LoadingState } from "@/workspaces/parent/components";
import type {
  ParentBootstrapProps,
  ParentLanguage,
  ParentNavKey,
  ParentOverview,
  ParentPreference,
} from "@/workspaces/parent/model";
import { navigateParentWorkspace } from "@/workspaces/parent/navigation";
import { ParentWorkspaceShell } from "@/workspaces/parent/ParentWorkspaceShell";
import { ChildrenScreen } from "@/workspaces/parent/screens/ChildrenScreen";
import { HomeScreen } from "@/workspaces/parent/screens/HomeScreen";
import { PaymentsScreen } from "@/workspaces/parent/screens/PaymentsScreen";
import { SupportScreen } from "@/workspaces/parent/screens/SupportScreen";
import { UpdatesScreen } from "@/workspaces/parent/screens/UpdatesScreen";

const PARENT_VIEWS = new Set<ParentNavKey>([
  "home",
  "updates",
  "children",
  "payments",
  "support",
]);

function normalizeView(view: string | undefined): ParentNavKey {
  return PARENT_VIEWS.has(view as ParentNavKey) ? view as ParentNavKey : "home";
}

function normalizeLanguage(value: string | undefined): ParentLanguage {
  return value === "uz" ? "uz" : "ru";
}

export default function ParentWorkspace({
  authLogin = "",
  csrfToken = "",
  logoutUrl = "/logout",
  view,
  selectedStudentId: initialStudentId = null,
  selectedTicketId = null,
  preferredLanguage,
}: ParentBootstrapProps) {
  const queryClient = useQueryClient();
  const activeView = normalizeView(view);
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(
    initialStudentId,
  );
  const [language, setLanguage] = useState<ParentLanguage>(
    normalizeLanguage(preferredLanguage),
  );
  const overview = useQuery({
    queryKey: ["parent", "overview"],
    queryFn: ({ signal }) => getParent<ParentOverview>("/overview", signal),
  });

  useEffect(() => {
    setSelectedStudentId(initialStudentId);
  }, [initialStudentId]);

  useEffect(() => {
    const storedLanguage = overview.data?.preference?.preferredLanguage;
    if (storedLanguage === "ru" || storedLanguage === "uz") {
      setLanguage(storedLanguage);
    }
  }, [overview.data?.preference?.preferredLanguage]);

  const preferenceMutation = useMutation({
    mutationFn: (nextLanguage: ParentLanguage) => sendParent<ParentPreference>(
      "/preferences",
      "PATCH",
      { preferredLanguage: nextLanguage },
      csrfToken,
    ),
    onSuccess: (preference) => {
      queryClient.setQueryData<ParentOverview>(
        ["parent", "overview"],
        (current) => current ? { ...current, preference } : current,
      );
    },
  });

  function changeLanguage(nextLanguage: ParentLanguage) {
    if (nextLanguage === language || preferenceMutation.isPending) return;
    setLanguage(nextLanguage);
    preferenceMutation.mutate(nextLanguage, {
      onError: () => setLanguage(language),
    });
  }

  function changeChild(studentId: number | null) {
    setSelectedStudentId(studentId);
    if (activeView === "children") {
      navigateParentWorkspace(
        studentId ? `/parent/children/${studentId}` : "/parent/children",
      );
    }
  }

  if (overview.isLoading) {
    return (
      <main className="min-h-[var(--tg-viewport-height)] bg-background p-4">
        <LoadingState
          label={language === "ru" ? "Загрузка кабинета" : "Kabinet yuklanmoqda"}
        />
      </main>
    );
  }

  if (overview.isError || !overview.data) {
    return (
      <main className="min-h-[var(--tg-viewport-height)] bg-background p-4">
        <ErrorState
          message={overview.error instanceof Error
            ? overview.error.message
            : "Could not load the parent workspace."}
          retry={() => void overview.refetch()}
          label={language === "ru" ? "Повторить" : "Qayta urinish"}
        />
      </main>
    );
  }

  const data = overview.data;
  return (
    <ParentWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      logoutUrl={logoutUrl}
      active={activeView}
      language={language}
      onLanguageChange={changeLanguage}
      childrenList={data.children}
      selectedStudentId={selectedStudentId}
      onChildChange={changeChild}
    >
      {preferenceMutation.isError ? (
        <p
          className="rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive"
          role="alert"
        >
          {language === "ru"
            ? "Не удалось сохранить язык."
            : "Tilni saqlab bo‘lmadi."}
        </p>
      ) : null}
      {activeView === "updates" ? (
        <UpdatesScreen language={language} />
      ) : activeView === "children" ? (
        <ChildrenScreen
          children={data.children}
          selectedStudentId={selectedStudentId}
          language={language}
        />
      ) : activeView === "payments" ? (
        <PaymentsScreen
          children={data.children}
          selectedStudentId={selectedStudentId}
          language={language}
        />
      ) : activeView === "support" ? (
        <SupportScreen
          children={data.children}
          selectedTicketId={selectedTicketId}
          language={language}
          csrfToken={csrfToken}
        />
      ) : (
        <HomeScreen overview={data} language={language} />
      )}
    </ParentWorkspaceShell>
  );
}

export { normalizeLanguage, normalizeView };
