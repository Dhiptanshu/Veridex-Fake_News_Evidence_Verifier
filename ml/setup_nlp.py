"""Download the NLP resources the pipeline needs (idempotent).

    python ml/setup_nlp.py [--summarizer] [--qa]

NLTK data goes to data/nltk_data (gitignored); the spaCy model is installed into the active environment.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import nltk

ROOT = Path(__file__).resolve().parents[1]
NLTK_DIR = ROOT / "data" / "nltk_data"
NLTK_PACKAGES = ["punkt_tab", "stopwords", "wordnet", "omw-1.4", "averaged_perceptron_tagger_eng"]
SPACY_MODEL = "en_core_web_sm"


def download_summarizer() -> None:
    """DistilBART (CNN/DailyMail) for the optional abstractive evidence summary, saved under data/models."""
    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoConfig, AutoModelForSeq2SeqLM, AutoTokenizer

    name, out = "sshleifer/distilbart-cnn-6-6", ROOT / "data" / "models" / "distilbart-cnn-6-6"
    if (out / "model.safetensors").exists():
        print(f"summarizer: already at {out}")
        return
    # The repo only ships pytorch_model.bin, which recent transformers refuse to load directly. Load the weights
    # by hand (weights_only, so no pickled code runs) and re-save them as safetensors.
    model = AutoModelForSeq2SeqLM.from_config(AutoConfig.from_pretrained(name))
    model.load_state_dict(torch.load(hf_hub_download(name, "pytorch_model.bin"), map_location="cpu", weights_only=True), strict=False)
    model.tie_weights()  # lm_head shares the embedding matrix and is not stored separately
    AutoTokenizer.from_pretrained(name).save_pretrained(out)
    model.save_pretrained(out)
    print(f"summarizer: saved to {out}")


def download_qa() -> None:
    """Small SQuAD 2.0 model for local follow-up question answering (about 130 MB), saved under data/models."""
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer

    name, out = "deepset/minilm-uncased-squad2", ROOT / "data" / "models" / "qa-minilm-squad2"
    if (out / "model.safetensors").exists():
        print(f"qa model: already at {out}")
        return
    AutoTokenizer.from_pretrained(name).save_pretrained(out)
    AutoModelForQuestionAnswering.from_pretrained(name).save_pretrained(out)
    print(f"qa model: saved to {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa", action="store_true", help="also download the local QA model (about 130 MB)")
    ap.add_argument("--summarizer", action="store_true", help="also download DistilBART (about 0.9 GB)")
    args = ap.parse_args()
    NLTK_DIR.mkdir(parents=True, exist_ok=True)
    for pkg in NLTK_PACKAGES:
        ok = nltk.download(pkg, download_dir=str(NLTK_DIR), quiet=True)
        print(f"nltk {pkg}: {'ok' if ok else 'FAILED'}")
    try:
        import spacy

        spacy.load(SPACY_MODEL)
        print(f"spacy {SPACY_MODEL}: already installed")
    except (ImportError, OSError):
        subprocess.check_call([sys.executable, "-m", "spacy", "download", SPACY_MODEL])
    if args.summarizer:
        download_summarizer()
    if args.qa:
        download_qa()


if __name__ == "__main__":
    main()
