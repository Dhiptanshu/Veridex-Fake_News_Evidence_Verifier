import { Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchChatStatus } from "@/api/client";
import { passagesOf, type ChatContext, type ChatSource } from "@/api/chat";
import type { ExplanationOut, RetrievalOut, VerificationOut } from "@/api/types";
import { Panel } from "@/components/ui";
import { AskPanel } from "@/features/verify/AskPanel";
import { ChatThread } from "./ChatThread";

export interface ChatStatus { configured: boolean; model: string; tools: string[] }

export function useChatStatus() {
  const [status, setStatus] = useState<ChatStatus | null>(null);
  useEffect(() => {
    const ctl = new AbortController();
    fetchChatStatus(ctl.signal).then(setStatus).catch(() => setStatus({ configured: false, model: "", tools: [] }));
    return () => ctl.abort();
  }, []);
  return status;
}

/** Chat about the current result. Without an LLM key it falls back to the small local question-answering box. */
export function AssistantPanel({
  claim, verification, explanation, retrieval, onJump,
}: {
  claim: string; verification: VerificationOut; explanation: ExplanationOut; retrieval: RetrievalOut; onJump: (s: ChatSource) => void;
}) {
  const status = useChatStatus();
  const sources = useMemo(() => passagesOf(retrieval), [retrieval]);
  const context: ChatContext = useMemo(() => ({
    claim, label: verification.label, confidence: verification.confidence, probabilities: verification.probabilities,
    reasoning: verification.reasoning ?? explanation.rationale, engine: verification.engine, notes: [...retrieval.notes, ...verification.notes],
  }), [claim, verification, explanation, retrieval]);

  if (status && !status.configured) return <AskPanel claim={claim} verification={verification} explanation={explanation} retrieval={retrieval} />;

  return (
    <Panel
      title={<span className="flex items-center gap-2"><Sparkles size={14} className="text-accent" />Assistant</span>}
      subtitle="Follow-up questions. It searches the web when the evidence here is not enough."
    >
      <ChatThread
        context={context} initialSources={sources} resetKey={`${claim}|${verification.label}|${verification.confidence}`} persistKey={`claim:${claim.toLowerCase().slice(0, 120)}`} onJump={onJump}
        suggestions={["Why this verdict?", "How reliable are the sources?", "What would change the verdict?", "Is there anything newer on this?"]}
        placeholder="Ask a follow-up..." modelHint={status?.model ? `Model: ${status.model}` : undefined}
      />
    </Panel>
  );
}
