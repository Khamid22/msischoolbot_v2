// Telegram Mini App viewport setup.
//
// The page embeds telegram.org/js/telegram-web-app.js, which injects
// window.Telegram.WebApp even in a plain browser. Without an explicit init the
// Mini App never expands and Telegram's "swipe down to close" gesture stays
// active — so scrolling the content down closes the app. This wires up the
// official fixes (expand + disableVerticalSwipes) and keeps the CSS viewport
// height in sync. It is a no-op outside a real Telegram client, so the
// browser-based admin console is unaffected.

interface TelegramWebApp {
  ready: () => void;
  expand?: () => void;
  /** Bot API 7.7+. Stops the swipe-down-to-close gesture; older clients ignore it. */
  disableVerticalSwipes?: () => void;
  isExpanded?: boolean;
  viewportHeight?: number;
  viewportStableHeight?: number;
  platform?: string;
  initData?: string;
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
  return platform !== "" && platform !== "unknown";
}

export function initTelegramViewport(): void {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  try {
    tg.ready();
  } catch {
    /* ignore */
  }

  if (!isRealTelegramClient(tg)) {
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
  };

  syncViewport();
  tg.onEvent?.("viewportChanged", syncViewport);
}
