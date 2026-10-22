---
project_id: issuepilot
implementation_agent: claude-code
branch: main
as_of: 5a95aae
active_milestone: none
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
| M5 Real use | PASS | `docs/runs/2026-10-21_m5-real-use.md` | ee4c20c |
| Field trial on real issues of well-known repositories | DONE | `docs/runs/2026-10-21_field-trial-1.md`, `docs/runs/2026-10-22_field-trial-2.md` | 5a95aae |

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
- `evals/` with 23 cases (5 are genuine ArchDrawer defects) and the field-trial harness
  (`evals/field.py`, 20 real issues in `evals/field/2026-10-21/`), `tests/acceptance/holdout/` with 10 locked scenarios,
  `.github/workflows/backtest.yml`; CI runs pytest and actionlint.
- `security/`: capability probe, injection issue, end-to-end self-test.
- `docs/assets/issuepilot-demo.mp4`: a 20-second English demo from real sandbox
  recordings (issue, run, comment, cited code); the README shows it as
  `issuepilot-demo.gif`, linked to the mp4.
- Releases v1.0.0 to v1.3.0. Sandbox `brkakyldz/issuepilot-sandbox` calls `@main`
  (and `@v1` by hand); brkakyldz/ArchDrawer and the ai-research-agent repository call `@v1`, which points at v1.3.0.
  v1.3.0 carries the field-trial changes.

## Open gates

- Two squash-merge commits made after the repository went public (50b690d, eb1f864)
  carry the account's e-mail address, and pre-rewrite commits stay reachable through
  `refs/pull/18–32/head`. Turning on "Keep my email addresses private" in the GitHub
  account stops new ones; removing the old ones needs a rewrite of public history or
  GitHub Support (owner).
- The owner's primary local checkout still has the pre-rewrite `main`; realign it with
  `git fetch origin` and `git reset --hard origin/main` (clean tree; owner).

## Blockers

None.

## Next

The weak spots listed in `docs/runs/2026-10-22_field-trial-2.md`, first the
repository's top-level layout in the prompt; measure with a new field-trial round on
fresh issues, not the 20 used to make the changes.
