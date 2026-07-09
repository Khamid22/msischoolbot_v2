// Telegram Mini App viewport setup.
//
// The page embeds telegram.org/js/telegram-web-app.js, which injects
// window.Telegram.WebApp even in a plain browser. Without an explicit init the
// Mini App never expands and Telegram's "swipe down to close" gesture stays
// active — so scrolling the content down closes the app. This wires up the
// official fixes (expand + disableVerticalSwipes) and keeps the CSS viewport
// height in sync. It is a no-op outside a real Telegram client, so the
// browser-based admin console is unaffected.

interface TelegramInsets {
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
}

interface TelegramWebApp {
  ready: () => void;
  expand?: () => void;
  /** Bot API 7.7+. Stops the swipe-down-to-close gesture; older clients ignore it. */
  disableVerticalSwipes?: () => void;
  isExpanded?: boolean;
  viewportHeight?: number;
  viewportStableHeight?: number;
  safeAreaInset?: TelegramInsets;
  contentSafeAreaInset?: TelegramInsets;
  platform?: string;
  initData?: string;
  initDataUnsafe?: {
    start_param?: string;
  };
  onEvent?: (event: string, handler: () => void) => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

/** True only when running inside an actual Telegram client (not a plain browser). */
function isRealTelegramClient(tg: TelegramWebApp): boolean {
  const platform = String(tg.platform || "unknown").toLowerCase();
  return Boolean(tg.initData) || (platform !== "" && platform !== "unknown");
}

export function isTelegramMiniApp(): boolean {
  if (typeof window === "undefined") return false;
  const tg = window.Telegram?.WebApp;
  return Boolean(tg && isRealTelegramClient(tg));
}

function safePixel(value: unknown): string {
  const parsed = Number(value);
  return `${Number.isFinite(parsed) && parsed > 0 ? Math.round(parsed) : 0}px`;
}

/**
 * Fallback viewport sync used whenever we are NOT in a real Telegram client
 * (plain mobile/desktop browser, or telegram-web-app.js loaded outside
 * Telegram for local preview). `100dvh` is usually accurate, but some mobile
 * browsers miscalculate it while the address bar animates in/out, so keep
 * it corrected from the live, widely-supported window/visualViewport size.
 */
function syncViewportFromWindow(): void {
  const height = Math.round(window.visualViewport?.height || window.innerHeight || 0);
  if (height <= 0) return;
  const root = document.documentElement;
  const value = `${height}px`;
  root.style.setProperty("--tg-app-height", value);
  root.style.setProperty("--tg-viewport-height", value);
  root.style.setProperty("--tg-visual-viewport-height", value);
}

function bindWindowViewportFallback(): void {
  syncViewportFromWindow();
  window.addEventListener("resize", syncViewportFromWindow);
  window.visualViewport?.addEventListener("resize", syncViewportFromWindow);
}

export function initTelegramViewport(): void {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    bindWindowViewportFallback();
    return;
  }

  try {
    tg.ready();
  } catch {
    /* ignore */
  }

  if (!isRealTelegramClient(tg)) {
    bindWindowViewportFallback();
    return;
  }

  try {
    tg.expand?.();
  } catch {
    /* ignore */
  }
  // The key fix: let the user scroll the content without the Mini App closing.
  try {
    tg.disableVerticalSwipes?.();
  } catch {
    /* ignore */
  }

  const root = document.documentElement;

  const syncViewport = () => {
    const stableHeight = Number(tg.viewportStableHeight || tg.viewportHeight || 0);
    if (stableHeight > 0) {
      const value = `${Math.round(stableHeight)}px`;
      root.style.setProperty("--tg-app-height", value);
      root.style.setProperty("--tg-viewport-height", value);
      root.style.setProperty("--tg-visual-viewport-height", value);
    }
    // Re-expand if Telegram collapsed the viewport (e.g. after a keyboard close).
    if (tg.isExpanded === false) {
      try {
        tg.expand?.();
      } catch {
        /* ignore */
      }
    }

    const safeArea = tg.safeAreaInset || {};
    const contentSafeArea = tg.contentSafeAreaInset || {};
    root.style.setProperty("--tg-safe-area-inset-top", safePixel(safeArea.top));
    root.style.setProperty("--tg-safe-area-inset-right", safePixel(safeArea.right));
    root.style.setProperty("--tg-safe-area-inset-bottom", safePixel(safeArea.bottom));
    root.style.setProperty("--tg-safe-area-inset-left", safePixel(safeArea.left));
    root.style.setProperty("--tg-content-safe-area-inset-top", safePixel(contentSafeArea.top));
    root.style.setProperty("--tg-content-safe-area-inset-right", safePixel(contentSafeArea.right));
    root.style.setProperty("--tg-content-safe-area-inset-bottom", safePixel(contentSafeArea.bottom));
    root.style.setProperty("--tg-content-safe-area-inset-left", safePixel(contentSafeArea.left));
  };

  syncViewport();
  tg.onEvent?.("viewportChanged", syncViewport);
  tg.onEvent?.("safeAreaChanged", syncViewport);
  tg.onEvent?.("contentSafeAreaChanged", syncViewport);
}

export function getTelegramStartParam(): string {
  const unsafeParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
  if (typeof unsafeParam === "string" && unsafeParam.trim()) {
    return unsafeParam.trim();
  }

  try {
    return new URLSearchParams(window.location.search).get("tgWebAppStartParam")?.trim() || "";
  } catch {
    return "";
  }
}
