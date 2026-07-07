import type { ReactNode } from "react";

type MetricCardTone = "default" | "success" | "warning" | "info" | "danger";
type MetricCardDensity = "default" | "compact";

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
  density?: MetricCardDensity;
  className?: string;
}

const densityClasses: Record<
  MetricCardDensity,
  { section: string; label: string; value: string; detail: string; icon: string }
> = {
  default: {
    section: "min-h-[5.25rem] px-3 py-3",
    label: "line-clamp-2 text-[10px] leading-4",
    value: "mt-1 break-words text-2xl",
    detail: "mt-2 line-clamp-2 text-[11px] leading-4",
    icon: "h-8 w-8",
  },
  compact: {
    section: "min-h-[3.875rem] px-2 py-2",
    label: "truncate text-[9px] leading-3",
    value: "mt-0.5 truncate text-lg sm:text-xl",
    detail: "mt-0.5 truncate text-[10px] leading-3",
    icon: "h-6 w-6",
  },
};

export function MetricCard({
  label,
  value,
  detail,
  icon,
  tone = "default",
  density = "default",
  className = "",
}: MetricCardProps) {
  const classes = toneClasses[tone];
  const densityClass = densityClasses[density];

  return (
    <section
      aria-label={label}
      className={`rounded-lg border shadow-sm transition-[border-color,box-shadow] duration-150 hover:shadow-card motion-reduce:transition-none ${densityClass.section} ${classes.container} ${className}`}
    >
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0">
          <p className={`font-black uppercase tracking-wide ${densityClass.label} ${classes.label}`}>
            {label}
          </p>
          <p className={`font-black leading-none tracking-normal tabular-nums ${densityClass.value}`}>{value}</p>
        </div>
        {icon ? (
          <span
            aria-hidden="true"
            className={`mt-0.5 flex shrink-0 items-center justify-center rounded-lg ${densityClass.icon} ${classes.icon}`}
          >
            {icon}
          </span>
        ) : null}
      </div>
      {detail ? <p className={`font-semibold text-muted-foreground ${densityClass.detail}`}>{detail}</p> : null}
    </section>
  );
}
