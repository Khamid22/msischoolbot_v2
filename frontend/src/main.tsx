import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App";
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
  }
});
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
