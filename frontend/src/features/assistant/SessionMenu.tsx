import { History, MessageSquare, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui";

export interface SessionMeta { id: string; title: string; updatedAt: number; count: number }

function dayLabel(ts: number): string {
  const d = new Date(ts);
  const today = new Date();
  const start = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((start(today) - start(d)) / 86400000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff < 7) return "This week";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: d.getFullYear() === today.getFullYear() ? undefined : "numeric" });
}
const clock = (ts: number) => new Date(ts).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

/** "Recent chats" dropdown: open, search or delete past conversations, grouped by day. */
export function SessionMenu({
  sessions, currentId, onOpen, onDelete, onDeleteAll, onNew,
}: {
  sessions: SessionMeta[]; currentId: string; onOpen: (id: string) => void; onDelete: (id: string) => void; onDeleteAll: () => void; onNew: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [open]);

  const groups = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt).filter((s) => !needle || s.title.toLowerCase().includes(needle));
    const out: { label: string; items: SessionMeta[] }[] = [];
    for (const s of list) {
      const label = dayLabel(s.updatedAt);
      const g = out.find((x) => x.label === label);
      if (g) g.items.push(s); else out.push({ label, items: [s] });
    }
    return out;
  }, [sessions, q]);

  return (
    <div ref={box} className="relative flex items-center gap-2">
      <Button size="sm" icon={<Plus size={14} />} onClick={() => { onNew(); setOpen(false); }}>New chat</Button>
      <Button size="sm" icon={<History size={14} />} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="listbox">
        Recent chats{sessions.length > 0 && <span className="rounded-full bg-accent/14 px-1.5 text-[11px] text-accent">{sessions.length}</span>}
      </Button>
      {open && (
        <div className="rise card-flat absolute right-0 top-11 z-40 w-[min(24rem,88vw)] overflow-hidden rounded-2xl shadow-pop">
          {sessions.length > 6 && (
            <label className="flex items-center gap-2 border-b border-line px-3.5 py-2.5">
              <Search size={14} className="text-muted" />
              <input
                value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search chats" aria-label="Search chats"
                className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted/70"
              />
            </label>
          )}
          <div className="max-h-[22rem] overflow-y-auto p-1.5">
            {sessions.length === 0 && <p className="px-3 py-6 text-center text-[13px] text-muted">No saved chats yet. Start one and it appears here.</p>}
            {sessions.length > 0 && groups.length === 0 && <p className="px-3 py-6 text-center text-[13px] text-muted">No chats match.</p>}
            {groups.map((g) => (
              <div key={g.label} className="mb-1">
                <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-muted">{g.label}</p>
                <ul>
                  {g.items.map((s) => (
                    <li key={s.id} className="group relative">
                      <button
                        onClick={() => { onOpen(s.id); setOpen(false); }}
                        className={`flex w-full items-start gap-2.5 rounded-lg px-3 py-2 pr-10 text-left transition hover:bg-surface2 ${s.id === currentId ? "bg-accent/12" : ""}`}
                      >
                        <MessageSquare size={14} className={`mt-0.5 shrink-0 ${s.id === currentId ? "text-accent" : "text-muted"}`} />
                        <span className="min-w-0">
                          <span className={`block truncate text-[13px] ${s.id === currentId ? "font-semibold" : "font-medium"}`}>{s.title}</span>
                          <span className="text-[11.5px] text-muted">{s.count} message{s.count === 1 ? "" : "s"} . {clock(s.updatedAt)}</span>
                        </span>
                      </button>
                      <button
                        onClick={() => onDelete(s.id)} aria-label={`Delete chat ${s.title}`}
                        className="absolute right-2 top-2 grid size-7 place-items-center rounded-md text-muted opacity-0 transition hover:bg-refuted/12 hover:text-refuted focus:opacity-100 group-hover:opacity-100"
                      ><Trash2 size={13} /></button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          {sessions.length > 0 && (
            <div className="border-t border-line px-3.5 py-2">
              <button
                onClick={() => { if (confirm(`Delete all ${sessions.length} saved chats?`)) { onDeleteAll(); setOpen(false); } }}
                className="text-[12px] font-medium text-muted hover:text-refuted"
              >Delete all chats</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
