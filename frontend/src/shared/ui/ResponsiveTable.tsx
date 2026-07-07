import type { ReactNode } from "react";

interface ResponsiveTableProps {
  children: ReactNode;
  showAt?: "md" | "lg";
  className?: string;
  ariaLabel?: string;
}

const showClasses = {
  md: "hidden md:block",
  lg: "hidden lg:block",
};

export function ResponsiveTable({
  children,
  showAt = "lg",
  className = "",
  ariaLabel = "Data table",
}: ResponsiveTableProps) {
  return (
    <div
      aria-label={ariaLabel}
      className={`overflow-auto ${showClasses[showAt]} miniapp-table-scroll rounded-lg border border-border bg-card shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${className}`}
      role="region"
      tabIndex={0}
    >
      {children}
    </div>
  );
}
