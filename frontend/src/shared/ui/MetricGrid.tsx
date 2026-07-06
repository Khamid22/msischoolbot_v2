import type { ReactNode } from "react";

interface MetricGridProps {
  children: ReactNode;
  className?: string;
}

/**
 * Responsive container for MetricCard/StatCard rows: 1 column on very narrow
 * screens, 2 columns on phones and tablets, 4 on laptops and up. Keep cards
 * compact — this grid is for KPI strips, not content sections.
 */
export function MetricGrid({ children, className = "" }: MetricGridProps) {
  return (
    <div className={`grid grid-cols-1 gap-2 min-[400px]:grid-cols-2 sm:gap-3 lg:grid-cols-4 ${className}`}>
      {children}
    </div>
  );
}
