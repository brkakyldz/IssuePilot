# Current state

## Milestones

Work is tracked as GitHub milestones and issues in brkakyldz/IssuePilot.

| | Milestone | State |
|---|---|---|
| M1 | Smoke test in the sandbox: issue → read-only Claude run → JSON → comment | done 2026-10-16 |
| M2 | Evidence verification, short comment, failure messages, single comment, security hardening | done 2026-10-16 |
| M3 | Investigation quality: prompt work and backtest evals on closed issues | done 2026-10-21 (`docs/runs/2026-10-21_m3-investigation-quality.md`) |
| M4 | Packaging as a reusable workflow, `docs/setup.md`, v1 release | v1.0.0 2026-10-21; setup doc checked on a fresh repository with M5 (#14) |
| M5 | Use on real projects | not started: install on ArchDrawer (#16), review five real analyses (#17) |

## What exists

- `.github/workflows/issuepilot.yml`: reusable workflow; `actions/investigate` (Claude
  Code, read-only token, file tools confined to the checkout, the repository's own
  Claude configuration ignored, tool-call hook and spend cap) and `actions/publish`
  (no Claude). Callers copy `templates/issuepilot.yml`. ADR 0001–0004.
- `prompts/investigate.md`, `schema/analysis.schema.json` (v2).
- `src/issuepilot/`: verify, render (English and Turkish labels), failure, leaks,
  github, check (verify without publishing).
- `evals/`: backtest harness and 16 cases; `tests/acceptance/holdout/`: 10 held-out
  scenarios (locked). `.github/workflows/backtest.yml` runs them; CI runs pytest and
  actionlint.
- `security/`: capability probe, injection issue, end-to-end self-test (leak scan,
  bad token).
- Sandbox `brkakyldz/issuepilot-sandbox` (private) calls the packaged workflow at
  `@main`, comments in Turkish; issue #5 is the self-test target.

## Measured

| What | Result |
|---|---|
| Held-out scenarios, current prompt | 10/10 (run 39515633451) |
| Real closed issues | 13/16, location hit 82%, no overconfident analysis (run 39515672719) |
| Cost per investigation | median $0.05–0.08 list-price equivalent, ~20 s; cap $0.50 |
| Security probe with the v1 flags | all reads outside the checkout refused, Glob/Grep absent, writes refused (sandbox run 39516767563) |
| Leak scan in a real run | blocked the canary, job failed (run 39504137493) |
| Invalid token | named sign-in failure (run 39504203614) |

## Open

- Known weak spots (M3 report): intended behaviour that is not written down is called a
  bug; large modules with several code paths (caldav) can yield a wrong cause at low or
  medium confidence; densify-like vague reports are not always `needs_info`.
- Upstream risk: anthropics/claude-code-action#1614, still open on 2026-10-21 (last
  report 2026-09-11, Claude Code 2.1.268), reports genuine 401s with valid setup tokens;
  some reporters' 401s were usage-limit 429s in disguise. Not our cause (ours was a
  pasted trailing newline, now stripped). A bad token now yields the named sign-in
  failure (sandbox run 39504203614), and `docs/setup.md` covers both upstream causes.
- Upstream: claude-code-action drops results whose turn count exceeds max-turns
  (#1758) and counts turns differently from the CLI (#1795); IssuePilot works around
  both.
