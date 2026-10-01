import { Check, X } from "lucide-react";
import { Fragment } from "react";
import type { Entity, Label, Slot, VerificationOut } from "@/api/types";
import { Badge, LABEL_COLOR, LABEL_TEXT, LABEL_TONE, Panel } from "@/components/ui";
import type { Stages } from "./useVerify";

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
    <p className="text-[17px] font-medium leading-snug">
      {parts.map((p, i) => (
        <Fragment key={i}>
          {p.entity ? <mark title={p.entity.label} className="rounded bg-accent/12 px-0.5 text-ink underline decoration-accent/50 decoration-2 underline-offset-4">{p.text}</mark> : p.text}
        </Fragment>
      ))}
    </p>
  );
}

const SLOT_SHORT: Record<Slot, string> = {
  preprocess: "preprocess", ner: "entities", keywords: "keywords", retrieval: "retrieve", verification: "verify", explanation: "explain",
};

function Probs({ v }: { v: VerificationOut }) {
  const labels: Label[] = ["supported", "refuted", "not_enough_info"];
  return (
    <ul className="space-y-1.5">
      {labels.map((l) => (
        <li key={l} className="grid grid-cols-[6.5rem_1fr_2.75rem] items-center gap-2 text-xs">
          <span className={v.label === l ? "font-semibold text-ink" : "text-muted"}>{LABEL_TEXT[l]}</span>
          <span className="h-1.5 overflow-hidden rounded-full bg-surface2">
            <span className="block h-full rounded-full transition-[width] duration-700" style={{ width: `${v.probabilities[l] * 100}%`, background: LABEL_COLOR[l] }} />
          </span>
          <span className="text-right font-mono tabular-nums text-muted">{(v.probabilities[l] * 100).toFixed(1)}%</span>
        </li>
      ))}
    </ul>
  );
}

export function ResultHeader({
  claim, stages, totalMs, gold,
}: { claim: string; stages: Stages; totalMs: number | null; gold: Label | null }) {
  const v = stages.verification.output;
  const entities = stages.ner.output?.entities ?? [];
  return (
    <Panel>
      <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {v ? (
              <>
                <Badge tone={LABEL_TONE[v.label]} className="px-2 py-1 text-[13px]">{LABEL_TEXT[v.label]}</Badge>
                <span className="font-mono text-sm tabular-nums text-muted">{(v.confidence * 100).toFixed(0)}% confidence</span>
                {gold && (
                  <Badge tone={gold === v.label ? "supported" : "refuted"} className="gap-1">
                    {gold === v.label ? <Check size={11} /> : <X size={11} />} FEVER label: {LABEL_TEXT[gold]}
                  </Badge>
                )}
              </>
            ) : (
              <Badge tone="neutral">Verifying...</Badge>
            )}
          </div>
          <ClaimText claim={claim} entities={entities} />
          <p className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[11px] text-muted">
            {(Object.keys(SLOT_SHORT) as Slot[]).filter((s) => stages[s].impl).map((s) => (
              <span key={s}>{SLOT_SHORT[s]}: <span className="text-ink/80">{stages[s].impl}</span>{stages[s].elapsedMs != null && ` ${Math.round(stages[s].elapsedMs!)}ms`}</span>
            ))}
            {totalMs != null && <span className="text-ink/80">total {(totalMs / 1000).toFixed(2)}s</span>}
          </p>
        </div>
        <div className="md:border-l md:border-line md:pl-5">{v ? <Probs v={v} /> : <p className="text-xs text-muted">Probabilities appear when verification finishes.</p>}</div>
      </div>
    </Panel>
  );
}
