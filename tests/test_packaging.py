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
    assert "blockReadsOutsideWorkingDirectories\":true" in INVESTIGATE


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
    for flag in ["--disallowedTools", "blockReadsOutsideWorkingDirectories"]:
        line = next(l for l in INVESTIGATE.splitlines() if flag in l).strip()
        assert line in probe, flag


def test_action_and_workflow_files_are_valid_yaml():
    yaml = pytest.importorskip("yaml")
    for path in [*(ROOT / "actions").glob("*/action.yml"), *(ROOT / "templates").glob("*.yml"), *(ROOT / ".github" / "workflows").glob("*.yml")]:
        assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict), path
