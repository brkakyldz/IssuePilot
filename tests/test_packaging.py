"""The packaged layout: action refs, prompt placeholders, and what the caller sees."""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pin_refs  # noqa: E402

WORKFLOW = (ROOT / ".github" / "workflows" / "issuepilot.yml").read_text(encoding="utf-8")
INVESTIGATE = (ROOT / "actions" / "investigate" / "action.yml").read_text(encoding="utf-8")
PROMPT = (ROOT / "prompts" / "investigate.md").read_text(encoding="utf-8")


def test_workflow_uses_both_actions_at_one_ref():
    assert pin_refs.refs(WORKFLOW) == ["main", "main"]
    pinned = pin_refs.pin(WORKFLOW, "v1.0.0")
    assert pin_refs.refs(pinned) == ["v1.0.0", "v1.0.0"]
    assert pinned.replace("@v1.0.0", "@main") == WORKFLOW


def test_pin_rejects_anything_but_a_ref():
    for bad in ["v1 ; rm -rf /", "", "a b", "$(x)"]:
        try:
            pin_refs.pin(WORKFLOW, bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")


def test_prompt_placeholders_are_all_filled_by_the_action():
    placeholders = set(re.findall(r"\$\{([A-Z_]+)\}", PROMPT))
    substituted = set(re.findall(r"\$([A-Z_]+)", re.search(r"envsubst '([^']+)'", INVESTIGATE).group(1)))
    assert placeholders == substituted


def test_agent_never_gets_write_tools_or_bare_file_tools():
    allowed = re.findall(r'tools="([^"]*)"', INVESTIGATE) + re.findall(r'tools="\$tools,([^"]*)"', INVESTIGATE)
    joined = ",".join(allowed)
    for tool in ["Edit", "Write", "comment", "Read,", "Grep", "Glob", "gh api"]:
        assert tool not in joined, tool
    assert "blockReadsOutsideWorkingDirectories: true" in INVESTIGATE


def test_jobs_keep_their_permissions():
    investigate, publish = WORKFLOW.split("\n  publish:\n")
    assert "issues: read" in investigate and "write" not in investigate.split("permissions:", 2)[2].split("outputs:")[0]
    assert "issues: write" in publish and "anthropics/claude-code-action" not in publish
    for key in ["timeout-minutes", "concurrency"]:
        assert key in WORKFLOW


def test_security_probe_matches_the_investigate_action():
    probe = (ROOT / "security" / "probe-capabilities.yml").read_text(encoding="utf-8")
    action_pin = re.search(r"anthropics/claude-code-action@(\S+)", INVESTIGATE).group(1)
    assert re.search(r"anthropics/claude-code-action@(\S+)", probe).group(1) == action_pin
    probe_allowed = re.search(r'--allowedTools "([^"]+)"', probe).group(1)
    base = re.search(r'tools="(Bash[^"]+)"', INVESTIGATE).group(1)
    issue_tools = re.search(r'tools="\$tools,([^"]+)"', INVESTIGATE).group(1)
    assert probe_allowed == f"{base},{issue_tools}"
    for flag in ["--disallowedTools", "--setting-sources", "--strict-mcp-config"]:
        line = next(l for l in INVESTIGATE.splitlines() if flag in l).strip()
        assert line in probe, flag
    assert "blockReadsOutsideWorkingDirectories" in probe


def test_action_and_workflow_files_are_valid_yaml():
    yaml = pytest.importorskip("yaml")
    for path in [*(ROOT / "actions").glob("*/action.yml"), *(ROOT / "templates").glob("*.yml"), *(ROOT / ".github" / "workflows").glob("*.yml")]:
        assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict), path


def test_the_investigated_repository_cannot_configure_the_agent():
    # A repository's .claude/settings.json hooks and .mcp.json servers would run its
    # own commands inside the investigate job (backtest run 39509333942, caldav).
    args = INVESTIGATE.split("claude_args: |", 1)[1]
    assert "--setting-sources user" in args and "--strict-mcp-config" in args


