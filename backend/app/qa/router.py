"""Answering a follow-up question: a small intent router for questions the system can answer from its own results
(why / sources / confidence), local extractive QA for factual questions about the evidence, or an LLM (AICredits) when configured."""
import re

from app.core.config import settings
from app.qa import llm, local
from app.qa.schemas import AskRequest, AskResponse, AskStatus

WHY = re.compile(r"\b(why|how come|reason|explain|justif)", re.I)
SOURCES = re.compile(r"\b(source|sources|cite|cited|citation|where (?:does|did|is|are) (?:this|that|it)|which (?:sentence|page|article))", re.I)
CONFIDENCE = re.compile(r"\b(confiden|how (?:sure|certain)|certain|uncertain|probab|reliable|trust)", re.I)


def intent(question: str) -> str:
    if WHY.search(question):
        return "rationale"
    if CONFIDENCE.search(question):
        return "confidence"
    if SOURCES.search(question):
        return "sources"
    return "factual"


def _confidence_text(req: AskRequest) -> str:
    probs = ", ".join(f"{k.replace('_', ' ')} {v:.0%}" for k, v in sorted(req.probabilities.items(), key=lambda kv: -kv[1]))
    level = "fairly confident" if req.confidence >= 0.8 else "moderately confident" if req.confidence >= 0.6 else "uncertain"
    return (
        f"The model is {level} ({req.confidence:.0%} for '{req.label.replace('_', ' ')}'). Full distribution: {probs}. "
        "These probabilities are calibrated on FEVER's validation data, but the model can still be confidently wrong, "
        "especially on dates, numbers and claims outside its Wikipedia training domain."
    )


def _sources_text(req: AskRequest) -> str:
    if not req.passages:
        return "No evidence passages were retrieved."
    return "The evidence behind this verdict:\n" + "\n".join(f"[{p.n}] {p.title}: {p.text}" for p in req.passages[:5])


def status() -> AskStatus:
    return AskStatus(
        llm_configured=bool(settings.aicredits_api_key.strip()), llm_model=settings.aicredits_model,
        local_qa_ready=local.ready(),
    )


def answer(req: AskRequest) -> AskResponse:
    use_llm = req.mode == "llm" or (req.mode == "auto" and bool(settings.aicredits_api_key.strip()))
    if use_llm:
        text, cited = llm.ask(req)
        return AskResponse(
            answer=text, method="llm", cited=cited,
            note=f"Written by {settings.aicredits_model} via AICredits from the evidence shown; the question, claim and evidence were sent to that service.",
        )

    kind = intent(req.question)
    if kind == "rationale":
        return AskResponse(answer=req.rationale, method="rationale", cited=[], note="The explanation shown above, in the same words.")
    if kind == "confidence":
        return AskResponse(answer=_confidence_text(req), method="confidence")
    if kind == "sources":
        return AskResponse(answer=_sources_text(req), method="sources", cited=[p.n for p in req.passages[:5]])

    span = local.get_qa().answer(req.question, req.passages)
    if span is None:
        return AskResponse(answer="The retrieved evidence does not answer that question.", method="extractive QA",
                           note="Local model: it can only quote a span from the evidence, and found none.")
    return AskResponse(
        answer=span.text, method="extractive QA", cited=[span.passage_n],
        note=f"Quoted from evidence [{span.passage_n}] by a local SQuAD 2.0 model; it extracts text rather than reasoning.",
    )
