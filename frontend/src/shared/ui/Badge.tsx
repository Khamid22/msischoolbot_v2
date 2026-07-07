import { forwardRef, type ReactNode } from "react";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  success: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/35 bg-warning/15 text-warning-foreground",
  danger: "border-destructive/25 bg-destructive/10 text-destructive",
  info: "border-info/25 bg-info/10 text-info",
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
    "inline-flex min-h-6 max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold leading-tight";
  const classes = `${base} ${toneClasses[tone]} ${className}`;

  if (onClick) {
    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        type="button"
        title={title}
        onClick={onClick}
        className={`${classes} transition-[transform,filter,box-shadow] duration-150 hover:brightness-95 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none motion-reduce:active:scale-100`}
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
