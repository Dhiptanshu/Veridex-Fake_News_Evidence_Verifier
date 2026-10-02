import { ArrowUp, Check, Copy, ExternalLink, Globe, Loader2, RotateCcw, Sparkles, Square } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { streamChat, type ChatContext, type ChatSource, type Turn } from "@/api/chat";
import { Badge, SourceMark } from "@/components/ui";
import { readJSON, writeJSON } from "@/lib/persist";

interface Msg { role: "user" | "assistant"; content: string; tools?: { id: string; label: string; done: boolean; error?: string | null }[]; cited?: number[]; error?: string; streaming?: boolean }

/** Text with [n] markers turned into small numbered chips that open the source. */
function Cited({ text, sources, onJump }: { text: string; sources: ChatSource[]; onJump?: (s: ChatSource) => void }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((p, i) => {
        const m = /^\[(\d+)\]$/.exec(p);
        const src = m ? sources.find((s) => s.n === Number(m[1])) : undefined;
        if (!src) return <Fragment key={i}>{p}</Fragment>;
        return (
          <button
            key={i} onClick={() => (onJump ? onJump(src) : src.url && window.open(src.url, "_blank", "noopener"))}
            title={`${src.title} (${src.source})`}
            className="mx-0.5 inline-grid h-[18px] min-w-[18px] place-items-center rounded-full bg-brand px-1 align-text-top text-[10px] font-bold text-accentink"
          >
            {src.n}
          </button>
        );
      })}
    </>
  );
}

function SourceCard({ s }: { s: ChatSource }) {
  const body = (
    <div className="flex items-start gap-2.5 rounded-xl border border-line bg-surface px-3 py-2 transition hover:border-accent/50">
      <SourceMark url={s.url} name={s.source || s.title} size={24} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-semibold">[{s.n}] {s.title}</p>
        <p className="truncate text-[11px] text-muted">{s.source}{s.date ? ` . ${s.date}` : ""}{s.tier && s.tier !== "unrated" ? ` . ${s.tier}` : ""}</p>
      </div>
      {s.url && <ExternalLink size={12} className="mt-1 shrink-0 text-muted" />}
    </div>
  );
  return s.url ? <a href={s.url} target="_blank" rel="noreferrer noopener" className="block">{body}</a> : body;
}

