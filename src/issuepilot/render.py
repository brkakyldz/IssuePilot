"""Turn a verified analysis, or a failure, into the issue comment.

The comment has a short part that is always visible (cause, location, fix,
uncertainty) and a collapsed <details> part with everything else. All text written
by Claude passes through `safe()` first: issue text can steer what Claude writes,
so it must not be able to ping people or inject HTML into the comment.
"""

from __future__ import annotations

import re

from issuepilot.failure import Failure
from issuepilot.i18n import text_for
from issuepilot.verify import EvidenceCheck, Verified

MARKER = "<!-- issuepilot -->"

RELATED_KIND = {"issue": "issue", "pull_request": "PR", "commit": "commit"}

HEADLINE_MAX = 300
FIX_MAX = 250
UNCERTAINTY_MAX = 200
MAX_EVIDENCE = 3
MAX_QUESTIONS = 5

_CODE_SPAN = re.compile(r"(`[^`\n]+`)")
_MENTION = re.compile(r"@(?=[A-Za-z0-9])")


def safe(text: str) -> str:
    """Escape HTML and break @mentions everywhere except inside `code spans`."""
    parts = _CODE_SPAN.split(text)
    for i in range(0, len(parts), 2):  # even indexes are outside code spans
        part = parts[i].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts[i] = _MENTION.sub("@​", part)
    return "".join(parts)


