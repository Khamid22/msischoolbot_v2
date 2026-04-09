import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { TelegramLayout, Topbar } from "./components/TelegramLayout"; // adjust path if needed
import "./index.css";

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        disableVerticalSwipes: () => void;
        isVersionAtLeast: (version: string) => boolean;
        themeParams: Record<string, string>;
        colorScheme: "light" | "dark";
      };
    };
  }
}

// 🚀 Initialize Telegram SDK BEFORE React mounts
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();                 // ✅ Tells TG your UI is ready
  tg.expand();                // ✅ Forces fullscreen (exits compact bottom-sheet)
  if (tg.isVersionAtLeast("6.9")) {
    tg.disableVerticalSwipes(); // ✅ Blocks pull-down-to-close gesture
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TelegramLayout
      topbar={
        <Topbar
          title="MSI School Portal"
          subtitle="Learn • Practice • Grow"
        />
      }
    >
      <App />
    </TelegramLayout>
  </StrictMode>
);