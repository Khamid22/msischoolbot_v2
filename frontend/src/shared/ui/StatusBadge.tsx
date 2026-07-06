import type { ReactNode } from "react";
import { Badge, type BadgeTone } from "@/shared/ui/Badge";

interface StatusBadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
  icon?: ReactNode;
  className?: string;
  title?: string;
}

export function StatusBadge({ children, tone = "neutral", icon, className = "", title }: StatusBadgeProps) {
  return (
    <Badge tone={tone} icon={icon} title={title} className={`max-w-full rounded-full px-2 py-0.5 font-black uppercase tracking-wide ${className}`}>
      <span className="truncate">{children}</span>
    </Badge>
  );
}
