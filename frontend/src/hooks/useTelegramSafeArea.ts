import { useEffect, useState } from "react";

export interface TelegramSafeInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

interface TelegramWebApp {
  safeAreaInset?: Partial<TelegramSafeInsets>;
  contentSafeAreaInset?: Partial<TelegramSafeInsets>;
  onEvent?: (eventType: string, callback: () => void) => void;
  offEvent?: (eventType: string, callback: () => void) => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

const TELEGRAM_SAFE_AREA_EVENTS = ["safeAreaChanged", "contentSafeAreaChanged", "fullscreenChanged"] as const;

const ZERO_INSETS: TelegramSafeInsets = {
  top: 0,
  right: 0,
  bottom: 0,
  left: 0,
};

function normalizeInset(value: unknown) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue) || numericValue <= 0) {
    return 0;
  }

  return Math.round(numericValue);
}

function readMergedInsets(webApp?: TelegramWebApp): TelegramSafeInsets {
  const safeAreaInset = webApp?.safeAreaInset || {};
  const contentSafeAreaInset = webApp?.contentSafeAreaInset || {};

  return {
    top: Math.max(normalizeInset(safeAreaInset.top), normalizeInset(contentSafeAreaInset.top)),
    right: Math.max(normalizeInset(safeAreaInset.right), normalizeInset(contentSafeAreaInset.right)),
    bottom: Math.max(normalizeInset(safeAreaInset.bottom), normalizeInset(contentSafeAreaInset.bottom)),
    left: Math.max(normalizeInset(safeAreaInset.left), normalizeInset(contentSafeAreaInset.left)),
  };
}

function writeCssSafeAreaVars(insets: TelegramSafeInsets) {
  const root = document.documentElement;

  root.style.setProperty("--safe-top", `${insets.top}px`);
  root.style.setProperty("--safe-right", `${insets.right}px`);
  root.style.setProperty("--safe-bottom", `${insets.bottom}px`);
  root.style.setProperty("--safe-left", `${insets.left}px`);
}

function areInsetsEqual(left: TelegramSafeInsets, right: TelegramSafeInsets) {
  return (
    left.top === right.top &&
    left.right === right.right &&
    left.bottom === right.bottom &&
    left.left === right.left
  );
}

export function useTelegramSafeArea() {
  const [insets, setInsets] = useState<TelegramSafeInsets>(ZERO_INSETS);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    if (!webApp) {
      return undefined;
    }

    const syncInsets = () => {
      const nextInsets = readMergedInsets(webApp);
      writeCssSafeAreaVars(nextInsets);
      setInsets((currentInsets) => (areInsetsEqual(currentInsets, nextInsets) ? currentInsets : nextInsets));
    };

    syncInsets();
    TELEGRAM_SAFE_AREA_EVENTS.forEach((eventName) => webApp.onEvent?.(eventName, syncInsets));

    return () => {
      TELEGRAM_SAFE_AREA_EVENTS.forEach((eventName) => webApp.offEvent?.(eventName, syncInsets));
    };
  }, []);

  return insets;
}
