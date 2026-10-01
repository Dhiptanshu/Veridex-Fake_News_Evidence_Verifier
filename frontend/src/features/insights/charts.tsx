import { motion } from "framer-motion";

export interface Series { key: string; label: string; color: string }
export interface BarRow { label: string; values: Record<string, number | undefined>; highlight?: boolean }

export function Legend({ series }: { series: Series[] }) {
  return (
    <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      {series.map((s) => (
        <span key={s.key} className="flex items-center gap-1.5">
          <i className="inline-block size-2.5 rounded-sm" style={{ background: s.color }} />
          {s.label}
        </span>
      ))}
    </div>
  );
}

/** Horizontal grouped bars on a 0..max scale; one group per row, one bar per series. */
export function HBars({ rows, series, max = 1 }: { rows: BarRow[]; series: Series[]; max?: number }) {
  return (
    <div>
      <Legend series={series} />
      <ul className="space-y-3">
        {rows.map((r) => (
          <li key={r.label} className="grid grid-cols-[minmax(0,11rem)_1fr] items-center gap-3 sm:grid-cols-[14rem_1fr]">
            <span className={`truncate text-sm ${r.highlight ? "font-semibold text-ink" : "text-ink/80"}`} title={r.label}>{r.label}</span>
            <div className="space-y-1">
              {series.map((s) => {
                const v = r.values[s.key];
                if (v === undefined) return null;
                return (
                  <div key={s.key} className="flex items-center gap-2">
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-surface2">
                      <motion.span
                        className="block h-full rounded-full"
                        style={{ background: s.color, opacity: r.highlight ? 1 : 0.75 }}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${Math.max(0, Math.min(1, v / max)) * 100}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.7 }}
                      />
                    </span>
                    <span className="w-11 text-right font-mono text-[11px] text-muted">{v.toFixed(3)}</span>
                  </div>
                );
              })}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export interface LineSeries { key: string; label: string; color: string; points: { x: number; y: number }[]; dashed?: boolean }

/** Simple multi-series line chart with light gridlines and 4 y ticks. */
export function LineChart({
  series, xLabel, yLabel, height = 220, yMin, yMax,
}: { series: LineSeries[]; xLabel: string; yLabel: string; height?: number; yMin?: number; yMax?: number }) {
  const W = 480, H = height, L = 44, R = 12, T = 10, B = 34;
  const pts = series.flatMap((s) => s.points);
  if (!pts.length) return null;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const lo = yMin ?? Math.min(...ys), hi = yMax ?? Math.max(...ys);
  const pad = (hi - lo) * 0.08 || 0.1;
  const y0 = yMin ?? lo - pad, y1 = yMax ?? hi + pad;
  const sx = (x: number) => L + ((x - x0) / (x1 - x0 || 1)) * (W - L - R);
  const sy = (y: number) => H - B - ((y - y0) / (y1 - y0 || 1)) * (H - T - B);
  const ticks = [0, 1, 2, 3].map((i) => y0 + ((y1 - y0) * i) / 3);
  return (
    <div>
      <Legend series={series} />
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`${yLabel} by ${xLabel}`}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} stroke="var(--border)" strokeWidth={1} />
            <text x={L - 6} y={sy(t) + 3} textAnchor="end" fontSize="10" fill="var(--muted)">{t.toFixed(2)}</text>
          </g>
        ))}
        {[x0, (x0 + x1) / 2, x1].map((t, i) => (
          <text key={i} x={sx(t)} y={H - B + 14} textAnchor={i === 0 ? "start" : i === 2 ? "end" : "middle"} fontSize="10" fill="var(--muted)">{Math.round(t * 100) / 100}</text>
        ))}
        <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" fontSize="10" fill="var(--muted)">{xLabel}</text>
        <text x={10} y={(T + H - B) / 2} fontSize="10" fill="var(--muted)" transform={`rotate(-90 10 ${(T + H - B) / 2})`} textAnchor="middle">{yLabel}</text>
        {series.map((s) => (
          <g key={s.key}>
            <motion.path
              d={s.points.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ")}
              fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? "5 4" : undefined}
              initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 0.9 }}
            />
            {s.points.length <= 12 && s.points.map((p, i) => <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={2.6} fill={s.color} />)}
          </g>
        ))}
      </svg>
    </div>
  );
}

/** Confusion matrix; cell shade shows the share of the TRUE class (row) landing in each predicted class. */
export function ConfusionMatrix({ labels, matrix }: { labels: string[]; matrix: number[][] }) {
  return (
    <div className="inline-block">
      <div className="mb-1 pl-24 text-[11px] uppercase tracking-wider text-muted">predicted</div>
      <div className="grid gap-1" style={{ gridTemplateColumns: `6rem repeat(${labels.length}, minmax(4.5rem, 1fr))` }}>
        <span />
        {labels.map((l) => <span key={l} className="text-center text-[11px] text-muted">{l}</span>)}
        {matrix.map((row, i) => {
          const total = row.reduce((a, b) => a + b, 0) || 1;
          return (
            <div key={labels[i]} className="contents">
              <span className="self-center pr-2 text-right text-[11px] text-muted">{labels[i]}</span>
              {row.map((n, j) => (
                <div
                  key={j}
                  className="grid place-items-center rounded-lg border border-line py-3 text-center"
                  style={{ background: `color-mix(in srgb, ${i === j ? "var(--supported)" : "var(--refuted)"} ${Math.round((n / total) * 70)}%, transparent)` }}
                  title={`${n.toLocaleString()} claims (${((n / total) * 100).toFixed(1)}% of true ${labels[i]})`}
                >
                  <span className="font-mono text-sm">{n.toLocaleString()}</span>
                  <span className="font-mono text-[10px] text-muted">{((n / total) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <div className="mt-1 text-[11px] uppercase tracking-wider text-muted">true label (rows)</div>
    </div>
  );
}
