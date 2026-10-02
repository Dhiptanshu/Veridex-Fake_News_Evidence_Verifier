import { CornerDownLeft, Plus, X } from "lucide-react";
import { useState } from "react";
import { runOnce, type RunResult } from "@/api/run";
import { Badge, Button, LABEL_TEXT, LABEL_TONE, Panel, ProbBar, Select } from "@/components/ui";
import { OptionsGrid, useStageCatalog } from "@/features/verify/OptionsPanel";
import { ResultDetail } from "@/features/verify/ResultDetail";
import { slimRun, usePersistentState } from "@/lib/persist";
import { entryFromRun, useAppState, type Options } from "@/state/AppState";

const PRESETS: { name: string; opts: Options }[] = [
  { name: "Live news + LLM judge (default)", opts: {} },
  { name: "Live news + BERT (offline model)", opts: { verification: "bert" } },
  { name: "Offline Wikipedia + BERT", opts: { retrieval: "dense_bge", verification: "bert" } },
  { name: "Offline Wikipedia + LLM judge", opts: { retrieval: "dense_bge" } },
  { name: "Claim only (ignores evidence)", opts: { retrieval: "dense_bge", verification: "claim_only" } },
  { name: "Offline TF-IDF + BERT", opts: { retrieval: "tfidf", verification: "bert" } },
  { name: "Offline BiLSTM baseline", opts: { retrieval: "dense_bge", verification: "lstm" } },
];
const SLOTS_SHOWN = ["retrieval", "verification", "explanation"] as const;

interface Cfg { id: number; preset: string; options: Options }
interface Outcome { run?: RunResult; error?: string }

