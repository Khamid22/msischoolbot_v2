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
    <div className="flex flex-col gap-1.5 p-4 sm:p-5">
      <p className={`text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5 ${colorClass}`}>
        {icon}
        {title}
      </p>
      <h3 className="font-display text-2xl font-bold sm:text-3xl">{value}</h3>
    </div>
  );

  const baseClass = "rounded-xl bg-surface shadow-card transition-all duration-200 hover:shadow-card-hover";

  if (href) {
    return (
      <a href={href} className={`${baseClass} block`}>
        {content}
      </a>
    );
  }

  return <div className={baseClass}>{content}</div>;
}
