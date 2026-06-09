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
    <div className="overflow-hidden rounded-lg border border-foreground/10 bg-surface shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-2 px-3.5 py-3 sm:px-4">
        <div className="min-w-0">
          <h3 className="font-display flex items-center gap-1.5 text-sm font-bold">
            {icon}
            {title}
          </h3>
          {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {headerActions}
      </div>
      <div className="px-3.5 pb-3.5 sm:px-4 sm:pb-4">{children}</div>
    </div>
  );
}
