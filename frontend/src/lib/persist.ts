import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import type { RunResult } from "@/api/run";

/** Safe localStorage JSON access: storage can be missing, full or blocked, and the app must keep working. */
export function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJSON(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch { /* quota exceeded or blocked */ }
}

/**
 * useState that survives tab switches, reloads and browser restarts (stored in localStorage under `key`).
 * Writes are debounced so typing does not hammer storage. `reviver` can reshape or reject stale stored data.
 */
export function usePersistentState<T>(key: string, initial: T, reviver?: (stored: unknown) => T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    const stored = readJSON<unknown>(key, undefined);
    if (stored === undefined) return initial;
    try {
      return reviver ? reviver(stored) : (stored as T);
    } catch {
      return initial;
    }
  });
  const timer = useRef<number | undefined>(undefined);
  const latest = useRef(value);
  latest.current = value;

  useEffect(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => writeJSON(key, value), 250);
    return () => window.clearTimeout(timer.current);
  }, [key, value]);

  // flush immediately when the page is closed or reloaded, so the last keystrokes are not lost
  useEffect(() => {
    const flush = () => writeJSON(key, latest.current);
    window.addEventListener("pagehide", flush);
    return () => window.removeEventListener("pagehide", flush);
  }, [key]);

  return [value, useCallback((v: SetStateAction<T>) => setValue(v), [])];
}

/** A finished run without the PCA background cloud (large, and only the Semantic map tab uses it): keeps storage small. */
export function slimRun<R extends Pick<RunResult, "out">>(run: R): R {
  const ret = run.out.retrieval;
  if (!ret?.projection) return run;
  return { ...run, out: { ...run.out, retrieval: { ...ret, projection: { ...ret.projection, background: ret.projection.background.slice(0, 80) } } } };
}
