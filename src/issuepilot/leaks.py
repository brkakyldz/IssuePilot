"""Refuse to publish a comment that contains a credential.

An injected instruction could make Claude copy a secret into its answer: the M2
security probe showed the file tools could read /proc/self/environ before they were
restricted. This is the last check before anything is posted. It looks for the
shapes of Anthropic and GitHub credentials, and for the run's canary: a harmless
value placed in the investigate job's environment so that any environment leak
shows up, even of a secret this module has no pattern for.
"""

from __future__ import annotations

import re

PATTERNS = {
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "github_pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    "url_credentials": re.compile(r"https?://[^/\s:@]+:[^/\s@]+@"),
}


def canary_for(run_id: str) -> str:
    """The canary value; the workflow sets ISSUEPILOT_CANARY to the same string."""
    return f"issuepilot-canary-{run_id}"


def find_leaks(text: str, canary: str | None = None) -> list[str]:
    """Names of the credential shapes found in text, empty when it is clean."""
    found = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    if canary and canary in text:
        found.append("canary")
    return found
