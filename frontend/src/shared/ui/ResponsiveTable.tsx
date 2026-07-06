import type { ReactNode } from "react";

interface ResponsiveTableProps {
  children: ReactNode;
  showAt?: "md" | "lg";
  className?: string;
}

const showClasses = {
  md: "hidden md:block",
  lg: "hidden lg:block",
};

export function ResponsiveTable({ children, showAt = "lg", className = "" }: ResponsiveTableProps) {
  return <div className={`overflow-auto ${showClasses[showAt]} miniapp-table-scroll ${className}`}>{children}</div>;
}
