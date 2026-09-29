import { motion } from "framer-motion";
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

export function PipelineTimeline({ stages }: { stages: Stages }) {
  return (
    <ol className="grid grid-cols-3 gap-3 sm:grid-cols-6" aria-label="Pipeline progress">
      {SLOTS.map((slot, i) => {
        const st = stages[slot];
        const done = st.status === "done";
        const running = st.status === "running";
        return (
          <li key={slot} className="relative flex flex-col items-center gap-2 text-center">
            {i > 0 && (
              <span className="absolute right-1/2 top-4 -z-0 hidden h-px w-full bg-line sm:block">
                <motion.span
                  className="absolute inset-y-0 left-0 bg-accent"
                  initial={false}
                  animate={{ width: stages[SLOTS[i - 1]].status === "done" ? "100%" : "0%" }}
                  transition={{ duration: 0.4 }}
                />
              </span>
            )}
            <motion.span
              initial={false}
              animate={{ scale: running ? 1.08 : 1 }}
              className={`relative z-10 grid size-8 place-items-center rounded-full border text-xs font-semibold transition-colors ${
                done
                  ? "border-accent bg-accent text-accentink"
                  : running
                    ? "border-accent bg-surface text-accent"
                    : "border-line bg-surface text-muted"
              }`}
            >
              {done ? <Check size={15} /> : running ? <Loader2 size={15} className="animate-spin" /> : i + 1}
            </motion.span>
            <span className={`text-xs font-medium ${done || running ? "text-ink" : "text-muted"}`}>{SLOT_LABEL[slot]}</span>
            <span className="h-3 font-mono text-[10px] text-muted">
              {done && st.elapsedMs != null ? `${Math.round(st.elapsedMs)} ms` : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
