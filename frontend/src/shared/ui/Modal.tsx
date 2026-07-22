import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { uiLayers } from "@/shared/ui/layers";
import { useBodyScrollLock } from "@/shared/ui/useBodyScrollLock";

type ModalSize = "sm" | "md" | "lg" | "xl" | "wide";
type ModalDesktopPlacement = "center" | "right";
type ModalMobileMode = "sheet" | "fullscreen";

interface ModalProps {
  open?: boolean;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  onClose: () => void;
  size?: ModalSize;
  desktopPlacement?: ModalDesktopPlacement;
  mobileMode?: ModalMobileMode;
  closeOnOutsideClick?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
  panelClassName?: string;
  initialFocusSelector?: string;
}

const sizeClass: Record<ModalSize, string> = {
  sm: "sm:max-w-md",
  md: "sm:max-w-xl",
  lg: "sm:max-w-2xl",
  xl: "sm:max-w-4xl",
  wide: "sm:max-w-6xl",
};

export function ModalHeader({
  title,
  subtitle,
  titleId,
  onClose,
  showCloseButton = true,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  titleId?: string;
  onClose?: () => void;
  showCloseButton?: boolean;
}) {
  return (
    <div className="flex shrink-0 items-center justify-between gap-3 border-b border-foreground/8 px-4 py-3">
      <div className="min-w-0">
        <h3 id={titleId} className="break-words text-sm font-bold">
          {title}
        </h3>
        {subtitle ? <p className="line-clamp-2 text-xs text-muted-foreground">{subtitle}</p> : null}
      </div>
      {showCloseButton && onClose ? (
        <button
          type="button"
          onClick={onClose}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      ) : null}
    </div>
  );
}

export function ModalBody({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`miniapp-scroll min-h-0 flex-1 overflow-y-auto px-4 py-4 pb-[calc(var(--app-bottom-inset)+1rem)] ${className}`}>
      {children}
    </div>
  );
}

export function ModalFooter({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`shrink-0 border-t border-foreground/8 bg-surface/95 px-4 py-3 pb-[calc(var(--app-bottom-inset)+0.75rem)] shadow-[0_-0.5rem_1.5rem_hsl(var(--foreground)/0.06)] backdrop-blur sm:pb-3 ${className}`}
    >
      {children}
    </div>
  );
}

export function Modal({
  open = true,
  title,
  subtitle,
  children,
  onClose,
  size = "lg",
  desktopPlacement = "center",
  mobileMode = "sheet",
  closeOnOutsideClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  panelClassName = "",
  initialFocusSelector,
}: ModalProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useBodyScrollLock(open);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    returnFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && closeOnEscape) {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => !element.hasAttribute("hidden"));
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
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      window.setTimeout(() => returnFocusRef.current?.focus(), 0);
    };
  }, [closeOnEscape, open]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => {
      const preferred = (initialFocusSelector
        ? panelRef.current?.querySelector<HTMLElement>(initialFocusSelector)
        : null)
        || panelRef.current?.querySelector<HTMLElement>("[autofocus]")
        || panelRef.current?.querySelector<HTMLElement>(
          'input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])',
        );
      (preferred || panelRef.current)?.focus();
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [initialFocusSelector, open]);

  if (!mounted || !open) return null;

  const desktopPlacementClass =
    desktopPlacement === "right"
      ? "sm:items-stretch sm:justify-end"
      : "sm:items-center sm:justify-center";
  const desktopPanelClass =
    desktopPlacement === "right"
      ? "sm:h-full sm:max-h-none sm:rounded-none sm:rounded-l-2xl"
      : `sm:rounded-2xl ${sizeClass[size]}`;
  const mobilePanelClass =
    mobileMode === "fullscreen"
      ? "h-full rounded-none"
      : "rounded-t-2xl";

  return createPortal(
    <div
      className={`fixed inset-0 ${uiLayers.overlay} flex items-end justify-center bg-foreground/60 backdrop-blur-[0.125rem] animate-in fade-in duration-200 motion-reduce:animate-none ${desktopPlacementClass}`}
      style={{
        paddingTop: "calc(var(--app-top-inset) + 0.5rem)",
        paddingRight: "calc(var(--app-right-inset) + 0.5rem)",
        paddingBottom: "calc(var(--app-bottom-inset) + 0.5rem)",
        paddingLeft: "calc(var(--app-left-inset) + 0.5rem)",
      }}
      role="presentation"
      data-modal-layer="global"
      data-modal-backdrop="true"
      onPointerDown={(event) => {
        if (!closeOnOutsideClick || event.target !== event.currentTarget) return;
        onClose();
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className={`flex w-full flex-col overflow-hidden bg-surface shadow-card-hover outline-none animate-in fade-in slide-in-from-bottom-4 duration-200 motion-reduce:animate-none sm:fade-in sm:zoom-in-95 ${mobilePanelClass} ${desktopPanelClass} ${panelClassName}`}
        style={{
          maxHeight: "calc(100dvh - var(--app-top-inset) - var(--app-bottom-inset) - 1rem)",
        }}
        data-mobile-mode={mobileMode}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <ModalHeader title={title} subtitle={subtitle} titleId={titleId} onClose={onClose} showCloseButton={showCloseButton} />
        {children}
      </div>
    </div>,
    document.body,
  );
}

/**
 * Mobile-first sheet: same global modal layer as Modal (portal, backdrop,
 * scroll lock, Escape/outside-click close), rendered as a slide-up bottom
 * sheet on phones and a centered dialog on larger screens.
 */
export function BottomSheet(props: ModalProps) {
  return <Modal size="md" {...props} desktopPlacement="center" />;
}
