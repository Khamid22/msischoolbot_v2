import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { TelegramLayout, Topbar } from "./components/TelegramLayout";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TelegramLayout
      topbar={<Topbar title="MSI School Portal" subtitle="Learn • Practice • Grow" />}
    >
      <App />
    </TelegramLayout>
  </StrictMode>
);