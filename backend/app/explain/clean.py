"""Display-only text cleanup. FEVER's Wikipedia sentences carry pronunciation guides like
"Paris (French pronunciation: [pɑʁi], [paʁi]) is the capital ..."; they are noise in quotes, summaries and word
differences. The verifier itself always sees the raw text, so citations keep it unchanged for word attribution."""
import re

_PRONUNCIATION = re.compile(r"\s*\((?:[^()]*pronunciation[^()]*)\)")
_BRACKETS = re.compile(r"\s*\[[^\]]*\]")
_LEADING_PUNCT = re.compile(r"\(\s*[;,:]\s*(?:[;,:]\s*)*")
_EMPTY_PAREN = re.compile(r"\s*\(\s*[;,:]*\s*\)")
_SPACE = re.compile(r"\s+")


def tidy(text: str) -> str:
    t = _PRONUNCIATION.sub("", text)
    t = _BRACKETS.sub("", t)
    t = _LEADING_PUNCT.sub("(", t)
    t = _EMPTY_PAREN.sub("", t)
    return _SPACE.sub(" ", t).replace(" ,", ",").replace(" .", ".").strip()
