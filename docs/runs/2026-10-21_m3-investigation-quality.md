# M3 run: investigation quality

2026-10-21. Backtests of the investigate action on cases with known answers
(`docs/contracts/backtest.md`), cause grades by a separate `claude -p --model opus`
judge. All runs in brkakyldz/IssuePilot Actions, model `sonnet`, language English.

## Suites

- **Held-out** `tests/acceptance/holdout/`: 10 fixture scenarios written by a separate
  Claude Code process (Sonnet) from the intent and contracts only, landed by that
  process (#24).
- **Real** `evals/cases/`: 14 closed issues from small, permissively licensed
  repositories (9 bugs, 3 too vague, 2 intended behaviour) replayed at the commit before
  their fix, plus the sandbox's planted regression and, from #27 on, a fixture whose
  Claude Code hooks block every prompt.

## Results

| Prompt / harness | Held-out | Real | Location hit (real bugs) | Overconfident | Median cost |
|---|---|---|---|---|---|
| M2 prompt (runs 39507541148, 39509305739) | 8/10 | 6/15 | 70% | 0 | $0.055 / $0.073 |
| docs as evidence, vague → needs_info (#25; runs 39508074629, 39509333942) | 10/10 | 11/15 | 80% | 0 | $0.066 / $0.090 |
| repo config ignored, tool budget, result fallback (#27; 39511948746, 39511259064) | 10/10 | 12/16 | 82% | 0 | $0.055 / $0.076 |
| spend cap, cause tied to observation (#28; 39515633451, 39515672719) | **10/10** | **13/16** | **82%** | **0** | $0.052 / $0.077 |

Acceptance run on main after #27 with `verify-holdout` (run 39513332769): VERIFIED,
10/10 scenarios. The planted rounding regression cited the contradicting README line as
verified evidence in 3/3 runs (#6), against 0/3 in M2.

## M3 bar (#7)

| Bar | Result |
|---|---|
| Location overlap on ≥ 70% of bug cases | held-out 100%, real 82% |
| No high-confidence analysis with a wrong cause | none in any run since #25 |
| `needs_info` cases never get an invented fix | 5/5 in the last run; densify varied (passed 3 of its last 4 runs) |
| Held-out scenarios pass | 10/10 |
| Median cost ≤ ~1.5× M2 ($0.08–0.14) | $0.052–0.077 |

## Failures that remain

- **battery-notes** (not_a_bug expected): the analysis traces the mechanism exactly
  (cause grade 2) but calls it a bug; the maintainer's "intended" is not written in the
  code or docs, so the checkout cannot settle it.
- **caldav** (bug): wrong cause at low or medium confidence; the fix is in a 1,200-line
  search module with several workaround paths.
- **cattrs** (bug): right cause (grade 2), evidence lines outside the changed hunks.

## Found on the way

- A repository's `.claude/settings.json` hook ran inside the investigate job (caldav,
  run 39509333942) → ADR 0004, `--setting-sources user --strict-mcp-config`.
- One case made 5529 empty Bash calls in 562 s for ~$3.40 under `--max-turns 30`
  (run 39509305739): max-turns counts API rounds, and calls with invalid input reach no
  hook → `--max-budget-usd` cap (default $0.50, verified in run 39515509895) plus a
  tool-call hook for valid-call loops.
- claude-code-action drops a schema-valid result when the turn count exceeds max-turns
  (anthropics/claude-code-action#1758, run 39511985945) → result taken from the
  transcript.

## Assumptions

- Expected locations are the hunks each fix changed, including diff context; a case
  passes the location check when a verified evidence item lies within 10 lines of one.
- The judge (Opus) sees only the expected cause and the analysis.
- Backtests give the agent no issue tracker: related issues and pull requests are not
  measured.

## Cost

About 170 investigations over the day, US$15.4 list-price equivalent of the
subscription quota in total, of which $3.40 was the single runaway run.
