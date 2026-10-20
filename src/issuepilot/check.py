"""Verify an analysis without publishing it; used by backtests.

  python -m issuepilot.check <analysis.json> <repo_root> <out.json>

Runs the same evidence check as the publish step against the checkout at
<repo_root>. Commit references are checked with the local git history; issue and
pull request references cannot be checked in a backtest and are kept. An empty or
unreadable analysis writes {"analysis": null}.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from issuepilot.verify import verify


def local_ref_exists(root: Path):
    def check(kind: str, ref: str) -> bool | None:
        if kind != "commit":
            return None
        result = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{ref.strip()}^{{commit}}"],
            capture_output=True,
        )
        return result.returncode == 0

    return check


def check_file(analysis_path: Path, root: Path) -> dict:
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        analysis = None
    if not isinstance(analysis, dict):
        return {"analysis": None}
    result = verify(analysis, root, local_ref_exists(root))
    return {
        "analysis": result.analysis,
        "original_confidence": analysis.get("confidence"),
        "evidence": [{**asdict(c), "original_lines": c.original_lines} for c in result.evidence],
        "unverified": [asdict(c) for c in result.unverified],
        "dropped_related": result.dropped_related,
        "confidence_note": result.confidence_note,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.exit(__doc__)
    analysis_path, root, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    out.write_text(json.dumps(check_file(analysis_path, root), indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
