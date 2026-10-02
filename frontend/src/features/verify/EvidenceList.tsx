import { motion } from "framer-motion";
import { ExternalLink, FileSearch, Newspaper, ShieldCheck, BookOpen } from "lucide-react";
import type { Citation, Evidence, EvidenceKind, RetrievalOut, VerificationOut } from "@/api/types";
import { Badge, Empty, Panel, Skeleton, SourceMark } from "@/components/ui";
import { PlaceholderTag } from "@/components/Card";

const KIND: Record<EvidenceKind, { label: string; icon: typeof Newspaper; tone: "accent" | "supported" | "neutral" }> = {
  news: { label: "News", icon: Newspaper, tone: "accent" },
  "fact-check": { label: "Fact-check", icon: ShieldCheck, tone: "supported" },
  background: { label: "Wikipedia", icon: BookOpen, tone: "neutral" },
  wikipedia: { label: "Wikipedia", icon: BookOpen, tone: "neutral" },
};
const TIER_TONE: Record<string, "supported" | "accent" | "neutral"> = { "fact-checker": "supported", "wire / major": "accent", established: "accent", unrated: "neutral" };

function Stance({ ev, v }: { ev: Evidence; v: VerificationOut | null }) {
  const s = v?.per_evidence.find((p) => p.evidence_id === ev.id);
  if (!s) return null;
  const top = s.refuted > s.supported && s.refuted > s.neutral ? "refuted" : s.supported > s.neutral ? "supported" : "neutral";
  const color = top === "refuted" ? "var(--refuted)" : top === "supported" ? "var(--supported)" : "var(--neutral)";
  const label = top === "refuted" ? "Contradicts" : top === "supported" ? "Supports" : "Neutral";
  return <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold" style={{ color }}><i className="size-2 rounded-full" style={{ background: color }} />{label}</span>;
}

export function EvidenceList({
  retrieval, verification, placeholder, citations = [],
}: { retrieval: RetrievalOut | null; verification: VerificationOut | null; placeholder: boolean; citations?: Citation[] }) {
  if (!retrieval) {
    return <Panel title="Evidence"><div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-24 w-full" />)}</div></Panel>;
  }
  if (retrieval.evidence.length === 0) {
    return <Panel><Empty icon={<FileSearch size={20} />} title="No evidence found">Try rephrasing the claim.</Empty></Panel>;
  }
  const cmap = new Map(citations.map((c) => [`${c.evidence_id}|${c.text}`, c]));
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        {placeholder && <PlaceholderTag />}
        {retrieval.queries.length > 0 && <span>Searched for: {retrieval.queries.map((q) => <code key={q} className="mr-1 rounded-md bg-surface2 px-1.5 py-0.5 font-mono text-[11px]">{q}</code>)}</span>}
        {Object.keys(retrieval.timings_ms).length > 0 && (
          <span className="font-mono">{Object.entries(retrieval.timings_ms).map(([k, ms]) => `${k} ${(ms / 1000).toFixed(1)}s`).join(" . ")}</span>
        )}
      </div>
      <ul className="space-y-3">
        {retrieval.evidence.map((ev, i) => {
          const k = KIND[ev.kind] ?? KIND.wikipedia;
          const Icon = k.icon;
          return (
            <motion.li
              key={ev.id} id={`evidence-${ev.id}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 * i }}
              className="scroll-mt-24 rounded-2xl border border-line bg-surface p-4 shadow-card"
            >
              <div className="flex items-start gap-3">
                <SourceMark url={ev.url} name={ev.source} size={30} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <h4 className="text-[14px] font-semibold leading-snug">{ev.title}</h4>
                    {ev.url && (
                      <a href={ev.url} target="_blank" rel="noreferrer noopener" aria-label={`Open ${ev.title}`} className="text-muted hover:text-accent"><ExternalLink size={13} /></a>
                    )}
                  </div>
                  <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                    <Badge tone={k.tone} className="gap-1"><Icon size={10} />{k.label}</Badge>
                    {ev.tier && <Badge tone={TIER_TONE[ev.tier] ?? "neutral"}>{ev.tier}</Badge>}
                    <span>{ev.source}</span>
                    {ev.rating && <Badge tone="warn">Rated: {ev.rating}</Badge>}
                    <span className="ml-auto flex items-center gap-3"><Stance ev={ev} v={verification} /><span className="font-mono">rel {ev.score.toFixed(2)}</span></span>
                  </p>
                </div>
              </div>
              <div className="mt-3 space-y-1.5">
                {ev.sentences.map((s, j) => {
                  const cite = cmap.get(`${ev.id}|${s.text}`);
                  return (
                    <p key={j} className={`flex gap-2 rounded-lg px-2.5 py-1.5 text-[13px] leading-relaxed ${cite ? "bg-accent/10 text-ink" : "text-ink/80"}`}>
                      {cite && <span className="mt-0.5 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-brand px-1 text-[10px] font-bold text-accentink" title={`cited as [${cite.n}]`}>{cite.n}</span>}
                      <span>{s.text}</span>
                    </p>
                  );
                })}
              </div>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
