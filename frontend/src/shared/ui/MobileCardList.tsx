import type { ReactNode } from "react";

interface MobileCardListProps {
  children: ReactNode;
  hideAt?: "md" | "lg";
  className?: string;
}

const hideClasses = {
  md: "md:hidden",
  lg: "lg:hidden",
};

export function MobileCardList({ children, hideAt = "lg", className = "" }: MobileCardListProps) {
  return <div className={`space-y-3 ${hideClasses[hideAt]} ${className}`}>{children}</div>;
}
