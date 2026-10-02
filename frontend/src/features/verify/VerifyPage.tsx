import { AlertTriangle, Brain, FileSearch, ListChecks, Newspaper, ScanSearch, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { SLOTS, type Label, type Slot } from "@/api/types";
import type { RunResult } from "@/api/run";
import { Badge, Empty, LABEL_TEXT, LABEL_TONE, Panel, Tabs } from "@/components/ui";
import { entryFromRun, useAppState, type Options } from "@/state/AppState";
import { readJSON, slimRun, usePersistentState, writeJSON } from "@/lib/persist";
import { AssistantPanel } from "@/features/assistant/AssistantPanel";
import type { ChatSource } from "@/api/chat";
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

const EXAMPLES = [
  "India won the T20 World Cup.",
  "RBI cut the repo rate in its latest policy meeting.",
  "Drinking hot water cures cancer.",
  "Modi held talks with Trump on trade.",
  "The Eiffel Tower is in Berlin.",
];
const STEPS = [
  { icon: FileSearch, title: "Understand", text: "Finds the people, places and key terms, and plans several news searches." },
  { icon: Newspaper, title: "Search", text: "Queries news (India-aware), fact-check sites and Wikipedia background in parallel." },
  { icon: Brain, title: "Judge", text: "An AI judge reads the full articles and weighs how credible each source is." },
  { icon: ListChecks, title: "Explain", text: "Verdict, cited sources, what is missing, and a chat to dig deeper." },
];

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
  const { status, claim, stages, error, totalMs, run, restore } = useVerify();
  const catalog = useStageCatalog();
  const [text, setText] = usePersistentState("fnev-verify-text", "");
  const [options, setOptions] = usePersistentState<Options>("fnev-verify-options", defaults);
  const [optOpen, setOptOpen] = useState(false);
  const [gold, setGold] = usePersistentState<Label | null>("fnev-verify-gold", null);
  const [tab, setTab] = usePersistentState<TabKey>("fnev-verify-tab", "why");
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

  // The last finished result survives a reload.
  useEffect(() => {
    const snap = readJSON<{ claim: string; stages: Stages; totalMs: number | null } | null>("fnev-verify-snap", null);
    if (snap?.claim && snap.stages?.verification?.output) restore(snap);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Every finished run is saved to History.
  useEffect(() => {
    if (status === "done" && runId.current !== savedId.current) {
      savedId.current = runId.current;
      addEntry(entryFromRun(toRunResult(claim, options, stages, totalMs, null), "verify", gold));
      const slim = slimRun(toRunResult(claim, options, stages, totalMs, null));
      const keep = { ...stages, retrieval: { ...stages.retrieval, output: slim.out.retrieval ?? stages.retrieval.output } };
      writeJSON("fnev-verify-snap", { claim, stages: keep, totalMs });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const jumpToSource = (s: ChatSource) => {
    if (s.evidenceId) {
      setTab("evidence");
      setTimeout(() => document.getElementById(`evidence-${s.evidenceId}`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 80);
    } else if (s.url) window.open(s.url, "_blank", "noopener");
  };

  const started = status !== "idle";
  const v = stages.verification.output;
  const ret = stages.retrieval.output;
  const expl = stages.explanation.output;
  const nEvidence = ret ? ret.evidence.reduce((n, e) => n + e.sentences.length, 0) : 0;

  return (
    <div className="space-y-4">
      {!started && (
        <div className="rise space-y-3 pt-2 text-center">
            <p className="mx-auto inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
              <Sparkles size={12} /> Live news, fact-checkers and an AI judge
            </p>
            <h2 className="mx-auto max-w-2xl text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
              Is it true? <span className="text-brand">Check any claim</span> against the evidence.
            </h2>
            <p className="mx-auto max-w-xl text-[14px] text-muted">
              Paste a headline, forward or social-media claim. It searches Indian and global news and fact-check sites, reads the articles, and tells you what the evidence says, with sources.
            </p>
          </div>
      )}
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
        <div className="space-y-8">
          <div className="mx-auto flex max-w-3xl flex-wrap justify-center gap-2">
            {EXAMPLES.map((e) => (
              <button key={e} onClick={() => { setText(e); start(e, null); }} className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-xs font-medium text-muted shadow-card transition hover:border-accent/50 hover:text-ink">{e}</button>
            ))}
          </div>

          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map(({ icon: Icon, title, text: d }, n) => (
              <li key={title} className="rise rounded-2xl border border-line bg-surface p-4 shadow-card" style={{ animationDelay: `${n * 60}ms` }}>
                <span className="grid size-9 place-items-center rounded-xl bg-accent/10 text-accent"><Icon size={17} /></span>
                <p className="mt-3 text-[13.5px] font-semibold">{n + 1}. {title}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{d}</p>
              </li>
            ))}
          </ol>

          {history.length > 0 && (
            <Panel title="Recent" actions={<button onClick={() => go("history")} className="text-xs font-medium text-accent hover:underline">All history</button>} flush>
              <ul className="divide-y divide-line">
                {history.slice(0, 5).map((h) => (
                  <li key={h.id}>
                    <button onClick={() => { setText(h.claim); setGold(h.goldLabel ?? null); }} className="flex w-full items-start justify-between gap-3 px-5 py-3 text-left text-[13px] hover:bg-surface2">
                      <span className="line-clamp-2">{h.claim}</span>
                      {h.label && <Badge tone={LABEL_TONE[h.label]} className="shrink-0">{LABEL_TEXT[h.label]}</Badge>}
                    </button>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
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
                <AssistantPanel claim={claim} verification={v} explanation={expl} retrieval={ret} onJump={jumpToSource} />
              ) : (
                <Panel title="Ask Vera"><p className="text-[13px] text-muted">Vera can answer follow-up questions once the check finishes.</p></Panel>
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
