---
type: run-report
status: DONE
run: field-trial-2
runtime: claude-code
started: 2026-10-21
ended: 2026-10-22
base_sha: dbab28c
head_sha: 5a95aae
---
# Run report — field trial 2: changes from trial 1, measured

The findings of [field trial 1](2026-10-21_field-trial-1.md) turned into changes to the
prompt, the tool-budget hook and the renderer, each measured on the same 20 issues with
the same reviewer setup. Final round in full:
[`2026-10-22_field-trial-2-reviews.md`](2026-10-22_field-trial-2-reviews.md).

## Rounds

| Round | Commit | Change |
|---|---|---|
| 1 | e6fde4a | baseline (trial 1) |
| — | 4e8b4a1 | prompt: check the reporter's diagnosis and add the delta, settle checkable assumptions, check fixes against callers, no unsearched negative claims, bisected regressions are bugs, one-call JSON. Run 39675243092 failed before Claude started: an apostrophe in a schema description ended the quoted `--json-schema` argument (fixed in 4192a22, guarded by a test) |
| 2 | 4192a22 | the above, run 39675893481 |
| 3 | e95eb69 | the first structured result is sent back once with a checklist (hook); the first suggested fix is not repeated |
| 4 | 5a95aae | renderer: no doubled labels, explanation steps as a list, sentence-end cuts, unverified items with lines; prompt: diff a reported version against the checkout, say when no code here is at fault. Run 39682870739 |

## Results

| | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| helpful | 10 | 13 | 14 | 13 |
| partly helpful | 8 | 7 | 6 | 7 |
| not helpful | 2 | 0 | 0 | 0 |
| harmful | 0 | 0 | 0 | 0 |
| a maintainer would be glad of it | 14/20 | 15/20 | 16/20 | 17/20 |
| cause right / partly / wrong / undetermined | 14/5/1/0 | 14/6/0/0 | 16/4/0/0 | 14/5/0/1 |
| mean diagnosis | 2.50 | 2.50 | 2.60 | 2.60 |
| mean location | 2.30 | 2.45 | 2.40 | 2.55 |
| mean evidence | 2.35 | 2.50 | 2.40 | 2.50 |
| mean calibration | 2.35 | 2.50 | 2.35 | 2.70 |
| mean actionability | 2.05 | 2.25 | 2.25 | 2.20 |
| mean clarity | 2.40 | 2.15 | 2.30 | 2.40 |
| major / minor problems | 18 / 84 | 17 / 79 | 11 / 97 | 12 / 86 |
| median cost / max (USD) | 0.088 / 0.136 | 0.111 / 0.168 | 0.150 / 0.220 | 0.133 / 0.252 |
| median turns / max | 8.5 / 13 | 9 / 13 | 11.5 / 19 | 11 / 20 |

- Round 4 on closed issues: 10/10 comments a maintainer would welcome, 8 helpful.
- Every round: every run produced an analysis, mechanical location hit 8/10 on closed
  issues, no high-confidence comment with poor calibration.
- Differences of one or two cases between rounds 3 and 4 are within what the reviewer
  itself varies; the trend from round 1 is the signal.
- Failed first `StructuredOutput` calls: 22 in round 1, 18 in round 2 after the prompt
  asked for JSON arrays. It is the model writing tool-call markup inside the `evidence`
  array; each costs a turn and no result was lost.

## Regression checks on the final commit

| Suite | Run | Result | Before (M5 report) |
|---|---|---|---|
| `tests/acceptance/holdout` (10, held out) | 39684681772 | 10/10, location hit 100%, median $0.095 | 10/10 |
| `evals/cases` (23) | 39683712521 | 18/23, location hit 87.5%, no overconfident, median $0.113 | 18/23, 87.5%, median $0.087 |

The five `evals/cases` failures are the cases that already varied in M3 and M5
(battery-notes, cattrs, densify) plus caldav (`needs_info` instead of a bug) and
minibill (a `must_mention` miss). Median cost per run rose about 30% and stays
within M3-A7.

## What is still weak

From the round 4 reviews (12 major problems):

- Searches limited to one package still miss vendored code in a monorepo
  (pydantic-13471 says pydantic-core is not in the checkout). The checklist names
  `git show HEAD:` but the investigator does not always run it. Next: put the
  repository's top-level layout into the prompt so the investigator never has to ask.
- Regressions: the named last-good release is not diffed against the first bad one
  (black-5122), and a line that did not change is blamed for a regression.
- A suggested fix removes the wrong one of two code paths, or touches a shared path,
  without checking every entry point (pydantic-13471, black-5122).
- svelte playground links (`#H4sI…`, gzip in base64url) are not decoded, so the
  reproduction is never read (svelte-18421).
- An evidence quote whose first line lost its indentation renders unevenly; the
  renderer could show the verified source lines instead of the model's copy.

## Assumptions and limits

As in trial 1: one reviewer model, its claims about the code not re-checked by a
person; 20 issues; open issues from four repositories. The same 20 issues were used to
make and to measure the changes, so the gain is an upper bound for unseen issues; the
held-out and `evals/cases` suites are the check that nothing else got worse.
