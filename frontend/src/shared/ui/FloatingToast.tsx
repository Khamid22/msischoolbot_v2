import { useEffect, useState } from "react";
import { CheckCircle2, Info, XCircle } from "lucide-react";

export type FloatingToastTone = "success" | "danger" | "info";

export type FloatingToastState = {
  message: string;
  tone?: FloatingToastTone;
} | null;

export function useFloatingToast(autoDismissMs = 2600) {
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

export function FloatingToast({ toast }: { toast: FloatingToastState }) {
  if (!toast?.message) return null;
  const tone = toast.tone || "success";
  const toneClass =
    tone === "danger"
      ? "bg-destructive text-destructive-foreground"
      : tone === "info"
        ? "bg-info text-white"
        : "bg-emerald-600 text-white";
  const Icon = tone === "danger" ? XCircle : tone === "info" ? Info : CheckCircle2;

  return (
    <div
      className={`fixed right-4 top-[calc(var(--app-top-inset)+4rem)] z-[70] flex max-w-[min(22rem,calc(100vw-2rem))] items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold shadow-card-hover animate-in fade-in slide-in-from-top-2 duration-150 motion-reduce:animate-none lg:top-4 ${toneClass}`}
      role={tone === "danger" ? "alert" : "status"}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="min-w-0 break-words">{toast.message}</span>
    </div>
  );
}
