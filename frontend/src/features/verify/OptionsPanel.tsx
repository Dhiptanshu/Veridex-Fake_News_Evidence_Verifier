import { useEffect, useState } from "react";
import { fetchStages } from "@/api/client";
import { SLOTS, type Slot, type StageInfo } from "@/api/types";
import { Badge, Select } from "@/components/ui";
import type { Options } from "@/state/AppState";
import { SLOT_LABEL } from "./PipelineTimeline";

/** Hook: the catalog of stage implementations, fetched once. */
export function useStageCatalog() {
  const [stages, setStages] = useState<StageInfo[]>([]);
  useEffect(() => {
    const ctl = new AbortController();
    fetchStages(ctl.signal).then(setStages).catch(() => undefined);
    return () => ctl.abort();
  }, []);
  return stages;
}

export function countChanged(o: Options) { return Object.keys(o).length; }

/** One select per pipeline slot; picking a slot's default removes it from the overrides. */
export function OptionsGrid({
  value, onChange, stages, slots = SLOTS,
}: { value: Options; onChange: (o: Options) => void; stages: StageInfo[]; slots?: readonly Slot[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {slots.map((slot) => {
        const impls = stages.filter((s) => s.slot === slot);
        if (impls.length < 2) return null;
        const def = impls.find((s) => s.is_default)?.name;
        const current = value[slot] ?? def;
        const info = impls.find((s) => s.name === current);
        return (
          <label key={slot} className="block">
            <span className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
              {SLOT_LABEL[slot]} {value[slot] && <Badge tone="accent">changed</Badge>}
            </span>
            <Select
              className="w-full"
              value={current ?? ""}
              onChange={(v) => {
                const next = { ...value };
                if (v === def) delete next[slot];
                else next[slot] = v;
                onChange(next);
              }}
            >
              {impls.map((s) => <option key={s.name} value={s.name}>{s.label}{s.is_default ? " (default)" : ""}</option>)}
            </Select>
            {info && <span className="mt-1 block text-xs leading-snug text-muted">{info.description}</span>}
          </label>
        );
      })}
    </div>
  );
}
