"""Check an analysis against the repository before it is published.

Claude cites files, line ranges and verbatim quotes. Each citation is checked
against the checkout: the file must exist inside the repository and the quote must
appear in it. A quote found on other lines keeps its place with corrected line
numbers; a quote found nowhere is moved out of the evidence. Issue, pull request and
commit references are checked against GitHub through a callable supplied by the caller.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["verified", "corrected", "unverified"]

# Reasons an evidence item could not be verified.
OUTSIDE_REPOSITORY = "outside_repository"
FILE_NOT_FOUND = "file_not_found"
EMPTY_QUOTE = "empty_quote"
QUOTE_NOT_FOUND = "quote_not_found"

CONFIDENCE_ORDER = ["low", "medium", "high"]


@dataclass(frozen=True)
class EvidenceCheck:
    item: dict
    status: Status
    original_lines: tuple[int, int] | None = None  # set when status == "corrected"
    reason: str | None = None  # set when status == "unverified"


@dataclass(frozen=True)
class Verified:
    """An analysis after checking; evidence is split by outcome."""

    analysis: dict
    evidence: list[EvidenceCheck]
    unverified: list[EvidenceCheck]
    dropped_related: list[dict]
    confidence_note: str | None  # why confidence was lowered, if it was


def resolve_in_repo(root: Path, path: str) -> Path | None:
    """Return the file for a repository-relative path, or None if it escapes the repo."""
    if not path or Path(path).is_absolute() or path.startswith(("/", "\\")):
        return None
    root = root.resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        return None
    return target


def find_quote(quote: str, text: str) -> list[tuple[int, int]]:
    """Return every (start, end) line range, 1-based, where the quote appears.

    Lines are compared with surrounding whitespace stripped and blank lines ignored,
    so a quote that lost its indentation or skipped an empty line still matches.
    """
    wanted = [line.strip() for line in quote.splitlines() if line.strip()]
    if not wanted:
        return []
    lines = [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1) if line.strip()]
    found = []
    for i in range(len(lines) - len(wanted) + 1):
        window = lines[i : i + len(wanted)]
        if [content for _, content in window] == wanted:
            found.append((window[0][0], window[-1][0]))
    return found


def check_evidence(item: dict, root: Path) -> EvidenceCheck:
    target = resolve_in_repo(root, item["path"])
    if target is None:
        return EvidenceCheck(item, "unverified", reason=OUTSIDE_REPOSITORY)
    if not target.is_file():
        return EvidenceCheck(item, "unverified", reason=FILE_NOT_FOUND)
    if not item["quote"].strip():
        return EvidenceCheck(item, "unverified", reason=EMPTY_QUOTE)

    matches = find_quote(item["quote"], target.read_text(encoding="utf-8", errors="replace"))
    if not matches:
        return EvidenceCheck(item, "unverified", reason=QUOTE_NOT_FOUND)

    start = item["start_line"]
    end = max(item["end_line"], start)
    if any(start <= m_start and m_end <= end for m_start, m_end in matches):
        return EvidenceCheck(item, "verified")

    m_start, m_end = min(matches, key=lambda m: abs(m[0] - start))
    fixed = {**item, "start_line": m_start, "end_line": m_end}
    return EvidenceCheck(fixed, "corrected", original_lines=(item["start_line"], item["end_line"]))


def lower_confidence(confidence: str, checks: list[EvidenceCheck], kind: str) -> tuple[str, str | None]:
    """Cap confidence by how much of the evidence held up."""
    found = [c for c in checks if c.status != "unverified"]
    missing = len(checks) - len(found)
    if kind == "bug_analysis" and not checks:
        cap, note = "low", "no_evidence"
    elif checks and not found:
        cap, note = "low", "no_evidence_verified"
    elif missing:
        cap, note = "medium", "some_evidence_unverified"
    else:
        return confidence, None
    if CONFIDENCE_ORDER.index(confidence) <= CONFIDENCE_ORDER.index(cap):
        return confidence, None
    return cap, note


def verify(
    analysis: dict,
    root: Path,
    ref_exists: Callable[[str, str], bool | None],
) -> Verified:
    """Check evidence against the checkout and references against GitHub.

    ref_exists(kind, ref) returns True or False, or None when it could not tell;
    a reference is dropped only on a definite False.
    """
    checks = [check_evidence(item, root) for item in analysis["evidence"]]
    kept = [c for c in checks if c.status != "unverified"]
    unverified = [c for c in checks if c.status == "unverified"]

    related, dropped = [], []
    for ref in analysis["related"]:
        (dropped if ref_exists(ref["kind"], ref["ref"]) is False else related).append(ref)

    confidence, note = lower_confidence(analysis["confidence"], checks, analysis["kind"])
    cleaned = {
        **analysis,
        "confidence": confidence,
        "evidence": [c.item for c in kept],
        "related": related,
    }
    return Verified(cleaned, kept, unverified, dropped, note)

