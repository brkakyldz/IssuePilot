# Changelog

All notable changes to IssuePilot. Versions follow [semantic versioning](https://semver.org/);
callers pinned to `@v1` receive every 1.x release.

## [Unreleased]

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
- Named failure messages (sign-in, usage limit, step limit, timeout, no result).
- Comment labels in English and Turkish (`language` input).
- `docs/setup.md`: installation, options, cost, security model, troubleshooting.
- Backtest harness (`evals/`, `.github/workflows/backtest.yml`) and the end-to-end
  self-test workflow (`security/self-test.yml`).
