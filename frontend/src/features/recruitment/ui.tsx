import type { ReactNode } from "react";

export const RECRUITMENT_API = "/api/v1/recruitment";

export const fieldClass =
  "min-h-11 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none transition-colors focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20";
export const buttonClass =
  "inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[13px] font-semibold text-primary-foreground transition-colors hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50";
export const secondaryButtonClass =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-[13px] font-semibold text-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50";

export function roleLabel(role: string) {
  return {
    hr_manager: "HR Manager",
    academic_director: "Academic Director",
    head_of_department: "Head of Department",
    ceo: "CEO",
  }[role] || "Recruitment";
}

export function workspaceHome(role: string) {
  return {
    hr_manager: "/hr-manager",
    academic_director: "/academic-director",
    head_of_department: "/head-of-departments",
    ceo: "/ceo",
  }[role] || "/";
}

export function queryError(error: unknown) {
  return error instanceof Error ? error.message : "Unable to load recruitment data.";
}

export function PageState({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "error" }) {
  return (
    <div
      className={`rounded-xl border p-4 text-sm ${tone === "error" ? "border-destructive/30 bg-destructive/5 text-destructive" : "border-border bg-card text-muted-foreground"}`}
    >
      {children}
    </div>
  );
}

export function EmptyLine({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-border px-3 py-3 text-sm text-muted-foreground">{children}</p>;
}

export function DefinitionGrid({ values }: { values: Array<[string, unknown]> }) {
  return (
    <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      {values.map(([label, value]) => {
        const displayValue = value === null || value === undefined || value === "" ? "Not set" : String(value);
        return (
          <div key={label} className="min-w-0 rounded-lg bg-muted/45 px-3 py-2.5">
            <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</dt>
            <dd className="mt-0.5 break-words text-[13px] font-semibold text-foreground">{displayValue}</dd>
          </div>
        );
      })}
    </dl>
  );
}

export function replaceUrlParams(values: Record<string, string | number | null | undefined>, clearKeys: string[] = []) {
  const url = new URL(window.location.href);
  clearKeys.forEach((key) => url.searchParams.delete(key));
  Object.entries(values).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") url.searchParams.delete(key);
    else url.searchParams.set(key, String(value));
  });
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

const returnPositionPrefix = "msi:recruitment:return:";
type RecruitmentReturnView = "pipeline" | "decisions" | "candidates" | "tasks" | "trash";

export function rememberRecruitmentReturn(view: RecruitmentReturnView) {
  try {
    window.sessionStorage.setItem(`${returnPositionPrefix}${view}`, JSON.stringify({
      url: `${window.location.pathname}${window.location.search}`,
      scrollY: window.scrollY,
    }));
  } catch {
    // Navigation still works when session storage is unavailable.
  }
}

export function restoreRecruitmentReturn(view: RecruitmentReturnView) {
  try {
    const raw = window.sessionStorage.getItem(`${returnPositionPrefix}${view}`);
    if (!raw) return;
    const saved = JSON.parse(raw) as { url?: string; scrollY?: number };
    if (saved.url !== `${window.location.pathname}${window.location.search}` || !Number.isFinite(saved.scrollY)) return;
    window.sessionStorage.removeItem(`${returnPositionPrefix}${view}`);
    window.requestAnimationFrame(() => window.scrollTo({ top: Number(saved.scrollY), behavior: "auto" }));
  } catch {
    // Ignore stale or unavailable session storage.
  }
}
