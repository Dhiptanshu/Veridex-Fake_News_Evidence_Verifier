import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.data_routes import router as data_router
from app.api.routes import router
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
log = logging.getLogger("fnev")


def _warm_up() -> None:
    """Load heavy resources once at startup. Failures are logged, not fatal: stages report a clear error per request."""
    from app.nlp import pmi, resources, text, topics, wordnet
    from app.retrieval import hybrid, projection
    from app.retrieval.tfidf import get_index

    def warm_tfidf() -> None:
        get_index().feature_names()

    def warm_dense() -> None:
        store = hybrid.get_store(hybrid.get_resources(), "bge_small")
        store.encode(["Warm up."])
        store.matrix32()  # float32 copy for global search, about 570 MB

    for name, load in [
        ("nltk + wordnet", lambda: (text.analyze("Warm up the tagger."), wordnet.synonyms("film", "NN"))),
        ("spacy", lambda: resources.spacy_nlp()("Warm up.")),
        ("tfidf index", warm_tfidf),
        ("pmi table", pmi.get_table),
        ("dense bge_small", warm_dense),
        ("lda topics", topics.get_topics),
        ("pca projection", lambda: projection.get_projector("bge_small")),
    ]:
        try:
            load()
            log.info("loaded %s", name)
        except Exception as exc:  # noqa: BLE001
            log.warning("could not load %s: %s", name, exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    import asyncio

    await asyncio.to_thread(_warm_up)
    yield


app = FastAPI(title="Fake News Evidence Verifier", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(router)
app.include_router(data_router)
