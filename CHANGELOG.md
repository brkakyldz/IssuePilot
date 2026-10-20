# Changelog

All notable changes to IssuePilot. Versions follow [semantic versioning](https://semver.org/);
callers pinned to `@v1` receive every 1.x release.

## [Unreleased]

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
