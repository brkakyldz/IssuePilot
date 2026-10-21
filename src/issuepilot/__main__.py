"""Publish step: verify the analysis, render the comment, post or update it.

Runs in the publish job, which has no Claude in it. Everything comes from
environment variables so that no issue-derived text passes through a shell:

  ANALYSIS            structured_output of the investigate job (may be empty)
  METRICS             JSON from the run's final result message (may be empty)
  INVESTIGATE_RESULT  the investigate job's result: success, failure, cancelled
  REPO, SHA, ISSUE_NUMBER, RUN_URL
  LANGUAGE            language of the comment's labels (default English)
  REPO_ROOT           checkout of the repository at SHA (default: .)
  GITHUB_RUN_ID       set by Actions; names the run's canary (see leaks.py)
  GITHUB_STEP_SUMMARY optional; a run summary is appended when set
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from issuepilot.failure import Failure, classify
from issuepilot.github import GitHub
from issuepilot.leaks import canary_for, find_leaks
from issuepilot.render import render_analysis, render_failure
from issuepilot.verify import Verified, verify


def parse_json(raw: str | None) -> dict | None:
    if not raw or not raw.strip() or raw.strip() == "null":
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def summary(metrics: dict | None, result: Verified | None, failure_code: str | None, action: str) -> str:
    m = metrics or {}
    rows = [
        ("outcome", failure_code or result.analysis["kind"]),
        ("comment", action),
        ("turns", m.get("num_turns")),
        ("duration (s)", round(m["duration_ms"] / 1000) if m.get("duration_ms") else None),
        ("list-price equivalent (USD)", m.get("total_cost_usd")),
    ]
    if result:
        statuses = [c.status for c in result.evidence] + ["unverified"] * len(result.unverified)
        rows += [
            ("evidence verified", statuses.count("verified")),
            ("evidence corrected", statuses.count("corrected")),
            ("evidence unverified", statuses.count("unverified")),
            ("references dropped", len(result.dropped_related)),
            ("confidence", result.analysis["confidence"] + (f" ({result.confidence_note})" if result.confidence_note else "")),
        ]
    lines = ["### IssuePilot", "", "| | |", "|---|---|"]
    lines += [f"| {name} | {value} |" for name, value in rows if value is not None]
    return "\n".join(lines) + "\n"


def main() -> int:
    env = os.environ
    repo, sha, run_url = env["REPO"], env["SHA"], env["RUN_URL"]
    issue = int(env["ISSUE_NUMBER"])
    language = env.get("LANGUAGE", "English")
    metrics = parse_json(env.get("METRICS"))
    analysis = parse_json(env.get("ANALYSIS"))
    github = GitHub(repo)

    # A feature request or plan reports no failure: there is nothing to investigate,
    # and a comment would only be noise on the maintainers' own planning issues.
    if analysis is not None and analysis.get("kind") == "feature_request":
        print(f"#{issue} is a feature request or plan; no comment posted")
        if env.get("GITHUB_STEP_SUMMARY"):
            with open(env["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
                fh.write("### IssuePilot\n\nFeature request or plan: nothing to investigate, no comment posted.\n")
        return 0

    result, failure_code = None, None
    if analysis is not None:
        result = verify(analysis, Path(env.get("REPO_ROOT", ".")), github.ref_exists)
        body = render_analysis(result, repo, sha, run_url, metrics, language)
    else:
        failure = classify(env.get("INVESTIGATE_RESULT", "failure"), metrics)
        failure_code = failure.code
        body = render_failure(failure, sha, run_url, metrics, language)

    # Scan the raw analysis too: the comment shortens some fields, and half a token
    # is still a leak.
    canary = canary_for(env["GITHUB_RUN_ID"]) if env.get("GITHUB_RUN_ID") else None
    leaks = find_leaks(body + "\n" + (env.get("ANALYSIS") or "") + "\n" + (env.get("METRICS") or ""), canary)
    if leaks:
        print(f"::error::Analysis not published: it contains {', '.join(leaks)}")
        result, failure_code = None, "secret_detected"
        body = render_failure(Failure("secret_detected"), sha, run_url, None, language)

    action = github.upsert_comment(issue, body)
    print(f"IssuePilot comment {action} on #{issue}")

    if env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(summary(metrics, result, failure_code, action))
    # A failed investigation still exits 0 here: the comment is the report, and the
    # investigate job already carries the failure status. A blocked leak fails the
    # job so that it cannot go unnoticed.
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
