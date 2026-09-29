import { motion } from "framer-motion";
import type { ExplanationOut, Label, VerificationOut } from "@/api/types";
import { Card, Eyebrow, PlaceholderTag } from "@/components/Card";

const META: Record<Label, { text: string; color: string }> = {
  supported: { text: "Supported", color: "var(--supported)" },
  refuted: { text: "Refuted", color: "var(--refuted)" },
  not_enough_info: { text: "Not enough info", color: "var(--neutral)" },
};

function Gauge({ value, color }: { value: number; color: string }) {
  const r = 52, c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 128 128" className="size-32 -rotate-90" role="img" aria-label={`Confidence ${Math.round(value * 100)}%`}>
      <circle cx="64" cy="64" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="10" />
      <motion.circle
        cx="64" cy="64" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
        strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - value) }}
        transition={{ duration: 0.9, ease: "easeOut" }}
      />
    </svg>
  );
}

export function VerdictPanel({
  verification, explanation, placeholder,
}: { verification: VerificationOut | null; explanation: ExplanationOut | null; placeholder: boolean }) {
  const meta = verification ? META[verification.label] : null;
  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center gap-2">
        <Eyebrow>Verdict</Eyebrow>
        {verification && placeholder && <PlaceholderTag />}
      </div>
      {!verification || !meta ? (
        <p className="text-sm text-muted">The verdict appears once evidence has been checked.</p>
      ) : (
        <div className="flex items-center gap-5">
          <div className="relative shrink-0">
            <Gauge value={verification.confidence} color={meta.color} />
            <span className="absolute inset-0 grid place-items-center font-mono text-lg font-medium">
              {Math.round(verification.confidence * 100)}%
            </span>
          </div>
          <div>
            <motion.p initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="font-serif text-3xl" style={{ color: meta.color }}>
              {meta.text}
            </motion.p>
            <dl className="mt-2 grid grid-cols-[auto_auto] gap-x-3 font-mono text-xs text-muted">
              {(Object.keys(META) as Label[]).map((l) => (
                <div key={l} className="contents">
                  <dt>{META[l].text}</dt>
                  <dd className="text-right text-ink">{(verification.probabilities[l] * 100).toFixed(1)}%</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
      {explanation && (
        <div className="mt-5 space-y-2 border-t border-line pt-4 text-sm leading-relaxed">
          <p className="text-ink/90">{explanation.rationale}</p>
          <p className="text-muted">{explanation.summary}</p>
        </div>
      )}
    </Card>
  );
}
