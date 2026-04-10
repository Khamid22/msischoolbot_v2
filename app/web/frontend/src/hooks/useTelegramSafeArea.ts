import { useEffect, useState } from "react";

export interface SafeInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

const ZERO_INSETS: SafeInsets = { top: 0, right: 0, bottom: 0, left: 0 };

type TelegramInsets = Partial<Record<keyof SafeInsets, number>>;

type TelegramWebApp = {
  safeAreaInset?: TelegramInsets;
  contentSafeAreaInset?: TelegramInsets;
  onEvent?: (event: string, callback: () => void) => void;
  offEvent?: (event: string, callback: () => void) => void;
};

const TelegramSafeAreaEvents = [
  "safeAreaChanged",
  "contentSafeAreaChanged",
  "fullscreenChanged",
] as const;

const SafeAreaCssVars = [
  "--safe-top",
  "--safe-right",
  "--safe-bottom",
  "--safe-left",
  "--tg-safe-area-inset-top",
  "--tg-safe-area-inset-right",
  "--tg-safe-area-inset-bottom",
  "--tg-safe-area-inset-left",
  "--tg-safe-area-top",
  "--tg-safe-area-right",
  "--tg-safe-area-bottom",
  "--tg-safe-area-left",
  "--tg-content-safe-area-inset-top",
  "--tg-content-safe-area-inset-right",
  "--tg-content-safe-area-inset-bottom",
  "--tg-content-safe-area-inset-left",
  "--tg-content-safe-area-top",
  "--tg-content-safe-area-right",
  "--tg-content-safe-area-bottom",
  "--tg-content-safe-area-left",
] as const;

const toNumberInset = (rawValue: unknown): number => {
  const numericValue = Number(rawValue);
  if (!Number.isFinite(numericValue) || numericValue <= 0) {
    return 0;
  }
  return numericValue;
};

const toPixel = (value: number): string => `${Math.max(0, Math.round(value))}px`;

const writeCssVar = (name: string, value: number) => {
  const root = document.documentElement;
  const cssValue = toPixel(value);
  if (root.style.getPropertyValue(name) === cssValue) {
    return;
  }
  root.style.setProperty(name, cssValue);
};

const sameInsets = (left: SafeInsets, right: SafeInsets): boolean =>
  left.top === right.top &&
  left.right === right.right &&
  left.bottom === right.bottom &&
  left.left === right.left;

const readMergedInsets = (webApp?: TelegramWebApp): SafeInsets => {
  const safeArea = webApp?.safeAreaInset ?? {};
  const contentSafeArea = webApp?.contentSafeAreaInset ?? {};
  return {
    top: Math.max(toNumberInset(safeArea.top), toNumberInset(contentSafeArea.top)),
    right: Math.max(toNumberInset(safeArea.right), toNumberInset(contentSafeArea.right)),
    bottom: Math.max(toNumberInset(safeArea.bottom), toNumberInset(contentSafeArea.bottom)),
    left: Math.max(toNumberInset(safeArea.left), toNumberInset(contentSafeArea.left)),
  };
};

const syncCssSafeAreaVars = (webApp: TelegramWebApp, mergedInsets: SafeInsets) => {
  const safeArea = webApp?.safeAreaInset ?? {};
  const contentSafeArea = webApp?.contentSafeAreaInset ?? {};

  const safeTop = toNumberInset(safeArea.top);
  const safeRight = toNumberInset(safeArea.right);
  const safeBottom = toNumberInset(safeArea.bottom);
  const safeLeft = toNumberInset(safeArea.left);
  const contentTop = toNumberInset(contentSafeArea.top);
  const contentRight = toNumberInset(contentSafeArea.right);
  const contentBottom = toNumberInset(contentSafeArea.bottom);
  const contentLeft = toNumberInset(contentSafeArea.left);

  writeCssVar("--safe-top", mergedInsets.top);
  writeCssVar("--safe-right", mergedInsets.right);
  writeCssVar("--safe-bottom", mergedInsets.bottom);
  writeCssVar("--safe-left", mergedInsets.left);

  // Device-level insets.
  writeCssVar("--tg-safe-area-inset-top", safeTop);
  writeCssVar("--tg-safe-area-inset-right", safeRight);
  writeCssVar("--tg-safe-area-inset-bottom", safeBottom);
  writeCssVar("--tg-safe-area-inset-left", safeLeft);

  // Backward-compatible aliases used by some legacy styles/scripts.
  writeCssVar("--tg-safe-area-top", safeTop);
  writeCssVar("--tg-safe-area-right", safeRight);
  writeCssVar("--tg-safe-area-bottom", safeBottom);
  writeCssVar("--tg-safe-area-left", safeLeft);

  // Telegram content-level insets.
  writeCssVar("--tg-content-safe-area-inset-top", contentTop);
  writeCssVar("--tg-content-safe-area-inset-right", contentRight);
  writeCssVar("--tg-content-safe-area-inset-bottom", contentBottom);
  writeCssVar("--tg-content-safe-area-inset-left", contentLeft);

  // Backward-compatible aliases.
  writeCssVar("--tg-content-safe-area-top", contentTop);
  writeCssVar("--tg-content-safe-area-right", contentRight);
  writeCssVar("--tg-content-safe-area-bottom", contentBottom);
  writeCssVar("--tg-content-safe-area-left", contentLeft);
};

const clearCssSafeAreaVars = () => {
  const root = document.documentElement;
  SafeAreaCssVars.forEach((varName) => {
    root.style.removeProperty(varName);
  });
};

const getTelegramWebApp = (): TelegramWebApp | undefined =>
  (window as Window & { Telegram?: { WebApp?: TelegramWebApp } }).Telegram?.WebApp;

export function useTelegramSafeArea(): SafeInsets {
  const [mergedInsets, setMergedInsets] = useState<SafeInsets>(ZERO_INSETS);

  useEffect(() => {
    const webApp = getTelegramWebApp();

    const updateInsets = () => {
      const currentWebApp = getTelegramWebApp() || webApp;
      if (!currentWebApp) {
        clearCssSafeAreaVars();
        setMergedInsets((prev) => (sameInsets(prev, ZERO_INSETS) ? prev : ZERO_INSETS));
        return;
      }

      const nextInsets = readMergedInsets(currentWebApp);
      syncCssSafeAreaVars(currentWebApp, nextInsets);
      setMergedInsets((prev) => (sameInsets(prev, nextInsets) ? prev : nextInsets));
    };

    updateInsets();

    TelegramSafeAreaEvents.forEach((eventName) => {
      webApp?.onEvent?.(eventName, updateInsets);
    });
    window.addEventListener("resize", updateInsets, { passive: true });
    window.visualViewport?.addEventListener("resize", updateInsets, { passive: true });

    return () => {
      TelegramSafeAreaEvents.forEach((eventName) => {
        webApp?.offEvent?.(eventName, updateInsets);
      });
      window.removeEventListener("resize", updateInsets);
      window.visualViewport?.removeEventListener("resize", updateInsets);
    };
  }, []);

  return mergedInsets;
}
