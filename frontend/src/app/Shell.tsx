import {
  BarChart3, Boxes, ChevronsLeft, ChevronsRight, Columns2, Database, History, ListChecks, Menu, Moon, Search, Settings, ShieldCheck, Sparkles, Sun,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Kbd } from "@/components/ui";
import { useTheme } from "@/theme/ThemeProvider";
import { CommandPalette } from "./CommandPalette";
import { ROUTES, type Route } from "./routes";

interface Item { route: Route; label: string; icon: LucideIcon }
const GROUPS: { title: string; items: Item[] }[] = [
  { title: "Workspace", items: [
    { route: "verify", label: "Verify", icon: ShieldCheck },
    { route: "assistant", label: "Assistant", icon: Sparkles },
    { route: "compare", label: "Compare", icon: Columns2 },
    { route: "batch", label: "Batch", icon: ListChecks },
    { route: "history", label: "History", icon: History },
  ] },
  { title: "Analysis", items: [
    { route: "data", label: "Data", icon: Database },
    { route: "insights", label: "Insights", icon: BarChart3 },
  ] },
  { title: "System", items: [
    { route: "pipeline", label: "Pipeline", icon: Boxes },
    { route: "settings", label: "Settings", icon: Settings },
  ] },
];
const TITLES: Record<Route, string> = {
  verify: "Verify a claim", assistant: "Assistant", compare: "Compare pipelines", batch: "Batch verification", history: "History",
  data: "Data", insights: "Insights", pipeline: "Pipeline and services", settings: "Settings",
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

function Logo({ small = false }: { small?: boolean }) {
  return (
    <span className={`grid shrink-0 place-items-center rounded-xl bg-brand text-accentink shadow-brand ${small ? "size-8" : "size-9"}`}>
      <ShieldCheck size={small ? 16 : 18} strokeWidth={2.2} />
    </span>
  );
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

  const nav = (compact: boolean, onPick?: () => void) => (
    <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-4">
      {GROUPS.map((g) => (
        <div key={g.title} className="mb-5">
          {!compact && <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">{g.title}</p>}
          <ul className="space-y-1">
            {g.items.map(({ route: r, label, icon: Icon }) => (
              <li key={r}>
                <a
                  href={`#/${r}`} onClick={(e) => { e.preventDefault(); go(r); onPick?.(); }} aria-current={route === r ? "page" : undefined}
                  title={compact ? label : undefined}
                  className={`flex h-10 items-center gap-3 rounded-xl text-[13.5px] font-medium transition ${compact ? "justify-center" : "px-3"} ${
                    route === r ? "bg-accent/12 text-accent" : "text-muted hover:bg-surface2 hover:text-ink"}`}
                >
                  <Icon size={17} strokeWidth={route === r ? 2.3 : 1.9} />
                  {!compact && label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-dvh">
      <aside className={`sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-surface/80 backdrop-blur-xl md:flex ${collapsed ? "w-[4.5rem]" : "w-64"} transition-[width] duration-200`}>
        <div className={`flex h-16 items-center gap-3 ${collapsed ? "justify-center" : "px-5"}`}>
          <Logo />
          {!collapsed && <div className="leading-tight"><p className="text-sm font-bold tracking-tight">Evidence</p><p className="text-sm font-bold tracking-tight text-brand">Verifier</p></div>}
        </div>
        {nav(collapsed)}
        <div className={`flex items-center border-t border-line p-3 ${collapsed ? "flex-col gap-2" : "justify-between"}`}>
          {!collapsed && (
            <span className="flex items-center gap-2 px-2 text-xs text-muted">
              <i className={`size-2 rounded-full ${online === null ? "bg-neutral" : online ? "bg-supported" : "bg-refuted"}`} />
              {online === null ? "Connecting" : online ? "API online" : "API offline"}
            </span>
          )}
          <button onClick={toggleNav} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} className="grid size-8 place-items-center rounded-lg text-muted hover:bg-surface2 hover:text-ink">
            {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
          </button>
        </div>
      </aside>

      {menu && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={() => setMenu(false)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <aside className="rise absolute inset-y-0 left-0 flex w-72 flex-col bg-surface shadow-pop" onClick={(e) => e.stopPropagation()}>
            <div className="flex h-16 items-center gap-3 px-5"><Logo /><p className="text-sm font-bold">Evidence <span className="text-brand">Verifier</span></p></div>
            {nav(false, () => setMenu(false))}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-line bg-bg/70 px-4 backdrop-blur-xl md:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button onClick={() => setMenu(true)} aria-label="Open menu" className="grid size-9 place-items-center rounded-xl border border-line bg-surface md:hidden"><Menu size={17} /></button>
            <h1 className="truncate text-[15px] font-semibold tracking-tight">{TITLES[route]}</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPalette(true)}
              className="hidden h-9 items-center gap-2 rounded-xl border border-line bg-surface px-3 text-[13px] text-muted shadow-card transition hover:text-ink sm:flex"
            >
              <Search size={14} /> Search or run a claim <Kbd>Ctrl K</Kbd>
            </button>
            <button onClick={() => setPalette(true)} aria-label="Search" className="grid size-9 place-items-center rounded-xl border border-line bg-surface sm:hidden"><Search size={16} /></button>
            <button onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} className="grid size-9 place-items-center rounded-xl border border-line bg-surface text-muted shadow-card transition hover:text-ink">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1240px] flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
      <CommandPalette open={palette} onClose={() => setPalette(false)} go={go} />
    </div>
  );
}

export { ROUTES };
