import { Loader2, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchClaims } from "@/api/client";
import type { ClaimPage, ClaimView, Label, SplitName } from "@/api/types";
import { Card } from "@/components/Card";
import { LABEL_META, LABELS } from "./labels";

const PAGE = 15;
const SPLITS: SplitName[] = ["test", "val", "train"];

function ClaimRow({ c }: { c: ClaimView }) {
  const meta = LABEL_META[c.label];
  return (
    <li className="rounded-xl border border-line bg-bg/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="font-serif text-lg leading-snug">{c.claim}</p>
        <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${meta.className}`}>{meta.text}</span>
      </div>
      {c.evidence_sets.length === 0 ? (
        <p className="mt-2 text-xs text-muted">No gold evidence: Wikipedia does not settle this claim.</p>
      ) : (
        c.evidence_sets.slice(0, 2).map((set, i) => (
          <div key={i} className="mt-3 space-y-1.5 border-l-2 border-accent/60 pl-3">
            {c.evidence_sets.length > 1 && <p className="font-mono text-[10px] uppercase tracking-wider text-muted">Evidence set {i + 1}</p>}
            {set.map((e) => (
              <p key={`${e.page}-${e.sent_id}`} className="text-sm leading-relaxed text-ink/90">
                <span className="mr-1.5 font-mono text-[11px] text-accent">{e.title}</span>
                {e.text}
              </p>
            ))}
          </div>
        ))
      )}
    </li>
  );
}

export function ClaimBrowser() {
  const [split, setSplit] = useState<SplitName>("test");
  const [label, setLabel] = useState<Label | undefined>();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [items, setItems] = useState<ClaimView[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  const load = (offset: number, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    return fetchClaims({ split, label, q: debounced, offset, limit: PAGE }, signal)
      .then((p: ClaimPage) => {
        setTotal(p.total);
        setItems((prev) => (offset === 0 ? p.items : [...prev, ...p.items]));
      })
      .catch((e: Error) => e.name !== "AbortError" && setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const ctl = new AbortController();
    load(0, ctl.signal);
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [split, label, debounced]);

  const chip = (active: boolean) =>
    `rounded-full border px-3 py-1 text-xs font-medium transition ${active ? "border-accent bg-accent text-accentink" : "border-line bg-surface text-muted hover:text-ink"}`;

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center gap-2">
        {SPLITS.map((s) => (
          <button key={s} className={chip(split === s)} onClick={() => setSplit(s)}>{s}</button>
        ))}
        <span className="mx-1 h-5 w-px bg-line" />
        <button className={chip(!label)} onClick={() => setLabel(undefined)}>all</button>
        {LABELS.map((l) => (
          <button key={l} className={chip(label === l)} onClick={() => setLabel(l)}>{LABEL_META[l].text}</button>
        ))}
        <label className="ml-auto flex items-center gap-2 rounded-full border border-line bg-bg/60 px-3 py-1.5 text-sm">
          <Search size={14} className="text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search claims"
            aria-label="Search claims"
            className="w-40 bg-transparent outline-none placeholder:text-muted/70"
          />
        </label>
      </div>

      {error && <p role="alert" className="mt-4 rounded-xl border border-refuted/40 bg-refuted/10 px-4 py-3 text-sm text-refuted">{error}</p>}
      <p className="mt-4 font-mono text-xs text-muted">{total.toLocaleString()} matching claims</p>
      <ul className="mt-3 space-y-3">{items.map((c) => <ClaimRow key={c.id} c={c} />)}</ul>

      {items.length < total && (
        <button
          onClick={() => load(items.length)}
          disabled={loading}
          className="mx-auto mt-5 flex items-center gap-2 rounded-full border border-line px-5 py-2 text-sm font-medium hover:bg-surface2 disabled:opacity-50"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          Load more
        </button>
      )}
      {loading && items.length === 0 && <p className="mt-6 text-center text-sm text-muted">Loading...</p>}
    </Card>
  );
}
