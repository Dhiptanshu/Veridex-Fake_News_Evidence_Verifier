import { motion } from "framer-motion";
import { Fragment } from "react";
import type { Attribution, Citation, ExplanationOut, WordScore } from "@/api/types";
import { Card, Eyebrow, PlaceholderTag } from "@/components/Card";

/** Scrolls to the evidence card of a citation. */
function jumpTo(evidenceId: string) {
  // several tabs stay mounted, so the same evidence id can exist more than once: scroll to the one that is visible
  const el = [...document.querySelectorAll<HTMLElement>(`[id="evidence-${CSS.escape(evidenceId)}"]`)].find((e) => e.offsetParent !== null);
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function CiteChip({ c, onClick }: { c: Citation; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title={`${c.title}: ${c.text}`}
      className="mx-0.5 inline-grid size-5 place-items-center rounded-full bg-accent align-text-top text-[11px] font-semibold text-accentink transition hover:brightness-110"
    >
      {c.n}
    </button>
  );
}

/** The rationale is plain text with [n] markers; turn each marker into a chip that jumps to its evidence. */
function Rationale({ text, citations }: { text: string; citations: Citation[] }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p className="text-[15px] leading-relaxed text-ink/90">
      {parts.map((p, i) => {
        const m = /^\[(\d+)\]$/.exec(p);
        const c = m ? citations.find((x) => x.n === Number(m[1])) : undefined;
        return c ? <CiteChip key={i} c={c} onClick={() => jumpTo(c.evidence_id)} /> : <Fragment key={i}>{p}</Fragment>;
      })}
    </p>
  );
}

function Heat({ words }: { words: WordScore[] }) {
  return (
    <span className="leading-8">
      {words.map((w, i) => (
        <motion.span
          key={i}
          initial={{ backgroundColor: "transparent" }}
          animate={{ backgroundColor: `color-mix(in srgb, var(--accent) ${Math.round(w.score * 75)}%, transparent)` }}
          transition={{ delay: 0.04 * i, duration: 0.5 }}
          title={`importance ${w.score.toFixed(2)}`}
          className="mr-1 rounded px-1"
        >
          {w.word}
        </motion.span>
      ))}
    </span>
  );
}

function Why({ a, citations }: { a: Attribution; citations: Citation[] }) {
  const cite = citations.find((c) => c.n === a.cite);
  const ranked = [...a.claim, ...a.evidence].sort((x, y) => y.score - x.score).filter((w) => w.score > 0.15).slice(0, 4);
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">
        Words that mattered. Each word was deleted in turn; the darker it is, the more the verdict weakened without it.
      </p>
      <div>
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">Claim</p>
        <p className="text-base font-medium"><Heat words={a.claim} /></p>
      </div>
      <div>
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">
          Evidence [{a.cite}]{cite ? `, ${cite.title}` : ""}
        </p>
        <p className="text-sm"><Heat words={a.evidence} /></p>
      </div>
      {ranked.length > 0 && (
        <p className="text-xs text-muted">
          Most decisive: {ranked.map((w) => `${w.word.replace(/[.,;:]+$/, "")} (${w.score.toFixed(2)})`).join(", ")}
        </p>
      )}
    </div>
  );
}

export function ExplanationPanel({ explanation, placeholder }: { explanation: ExplanationOut | null; placeholder: boolean }) {
  return (
    <Card className="p-4">
      <div className="mb-4 flex items-center gap-2">
        <Eyebrow>Why</Eyebrow>
        {explanation && placeholder && <PlaceholderTag />}
      </div>
      {!explanation ? (
        <p className="text-sm text-muted">The explanation appears after the verdict.</p>
      ) : (
        <div className="space-y-5">
          <Rationale text={explanation.rationale} citations={explanation.citations} />

          {explanation.differences && (explanation.differences.claim_only.length > 0 || explanation.differences.evidence_only.length > 0) && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-muted">Wording differs:</span>
              {explanation.differences.claim_only.map((w) => (
                <span key={`c-${w}`} className="rounded-full border border-refuted/40 bg-refuted/10 px-2 py-0.5 text-refuted">claim: {w}</span>
              ))}
              {explanation.differences.evidence_only.map((w) => (
                <span key={`e-${w}`} className="rounded-full border border-supported/40 bg-supported/10 px-2 py-0.5 text-supported">evidence: {w}</span>
              ))}
            </div>
          )}

          {explanation.attribution && (
            <div className="border-t border-line pt-4"><Why a={explanation.attribution} citations={explanation.citations} /></div>
          )}

          {explanation.summary && (
            <div className="border-t border-line pt-4">
              <div className="mb-1 flex items-center gap-2">
                <h4 className="text-sm font-semibold">What the evidence says</h4>
                <span className="rounded-full border border-line px-2 py-0.5 text-[10px] text-muted">{explanation.summary_method}</span>
              </div>
              <p className="text-sm leading-relaxed text-ink/90">{explanation.summary}</p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
