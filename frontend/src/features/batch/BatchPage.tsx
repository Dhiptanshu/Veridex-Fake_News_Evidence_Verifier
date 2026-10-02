import { Download, Play, Square, Upload } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import type { Label } from "@/api/types";
import { runOnce, type RunResult } from "@/api/run";
import { CheckCircle2, CircleHelp, ListChecks as ListIcon, Timer, XCircle } from "lucide-react";
import { Badge, Button, Empty, LABEL_TEXT, LABEL_TONE, Panel, StatCard } from "@/components/ui";
import { download, stamp, toCSV } from "@/lib/download";
import { OptionsGrid, useStageCatalog } from "@/features/verify/OptionsPanel";
import { ResultDetail } from "@/features/verify/ResultDetail";
import { slimRun, usePersistentState } from "@/lib/persist";
import { entryFromRun, useAppState, type Options } from "@/state/AppState";

const MAX = 100;
const LABEL_WORDS: Record<string, Label> = { supported: "supported", refuted: "refuted", not_enough_info: "not_enough_info", nei: "not_enough_info", "not enough info": "not_enough_info" };

interface Row { n: number; claim: string; gold: Label | null; status: "queued" | "running" | "done" | "error"; run?: RunResult; error?: string }

/** One claim per line. Optional ground truth after a tab or a final comma: `claim<TAB>supported`. */
export function parseLines(text: string): { claim: string; gold: Label | null }[] {
  return text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).map((line) => {
    const tab = line.split("\t");
    if (tab.length >= 2 && LABEL_WORDS[tab[tab.length - 1].trim().toLowerCase()]) {
      return { claim: tab.slice(0, -1).join(" ").trim().replace(/^"|"$/g, ""), gold: LABEL_WORDS[tab[tab.length - 1].trim().toLowerCase()] };
    }
    const m = /^(.*),\s*"?(supported|refuted|not_enough_info|nei|not enough info)"?$/i.exec(line);
    if (m) return { claim: m[1].trim().replace(/^"|"$/g, ""), gold: LABEL_WORDS[m[2].toLowerCase()] };
    return { claim: line.replace(/^"|"$/g, ""), gold: null };
  });
}

