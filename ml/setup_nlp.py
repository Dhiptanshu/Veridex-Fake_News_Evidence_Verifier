"""Download the NLP resources the pipeline needs (idempotent).

    python ml/setup_nlp.py

NLTK data goes to data/nltk_data (gitignored); the spaCy model is installed into the active environment.
"""
import subprocess
import sys
from pathlib import Path

import nltk

ROOT = Path(__file__).resolve().parents[1]
NLTK_DIR = ROOT / "data" / "nltk_data"
NLTK_PACKAGES = ["punkt_tab", "stopwords", "wordnet", "omw-1.4", "averaged_perceptron_tagger_eng"]
SPACY_MODEL = "en_core_web_sm"


def main() -> None:
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


if __name__ == "__main__":
    main()
