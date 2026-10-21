"""Field trial: IssuePilot on real issues of well-known repositories, each resulting
comment reviewed by a separate model. Nothing is posted anywhere.

  python evals/field.py select --repos evals/field/repos.json --closed 10 --open 10 --seed 1 --out DIR
      pick issues by the rules below and write one case file per issue into DIR.
  python evals/backtest.py run --suite DIR --ref BRANCH --out RUN
      run the investigations: the backtest workflow, production limits.
  python evals/field.py review --suite DIR --results RUN/results --cache CACHE --out REVIEWS [--model opus]
      render each comment exactly as it would be posted and have a separate
      `claude -p` review it inside the repository at the investigated commit.
  python evals/field.py report --suite DIR --results RUN/results --reviews REVIEWS --out FILE
      one table per case plus every problem the reviewers found, by component.

Selection rules. Closed: labelled as a bug, closed as completed after closed_since,
closed by a merged pull request whose change touches 1-6 code files and at most 300
code lines (tests, docs and changelogs excluded); the case replays the commit before
the merge, and the reviewer sees the merged change. Open: labelled as a bug, opened
after open_since, no linked pull request; the case replays the default branch as it
was when the issue was opened, and nobody knows the answer. Both: a human author and
a body of at least 200 characters. Bug means a bug label or GitHub's Bug issue
type. Candidates are shuffled with the seed and taken round-robin across
repositories, at most --per-repo of each type from one repository.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "src"))

import backtest  # noqa: E402
from backtest import changed_ranges, gh, is_changelog, is_test_path, read_json  # noqa: E402

MIN_BODY = 200
MAX_CODE_FILES = 6
MAX_CODE_LINES = 300

SEARCH = """query($q: String!) {
  search(query: $q, type: ISSUE, first: 50) {
    nodes { ... on Issue {
      number title body createdAt url
      author { login __typename }
      closedByPullRequestsReferences(first: 5, includeClosedPrs: true) {
        nodes { number title merged mergeCommit { oid parents(first: 1) { nodes { oid } } } }
      }
    } }
  }
}"""


# --- selection ---------------------------------------------------------------


def search(repo: str, label: str, state: str, since: str) -> list[dict]:
    """Issues marked as bugs by label or by GitHub issue type, newest first."""
    when = f"closed:>{since} reason:completed" if state == "closed" else f"created:>{since}"
    found: dict[int, dict] = {}
    for marker in (f'label:"{label}"', "type:Bug"):
        query = f"repo:{repo} is:issue is:{state} {marker} {when} sort:created-desc"
        data = json.loads(gh("api", "graphql", "-f", f"query={SEARCH}", "-f", f"q={query}"))
        for node in data["data"]["search"]["nodes"]:
            if node:
                found.setdefault(node["number"], node)
    return sorted(found.values(), key=lambda n: n["number"], reverse=True)


def human_with_body(node: dict) -> bool:
    author = node.get("author") or {}
    return author.get("__typename") == "User" and len((node.get("body") or "").strip()) >= MIN_BODY


def is_code(f: dict) -> bool:
    path = f["filename"]
    docs = path.startswith("docs/") or Path(path).suffix.lower() in {".md", ".rst", ".txt"}
    return bool(f.get("patch")) and not (is_test_path(path) or is_changelog(path) or docs)


def closed_case(repo: str, node: dict) -> tuple[dict | None, str]:
    prs = [p for p in node["closedByPullRequestsReferences"]["nodes"] if p["merged"] and p.get("mergeCommit")]
    if not prs:
        return None, "not closed by a merged pull request"
    pr = prs[0]
    fix = pr["mergeCommit"]["oid"]
    pre = pr["mergeCommit"]["parents"]["nodes"][0]["oid"]
    compare = json.loads(gh("api", f"repos/{repo}/compare/{pre}...{fix}"))
    code = [f for f in compare.get("files", []) if is_code(f)]
    lines = sum(f["additions"] + f["deletions"] for f in code)
    if not 1 <= len(code) <= MAX_CODE_FILES or lines > MAX_CODE_LINES:
        return None, f"fix touches {len(code)} code files, {lines} lines"
    locations = [{"path": f["filename"], "start_line": a, "end_line": b}
                 for f in code if f["status"] != "added" for a, b in changed_ranges(f["patch"])]
    if not locations:
        return None, "fix only adds files"
    return {"source": {"repo": repo, "sha": pre}, "expected": {"kind": "bug_analysis", "locations": locations},
            "field": {"type": "closed", "fix_pr": pr["number"], "fix_pr_title": pr["title"], "fix_commit": fix}}, ""


def open_case(repo: str, node: dict, branch: str) -> tuple[dict | None, str]:
    if node["closedByPullRequestsReferences"]["nodes"]:
        return None, "has a linked pull request"
    commits = json.loads(gh("api", f"repos/{repo}/commits?sha={branch}&until={node['createdAt']}&per_page=1"))
    if not commits:
        return None, "no commit before the issue"
    return {"source": {"repo": repo, "sha": commits[0]["sha"]}, "expected": {"kind": backtest.UNKNOWN},
            "field": {"type": "open"}}, ""


def make_case(repo: dict, node: dict, built: dict, since: str) -> dict:
    field = built.pop("field")
    notes = {"url": node["url"], "created_at": node["createdAt"], "license": repo["license"],
             "why": f"field trial: {field['type']} {repo['bug_label']!r} issue since {since}", **field}
    return {
        "id": f"{repo['repo'].split('/')[1]}-{node['number']}",
        "issue": {"number": node["number"], "title": node["title"], "body": node["body"]},
        **built,
        "acceptance": [],
        "notes": json.dumps(notes, ensure_ascii=False),
    }


def select(args) -> int:
    config = json.loads(Path(args.repos).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = {"closed": args.closed, "open": args.open}
    picked: list[dict] = []
    for state, count in wanted.items():
        since = config[f"{state}_since"]
        pools = {}
        for repo in config["repos"]:
            nodes = [n for n in search(repo["repo"], repo["bug_label"], state, since) if human_with_body(n)]
            random.Random(f"{args.seed}:{state}:{repo['repo']}").shuffle(nodes)
            pools[repo["repo"]] = nodes
            print(f"{state:6} {repo['repo']:24} {len(nodes)} candidates", file=sys.stderr)
        branches = {}
        taken, per_repo = 0, {r["repo"]: 0 for r in config["repos"]}
        while taken < count and any(pools[r] for r in pools if per_repo[r] < args.per_repo):
            for repo in config["repos"]:
                if taken >= count:
                    break
                if per_repo[repo["repo"]] >= args.per_repo:
                    continue
                pool = pools[repo["repo"]]
                while pool:
                    node = pool.pop(0)
                    if state == "closed":
                        built, why = closed_case(repo["repo"], node)
                    else:
                        if repo["repo"] not in branches:
                            branches[repo["repo"]] = json.loads(gh("api", f"repos/{repo['repo']}"))["default_branch"]
                        built, why = open_case(repo["repo"], node, branches[repo["repo"]])
                    if built:
                        picked.append(make_case(repo, node, built, since))
                        taken += 1
                        per_repo[repo["repo"]] += 1
                        break
                    print(f"  skip {repo['repo']}#{node['number']}: {why}", file=sys.stderr)
    for case in picked:
        problems = backtest.validate_case(case)
        if problems:
            raise ValueError(f"{case['id']}: {problems}")
        (out / f"{case['id']}.json").write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{case['id']:28} {json.loads(case['notes'])['type']:6} {case['notes'] and json.loads(case['notes'])['url']}")
    return 0


# --- review ------------------------------------------------------------------


DIMENSIONS = ["diagnosis", "location", "evidence", "calibration", "actionability", "clarity"]
CATEGORIES = ["wrong_cause", "wrong_kind", "missed_location", "invented_code", "unsupported_claim", "overconfident",
              "underconfident", "weak_fix", "missing_questions", "ignored_issue_detail", "too_long", "unclear",
              "budget", "process", "rendering", "other"]
COMPONENTS = ["prompt", "verify", "schema", "render", "budget", "gate", "other"]
VERDICTS = ["helpful", "partly_helpful", "not_helpful", "harmful"]

_str = {"type": "string"}
REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["actual_cause", "cause_matches", "scores", "verdict", "would_post", "claims", "problems",
                 "strengths", "summary"],
    "properties": {
        "actual_cause": _str,
        "cause_matches": {"type": "string", "enum": ["yes", "partly", "no", "undetermined"]},
        "scores": {"type": "object", "additionalProperties": False, "required": DIMENSIONS,
                   "properties": {d: {"type": "integer", "enum": [0, 1, 2, 3]} for d in DIMENSIONS}},
        "verdict": {"type": "string", "enum": VERDICTS},
        "would_post": {"type": "boolean"},
        "claims": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["claim", "status", "note"],
            "properties": {"claim": _str, "status": {"type": "string", "enum": ["correct", "wrong", "unverifiable"]},
                           "note": _str}}},
        "problems": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["category", "severity", "component", "what_happened", "change"],
            "properties": {"category": {"type": "string", "enum": CATEGORIES},
                           "severity": {"type": "string", "enum": ["major", "minor"]},
                           "component": {"type": "string", "enum": COMPONENTS},
                           "what_happened": _str, "change": _str}}},
        "strengths": {"type": "array", "items": _str},
        "summary": _str,
    },
}

REVIEW_TOOLS = "Read,Grep,Glob,Bash(git log:*),Bash(git show:*),Bash(git blame:*),Bash(git grep:*),Bash(git diff:*)"
MAX_FIX_CHARS = 40_000
MAX_TRACE_LINES = 120


def git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def checkout(cache: Path, repo: str, case_id: str, shas: list[str]) -> tuple[Path, Path]:
    """A blobless bare clone per repository and one worktree per case at shas[0]."""
    bare = cache / (repo.replace("/", "__") + ".git")
    if not bare.exists():
        git("clone", "-q", "--bare", "--filter=blob:none", f"https://github.com/{repo}", str(bare))
        git("--git-dir", str(bare), "config", "core.autocrlf", "false")
        git("--git-dir", str(bare), "config", "core.longpaths", "true")
    for sha in shas:
        if git("--git-dir", str(bare), "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode:
            git("--git-dir", str(bare), "fetch", "-q", "origin", sha)
    tree = cache / "wt" / case_id
    if not tree.exists():
        git("--git-dir", str(bare), "worktree", "add", "-q", "--detach", str(tree), shas[0])
    return bare, tree


def tool_trace(transcript) -> list[str]:
    lines: list[str] = []
    errors: dict[str, bool] = {}
    if not isinstance(transcript, list):
        return lines
    for message in transcript:
        if not isinstance(message, dict) or message.get("type") != "user":
            continue
        for block in (message.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                errors[block.get("tool_use_id")] = bool(block.get("is_error"))
    for message in transcript:
        if not isinstance(message, dict) or message.get("type") != "assistant":
            continue
        for block in (message.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                args = json.dumps(block.get("input"), ensure_ascii=False)
                mark = " [refused or failed]" if errors.get(block.get("id")) else ""
                lines.append(f"{len(lines) + 1}. {block.get('name')} {args[:160]}{mark}")
    if len(lines) > MAX_TRACE_LINES:
        lines = lines[:MAX_TRACE_LINES] + [f"... {len(lines) - MAX_TRACE_LINES} more calls"]
    return lines


def comment_for(case: dict, folder: Path, tree: Path) -> str:
    from issuepilot.check import local_ref_exists
    from issuepilot.failure import classify
    from issuepilot.render import render_analysis, render_failure
    from issuepilot.verify import verify

    analysis, metrics = read_json(folder / "analysis.json"), read_json(folder / "metrics.json")
    sha, run_url = case["source"]["sha"], "https://github.com/brkakyldz/IssuePilot/actions"
    if analysis is None:
        return render_failure(classify("failure", metrics), sha, run_url, metrics)
    if analysis.get("kind") == "feature_request":
        return ""
    return render_analysis(verify(analysis, tree, local_ref_exists(tree)), case["source"]["repo"], sha, run_url, metrics)


def check_summary(checked: dict | None) -> str:
    if not checked or not checked.get("analysis"):
        return "No analysis was produced."
    lines = [f"confidence: {checked.get('original_confidence')} as written, {checked['analysis']['confidence']} after the check"
             + (f" ({checked['confidence_note']})" if checked.get("confidence_note") else "")]
    for e in checked.get("evidence", []):
        item = e["item"]
        lines.append(f"- {e['status']}: {item['path']}:{item['start_line']}-{item['end_line']}")
    for u in checked.get("unverified", []):
        item = u.get("item") or {}
        lines.append(f"- unverified: {item.get('path')}:{item.get('start_line')}-{item.get('end_line')} ({u.get('reason')})")
    if checked.get("dropped_related"):
        lines.append(f"- references dropped: {checked['dropped_related']}")
    return "\n".join(lines)


def run_summary(folder: Path) -> str:
    m = read_json(folder / "metrics.json") or {}
    head = (f"turns: {m.get('num_turns')}, list-price equivalent USD: {m.get('total_cost_usd')}, "
            f"seconds: {round(m['duration_ms'] / 1000) if m.get('duration_ms') else None}, end: {m.get('subtype')}")
    try:
        transcript = json.loads((folder / "transcript.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        transcript = None
    trace = tool_trace(transcript)
    return head + "\n" + ("\n".join(trace) if trace else "(no tool trace available)")


def review_prompt(case: dict, folder: Path, tree: Path, bare: Path) -> str:
    notes = json.loads(case.get("notes") or "{}")
    closed = notes.get("type") == "closed"
    comment = comment_for(case, folder, tree)
    fix = ""
    if closed:
        diff = git("--git-dir", str(bare), "diff", case["source"]["sha"], notes["fix_commit"]).stdout
        if len(diff) > MAX_FIX_CHARS:
            diff = diff[:MAX_FIX_CHARS] + "\n... (diff truncated)"
        fix = (f"BEGIN FIX (the change that later fixed this issue: pull request #{notes['fix_pr']}, "
               f"\"{notes['fix_pr_title']}\"; IssuePilot never saw it)\n{diff}\nEND FIX")
    values = {
        "CASE_TYPE": "closed - the issue was later fixed" if closed else "open - nobody has confirmed the cause yet",
        "GROUND_TRUTH_NOTE": ("The FIX section shows the change that actually fixed the issue. Treat it as the "
                              "reference for cause and location, but it may also contain unrelated changes."
                              if closed else "There is no reference answer: establish the cause from the code yourself."),
        "ISSUE": backtest.issue_markdown(case),
        "COMMENT": comment if comment else "(no comment: IssuePilot classified this as a feature request)",
        "CHECK": check_summary(read_json(folder / "checked.json")),
        "RUN": run_summary(folder),
        "FIX": fix,
        "FIX_HINT": " and the FIX section" if closed else "",
    }
    text = (ROOT / "evals" / "field" / "reviewer.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def review_one(case: dict, args) -> str:
    out = Path(args.out)
    target = out / f"{case['id']}.json"
    if target.exists():
        return f"{case['id']}: already reviewed"
    notes = json.loads(case.get("notes") or "{}")
    shas = [case["source"]["sha"]] + ([notes["fix_commit"]] if notes.get("fix_commit") else [])
    bare, tree = checkout(Path(args.cache), case["source"]["repo"], case["id"], shas)
    folder = Path(args.results) / f"result-{case['id']}"
    prompt = review_prompt(case, folder, tree, bare)
    (out / f"{case['id']}.prompt.md").write_text(prompt, encoding="utf-8")
    result = subprocess.run(
        ["claude", "-p", "--model", args.model, "--output-format", "json", "--json-schema", json.dumps(REVIEW_SCHEMA),
         "--setting-sources", "user", "--strict-mcp-config", "--no-session-persistence",
         "--allowedTools", REVIEW_TOOLS, "--disallowedTools", "Edit,Write,NotebookEdit,WebFetch,WebSearch,Task",
         "--max-turns", "80", "--max-budget-usd", str(args.max_cost)],
        input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=tree, timeout=1800,
    )
    (out / f"{case['id']}.raw.json").write_text(result.stdout or result.stderr, encoding="utf-8")
    try:
        envelope = json.loads(result.stdout)
        value = envelope.get("structured_output") or json.loads(envelope.get("result") or "{}")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return f"{case['id']}: review failed: {(result.stderr or result.stdout)[:200]}"
    if not isinstance(value, dict) or "verdict" not in value:
        return f"{case['id']}: review returned no verdict"
    value["_cost_usd"] = envelope.get("total_cost_usd")
    target.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"{case['id']}: {value['verdict']}"


def review(args) -> int:
    cases = backtest.load_cases(Path(args.suite), backtest.split_ids(args.ids))
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.cache) / "wt").mkdir(parents=True, exist_ok=True)
    # Clone each repository once before the parallel part.
    for repo in sorted({c["source"]["repo"] for c in cases}):
        first = next(c for c in cases if c["source"]["repo"] == repo)
        checkout(Path(args.cache), repo, first["id"], [first["source"]["sha"]])
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for line in pool.map(lambda c: review_one(c, args), cases):
            print(line, flush=True)
    return 0


# --- report ------------------------------------------------------------------


def report(args) -> int:
    cases = backtest.load_cases(Path(args.suite))
    results, reviews = Path(args.results), Path(args.reviews)
    rows, problems = [], []
    for case in cases:
        notes = json.loads(case.get("notes") or "{}")
        folder = results / f"result-{case['id']}"
        scored = backtest.score_case(case, read_json(folder / "checked.json"), read_json(folder / "metrics.json"))
        rev = read_json(reviews / f"{case['id']}.json")
        rows.append((case, notes, scored, rev))
        for p in (rev or {}).get("problems", []):
            problems.append({**p, "case": case["id"]})

    out = ["| case | type | kind | confidence | evidence ok/unverified | location | cause matches | verdict | post | "
           + " | ".join(DIMENSIONS) + " | turns | $ |", "|" + "---|" * (12 + len(DIMENSIONS) - 2)]
    for case, notes, s, rev in rows:
        m, sc = s["metrics"], (rev or {}).get("scores", {})
        conf = s.get("confidence") or ""
        if s.get("original_confidence") and s.get("original_confidence") != conf:
            conf = f"{s['original_confidence']}→{conf}"
        loc = "" if "location" not in s["checks"] else ("hit" if s["checks"]["location"] else "miss")
        out.append(
            f"| [{case['id']}]({notes.get('url')}) | {notes.get('type')} | {s.get('kind') or s.get('error')} | {conf} | "
            f"{s.get('evidence_verified', '')}/{s.get('evidence_unverified', '')} | {loc} | "
            f"{(rev or {}).get('cause_matches', 'no review')} | {(rev or {}).get('verdict', '')} | "
            f"{'yes' if (rev or {}).get('would_post') else 'no' if rev else ''} | "
            + " | ".join(str(sc.get(d, "")) for d in DIMENSIONS)
            + f" | {m.get('num_turns', '')} | {m.get('total_cost_usd', '')} |"
        )

    reviewed = [r for r in rows if r[3]]
    agg = ["", "| summary | all | closed | open |", "|---|---|---|---|"]

    def stat(name, fn):
        parts = [fn([r for r in reviewed if t is None or r[1].get("type") == t]) for t in (None, "closed", "open")]
        agg.append(f"| {name} | " + " | ".join(parts) + " |")

    stat("reviewed", lambda rs: str(len(rs)))
    for v in VERDICTS:
        stat(v, lambda rs, v=v: str(sum(r[3]["verdict"] == v for r in rs)))
    stat("would post", lambda rs: f"{sum(r[3]['would_post'] for r in rs)}/{len(rs)}")
    for c in ["yes", "partly", "no", "undetermined"]:
        stat(f"cause {c}", lambda rs, c=c: str(sum(r[3]["cause_matches"] == c for r in rs)))
    for d in DIMENSIONS:
        stat(f"mean {d}", lambda rs, d=d: f"{statistics.mean(r[3]['scores'][d] for r in rs):.2f}" if rs else "")
    stat("high confidence, calibration ≤ 1",
         lambda rs: str(sum(r[2].get("confidence") == "high" and r[3]["scores"]["calibration"] <= 1 for r in rs)))
    closed_loc = [r for r in rows if "location" in r[2]["checks"]]
    agg.append(f"| location hit (closed, mechanical) | {sum(r[2]['checks']['location'] for r in closed_loc)}/{len(closed_loc)} | | |")
    costs = [r[2]["metrics"]["total_cost_usd"] for r in rows if r[2]["metrics"].get("total_cost_usd") is not None]
    turns = [r[2]["metrics"]["num_turns"] for r in rows if r[2]["metrics"].get("num_turns") is not None]
    if costs:
        agg.append(f"| median cost / max | {statistics.median(costs):.3f} / {max(costs):.3f} | | |")
    if turns:
        agg.append(f"| median turns / max | {statistics.median(turns)} / {max(turns)} | | |")
    review_costs = [r[3].get("_cost_usd") for r in reviewed if r[3].get("_cost_usd") is not None]
    if review_costs:
        agg.append(f"| review cost total | {sum(review_costs):.2f} | | |")

    counts: dict[tuple[str, str], int] = {}
    for p in problems:
        counts[(p["category"], p["severity"])] = counts.get((p["category"], p["severity"]), 0) + 1
    cat = ["", "| problem category | major | minor |", "|---|---|---|"]
    for c in CATEGORIES:
        if counts.get((c, "major")) or counts.get((c, "minor")):
            cat.append(f"| {c} | {counts.get((c, 'major'), 0)} | {counts.get((c, 'minor'), 0)} |")

    by_component = []
    for comp in COMPONENTS:
        items = [p for p in problems if p["component"] == comp]
        if not items:
            continue
        by_component += ["", f"### {comp} ({len(items)})", ""]
        for p in sorted(items, key=lambda p: (p["severity"] != "major", p["category"])):
            by_component.append(f"- **{p['case']}** ({p['severity']}, {p['category']}): {p['what_happened']} "
                                f"→ *{p['change']}*")

    summaries = ["", "## Per-case summaries", ""]
    for case, _, _, rev in rows:
        if rev:
            summaries.append(f"- **{case['id']}** ({rev['verdict']}): {rev['summary']}")

    text = "\n".join(["## Results", ""] + out + agg + cat + ["", "## Problems by component"] + by_component + summaries) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("select")
    p.add_argument("--repos", required=True)
    p.add_argument("--closed", type=int, default=10)
    p.add_argument("--open", type=int, default=10)
    p.add_argument("--per-repo", type=int, default=2)
    p.add_argument("--seed", default="1")
    p.add_argument("--out", required=True)
    p.set_defaults(func=select)
    p = sub.add_parser("review")
    for flag in ["--suite", "--results", "--cache", "--out"]:
        p.add_argument(flag, required=True)
    p.add_argument("--ids")
    p.add_argument("--model", default="opus")
    p.add_argument("--max-cost", type=float, default=3.0)
    p.add_argument("--jobs", type=int, default=4)
    p.set_defaults(func=review)
    p = sub.add_parser("report")
    for flag in ["--suite", "--results", "--reviews", "--out"]:
        p.add_argument(flag, required=True)
    p.set_defaults(func=report)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
