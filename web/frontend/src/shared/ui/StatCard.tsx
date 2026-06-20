import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string;
  icon?: ReactNode;
  href?: string;
  colorClass?: string;
}

export function StatCard({ title, value, icon, href, colorClass = "text-foreground" }: StatCardProps) {
  const content = (
    <div className="flex min-h-[5.25rem] flex-col justify-between gap-2 p-3 sm:p-3.5">
      <p className={`flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground ${colorClass}`}>
        {icon}
        {title}
      </p>
      <h3 className="font-display text-xl font-bold leading-none sm:text-2xl">{value}</h3>
    </div>
  );

  const baseClass = "rounded-lg border border-foreground/10 bg-surface shadow-card transition-[box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-card-hover";

  if (href) {
    return (
      <a href={href} className={`${baseClass} block`}>
        {content}
      </a>
    );
  }

  return <div className={baseClass}>{content}</div>;
}
