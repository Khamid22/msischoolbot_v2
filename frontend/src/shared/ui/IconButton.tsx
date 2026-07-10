import type { ReactNode } from "react";
import { motion } from "@/shared/lib/motion";

interface IconButtonProps {
  label: string;
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  className?: string;
}

export function IconButton({ label, children, onClick, disabled = false, danger = false, className = "" }: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex h-11 min-h-11 w-11 min-w-11 shrink-0 items-center justify-center rounded-lg border border-border bg-background shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 disabled:cursor-not-allowed disabled:opacity-50 ${motion.button} ${
        danger
          ? "text-destructive hover:border-destructive/25 hover:bg-destructive/10"
          : "text-muted-foreground hover:border-primary/20 hover:bg-muted hover:text-foreground"
      } ${className}`}
    >
      {children}
    </button>
  );
}
