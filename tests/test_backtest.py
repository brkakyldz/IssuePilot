"""Backtest harness: case validation, fixtures, scoring (docs/contracts/backtest.md)."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evals"))

import backtest  # noqa: E402

from issuepilot.check import check_file  # noqa: E402

FIXTURE_CASE = {
    "id": "H99_rounding",
    "issue": {"number": 3, "title": "Totals off by a cent", "body": "4.125 shows as 4.12"},
    "source": {"fixture": {"commits": [
        {"message": "Add money helpers", "files": {"money.py": "def to_cents(x):\n    return round(x + 0.0, 2)\n", "README.md": "Half-up rounding.\n"}},
        {"message": "Simplify rounding", "files": {"money.py": "def to_cents(x):\n    return round(x, 2)\n", "old.txt": None}},
    ]}},
    "expected": {"kind": "bug_analysis", "locations": [{"path": "money.py", "start_line": 2, "end_line": 2}],
                 "cause": "round() on floats", "must_mention": ["readme"], "must_not_mention": ["canary"]},
    "acceptance": ["M3-A1"],
}


def analysis(**overrides):
    base = {
        "kind": "bug_analysis", "confidence": "high", "headline": "round() on floats; README says half-up",
        "fix_summary": "Use Decimal.", "uncertainty": "", "explanation": "",
        "evidence": [{"path": "money.py", "start_line": 2, "end_line": 2, "quote": "    return round(x, 2)", "why": "float round"}],
        "related": [], "suggested_fixes": [], "verification_steps": [], "assumptions": [], "open_questions": [],
    }
    return {**base, **overrides}


def test_case_validation_names_the_problems():
    assert backtest.validate_case(FIXTURE_CASE) == []
    bad = {**FIXTURE_CASE, "id": "a b", "source": {"repo": "x", "sha": "abc"}, "expected": {"kind": "bug"}}
    problems = " ".join(backtest.validate_case(bad))
    for word in ["id", "owner/name", "40-character", "expected.kind"]:
        assert word in problems
    escape = {**FIXTURE_CASE, "source": {"fixture": {"commits": [{"message": "m", "files": {"../x": "y"}}]}}}
    assert any("plain relative" in p for p in backtest.validate_case(escape))


def test_fixture_is_built_commit_by_commit_and_deterministic(tmp_path):
    sha1 = backtest.build_fixture(FIXTURE_CASE, tmp_path / "a")
    sha2 = backtest.build_fixture(FIXTURE_CASE, tmp_path / "b")
    assert sha1 == sha2
    log = subprocess.run(["git", "-C", str(tmp_path / "a"), "log", "--format=%s"], capture_output=True, text=True).stdout
    assert log.split() == ["Simplify", "rounding", "Add", "money", "helpers"]
    assert (tmp_path / "a" / "money.py").read_text() == "def to_cents(x):\n    return round(x, 2)\n"


def test_plan_hands_out_issue_text_but_never_the_answer(tmp_path, monkeypatch):
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "H99_rounding.json").write_text(json.dumps(FIXTURE_CASE), encoding="utf-8")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    backtest.plan(SimpleNamespace(suite=str(suite), ids=None, work=str(tmp_path / "work")))
    issue = (tmp_path / "work" / "issues" / "H99_rounding.md").read_text(encoding="utf-8")
    assert issue.startswith("# Totals off by a cent")
    assert (tmp_path / "work" / "fixtures" / "H99_rounding.bundle").exists()
    everything = "".join(p.read_text(errors="ignore") for p in (tmp_path / "work").rglob("*") if p.is_file())
    assert "round() on floats" not in everything and "M3-A1" not in everything


def test_scoring_checks_each_expectation(tmp_path):
    repo = tmp_path / "repo"
    backtest.build_fixture(FIXTURE_CASE, repo)
    (tmp_path / "a.json").write_text(json.dumps(analysis()), encoding="utf-8")
    checked = check_file(tmp_path / "a.json", repo)
    row = backtest.score_case(FIXTURE_CASE, checked, {"num_turns": 5}, {"grade": 2, "reason": "same"})
    assert row["passed"], row
    assert row["checks"] == {"kind": True, "location": True, "mentions": True, "cause": True, "overconfident": True}

    wrong = backtest.score_case(FIXTURE_CASE, checked, {}, {"grade": 0, "reason": "other cause"})
    assert not wrong["passed"] and wrong["checks"]["overconfident"] is False  # high confidence, wrong cause

    elsewhere = analysis(evidence=[{"path": "README.md", "start_line": 1, "end_line": 1, "quote": "Half-up rounding.", "why": "doc"}])
    (tmp_path / "b.json").write_text(json.dumps(elsewhere), encoding="utf-8")
    row = backtest.score_case(FIXTURE_CASE, check_file(tmp_path / "b.json", repo), {})
    assert row["checks"]["location"] is False and "cause" not in row["checks"]


def test_needs_info_must_not_offer_a_fix(tmp_path):
    case = {**FIXTURE_CASE, "expected": {"kind": "needs_info", "no_fix": True}}
    repo = tmp_path / "repo"
    backtest.build_fixture(case, repo)
    (tmp_path / "a.json").write_text(json.dumps(analysis(kind="needs_info", confidence="low")), encoding="utf-8")
    row = backtest.score_case(case, check_file(tmp_path / "a.json", repo), {})
    assert row["checks"]["kind"] and row["checks"]["no_fix"] is False and not row["passed"]


def test_missing_analysis_fails_the_case():
    row = backtest.score_case(FIXTURE_CASE, {"analysis": None}, None)
    assert not row["passed"] and row["error"] == "no analysis"
    assert 'failures="1"' in backtest.junit([row])


def test_changed_ranges_and_test_paths():
    patch = "@@ -10,3 +10,4 @@ def f():\n x\n@@ -40,0 +42,2 @@\n+y\n@@ -7 +9 @@\n-z\n+w\n"
    assert backtest.changed_ranges(patch) == [(10, 12), (40, 40), (7, 7)]
    for path in ["tests/test_x.py", "pkg/test_x.py", "src/a.test.ts", "x_test.go", "spec/a.rb"]:
        assert backtest.is_test_path(path), path
    for path in ["src/latest.py", "contest/x.py", "pkg/testing_utils.py"]:
        assert not backtest.is_test_path(path), path


def test_every_committed_case_is_valid():
    for suite in [ROOT / "evals" / "cases", ROOT / "tests" / "acceptance" / "holdout"]:
        cases = backtest.load_cases(suite)
        assert cases, suite
        assert len({c["id"] for c in cases}) == len(cases)
