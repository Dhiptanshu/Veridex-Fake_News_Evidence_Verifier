import { Check, Loader2 } from "lucide-react";
import { SLOTS, type Slot } from "@/api/types";
import type { Stages } from "./useVerify";

export const SLOT_LABEL: Record<Slot, string> = {
  preprocess: "Preprocess",
  ner: "Entities",
  keywords: "Keywords",
  retrieval: "Retrieve",
  verification: "Verify",
  explanation: "Explain",
};

/** Compact stage tracker: one chip per pipeline stage with live status and timing. */
export function PipelineTimeline({ stages }: { stages: Stages }) {
  return (
    <ol className="flex flex-wrap items-center gap-1.5" aria-label="Pipeline progress">
      {SLOTS.map((slot, i) => {
        const st = stages[slot];
        const done = st.status === "done";
        const running = st.status === "running";
        return (
          <li key={slot} className="flex items-center gap-1.5">
            {i > 0 && <span className={`h-px w-4 ${done || running ? "bg-accent" : "bg-line"}`} />}
            <span
              className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-xs font-medium transition ${
                done ? "border-line bg-surface text-ink" : running ? "border-accent/50 bg-accent/10 text-accent" : "border-line bg-surface2 text-muted"}`}
            >
              {done ? <Check size={12} className="text-supported" /> : running ? <Loader2 size={12} className="animate-spin" /> : <i className="size-1.5 rounded-full bg-muted/50" />}
              {SLOT_LABEL[slot]}
              {done && st.elapsedMs != null && <span className="font-mono text-[11px] text-muted">{Math.round(st.elapsedMs)}ms</span>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
