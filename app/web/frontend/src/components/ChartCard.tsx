import { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  children: ReactNode;
  headerActions?: ReactNode;
}

export function ChartCard({ title, subtitle, icon, children, headerActions }: ChartCardProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-foreground/10 bg-surface shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-2 p-4 pb-2 sm:p-5 sm:pb-3">
        <div>
          <h3 className="font-display text-sm font-bold flex items-center gap-1.5 sm:text-base">
            {icon}
            {title}
          </h3>
          {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
        </div>
        {headerActions}
      </div>
      <div className="p-4 pt-0 sm:p-5 sm:pt-0">{children}</div>
    </div>
  );
}
