import { useEffect } from "react";

let bodyLockCount = 0;
let previousBodyOverflow = "";

export function useBodyScrollLock(active: boolean) {
  useEffect(() => {
    if (!active || typeof document === "undefined") return;

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
  }, [active]);
}
