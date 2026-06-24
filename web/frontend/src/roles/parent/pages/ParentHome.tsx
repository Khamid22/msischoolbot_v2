import { lazy, Suspense } from "react";
import { LogOut, UserRound } from "lucide-react";

const ParentPanel = lazy(() => import("@/roles/admin/panels/ParentPanel"));

export default function ParentHome(props: Record<string, unknown>) {
  const authLogin = String(props.authLogin || "");
  const logoutUrl = String(props.logoutUrl || "/logout");
  const csrfToken = String(props.csrfToken || "");

  // ParentPanel reads state.props?.adminAnnouncements, so mirror top-level props there.
  const state = { ...props, props };

  async function handleLogout(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await fetch(logoutUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    }).catch(() => {});
    window.location.href = "/";
  }

  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-30 border-b border-foreground/8 bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
            <UserRound className="h-4 w-4 text-foreground" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold leading-tight">{authLogin || "Ota-ona"}</p>
            <p className="text-[11px] text-muted-foreground">Ota-ona kabineti / Кабинет родителя</p>
          </div>
          <form onSubmit={handleLogout}>
            <button
              type="submit"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 px-2.5 text-xs font-bold text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <LogOut className="h-3.5 w-3.5" />
              Chiqish / Выйти
            </button>
          </form>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-4">
        <Suspense
          fallback={
            <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
              Yuklanmoqda… / Загрузка…
            </div>
          }
        >
          <ParentPanel state={state} />
        </Suspense>
      </main>
    </div>
  );
}
