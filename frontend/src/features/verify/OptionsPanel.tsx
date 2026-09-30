import { ChevronDown, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchStages } from "@/api/client";
import { SLOTS, type Slot, type StageInfo } from "@/api/types";
import { SLOT_LABEL } from "./PipelineTimeline";

export type Options = Partial<Record<Slot, string>>;

/** Lets the user swap the implementation of each stage, e.g. TF-IDF vs a plain baseline, and compare results. */
export function OptionsPanel({ value, onChange }: { value: Options; onChange: (o: Options) => void }) {
  const [open, setOpen] = useState(false);
  const [stages, setStages] = useState<StageInfo[]>([]);

  useEffect(() => {
    const ctl = new AbortController();
    fetchStages(ctl.signal).then(setStages).catch(() => undefined);
    return () => ctl.abort();
  }, []);

  const changed = Object.keys(value).length;
  return (
    <div className="mx-auto max-w-3xl">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="mx-auto flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium text-muted transition hover:text-ink"
      >
        <SlidersHorizontal size={13} /> Pipeline options{changed > 0 && ` (${changed} changed)`}
        <ChevronDown size={13} className={`transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="mt-2 grid gap-3 rounded-2xl border border-line bg-surface p-4 shadow-card sm:grid-cols-2">
          {SLOTS.map((slot) => {
            const impls = stages.filter((s) => s.slot === slot);
            if (impls.length < 2) return null;
            const current = value[slot] ?? impls.find((s) => s.is_default)?.name;
            const info = impls.find((s) => s.name === current);
            return (
              <label key={slot} className="block text-sm">
                <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wider text-muted">{SLOT_LABEL[slot]}</span>
                <select
                  value={current}
                  onChange={(e) => {
                    const next = { ...value };
                    if (impls.find((s) => s.name === e.target.value)?.is_default) delete next[slot];
                    else next[slot] = e.target.value;
                    onChange(next);
                  }}
                  className="w-full rounded-lg border border-line bg-bg/60 px-2.5 py-1.5 outline-none focus:border-accent"
                >
                  {impls.map((s) => <option key={s.name} value={s.name}>{s.label}</option>)}
                </select>
                {info && <span className="mt-1 block text-xs leading-snug text-muted">{info.description}</span>}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
