import { motion } from "framer-motion";
import { Fragment } from "react";
import type { Entity } from "@/api/types";
import { Card, Eyebrow, PlaceholderTag } from "@/components/Card";

/** Renders the claim with entity spans highlighted; before NER finishes it shows plain text. */
export function AnnotatedClaim({
  claim, entities, placeholder,
}: { claim: string; entities: Entity[] | null; placeholder: boolean }) {
  const spans = [...(entities ?? [])].sort((a, b) => a.start - b.start);
  const parts: { text: string; entity?: Entity }[] = [];
  let cursor = 0;
  for (const e of spans) {
    if (e.start < cursor) continue;
    if (e.start > cursor) parts.push({ text: claim.slice(cursor, e.start) });
    parts.push({ text: claim.slice(e.start, e.end), entity: e });
    cursor = e.end;
  }
  if (cursor < claim.length) parts.push({ text: claim.slice(cursor) });

  return (
    <Card className="p-6">
      <div className="mb-3 flex items-center gap-2">
        <Eyebrow>Claim</Eyebrow>
        {entities && placeholder && <PlaceholderTag />}
      </div>
      <p className="font-serif text-2xl leading-snug">
        {parts.map((p, i) => (
          <Fragment key={i}>
            {p.entity ? (
              <motion.mark
                initial={{ backgroundSize: "0% 100%" }}
                animate={{ backgroundSize: "100% 100%" }}
                transition={{ duration: 0.5, delay: i * 0.06 }}
                title={p.entity.label}
                className="rounded bg-transparent px-1 text-ink"
                style={{
                  backgroundImage: "linear-gradient(color-mix(in srgb, var(--accent) 28%, transparent), color-mix(in srgb, var(--accent) 28%, transparent))",
                  backgroundRepeat: "no-repeat",
                }}
              >
                {p.text}
              </motion.mark>
            ) : (
              p.text
            )}
          </Fragment>
        ))}
      </p>
    </Card>
  );
}
