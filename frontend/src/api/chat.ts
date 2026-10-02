import type { EvidenceKind, Label, RetrievalOut } from "./types";

export interface ChatSource {
  n: number; title: string; text: string; url: string | null; source: string; kind: string; date: string | null; tier: string | null;
  /** Evidence card id on the Verify page, when this source is one of the retrieved passages. */
  evidenceId?: string;
}
export interface ChatContext {
  claim: string; label: Label; confidence: number; probabilities: Record<Label, number>; reasoning: string; engine: string; notes: string[];
}
export interface Turn { role: "user" | "assistant"; content: string }

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "tool"; id: string; name: string; label: string }
  | { type: "tool_done"; id: string; name: string; count: number; error: string | null }
  | { type: "sources"; sources: ChatSource[] }
  | { type: "done"; cited: number[]; model: string }
  | { type: "error"; message: string };

const MAX_PASSAGES = 12; // must match backend/app/evidence/passages.py

/** The numbered passages the backend cites as [n]: evidence in rank order, sentences in order, capped. */
export function passagesOf(ret: RetrievalOut | null): ChatSource[] {
  if (!ret) return [];
  const out: ChatSource[] = [];
  for (const e of ret.evidence) {
    for (const s of e.sentences) {
      out.push({
        n: out.length + 1, title: e.title, text: s.text, url: e.url, source: e.source, kind: (e.kind satisfies EvidenceKind) as string,
        date: e.published, tier: e.tier, evidenceId: e.id,
      });
    }
  }
  return out.slice(0, MAX_PASSAGES);
}

export async function* streamChat(
  body: { messages: Turn[]; context: ChatContext | null; sources: ChatSource[]; model?: string }, signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const res = await fetch("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({
      ...body,
      sources: body.sources.map(({ n, title, text, url, source, kind, date, tier }) => ({ n, title, text: text.slice(0, 1500), url, source, kind, date, tier })),
    }),
  });
  if (!res.ok || !res.body) {
    const detail = await res.json().then((j) => (typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? ""))).catch(() => "");
    throw new Error(detail || `HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, i);
      buf = buf.slice(i + 2);
      if (frame.startsWith("data: ")) yield JSON.parse(frame.slice(6)) as ChatEvent;
    }
  }
}
