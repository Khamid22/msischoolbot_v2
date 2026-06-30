import { ReactNode } from "react";
import { motion } from "@/shared/lib/motion";

interface StatCardProps {
  title: string;
  value: string;
  icon?: ReactNode;
  href?: string;
  colorClass?: string;
}

export function StatCard({ title, value, icon, href, colorClass = "text-foreground" }: StatCardProps) {
  const content = (
    <div className="flex min-h-[4.5rem] flex-col justify-between gap-1.5 p-2.5 sm:min-h-[4.75rem] sm:p-3">
      <p className={`flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground ${colorClass}`}>
        {icon}
        {title}
      </p>
      <h3 className="font-display text-lg font-bold leading-none sm:text-xl">{value}</h3>
    </div>
  );

  const baseClass = `rounded-lg border border-foreground/10 bg-surface shadow-card ${motion.card}`;

  if (href) {
    return (
      <a href={href} className={`${baseClass} block`}>
        {content}
      </a>
    );
  }

  return <div className={baseClass}>{content}</div>;
}
