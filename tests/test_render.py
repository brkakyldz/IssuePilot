import json
from pathlib import Path

from issuepilot.failure import classify
from issuepilot.render import MARKER, fence, render_analysis, render_failure, safe, short
from issuepilot.verify import verify

FIXTURES = Path(__file__).parent / "fixtures"
REPO = FIXTURES / "minibill_repo"
SHA = "9aaa1d47e911626c6d01574ea1cdedb87c544645"
RUN = "https://github.com/o/r/actions/runs/1"
METRICS = {"num_turns": 6, "duration_ms": 29113}


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def rendered(analysis: dict) -> str:
    result = verify(analysis, REPO, lambda kind, ref: True)
    return render_analysis(result, "o/r", SHA, RUN, METRICS, "Turkish")


def visible_part(comment: str) -> str:
    return comment.split("<details>")[0]


def test_bug_analysis_shows_the_short_part_first():
    comment = rendered(load("v2_issue2_analysis.json"))
    top = visible_part(comment)

    assert comment.startswith(MARKER)
    assert "### IssuePilot · Hata analizi · güven: yüksek" in top
    for label in ["**Neden:**", "**Nerede:**", "**Öneri:**", "**Emin olmadığım:**"]:
        assert label in top
    # The location is the first evidence item, as a bare permalink line.
    assert f"\nhttps://github.com/o/r/blob/{SHA}/minibill/money.py#L9-L11\n" in top
    assert len(top.splitlines()) <= 14
    assert "<summary>" in comment and comment.rstrip().endswith("</sub>")


def test_corrected_line_numbers_are_disclosed():
    comment = rendered(load("v2_issue2_analysis.json"))
    assert "minibill/pricing.py#L14-L16" in comment
    assert "analizde 24-27 yazıyordu" in comment


def test_empty_sections_are_not_rendered():
    analysis = load("v2_issue2_analysis.json")
    analysis["assumptions"] = []
    analysis["open_questions"] = []
    comment = rendered(analysis)
    assert "Varsayımlar" not in comment
    assert "Açık sorular" not in comment
    assert "_yok_" not in comment


def test_the_first_fix_points_at_the_suggestion_instead_of_repeating_it():
    analysis = load("v2_issue2_analysis.json")
    analysis["fix_summary"] = "Use Decimal with ROUND_HALF_UP in to_cents."
    analysis["suggested_fixes"] = [
        {"title": "Decimal half-up", "files": ["minibill/money.py"], "description": "FIRST-DESCRIPTION"},
        {"title": "Integer cents", "files": [], "description": "SECOND-DESCRIPTION"},
    ]
    comment = rendered(analysis)
    assert "1. **Decimal half-up**: yukarıdaki öneri (`minibill/money.py`)" in comment
    assert "FIRST-DESCRIPTION" not in comment and "2. **Integer cents**: SECOND-DESCRIPTION" in comment

    analysis["fix_summary"] = ""  # nothing shown above: the first fix is written out
    assert "FIRST-DESCRIPTION" in rendered(analysis)


def test_needs_info_asks_questions_up_front_and_offers_no_fix():
    comment = rendered(load("v2_issue3_analysis.json"))
    top = visible_part(comment)
    assert "Daha fazla bilgi gerekiyor" in top
    assert "**Eksik olan:**" in top and "**Sorular:**" in top
    assert "**Öneri:**" not in top and "Çözüm önerileri" not in comment
    assert top.count("\n- ") == 5


def test_unverified_evidence_is_shown_and_lowers_confidence():
    analysis = load("v2_issue2_analysis.json")
    analysis["evidence"] = [
        {"path": "minibill/tax.py", "start_line": 1, "end_line": 1, "quote": "x", "why": "uydurma"}
    ]
    comment = rendered(analysis)
    assert "güven: düşük (kontrolden sonra düşürüldü)" in comment
    assert "**Nerede:** Doğrulanmış bir konum yok." in comment
    assert "dosya bulunamadı" in comment


def test_mentions_and_html_from_claude_are_neutralised():
    analysis = load("v2_issue2_analysis.json")
    analysis["headline"] = "Ping @octocat </details><!-- issuepilot --> but keep `a @b <c>` code"
    comment = rendered(analysis)
    top = visible_part(comment)
    assert "@octocat" not in comment
    assert "@​octocat" in top
    assert "&lt;/details&gt;" in top
    assert comment.count(MARKER) == 1
    assert "`a @b <c>`" in top


def test_text_helpers():
    assert short("a\n  b", 10) == "a b"
    assert short("x" * 20, 10) == "x" * 9 + "…"
    assert fence("plain") == "```"
    assert fence("has ``` inside") == "````"
    assert safe("a & b") == "a &amp; b"


def test_failure_comment_names_the_cause():
    # M1 run 1: the rejected token was reported as subtype success, is_error true.
    metrics = {"subtype": "success", "is_error": True, "api_error_status": 401,
               "result": "Not logged in · Please run /login", "num_turns": 1, "duration_ms": 2227}
    failure = classify("failure", metrics)
    comment = render_failure(failure, SHA, RUN, metrics, "Turkish")
    assert failure.code == "auth"
    assert "Analiz yapılamadı" in comment and "claude setup-token" in comment


def test_failure_classification():
    assert classify("cancelled", None).code == "cancelled"
    assert classify("failure", None).code == "not_started"
    assert classify("failure", {"api_error_status": 429}).code == "usage_limit"
    assert classify("failure", {"subtype": "error_max_turns"}).code == "max_turns"
    assert classify("failure", {"subtype": "error_max_budget_usd"}).code == "budget"
    assert classify("failure", {"subtype": "success", "is_error": False}).code == "no_output"


def test_labels_follow_the_configured_language():
    result = verify(load("v2_issue2_analysis.json"), REPO, lambda kind, ref: True)
    english = render_analysis(result, "o/r", SHA, RUN, METRICS)
    assert "### IssuePilot · Bug analysis · confidence: high" in english
    for label in ["**Cause:**", "**Where:**", "**Suggestion:**", "**Not sure about:**", "6 turns", "read-only, code not run"]:
        assert label in english
    assert "Neden" not in english
    # A language without a label table gets English labels around Claude's text.
    assert "**Cause:**" in render_analysis(result, "o/r", SHA, RUN, METRICS, "German")


def test_every_failure_has_a_message_in_every_language():
    from issuepilot.i18n import EN, TR
    codes = {"auth", "usage_limit", "max_turns", "budget", "cancelled", "no_output", "secret_detected", "not_started"}
    assert set(EN["failures"]) == set(TR["failures"]) == codes
    assert EN.keys() == TR.keys()
    english = render_failure(classify("cancelled", None), SHA, RUN, None)
    assert "Analysis failed" in english and "cancelled" in english


def test_footer_counts_one_turn_in_the_singular():
    english = render_failure(classify("failure", {"api_error_status": 401, "num_turns": 1}), SHA, RUN, {"num_turns": 1})
    assert "1 turn ·" in english
