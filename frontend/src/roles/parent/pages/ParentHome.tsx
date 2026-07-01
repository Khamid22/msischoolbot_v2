import { FormEvent, useEffect } from "react";
import { ArrowRight, LogOut, UserRound } from "lucide-react";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";

function asArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function childName(child: Record<string, unknown>): string {
  return (
    asString(child.student_full_name) ||
    asString(child.full_name) ||
    asString(child.name) ||
    "O'quvchi"
  );
}

function childCode(child: Record<string, unknown>): string {
  return asString(child.student_id) || asString(child.student_code) || "";
}

function childRowId(child: Record<string, unknown>): number {
  return asNumber(child.student_row_id) || asNumber(child.id);
}

function childDashboardUrl(child: Record<string, unknown>): string {
  const rowId = childRowId(child);
  return rowId > 0 ? `/parent/dashboard/${rowId}` : "/";
}

export default function ParentHome(props: Record<string, unknown>) {
  const authLogin = asString(props.authLogin) || "Ota-ona";
  const logoutUrl = asString(props.logoutUrl) || "/logout";
  const csrfToken = asString(props.csrfToken);
  const children = asArray(props.parentChildren);
  const hasSingleChild = children.length === 1;

  useEffect(() => {
    if (!hasSingleChild) {
      return;
    }
    const url = childDashboardUrl(children[0]);
    if (url !== "/") {
      window.location.replace(url);
    }
  }, [children, hasSingleChild]);

  async function handleLogout(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      window.sessionStorage.setItem("msiManualLoginMode", "1");
    } catch {
      // The logged_out URL flag still prevents auto-login when storage is unavailable.
    }
    await fetch(logoutUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    }).catch(() => {});
    window.location.href = "/?logged_out=1";
  }

  const topbar = (
    <Topbar
      title={authLogin}
      subtitle="Ota-ona kabineti / Кабинет родителя"
      leadingContent={
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <UserRound className="h-4 w-4 text-foreground" />
        </span>
      }
      rightContent={
        <form onSubmit={handleLogout}>
          <button
            type="submit"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 text-xs font-bold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:w-auto sm:gap-1.5 sm:px-3"
            aria-label="Chiqish / Выйти"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Chiqish / Выйти</span>
          </button>
        </form>
      }
    />
  );

  return (
    <TelegramLayout topbar={topbar}>
      <div className="mx-auto flex min-h-[calc(var(--tg-app-height)-var(--app-top-inset)-var(--app-bottom-inset)-7.5rem)] w-full max-w-4xl flex-col justify-center py-4">
        {hasSingleChild ? (
          <section className="rounded-xl border border-foreground/10 bg-surface p-5 text-center shadow-card">
            <p className="text-sm font-bold text-foreground">Kabinet ochilmoqda… / Открываем кабинет…</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Farzandingiz natijalariga yo'naltiryapmiz.
            </p>
          </section>
        ) : children.length > 1 ? (
          <section className="rounded-xl border border-foreground/10 bg-surface p-4 shadow-card">
            <div className="mb-4">
              <h1 className="font-display text-lg font-bold">Farzandni tanlang / Выберите ребёнка</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Natijalarni ko'rish uchun kabinetni oching.
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {children.map((child) => {
                const url = childDashboardUrl(child);
                const code = childCode(child);
                return (
                  <a
                    key={`${childRowId(child)}-${code}`}
                    href={url}
                    className="group flex items-center justify-between gap-3 rounded-lg border border-foreground/10 bg-background px-3 py-3 hover:border-primary/40 hover:bg-muted/70"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-bold">{childName(child)}</span>
                      {code ? (
                        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                          Code {code}
                        </span>
                      ) : null}
                    </span>
                    <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-primary" />
                  </a>
                );
              })}
            </div>
          </section>
        ) : (
          <section className="rounded-xl border border-foreground/10 bg-surface p-5 text-center shadow-card">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
              <UserRound className="h-5 w-5 text-muted-foreground" />
            </span>
            <h1 className="mt-4 font-display text-lg font-bold">Farzand ulanmagan / Ребёнок не подключён</h1>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
              Administrator yuborgan yangi havolani Telegram ichida oching. Ulanish tugagach,
              kabinet avtomatik ochiladi.
            </p>
          </section>
        )}
      </div>
    </TelegramLayout>
  );
}
