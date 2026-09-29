"""Reading the FEVER Wikipedia dump (wiki-pages.zip: 109 jsonl files, ~5.4M pages) and cleaning its text."""
import json
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

_PTB = {"-LRB-": "(", "-RRB-": ")", "-LSB-": "[", "-RSB-": "]", "-LCB-": "{", "-RCB-": "}", "-COLON-": ":"}
_PTB_RE = re.compile("|".join(map(re.escape, _PTB)))
_ID_RE = re.compile(r'^\{"id":\s*("(?:[^"\\]|\\.)*")')


def _unescape_ptb(text: str) -> str:
    return _PTB_RE.sub(lambda m: _PTB[m.group()], text)


def display_title(page_id: str) -> str:
    return _unescape_ptb(page_id).replace("_", " ")


def clean_sentence(text: str) -> str:
    """FEVER sentences are PTB-tokenised ('-LRB- born 1970 -RRB- is , '); undo that for readability."""
    t = _unescape_ptb(text).replace("``", '"').replace("''", '"')
    t = re.sub(r"\s+([,.;:!?%)\]}])", r"\1", t)
    t = re.sub(r"([(\[{])\s+", r"\1", t)
    t = re.sub(r"\s+('s|n't|'re|'ve|'ll|'d|'m)\b", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_lines(lines: str) -> list[str]:
    """Turn a page's `lines` field ('0\\tText\\tlink...\\n1\\t...') into a list indexed by sentence id."""
    by_id: dict[int, str] = {}
    for row in lines.split("\n"):
        parts = row.split("\t")
        if len(parts) >= 2 and parts[0].isdigit():
            by_id[int(parts[0])] = clean_sentence(parts[1])
    if not by_id:
        return []
    return [by_id.get(i, "") for i in range(max(by_id) + 1)]


def page_id_of(raw_line: str) -> str | None:
    """Cheaply read a page's id without parsing the whole JSON line (most pages are discarded)."""
    m = _ID_RE.match(raw_line)
    return json.loads(m.group(1)) if m else None


def iter_raw_pages(zip_path: Path) -> Iterator[str]:
    """Yield raw jsonl lines from every shard in the dump without extracting it to disk."""
    with zipfile.ZipFile(zip_path) as zf:
        # The official zip also holds macOS resource forks (__MACOSX/wiki-pages/._wiki-001.jsonl): binary, not shards.
        shards = [n for n in zf.namelist() if n.endswith(".jsonl") and not n.startswith("__MACOSX") and "/._" not in n]
        for name in sorted(shards):
            with zf.open(name) as fh:
                for raw in fh:
                    yield raw.decode("utf-8")
