import type { ReactNode } from "react";
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
    <div className="flex min-h-[5rem] min-w-0 flex-col justify-between gap-2 p-3">
      <p className={`flex min-w-0 items-center gap-1.5 text-[11px] font-black uppercase leading-4 tracking-wide ${colorClass}`}>
        {icon}
        <span className="min-w-0 line-clamp-2">{title}</span>
      </p>
      <h3 className="font-display break-words text-xl font-black leading-none tracking-normal sm:text-2xl">{value}</h3>
    </div>
  );

  const baseClass = `overflow-hidden rounded-lg border border-border/80 bg-card text-card-foreground shadow-card ${motion.card}`;

  if (href) {
    return (
      <a
        href={href}
        aria-label={`${title}: ${value}`}
        className={`${baseClass} block focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35`}
      >
        {content}
      </a>
    );
  }

  return <div className={baseClass} aria-label={`${title}: ${value}`}>{content}</div>;
}
