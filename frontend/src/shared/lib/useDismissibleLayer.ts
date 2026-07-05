import { useEffect, useRef, type RefObject } from "react";

type DismissEvent = KeyboardEvent | PointerEvent;

interface UseDismissibleLayerOptions {
  enabled?: boolean;
  onDismiss: (event: DismissEvent) => void;
  refs?: Array<RefObject<HTMLElement>>;
  dismissOnEscape?: boolean;
  dismissOnOutsidePointer?: boolean;
}

function containsTarget(ref: RefObject<HTMLElement>, target: EventTarget | null) {
  return Boolean(target instanceof Node && ref.current?.contains(target));
}

export function useDismissibleLayer<T extends HTMLElement>({
  enabled = true,
  onDismiss,
  refs,
  dismissOnEscape = true,
  dismissOnOutsidePointer = true,
}: UseDismissibleLayerOptions) {
  const layerRef = useRef<T>(null);

  useEffect(() => {
    if (!enabled) return;

    const activeRefs = refs?.length ? refs : [layerRef as RefObject<HTMLElement>];

    function handlePointerDown(event: PointerEvent) {
      if (!dismissOnOutsidePointer) return;
      if (activeRefs.some((ref) => containsTarget(ref, event.target))) return;
      onDismiss(event);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (!dismissOnEscape || event.key !== "Escape") return;
      onDismiss(event);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [dismissOnEscape, dismissOnOutsidePointer, enabled, onDismiss, refs]);

  return layerRef;
}
