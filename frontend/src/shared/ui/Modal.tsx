import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { uiLayers } from "@/shared/ui/layers";

type ModalSize = "sm" | "md" | "lg" | "xl" | "wide";
type ModalDesktopPlacement = "center" | "right";

interface ModalProps {
  open?: boolean;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  onClose: () => void;
  size?: ModalSize;
  desktopPlacement?: ModalDesktopPlacement;
  closeOnOutsideClick?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
  panelClassName?: string;
}

let bodyLockCount = 0;
let previousBodyOverflow = "";

function lockBodyScroll() {
  if (typeof document === "undefined") {
    return () => {};
  }
  if (bodyLockCount === 0) {
    previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
  bodyLockCount += 1;
  return () => {
    bodyLockCount = Math.max(0, bodyLockCount - 1);
    if (bodyLockCount === 0) {
      document.body.style.overflow = previousBodyOverflow;
    }
  };
}

const sizeClass: Record<ModalSize, string> = {
  sm: "sm:max-w-md",
  md: "sm:max-w-xl",
  lg: "sm:max-w-2xl",
  xl: "sm:max-w-4xl",
  wide: "sm:max-w-6xl",
};

export function Modal({
  open = true,
  title,
  subtitle,
  children,
  onClose,
  size = "lg",
  desktopPlacement = "center",
  closeOnOutsideClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  panelClassName = "",
}: ModalProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    return lockBodyScroll();
  }, [open]);

  useEffect(() => {
    if (!open || !closeOnEscape) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.stopPropagation();
      onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [closeOnEscape, onClose, open]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => panelRef.current?.focus(), 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [open]);

  if (!mounted || !open) return null;

  const desktopPlacementClass =
    desktopPlacement === "right"
      ? "sm:items-stretch sm:justify-end"
      : "sm:items-center sm:justify-center";
  const desktopPanelClass =
    desktopPlacement === "right"
      ? "sm:h-full sm:max-h-none sm:rounded-none sm:rounded-l-2xl"
      : `sm:rounded-2xl ${sizeClass[size]}`;

  return createPortal(
    <div
      className={`fixed inset-0 ${uiLayers.overlay} flex items-end justify-center bg-foreground/60 backdrop-blur-[2px] animate-in fade-in duration-200 motion-reduce:animate-none ${desktopPlacementClass}`}
      style={{
        paddingTop: "calc(var(--app-top-inset) + 0.5rem)",
        paddingRight: "calc(var(--app-right-inset) + 0.5rem)",
        paddingBottom: "calc(var(--app-bottom-inset) + 0.5rem)",
        paddingLeft: "calc(var(--app-left-inset) + 0.5rem)",
      }}
      role="presentation"
      data-modal-layer="global"
      onPointerDown={(event) => {
        if (!closeOnOutsideClick || event.target !== event.currentTarget) return;
        onClose();
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className={`flex w-full flex-col overflow-hidden rounded-t-2xl bg-surface shadow-card-hover outline-none animate-in fade-in slide-in-from-bottom-4 duration-[250ms] motion-reduce:animate-none sm:fade-in sm:zoom-in-95 ${desktopPanelClass} ${panelClassName}`}
        style={{
          maxHeight: "calc(100dvh - var(--app-top-inset) - var(--app-bottom-inset) - 1rem)",
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-foreground/8 px-4 py-3">
          <div className="min-w-0">
            <h3 id={titleId} className="break-words text-sm font-bold">
              {title}
            </h3>
            {subtitle ? <p className="line-clamp-2 text-xs text-muted-foreground">{subtitle}</p> : null}
          </div>
          {showCloseButton ? (
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
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
