import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Label, Slot } from "@/api/types";
import type { RunResult } from "@/api/run";

export type Options = Partial<Record<Slot, string>>;

export interface HistoryEntry {
  id: string;
  ts: number;
  source: "verify" | "batch" | "compare";
  claim: string;
  label: Label | null;
  confidence: number | null;
  probabilities: Record<Label, number> | null;
  impl: Options;
  totalMs: number | null;
  rationale: string | null;
  topSource: { title: string; text: string; url: string | null } | null;
  goldLabel?: Label | null;
  error: string | null;
}

const HISTORY_KEY = "fnev-history";
const PREFS_KEY = "fnev-prefs";
const MAX_HISTORY = 200;

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function write(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage full or unavailable */ }
}

export function entryFromRun(r: RunResult, source: HistoryEntry["source"], goldLabel?: Label | null): HistoryEntry {
  const first = r.out.explanation?.citations?.[0] ?? null;
  return {
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    ts: Date.now(), source, claim: r.claim,
    label: r.out.verification?.label ?? null, confidence: r.out.verification?.confidence ?? null,
    probabilities: r.out.verification?.probabilities ?? null, impl: r.impl, totalMs: r.totalMs,
    rationale: r.out.explanation?.rationale ?? null,
    topSource: first ? { title: first.title, text: first.text, url: r.out.retrieval?.evidence.find((e) => e.id === first.evidence_id)?.url ?? null } : null,
    goldLabel: goldLabel ?? null, error: r.error,
  };
}

interface Ctx {
  history: HistoryEntry[];
  addEntry: (e: HistoryEntry) => void;
  removeEntry: (id: string) => void;
  clearHistory: () => void;
  defaults: Options;
  setDefaults: (o: Options) => void;
  /** A claim another tab wants the Verify tab to start with (History -> re-run). */
  draft: string | null;
  setDraft: (c: string | null) => void;
}

const AppCtx = createContext<Ctx | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<HistoryEntry[]>(() => read<HistoryEntry[]>(HISTORY_KEY, []));
  const [defaults, setDefaultsState] = useState<Options>(() => read<{ options?: Options }>(PREFS_KEY, {}).options ?? {});
  const [draft, setDraft] = useState<string | null>(null);

  useEffect(() => write(HISTORY_KEY, history), [history]);

  const addEntry = useCallback((e: HistoryEntry) => setHistory((h) => [e, ...h].slice(0, MAX_HISTORY)), []);
  const removeEntry = useCallback((id: string) => setHistory((h) => h.filter((x) => x.id !== id)), []);
  const clearHistory = useCallback(() => setHistory([]), []);
  const setDefaults = useCallback((o: Options) => { setDefaultsState(o); write(PREFS_KEY, { options: o }); }, []);

  const value = useMemo(
    () => ({ history, addEntry, removeEntry, clearHistory, defaults, setDefaults, draft, setDraft }),
    [history, addEntry, removeEntry, clearHistory, defaults, setDefaults, draft],
  );
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useAppState must be used inside AppStateProvider");
  return ctx;
}
