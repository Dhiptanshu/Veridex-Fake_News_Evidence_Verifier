import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "@/app/App";
import { AppStateProvider } from "@/state/AppState";
import { ThemeProvider } from "@/theme/ThemeProvider";
import "@/theme/theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AppStateProvider>
        <App />
      </AppStateProvider>
    </ThemeProvider>
  </StrictMode>,
);
