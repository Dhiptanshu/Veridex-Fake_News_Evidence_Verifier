import { useEffect, useState } from "react";
import { fetchDataStats } from "@/api/client";
import type { DataStats } from "@/api/types";
import { ClaimBrowser } from "./ClaimBrowser";
import { StatsPanel } from "./StatsPanel";

export function DataPage() {
  const [stats, setStats] = useState<DataStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    fetchDataStats(ctl.signal).then(setStats).catch((e: Error) => e.name !== "AbortError" && setError(e.message));
    return () => ctl.abort();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-3xl">Data</h1>
        <p className="mt-1 text-sm text-muted">FEVER claims with gold evidence sentences from Wikipedia. Everything here is real data.</p>
      </div>
      {error ? (
        <p role="alert" className="rounded-xl border border-refuted/40 bg-refuted/10 px-4 py-3 text-sm text-refuted">{error}</p>
      ) : (
        <>
          {stats && <StatsPanel stats={stats} />}
          <ClaimBrowser />
        </>
      )}
    </div>
  );
}
