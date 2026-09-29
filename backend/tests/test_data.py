import json
import zipfile

from app.data import fever, wiki
from app.data.corpus import iter_sentences, load_claims
from app.data.subset import SubsetConfig, build


def test_display_title_and_sentence_cleaning():
    assert wiki.display_title("Homeland_-LRB-TV_series-RRB-") == "Homeland (TV series)"
    raw = "Homeland -LRB- TV series -RRB- is a show , made by Fox ."
    assert wiki.clean_sentence(raw) == "Homeland (TV series) is a show, made by Fox."


def test_parse_lines_keeps_sentence_ids_aligned():
    lines = "0\tFirst .\tlink\n2\tThird sentence .\n1\t"
    assert wiki.parse_lines(lines) == ["First.", "", "Third sentence."]


def test_page_id_extraction_handles_escapes():
    assert wiki.page_id_of('{"id": "AC\\/DC", "text": "x", "lines": ""}') == "AC/DC"


def test_parse_claim_supports_multiple_evidence_sets_and_nei():
    sup = fever.parse_claim({
        "id": 1, "label": "SUPPORTS", "claim": "c",
        "evidence": [[[1, 2, "A", 0], [1, 2, "B", 3]], [[1, 3, "A", 1]]],
    })
    assert sup.label == "supported" and len(sup.evidence_sets) == 2 and sup.evidence_sets[0][1].page == "B"
    dup = fever.parse_claim({
        "id": 3, "label": "SUPPORTS", "claim": "c",
        "evidence": [[[1, 2, "A", 0]], [[5, 6, "A", 0]], [[1, 3, "B", 1]]],
    })
    assert [[(r.page, r.sent_id) for r in s] for s in dup.evidence_sets] == [[("A", 0)], [("B", 1)]]
    nei = fever.parse_claim({"id": 2, "label": "NOT ENOUGH INFO", "claim": "c", "evidence": [[[9, None, None, None]]]})
    assert nei.label == "not_enough_info" and nei.evidence_sets == []


def test_build_subset_end_to_end(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()

    def claim(i, label, ev):
        return json.dumps({"id": i, "label": label, "claim": f"claim number {i}", "evidence": ev, "verifiable": "x"})

    (raw / "train.jsonl").write_text("\n".join([
        claim(1, "SUPPORTS", [[[1, 1, "Alpha", 0]]]),
        claim(2, "REFUTES", [[[2, 2, "Beta", 1]]]),
        claim(3, "SUPPORTS", [[[3, 3, "Missing_page", 0]]]),  # gold page absent from dump -> dropped
        claim(4, "NOT ENOUGH INFO", [[[4, None, None, None]]]),
    ]), encoding="utf-8")
    (raw / "shared_task_dev.jsonl").write_text(claim(10, "SUPPORTS", [[[5, 5, "Alpha", 0]]]), encoding="utf-8")

    def page(pid, lines):
        return json.dumps({"id": pid, "text": "", "lines": lines})

    with zipfile.ZipFile(raw / "wiki-pages.zip", "w") as zf:
        zf.writestr("wiki-pages/wiki-001.jsonl", "\n".join([
            page("Alpha", "0\tAlpha is first .\n1\tIt has two sentences ."),
            page("Beta", "0\tBeta intro .\n1\tBeta fact ."),
            page("Gamma", "0\tGamma is a distractor ."),
            page("Empty", ""),
        ]))
        zf.writestr("__MACOSX/wiki-pages/._wiki-001.jsonl", b"\x00\x05\x16\x07\xb0binary resource fork")

    stats = build(SubsetConfig(raw, out, n_train=10, n_val=0, n_distractors=5, seed=1, total_pages=4))

    assert stats["splits"]["train"]["claims"] == 3 and stats["splits"]["train"]["dropped_unanswerable"] == 1
    assert stats["splits"]["test"]["claims"] == 1
    assert stats["corpus"]["gold_pages"] == 2 and stats["corpus"]["distractor_pages"] == 1  # Empty is skipped
    assert {c.id for c in load_claims("train", out)} == {1, 2, 4}
    assert ("Alpha", 1, "It has two sentences.") in set(iter_sentences(out / "corpus.jsonl"))
