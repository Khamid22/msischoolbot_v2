import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { GraduationCap, LogOut, Menu, RefreshCw, X } from "lucide-react";
import { FormAlert } from "@/components/PortalCard";
import { routes } from "@/lib/routes";
import {
  AdminPageProps,
  adminHeaderPadTop,
  adminMainPadTop,
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
    <div className="rounded-xl border border-foreground/10 bg-surface px-4 py-3 text-sm text-muted-foreground">
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

  return (
    <div className="min-h-[100dvh] bg-background">
      <header
        className="fixed inset-x-0 top-0 z-50 border-b border-foreground/5 bg-surface/95 backdrop-blur"
        style={{ paddingTop: adminHeaderPadTop }}
      >
        <div className="mx-auto flex w-full max-w-6xl items-center gap-3 px-3 py-2.5 sm:px-4 md:px-6">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh data from Google Sheets"
            className={`flex items-center gap-2 rounded-lg px-2 py-2 font-display text-sm font-bold transition-colors disabled:opacity-60 ${
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
              <RefreshCw className="h-5 w-5 animate-spin" />
            ) : (
              <GraduationCap className="h-5 w-5" />
            )}
            MSI
          </button>
          <nav
            className="hidden min-w-0 flex-1 gap-1 overflow-x-auto sm:flex"
            aria-label="Admin navigation"
            >
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => state.switchAdminTab(tab.key)}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-bold transition-colors ${
                  state.activeTab === tab.key
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 sm:hidden">
            <button
              type="button"
              onClick={() => state.setMobileNavOpen((current: boolean) => !current)}
              className="relative z-50 flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-muted"
              aria-label={state.mobileNavOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={state.mobileNavOpen}
              aria-controls="admin-mobile-nav"
            >
              {state.mobileNavOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
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
          <div className="mx-auto w-full max-w-6xl px-3 pb-2 sm:px-4 md:px-6">
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
          <div id="admin-mobile-nav" className="relative z-50 border-t border-foreground/5 px-3 pb-3 pt-2 sm:hidden">
            <nav className="grid grid-cols-2 gap-2" aria-label="Admin mobile navigation">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => state.switchAdminTab(tab.key)}
                  className={`rounded-xl px-3 py-3 text-left text-sm font-bold transition-colors ${
                    state.activeTab === tab.key
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground hover:bg-foreground/10"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-6xl px-3 pb-4 sm:px-4 md:px-6" style={{ paddingTop: adminMainPadTop }}>
        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}

        {state.resourceUploadState.active && state.activeTab !== "resources" ? (
          <div className="mb-4 rounded-xl border border-foreground/10 bg-surface px-4 py-3 shadow-card">
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
