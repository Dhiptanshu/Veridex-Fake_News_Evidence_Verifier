import { AlertTriangle, History as HistoryIcon, ScanSearch } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { SLOTS, type Label, type Slot } from "@/api/types";
import type { RunResult } from "@/api/run";
import { Badge, Empty, LABEL_TEXT, LABEL_TONE, Panel, Tabs } from "@/components/ui";
import { entryFromRun, useAppState, type Options } from "@/state/AppState";
import { AskPanel } from "./AskPanel";
import { ClaimBar } from "./ClaimBar";
import { EvidenceList } from "./EvidenceList";
import { ExplanationPanel } from "./ExplanationPanel";
import { countChanged, OptionsGrid, useStageCatalog } from "./OptionsPanel";
import { PipelineTimeline } from "./PipelineTimeline";
import { ResultHeader } from "./ResultHeader";
import { SemanticMap } from "./SemanticMap";
import { StageDetails } from "./StageDetails";
import { useVerify, type Stages } from "./useVerify";

type TabKey = "why" | "evidence" | "pipeline" | "map";

function toRunResult(claim: string, options: Options, stages: Stages, totalMs: number | null, error: string | null): RunResult {
  const r: RunResult = { claim, options, impl: {}, out: {}, stageMs: {}, totalMs, error };
  for (const s of SLOTS as Slot[]) {
    const st = stages[s];
    if (st.output) (r.out as Record<string, unknown>)[s] = st.output;
    if (st.impl) r.impl[s] = st.impl;
    if (st.elapsedMs != null) r.stageMs[s] = st.elapsedMs;
  }
  return r;
}

export function VerifyPage({ go }: { go: (r: "history") => void }) {
  const { defaults, addEntry, draft, setDraft, history } = useAppState();
  const { status, claim, stages, error, totalMs, run } = useVerify();
  const catalog = useStageCatalog();
  const [text, setText] = useState("");
  const [options, setOptions] = useState<Options>(defaults);
  const [optOpen, setOptOpen] = useState(false);
  const [gold, setGold] = useState<Label | null>(null);
  const [tab, setTab] = useState<TabKey>("why");
  const runId = useRef(0);
  const savedId = useRef(0);

  const start = (c: string, g: Label | null) => {
    runId.current += 1;
    setGold(g);
    setTab("why");
    void run(c, options as Record<string, string>);
  };

  // A claim sent from History ("re-run") starts immediately.
  useEffect(() => {
    if (draft) { setText(draft); setDraft(null); start(draft, null); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  // Every finished run is saved to History.
  useEffect(() => {
    if (status === "done" && runId.current !== savedId.current) {
      savedId.current = runId.current;
      addEntry(entryFromRun(toRunResult(claim, options, stages, totalMs, null), "verify", gold));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const started = status !== "idle";
  const v = stages.verification.output;
  const ret = stages.retrieval.output;
  const expl = stages.explanation.output;
  const nEvidence = ret ? ret.evidence.reduce((n, e) => n + e.sentences.length, 0) : 0;

  return (
    <div className="space-y-4">
      <ClaimBar
        value={text} onChange={setText} running={status === "running"} onRun={start}
        optionsOpen={optOpen} onToggleOptions={() => setOptOpen((o) => !o)} changedOptions={countChanged(options)}
      />
      {optOpen && (
        <Panel title="Pipeline options" actions={countChanged(options) > 0 ? <button onClick={() => setOptions({})} className="text-xs text-accent hover:underline">Reset to defaults</button> : null}>
          <OptionsGrid value={options} onChange={setOptions} stages={catalog} />
        </Panel>
      )}

      {!started && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <Panel title="How a claim is checked">
            <ol className="space-y-3 text-[13px]">
              {[
                ["Analyse", "Tokenise, tag parts of speech, find named entities and the keywords that matter (NLTK, spaCy, TF-IDF, PMI)."],
                ["Retrieve", "Find the sentences that bear on the claim, from 372k Wikipedia sentences or live Wikipedia and news (BGE embeddings)."],
                ["Verify", "A fine-tuned BERT reads the claim against each sentence; a stacker combines them into supported / refuted / not enough info."],
                ["Explain", "Cite the decisive sentences, show which words mattered, and let you ask follow-up questions."],
              ].map(([t, d], i) => (
                <li key={t} className="grid grid-cols-[1.5rem_1fr] gap-2">
                  <span className="grid size-5 place-items-center rounded bg-surface2 font-mono text-[11px] text-muted">{i + 1}</span>
                  <p><b className="font-semibold">{t}.</b> <span className="text-muted">{d}</span></p>
                </li>
              ))}
            </ol>
            <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
              Tip: use <b>Real FEVER claims</b> above to test against ground truth, <b>Compare</b> to see two pipelines side by side, or <b>Batch</b> for many claims at once.
            </p>
          </Panel>
          <Panel title="Recent" actions={history.length > 0 ? <button onClick={() => go("history")} className="text-xs text-accent hover:underline">All history</button> : null} flush>
            {history.length === 0 ? (
              <Empty icon={<HistoryIcon size={18} />} title="No runs yet">Every claim you verify is saved here, in your browser only.</Empty>
            ) : (
              <ul className="divide-y divide-line">
                {history.slice(0, 6).map((h) => (
                  <li key={h.id}>
                    <button onClick={() => { setText(h.claim); setGold(h.goldLabel ?? null); }} className="flex w-full items-start justify-between gap-3 px-4 py-2.5 text-left text-[13px] hover:bg-surface2">
                      <span className="line-clamp-2">{h.claim}</span>
                      {h.label && <Badge tone={LABEL_TONE[h.label]} className="shrink-0">{LABEL_TEXT[h.label]}</Badge>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      )}

      {started && (
        <>
          <PipelineTimeline stages={stages} />
          {error && (
            <p role="alert" className="flex items-start gap-2 rounded-lg border border-refuted/30 bg-refuted/10 px-3 py-2.5 text-[13px] text-refuted">
              <AlertTriangle size={15} className="mt-0.5 shrink-0" /> {error}
            </p>
          )}
          <ResultHeader claim={claim} stages={stages} totalMs={totalMs} gold={gold} />

          <Tabs
            value={tab} onChange={setTab}
            tabs={[
              { value: "why", label: "Explanation" },
              { value: "evidence", label: "Evidence", count: nEvidence || undefined },
              { value: "pipeline", label: "Pipeline" },
              { value: "map", label: "Semantic map" },
            ]}
          />

          {tab === "why" && (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
              <ExplanationPanel explanation={expl} placeholder={stages.explanation.placeholder} />
              {status === "done" && v && expl && ret ? (
                <AskPanel claim={claim} verification={v} explanation={expl} retrieval={ret} />
              ) : (
                <Panel title="Ask about this result"><p className="text-[13px] text-muted">Available once the run finishes.</p></Panel>
              )}
            </div>
          )}
          {tab === "evidence" && <EvidenceList retrieval={ret} verification={v} placeholder={stages.retrieval.placeholder} citations={expl?.citations} />}
          {tab === "pipeline" && <StageDetails pre={stages.preprocess.output} ner={stages.ner.output} kw={stages.keywords.output} />}
          {tab === "map" && (
            ret?.projection ? <SemanticMap projection={ret.projection} /> : (
              <Panel><Empty icon={<ScanSearch size={18} />} title="No semantic map for this retriever">The map needs dense embeddings. Choose a BGE or MiniLM retriever in Options.</Empty></Panel>
            )
          )}
        </>
      )}
    </div>
  );
}
