"""Point the reusable workflow's own action refs at one IssuePilot ref.

Usage: python scripts/pin_refs.py <ref>        e.g. v1.0.0, main, or a commit SHA
       python scripts/pin_refs.py --check <ref>  exit 1 if any ref differs

A caller pins `.github/workflows/issuepilot.yml@<ref>`; the workflow then runs
`brkakyldz/IssuePilot/actions/{investigate,publish}@<ref>`, which carry the prompt,
schema and publish code of that same ref. On main the refs say @main; a release
commit pins them to its tag (ADR 0003).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "issuepilot.yml"
ACTION_REF = re.compile(r"(uses:\s*brkakyldz/IssuePilot/actions/[a-z]+)@([A-Za-z0-9._/-]+)")


def refs(text: str) -> list[str]:
    return [m.group(2) for m in ACTION_REF.finditer(text)]


def pin(text: str, ref: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", ref):
        raise ValueError(f"not a git ref: {ref!r}")
    return ACTION_REF.sub(lambda m: f"{m.group(1)}@{ref}", text)


def main(argv: list[str]) -> int:
    check = argv[:1] == ["--check"]
    args = argv[1:] if check else argv
    if len(args) != 1:
        sys.exit(__doc__)
    ref = args[0]
    text = WORKFLOW.read_text(encoding="utf-8")
    found = refs(text)
    if not found:
        sys.exit(f"no IssuePilot action refs in {WORKFLOW}")
    if check:
        wrong = [r for r in found if r != ref]
        print("ok" if not wrong else f"refs not at {ref}: {sorted(set(wrong))}")
        return 1 if wrong else 0
    WORKFLOW.write_text(pin(text, ref), encoding="utf-8", newline="\n")
    print(f"pinned {len(found)} action refs to @{ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
