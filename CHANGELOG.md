# Changelog

All notable changes to IssuePilot. Versions follow [semantic versioning](https://semver.org/);
callers pinned to `@v1` receive every 1.x release.

## [Unreleased]

## [1.3.0] - 2026-10-22

Measured on 20 real issues from pydantic, pandas, black, pytest, hono, vite and svelte
(field trial, `docs/runs/2026-10-21_field-trial-1.md`).

### Changed
- When the reporter has already explained the cause, the comment says whether the
  code confirms it and adds what they did not cover (other callers, sibling sites,
  risks of their fix) instead of restating it.
- The investigation checks before it writes: an exact error text across the whole
  repository, the whole function it blames, a traceback's own version, every caller of
  the code a fix changes, and assumptions one read would settle. The first result is
  sent back once with that checklist while tool budget remains.
- No claim that code is absent or external without a search that ran; a bisected
  regression is analysed from the culprit's diff instead of asking for more information.
- The comment no longer repeats the suggested fix below the Suggestion line, numbered
  explanation steps render as a list, and long lines are cut at a sentence end.

### Fixed
- An apostrophe in the analysis schema would have stopped Claude Code from starting;
  a test now guards the quoted `--json-schema` argument.

## [1.2.0] - 2026-10-21

### Fixed
- A cited quote that cuts a long line short (at least 12 characters, verbatim) now
  counts as found; such citations were set aside and lowered the stated confidence.

### Changed
- The comment footer says the analysis is read-only and the code was not run; the
  "not sure about" line names the specific open point instead.

## [1.1.0] - 2026-10-21

### Added
- Feature requests and plans are recognised. New issues opened by bots or carrying one
  of `skip_labels` (default `enhancement`, `feature`, `epic`) or `issuepilot:skip` are
  left alone before any AI runs. An unlabelled issue that asks for new behaviour is
  classified `feature_request` and gets no comment.

### Changed
- The analysis schema's `kind` gains `feature_request`.

## [1.0.0] - 2026-10-21

### Added
- Reusable workflow `.github/workflows/issuepilot.yml` with a ten-line caller,
  `templates/issuepilot.yml`; the prompt, schema and publish code travel with the
  workflow's own version (ADR 0003).
- Investigation of each newly opened issue by Claude Code on the repository owner's
  subscription, in a job with a read-only token, no write tools and file access
  confined to the checkout (ADR 0001, 0002).
- One comment per issue, updated in place on re-runs: cause, location, suggested fix
  and what could not be verified up front, everything else collapsed.
- Every cited file, line range and quote checked against a fresh checkout before
  posting; failed citations are disclosed and lower the stated confidence.
- Leak scan: an analysis containing a credential shape or the run's canary is not
  published and the job fails.
- Named failure messages (sign-in, usage limit, step limit, spending limit, timeout, no result).
- Comment labels in English and Turkish (`language` input).
- `docs/setup.md`: installation, options, cost, security model, troubleshooting.
- The investigated repository's own Claude Code configuration (hooks, permissions,
  MCP servers) is never loaded (ADR 0004).
- Every run is bounded: a spend cap (`max_cost_usd`, default US$0.50), a tool-call
  budget enforced by IssuePilot's own hook (`max_tool_calls`, default 40), the job
  timeout, and one run per issue at a time.
- Backtest harness (`evals/`, `.github/workflows/backtest.yml`), 16 cases and 10
  held-out scenarios: 10/10 held-out and 13/16 real closed issues at release
  (`docs/runs/2026-10-21_m3-investigation-quality.md`); the end-to-end self-test
  workflow (`security/self-test.yml`).