export function ChatThread({
  context, initialSources, suggestions, placeholder, onJump, resetKey, height = "min-h-[22rem]", modelHint, persistKey,
}: {
  context: ChatContext | null; initialSources: ChatSource[]; suggestions: string[]; placeholder: string; onJump?: (s: ChatSource) => void;
  resetKey: string; height?: string; modelHint?: string; persistKey?: string;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [sources, setSources] = useState<ChatSource[]>(initialSources);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const ctl = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const sourcesRef = useRef(sources);
  sourcesRef.current = sources;

  // a new claim/result starts (or resumes) its own conversation; conversations are saved so a reload or tab switch loses nothing
  useEffect(() => {
    ctl.current?.abort();
    setBusy(false);
    const saved = persistKey ? readJSON<{ msgs: Msg[]; sources: ChatSource[] } | null>(`fnev-chat:${persistKey}`, null) : null;
    if (saved?.msgs?.length) {
      setMsgs(saved.msgs.map((m) => ({ ...m, streaming: false })));
      setSources(saved.sources?.length ? saved.sources : initialSources);
    } else {
      setMsgs([]);
      setSources(initialSources);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);
  useEffect(() => {
    if (!persistKey || msgs.length === 0 || msgs.some((m) => m.streaming)) return;
    writeJSON(`fnev-chat:${persistKey}`, { msgs: msgs.slice(-30), sources });
    const index = readJSON<string[]>("fnev-chat-index", []).filter((k) => k !== persistKey);
    index.push(persistKey);
    while (index.length > 12) { try { localStorage.removeItem(`fnev-chat:${index.shift()}`); } catch { /* ignore */ } }
    writeJSON("fnev-chat-index", index);
  }, [msgs, sources, persistKey]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs]);
  useEffect(() => () => ctl.current?.abort(), []);

  const patchLast = (fn: (m: Msg) => Msg) => setMsgs((all) => all.map((m, i) => (i === all.length - 1 ? fn(m) : m)));

  const send = useCallback(async (question: string, base?: Msg[]) => {
    const q = question.trim();
    if (q.length < 2 || busy) return;
    const history: Msg[] = [...(base ?? msgs), { role: "user", content: q }];
    setMsgs([...history, { role: "assistant", content: "", tools: [], streaming: true }]);
    setText("");
    setBusy(true);
    const c = new AbortController();
    ctl.current = c;
    const turns: Turn[] = history.filter((m) => !m.error && m.content).map((m) => ({ role: m.role, content: m.content }));
    try {
      for await (const ev of streamChat({ messages: turns, context, sources: sourcesRef.current }, c.signal)) {
        if (ev.type === "token") patchLast((m) => ({ ...m, content: m.content + ev.text }));
        else if (ev.type === "tool") patchLast((m) => ({ ...m, tools: [...(m.tools ?? []), { id: ev.id, label: ev.label, done: false }] }));
        else if (ev.type === "tool_done") patchLast((m) => ({ ...m, tools: (m.tools ?? []).map((t) => (t.id === ev.id ? { ...t, done: true, error: ev.error } : t)) }));
        else if (ev.type === "sources") setSources((s) => [...s, ...ev.sources.filter((n) => !s.some((x) => x.n === n.n))]);
        else if (ev.type === "done") patchLast((m) => ({ ...m, cited: ev.cited, streaming: false }));
        else if (ev.type === "error") patchLast((m) => ({ ...m, error: ev.message, streaming: false }));
      }
      patchLast((m) => ({ ...m, streaming: false }));
    } catch (e) {
      if ((e as Error).name !== "AbortError") patchLast((m) => ({ ...m, error: (e as Error).message, streaming: false }));
      else patchLast((m) => ({ ...m, streaming: false }));
    } finally {
      setBusy(false);
    }
  }, [busy, msgs, context]);

  const retry = () => {
    const lastUser = [...msgs].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    const idx = msgs.lastIndexOf(lastUser);
    void send(lastUser.content, msgs.slice(0, idx));
  };

  const followUps = useMemo(() => suggestions, [suggestions]);

  return (
    <div className="flex flex-col">
      <div className={`${height} max-h-[34rem] space-y-4 overflow-y-auto pr-1`} aria-live="polite">
        {msgs.length === 0 && (
          <div className="grid place-items-center gap-3 py-8 text-center">
            <span className="grid size-11 place-items-center rounded-2xl bg-brand text-accentink shadow-brand"><Sparkles size={20} /></span>
            <p className="max-w-sm text-[13px] text-muted">
              Ask anything about this result, or any factual question. If the evidence here is not enough, I search news, fact-checkers and Wikipedia and cite what I find.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {followUps.map((s) => (
                <button key={s} onClick={() => void send(s)} className="rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-medium text-muted transition hover:border-accent/50 hover:text-ink">{s}</button>
              ))}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`rise flex flex-col gap-1.5 ${m.role === "user" ? "items-end" : "items-start"}`}>
            {m.role === "user" ? (
              <p className="max-w-[88%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand px-4 py-2.5 text-[13.5px] leading-relaxed text-accentink shadow-brand">{m.content}</p>
            ) : (
              <div className="w-full max-w-[96%] space-y-2">
                {(m.tools ?? []).length > 0 && (
                  <ul className="flex flex-wrap gap-1.5">
                    {m.tools!.map((t) => (
                      <li key={t.id}>
                        <Badge tone={t.error ? "warn" : t.done ? "supported" : "accent"} className="gap-1.5">
                          {t.done ? (t.error ? <Globe size={11} /> : <Check size={11} />) : <Loader2 size={11} className="animate-spin" />}
                          {t.label}
                          {t.error && <span className="opacity-80"> (no results)</span>}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                )}
                {(m.content || m.streaming) && (
                  <div className="rounded-2xl rounded-bl-md border border-line bg-surface px-4 py-3 text-[13.5px] leading-relaxed shadow-card">
                    <p className="whitespace-pre-wrap">
                      <Cited text={m.content} sources={sources} onJump={onJump} />
                      {m.streaming && <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse rounded-sm bg-accent align-middle" />}
                    </p>
                    {!m.streaming && m.content && (
                      <div className="mt-2 flex items-center gap-1 text-muted">
                        <button
                          onClick={() => { void navigator.clipboard?.writeText(m.content); setCopied(i); setTimeout(() => setCopied(null), 1400); }}
                          aria-label="Copy answer" className="grid size-6 place-items-center rounded-md hover:bg-surface2 hover:text-ink"
                        >{copied === i ? <Check size={13} /> : <Copy size={13} />}</button>
                        {i === msgs.length - 1 && (
                          <button onClick={retry} aria-label="Try again" className="grid size-6 place-items-center rounded-md hover:bg-surface2 hover:text-ink"><RotateCcw size={13} /></button>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {m.error && <p role="alert" className="rounded-xl border border-refuted/30 bg-refuted/10 px-3 py-2 text-[13px] text-refuted">{m.error}</p>}
                {(m.cited ?? []).length > 0 && (
                  <div className="grid gap-1.5 sm:grid-cols-2">
                    {m.cited!.map((n) => sources.find((s) => s.n === n)).filter((s): s is ChatSource => !!s).map((s) => <SourceCard key={s.n} s={s} />)}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); void send(text); }} className="mt-3 flex items-end gap-2 rounded-2xl border border-line bg-surface p-1.5 pl-4 shadow-card focus-within:border-accent">
        <label htmlFor={`chat-${resetKey}`} className="sr-only">Message</label>
        <textarea
          id={`chat-${resetKey}`} value={text} onChange={(e) => setText(e.target.value)} rows={1} maxLength={1500} placeholder={placeholder}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(text); } }}
          className="max-h-32 min-h-9 flex-1 resize-none self-center bg-transparent py-1.5 text-[13.5px] outline-none placeholder:text-muted/70"
        />
        {busy ? (
          <button type="button" onClick={() => ctl.current?.abort()} aria-label="Stop" className="grid size-9 place-items-center rounded-xl bg-surface2 text-ink"><Square size={14} /></button>
        ) : (
          <button type="submit" disabled={text.trim().length < 2} aria-label="Send" className="grid size-9 place-items-center rounded-xl bg-brand text-accentink shadow-brand disabled:opacity-40"><ArrowUp size={16} /></button>
        )}
      </form>
      <p className="mt-1.5 px-1 text-[11px] text-muted">
        {modelHint ? `${modelHint}. ` : ""}Answers can be wrong; check the cited sources. Your question and the evidence shown are sent to AICredits.
      </p>
    </div>
  );
}
