import { AnimatePresence, motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { DataPage } from "@/features/data/DataPage";
import { InsightsPage } from "@/features/insights/InsightsPage";
import { AnnotatedClaim } from "@/features/verify/AnnotatedClaim";
import { ClaimInput } from "@/features/verify/ClaimInput";
import { ExplanationPanel } from "@/features/verify/ExplanationPanel";
import { OptionsPanel, type Options } from "@/features/verify/OptionsPanel";
import { SemanticMap } from "@/features/verify/SemanticMap";
import { StageDetails } from "@/features/verify/StageDetails";
import { EvidenceList } from "@/features/verify/EvidenceList";
import { PipelineTimeline } from "@/features/verify/PipelineTimeline";
import { useVerify } from "@/features/verify/useVerify";
import { VerdictPanel } from "@/features/verify/VerdictPanel";

type View = "verify" | "data" | "insights";
const VIEWS: { id: View; label: string }[] = [
  { id: "verify", label: "Verify" },
  { id: "data", label: "Data" },
  { id: "insights", label: "Insights" },
];

export default function App() {
  const { status, claim, stages, error, totalMs, run } = useVerify();
  const [view, setView] = useState<View>("verify");
  const [options, setOptions] = useState<Options>({});
  const started = status !== "idle";

  return (
    <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-5 pb-16 sm:px-8">
      <header className="flex items-center justify-between gap-4 py-6">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-accent text-accentink"><ShieldCheck size={19} /></span>
          <span className="hidden font-serif text-xl sm:inline">Evidence Verifier</span>
        </div>
        <nav aria-label="Sections" className="flex gap-1 rounded-full border border-line bg-surface p-1 shadow-card">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              onClick={() => setView(v.id)}
              aria-current={view === v.id ? "page" : undefined}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${view === v.id ? "bg-accent text-accentink" : "text-muted hover:text-ink"}`}
            >
              {v.label}
            </button>
          ))}
        </nav>
        <ThemeToggle />
      </header>

      {view === "data" && <main className="flex-1"><DataPage /></main>}
      {view === "insights" && <main className="flex-1"><InsightsPage /></main>}
      <main className={`flex flex-1 flex-col gap-8 ${view === "verify" ? "" : "hidden"}`}>
        <motion.div layout className={started ? "" : "mt-[12vh]"}>
          {!started && (
            <div className="mb-8 text-center">
              <h1 className="font-serif text-4xl leading-tight sm:text-5xl">Don't just label it. <em className="text-accent">Show the evidence.</em></h1>
              <p className="mx-auto mt-3 max-w-xl text-muted">
                Paste a claim. The pipeline extracts entities, retrieves supporting articles, verifies the claim
                with a language model, and explains why.
              </p>
            </div>
          )}
          <div className="mx-auto max-w-3xl"><ClaimInput running={status === "running"} onSubmit={(c) => run(c, options as Record<string, string>)} /></div>
          <div className="mt-2"><OptionsPanel value={options} onChange={setOptions} /></div>
        </motion.div>

        <AnimatePresence>
          {started && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              <PipelineTimeline stages={stages} />
              {error && (
                <p role="alert" className="rounded-xl border border-refuted/40 bg-refuted/10 px-4 py-3 text-sm text-refuted">{error}</p>
              )}
              <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                <div className="space-y-6">
                  <AnnotatedClaim claim={claim} entities={stages.ner.output?.entities ?? null} placeholder={stages.ner.placeholder} />
                  <ExplanationPanel explanation={stages.explanation.output} placeholder={stages.explanation.placeholder} />
                  <StageDetails pre={stages.preprocess.output} ner={stages.ner.output} kw={stages.keywords.output} />
                  <EvidenceList retrieval={stages.retrieval.output} verification={stages.verification.output} placeholder={stages.retrieval.placeholder} citations={stages.explanation.output?.citations} />
                </div>
                <div className="space-y-6">
                  <VerdictPanel verification={stages.verification.output} placeholder={stages.verification.placeholder} />
                  {stages.retrieval.output?.projection && <SemanticMap projection={stages.retrieval.output.projection} />}
                </div>
              </div>
              {totalMs != null && <p className="text-center font-mono text-xs text-muted">Completed in {Math.round(totalMs)} ms</p>}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
