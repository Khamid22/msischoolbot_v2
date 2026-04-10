import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

const VITE_CHUNK_RELOAD_KEY = "__msi_vite_chunk_reload_once";

window.addEventListener("vite:preloadError", (event: Event) => {
  event.preventDefault();
  try {
    if (window.sessionStorage.getItem(VITE_CHUNK_RELOAD_KEY) !== "1") {
      window.sessionStorage.setItem(VITE_CHUNK_RELOAD_KEY, "1");
      window.location.reload();
    }
  } catch (_error) {
    window.location.reload();
  }
});

window.addEventListener("pageshow", () => {
  try {
    window.sessionStorage.removeItem(VITE_CHUNK_RELOAD_KEY);
  } catch (_error) {
    // Ignore sessionStorage availability issues.
  }
});

type TelegramWebApp = {
  ready?: () => void;
  expand?: () => void;
  requestFullscreen?: () => void;
  disableVerticalSwipes?: () => void;
  onEvent?: (event: string, callback: () => void) => void;
};

function bootstrapTelegramWebApp() {
  const webApp = (window as Window & { Telegram?: { WebApp?: TelegramWebApp } }).Telegram?.WebApp;
  if (!webApp) {
    return false;
  }

  const lockVerticalSwipes = () => {
    try {
      webApp.disableVerticalSwipes?.();
    } catch (_error) {
      // Ignore unsupported swipe-lock calls.
    }
  };

  try {
    webApp.ready?.();
  } catch (_error) {
    // Ignore unsupported ready() calls.
  }
  try {
    webApp.expand?.();
  } catch (_error) {
    // Ignore unsupported expand() calls.
  }
  try {
    webApp.requestFullscreen?.();
  } catch (_error) {
    // Ignore unsupported fullscreen calls.
  }

  lockVerticalSwipes();
  webApp.onEvent?.("fullscreenChanged", lockVerticalSwipes);
  webApp.onEvent?.("viewportChanged", lockVerticalSwipes);
  webApp.onEvent?.("safeAreaChanged", lockVerticalSwipes);
  webApp.onEvent?.("contentSafeAreaChanged", lockVerticalSwipes);

  return true;
}

if (!bootstrapTelegramWebApp()) {
  let retries = 24;
  const retryTimer = window.setInterval(() => {
    if (bootstrapTelegramWebApp() || retries <= 0) {
      window.clearInterval(retryTimer);
      return;
    }
    retries -= 1;
  }, 80);
}

// Each page component owns its own TelegramLayout — no wrapper needed here.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
