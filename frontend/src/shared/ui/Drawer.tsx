import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { uiLayers } from "@/shared/ui/layers";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  /** Top-right slot next to the close button (e.g. a status badge). */
  headerExtra?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  /** Width of the panel on >= sm screens. Full-screen below that. */
  widthClass?: string;
}

/**
 * Accessible right-side drawer. Full-screen on narrow viewports, a fixed-width
 * panel on laptops/desktops. Closes on Escape and backdrop click, locks body
 * scroll, and moves focus into the panel on open. Reusable across admin panels.
 */
export function Drawer({
  open,
  onClose,
  title,
  description,
  headerExtra,
  footer,
  children,
  widthClass = "sm:max-w-md",
}: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const headingId = useId();

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    // Move focus into the panel so keyboard users land inside the dialog.
    const focusTimer = window.setTimeout(() => {
      panelRef.current?.focus();
    }, 0);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      window.clearTimeout(focusTimer);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className={`fixed inset-0 ${uiLayers.overlay}`} role="dialog" aria-modal="true" aria-labelledby={headingId}>
      <button
        type="button"
        aria-label="Close panel"
        onClick={onClose}
        className="absolute inset-0 h-full w-full cursor-default bg-foreground/50 backdrop-blur-[1px] animate-in fade-in duration-200 motion-reduce:animate-none"
      />
      <div
        ref={panelRef}
        tabIndex={-1}
        className={`absolute inset-0 flex w-full flex-col bg-surface shadow-card-hover outline-none sm:inset-y-0 sm:right-0 sm:left-auto sm:w-full ${widthClass} animate-in slide-in-from-right duration-300 motion-reduce:animate-none`}
        style={{
          paddingTop: "var(--app-top-inset)",
          paddingRight: "var(--app-right-inset)",
          paddingBottom: "var(--app-bottom-inset)",
          paddingLeft: "var(--app-left-inset)",
        }}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-foreground/8 px-3 py-3 sm:px-5">
          <div className="min-w-0 flex-1">
            <h2 id={headingId} className="font-display break-words text-base font-bold leading-tight">
              {title}
            </h2>
            {description ? (
              <div className="mt-0.5 break-words text-xs text-muted-foreground">{description}</div>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {headerExtra}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="miniapp-scroll flex-1 bg-surface px-3 py-3 sm:px-5 sm:py-4">{children}</div>

        {footer ? (
          <div className="shrink-0 border-t border-foreground/8 bg-surface/95 px-3 py-3 shadow-[0_-8px_24px_hsl(var(--foreground)/0.06)] backdrop-blur sm:px-5">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
