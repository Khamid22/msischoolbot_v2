import { AlertCircle, RefreshCw, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import type { ParentChild, ParentLanguage } from "@/workspaces/parent/model";
import { parentCopy } from "@/workspaces/parent/copy";

export function ParentPageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="font-display text-xl font-black text-foreground sm:text-2xl">{title}</h1>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {action}
    </header>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="space-y-3" role="status" aria-label={label}>
      {[0, 1, 2].map((item) => (
        <div
          key={item}
          className="h-24 animate-pulse rounded-xl border border-border/70 bg-surface motion-reduce:animate-none"
        />
      ))}
    </div>
  );
}

export function ErrorState({
  message,
  retry,
  label,
}: {
  message: string;
  retry: () => void;
  label: string;
}) {
  return (
    <section className="rounded-xl border border-destructive/25 bg-destructive/5 p-5 text-center" role="alert">
      <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
      <p className="mt-3 text-sm font-semibold text-foreground">{message}</p>
      <button
        type="button"
        onClick={retry}
        className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
      >
        <RefreshCw className="h-4 w-4" />
        {label}
      </button>
    </section>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-dashed border-border bg-surface p-6 text-center">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        <UserRound className="h-5 w-5" />
      </span>
      <h2 className="mt-4 text-base font-black text-foreground">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </section>
  );
}

export function ChildSelector({
  children,
  selectedId,
  language,
  onChange,
}: {
  children: ParentChild[];
  selectedId: number | null;
  language: ParentLanguage;
  onChange: (studentId: number | null) => void;
}) {
  const copy = parentCopy[language];
  return (
    <label className="block min-w-0 text-xs font-bold text-muted-foreground">
      <span className="sr-only">{copy.children}</span>
      <select
        value={selectedId || ""}
        onChange={(event) => onChange(Number(event.target.value) || null)}
        className="min-h-11 w-full rounded-lg border border-border bg-surface px-3 text-sm font-semibold text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:w-auto sm:min-w-56"
      >
        <option value="">{copy.allChildren}</option>
        {children.map((child) => (
          <option key={child.studentRowId} value={child.studentRowId}>
            {child.fullName}
          </option>
        ))}
      </select>
    </label>
  );
}

export function formatMoney(value: number, currency = "UZS") {
  return `${Math.round(Number(value) || 0).toLocaleString()} ${currency}`;
}

export function formatDate(value: string) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}
