"""What is built and what is configured, for the Pipeline tab. Reports booleans and model names only, never key values."""
import importlib.util
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.nlp import resources
from app.verification import text as vtext

router = APIRouter(prefix="/api/system", tags=["system"])


class Check(BaseModel):
    key: str
    label: str
    ready: bool
    detail: str
    fix: str | None = None


class SystemStatus(BaseModel):
    resources: list[Check]
    services: list[Check]


def _file(label: str, key: str, path: Path, fix: str, what: str) -> Check:
    ok = path.exists()
    return Check(key=key, label=label, ready=ok, detail=what if ok else "missing", fix=None if ok else fix)


def build_status() -> SystemStatus:
    idx, models, proc = resources.INDEX_DIR, vtext.MODEL_DIR, resources.ROOT / "data" / "processed"
    spacy_ok = importlib.util.find_spec(resources.SPACY_MODEL) is not None
    res = [
        Check(key="spacy", label="spaCy model", ready=spacy_ok, detail=resources.SPACY_MODEL if spacy_ok else "missing",
              fix=None if spacy_ok else "python ml/setup_nlp.py"),
        _file("NLTK data", "nltk", resources.NLTK_DIR / "tokenizers", "python ml/setup_nlp.py", "tokenizers, tagger, WordNet"),
        _file("Evidence corpus", "corpus", proc / "corpus.jsonl", "python ml/build_subset.py", "69k Wikipedia pages (FEVER subset)"),
        _file("TF-IDF index", "tfidf", idx / "tfidf.joblib", "python ml/build_indexes.py", "page + sentence TF-IDF"),
        _file("PMI table", "pmi", idx / "pmi.joblib", "python ml/build_indexes.py", "collocation statistics"),
        _file("BGE-small embeddings", "bge", idx / "emb_bge_small.npy", "Kaggle GPU kernel, see README (Phase 4)", "dense retrieval (default)"),
        _file("MiniLM embeddings", "minilm", idx / "emb_minilm.npy", "Kaggle GPU kernel, see README (Phase 4)", "alternative dense retriever"),
        _file("Word2Vec / GloVe vectors", "wordvec", idx / "sent_w2v.npy", "python ml/build_wordvecs.py", "word-vector retrievers"),
        _file("LDA topics", "topics", idx / "topics.joblib", "python ml/build_topics.py", "20 topics"),
        _file("PCA projection", "projection", idx / "projection_bge_small.joblib", "python ml/build_projection.py", "semantic map"),
        _file("BERT verifier", "bert", models / "bert_fever" / "model.safetensors", "Kaggle GPU kernel, see README (Phase 5)", "fine-tuned bert-base"),
        _file("Stacker", "stacker", models / "stacker.joblib", "python ml/train_stacker.py", "verdict combiner"),
        _file("BiLSTM / BiGRU", "rnn", models / "lstm.pt", "Kaggle GPU kernel, see README (Phase 5)", "recurrent baselines"),
        _file("Claim-only baseline", "claim_only", models / "claim_only.joblib", "python ml/train_claim_baseline.py", "TF-IDF + logistic regression"),
        _file("Local QA model", "qa", models / "qa-minilm-squad2" / "model.safetensors", "python ml/setup_nlp.py --qa", "follow-up answers (local)"),
        _file("DistilBART summarizer", "summarizer", models / "distilbart-cnn-6-6" / "model.safetensors", "python ml/setup_nlp.py --summarizer", "abstractive summaries (optional)"),
    ]
    services = [
        Check(key="wikipedia", label="Live Wikipedia search", ready=bool(settings.wikipedia_contact.strip()),
              detail="contact set" if settings.wikipedia_contact.strip() else "not configured",
              fix=None if settings.wikipedia_contact.strip() else "Set FNEV_WIKIPEDIA_CONTACT in backend/.env"),
        Check(key="gnews", label="GNews", ready=bool(settings.gnews_api_key.strip()),
              detail="key set" if settings.gnews_api_key.strip() else "not configured",
              fix=None if settings.gnews_api_key.strip() else "Set FNEV_GNEWS_API_KEY in backend/.env"),
        Check(key="newsapi", label="NewsAPI", ready=bool(settings.newsapi_key.strip()),
              detail="key set" if settings.newsapi_key.strip() else "not configured (optional)",
              fix=None if settings.newsapi_key.strip() else "Set FNEV_NEWSAPI_KEY in backend/.env"),
        Check(key="aicredits", label="AICredits LLM", ready=bool(settings.aicredits_api_key.strip()),
              detail=f"model {settings.aicredits_model}" if settings.aicredits_api_key.strip() else "not configured",
              fix=None if settings.aicredits_api_key.strip() else "Set FNEV_AICREDITS_API_KEY in backend/.env"),
    ]
    return SystemStatus(resources=res, services=services)


@router.get("/status", response_model=SystemStatus)
def status() -> SystemStatus:
    return build_status()