export function ComparePage() {
  const { addEntry } = useAppState();
  const catalog = useStageCatalog();
  const [claim, setClaim] = usePersistentState("fnev-compare-claim", "");
  const [cfgs, setCfgs] = usePersistentState<Cfg[]>("fnev-compare-cfgs", [
    { id: 1, preset: PRESETS[0].name, options: PRESETS[0].opts },
    { id: 2, preset: PRESETS[1].name, options: PRESETS[1].opts },
  ], (stored) => {
    const known = new Set([...PRESETS.map((p) => p.name), "Custom"]);
    const ok = (stored as Cfg[]).filter((c) => known.has(c.preset));
    if (ok.length < 2) throw new Error("outdated saved presets");  // fall back to the defaults
    return ok;
  });
  const [outcomes, setOutcomes] = usePersistentState<Record<number, Outcome | "running">>(
    "fnev-compare-out", {}, (stored) => Object.fromEntries(Object.entries(stored as Record<string, Outcome | "running">).filter(([, v]) => v !== "running")),
  );
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);

  const setPreset = (id: number, name: string) => {
    const p = PRESETS.find((x) => x.name === name);
    setCfgs((c) => c.map((x) => (x.id === id ? { ...x, preset: p ? name : "Custom", options: p ? p.opts : x.options } : x)));
  };

  const run = async () => {
    const text = claim.trim();
    if (text.length < 3 || busy) return;
    setBusy(true);
    setOutcomes(Object.fromEntries(cfgs.map((c) => [c.id, "running" as const])));
    await Promise.all(cfgs.map(async (c) => {
      try {
        const r = await runOnce(text, c.options);
        setOutcomes((o) => ({ ...o, [c.id]: { run: slimRun(r) } }));
        if (!r.error) addEntry(entryFromRun(r, "compare"));
      } catch (e) {
        setOutcomes((o) => ({ ...o, [c.id]: { error: (e as Error).message } }));
      }
    }));
    setBusy(false);
  };

  const done = cfgs.map((c) => outcomes[c.id]).filter((o): o is Outcome => !!o && o !== "running");
  const labels = done.map((o) => o.run?.out.verification?.label).filter(Boolean);
  const disagree = labels.length > 1 && new Set(labels).size > 1;

  return (
    <div className="space-y-4">
      <div className="card rounded-[22px] focus-within:border-accent">
        <label htmlFor="cmp-claim" className="sr-only">Claim</label>
        <textarea
          id="cmp-claim" value={claim} onChange={(e) => setClaim(e.target.value)} rows={2} maxLength={2000}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void run(); } }}
          placeholder="One claim, several pipelines: see where they agree and where they do not..."
          className="block w-full resize-none bg-transparent px-4 pb-1 pt-3 text-[15px] leading-snug outline-none placeholder:text-muted/70"
        />
        <div className="flex items-center justify-between border-t border-line px-3 py-2">
          <Button size="sm" variant="ghost" icon={<Plus size={14} />} disabled={cfgs.length >= 3}
            onClick={() => setCfgs((c) => [...c, { id: Math.max(...c.map((x) => x.id)) + 1, preset: PRESETS[2].name, options: PRESETS[2].opts }])}>
            Add pipeline
          </Button>
          <Button variant="primary" onClick={() => void run()} disabled={claim.trim().length < 3} loading={busy} icon={<CornerDownLeft size={14} />}>Run all</Button>
        </div>
      </div>

      {disagree && <p className="rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-[13px] text-warn">The pipelines disagree on this claim.</p>}

      <div className={`grid gap-4 ${cfgs.length === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2"}`}>
        {cfgs.map((c, i) => {
          const o = outcomes[c.id];
          const run = o && o !== "running" ? o.run : undefined;
          const v = run?.out.verification;
          const ret = run?.out.retrieval;
          return (
            <Panel
              key={c.id}
              title={`Pipeline ${String.fromCharCode(65 + i)}`}
              actions={cfgs.length > 2 ? <button aria-label="Remove pipeline" onClick={() => setCfgs((x) => x.filter((y) => y.id !== c.id))} className="text-muted hover:text-ink"><X size={14} /></button> : null}
            >
              <div className="space-y-3">
                <Select ariaLabel="Preset" value={c.preset} onChange={(v) => setPreset(c.id, v)} className="w-full">
                  {PRESETS.map((p) => <option key={p.name}>{p.name}</option>)}
                  {c.preset === "Custom" && <option>Custom</option>}
                </Select>
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted hover:text-ink">Customise stages</summary>
                  <div className="mt-3">
                    <OptionsGrid stacked value={c.options} stages={catalog} slots={SLOTS_SHOWN}
                      onChange={(opts) => setCfgs((x) => x.map((y) => (y.id === c.id ? { ...y, options: opts, preset: "Custom" } : y)))} />
                  </div>
                </details>

                <div className="min-h-40 border-t border-line pt-3">
                  {o === "running" && <p className="text-[13px] text-muted">Running...</p>}
                  {o && o !== "running" && o.error && <p role="alert" className="text-[13px] text-refuted">{o.error}</p>}
                  {run?.error && <p role="alert" className="text-[13px] text-refuted">{run.error}</p>}
                  {v && run && (
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={LABEL_TONE[v.label]} className="px-2 py-1 text-[13px]">{LABEL_TEXT[v.label]}</Badge>
                        <span className="font-mono text-sm text-muted">{(v.confidence * 100).toFixed(0)}%</span>
                        <span className="ml-auto font-mono text-[11px] text-muted">{run.totalMs != null ? `${(run.totalMs / 1000).toFixed(2)}s` : ""}</span>
                      </div>
                      <ProbBar values={[{ label: "supported", value: v.probabilities.supported }, { label: "refuted", value: v.probabilities.refuted }, { label: "not_enough_info", value: v.probabilities.not_enough_info }]} />
                      <p className="font-mono text-[11px] text-muted">{run.impl.retrieval} / {run.impl.verification}</p>
                      {run.out.explanation && <p className="text-[13px] leading-relaxed text-ink/90">{run.out.explanation.rationale.replace(/\[\d+\]/g, "")}</p>}
                      <button onClick={() => setOpen(open === c.id ? null : c.id)} className="text-xs font-semibold text-accent hover:underline">
                        {open === c.id ? "Hide full result" : "Show full result (explanation and all evidence)"}
                      </button>
                      {open === c.id && <div className="rounded-xl border border-line bg-bg/60 p-3"><ResultDetail run={run} /></div>}
                      {ret && open !== c.id && (
                        <div>
                          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted">Top evidence</p>
                          <ul className="space-y-1.5">
                            {ret.evidence.slice(0, 3).map((e) => (
                              <li key={e.id} className="rounded-md border border-line bg-bg/60 px-2.5 py-1.5 text-xs">
                                <span className="font-medium">{e.title}</span> <span className="text-muted">{e.source}</span>
                                <p className="mt-0.5 text-ink/80">{e.sentences[0].text}</p>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                  {!o && <p className="text-[13px] text-muted">Pick a preset, then Run all.</p>}
                </div>
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
