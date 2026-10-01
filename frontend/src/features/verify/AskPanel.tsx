import { motion } from "framer-motion";
import { ArrowUp, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { askQuestion, fetchAskStatus } from "@/api/client";
import type { AskPassage, AskResponse, AskStatus, ExplanationOut, RetrievalOut, VerificationOut } from "@/api/types";
import { Card, Eyebrow } from "@/components/Card";

type Mode = "auto" | "local" | "llm";
interface Turn { question: string; answer?: AskResponse; error?: string }

const STARTERS = ["Why is this the verdict?", "How confident is the model?", "What are the sources?"];

function jumpTo(id: string) {
  document.getElementById(`evidence-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
}

/** Follow-up questions about the current result. Everything it sends is what the page already shows. */
export function AskPanel({
  claim, verification, explanation, retrieval,
}: { claim: string; verification: VerificationOut; explanation: ExplanationOut; retrieval: RetrievalOut }) {
  const [status, setStatus] = useState<AskStatus | null>(null);
  const [mode, setMode] = useState<Mode>("auto");
  const [text, setText] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ctl = new AbortController();
    fetchAskStatus(ctl.signal).then(setStatus).catch(() => undefined);
    return () => ctl.abort();
  }, []);

  // A new verification result starts a new conversation.
  useEffect(() => { setTurns([]); }, [claim, verification.label, verification.confidence]);

  const passages: (AskPassage & { evidenceId: string })[] = useMemo(() => {
    let n = 0;
    return retrieval.evidence.flatMap((e) =>
      e.sentences.map((s) => ({ n: ++n, title: e.title, text: s.text, url: e.url, evidenceId: e.id })),
    ).slice(0, 12);
  }, [retrieval]);

  const ask = async (question: string) => {
    const q = question.trim();
    if (q.length < 3 || busy) return;
    setBusy(true);
    setText("");
    const idx = turns.length;
    setTurns((t) => [...t, { question: q }]);
    try {
      const answer = await askQuestion({
        question: q, claim, label: verification.label, confidence: verification.confidence,
        probabilities: verification.probabilities, rationale: explanation.rationale,
        passages: passages.map(({ n, title, text: tx, url }) => ({ n, title, text: tx, url })), mode,
      });
      setTurns((t) => t.map((x, i) => (i === idx ? { ...x, answer } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === idx ? { ...x, error: (e as Error).message } : x)));
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: FormEvent) => { e.preventDefault(); void ask(text); };
  const llmOn = status?.llm_configured;

  return (
    <Card className="p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Eyebrow>Ask about this result</Eyebrow>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as Mode)}
          aria-label="Answering mode"
          className="ml-auto rounded-lg border border-line bg-bg/60 px-2 py-1 text-xs outline-none focus:border-accent"
        >
          <option value="auto">{llmOn ? "Auto (LLM)" : "Auto (local)"}</option>
          <option value="local">Local model (private)</option>
          {llmOn && <option value="llm">LLM ({status?.llm_model})</option>}
        </select>
      </div>

      <div className="flex flex-wrap gap-2">
        {STARTERS.map((s) => (
          <button key={s} onClick={() => void ask(s)} disabled={busy} className="rounded-full border border-line bg-surface px-3 py-1 text-xs text-muted transition hover:text-ink disabled:opacity-50">{s}</button>
        ))}
      </div>

      <ul className="mt-4 space-y-4">
        {turns.map((t, i) => (
          <motion.li key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
            <p className="ml-auto w-fit max-w-[90%] rounded-lg rounded-br-sm bg-accent px-3.5 py-2 text-sm text-accentink">{t.question}</p>
            {t.answer && (
              <div className="max-w-[95%] rounded-lg rounded-bl-sm border border-line bg-bg/60 px-3.5 py-2.5">
                <p className="whitespace-pre-line text-sm leading-relaxed">{t.answer.answer}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                  <span className="rounded-full border border-line px-2 py-0.5">{t.answer.method}</span>
                  {t.answer.cited.map((n) => {
                    const p = passages.find((x) => x.n === n);
                    return p ? (
                      <button key={n} onClick={() => jumpTo(p.evidenceId)} title={`${p.title}: ${p.text}`} className="grid size-5 place-items-center rounded-full bg-accent font-semibold text-accentink">{n}</button>
                    ) : null;
                  })}
                  {t.answer.note && <span className="basis-full leading-snug">{t.answer.note}</span>}
                </div>
              </div>
            )}
            {t.error && <p role="alert" className="max-w-[95%] rounded-md border border-refuted/40 bg-refuted/10 px-3 py-2 text-sm text-refuted">{t.error}</p>}
            {!t.answer && !t.error && <p className="flex items-center gap-2 text-xs text-muted"><Loader2 size={13} className="animate-spin" /> thinking...</p>}
          </motion.li>
        ))}
      </ul>

      <form onSubmit={submit} className="mt-4 flex items-center gap-2 rounded-full border border-line bg-bg/60 py-1.5 pl-4 pr-1.5 focus-within:border-accent">
        <label htmlFor="ask" className="sr-only">Your question</label>
        <input
          id="ask" value={text} onChange={(e) => setText(e.target.value)} maxLength={300}
          placeholder={llmOn && mode !== "local" ? "Ask anything about the evidence..." : "Ask a factual question, e.g. Where was he born?"}
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted/70"
        />
        <button type="submit" disabled={busy || text.trim().length < 3} aria-label="Ask" className="grid size-8 place-items-center rounded-full bg-accent text-accentink disabled:opacity-40">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <ArrowUp size={15} />}
        </button>
      </form>
      {mode !== "local" && llmOn && (
        <p className="mt-2 text-[11px] text-muted">LLM mode sends your question, the claim and the evidence shown here to AICredits.</p>
      )}
    </Card>
  );
}
