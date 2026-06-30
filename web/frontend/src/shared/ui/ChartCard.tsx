import { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  children: ReactNode;
  headerActions?: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function ChartCard({ title, subtitle, icon, children, headerActions, className = "", bodyClassName = "" }: ChartCardProps) {
  return (
    <div className={`overflow-hidden rounded-lg border border-foreground/10 bg-surface shadow-card ${className}`}>
      <div className="flex shrink-0 flex-wrap items-start justify-between gap-2 px-3 py-2.5 sm:px-4 sm:py-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-display flex min-w-0 items-center gap-1.5 text-sm font-bold leading-tight">
            {icon}
            <span className="min-w-0 break-words">{title}</span>
          </h3>
          {subtitle && <p className="mt-0.5 break-words text-xs leading-snug text-muted-foreground">{subtitle}</p>}
        </div>
        {headerActions ? <div className="flex max-w-full shrink-0 flex-wrap items-center gap-2">{headerActions}</div> : null}
      </div>
      <div className={`min-w-0 px-3 pb-3 sm:px-4 sm:pb-4 ${bodyClassName}`}>{children}</div>
    </div>
  );
}
