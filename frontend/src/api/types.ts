// Mirrors backend/app/schemas. Keep in sync when a schema changes.

export type Slot = "preprocess" | "ner" | "keywords" | "retrieval" | "verification" | "explanation";
export const SLOTS: Slot[] = ["preprocess", "ner", "keywords", "retrieval", "verification", "explanation"];

export type Label = "supported" | "refuted" | "not_enough_info";

export interface StageInfo {
  slot: Slot;
  name: string;
  label: string;
  description: string;
  family: "classical" | "neural" | "hybrid" | "placeholder";
  is_default: boolean;
  placeholder: boolean;
}

export interface PreprocessOut { original: string; sentences: string[]; tokens: string[]; normalized: string[] }
export interface Entity { text: string; label: string; start: number; end: number }
export interface NerOut { entities: Entity[] }
export interface KeywordsOut { keywords: { term: string; score: number }[]; query: string }
export interface Evidence {
  id: string; title: string; source: string; url: string | null; score: number;
  sentences: { text: string; score: number }[];
}
export interface RetrievalOut { evidence: Evidence[]; score_entropy: number | null }
export interface VerificationOut {
  label: Label; confidence: number; probabilities: Record<Label, number>;
  per_evidence: { evidence_id: string; supported: number; refuted: number; neutral: number }[];
}
export interface ExplanationOut { summary: string; rationale: string; cited_evidence_ids: string[] }

export interface SlotOutputs {
  preprocess: PreprocessOut; ner: NerOut; keywords: KeywordsOut;
  retrieval: RetrievalOut; verification: VerificationOut; explanation: ExplanationOut;
}

export interface PipelineEvent {
  type: "pipeline_start" | "stage_start" | "stage_end" | "pipeline_end" | "error";
  slot: Slot | null;
  impl: string | null;
  placeholder: boolean;
  elapsed_ms: number | null;
  payload: Record<string, unknown> | null;
  message: string | null;
}
