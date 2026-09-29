import { useCallback, useEffect, useRef, useState } from "react";
import { streamVerify } from "@/api/client";
import { SLOTS, type Slot, type SlotOutputs } from "@/api/types";

export type StageStatus = "idle" | "running" | "done";

export interface StageState<S extends Slot = Slot> {
  status: StageStatus;
  impl: string | null;
  placeholder: boolean;
  elapsedMs: number | null;
  output: SlotOutputs[S] | null;
}

export type RunStatus = "idle" | "running" | "done" | "error";
export type Stages = { [S in Slot]: StageState<S> };

const emptyStage = { status: "idle", impl: null, placeholder: false, elapsedMs: null, output: null } as const;
const emptyStages = (): Stages => Object.fromEntries(SLOTS.map((s) => [s, { ...emptyStage }])) as unknown as Stages;

export function useVerify() {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [claim, setClaim] = useState("");
  const [stages, setStages] = useState<Stages>(emptyStages);
  const [error, setError] = useState<string | null>(null);
  const [totalMs, setTotalMs] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback(async (text: string, options: Record<string, string> = {}) => {
    abortRef.current?.abort();
    const ctl = new AbortController();
    abortRef.current = ctl;
    setClaim(text);
    setStages(emptyStages());
    setError(null);
    setTotalMs(null);
    setStatus("running");
    try {
      for await (const ev of streamVerify(text, options, ctl.signal)) {
        if (ev.type === "stage_start" && ev.slot) {
          setStages((s) => ({ ...s, [ev.slot!]: { ...s[ev.slot!], status: "running", impl: ev.impl, placeholder: ev.placeholder } }));
        } else if (ev.type === "stage_end" && ev.slot) {
          setStages((s) => ({
            ...s,
            [ev.slot!]: { status: "done", impl: ev.impl, placeholder: ev.placeholder, elapsedMs: ev.elapsed_ms, output: ev.payload },
          }));
        } else if (ev.type === "pipeline_end") {
          setTotalMs(ev.elapsed_ms);
          setStatus("done");
        } else if (ev.type === "error") {
          setError(ev.message ?? "Unknown pipeline error");
          setStatus("error");
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setError((e as Error).message);
      setStatus("error");
    }
  }, []);

  return { status, claim, stages, error, totalMs, run };
}
