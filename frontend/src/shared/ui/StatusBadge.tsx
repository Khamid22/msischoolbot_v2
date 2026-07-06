import type { ReactNode } from "react";
import { Badge, type BadgeTone } from "@/shared/ui/Badge";
import { statusLabel, statusTone } from "@/shared/ui/statusTones";

interface StatusBadgeProps {
  /**
   * Known status key or label ("active", "In Training", "needs_support", …).
   * Supplies both the display text and the tone; `children`/`tone` override.
   */
  status?: string;
  children?: ReactNode;
  tone?: BadgeTone;
  icon?: ReactNode;
  className?: string;
  title?: string;
}

export function StatusBadge({ status, children, tone, icon, className = "", title }: StatusBadgeProps) {
  const resolvedTone = tone ?? (status ? statusTone(status) : "neutral");
  const content = children ?? (status ? statusLabel(status) : null);

  return (
    <Badge tone={resolvedTone} icon={icon} title={title} className={`max-w-full rounded-full px-2 py-0.5 font-black uppercase tracking-wide ${className}`}>
      <span className="truncate">{content}</span>
    </Badge>
  );
}
