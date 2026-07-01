import { forwardRef, type ReactNode } from "react";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "border-foreground/10 bg-muted text-muted-foreground",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
};

interface BadgeProps {
  tone?: BadgeTone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  /** Render as a button and make the badge interactive. */
  onClick?: () => void;
  title?: string;
}

/**
 * Compact semantic status badge. Presentation-only and reusable across the
 * admin panels (Parents today, Students/Teachers later). When `onClick` is
 * provided it renders as an accessible button.
 */
export const Badge = forwardRef<HTMLElement, BadgeProps>(function Badge(
  { tone = "neutral", icon, children, className = "", onClick, title },
  ref,
) {
  const base =
    "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-semibold leading-tight";
  const classes = `${base} ${toneClasses[tone]} ${className}`;

  if (onClick) {
    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        type="button"
        title={title}
        onClick={onClick}
        className={`${classes} transition-colors hover:brightness-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30`}
      >
        {icon}
        {children}
      </button>
    );
  }

  return (
    <span ref={ref as React.Ref<HTMLSpanElement>} title={title} className={classes}>
      {icon}
      {children}
    </span>
  );
});
