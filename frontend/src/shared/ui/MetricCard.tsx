import type { ReactNode } from "react";

type MetricCardTone = "default" | "success" | "warning" | "info" | "danger";

const toneClasses: Record<MetricCardTone, { container: string; label: string; icon: string }> = {
  default: {
    container: "border-border/80 bg-card text-card-foreground",
    label: "text-muted-foreground",
    icon: "bg-muted text-primary",
  },
  success: {
    container: "border-success/25 bg-success/10 text-foreground",
    label: "text-success",
    icon: "bg-success/15 text-success",
  },
  warning: {
    container: "border-warning/35 bg-warning/10 text-foreground",
    label: "text-warning-foreground",
    icon: "bg-warning/20 text-warning-foreground",
  },
  info: {
    container: "border-info/25 bg-info/10 text-foreground",
    label: "text-info",
    icon: "bg-info/15 text-info",
  },
  danger: {
    container: "border-destructive/25 bg-destructive/10 text-foreground",
    label: "text-destructive",
    icon: "bg-destructive/15 text-destructive",
  },
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
  const classes = toneClasses[tone];

  return (
    <section
      aria-label={label}
      className={`min-h-[5.25rem] rounded-lg border px-3 py-3 shadow-sm transition-[border-color,box-shadow] duration-150 hover:shadow-card motion-reduce:transition-none ${classes.container} ${className}`}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <p className={`line-clamp-2 text-[10px] font-black uppercase leading-4 tracking-wide ${classes.label}`}>
            {label}
          </p>
          <p className="mt-1 break-words text-2xl font-black leading-none tracking-normal tabular-nums">{value}</p>
        </div>
        {icon ? (
          <span
            aria-hidden="true"
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${classes.icon}`}
          >
            {icon}
          </span>
        ) : null}
      </div>
      {detail ? <p className="mt-2 line-clamp-2 text-[11px] font-semibold leading-4 text-muted-foreground">{detail}</p> : null}
    </section>
  );
}
