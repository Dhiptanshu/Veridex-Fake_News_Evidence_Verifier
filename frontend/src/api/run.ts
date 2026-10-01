import type { Label, PipelineEvent, Slot, SlotOutputs } from "./types";

/** One finished pipeline run, as used by Compare, Batch and History. */
export interface RunResult {
  claim: string;
  options: Partial<Record<Slot, string>>;
  impl: Partial<Record<Slot, string>>;
  out: Partial<SlotOutputs>;
  stageMs: Partial<Record<Slot, number>>;
  totalMs: number | null;
  error: string | null;
}

export function collect(claim: string, options: Partial<Record<Slot, string>>, events: PipelineEvent[]): RunResult {
  const r: RunResult = { claim, options, impl: {}, out: {}, stageMs: {}, totalMs: null, error: null };
  for (const e of events) {
    if (e.type === "stage_end" && e.slot) {
      (r.out as Record<string, unknown>)[e.slot] = e.payload;
      r.impl[e.slot] = e.impl ?? undefined;
      r.stageMs[e.slot] = e.elapsed_ms ?? undefined;
    } else if (e.type === "pipeline_end") r.totalMs = e.elapsed_ms;
    else if (e.type === "error") r.error = e.message ?? "Unknown pipeline error";
  }
  return r;
}

/** Runs a claim through the whole pipeline and returns the collected result (non-streaming). */
export async function runOnce(claim: string, options: Partial<Record<Slot, string>>, signal?: AbortSignal): Promise<RunResult> {
  const res = await fetch("/api/verify", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ claim, options }), signal,
  });
  if (!res.ok) {
    const detail = await res.json().then((j) => (typeof j.detail === "string" ? j.detail : "")).catch(() => "");
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return collect(claim, options, (await res.json()) as PipelineEvent[]);
}

export const verdictOf = (r: RunResult): { label: Label; confidence: number } | null => {
  const v = r.out.verification;
  return v ? { label: v.label, confidence: v.confidence } : null;
};
