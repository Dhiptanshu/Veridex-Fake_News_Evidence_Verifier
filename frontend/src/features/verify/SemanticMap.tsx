import { motion } from "framer-motion";
import { useState } from "react";
import type { Projection } from "@/api/types";
import { Card, Eyebrow } from "@/components/Card";

const W = 420;
const H = 260;
const PAD = 18;

/** 2-D PCA of the claim and evidence embeddings over a backdrop of corpus sentences. */
export function SemanticMap({ projection }: { projection: Projection }) {
  const [hover, setHover] = useState<number | null>(null);
  const all = [...projection.background, ...projection.points.map((p) => [p.x, p.y] as [number, number])];
  const xs = all.map((p) => p[0]);
  const ys = all.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const sx = (x: number) => PAD + ((x - x0) / (x1 - x0 || 1)) * (W - 2 * PAD);
  const sy = (y: number) => H - PAD - ((y - y0) / (y1 - y0 || 1)) * (H - 2 * PAD);
  let n = 0;

  return (
    <Card className="p-6">
      <Eyebrow>Semantic map</Eyebrow>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full rounded-xl bg-bg/60" role="img" aria-label="2-D map of the claim and its evidence">
        {projection.background.map(([x, y], i) => (
          <circle key={i} cx={sx(x)} cy={sy(y)} r={1.6} fill="var(--muted)" opacity={0.3} />
        ))}
        {projection.points.map((p, i) => {
          const isClaim = p.kind === "claim";
          const idx = isClaim ? 0 : ++n;
          return (
            <motion.g
              key={i}
              initial={{ opacity: 0, scale: 0.4 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * i }}
              style={{ transformOrigin: `${sx(p.x)}px ${sy(p.y)}px` }}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            >
              {isClaim ? (
                <rect x={sx(p.x) - 6} y={sy(p.y) - 6} width={12} height={12} rx={2} transform={`rotate(45 ${sx(p.x)} ${sy(p.y)})`} fill="var(--ink)" />
              ) : (
                <>
                  <circle cx={sx(p.x)} cy={sy(p.y)} r={8} fill="var(--accent)" opacity={0.9} />
                  <text x={sx(p.x)} y={sy(p.y) + 3.5} textAnchor="middle" fontSize="10" fontWeight="600" fill="var(--accent-ink)">{idx}</text>
                </>
              )}
              <title>{p.label}</title>
            </motion.g>
          );
        })}
      </svg>
      <div className="mt-2 flex items-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><i className="inline-block size-2.5 rotate-45 bg-ink" /> claim</span>
        <span className="flex items-center gap-1.5"><i className="inline-block size-2.5 rounded-full bg-accent" /> evidence (ranked)</span>
        <span className="flex items-center gap-1.5"><i className="inline-block size-1.5 rounded-full bg-muted/40" /> corpus sample</span>
      </div>
      {hover !== null && <p className="mt-2 truncate text-xs text-ink/80">{projection.points[hover].label}</p>}
      <p className="mt-2 text-[11px] leading-snug text-muted">
        PCA to 2 components keeps {(projection.explained_variance * 100).toFixed(1)}% of the variance, so distances are
        approximate. Closer means more similar in meaning.
      </p>
    </Card>
  );
}
