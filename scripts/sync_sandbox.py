"""Copy IssuePilot into a target repository checkout (until M4 packaging).

Usage: python scripts/sync_sandbox.py <path-to-target-checkout>

Writes .github/workflows/issuepilot.yml and .github/issuepilot/ (prompt, schema and
the issuepilot package). Files left over from earlier layouts are removed.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STALE = [".github/issuepilot/render.py"]


def main(target: Path) -> None:
    if not (target / ".git").exists():
        sys.exit(f"{target} is not a git checkout")
    dest = target / ".github" / "issuepilot"
    package = dest / "issuepilot"
    if package.exists():
        shutil.rmtree(package)
    package.mkdir(parents=True)
    for source in sorted((ROOT / "src" / "issuepilot").glob("*.py")):
        shutil.copy2(source, package / source.name)
    shutil.copy2(ROOT / "prompts" / "investigate.md", dest / "prompt.md")
    shutil.copy2(ROOT / "schema" / "analysis.schema.json", dest / "analysis.schema.json")
    shutil.copy2(ROOT / "workflow" / "issuepilot.yml", target / ".github" / "workflows" / "issuepilot.yml")
    for stale in STALE:
        (target / stale).unlink(missing_ok=True)
    print(f"synced IssuePilot into {target}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve())
