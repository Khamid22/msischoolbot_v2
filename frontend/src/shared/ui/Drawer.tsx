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
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const headingId = useId();
  const descriptionId = useId();

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => !element.hasAttribute("hidden") && element.getAttribute("aria-hidden") !== "true");
      if (!focusable.length) {
        event.preventDefault();
        panelRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    // Move focus to the first control, falling back to the panel itself.
    const focusTimer = window.setTimeout(() => {
      const firstControl = panelRef.current?.querySelector<HTMLElement>(
        '[data-drawer-content] input:not([disabled]), [data-drawer-content] select:not([disabled]), [data-drawer-content] textarea:not([disabled]), [data-drawer-content] button:not([disabled]), [data-drawer-content] a[href]',
      );
      (firstControl || panelRef.current)?.focus();
    }, 0);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      window.clearTimeout(focusTimer);
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className={`fixed inset-0 ${uiLayers.overlay}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      aria-describedby={description ? descriptionId : undefined}
    >
      <button
        type="button"
        aria-label="Close panel"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 h-full w-full cursor-default bg-foreground/50 backdrop-blur-[0.0625rem] animate-in fade-in duration-200 motion-reduce:animate-none"
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
              <div id={descriptionId} className="mt-0.5 break-words text-xs text-muted-foreground">{description}</div>
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

        <div data-drawer-content className="miniapp-scroll flex-1 bg-surface px-3 py-3 sm:px-5 sm:py-4">{children}</div>

        {footer ? (
          <div className="shrink-0 border-t border-foreground/8 bg-surface/95 px-3 py-3 shadow-[0_-0.5rem_1.5rem_hsl(var(--foreground)/0.06)] backdrop-blur sm:px-5">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