def short(text: str, limit: int) -> str:
    """One line, at most `limit` characters."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def fence(quote: str) -> str:
    """A code fence longer than any backtick run inside the quote."""
    longest = max((len(run) for run in re.findall(r"`+", quote)), default=0)
    return "`" * max(3, longest + 1)


def permalink(repo: str, sha: str, item: dict) -> str:
    start, end = item["start_line"], item["end_line"]
    anchor = f"L{start}" if start >= end else f"L{start}-L{end}"
    return f"https://github.com/{repo}/blob/{sha}/{item['path']}#{anchor}"


def line_label(item: dict) -> str:
    start, end = item["start_line"], item["end_line"]
    lines = f"{start}" if start >= end else f"{start}-{end}"
    return f"{item['path']}:{lines}"


def _section(title: str, lines: list[str]) -> list[str]:
    return [f"#### {title}", "", *lines, ""] if lines else []


def _evidence_lines(checks: list[EvidenceCheck], repo: str, sha: str, t: dict) -> list[str]:
    out = []
    for check in checks[:MAX_EVIDENCE]:
        item = check.item
        out.append(f"- [`{line_label(item)}`]({permalink(repo, sha, item)}): {safe(item['why'])}")
        if check.status == "corrected":
            start, end = check.original_lines
            out.append(f"  <sub>{t['line_corrected'].format(start=start, end=end)}</sub>")
        mark = fence(item["quote"])
        out += [f"  {mark}", *(f"  {line}" for line in item["quote"].splitlines()), f"  {mark}"]
    return out


def _unverified_lines(result: Verified, t: dict) -> list[str]:
    out = [
        f"- `{safe(c.item['path'])}`: {safe(c.item['why'])} "
        f"<sub>({t['unverified_reason'].get(c.reason, c.reason)})</sub>"
        for c in result.unverified
    ]
    out += [f"- {safe(r['ref'])}: {t['ref_not_found']}" for r in result.dropped_related]
    if out and result.confidence_note:
        out.append("")
        out.append(t["confidence_lowered_note"])
    return out


def _fix_lines(a: dict, t: dict) -> list[str]:
    """The first fix is the Suggestion line already shown above: name it, do not repeat it."""
    out = []
    for n, fix in enumerate(a["suggested_fixes"], 1):
        files = ", ".join(f"`{f}`" for f in fix["files"])
        text = t["fix_above"] if n == 1 and a["fix_summary"].strip() else safe(fix["description"])
        out.append(f"{n}. **{safe(fix['title'])}**: {text}" + (f" ({files})" if files else ""))
    return out


def _details(result: Verified, repo: str, sha: str, t: dict) -> list[str]:
    a = result.analysis
    related = [f"- {safe(r['ref'])} ({RELATED_KIND[r['kind']]}): {safe(r['why'])}" for r in a["related"]]
    fixes = _fix_lines(a, t)
    questions = [] if a["kind"] == "needs_info" else a["open_questions"]
    body = [
        *_section(t["explanation"], [safe(a["explanation"])] if a["explanation"].strip() else []),
        *_section(t["evidence"], _evidence_lines(result.evidence, repo, sha, t)),
        *_section(t["unverified"], _unverified_lines(result, t)),
        *_section(t["related"], related),
        *_section(t["suggested_fixes"], fixes),
        *_section(t["verification_steps"], [f"- {safe(s)}" for s in a["verification_steps"]]),
        *_section(t["assumptions"], [f"- {safe(s)}" for s in a["assumptions"]]),
        *_section(t["open_questions"], [f"- {safe(s)}" for s in questions]),
    ]
    if not body:
        return []
    return ["<details>", f"<summary>{t['details_summary']}</summary>", "", *body, "</details>", ""]


def footer(sha: str, run_url: str, metrics: dict | None, t: dict) -> str:
    parts = [t["read_only"], f"commit `{sha[:7]}`"]
    metrics = metrics or {}
    if metrics.get("num_turns") is not None:
        parts.append(t["turn" if metrics["num_turns"] == 1 else "turns"].format(n=metrics["num_turns"]))
    if metrics.get("duration_ms") is not None:
        parts.append(t["seconds"].format(n=f"{metrics['duration_ms'] / 1000:.0f}"))
    parts.append(f"[{t['run_log']}]({run_url})")
    return "<sub>IssuePilot · " + " · ".join(parts) + "</sub>"


def render_analysis(
    result: Verified, repo: str, sha: str, run_url: str, metrics: dict | None, language: str = "English"
) -> str:
    t = text_for(language)
    a = result.analysis
    confidence = t["confidence"].get(a["confidence"], a["confidence"])
    if result.confidence_note:
        confidence += t["confidence_lowered"]
    kind = t["kind"].get(a["kind"], a["kind"])
    out = [MARKER, f"### IssuePilot · {kind} · {t['confidence_label']}: {confidence}", ""]

    if a["kind"] == "needs_info":
        out += [f"{t['missing']} {safe(short(a['headline'], HEADLINE_MAX))}", ""]
        questions = a["open_questions"][:MAX_QUESTIONS]
        if questions:
            out += [t["questions"], *(f"- {safe(short(q, HEADLINE_MAX))}" for q in questions), ""]
    else:
        out += [f"{t['cause']} {safe(short(a['headline'], HEADLINE_MAX))}", ""]
        if result.evidence:
            # A bare permalink on its own line renders as a code preview on GitHub.
            out += [t["where"], permalink(repo, sha, result.evidence[0].item), ""]
        else:
            out += [t["where_none"], ""]
        if a["fix_summary"].strip():
            out += [f"{t['fix']} {safe(short(a['fix_summary'], FIX_MAX))}", ""]

    if a["uncertainty"].strip():
        out += [f"{t['unsure']} {safe(short(a['uncertainty'], UNCERTAINTY_MAX))}", ""]
    out += _details(result, repo, sha, t)
    out.append(footer(sha, run_url, metrics, t))
    return "\n".join(out) + "\n"


def render_failure(failure: Failure, sha: str, run_url: str, metrics: dict | None, language: str = "English") -> str:
    t = text_for(language)
    title = f"### IssuePilot · {t['failed_title']}"
    reason = f"{t['reason']} {t['failures'][failure.code]}"
    return "\n".join([MARKER, title, "", reason, "", footer(sha, run_url, metrics, t)]) + "\n"
