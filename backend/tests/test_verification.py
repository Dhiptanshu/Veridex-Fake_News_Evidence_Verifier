import numpy as np
import pytest

from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut
from app.stages.verification import verify, verify_stacked
from app.verification import models, stack
from app.verification import text as vtext


def _retrieval() -> RetrievalOut:
    return RetrievalOut(evidence=[
        Evidence(id="Marie_Curie", title="Marie Curie", source="wikipedia", score=0.9,
                 sentences=[EvidenceSentence(text="She won the Nobel Prize in Chemistry.", score=0.9),
                            EvidenceSentence(text="She was a physicist.", score=0.4)]),
        Evidence(id="Paris", title="Paris", source="wikipedia", score=0.5,
                 sentences=[EvidenceSentence(text="Paris is the capital of France.", score=0.5)]),
    ])


def test_evidence_format_matches_the_training_format():
    assert vtext.fmt_evidence([{"title": "Marie Curie", "text": "She won."}, {"title": "Paris", "text": "A city."}]) == "Marie Curie: She won. Paris: A city."


@pytest.mark.parametrize("kind", ["bert", "bert_concat", "lstm", "gru"])
def test_neural_predictors_return_probability_rows(kind):
    probs = models.load(kind).predict([("marie curie won a prize", "Marie Curie: she won the nobel prize."), ("x", "y")])
    assert probs.shape == (2, 3)
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5) and (probs >= 0).all()


def test_claim_only_ignores_the_evidence():
    p = models.load("claim_only")
    a = p.predict([("marie curie won a prize", "one evidence")])
    b = p.predict([("marie curie won a prize", "completely different evidence")])
    assert np.allclose(a, b)
    assert a.shape == (1, 3)


@pytest.mark.parametrize("kind", ["bert_concat", "lstm", "gru", "claim_only"])
def test_verify_builds_a_verdict_with_per_evidence_stances(kind):
    out = verify(kind, "Marie Curie won a Nobel Prize.", _retrieval())
    assert out.label in vtext.LABELS
    assert abs(sum(out.probabilities.values()) - 1) < 1e-3
    assert out.confidence == max(out.probabilities.values())
    assert [v.evidence_id for v in out.per_evidence] == ["Marie_Curie", "Paris"]
    assert all(abs(v.supported + v.refuted + v.neutral - 1) < 1e-3 for v in out.per_evidence)


def test_missing_model_raises_a_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Kaggle"):
        models.load("bert", tmp_path)


def test_temperature_is_read_from_the_calibration_file(tmp_path):
    assert models.temperature("bert", tmp_path) == 1.0  # no file: unchanged probabilities
    (tmp_path / "calibration.json").write_text('{"bert": 1.6, "lstm": 1.25}')
    assert models.temperature("bert", tmp_path) == 1.6 and models.temperature("gru", tmp_path) == 1.0


def test_higher_temperature_softens_bert_probabilities():
    pairs = [("marie curie won a prize", "Marie Curie: she won the nobel prize.")]
    sharp = models.BertPredictor(vtext.MODEL_DIR / "bert_fever", T=1.0).predict(pairs)
    soft = models.BertPredictor(vtext.MODEL_DIR / "bert_fever", T=5.0).predict(pairs)
    assert soft.max() < sharp.max() and np.allclose(soft.sum(), 1.0, atol=1e-5)
    assert soft.argmax() == sharp.argmax()  # calibration never changes the predicted label


def test_stacked_verifier_returns_a_calibrated_verdict_and_page_stances():
    out = verify_stacked("Marie Curie won a Nobel Prize.", _retrieval())
    assert out.label in vtext.LABELS and abs(sum(out.probabilities.values()) - 1) < 1e-3
    assert out.confidence == max(out.probabilities.values())
    assert [v.evidence_id for v in out.per_evidence] == ["Marie_Curie", "Paris"]
    assert all(abs(v.supported + v.refuted + v.neutral - 1) < 1e-3 for v in out.per_evidence)


def test_serving_and_training_features_agree():
    rng = np.random.default_rng(1)
    sent = rng.dirichlet(np.ones(3), size=(4, 5))
    concat = rng.dirichlet(np.ones(3), size=4)
    top = rng.random(4)
    batch = stack.batch_features(sent, concat, top)
    assert batch.shape == (4, stack.N_FEATURES)
    for i in range(4):
        assert np.allclose(stack.features(sent[i], concat[i], float(top[i])), batch[i], atol=1e-6)
