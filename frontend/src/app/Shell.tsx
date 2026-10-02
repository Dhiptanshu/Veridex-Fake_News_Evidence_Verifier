import {
  BarChart3, Boxes, ChevronsLeft, ChevronsRight, Columns2, Database, History, ListChecks, Menu, Moon, Search, Settings, ShieldCheck, Sparkles, Sun,
  type LucideIcon,
} from "lucide-react";
import { Fragment, useEffect, useState, type ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { Kbd } from "@/components/ui";
import { useTheme } from "@/theme/ThemeProvider";
import { CommandPalette } from "./CommandPalette";
import { type Route } from "./routes";

interface Item { route: Route; label: string; icon: LucideIcon }
const GROUPS: Item[][] = [
  [
    { route: "verify", label: "Verify", icon: ShieldCheck },
    { route: "assistant", label: "Vera", icon: Sparkles },
    { route: "compare", label: "Compare", icon: Columns2 },
    { route: "batch", label: "Batch", icon: ListChecks },
    { route: "history", label: "History", icon: History },
  ],
  [
    { route: "data", label: "Data", icon: Database },
    { route: "insights", label: "Insights", icon: BarChart3 },
  ],
  [
    { route: "pipeline", label: "Pipeline", icon: Boxes },
    { route: "settings", label: "Settings", icon: Settings },
  ],
];
const PAGE: Record<Route, { title: string; sub: string }> = {
  verify: { title: "Verify a claim", sub: "Check a claim against live news, fact-checkers and an AI judge" },
  assistant: { title: "Chat with Vera", sub: "Your investigative sidekick. She digs through the news and fact-checkers and cites every source" },
  compare: { title: "Compare pipelines", sub: "Run one claim through different evidence and verdict engines side by side" },
  batch: { title: "Batch verification", sub: "Check many claims at once, with accuracy scoring for labelled data" },
  history: { title: "History", sub: "Every claim you have checked, saved in this browser only" },
  data: { title: "Data", sub: "The FEVER benchmark claims and Wikipedia evidence corpus" },
  insights: { title: "Insights", sub: "Evaluation results for every model and experiment" },
  pipeline: { title: "Pipeline and services", sub: "What is built, what is configured, and how to fix what is missing" },
  settings: { title: "Settings", sub: "Appearance, default pipeline and data on this device" },
};

function useApiStatus() {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    const ping = () => fetch("/api/health").then((r) => alive && setOk(r.ok)).catch(() => alive && setOk(false));
    ping();
    const t = setInterval(ping, 20000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return ok;
}

export function Shell({ route, go, children }: { route: Route; go: (r: Route) => void; children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const online = useApiStatus();
  const [palette, setPalette] = useState(false);
  const [menu, setMenu] = useState(false);
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem("fnev-nav") === "1"; } catch { return false; } });
  const toggleNav = () => setCollapsed((c) => { try { localStorage.setItem("fnev-nav", c ? "0" : "1"); } catch { /* ignore */ } return !c; });

  useEffect(() => {
    const on = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((p) => !p); } };
    addEventListener("keydown", on);
    return () => removeEventListener("keydown", on);
  }, []);
  useEffect(() => setMenu(false), [route]);

  const brand = (compact: boolean) => (
    <div className={`flex items-center gap-3 ${compact ? "justify-center" : "px-2"}`}>
      <Logo size={compact ? 36 : 38} />
      {!compact && (
        <div className="min-w-0 leading-none">
          <p className="font-display text-[19px] font-bold tracking-[0.1em]">VERIDEX</p>
          <p className="mt-1 truncate text-[11px] font-medium text-accent">Verify before you share</p>
        </div>
      )}
    </div>
  );

  const nav = (compact: boolean, onPick?: () => void) => (
    <nav aria-label="Main" className="flex-1 overflow-y-auto py-2">
      {GROUPS.map((g, gi) => (
        <Fragment key={gi}>
          {gi > 0 && <div className="mx-2 my-3 h-px bg-line" />}
          <ul className="space-y-1.5">
            {g.map(({ route: r, label, icon: Icon }) => (
              <li key={r}>
                <a
                  href={`#/${r}`} onClick={(e) => { e.preventDefault(); go(r); onPick?.(); }} aria-current={route === r ? "page" : undefined}
                  title={compact ? label : undefined}
                  className={`flex h-10 items-center gap-3 rounded-xl border text-[13.5px] font-medium transition ${compact ? "justify-center" : "px-3"} ${
                    route === r ? "border-accent/45 bg-accent/12 text-ink" : "border-transparent text-ink/80 hover:bg-surface2 hover:text-ink"}`}
                >
                  <Icon size={17} strokeWidth={route === r ? 2.2 : 1.8} className={route === r ? "text-accent" : "text-muted"} />
                  {!compact && label}
                </a>
              </li>
            ))}
          </ul>
        </Fragment>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-dvh gap-5 p-3 md:p-5">
      <aside className={`card-flat sticky top-5 hidden h-[calc(100dvh-2.5rem)] shrink-0 flex-col rounded-[24px] p-3 md:flex ${collapsed ? "w-[4.75rem]" : "w-[15rem]"} transition-[width] duration-200`}>
        <div className="pb-3 pt-1">{brand(collapsed)}</div>
        {nav(collapsed)}
        <div className="mt-2 border-t border-line pt-3">
          <div className={`flex items-center ${collapsed ? "flex-col gap-2" : "justify-between"} px-1`}>
            <span className="flex items-center gap-2 text-[12.5px] text-muted" title={online ? "API online" : "API offline"}>
              <i className={`size-2.5 rounded-full ${online === null ? "bg-neutral" : online ? "bg-supported" : "bg-refuted"}`} />
              {!collapsed && (online === null ? "Connecting" : online ? "API online" : "API offline")}
            </span>
            <button onClick={toggleNav} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} className="grid size-9 place-items-center rounded-xl text-muted hover:bg-surface2 hover:text-ink">
              {collapsed ? <ChevronsRight size={17} /> : <ChevronsLeft size={17} />}
            </button>
          </div>
        </div>
      </aside>

      {menu && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setMenu(false)}>
          <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" />
          <aside className="card-flat rise absolute inset-y-3 left-3 flex w-72 flex-col rounded-[28px] p-4" onClick={(e) => e.stopPropagation()}>
            <div className="pb-4 pt-1">{brand(false)}</div>
            {nav(false, () => setMenu(false))}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-start justify-between gap-4 px-1 pb-5 pt-1 md:pb-6">
          <div className="flex min-w-0 items-start gap-3">
            <button onClick={() => setMenu(true)} aria-label="Open menu" className="card-flat mt-0.5 grid size-11 shrink-0 place-items-center rounded-2xl md:hidden"><Menu size={19} /></button>
            <div className="min-w-0">
              <h1 className="truncate font-display text-[20px] font-bold leading-tight tracking-tight md:text-[24px]">{PAGE[route].title}</h1>
              <p className="mt-0.5 text-[13px] text-muted">{PAGE[route].sub}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2.5">
            <button
              onClick={() => setPalette(true)}
              className="card-flat hidden h-10 items-center gap-2.5 rounded-xl px-3.5 text-[13px] text-muted transition hover:text-ink sm:flex"
            >
              <Search size={16} /> Search or run a claim <Kbd>Ctrl K</Kbd>
            </button>
            <button onClick={() => setPalette(true)} aria-label="Search" className="card-flat grid size-11 place-items-center rounded-2xl sm:hidden"><Search size={18} /></button>
            <button onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} className="card-flat grid size-10 place-items-center rounded-xl text-muted transition hover:text-ink">
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>
        <main className="w-full max-w-[1280px] flex-1 pb-8">{children}</main>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} go={go} />
    </div>
  );
}
