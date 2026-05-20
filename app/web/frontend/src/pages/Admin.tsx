import { Suspense, lazy, useEffect, useRef, useState } from "react";
import {
  Bell,
  BookOpen,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  RefreshCw,
  Search,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { FormAlert } from "@/components/PortalCard";
import { routes } from "@/lib/routes";
import {
  AdminPageProps,
  asNumber,
  asString,
  tabs,
} from "./admin/shared";
import { useAdminState } from "./admin/useAdminState";

const OverviewPanel = lazy(() => import("./admin/panels/OverviewPanel"));
const StudentsPanel = lazy(() => import("./admin/panels/StudentsPanel"));
const TeachersPanel = lazy(() => import("./admin/panels/TeachersPanel"));
const ResourcesPanel = lazy(() => import("./admin/panels/ResourcesPanel"));
const ChatPanel = lazy(() => import("./admin/panels/ChatPanel"));

function PanelFallback() {
  return (
    <div className="rounded-lg border border-foreground/10 bg-surface px-4 py-3 text-sm text-muted-foreground shadow-card">
      Loading panel...
    </div>
  );
}

function ActivePanel({ state }: { state: any }) {
  switch (state.activeTab) {
    case "overview":
      return <OverviewPanel state={state} />;
    case "students":
      return <StudentsPanel state={state} />;
    case "teachers":
      return <TeachersPanel state={state} />;
    case "resources":
      return <ResourcesPanel state={state} />;
    case "chat":
      return <ChatPanel state={state} />;
    default:
      return <OverviewPanel state={state} />;
  }
}

const tabIcons: Record<string, LucideIcon> = {
  overview: LayoutDashboard,
  students: Users,
  teachers: GraduationCap,
  resources: BookOpen,
  chat: MessageSquare,
};

const tabDescriptions: Record<string, string> = {
  overview: "School performance, groups, and attention signals.",
  students: "Manage student accounts, profiles, and access.",
  teachers: "Assign teachers, rates, and group ownership.",
  resources: "Upload and organize learning materials.",
  chat: "Moderate student conversations and support rooms.",
};

function AdminSidebar({
  state,
  csrfToken,
  compact = false,
}: {
  state: any;
  csrfToken?: string;
  compact?: boolean;
}) {
  return (
    <aside
      className={
        compact
          ? "flex h-full flex-col bg-sidebar text-sidebar-foreground"
          : "fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex"
      }
    >
      <div className="border-b border-sidebar-border px-4 py-4">
        <button
          type="button"
          onClick={() => state.switchAdminTab("overview")}
          className="flex w-full items-center gap-2.5 rounded-lg text-left"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary font-bold text-primary-foreground">
            M
          </div>
          <div className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-semibold text-foreground">MSI School</span>
            <span className="block truncate text-xs text-muted-foreground">Admin Console</span>
          </div>
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        <p className="px-2 pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          Manage
        </p>
        <nav className="space-y-1" aria-label="Admin navigation">
          {tabs.map((tab) => {
            const Icon = tabIcons[tab.key] || LayoutDashboard;
            const isActive = state.activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => state.switchAdminTab(tab.key)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-semibold transition-colors ${
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
            KA
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-sm font-medium text-foreground">Khamid A.</span>
            <span className="block truncate text-xs text-muted-foreground">Owner admin</span>
          </div>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Exit"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}

export default function AdminPage(props: AdminPageProps) {
  const state = useAdminState(props);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState<"idle" | "ok" | "warn" | "error">("idle");
  const [refreshMessage, setRefreshMessage] = useState("");
  const refreshResetTimerRef = useRef<number | null>(null);

  function clearRefreshResetTimer() {
    if (refreshResetTimerRef.current !== null) {
      window.clearTimeout(refreshResetTimerRef.current);
      refreshResetTimerRef.current = null;
    }
  }

  useEffect(() => {
    return () => {
      clearRefreshResetTimer();
    };
  }, []);

  async function handleRefresh() {
    if (refreshing) return;
    clearRefreshResetTimer();
    setRefreshing(true);
    setRefreshStatus("idle");
    setRefreshMessage("Refreshing Google Sheets data...");
    try {
      const res = await fetch(routes.adminRefreshApi, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": props.csrfToken || "",
        },
      });
      let payload: Record<string, unknown> = {};
      try {
        payload = (await res.json()) as Record<string, unknown>;
      } catch {
        payload = {};
      }

      const apiMessage = asString(payload.message);
      const alreadyRunning = Boolean(payload.already_running);
      if (res.status === 202) {
        setRefreshStatus("ok");
        setRefreshMessage(apiMessage || "Refresh started in background.");
      } else if (res.status === 503 && alreadyRunning) {
        setRefreshStatus("warn");
        setRefreshMessage(apiMessage || "Refresh is already running; rerun queued.");
      } else {
        setRefreshStatus("error");
        setRefreshMessage(apiMessage || "Unable to start refresh.");
      }
    } catch {
      setRefreshStatus("error");
      setRefreshMessage("Network error. Please try again.");
    } finally {
      setRefreshing(false);
      refreshResetTimerRef.current = window.setTimeout(() => {
        setRefreshStatus("idle");
        setRefreshMessage("");
        refreshResetTimerRef.current = null;
      }, 4000);
    }
  }

  function handleSchoolChange(nextSchool: string) {
    const params = new URLSearchParams();
    params.set("panel", state.activeTab);
    params.set("school", nextSchool || "all");
    window.location.href = `/?${params.toString()}`;
  }

  const activeTabLabel = tabs.find((tab) => tab.key === state.activeTab)?.label || "Overview";
  const activeTabDescription = tabDescriptions[state.activeTab] || "Manage the admin workspace.";

  return (
    <div className="min-h-[100dvh] bg-background">
      <AdminSidebar state={state} csrfToken={props.csrfToken} />

      <header
        className="fixed inset-x-0 top-0 z-50 border-b border-foreground/5 bg-surface/95 backdrop-blur lg:left-64"
        style={{ paddingTop: "var(--app-top-inset)" }}
      >
        <div className="flex h-14 w-full items-center gap-3 px-3 sm:px-4 md:px-6">
          <button
            type="button"
            onClick={() => state.setMobileNavOpen((current: boolean) => !current)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-muted lg:hidden"
            aria-label={state.mobileNavOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={state.mobileNavOpen}
            aria-controls="admin-mobile-nav"
          >
            {state.mobileNavOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>

          <div className="relative hidden min-w-0 max-w-md flex-1 md:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={state.searchQuery}
              onChange={(event) => state.setSearchQuery(event.target.value)}
              placeholder="Search students, resources..."
              className="h-9 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-foreground/30"
            />
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh data from Google Sheets"
            className={`ml-auto flex h-9 items-center gap-2 rounded-lg px-3 text-xs font-bold transition-colors disabled:opacity-60 ${
              refreshStatus === "ok"
                ? "text-green-600"
                : refreshStatus === "warn"
                  ? "text-amber-600"
                : refreshStatus === "error"
                  ? "text-destructive"
                  : "hover:bg-muted"
            }`}
          >
            {refreshing ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Refresh</span>
          </button>

          <button
            type="button"
            className="relative hidden h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground sm:flex"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-destructive" />
          </button>

          <form action={routes.logout} method="post" className="shrink-0 sm:ml-auto">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button
              type="submit"
              className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-muted"
              aria-label="Exit"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
        {refreshMessage ? (
          <div className="w-full px-3 pb-2 sm:px-4 md:px-6">
            <p
              role="status"
              aria-live="polite"
              className={`text-xs font-semibold ${
                refreshing
                  ? "text-muted-foreground"
                  : refreshStatus === "ok"
                    ? "text-green-600"
                    : refreshStatus === "warn"
                      ? "text-amber-600"
                      : refreshStatus === "error"
                        ? "text-destructive"
                        : "text-muted-foreground"
              }`}
            >
              {refreshMessage}
            </p>
          </div>
        ) : null}
        {state.mobileNavOpen ? (
          <div id="admin-mobile-nav" className="fixed inset-x-0 bottom-0 top-14 z-50 border-t border-foreground/5 bg-foreground/35 lg:hidden">
            <div className="h-full w-[min(20rem,86vw)] shadow-card-hover">
              <AdminSidebar state={state} csrfToken={props.csrfToken} compact />
            </div>
          </div>
        ) : null}
      </header>

      <main
        className="w-full px-3 pb-6 pt-[calc(var(--app-top-inset)+4.5rem)] sm:px-4 md:px-6 lg:ml-64 lg:w-[calc(100%-16rem)]"
      >
        <section className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-normal text-foreground">
              {activeTabLabel}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">{activeTabDescription}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={state.currentSchool}
              onChange={(event) => handleSchoolChange(event.target.value)}
              className="h-9 rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-semibold outline-none focus:border-foreground/30"
              aria-label="School"
            >
              {state.schoolOptions.map((school: { code: string; label: string }) => (
                <option key={school.code} value={school.code}>
                  {school.label}
                </option>
              ))}
            </select>
            <div className="relative w-full sm:hidden">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="search"
                value={state.searchQuery}
                onChange={(event) => state.setSearchQuery(event.target.value)}
                placeholder="Search..."
                className="h-9 w-full rounded-lg border border-foreground/10 bg-surface pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
              />
            </div>
          </div>
        </section>

        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}

        {state.resourceUploadState.active && state.activeTab !== "resources" ? (
          <div className="mb-4 rounded-lg border border-foreground/10 bg-surface px-4 py-3 shadow-card">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className={`text-xs font-semibold uppercase tracking-wide ${state.resourceUploadState.error ? "text-destructive" : "text-muted-foreground"}`}>
                  {state.resourceUploadState.message}
                </p>
              </div>
              <button
                type="button"
                onClick={() => state.switchAdminTab("resources")}
                className="shrink-0 rounded-lg bg-muted px-3 py-1.5 text-[11px] font-bold text-foreground hover:bg-foreground/10"
              >
                Open Upload
              </button>
            </div>
            <div
              className="overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(state.resourceUploadState.percent)}
            >
              <div
                className={`h-2 rounded-full transition-[width] duration-200 ${state.resourceUploadState.error ? "bg-destructive" : "bg-primary"}`}
                style={{
                  width: `${Math.max(0, Math.min(100, state.resourceUploadState.percent))}%`,
                }}
              />
            </div>
          </div>
        ) : null}

        <Suspense fallback={<PanelFallback />}>
          <ActivePanel state={state} />
        </Suspense>
      </main>

      {state.editingResource ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
          onClick={() => {
            state.setEditingResource(null);
            state.setEditError("");
          }}
        >
          <div
            className="flex max-h-[88dvh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 className="text-sm font-bold">Edit Resource</h3>
              <button
                type="button"
                onClick={() => {
                  state.setEditingResource(null);
                  state.setEditError("");
                }}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="space-y-3 px-5 py-4">
                {state.editError ? (
                  <p className="text-xs font-semibold text-destructive">{state.editError}</p>
                ) : null}

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Title</span>
                  <input
                    type="text"
                    value={state.editingResource.title}
                    onChange={(e) =>
                      state.setEditingResource((prev: any) =>
                        prev ? { ...prev, title: e.target.value } : null
                      )
                    }
                    maxLength={180}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</span>
                  <textarea
                    value={state.editingResource.description}
                    onChange={(e) =>
                      state.setEditingResource((prev: any) =>
                        prev ? { ...prev, description: e.target.value } : null
                      )
                    }
                    rows={3}
                    maxLength={2000}
                    className="w-full resize-none rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Resource Type</span>
                  <select
                    value={String(state.editingResource.resourceTypeId)}
                    onChange={(e) =>
                      state.setEditingResource((prev: any) =>
                        prev ? { ...prev, resourceTypeId: Number(e.target.value) } : null
                      )
                    }
                    disabled={state.editSaving}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30 disabled:opacity-50"
                  >
                    {state.activeResourceTypes.map((typeRow: Record<string, unknown>) => (
                      <option key={asNumber(typeRow.id)} value={asNumber(typeRow.id)}>
                        {asString(typeRow.name)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {state.editingResource.resourceFileKind === "video" ? "Swap Video" : "Replace File"}
                    <span className="ml-1 font-normal normal-case text-muted-foreground/60">
                      (optional — leave empty to keep current)
                    </span>
                  </span>
                  <input
                    ref={state.editResourceFileRef}
                    type="file"
                    name="resource_file"
                    accept={
                      state.editingResource.resourceFileKind === "video"
                        ? "video/mp4,video/quicktime,video/x-m4v"
                        : undefined
                    }
                    disabled={state.editSaving}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                  />
                </label>

                {state.editingResource.resourceFileKind === "video" ? (
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {state.editingResource.thumbnailUrl ? "Swap Thumbnail" : "Add Thumbnail"}
                      <span className="ml-1 font-normal normal-case text-muted-foreground/60">
                        (optional)
                      </span>
                    </span>
                    {state.editingResource.thumbnailUrl ? (
                      <img
                        src={state.editingResource.thumbnailUrl}
                        alt="Current thumbnail"
                        className="mb-2 h-20 w-auto rounded-lg object-cover"
                      />
                    ) : null}
                    <input
                      ref={state.editThumbnailFileRef}
                      type="file"
                      name="thumbnail_file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={state.editSaving}
                      className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                    />
                  </label>
                ) : null}
              </div>
            </div>

            <div className="flex shrink-0 gap-2 border-t border-foreground/5 px-5 py-3">
              <button
                type="button"
                disabled={state.editSaving}
                onClick={state.saveEditResource}
                className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50"
              >
                {state.editSaving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  state.setEditingResource(null);
                  state.setEditError("");
                }}
                className="rounded-xl bg-muted px-5 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
