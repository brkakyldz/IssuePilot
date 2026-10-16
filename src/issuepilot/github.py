"""The few GitHub API calls the publisher needs, made through the `gh` CLI.

`gh` is preinstalled on GitHub-hosted runners and reads GH_TOKEN from the
environment. The command runner is injectable so tests never touch the network.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from issuepilot.render import MARKER

BOT_LOGIN = "github-actions[bot]"

Runner = Callable[[list[str], str | None], "Completed"]


@dataclass(frozen=True)
class Completed:
    returncode: int
    stdout: str
    stderr: str


def run_gh(args: list[str], stdin: str | None = None) -> Completed:
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True, encoding="utf-8")
    return Completed(proc.returncode, proc.stdout, proc.stderr)


class GitHub:
    def __init__(self, repo: str, runner: Runner = run_gh):
        self.repo = repo
        self.runner = runner

    def _api(self, path: str, *args: str, stdin: str | None = None) -> Completed:
        return self.runner(["api", f"repos/{self.repo}/{path}", *args], stdin)

    def ref_exists(self, kind: str, ref: str) -> bool | None:
        """True or False when GitHub answers clearly, None when it could not tell."""
        ref = ref.strip()
        if kind in ("issue", "pull_request"):
            match = re.fullmatch(r"#?(\d+)", ref)
            path = f"issues/{match.group(1)}" if match else None
        else:
            path = f"commits/{ref}" if re.fullmatch(r"[0-9a-fA-F]{7,40}", ref) else None
        if path is None:
            return False
        result = self._api(path, "--silent")
        if result.returncode == 0:
            return True
        if "HTTP 404" in result.stderr or "HTTP 422" in result.stderr:
            return False
        return None

    def own_comment_id(self, issue: int) -> int | None:
        """The latest comment this workflow posted on the issue, if any."""
        query = f'.[] | select(.user.login == "{BOT_LOGIN}") | select(.body | startswith("{MARKER}")) | .id'
        result = self._api(f"issues/{issue}/comments", "--paginate", "--jq", query)
        if result.returncode != 0:
            raise RuntimeError(f"listing comments failed: {result.stderr.strip()}")
        ids = [int(line) for line in result.stdout.split()]
        return ids[-1] if ids else None

    def upsert_comment(self, issue: int, body: str) -> str:
        """Update IssuePilot's existing comment, or create one. Returns "updated" or "created"."""
        payload = json.dumps({"body": body})
        existing = self.own_comment_id(issue)
        if existing is None:
            result = self._api(f"issues/{issue}/comments", "--method", "POST", "--input", "-", "--silent", stdin=payload)
            action = "created"
        else:
            result = self._api(f"issues/comments/{existing}", "--method", "PATCH", "--input", "-", "--silent", stdin=payload)
            action = "updated"
        if result.returncode != 0:
            raise RuntimeError(f"posting the comment failed: {result.stderr.strip()}")
        return action
