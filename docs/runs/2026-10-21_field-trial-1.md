---
type: run-report
status: DONE
run: field-trial-1
runtime: claude-code
started: 2026-10-21
ended: 2026-10-21
base_sha: efbd63a
head_sha: 110c09a
---
# Run report — field trial 1

IssuePilot's investigation run on 20 real issues of well-known open-source projects.
Nothing was posted: each comment was rendered exactly as it would have been posted
and reviewed by a separate model inside the repository at the investigated commit.
Full per-case table, every problem the reviewers raised and per-case summaries:
[`2026-10-21_field-trial-1-reviews.md`](2026-10-21_field-trial-1-reviews.md).

## Setup

- Harness: `evals/field.py` (select, review, report) on top of the backtest workflow;
  cases in `evals/field/2026-10-21/`, rules in the module docstring.
- Repositories (`evals/field/repos.json`): rich, pydantic, pandas, black, pytest, hono,
  vite, svelte. rich had no issue that met the rules, so 7 repositories contributed.
- 10 closed issues: bug, fixed by a merged pull request touching 1-6 code files and at
  most 300 code lines, replayed at the commit before the merge. The reviewer saw the
  merged change.
- 10 open issues: bug, opened since 2026-05-21, no linked pull request, replayed at the
  default branch as it was when the issue was opened. Nobody knows the answer.
- Investigation: backtest run 39580359625, production limits (model sonnet, 60 turns,
  40 tool calls, $0.50 cap), English. The investigator sees only the issue title and
  body, as on a newly opened issue.
- Review: `claude -p --model opus`, read-only tools and git, prompt
  `evals/field/reviewer.md`, structured result (scores 0-3 on six dimensions, verdict,
  claims checked, problems with the IssuePilot component to change).

## Results

| | all | closed | open |
|---|---|---|---|
| helpful | 10 | 7 | 3 |
| partly helpful | 8 | 2 | 6 |
| not helpful | 2 | 1 | 1 |
| harmful | 0 | 0 | 0 |
| a maintainer would be glad of it | 14/20 | 8/10 | 6/10 |
| cause right / partly / wrong | 14 / 5 / 1 | 8 / 2 / 0 | 6 / 3 / 1 |
| mean diagnosis (0-3) | 2.50 | 2.70 | 2.30 |
| mean location | 2.30 | 2.70 | 1.90 |
| mean evidence | 2.35 | 2.60 | 2.10 |
| mean calibration | 2.35 | 2.40 | 2.30 |
| mean actionability | 2.05 | 2.20 | 1.90 |
| mean clarity | 2.40 | 2.40 | 2.40 |
| high confidence with calibration ≤ 1 | 0 | 0 | 0 |

- Every run produced an analysis. Mechanical location hit on closed issues 8/10, the
  fixed file 10/10.
- Median cost $0.088 (max $0.136), median 8.5 turns (max 13), median 28 s. Review cost
  $8.64 in total.
- Not helpful: pandas-71254 (blamed the wrong call in a native crash; did not map the
  reporter's traceback, from another release, onto that release's source) and
  svelte-18421 (a regression bisected to one pull request, answered with `needs_info`).

## What the reviews found

122 problems, 19 major. Recurring patterns, most frequent first:

1. **Restating the reporter.** In 8 of 20 issues the reporter had already diagnosed the
   cause (hono-5129, pandas-71277, pandas-71278, pydantic-13507, pydantic-13781,
   pydantic-13817, svelte-18374, vite-23781). The comment mostly repeats it and never
   says which of the reporter's claims it checked against the code; the useful delta
   (other callers, sibling sites, risks of the proposed fix) is thin or missing.
2. **Stopping early; checkable things left as assumptions.** Runs end after 5-13 turns
   with most of the tool budget unused, while "Not sure about" and "Assumptions" list
   things one read or grep would settle (black-4912, black-5122, pandas-67375,
   pandas-71278, pydantic-13471, pydantic-13781, pydantic-13817). Regression windows
   named in the issue are not checked with `git log` (black-5122, hono-5129, vite-22725).
3. **Fixes not checked against callers and entry paths.** Suggested fixes break another
   caller (vite-23781), another entry path (pydantic-13471), or rely on a mechanism the
   comment itself shows does not hold (svelte-18374); alternatives are offered that do
   nothing (pandas-67375, pandas-71277). Sibling sites with the same defect are missed
   (pandas-71278, pydantic-13817, pytest-12175, vite-23383, vite-23781).
4. **Negative claims without a successful search.** "Not in this checkout"
   (pydantic-14034, the code was in `pydantic-core/`), "Vite sets no tree-shaking
   options" after the grep failed (vite-22725), "Vite 7 has no native code"
   (vite-22918, taken from the issue). Failed tool calls are not retried.
5. **Tracebacks and versions.** A traceback from another release is not mapped to that
   release's source (pandas-71254), traceback frames are not tied to the cited code
   (pandas-69014), version claims are not checked against history.
6. **Duplicated text.** Cause vs Explanation and Suggestion vs Suggested fixes repeat
   each other in 8 comments.
7. **Primary location.** The "Where" link can point at control code rather than the
   code to change (pydantic-13507, pydantic-14034).
8. **Structured output.** The first `StructuredOutput` call failed to parse 22 times in
   20 runs: at the `evidence` array the model switches from JSON to tool-call markup
   (`<parameter name="path">`). Each failure costs a turn; no run lost its result.

Reviewer-proposed changes, by component, are in the reviews file.

## Assumptions and limits

- One reviewer model judges every case; its own claims about the code were not
  re-checked by a person. For closed issues the merged fix anchors it; for open issues
  it does not.
- 20 issues from 7 repositories, mostly Python and TypeScript; open issues come from
  four repositories only (the others had no unlinked open bug in the window).
- The investigator in a backtest has no issue tracker access (no related issues or
  pull requests) and no tags, unlike a production run.
