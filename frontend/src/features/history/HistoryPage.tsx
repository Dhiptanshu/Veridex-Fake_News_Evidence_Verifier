import { Download, History as HistoryIcon, RotateCcw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type { Label } from "@/api/types";
import { Badge, Button, Empty, LABEL_COLOR, LABEL_TEXT, LABEL_TONE, Panel, Select, Stat } from "@/components/ui";
import { download, stamp, toCSV } from "@/lib/download";
import { useAppState } from "@/state/AppState";

export function HistoryPage({ go }: { go: (r: "verify") => void }) {
  const { history, removeEntry, clearHistory, setDraft } = useAppState();
  const [q, setQ] = useState("");
  const [label, setLabel] = useState<"all" | Label>("all");
  const [source, setSource] = useState<"all" | "verify" | "batch" | "compare">("all");
  const [open, setOpen] = useState<string | null>(null);

  const rows = useMemo(() => history.filter((h) =>
    (label === "all" || h.label === label) && (source === "all" || h.source === source) && (!q || h.claim.toLowerCase().includes(q.toLowerCase())),
  ), [history, q, label, source]);

  const counts = useMemo(() => {
    const c = { supported: 0, refuted: 0, not_enough_info: 0 } as Record<Label, number>;
    history.forEach((h) => { if (h.label) c[h.label] += 1; });
    return c;
  }, [history]);
  const graded = history.filter((h) => h.goldLabel && h.label);
  const agree = graded.filter((h) => h.goldLabel === h.label).length;

  const exportRows = () => rows.map((h) => ({
    time: new Date(h.ts).toISOString(), source: h.source, claim: h.claim, verdict: h.label ?? "", confidence: h.confidence?.toFixed(4) ?? "",
    fever_label: h.goldLabel ?? "", retrieval: h.impl.retrieval ?? "", verification: h.impl.verification ?? "",
    seconds: h.totalMs != null ? (h.totalMs / 1000).toFixed(2) : "", rationale: h.rationale ?? "",
  }));
  const cols = ["time", "source", "claim", "verdict", "confidence", "fever_label", "retrieval", "verification", "seconds", "rationale"];

  if (history.length === 0) {
    return <Panel><Empty icon={<HistoryIcon size={18} />} title="Nothing here yet">Claims you verify, compare or run in batch are saved in this browser and listed here.</Empty></Panel>;
  }

  return (
    <div className="space-y-4">
      <Panel>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <Stat label="Runs" value={history.length} />
          {(["supported", "refuted", "not_enough_info"] as Label[]).map((l) => (
            <Stat key={l} label={LABEL_TEXT[l]} value={<span style={{ color: LABEL_COLOR[l] }}>{counts[l]}</span>} />
          ))}
          <Stat label="Agree with FEVER label" value={graded.length ? `${((agree / graded.length) * 100).toFixed(0)}%` : "n/a"} hint={graded.length ? `${agree}/${graded.length} labelled runs` : "no labelled runs yet"} />
        </div>
      </Panel>

      <Panel
        flush title={`${rows.length} run${rows.length === 1 ? "" : "s"}`}
        actions={<>
          <Button size="sm" variant="ghost" icon={<Download size={14} />} onClick={() => download(`history-${stamp()}.csv`, toCSV(exportRows(), cols), "text/csv")}>CSV</Button>
          <Button size="sm" variant="ghost" icon={<Download size={14} />} onClick={() => download(`history-${stamp()}.json`, JSON.stringify(rows, null, 2), "application/json")}>JSON</Button>
          <Button size="sm" variant="ghost" icon={<Trash2 size={14} />} onClick={() => { if (confirm(`Delete all ${history.length} saved runs from this browser?`)) clearHistory(); }}>Clear</Button>
        </>}
      >
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5">
          <input
            value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search claims" aria-label="Search claims"
            className="h-8 w-56 rounded-md border border-line bg-bg/60 px-2.5 text-[13px] outline-none focus:border-accent"
          />
          <Select ariaLabel="Verdict" value={label} onChange={(v) => setLabel(v as typeof label)}>
            <option value="all">All verdicts</option><option value="supported">Supported</option><option value="refuted">Refuted</option><option value="not_enough_info">Not enough info</option>
          </Select>
          <Select ariaLabel="Source" value={source} onChange={(v) => setSource(v as typeof source)}>
            <option value="all">All sources</option><option value="verify">Verify</option><option value="batch">Batch</option><option value="compare">Compare</option>
          </Select>
        </div>
        <ul className="divide-y divide-line">
          {rows.map((h) => (
            <li key={h.id}>
              <div className="flex items-start gap-3 px-4 py-2.5">
                <button onClick={() => setOpen(open === h.id ? null : h.id)} className="min-w-0 flex-1 text-left">
                  <p className="text-[13px] font-medium">{h.claim}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted">
                    <span>{new Date(h.ts).toLocaleString()}</span>
                    <Badge>{h.source}</Badge>
                    {h.impl.retrieval && <span className="font-mono">{h.impl.retrieval} / {h.impl.verification}</span>}
                    {h.totalMs != null && <span className="font-mono">{(h.totalMs / 1000).toFixed(1)}s</span>}
                    {h.goldLabel && <span>FEVER: {LABEL_TEXT[h.goldLabel]}</span>}
                  </p>
                </button>
                <div className="flex shrink-0 items-center gap-2">
                  {h.label ? <Badge tone={LABEL_TONE[h.label]}>{LABEL_TEXT[h.label]} {h.confidence != null && `${(h.confidence * 100).toFixed(0)}%`}</Badge> : <Badge tone="refuted">error</Badge>}
                  <Button size="sm" variant="ghost" icon={<RotateCcw size={13} />} aria-label="Run again" onClick={() => { setDraft(h.claim); go("verify"); }}>Re-run</Button>
                  <button aria-label="Delete run" onClick={() => removeEntry(h.id)} className="text-muted hover:text-refuted"><Trash2 size={14} /></button>
                </div>
              </div>
              {open === h.id && (
                <div className="border-t border-line bg-bg/60 px-4 py-3 text-[13px] leading-relaxed">
                  {h.rationale && <p>{h.rationale}</p>}
                  {h.topSource && (
                    <p className="mt-2 text-muted">Top source: <b className="text-ink">{h.topSource.title}</b> {h.topSource.url && <a className="text-accent hover:underline" href={h.topSource.url} target="_blank" rel="noreferrer">open</a>}</p>
                  )}
                  {h.error && <p className="text-refuted">{h.error}</p>}
                </div>
              )}
            </li>
          ))}
          {rows.length === 0 && <li className="px-4 py-8 text-center text-[13px] text-muted">No runs match these filters.</li>}
        </ul>
      </Panel>
    </div>
  );
}
