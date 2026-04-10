import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Tell Telegram the mini app is ready and expand to full height.
// This triggers the SDK to inject safe-area CSS variables before layout runs.
const tg = (window as Window & { Telegram?: { WebApp?: { ready?: () => void; expand?: () => void } } }).Telegram?.WebApp;
if (tg) {
  tg.ready?.();
  tg.expand?.();
}

// Each page component owns its own TelegramLayout — no wrapper needed here.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
