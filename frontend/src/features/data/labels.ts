import type { Label } from "@/api/types";

export const LABEL_META: Record<Label, { text: string; className: string }> = {
  supported: { text: "Supported", className: "border-supported/40 bg-supported/10 text-supported" },
  refuted: { text: "Refuted", className: "border-refuted/40 bg-refuted/10 text-refuted" },
  not_enough_info: { text: "Not enough info", className: "border-neutral/40 bg-neutral/10 text-neutral" },
};

export const LABELS = Object.keys(LABEL_META) as Label[];
