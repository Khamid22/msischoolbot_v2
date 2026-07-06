import type { ReactNode } from "react";

type MetricCardTone = "default" | "success" | "warning" | "info" | "danger";

const toneClasses: Record<MetricCardTone, string> = {
  default: "border-foreground/10 bg-surface text-foreground",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  info: "border-sky-200 bg-sky-50 text-sky-900",
  danger: "border-rose-200 bg-rose-50 text-rose-900",
};

interface MetricCardProps {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  icon?: ReactNode;
  tone?: MetricCardTone;
  className?: string;
}

export function MetricCard({ label, value, detail, icon, tone = "default", className = "" }: MetricCardProps) {
  return (
    <section className={`rounded-lg border px-3 py-2.5 shadow-sm ${toneClasses[tone]} ${className}`}>
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="mt-1 truncate text-xl font-black leading-none tabular-nums">{value}</p>
        </div>
        {icon ? <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background/70 text-primary">{icon}</span> : null}
      </div>
      {detail ? <p className="mt-1 line-clamp-2 text-[11px] font-semibold leading-4 text-muted-foreground">{detail}</p> : null}
    </section>
  );
}
