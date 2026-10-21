import json
from pathlib import Path

from issuepilot.verify import check_evidence, find_quote, lower_confidence, resolve_in_repo, verify

FIXTURES = Path(__file__).parent / "fixtures"
REPO = FIXTURES / "minibill_repo"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def evidence(path: str, start: int, end: int, quote: str) -> dict:
    return {"path": path, "start_line": start, "end_line": end, "quote": quote, "why": "x"}


def test_m1_issue2_wrong_lines_are_corrected():
    # Real M1 output: `cat -n money.py pricing.py` numbered pricing.py from line 12,
    # so the cited L24-27 point past the end of a 16-line file. The quote is right.
    item = load("m1_issue2_analysis.json")["evidence"][2]
    assert (item["path"], item["start_line"], item["end_line"]) == ("minibill/pricing.py", 24, 27)

    check = check_evidence(item, REPO)

    assert check.status == "corrected"
    assert check.original_lines == (24, 27)
    assert (check.item["start_line"], check.item["end_line"]) == (14, 16)


def test_m1_issue2_correct_citations_pass_unchanged():
    items = load("m1_issue2_analysis.json")["evidence"][:2]
    checks = [check_evidence(item, REPO) for item in items]
    assert [c.status for c in checks] == ["verified", "verified"]
    assert [c.item for c in checks] == items


def test_m1_issue3_citation_inside_a_wider_range_passes():
    # Cites L9-12 but quotes L9-11: the quote sits inside the range.
    item = load("m1_issue3_analysis.json")["evidence"][0]
    assert check_evidence(item, REPO).status == "verified"


def test_missing_file_is_unverified():
    check = check_evidence(evidence("minibill/tax.py", 1, 2, "def tax():"), REPO)
    assert (check.status, check.reason) == ("unverified", "file_not_found")


def test_invented_quote_is_unverified():
    check = check_evidence(evidence("minibill/money.py", 9, 11, "return math.floor(amount)"), REPO)
    assert (check.status, check.reason) == ("unverified", "quote_not_found")


def test_empty_quote_is_unverified():
    check = check_evidence(evidence("minibill/money.py", 9, 11, "  \n "), REPO)
    assert (check.status, check.reason) == ("unverified", "empty_quote")


def test_paths_outside_the_repository_are_rejected():
    for path in ["../secrets.txt", "/etc/passwd", "minibill/../../x.py", ""]:
        check = check_evidence(evidence(path, 1, 1, "x"), REPO)
        assert (check.status, check.reason) == ("unverified", "outside_repository"), path
    assert resolve_in_repo(REPO, "minibill/money.py") is not None


def test_quote_matching_ignores_indentation_and_blank_lines():
    text = "def f():\n    a = 1\n\n    return a\n"
    assert find_quote("a = 1\nreturn a", text) == [(2, 4)]
    assert find_quote("return b", text) == []


def test_quote_found_twice_is_reported_at_both_places():
    text = "x = 1\n" + "pass\n" * 20 + "x = 1\n"
    assert find_quote("x = 1", text) == [(1, 1), (22, 22)]


def test_far_off_citation_is_moved_to_where_the_quote_is():
    # "return float(value)" is line 6 of money.py.
    check = check_evidence(evidence("minibill/money.py", 40, 40, "return float(value)"), REPO)
    assert check.status == "corrected"
    assert (check.item["start_line"], check.item["end_line"]) == (6, 6)


def test_confidence_is_capped_by_unverified_evidence():
    ok = check_evidence(evidence("minibill/money.py", 11, 11, "return round(amount, 2)"), REPO)
    bad = check_evidence(evidence("minibill/money.py", 1, 1, "nope"), REPO)
    assert lower_confidence("high", [ok], "bug_analysis") == ("high", None)
    assert lower_confidence("high", [ok, bad], "bug_analysis") == ("medium", "some_evidence_unverified")
    assert lower_confidence("high", [bad], "bug_analysis") == ("low", "no_evidence_verified")
    assert lower_confidence("medium", [], "bug_analysis") == ("low", "no_evidence")
    assert lower_confidence("low", [bad], "bug_analysis") == ("low", None)
    assert lower_confidence("low", [], "needs_info") == ("low", None)


def test_verify_splits_evidence_and_drops_only_definitely_missing_refs():
    analysis = load("m1_issue2_analysis.json")
    analysis["evidence"].append(evidence("minibill/money.py", 1, 1, "import decimal"))
    analysis["related"].append({"kind": "issue", "ref": "#99", "why": "x"})
    known = {"#1": True, "#99": False}

    result = verify(analysis, REPO, lambda kind, ref: known.get(ref))

    assert [c.status for c in result.evidence] == ["verified", "verified", "corrected"]
    assert [c.reason for c in result.unverified] == ["quote_not_found"]
    assert [r["ref"] for r in result.dropped_related] == ["#99"]
    assert "#99" not in [r["ref"] for r in result.analysis["related"]]
    assert len(result.analysis["evidence"]) == 3
    assert result.analysis["confidence"] == "medium"
    assert result.confidence_note == "some_evidence_unverified"


def test_quote_that_cuts_a_long_line_short_still_matches():
    # ArchDrawer replays (M5): verbatim starts of long lines were set aside as not found.
    text = "a = 1\n    edges.push({ id: fresh(`${e.from}-${e.to}`), from: a, to: b, label: e.label });\nb = 2\n"
    assert find_quote("edges.push({ id: fresh(`${e.from}-${e.to}`), from: a, to: b,", text) == [(2, 2)]
    assert find_quote("from: a, to: b, label", text) == [(2, 2)]
    two = "const w = Math.max(maxX - minX, 1);\n        r = { x: minX, y: minY, w };\n"
    assert find_quote("const w = Math.max(maxX - minX, 1);\nr = { x: minX", two) == [(1, 2)]


def test_short_or_invented_fragments_do_not_match():
    text = "value = compute(x)\nreturn value\n"
    assert find_quote("e = c", text) == []  # too short to count as a partial quote
    assert find_quote("value = compute(y)", text) == []
    assert find_quote("compute(x)\nreturn val", text) == [(1, 2)]
    assert find_quote("compute(x)\nreturned", text) == []
