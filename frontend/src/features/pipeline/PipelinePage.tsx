import { CheckCircle2, CircleDashed, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { fetchSystemStatus } from "@/api/client";
import { SLOTS, type Check, type StageInfo, type SystemStatus } from "@/api/types";
import { Badge, Button, Panel } from "@/components/ui";
import { useStageCatalog } from "@/features/verify/OptionsPanel";
import { SLOT_LABEL } from "@/features/verify/PipelineTimeline";

function Row({ c }: { c: Check }) {
  return (
    <li className="flex items-start gap-3 px-4 py-2.5">
      {c.ready ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-supported" /> : <CircleDashed size={16} className="mt-0.5 shrink-0 text-muted" />}
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium">{c.label}</p>
        <p className="text-xs text-muted">{c.detail}</p>
        {c.fix && <p className="mt-1 break-words font-mono text-[11px] text-ink/80"><span className="text-muted">fix: </span>{c.fix}</p>}
      </div>
      <Badge tone={c.ready ? "supported" : "neutral"}>{c.ready ? "ready" : "not set up"}</Badge>
    </li>
  );
}

const FAMILY_TONE = { classical: "neutral", neural: "accent", hybrid: "accent", placeholder: "warn" } as const;

export function PipelinePage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const catalog = useStageCatalog();

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchSystemStatus().then(setStatus).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  useEffect(load, [load]);

  const bySlot = (slot: string): StageInfo[] => catalog.filter((s) => s.slot === slot);

  return (
    <div className="space-y-4">
      {error && <p role="alert" className="rounded-lg border border-refuted/30 bg-refuted/10 px-3 py-2.5 text-[13px] text-refuted">{error}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Services" flush actions={<Button size="sm" variant="ghost" icon={<RefreshCw size={13} />} loading={loading} onClick={load}>Refresh</Button>}>
          <ul className="divide-y divide-line">{status?.services.map((c) => <Row key={c.key} c={c} />)}</ul>
          <p className="border-t border-line px-4 py-2.5 text-xs text-muted">Keys live in <span className="font-mono">backend/.env</span>; only whether they are set is shown here, never the values. Restart the API after editing.</p>
        </Panel>
        <Panel title={`Resources${status ? ` (${status.resources.filter((c) => c.ready).length}/${status.resources.length} ready)` : ""}`} flush>
          <ul className="max-h-[28rem] divide-y divide-line overflow-y-auto">{status?.resources.map((c) => <Row key={c.key} c={c} />)}</ul>
        </Panel>
      </div>

      <Panel title="Stage implementations" flush>
        <p className="border-b border-line px-4 py-2.5 text-xs text-muted">
          Every stage has interchangeable implementations. Pick them per run in Verify, Compare and Batch, or set defaults in Settings.
        </p>
        <div className="divide-y divide-line">
          {SLOTS.map((slot) => (
            <div key={slot} className="grid gap-3 px-4 py-3 md:grid-cols-[9rem_1fr]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{SLOT_LABEL[slot]}</p>
              <ul className="space-y-2">
                {bySlot(slot).map((s) => (
                  <li key={s.name} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="text-[13px] font-medium">{s.label}</span>
                    <Badge tone={FAMILY_TONE[s.family]}>{s.family}</Badge>
                    {s.is_default && <Badge tone="supported">default</Badge>}
                    <span className="basis-full text-xs leading-snug text-muted">{s.description}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
