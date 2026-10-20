"""Cut an IssuePilot release: pin the workflow's action refs, tag, publish.

Usage: python scripts/release.py 1.0.0 [--push]

From a clean, up-to-date main whose tests pass, this creates a release commit on a
detached HEAD that pins `.github/workflows/issuepilot.yml`'s action refs to the new
tag (ADR 0003), tags it `v1.0.0` and `v1` (annotated), and with --push pushes both
tags and creates the GitHub release from the CHANGELOG section. Main keeps @main.
Moving an existing major tag (v1 on a later release) needs a forced tag push, which
this script leaves to the maintainer and prints instead.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pin_refs  # noqa: E402


def sh(*args: str, check: bool = True) -> str:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def changelog_section(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^## \[?v?{re.escape(version)}\]?.*?\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        sys.exit(f"CHANGELOG.md has no section for {version}")
    return match.group(1).strip()


def main(argv: list[str]) -> int:
    push = "--push" in argv
    args = [a for a in argv if a != "--push"]
    if len(args) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", args[0]):
        sys.exit(__doc__)
    version = args[0]
    tag, major = f"v{version}", f"v{version.split('.')[0]}"

    if sh("git", "status", "--porcelain"):
        sys.exit("working tree is not clean")
    sh("git", "fetch", "-q", "origin", "main", "--tags")
    if sh("git", "rev-parse", "HEAD") != sh("git", "rev-parse", "origin/main"):
        sys.exit("HEAD is not origin/main; check out (or detach at) origin/main first")
    if sh("git", "tag", "-l", tag):
        sys.exit(f"{tag} already exists")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if f'version = "{version}"' not in pyproject:
        sys.exit(f"pyproject.toml version is not {version}")
    notes = changelog_section(version)
    if subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT).returncode:
        sys.exit("tests fail")

    start = sh("git", "branch", "--show-current") or sh("git", "rev-parse", "HEAD")
    sh("git", "switch", "-q", "--detach")
    workflow = pin_refs.WORKFLOW
    workflow.write_text(pin_refs.pin(workflow.read_text(encoding="utf-8"), tag), encoding="utf-8", newline="\n")
    sh("git", "add", str(workflow))
    sh("git", "commit", "-q", "-m", f"Release {tag}: pin the workflow's actions to {tag}")
    sh("git", "tag", "-a", tag, "-m", f"IssuePilot {tag}\n\n{notes}")
    major_exists = bool(sh("git", "ls-remote", "--tags", "origin", f"refs/tags/{major}"))
    sh("git", "tag", "-fa", major, "-m", f"IssuePilot {major} (currently {tag})")
    release_commit = sh("git", "rev-parse", "HEAD")
    sh("git", "switch", "-q", *(["--detach", start] if re.fullmatch(r"[0-9a-f]{40}", start) else [start]))
    print(f"tagged {tag} and {major} at {release_commit[:12]}")

    if not push:
        print(f"review, then: python scripts/release.py {version} --push  (or push the tags yourself)")
        return 0
    sh("git", "push", "-q", "origin", f"refs/tags/{tag}")
    if major_exists:
        print(f"{major} exists on origin; move it yourself: git push origin {major} --force")
    else:
        sh("git", "push", "-q", "origin", f"refs/tags/{major}")
    sh("gh", "release", "create", tag, "--title", f"IssuePilot {tag}", "--notes", notes, "--verify-tag")
    print(f"released {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
