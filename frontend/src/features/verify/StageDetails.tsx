import { motion } from "framer-motion";
import type { ReactNode } from "react";
import type { KeywordsOut, NerOut, PreprocessOut } from "@/api/types";
import { Card, Eyebrow } from "@/components/Card";

/** Penn-tag family -> colour token, so the tag sequence is readable at a glance. */
function tagColor(tag: string): string {
  if (tag.startsWith("NNP")) return "var(--accent)";
  if (tag.startsWith("NN")) return "var(--supported)";
  if (tag.startsWith("VB")) return "var(--refuted)";
  if (tag.startsWith("JJ") || tag.startsWith("RB")) return "var(--neutral)";
  if (tag === "CD") return "var(--accent)";
  return "var(--muted)";
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline gap-2">
        <h4 className="text-sm font-semibold">{title}</h4>
        {hint && <span className="text-xs text-muted">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function Meter({ label, value, min, max }: { label: string; value: number; min: number; max: number }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-24 text-muted">{label}</span>
      <span className="relative h-1.5 w-28 rounded-full bg-surface2">
        <motion.span className="absolute top-1/2 size-2.5 -translate-y-1/2 rounded-full bg-accent" initial={false} animate={{ left: `calc(${pct}% - 5px)` }} />
      </span>
      <span className="font-mono">{value.toFixed(2)}</span>
    </div>
  );
}

export function StageDetails({
  pre, ner, kw,
}: { pre: PreprocessOut | null; ner: NerOut | null; kw: KeywordsOut | null }) {
  if (!pre && !ner && !kw) return null;
  return (
    <Card className="p-4">
      <Eyebrow>How it got here</Eyebrow>
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        {pre && (
          <Section title="Tokens and parts of speech" hint={pre.pos.length ? "NLTK, Penn tags" : "no tagger in this implementation"}>
            <div className="flex flex-wrap gap-1.5">
              {(pre.pos.length ? pre.pos : pre.tokens.map((t) => ({ token: t, tag: "" }))).map((p, i) => (
                <span key={i} className="rounded-md border border-line bg-bg/60 px-1.5 py-0.5 text-sm">
                  {p.token}
                  {p.tag && <sub className="ml-1 font-mono text-[10px]" style={{ color: tagColor(p.tag) }}>{p.tag}</sub>}
                </span>
              ))}
            </div>
            {pre.normalized.length > 0 && (
              <p className="mt-3 text-xs text-muted">
                Normalised (lemmas, no stop-words): <span className="font-mono text-ink/80">{pre.normalized.join(" ")}</span>
              </p>
            )}
            {pre.sentiment && (
              <div className="mt-3 space-y-1.5">
                <Meter label="Polarity" value={pre.sentiment.polarity} min={-1} max={1} />
                <Meter label="Subjectivity" value={pre.sentiment.subjectivity} min={0} max={1} />
              </div>
            )}
          </Section>
        )}

        {ner && (
          <Section title="Entities, chunks and triples" hint="spaCy">
            <div className="flex flex-wrap gap-1.5">
              {ner.entities.map((e, i) => (
                <span key={i} className="rounded-full border border-accent/40 bg-accent/10 px-2.5 py-0.5 text-xs">
                  {e.text} <span className="font-mono text-[10px] text-accent">{e.label}</span>
                </span>
              ))}
              {ner.entities.length === 0 && <span className="text-xs text-muted">No entities found.</span>}
            </div>
            {ner.noun_chunks.length > 0 && (
              <p className="mt-3 text-xs text-muted">Noun chunks: <span className="text-ink/80">{ner.noun_chunks.join(" · ")}</span></p>
            )}
            {ner.triples.map((t, i) => (
              <p key={i} className="mt-2 font-mono text-xs">
                <span className="text-accent">{t.subject}</span> —{t.predicate}→ <span className="text-supported">{t.object}</span>
              </p>
            ))}
          </Section>
        )}

        {kw && (
          <Section title="Keywords" hint="weight in the claim">
            <ul className="space-y-1.5">
              {kw.keywords.map((k) => {
                const top = Math.max(...kw.keywords.map((x) => x.score));
                return (
                  <li key={k.term} className="flex items-center gap-2 text-sm">
                    <span className="w-36 truncate">{k.term}{k.kind === "phrase" && <span className="ml-1 text-[10px] text-muted">phrase</span>}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2">
                      <motion.span className="block h-full rounded-full bg-accent" initial={{ width: 0 }} animate={{ width: `${(k.score / top) * 100}%` }} />
                    </span>
                    <span className="w-10 text-right font-mono text-[11px] text-muted">{k.score}</span>
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-xs text-muted">Query terms: <span className="font-mono text-ink/80">{kw.query}</span></p>
          </Section>
        )}
      </div>
    </Card>
  );
}
