import { useEffect, useId, useRef, type ReactNode } from "react";
import { TriangleAlert } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Accessible confirmation dialog for dangerous or irreversible actions.
 * Uses role="alertdialog", focuses the confirm button on open, closes on
 * Escape, and supports a busy state to prevent double submits.
 */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const headingId = useId();
  const bodyId = useId();

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        event.stopPropagation();
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    const timer = window.setTimeout(() => confirmRef.current?.focus(), 0);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      window.clearTimeout(timer);
    };
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-foreground/60 p-4"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby={headingId}
      aria-describedby={bodyId}
    >
      <button
        type="button"
        aria-label="Cancel"
        onClick={() => !busy && onCancel()}
        className="absolute inset-0 h-full w-full cursor-default"
      />
      <div className="relative w-full max-w-sm overflow-hidden rounded-xl bg-surface shadow-card-hover">
        <div className="flex items-start gap-3 px-5 pt-5">
          {danger ? (
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
              <TriangleAlert className="h-5 w-5" />
            </span>
          ) : null}
          <div className="min-w-0">
            <h3 id={headingId} className="text-sm font-bold">
              {title}
            </h3>
            <div id={bodyId} className="mt-1 text-sm leading-5 text-muted-foreground">
              {message}
            </div>
          </div>
        </div>

        <div className="mt-5 flex gap-2 px-5 pb-5">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="h-10 flex-1 rounded-lg border border-foreground/10 text-sm font-bold hover:bg-muted disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={`h-10 flex-1 rounded-lg text-sm font-bold text-white disabled:opacity-50 ${
              danger ? "bg-destructive hover:bg-destructive/90" : "bg-primary text-primary-foreground hover:bg-primary/90"
            }`}
          >
            {busy ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
