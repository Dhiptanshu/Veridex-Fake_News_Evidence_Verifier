import { CornerDownLeft, Dices, SlidersHorizontal } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { fetchClaims, fetchDataStats } from "@/api/client";
import type { ClaimView, Label } from "@/api/types";
import { Button, Kbd, LABEL_TEXT, LABEL_TONE, Badge } from "@/components/ui";

/** The input row of the Verify tab: claim text, a picker of real FEVER test claims, options and Run. */
export function ClaimBar({
  value, onChange, running, onRun, optionsOpen, onToggleOptions, changedOptions,
}: {
  value: string; onChange: (v: string) => void; running: boolean; onRun: (claim: string, gold: Label | null) => void;
  optionsOpen: boolean; onToggleOptions: () => void; changedOptions: number;
}) {
  const [gold, setGold] = useState<Label | null>(null);
  const [examples, setExamples] = useState<ClaimView[] | null>(null);
  const [menu, setMenu] = useState(false);
  const [loadingEx, setLoadingEx] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const valid = value.trim().length >= 3;

  useEffect(() => {
    if (!menu) return;
    const close = (e: MouseEvent) => { if (!boxRef.current?.contains(e.target as Node)) setMenu(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menu]);

  const loadExamples = async () => {
    setMenu((m) => !m);
    if (examples || loadingEx) return;
    setLoadingEx(true);
    try {
      const total = (await fetchDataStats()).splits.test.claims;
      const offset = Math.floor(Math.random() * Math.max(1, total - 8));
      setExamples((await fetchClaims({ split: "test", offset, limit: 8 })).items);
    } catch {
      setExamples([]);
    } finally {
      setLoadingEx(false);
    }
  };

  const shuffle = async () => {
    setLoadingEx(true);
    try {
      const total = (await fetchDataStats()).splits.test.claims;
      const offset = Math.floor(Math.random() * Math.max(1, total - 8));
      const items = (await fetchClaims({ split: "test", offset, limit: 8 })).items;
      setExamples(items);
    } catch { /* keep the old list */ } finally { setLoadingEx(false); }
  };

  const submit = () => { if (valid && !running) { setMenu(false); onRun(value.trim(), gold); } };

  return (
    <div className="rounded-lg border border-line bg-surface focus-within:border-accent">
      <label htmlFor="claim" className="sr-only">Claim to verify</label>
      <textarea
        id="claim"
        value={value}
        onChange={(e) => { onChange(e.target.value); setGold(null); }}
        onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey || !e.shiftKey)) { e.preventDefault(); submit(); } }}
        rows={2}
        maxLength={2000}
        placeholder="Enter a claim or headline to verify against evidence..."
        className="block w-full resize-none bg-transparent px-4 pb-1 pt-3 text-[15px] leading-snug outline-none placeholder:text-muted/70"
      />
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-3 py-2">
        <div ref={boxRef} className="relative">
          <Button size="sm" variant="ghost" icon={<Dices size={14} />} onClick={() => void loadExamples()} aria-expanded={menu}>Real FEVER claims</Button>
          {menu && (
            <div className="absolute left-0 top-9 z-30 w-[min(34rem,90vw)] rounded-lg border border-line bg-surface p-1 shadow-lg">
              <div className="flex items-center justify-between px-2 py-1.5">
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted">Random test claims, with FEVER's label</p>
                <Button size="sm" variant="ghost" onClick={() => void shuffle()} loading={loadingEx}>Shuffle</Button>
              </div>
              {examples && examples.length === 0 && <p className="px-3 py-3 text-xs text-muted">Data not built yet (see the Pipeline tab).</p>}
              <ul className="max-h-72 overflow-y-auto">
                {(examples ?? []).map((c) => (
                  <li key={c.id}>
                    <button
                      onClick={() => { onChange(c.claim); setGold(c.label); setMenu(false); }}
                      className="flex w-full items-start justify-between gap-3 rounded-md px-2 py-2 text-left text-[13px] hover:bg-surface2"
                    >
                      <span>{c.claim}</span>
                      <Badge tone={LABEL_TONE[c.label]} className="shrink-0">{LABEL_TEXT[c.label]}</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        {gold && <Badge tone="accent">FEVER label: {LABEL_TEXT[gold]}</Badge>}
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="ghost" icon={<SlidersHorizontal size={14} />} onClick={onToggleOptions} aria-expanded={optionsOpen}>
            Options{changedOptions > 0 ? ` (${changedOptions})` : ""}
          </Button>
          <span className="hidden items-center gap-1 text-[11px] text-muted sm:flex"><Kbd>Enter</Kbd> to run</span>
          <Button variant="primary" onClick={submit} disabled={!valid} loading={running} icon={<CornerDownLeft size={14} />}>
            {running ? "Running" : "Verify"}
          </Button>
        </div>
      </div>
    </div>
  );
}
