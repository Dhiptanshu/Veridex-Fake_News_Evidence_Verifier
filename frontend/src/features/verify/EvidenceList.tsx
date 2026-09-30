import { motion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import type { RetrievalOut, VerificationOut } from "@/api/types";
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
  retrieval, verification, placeholder,
}: { retrieval: RetrievalOut | null; verification: VerificationOut | null; placeholder: boolean }) {
  return (
    <Card className="p-6">
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
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                className="rounded-xl border border-line bg-bg/60 p-4"
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
                {ev.sentences.map((s, j) => (
                  <p key={j} className="mt-3 border-l-2 border-accent/60 pl-3 text-sm leading-relaxed text-ink/90">{s.text}</p>
                ))}
              </motion.li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
