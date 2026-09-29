import { motion } from "framer-motion";
import type { DataStats, SplitName } from "@/api/types";
import { Card, Eyebrow } from "@/components/Card";
import { LABELS } from "./labels";

const nf = new Intl.NumberFormat();
const BAR: Record<string, string> = { supported: "bg-supported", refuted: "bg-refuted", not_enough_info: "bg-neutral" };

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-serif text-3xl">{value}</p>
      <p className="text-xs text-muted">{label}</p>
    </div>
  );
}

export function StatsPanel({ stats }: { stats: DataStats }) {
  const c = stats.corpus;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
      <Card className="p-6">
        <Eyebrow>Evidence corpus</Eyebrow>
        <div className="mt-4 grid grid-cols-2 gap-5">
          <Tile label="pages" value={nf.format(c.pages)} />
          <Tile label="sentences (retrieval units)" value={nf.format(c.sentences)} />
          <Tile label="gold pages" value={nf.format(c.gold_pages)} />
          <Tile label="distractor pages" value={nf.format(c.distractor_pages)} />
        </div>
        <p className="mt-5 text-xs leading-relaxed text-muted">
          A bounded Wikipedia subset: every page cited as gold evidence plus a random sample of other pages, so retrieval
          is a real search problem. {c.mean_sentences_per_page} sentences per page on average.
        </p>
      </Card>

      <Card className="p-6">
        <Eyebrow>Claim splits</Eyebrow>
        <ul className="mt-4 space-y-4">
          {(Object.keys(stats.splits) as SplitName[]).map((name) => {
            const s = stats.splits[name];
            return (
              <li key={name}>
                <div className="mb-1.5 flex items-baseline justify-between text-sm">
                  <span className="font-medium capitalize">{name}</span>
                  <span className="font-mono text-xs text-muted">
                    {nf.format(s.claims)} claims · {s.mean_claim_words} words avg
                    {s.dropped_unanswerable > 0 && ` · ${nf.format(s.dropped_unanswerable)} dropped`}
                  </span>
                </div>
                <div className="flex h-2.5 overflow-hidden rounded-full bg-surface2">
                  {LABELS.map((l) => (
                    <motion.span
                      key={l}
                      className={BAR[l]}
                      initial={{ width: 0 }}
                      animate={{ width: `${((s.labels[l] ?? 0) / Math.max(s.claims, 1)) * 100}%` }}
                      transition={{ duration: 0.7 }}
                      title={`${l}: ${s.labels[l] ?? 0}`}
                    />
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
        <div className="mt-4 flex gap-4 text-xs text-muted">
          {LABELS.map((l) => (
            <span key={l} className="flex items-center gap-1.5">
              <i className={`size-2 rounded-full ${BAR[l]}`} />
              {l.replaceAll("_", " ")}
            </span>
          ))}
        </div>
      </Card>
    </div>
  );
}
