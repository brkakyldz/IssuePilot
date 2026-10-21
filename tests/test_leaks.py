import json
from pathlib import Path

import issuepilot.__main__ as publish
from issuepilot.github import GitHub
from issuepilot.leaks import canary_for, find_leaks
from test_publish import FakeGh

FIXTURES = Path(__file__).parent / "fixtures"


def test_credential_shapes_are_found():
    assert find_leaks("token sk-ant-oat01-" + "a" * 40) == ["anthropic_key"]
    assert find_leaks("ghs_" + "A1" * 15) == ["github_token"]
    assert find_leaks("github_pat_" + "x" * 30) == ["github_pat"]
    assert find_leaks("https://x-access-token:abc123@github.com/o/r") == ["url_credentials"]


def test_ordinary_text_is_clean():
    text = "sk-ant-oat01- prefix is expected; see https://github.com/o/r/blob/abc/x.py#L3 and ghs_ tokens"
    assert find_leaks(text) == []


def test_the_canary_is_caught():
    canary = canary_for("12345")
    assert canary == "issuepilot-canary-12345"
    assert find_leaks(f"value is {canary}", canary) == ["canary"]
    assert find_leaks("value is issuepilot-canary-99", canary) == []


def run_publish(monkeypatch, analysis: dict, run_id: str = "777", summary=None) -> tuple[int, FakeGh]:
    gh = FakeGh()
    monkeypatch.setattr(publish, "GitHub", lambda repo: GitHub(repo, gh))
    for key, value in {
        "REPO": "o/r", "SHA": "9aaa1d4" + "0" * 33, "RUN_URL": "https://run", "ISSUE_NUMBER": "2",
        "REPO_ROOT": str(FIXTURES / "minibill_repo"), "GITHUB_RUN_ID": run_id,
        "ANALYSIS": json.dumps(analysis), "METRICS": "{}", "INVESTIGATE_RESULT": "success",
        "LANGUAGE": "Turkish",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    if summary is not None:
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    return publish.main(), gh


def posted_body(gh: FakeGh) -> str:
    return json.loads(gh.calls[-1][1])["body"]


def test_clean_analysis_is_published(monkeypatch):
    analysis = json.loads((FIXTURES / "v2_issue2_analysis.json").read_text(encoding="utf-8"))
    code, gh = run_publish(monkeypatch, analysis)
    assert code == 0
    assert "Hata analizi" in posted_body(gh)


def test_feature_request_posts_no_comment(monkeypatch, tmp_path):
    analysis = json.loads((FIXTURES / "v2_issue2_analysis.json").read_text(encoding="utf-8"))
    analysis.update(kind="feature_request", headline="Asks for a CSV export.", evidence=[], suggested_fixes=[])
    summary_file = tmp_path / "summary.md"
    code, gh = run_publish(monkeypatch, analysis, summary=summary_file)
    assert code == 0 and gh.calls == []
    assert "no comment posted" in summary_file.read_text(encoding="utf-8")


def test_injected_canary_blocks_publication(monkeypatch):
    # What a successful prompt injection would look like: the environment value
    # copied into a field that is cut short in the comment.
    analysis = json.loads((FIXTURES / "v2_issue2_analysis.json").read_text(encoding="utf-8"))
    analysis["headline"] = "x" * 400 + " issuepilot-canary-777"
    code, gh = run_publish(monkeypatch, analysis, run_id="777")
    body = posted_body(gh)
    assert code == 1
    assert "Analiz yayınlanmadı" in body
    assert "issuepilot-canary-777" not in body and "xxxx" not in body


def test_token_in_a_detail_field_blocks_publication(monkeypatch):
    analysis = json.loads((FIXTURES / "v2_issue2_analysis.json").read_text(encoding="utf-8"))
    analysis["assumptions"] = ["remote is https://x-access-token:ghs_" + "Z" * 36 + "@github.com/o/r"]
    code, gh = run_publish(monkeypatch, analysis)
    assert code == 1
    assert "ghs_" not in posted_body(gh)
