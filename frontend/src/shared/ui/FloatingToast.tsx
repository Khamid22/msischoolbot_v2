import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { uiLayers } from "@/shared/ui/layers";

/** "danger" is a legacy alias of "error"; both render the error style. */
export type FloatingToastTone = "success" | "error" | "warning" | "info" | "danger";

export type FloatingToastState = {
  message: string;
  tone?: FloatingToastTone;
} | null;

export function useFloatingToast(autoDismissMs = 3500) {
  const [toast, setToast] = useState<FloatingToastState>(null);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), autoDismissMs);
    return () => window.clearTimeout(timer);
  }, [autoDismissMs, toast]);

  function showToast(message: string, tone: FloatingToastTone = "success") {
    setToast({ message, tone });
  }

  function clearToast() {
    setToast(null);
  }

  return { toast, showToast, clearToast };
}

const toneStyles: Record<"success" | "error" | "warning" | "info", { className: string; icon: typeof Info }> = {
  success: { className: "bg-emerald-600 text-white", icon: CheckCircle2 },
  error: { className: "bg-destructive text-destructive-foreground", icon: XCircle },
  warning: { className: "bg-amber-500 text-white", icon: AlertTriangle },
  info: { className: "bg-info text-white", icon: Info },
};

/**
 * Compact feedback toast. Sits above the mobile bottom nav on phones and in
 * the top-right corner on desktop; auto-dismisses (see useFloatingToast) and
 * offers a manual close button when `onClose` is provided. Never blocks the
 * UI: single line of small text, pointer events limited to the toast itself.
 */
export function FloatingToast({ toast, onClose }: { toast: FloatingToastState; onClose?: () => void }) {
  if (!toast?.message) return null;
  const tone = toast.tone === "danger" ? "error" : toast.tone || "success";
  const { className, icon: Icon } = toneStyles[tone];

  return createPortal(
    <div
      className={`fixed left-4 right-4 ${uiLayers.toast} bottom-[calc(var(--app-bottom-inset)+5.5rem)] ml-auto flex w-fit max-w-[min(22rem,calc(100vw-2rem))] items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold shadow-card-hover animate-in fade-in slide-in-from-bottom-2 duration-200 motion-reduce:animate-none lg:bottom-auto lg:left-auto lg:top-4 lg:slide-in-from-top-2 ${className}`}
      role={tone === "error" ? "alert" : "status"}
      aria-live={tone === "error" ? "assertive" : "polite"}
      aria-atomic="true"
      data-toast-tone={tone}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="min-w-0 break-words">{toast.message}</span>
      {onClose ? (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss notification"
          className="ml-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md hover:bg-white/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      ) : null}
    </div>,
    document.body,
  );
}
