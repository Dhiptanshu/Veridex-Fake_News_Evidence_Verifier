import { useState } from "react";
import type { RunResult } from "@/api/run";
import { Badge, LABEL_TEXT, LABEL_TONE, Tabs } from "@/components/ui";
import { EvidenceList } from "./EvidenceList";
import { ExplanationPanel } from "./ExplanationPanel";

/** The full result of one finished run (explanation, notes and evidence), reused by Batch and Compare. */
export function ResultDetail({ run }: { run: RunResult }) {
  const [tab, setTab] = useState<"why" | "evidence">("why");
  const v = run.out.verification;
  const ret = run.out.retrieval;
  const ex = run.out.explanation;
  const notes = [...(ret?.notes ?? []), ...(v?.notes ?? [])];
  const count = ret ? ret.evidence.reduce((n, e) => n + e.sentences.length, 0) : 0;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {v && <Badge tone={LABEL_TONE[v.label]} className="px-2.5 py-1 text-[13px]">{LABEL_TEXT[v.label]}</Badge>}
        {v && <span className="font-mono text-sm text-muted">{Math.round(v.confidence * 100)}% confidence</span>}
        {v && <Badge>{v.engine === "llm" ? "LLM judge" : "BERT (offline)"}</Badge>}
        {run.totalMs != null && <span className="ml-auto font-mono text-[11px] text-muted">{(run.totalMs / 1000).toFixed(1)}s</span>}
      </div>
      {notes.length > 0 && (
        <ul className="space-y-1.5">
          {notes.map((n, i) => <li key={i} className="rounded-xl bg-warn/10 px-3 py-2 text-xs leading-snug text-warn">{n}</li>)}
        </ul>
      )}
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "why", label: "Explanation" }, { value: "evidence", label: "Evidence", count: count || undefined }]} />
      {tab === "why" && <ExplanationPanel explanation={ex ?? null} placeholder={false} />}
      {tab === "evidence" && <EvidenceList retrieval={ret ?? null} verification={v ?? null} placeholder={false} citations={ex?.citations} />}
    </div>
  );
}
