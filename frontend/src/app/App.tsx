import { AnimatePresence, motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AnnotatedClaim } from "@/features/verify/AnnotatedClaim";
import { ClaimInput } from "@/features/verify/ClaimInput";
import { EvidenceList } from "@/features/verify/EvidenceList";
import { PipelineTimeline } from "@/features/verify/PipelineTimeline";
import { useVerify } from "@/features/verify/useVerify";
import { VerdictPanel } from "@/features/verify/VerdictPanel";

export default function App() {
  const { status, claim, stages, error, totalMs, run } = useVerify();
  const started = status !== "idle";

  return (
    <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-5 pb-16 sm:px-8">
      <header className="flex items-center justify-between py-6">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-accent text-accentink"><ShieldCheck size={19} /></span>
          <span className="font-serif text-xl">Evidence Verifier</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="flex flex-1 flex-col gap-8">
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
          <div className="mx-auto max-w-3xl"><ClaimInput running={status === "running"} onSubmit={(c) => run(c)} /></div>
        </motion.div>

        <AnimatePresence>
          {started && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              <PipelineTimeline stages={stages} />
              {error && (
                <p role="alert" className="rounded-xl border border-refuted/40 bg-refuted/10 px-4 py-3 text-sm text-refuted">{error}</p>
              )}
              <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
                <div className="space-y-6">
                  <AnnotatedClaim claim={claim} entities={stages.ner.output?.entities ?? null} placeholder={stages.ner.placeholder} />
                  <EvidenceList retrieval={stages.retrieval.output} verification={stages.verification.output} placeholder={stages.retrieval.placeholder} />
                </div>
                <VerdictPanel verification={stages.verification.output} explanation={stages.explanation.output} placeholder={stages.verification.placeholder} />
              </div>
              {totalMs != null && <p className="text-center font-mono text-xs text-muted">Completed in {Math.round(totalMs)} ms</p>}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
