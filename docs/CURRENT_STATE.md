---
project_id: issuepilot
implementation_agent: claude-code
branch: main
as_of: eb1f864
active_milestone: M5
active_run: none
---
# Current state

Work is tracked as GitHub milestones and issues in brkakyldz/IssuePilot (public).

## Milestones

| ID | Status | Evidence | Commit |
|---|---|---|---|
| M1 Smoke test in the sandbox | PASS | sandbox run 38829549478 | 61d8610 |
| M2 Verified, hardened investigation | PASS | sandbox runs 38836764621, 38935153786 | 61d8610 |
| M3 Investigation quality | PASS | `docs/runs/2026-10-21_m3-investigation-quality.md` | bccdd8d |
| M4 Packaging and v1 | PASS | release v1.0.0; `docs/runs/2026-10-21_m3-to-m5.md` | 64a6cef |
| M5 Real use | IN_PROGRESS | installed on brkakyldz/ArchDrawer; first run on #31; v1.1.0 recognises feature requests (#34) | eb1f864 |

## What exists

- `.github/workflows/issuepilot.yml`: reusable workflow — a gate job (bots, skip
  labels), `actions/investigate` (Claude Code, read-only token, file tools confined to
  the checkout, the repository's own Claude configuration ignored, tool-call hook,
  spend cap) and `actions/publish` (no AI). Callers copy `templates/issuepilot.yml`.
  ADR 0001–0004.
- `prompts/investigate.md`, `schema/analysis.schema.json` (kinds: bug_analysis,
  needs_info, not_a_bug, feature_request).
- `src/issuepilot/`: verify, render (English and Turkish), failure, leaks, github,
  check.
- `evals/` with 18 cases, `tests/acceptance/holdout/` with 10 locked scenarios,
  `.github/workflows/backtest.yml`; CI runs pytest and actionlint.
- `security/`: capability probe, injection issue, end-to-end self-test.
- Releases v1.0.0 and v1.1.0. Sandbox `brkakyldz/issuepilot-sandbox` calls `@main`
  (and `@v1` by hand); brkakyldz/ArchDrawer calls `@v1`.

## Open gates

- Move the `v1` tag to v1.1.0: `git push origin refs/tags/v1 --force` from a checkout
  that has the new local `v1` (owner; forced tag pushes are not run by the agent).
- Two squash-merge commits made after the repository went public (50b690d, eb1f864)
  carry the account's e-mail address, and pre-rewrite commits stay reachable through
  `refs/pull/18–32/head`. Turning on "Keep my email addresses private" in the GitHub
  account stops new ones; removing the old ones needs a rewrite of public history or
  GitHub Support (owner).
- The owner's primary local checkout still has the pre-rewrite `main`; realign it with
  `git fetch origin` and `git reset --hard origin/main` (clean tree; owner).

## Blockers

- BLOCKED(external): #17 needs five real problem reports in ArchDrawer; every open issue
  there today is a feature spec or an epic.

## Next

Review IssuePilot's comments on the next problem reports opened in ArchDrawer (#17);
known weak spots are in the M3 report.
