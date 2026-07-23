import type { ReactNode } from "react";

export const primaryButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-black text-primary-foreground transition-colors duration-150 hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
export const secondaryButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-black text-foreground transition-colors duration-150 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/25 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
export const dangerButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm font-black text-destructive transition-colors duration-150 hover:bg-destructive/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
export const inputClass = "min-h-11 w-full rounded-lg border border-border bg-background px-3 text-base font-semibold text-foreground outline-none transition-colors duration-150 placeholder:text-muted-foreground/70 focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground motion-reduce:transition-none";

export function asText(value: unknown) {
  return String(value ?? "").trim();
}

export function asNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatDate(value: string | null | undefined, includeTime = false) {
  const raw = asText(value);
  if (!raw) return "Not set";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(new Date(parsed));
}

export function money(value: number | string | null | undefined, currency = "UZS") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "UZS",
    maximumFractionDigits: 0,
  }).format(asNumber(value));
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor: string }) {
  return <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-black uppercase tracking-wide text-muted-foreground">{children}</label>;
}

export function Field({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="min-w-0 rounded-lg border border-border/80 bg-background px-3 py-2.5">
      <dt className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={`mt-1 break-words text-sm font-bold text-foreground ${mono ? "font-mono" : ""}`}>{value || "Not set"}</dd>
    </div>
  );
}

export function DetailSection({
  title,
  icon,
  action,
  children,
}: {
  title: string;
  icon: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-card shadow-sm">
      <header className="flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="flex min-w-0 items-center gap-2 text-sm font-black text-foreground">
          <span className="text-primary">{icon}</span>
          <span className="break-words">{title}</span>
        </h2>
        {action}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function DetailSkeleton() {
  return (
    <div className="space-y-4" aria-label="Loading record" role="status">
      <span className="sr-only">Loading record details</span>
      {[1, 2, 3].map((item) => (
        <div key={item} className="h-40 animate-pulse rounded-lg border border-border bg-muted motion-reduce:animate-none" />
      ))}
    </div>
  );
}
