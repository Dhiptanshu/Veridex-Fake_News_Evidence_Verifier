import { motion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import type { Citation, RetrievalOut, VerificationOut } from "@/api/types";
import { Card, Eyebrow, PlaceholderTag } from "@/components/Card";

function StanceBar({ s, r, n }: { s: number; r: number; n: number }) {
  return (
    <div className="flex h-1.5 w-28 overflow-hidden rounded-full bg-surface2" role="img"
      aria-label={`supports ${Math.round(s * 100)}%, refutes ${Math.round(r * 100)}%, neutral ${Math.round(n * 100)}%`}>
      <motion.span className="bg-supported" initial={{ width: 0 }} animate={{ width: `${s * 100}%` }} />
      <motion.span className="bg-refuted" initial={{ width: 0 }} animate={{ width: `${r * 100}%` }} />
      <motion.span className="bg-neutral/60" initial={{ width: 0 }} animate={{ width: `${n * 100}%` }} />
    </div>
  );
}

export function EvidenceList({
  retrieval, verification, placeholder, citations = [],
}: { retrieval: RetrievalOut | null; verification: VerificationOut | null; placeholder: boolean; citations?: Citation[] }) {
  return (
    <Card className="p-4">
      <div className="mb-4 flex items-center gap-2">
        <Eyebrow>Evidence</Eyebrow>
        {retrieval && placeholder && <PlaceholderTag />}
        {retrieval?.score_entropy != null && (
          <span className="ml-auto font-mono text-[11px] text-muted">score entropy {retrieval.score_entropy.toFixed(2)} bits</span>
        )}
      </div>
      {!retrieval ? (
        <p className="text-sm text-muted">Waiting for the retriever...</p>
      ) : (
        <ul className="space-y-3">
          {retrieval.evidence.map((ev, i) => {
            const v = verification?.per_evidence.find((p) => p.evidence_id === ev.id);
            return (
              <motion.li
                key={ev.id}
                id={`evidence-${ev.id}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                className="rounded-md border border-line bg-bg/60 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h4 className="flex items-center gap-2 font-medium">
                      <span className="truncate">{ev.title}</span>
                      {ev.topic && (
                        <span title={`LDA topic ${ev.topic.id}: ${ev.topic.words.join(", ")}`} className="shrink-0 rounded-full border border-line px-2 py-0.5 text-[10px] font-normal text-muted">
                          {ev.topic.label}
                        </span>
                      )}
                    </h4>
                    <p className="mt-0.5 flex items-center gap-1.5 font-mono text-[11px] text-muted">
                      {ev.source} · score {ev.score.toFixed(3)}
                      {ev.url && (
                        <a href={ev.url} target="_blank" rel="noreferrer" aria-label="Open source" className="text-accent">
                          <ExternalLink size={11} />
                        </a>
                      )}
                    </p>
                  </div>
                  {v && <StanceBar s={v.supported} r={v.refuted} n={v.neutral} />}
                </div>
                {ev.sentences.map((s, j) => {
                  const cite = citations.find((c) => c.evidence_id === ev.id && c.text === s.text);
                  return (
                    <p
                      key={j}
                      className={`mt-3 border-l-2 pl-3 text-sm leading-relaxed ${cite ? "border-accent bg-accent/10 py-1 pr-2 text-ink" : "border-accent/30 text-ink/80"}`}
                    >
                      {cite && (
                        <span className="mr-2 inline-grid size-5 place-items-center rounded-full bg-accent align-text-top text-[11px] font-semibold text-accentink" title={`cited as [${cite.n}] (${cite.role})`}>
                          {cite.n}
                        </span>
                      )}
                      {s.text}
                    </p>
                  );
                })}
              </motion.li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
