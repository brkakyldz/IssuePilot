"""Name the reason an investigation produced no analysis.

Claude Code reports some failures as `subtype: success` with `is_error: true`
(a rejected token looked exactly like that in M1), so the job result alone is not
enough. The metrics come from the final `result` message of the run.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Failure:
    code: str


# The message for each code, in each language, lives in issuepilot.i18n.


def classify(investigate_result: str, metrics: dict | None) -> Failure:
    """investigate_result is the job result: success, failure, cancelled or skipped."""
    if investigate_result == "cancelled":
        return Failure("cancelled")
    if not metrics:
        return Failure("not_started")

    status = metrics.get("api_error_status")
    text = (metrics.get("result") or "").lower()
    if status == 401 or "not logged in" in text or "authenticate" in text:
        code = "auth"
    elif status == 429 or "usage limit" in text or "rate limit" in text:
        code = "usage_limit"
    elif metrics.get("subtype") == "error_max_turns":
        code = "max_turns"
    elif metrics.get("subtype") == "error_max_budget_usd":
        code = "budget"
    else:
        code = "no_output"
    return Failure(code)