export function BatchPage() {
  const { addEntry } = useAppState();
  const catalog = useStageCatalog();
  const [text, setText] = usePersistentState("fnev-batch-text", "");
  const [options, setOptions] = usePersistentState<Options>("fnev-batch-options", {});
  // a batch that was running when the page was reloaded cannot continue: mark its unfinished rows instead of leaving them "running"
  const [rows, setRows] = usePersistentState<Row[]>("fnev-batch-rows", [], (stored) =>
    (stored as Row[]).map((r) => (r.status === "queued" || r.status === "running" ? { ...r, status: "error" as const, error: "Interrupted (page was reloaded)" } : r)));
  const [running, setRunning] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const cancel = useRef(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const parsed = useMemo(() => parseLines(text), [text]);
  const tooMany = parsed.length > MAX;

  const start = async () => {
    const items = parsed.slice(0, MAX);
    if (!items.length || running) return;
    cancel.current = false;
    setRunning(true);
    setOpen(null);
    setRows(items.map((it, i) => ({ n: i + 1, claim: it.claim, gold: it.gold, status: "queued" })));
    let next = 0;
    const worker = async () => {
      while (!cancel.current) {
        const i = next++;
        if (i >= items.length) return;
        setRows((r) => r.map((x) => (x.n === i + 1 ? { ...x, status: "running" } : x)));
        try {
          const run = await runOnce(items[i].claim, options);
          setRows((r) => r.map((x) => (x.n === i + 1 ? { ...x, status: run.error ? "error" : "done", run: slimRun(run), error: run.error ?? undefined } : x)));
          if (!run.error) addEntry(entryFromRun(run, "batch", items[i].gold));
        } catch (e) {
          setRows((r) => r.map((x) => (x.n === i + 1 ? { ...x, status: "error", error: (e as Error).message } : x)));
        }
      }
    };
    await Promise.all([worker(), worker()]);  // two claims in flight at a time
    setRunning(false);
  };

  const onFile = async (f: File | undefined) => { if (f) setText(await f.text()); };

  const done = rows.filter((r) => r.status === "done");
  const counts = { supported: 0, refuted: 0, not_enough_info: 0 } as Record<Label, number>;
  done.forEach((r) => { const l = r.run?.out.verification?.label; if (l) counts[l] += 1; });
  const scored = done.filter((r) => r.gold && r.run?.out.verification);
  const correct = scored.filter((r) => r.run!.out.verification!.label === r.gold).length;
  const meanMs = done.length ? done.reduce((a, r) => a + (r.run?.totalMs ?? 0), 0) / done.length : 0;
  const progress = rows.length ? Math.round(((rows.filter((r) => r.status === "done" || r.status === "error").length) / rows.length) * 100) : 0;

  const exportRows = () => rows.map((r) => {
    const v = r.run?.out.verification;
    const first = r.run?.out.explanation?.citations[0];
    return {
      claim: r.claim, verdict: v?.label ?? "", confidence: v ? v.confidence.toFixed(4) : "", gold_label: r.gold ?? "",
      correct: r.gold && v ? String(v.label === r.gold) : "", top_source: first?.title ?? "", top_sentence: first?.text ?? "",
      rationale: r.run?.out.explanation?.rationale ?? "", seconds: r.run?.totalMs != null ? (r.run.totalMs / 1000).toFixed(2) : "", error: r.error ?? "",
    };
  });
  const cols = ["claim", "verdict", "confidence", "gold_label", "correct", "top_source", "top_sentence", "rationale", "seconds", "error"];

  return (
    <div className="space-y-4">
      <Panel
        title="Claims"
        actions={<>
          <input ref={fileRef} type="file" accept=".txt,.csv,.tsv,text/plain" className="hidden" onChange={(e) => void onFile(e.target.files?.[0])} />
          <Button size="sm" variant="ghost" icon={<Upload size={14} />} onClick={() => fileRef.current?.click()}>Upload .txt / .csv</Button>
        </>}
      >
        <label htmlFor="batch" className="sr-only">Claims, one per line</label>
        <textarea
          id="batch" value={text} onChange={(e) => setText(e.target.value)} rows={7}
          placeholder={"One claim per line, e.g.\nMarie Curie won two Nobel Prizes.\nThe capital of Australia is Sydney.\n\nOptional ground truth after a tab or comma: Paris is the capital of Germany.,refuted"}
          className="block w-full resize-y rounded-md border border-line bg-bg/60 p-3 font-mono text-[14px] leading-relaxed outline-none focus:border-accent"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted">
            {parsed.length} claim{parsed.length === 1 ? "" : "s"}
            {parsed.some((p) => p.gold) && ` (${parsed.filter((p) => p.gold).length} with a label: accuracy will be computed)`}
            {tooMany && <span className="text-refuted"> . Only the first {MAX} will run.</span>}
          </p>
          <div className="flex items-center gap-2">
            {running && <Button size="sm" icon={<Square size={13} />} onClick={() => { cancel.current = true; }}>Stop</Button>}
            <Button variant="primary" icon={<Play size={14} />} onClick={() => void start()} disabled={!parsed.length} loading={running}>Run batch</Button>
          </div>
        </div>
        <details className="mt-3 text-xs">
          <summary className="cursor-pointer text-muted hover:text-ink">Pipeline options</summary>
          <div className="mt-3"><OptionsGrid value={options} onChange={setOptions} stages={catalog} /></div>
        </details>
      </Panel>

      {rows.length > 0 && (
        <>
          <div className="space-y-4">
            <div className="h-2 overflow-hidden rounded-full bg-surface2"><div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${progress}%` }} /></div>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <StatCard icon={<ListIcon size={22} />} value={`${rows.filter((r) => r.status === "done").length}/${rows.length}`} label="Completed" hint={running ? "running..." : "claims checked"} />
              <StatCard icon={<CheckCircle2 size={22} />} value={counts.supported} label="Supported" tint="var(--supported)" />
              <StatCard icon={<XCircle size={22} />} value={counts.refuted} label="Refuted" tint="var(--refuted)" />
              <StatCard icon={<CircleHelp size={22} />} value={counts.not_enough_info} label="Not enough info" tint="var(--neutral)" />
              <StatCard
                icon={<Timer size={22} />} tint="var(--warn)"
                value={scored.length ? `${((correct / scored.length) * 100).toFixed(0)}` : (meanMs / 1000).toFixed(1)} unit={scored.length ? "%" : "s"}
                label={scored.length ? "Accuracy" : "Mean time"} hint={scored.length ? `${correct}/${scored.length} labelled` : "per claim"}
              />
            </div>
          </div>
          <Panel
            title="Results" flush
            actions={<>
              <Button size="sm" variant="ghost" icon={<Download size={14} />} onClick={() => download(`verdicts-${stamp()}.csv`, toCSV(exportRows(), cols), "text/csv")}>CSV</Button>
              <Button size="sm" variant="ghost" icon={<Download size={14} />} onClick={() => download(`verdicts-${stamp()}.json`, JSON.stringify(exportRows(), null, 2), "application/json")}>JSON</Button>
            </>}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-[14px]">
                <thead>
                  <tr className="border-b border-line text-left text-[12px] uppercase tracking-wide text-muted">
                    <th className="w-10 px-4 py-2 font-medium">#</th><th className="px-2 py-2 font-medium">Claim</th>
                    <th className="px-2 py-2 font-medium">Verdict</th><th className="px-2 py-2 font-medium">Conf.</th>
                    <th className="px-2 py-2 font-medium">Label</th><th className="px-4 py-2 text-right font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const v = r.run?.out.verification;
                    return (
                      <>
                        <tr key={r.n} onClick={() => setOpen(open === r.n ? null : r.n)} className="cursor-pointer border-b border-line hover:bg-surface2">
                          <td className="px-4 py-2 font-mono text-xs text-muted">{r.n}</td>
                          <td className="max-w-md px-2 py-2"><span className="line-clamp-2">{r.claim}</span></td>
                          <td className="px-2 py-2">
                            {r.status === "queued" && <span className="text-xs text-muted">queued</span>}
                            {r.status === "running" && <span className="text-xs text-accent">running...</span>}
                            {r.status === "error" && <Badge tone="refuted">error</Badge>}
                            {v && <Badge tone={LABEL_TONE[v.label]}>{LABEL_TEXT[v.label]}</Badge>}
                          </td>
                          <td className="px-2 py-2 font-mono text-xs">{v ? `${(v.confidence * 100).toFixed(0)}%` : ""}</td>
                          <td className="px-2 py-2">
                            {r.gold && (v ? <Badge tone={v.label === r.gold ? "supported" : "refuted"}>{LABEL_TEXT[r.gold]}</Badge> : <span className="text-xs text-muted">{LABEL_TEXT[r.gold]}</span>)}
                          </td>
                          <td className="px-4 py-2 text-right font-mono text-xs text-muted">{r.run?.totalMs != null ? `${(r.run.totalMs / 1000).toFixed(1)}s` : ""}</td>
                        </tr>
                        {open === r.n && (
                          <tr key={`${r.n}-d`} className="border-b border-line bg-bg/60">
                            <td />
                            <td colSpan={5} className="px-2 py-4 text-[14px] leading-relaxed">
                              {r.error && <p className="mb-2 text-refuted">{r.error}</p>}
                              {r.run && !r.run.error && <ResultDetail run={r.run} />}
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
      {rows.length === 0 && <Panel><Empty icon={<Play size={18} />} title="No batch run yet">Paste claims or upload a file. Add a label after each claim to get an accuracy score for your own dataset.</Empty></Panel>}
    </div>
  );
}
