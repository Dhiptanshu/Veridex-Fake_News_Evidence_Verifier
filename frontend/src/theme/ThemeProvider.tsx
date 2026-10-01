import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemeMode = "system" | "light" | "dark";
type Resolved = "light" | "dark";
const KEY = "fnev-theme";

interface Ctx { theme: Resolved; mode: ThemeMode; setMode: (m: ThemeMode) => void; toggle: () => void }
const ThemeCtx = createContext<Ctx | null>(null);

const systemTheme = (): Resolved => (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

function storedMode(): ThemeMode {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(storedMode);
  const [system, setSystem] = useState<Resolved>(systemTheme);
  const theme: Resolved = mode === "system" ? system : mode;

  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);

  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const on = (e: MediaQueryListEvent) => setSystem(e.matches ? "dark" : "light");
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m);
    try {
      if (m === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, m);
    } catch { /* storage unavailable */ }
  }, []);

  const toggle = useCallback(() => setMode(theme === "dark" ? "light" : "dark"), [theme, setMode]);
  const value = useMemo(() => ({ theme, mode, setMode, toggle }), [theme, mode, setMode, toggle]);
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error("useTheme must be used inside ThemeProvider");
  return ctx;
}
