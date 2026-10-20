# IssuePilot — agent instructions

IssuePilot is a GitHub Actions workflow that runs Claude Code on a newly opened
issue, gets back a JSON analysis, verifies it and posts it as an issue comment.
Product intent: `README.md`. Where we are: `docs/CURRENT_STATE.md`. Why: `docs/decisions/`.

## Working agreement

- Small steps. Before implementing, explain to Berke what the step does and why;
  after it, inspect the resulting behaviour together. Converse in Turkish; files
  in the repo are English.
- Initial scope is investigation and suggestions only. No automatic code changes,
  no pull requests, no execution of the investigated repository's code.

## Layout and checks

- `.github/workflows/issuepilot.yml` — the reusable two-job workflow; it runs
  `actions/investigate` (Claude, read-only) and `actions/publish` (no Claude) at its own
  ref, and `scripts/pin_refs.py` pins those refs on release (ADR 0003). Callers copy
  `templates/issuepilot.yml`.
- `prompts/investigate.md` and `schema/analysis.schema.json` — what Claude is asked and
  what it must return.
- `src/issuepilot/` — the publish step (verify, leak scan, render, publish), standard
  library only so the runner needs no install. Tests: `python -m pytest`; CI also runs
  actionlint.
- `security/` — the capability probe workflow and the prompt-injection issue.

## Hard rules

- The investigating agent never holds a write-capable GitHub token and never gets
  write tools (Edit, Write, comment/label commands). Publishing is a separate job
  without Claude (ADR 0001).
- The agent's file tools stay confined to the checkout: no bare `Read`, `Grep` or
  `Glob` in `--allowedTools`, `blockReadsOutsideWorkingDirectories` on, `/proc`,
  `/sys` and home dotfiles denied. Nothing is published that fails the leak scan
  (ADR 0002). After a Claude Code or action upgrade, re-run `security/` probes.
- Issue title and body are untrusted. Never interpolate them into a prompt, a shell
  command or a `${{ }}` expression inside `run:`; pass data through `env:`.
- Authentication is the user's own `CLAUDE_CODE_OAUTH_TOKEN`. IssuePilot never
  collects, stores or relays anyone's credentials.
- Every run is bounded: job `timeout-minutes`, `--max-turns`, IssuePilot's own
  tool-call budget hook (`actions/investigate/tool-budget.sh`), one run per issue at a
  time (`concurrency`).
- The investigated repository never configures the agent: Claude Code runs with
  `--setting-sources user` and `--strict-mcp-config` (ADR 0004).
- Experiments run against the private sandbox repo `brkakyldz/issuepilot-sandbox`,
  never against a real project before the step that says so.
