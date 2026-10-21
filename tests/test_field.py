"""Field trial harness: selection filters, review inputs, report (evals/field.py)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evals"))

import field  # noqa: E402

from test_backtest import FIXTURE_CASE, analysis  # noqa: E402


def test_code_files_exclude_tests_docs_and_changelogs():
    code = lambda name, patch="@@ -1 +1 @@": field.is_code({"filename": name, "patch": patch})
    assert code("pandas/core/frame.py") and code("packages/vite/src/node/server.ts")
    assert not code("tests/test_frame.py") and not code("docs/whatsnew/v3.rst") and not code("CHANGES.md")
    assert not code("src/x.py", patch=None)  # binary or too large: no patch, no line ranges


def test_bot_and_short_reports_are_skipped():
    body = "x" * field.MIN_BODY
    assert field.human_with_body({"author": {"__typename": "User"}, "body": body})
    assert not field.human_with_body({"author": {"__typename": "Bot"}, "body": body})
    assert not field.human_with_body({"author": {"__typename": "User"}, "body": "too short"})
    assert not field.human_with_body({"author": None, "body": body})


def test_tool_trace_lists_calls_in_order_and_marks_refusals():
    transcript = [
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "looking"},
            {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "git grep -n to_cents"}},
            {"type": "tool_use", "id": "b", "name": "Read", "input": {"file_path": "/etc/passwd"}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "money.py:2"},
            {"type": "tool_result", "tool_use_id": "b", "is_error": True, "content": "denied"},
        ]}},
    ]
    trace = field.tool_trace(transcript)
    assert trace[0].startswith("1. Bash ") and "git grep" in trace[0] and "refused" not in trace[0]
    assert trace[1].startswith("2. Read ") and trace[1].endswith("[refused or failed]")
    assert field.tool_trace(None) == []


def test_review_prompt_fills_every_slot(tmp_path):
    from backtest import build_fixture
    from issuepilot.check import check_file

    repo = tmp_path / "repo"
    sha = build_fixture(FIXTURE_CASE, repo)
    case = {**FIXTURE_CASE, "source": {"repo": "owner/name", "sha": sha},
            "notes": json.dumps({"type": "open", "url": "https://example.com/1"})}
    folder = tmp_path / "result"
    folder.mkdir()
    (folder / "analysis.json").write_text(json.dumps(analysis()), encoding="utf-8")
    (folder / "checked.json").write_text(json.dumps(check_file(folder / "analysis.json", repo)), encoding="utf-8")
    (folder / "metrics.json").write_text(json.dumps({"num_turns": 7, "total_cost_usd": 0.1}), encoding="utf-8")
    prompt = field.review_prompt(case, folder, repo, repo / ".git")
    assert "{{" not in prompt and "}}" not in prompt
    assert "Totals off by a cent" in prompt and "round() on floats" in prompt
    assert "verified: money.py:2-2" in prompt and "turns: 7" in prompt
    assert "There is no reference answer" in prompt and "BEGIN FIX" not in prompt


def review(verdict="helpful", calibration=3, problems=()):
    return {"actual_cause": "c", "cause_matches": "yes", "verdict": verdict, "would_post": verdict == "helpful",
            "scores": {d: 3 for d in field.DIMENSIONS} | {"calibration": calibration},
            "claims": [], "problems": list(problems), "strengths": [], "summary": "s"}


def test_report_counts_verdicts_and_groups_problems(tmp_path):
    suite, results, reviews = tmp_path / "suite", tmp_path / "results", tmp_path / "reviews"
    for d in (suite, reviews):
        d.mkdir()
    for n, kind in [(1, "closed"), (2, "open")]:
        case = {**FIXTURE_CASE, "id": f"c{n}", "source": {"repo": "o/r", "sha": "a" * 40},
                "expected": {"kind": "bug_analysis" if kind == "closed" else "unknown"},
                "notes": json.dumps({"type": kind, "url": f"https://example.com/{n}"})}
        (suite / f"c{n}.json").write_text(json.dumps(case), encoding="utf-8")
    problem = {"category": "overconfident", "severity": "major", "component": "prompt",
               "what_happened": "said high", "change": "ask for a reproduction"}
    (reviews / "c1.json").write_text(json.dumps(review()), encoding="utf-8")
    (reviews / "c2.json").write_text(json.dumps(review("harmful", 0, [problem])), encoding="utf-8")
    out = tmp_path / "report.md"
    field.report(SimpleNamespace(suite=suite, results=results, reviews=reviews, out=out))
    text = out.read_text(encoding="utf-8")
    assert "| harmful | 1 | 0 | 1 |" in text and "| would post | 1/2 | 1/1 | 0/1 |" in text
    assert "| overconfident | 1 | 0 |" in text
    assert "### prompt (1)" in text and "**c2** (major, overconfident): said high → *ask for a reproduction*" in text
