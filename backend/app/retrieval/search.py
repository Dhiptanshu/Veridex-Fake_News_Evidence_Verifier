"""End-to-end TF-IDF search producing the pipeline's RetrievalOut."""
import math
from urllib.parse import quote

from app.data import wiki
from app.retrieval.tfidf import TfidfIndex
from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut

DEFAULT_BOOST = 0.2  # tuned on the val split (see docs/results/retrieval_tfidf.json)


def entropy_bits(scores: list[float]) -> float:
    """Shannon entropy of the normalised score distribution: low = one page clearly dominates, high = unsure."""
    total = sum(s for s in scores if s > 0)
    if total <= 0:
        return 0.0
    return -sum((s / total) * math.log2(s / total) for s in scores if s > 0)


def wikipedia_url(page_id: str) -> str:
    return "https://en.wikipedia.org/wiki/" + quote(wiki.display_title(page_id).replace(" ", "_"))


def search(
    index: TfidfIndex, claim: str, entity_texts: list[str], *, use_titles: bool = True,
    boost: float = DEFAULT_BOOST, k_pages: int = 10, k_sentences: int = 5,
) -> RetrievalOut:
    boosted = None
    if use_titles:
        boosted = [index.titles_in_text(claim) | index.titles_for_entities(entity_texts)]
    hits = index.rank_pages([claim], boosted, boost if use_titles else 0.0, k=k_pages)[0]
    page_score = {h.page_idx: h.score for h in hits}
    sent_hits = index.rank_sentences(claim, hits, k=k_sentences)

    by_page: dict[int, list] = {}
    for s in sent_hits:
        by_page.setdefault(s.page_idx, []).append(s)
    evidence = [
        Evidence(
            id=index.page_ids[pi], title=index.titles[pi], source="wikipedia", url=wikipedia_url(index.page_ids[pi]),
            score=round(page_score[pi], 4),
            sentences=[EvidenceSentence(text=index.page_sentences[pi][s.sent_id], score=round(max(0.0, min(1.0, s.score)), 4)) for s in ss],
        )
        for pi, ss in by_page.items()
    ]
    evidence.sort(key=lambda e: -e.sentences[0].score)
    return RetrievalOut(
        evidence=evidence, query=claim, score_entropy=round(entropy_bits([h.score for h in hits]), 3),
    )
