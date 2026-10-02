import { AlertTriangle, Brain, Check, Cpu, Info, X } from "lucide-react";
import { Fragment } from "react";
import type { Entity, Label, Slot } from "@/api/types";
import { Badge, LABEL_COLOR, LABEL_TEXT, LABEL_TONE, Ring, Skeleton } from "@/components/ui";
import type { Stages } from "./useVerify";

const NUANCE: Record<string, string> = {
  partly_true: "Partly true", misleading: "Misleading", outdated: "Outdated", satire: "Satire", opinion: "Opinion",
  unverifiable_future: "About the future", needs_context: "Needs context",
};
const HEADLINE: Record<Label, string> = {
  supported: "The evidence supports this claim", refuted: "The evidence contradicts this claim", not_enough_info: "Not enough evidence to decide",
};

/** The claim with its named entities underlined; plain text until NER has run. */
function ClaimText({ claim, entities }: { claim: string; entities: Entity[] }) {
  const spans = [...entities].sort((a, b) => a.start - b.start);
  const parts: { text: string; entity?: Entity }[] = [];
  let cur = 0;
  for (const e of spans) {
    if (e.start < cur) continue;
    if (e.start > cur) parts.push({ text: claim.slice(cur, e.start) });
    parts.push({ text: claim.slice(e.start, e.end), entity: e });
    cur = e.end;
  }
  if (cur < claim.length) parts.push({ text: claim.slice(cur) });
  return (
    <p className="text-lg font-medium leading-snug sm:text-xl">
      <span className="mr-1 select-none text-accent/60">“</span>
      {parts.map((p, i) => (
        <Fragment key={i}>
          {p.entity ? <mark title={p.entity.label} className="rounded-md bg-accent/12 px-0.5 text-ink">{p.text}</mark> : p.text}
        </Fragment>
      ))}
      <span className="ml-0.5 select-none text-accent/60">”</span>
    </p>
  );
}

const SLOT_SHORT: Record<Slot, string> = {
  preprocess: "preprocess", ner: "entities", keywords: "keywords", retrieval: "retrieve", verification: "judge", explanation: "explain",
};

export function ResultHeader({
  claim, stages, totalMs, gold,
}: { claim: string; stages: Stages; totalMs: number | null; gold: Label | null }) {
  const v = stages.verification.output;
  const ret = stages.retrieval.output;
  const entities = stages.ner.output?.entities ?? [];
  const color = v ? LABEL_COLOR[v.label] : "var(--muted)";
  const notes = [...(ret?.notes ?? []), ...(v?.notes ?? [])];
  const fastCount = ret ? ret.evidence.filter((e) => e.kind === "news" || e.kind === "fact-check").length : 0;

  return (
    <section className="card relative overflow-hidden rounded-[28px]" style={{ ["--tint" as string]: color }}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1.5" style={{ background: v ? `linear-gradient(90deg, ${color}, transparent)` : "var(--surface-2)" }} />
      <div className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full opacity-[0.13] blur-3xl" style={{ background: color }} />
      <div className="relative grid gap-6 p-6 md:grid-cols-[auto_minmax(0,1fr)] md:gap-8">
        <div className="flex items-center gap-5 md:flex-col md:items-center md:gap-3">
          {v ? (
            <Ring value={v.confidence} color={color} size={112} stroke={10}>
              <div className="text-center">
                <p className="font-mono text-2xl font-semibold tabular-nums">{Math.round(v.confidence * 100)}<span className="text-sm text-muted">%</span></p>
                <p className="-mt-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted">confidence</p>
              </div>
            </Ring>
          ) : (
            <Skeleton className="size-28 rounded-full" />
          )}
        </div>

        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {v ? (
              <>
                <Badge tone={LABEL_TONE[v.label]} className="px-3 py-1 text-sm font-semibold">{LABEL_TEXT[v.label]}</Badge>
                {v.nuance && <Badge tone="warn">{NUANCE[v.nuance] ?? v.nuance}</Badge>}
                <Badge tone="neutral" className="gap-1">
                  {v.engine === "llm" ? <Brain size={11} /> : <Cpu size={11} />}
                  {v.engine === "llm" ? "LLM judge" : "BERT (offline)"}
                </Badge>
                {gold && (
                  <Badge tone={gold === v.label ? "supported" : "refuted"} className="gap-1">
                    {gold === v.label ? <Check size={11} /> : <X size={11} />} FEVER label: {LABEL_TEXT[gold]}
                  </Badge>
                )}
              </>
            ) : (
              <>
                <Skeleton className="h-7 w-28 rounded-full" />
                <span className="text-xs text-muted">Gathering evidence and judging...</span>
              </>
            )}
          </div>

          <ClaimText claim={claim} entities={entities} />
          {v && <p className="text-[14px] text-muted">{HEADLINE[v.label]}{fastCount > 0 ? `, based on ${fastCount} live source${fastCount === 1 ? "" : "s"}` : ""}.</p>}

          {notes.length > 0 && (
            <ul className="space-y-1.5">
              {notes.map((n, i) => (
                <li key={i} className="flex items-start gap-2 rounded-xl bg-warn/10 px-3 py-2 text-xs leading-snug text-warn">
                  {/ BERT |Wikipedia-trained/.test(n) ? <Info size={13} className="mt-0.5 shrink-0" /> : <AlertTriangle size={13} className="mt-0.5 shrink-0" />}
                  <span>{n}</span>
                </li>
              ))}
            </ul>
          )}

          <p className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[12px] text-muted">
            {(Object.keys(SLOT_SHORT) as Slot[]).filter((s) => stages[s].impl).map((s) => (
              <span key={s}>{SLOT_SHORT[s]}: <span className="text-ink/80">{stages[s].impl}</span>{stages[s].elapsedMs != null && ` ${(stages[s].elapsedMs! / 1000).toFixed(1)}s`}</span>
            ))}
            {totalMs != null && <span className="font-semibold text-ink/80">total {(totalMs / 1000).toFixed(1)}s</span>}
          </p>
        </div>
      </div>
    </section>
  );
}
