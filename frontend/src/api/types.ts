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

export interface TaggedToken { token: string; tag: string }
export interface Sentiment { polarity: number; subjectivity: number }
export interface PreprocessOut {
  original: string; sentences: string[]; tokens: string[]; pos: TaggedToken[]; lemmas: string[];
  normalized: string[]; sentiment: Sentiment | null;
}
export interface Entity { text: string; label: string; start: number; end: number }
export interface Triple { subject: string; predicate: string; object: string }
export interface NerOut { entities: Entity[]; noun_chunks: string[]; triples: Triple[] }
export interface KeywordsOut { keywords: { term: string; score: number; kind: string }[]; query: string }
export interface Topic { id: number; label: string; words: string[] }
export interface Evidence {
  id: string; title: string; source: string; url: string | null; score: number;
  sentences: { text: string; score: number }[]; topic: Topic | null;
}
export interface MapPoint { x: number; y: number; kind: "claim" | "evidence"; label: string; score: number | null }
export interface Projection { points: MapPoint[]; background: [number, number][]; explained_variance: number }
export interface RetrievalOut {
  evidence: Evidence[]; query: string | null; score_entropy: number | null; projection: Projection | null;
}
export interface VerificationOut {
  label: Label; confidence: number; probabilities: Record<Label, number>;
  per_evidence: { evidence_id: string; supported: number; refuted: number; neutral: number }[];
}
export interface Citation {
  n: number; evidence_id: string; title: string; text: string; role: "decisive" | "closest" | "context";
  supported: number | null; refuted: number | null; neutral: number | null;
}
export interface WordScore { word: string; score: number }
export interface Attribution { cite: number; target: Label; claim: WordScore[]; evidence: WordScore[] }
export interface Differences { cite: number; claim_only: string[]; evidence_only: string[] }
export interface ExplanationOut {
  summary: string; summary_method: string; rationale: string; cited_evidence_ids: string[];
  citations: Citation[]; differences: Differences | null; attribution: Attribution | null;
}

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

// --- data inspection (backend/app/api/data_routes.py) ---
export type SplitName = "train" | "val" | "test";

export interface DataStats {
  config: { n_train: number; n_val: number; n_distractors: number; seed: number };
  splits: Record<SplitName, {
    claims: number; labels: Partial<Record<Label, number>>; dropped_unanswerable: number; mean_claim_words: number;
  }>;
  corpus: { pages: number; gold_pages: number; distractor_pages: number; sentences: number; mean_sentences_per_page: number };
}

export interface EvidenceView { page: string; title: string; sent_id: number; text: string }
export interface ClaimView { id: number; claim: string; label: Label; evidence_sets: EvidenceView[][] }
export interface ClaimPage { total: number; items: ClaimView[] }

// --- follow-up questions (backend/app/qa) ---
export interface AskPassage { n: number; title: string; text: string; url: string | null }
export interface AskRequest {
  question: string; claim: string; label: Label; confidence: number; probabilities: Record<Label, number>;
  rationale: string; passages: AskPassage[]; mode: "auto" | "local" | "llm";
}
export interface AskResponse { answer: string; method: string; cited: number[]; note: string | null }
export interface AskStatus { llm_configured: boolean; llm_model: string; local_qa_ready: boolean }