def _hook(tmp_path, payload: dict, budget: int = 3) -> str:
    import json
    import shutil
    import subprocess

    if not shutil.which("bash") or not shutil.which("jq"):
        pytest.skip("needs bash and jq")
    env = {**__import__("os").environ, "ISSUEPILOT_BUDGET_FILE": str(tmp_path / "count"), "ISSUEPILOT_TOOL_BUDGET": str(budget)}
    script = (ROOT / "actions" / "investigate" / "tool-budget.sh").as_posix()
    return subprocess.run(["bash", script], input=json.dumps(payload), capture_output=True, text=True, env=env).stdout


def test_tool_budget_hook_refuses_then_stops(tmp_path):
    call = {"tool_name": "Bash", "tool_input": {"command": "git log -1"}}
    assert [_hook(tmp_path, call) for _ in range(3)] == ["", "", ""]
    assert '"deny"' in _hook(tmp_path, call) and "budget exhausted" in _hook(tmp_path, call)
    for _ in range(8):
        _hook(tmp_path, call)
    assert '"continue":false' in _hook(tmp_path, call).replace(" ", "")
    # The structured result is never refused, even past the budget.
    assert _hook(tmp_path, {"tool_name": "StructuredOutput", "tool_input": {}}) == ""


def test_tool_budget_hook_refuses_an_empty_bash_call(tmp_path):
    out = _hook(tmp_path, {"tool_name": "Bash", "tool_input": {}}, budget=40)
    assert '"deny"' in out and "without a command" in out


def test_analysis_is_recovered_from_the_transcript_when_the_action_drops_it(tmp_path):
    import json
    import shutil
    import subprocess

    if not shutil.which("jq"):
        pytest.skip("needs jq")
    expr = re.search(r"jq -c '(\[\.\[\] \| select\(\.type == \"result\"\)\] \| last \| \.structured_output[^']*)'", INVESTIGATE).group(1)
    transcript = tmp_path / "t.json"
    transcript.write_text(json.dumps([{"type": "assistant"}, {"type": "result", "structured_output": {"kind": "needs_info"}}]))
    out = subprocess.run(["jq", "-c", expr, str(transcript)], capture_output=True, text=True).stdout.strip()
    assert json.loads(out) == {"kind": "needs_info"}
    transcript.write_text(json.dumps([{"type": "result", "structured_output": None}]))
    assert subprocess.run(["jq", "-c", expr, str(transcript)], capture_output=True, text=True).stdout.strip() == ""


def _gate(event: str, labels: list, author: str = "User", skip: str = "enhancement,feature,epic") -> str:
    import json
    import os
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("bash") or not shutil.which("jq"):
        pytest.skip("needs bash and jq")
    script = WORKFLOW.split("        run: |\n", 1)[1].split("\n\n  investigate:", 1)[0]
    script = "\n".join(line[10:] for line in script.splitlines())
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out")
        env = {**os.environ, "EVENT": event, "AUTHOR_TYPE": author, "LABELS": json.dumps(labels),
               "SKIP_LABELS": skip, "GITHUB_OUTPUT": out, "GITHUB_STEP_SUMMARY": os.path.join(tmp, "s")}
        subprocess.run(["bash", "-c", script], env=env, check=True)
        return open(out).read().strip()


def test_gate_skips_bots_and_skip_labels_before_any_ai_runs():
    assert _gate("issues", ["bug"]) == "run=true"
    assert _gate("issues", []) == "run=true"
    assert _gate("issues", ["Feature", "area:web"]) == "run=false"
    assert _gate("issues", ["issuepilot:skip"]) == "run=false"
    assert _gate("issues", ["bug"], author="Bot") == "run=false"
    assert _gate("issues", ["question"], skip="question, help wanted") == "run=false"
    assert _gate("workflow_dispatch", ["feature"]) == "run=true"
