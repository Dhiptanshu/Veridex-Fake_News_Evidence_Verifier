import {
  BarChart3, Boxes, ChevronsLeft, ChevronsRight, Columns2, Database, History, ListChecks, Moon, Settings, ShieldCheck, Sun,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useTheme } from "@/theme/ThemeProvider";
import { ROUTES, type Route } from "./routes";

interface Item { route: Route; label: string; icon: LucideIcon }
const GROUPS: { title: string; items: Item[] }[] = [
  { title: "Workspace", items: [
    { route: "verify", label: "Verify", icon: ShieldCheck },
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
  verify: "Verify a claim", compare: "Compare pipelines", batch: "Batch verification", history: "History",
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

export function Shell({ route, go, children }: { route: Route; go: (r: Route) => void; children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const online = useApiStatus();
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem("fnev-nav") === "1"; } catch { return false; } });
  const toggleNav = () => setCollapsed((c) => { try { localStorage.setItem("fnev-nav", c ? "0" : "1"); } catch { /* ignore */ } return !c; });

  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      {/* sidebar (md and up) */}
      <aside className={`sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-surface md:flex ${collapsed ? "w-14" : "w-56"} transition-[width] duration-150`}>
        <div className={`flex h-12 items-center gap-2 border-b border-line ${collapsed ? "justify-center" : "px-4"}`}>
          <span className="grid size-6 place-items-center rounded-md bg-accent text-accentink"><ShieldCheck size={14} /></span>
          {!collapsed && <span className="text-[13px] font-semibold tracking-tight">Evidence Verifier</span>}
        </div>
        <nav aria-label="Main" className="flex-1 overflow-y-auto px-2 py-3">
          {GROUPS.map((g) => (
            <div key={g.title} className="mb-4">
              {!collapsed && <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted">{g.title}</p>}
              <ul className="space-y-0.5">
                {g.items.map(({ route: r, label, icon: Icon }) => (
                  <li key={r}>
                    <a
                      href={`#/${r}`}
                      onClick={(e) => { e.preventDefault(); go(r); }}
                      aria-current={route === r ? "page" : undefined}
                      title={collapsed ? label : undefined}
                      className={`flex h-8 items-center gap-2.5 rounded-md text-[13px] font-medium transition ${collapsed ? "justify-center" : "px-2.5"} ${
                        route === r ? "bg-accent/10 text-accent" : "text-muted hover:bg-surface2 hover:text-ink"}`}
                    >
                      <Icon size={16} strokeWidth={route === r ? 2.2 : 1.8} />
                      {!collapsed && label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className={`flex items-center border-t border-line p-2 ${collapsed ? "flex-col gap-1" : "justify-between"}`}>
          <span className={`flex items-center gap-2 px-1.5 text-xs text-muted ${collapsed ? "hidden" : ""}`}>
            <i className={`size-2 rounded-full ${online === null ? "bg-neutral" : online ? "bg-supported" : "bg-refuted"}`} />
            {online === null ? "Connecting" : online ? "API online" : "API offline"}
          </span>
          <div className={`flex ${collapsed ? "flex-col" : ""} gap-1`}>
            <button onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} className="grid size-7 place-items-center rounded-md text-muted hover:bg-surface2 hover:text-ink">
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
            <button onClick={toggleNav} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} className="grid size-7 place-items-center rounded-md text-muted hover:bg-surface2 hover:text-ink">
              {collapsed ? <ChevronsRight size={15} /> : <ChevronsLeft size={15} />}
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="sticky top-0 z-20 flex h-12 items-center justify-between gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur md:px-6">
          <div className="flex min-w-0 items-center gap-2 text-[13px]">
            <span className="hidden text-muted sm:inline">Evidence Verifier</span>
            <span className="hidden text-muted sm:inline">/</span>
            <h1 className="truncate font-semibold">{TITLES[route]}</h1>
          </div>
          <div className="flex items-center gap-2 md:hidden">
            <button onClick={toggle} aria-label="Toggle theme" className="grid size-8 place-items-center rounded-md border border-line bg-surface">
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>
          </div>
        </header>
        {/* mobile nav */}
        <nav aria-label="Sections" className="flex gap-1 overflow-x-auto border-b border-line bg-surface px-3 py-2 md:hidden">
          {ROUTES.map((r) => (
            <a key={r} href={`#/${r}`} onClick={(e) => { e.preventDefault(); go(r); }} aria-current={route === r ? "page" : undefined}
              className={`shrink-0 rounded-md px-2.5 py-1 text-xs font-medium capitalize ${route === r ? "bg-accent/10 text-accent" : "text-muted"}`}>{r}</a>
          ))}
        </nav>
        <main className="mx-auto w-full max-w-[1280px] flex-1 px-4 py-5 md:px-6">{children}</main>
      </div>
    </div>
  );
}
