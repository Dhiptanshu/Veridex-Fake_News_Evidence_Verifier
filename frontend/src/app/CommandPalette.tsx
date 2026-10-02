import { CornerDownLeft, History, Search, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Label } from "@/api/types";
import { Kbd, LABEL_TEXT, Badge, LABEL_TONE } from "@/components/ui";
import { useAppState } from "@/state/AppState";
import type { Route } from "./routes";

interface Cmd { id: string; label: string; hint?: string; icon: typeof Search; run: () => void; verdict?: Label | null }

const TABS: { route: Route; label: string }[] = [
  { route: "verify", label: "Verify a claim" }, { route: "assistant", label: "Assistant" }, { route: "compare", label: "Compare pipelines" },
  { route: "batch", label: "Batch verification" }, { route: "history", label: "History" }, { route: "data", label: "Data" },
  { route: "insights", label: "Insights" }, { route: "pipeline", label: "Pipeline and services" }, { route: "settings", label: "Settings" },
];

export function CommandPalette({ open, onClose, go }: { open: boolean; onClose: () => void; go: (r: Route) => void }) {
  const { history, setDraft } = useAppState();
  const [q, setQ] = useState("");
  const [i, setI] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => { if (open) { setQ(""); setI(0); setTimeout(() => input.current?.focus(), 20); } }, [open]);

  const items = useMemo<Cmd[]>(() => {
    const needle = q.trim().toLowerCase();
    const out: Cmd[] = [];
    if (q.trim().length >= 3) {
      out.push({ id: "verify-typed", label: `Verify: ${q.trim()}`, hint: "run now", icon: ShieldCheck, run: () => { setDraft(q.trim()); go("verify"); } });
    }
    for (const t of TABS) if (!needle || t.label.toLowerCase().includes(needle)) out.push({ id: t.route, label: t.label, hint: "go to", icon: Search, run: () => go(t.route) });
    for (const h of history.slice(0, 40)) {
      if (needle && !h.claim.toLowerCase().includes(needle)) continue;
      out.push({ id: h.id, label: h.claim, hint: "re-run", icon: History, run: () => { setDraft(h.claim); go("verify"); }, verdict: h.label });
      if (out.length > 14) break;
    }
    return out.slice(0, 12);
  }, [q, history, go, setDraft]);

  if (!open) return null;
  const choose = (c?: Cmd) => { if (c) { c.run(); onClose(); } };

  return (
    <div className="fixed inset-0 z-50 grid place-items-start justify-center bg-black/40 px-4 pt-[14vh] backdrop-blur-sm" onMouseDown={onClose} role="dialog" aria-modal aria-label="Command palette">
      <div className="rise w-full max-w-xl overflow-hidden rounded-2xl border border-line bg-surface shadow-pop" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search size={16} className="text-muted" />
          <input
            ref={input} value={q} onChange={(e) => { setQ(e.target.value); setI(0); }} placeholder="Type a claim to verify, or search tabs and history..."
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setI((x) => Math.min(x + 1, items.length - 1)); }
              else if (e.key === "ArrowUp") { e.preventDefault(); setI((x) => Math.max(x - 1, 0)); }
              else if (e.key === "Enter") { e.preventDefault(); choose(items[i]); }
              else if (e.key === "Escape") onClose();
            }}
            className="h-12 flex-1 bg-transparent text-[14px] outline-none placeholder:text-muted/70"
          />
          <Kbd>Esc</Kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-2">
          {items.length === 0 && <li className="px-3 py-6 text-center text-[13px] text-muted">Nothing matches.</li>}
          {items.map((c, idx) => {
            const Icon = c.icon;
            return (
              <li key={c.id}>
                <button
                  onMouseEnter={() => setI(idx)} onClick={() => choose(c)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[13px] ${idx === i ? "bg-accent/10 text-ink" : "text-ink/85"}`}
                >
                  <Icon size={15} className={idx === i ? "text-accent" : "text-muted"} />
                  <span className="min-w-0 flex-1 truncate">{c.label}</span>
                  {c.verdict && <Badge tone={LABEL_TONE[c.verdict]}>{LABEL_TEXT[c.verdict]}</Badge>}
                  {c.hint && <span className="shrink-0 text-[11px] text-muted">{c.hint}</span>}
                  {idx === i && <CornerDownLeft size={12} className="shrink-0 text-muted" />}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
