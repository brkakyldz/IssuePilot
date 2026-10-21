<p align="center">
  <img src="docs/assets/hero.jpg" alt="IssuePilot: every new issue gets one investigated comment, checked against your code before it is posted" width="100%">
</p>

<p align="center">
  <img alt="Release v1.0.0" src="https://img.shields.io/badge/release-v1.0.0-5D768B?style=flat-square&labelColor=2E3E4C">
  <img alt="Runs on GitHub Actions" src="https://img.shields.io/badge/runs_on-GitHub_Actions-476D9E?style=flat-square&labelColor=2E3E4C">
  <img alt="Claude Code, your own subscription" src="https://img.shields.io/badge/Claude_Code-your_subscription-C8B39B?style=flat-square&labelColor=2E3E4C">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-8AA0B2?style=flat-square&labelColor=2E3E4C">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#quality">Quality</a> ·
  <a href="docs/setup.md">Setup guide</a>
</p>

IssuePilot investigates every new GitHub issue in your repository and posts one
comment: the likely cause, where it is in the code, a suggested fix, and what it could
not verify. It runs Claude Code in GitHub Actions on your own Claude subscription. There
is no server, and every file, line and quote it cites is checked against your code
before anything is posted.

## What you get

<p align="center">
  <img src="docs/assets/comment-example.png" alt="An IssuePilot comment on pytest-dev/pyfakefs#1304: the cause (FakeFileWrapper.seek returns None), a permalink to the lines, a suggested fix, what it is not sure about, and collapsed details" width="100%">
</p>

The comment above is IssuePilot's real output for
[pytest-dev/pyfakefs#1304](https://github.com/pytest-dev/pyfakefs/issues/1304), replayed
at the commit before the fix during the v1.0.0 backtest. The short part answers the
reporter; evidence with quoted lines, suggested fixes, verification steps and
assumptions are collapsed below it. Runs that fail post a plain reason instead, such as
an expired token.

## Quick start

1. Create a token on your machine: `claude setup-token` (Claude Pro or Max).
2. Add it to your repository as the Actions secret `CLAUDE_CODE_OAUTH_TOKEN`:
   `gh secret set CLAUDE_CODE_OAUTH_TOKEN`.
3. Copy [`templates/issuepilot.yml`](templates/issuepilot.yml) to
   `.github/workflows/issuepilot.yml`:

```yaml
on:
  issues:
    types: [opened]
jobs:
  issuepilot:
    uses: brkakyldz/IssuePilot/.github/workflows/issuepilot.yml@v1
    permissions: {contents: read, issues: write, pull-requests: read}
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

The next issue gets a comment within a minute or two. Options (language, model, limits),
cost and troubleshooting are in [docs/setup.md](docs/setup.md).

## How it works

![IssuePilot architecture: a read-only Claude Code job returns JSON; a second job without AI verifies it, scans it for secrets and posts one comment](docs/assets/architecture-coast.png)

1. A new issue starts the **investigate** job. Claude Code reads the issue as data,
   explores the repository with read-only tools (`git grep`, `git log`, `git blame`,
   `gh issue view`, ...) and returns its analysis as JSON that must match
   [`schema/analysis.schema.json`](schema/analysis.schema.json). The prompt is
   [`prompts/investigate.md`](prompts/investigate.md).
2. That job holds a GitHub token that can only read, gets no tool that writes, and can
   open files only inside the checkout. Your repository's own Claude Code settings,
   hooks and MCP servers are not loaded. A spend cap (US$0.50 by default) and a
   tool-call budget bound every run.
3. The **publish** job runs no AI. On a fresh checkout it checks every cited path, line
   range and quote, corrects line numbers that moved, sets aside citations that do not
   hold, and lowers the stated confidence when evidence fails.
4. It scans the whole analysis for credential shapes and for a marker value that only
   exists in the investigate job's environment; a match blocks publication.
5. It renders a short comment with the details collapsed, and creates or updates
   IssuePilot's one comment on the issue.

The design decisions, with the attacks and failures that shaped them, are in
[`docs/decisions/`](docs/decisions/).

## Quality

IssuePilot is measured, not just tried. [`evals/`](evals/README.md) replays issues
whose right answer is known: closed issues from real repositories at the commit before
their fix, and ten held-out scenarios written by a separate model that never saw the
implementation ([`tests/acceptance/holdout/`](tests/acceptance/holdout/)). At v1.0.0:

| Measure | Result |
|---|---|
| Held-out scenarios passed | 10 / 10 |
| Real cases passed | 13 / 16 |
| Real bugs where it pointed at the code the fix changed | 82% |
| Wrong causes stated with high confidence | 0 |
| Median run | about 20 s, about US$0.08 of list-price equivalent quota |

Details: [docs/runs/2026-10-21_m3-investigation-quality.md](docs/runs/2026-10-21_m3-investigation-quality.md).

## Scope

IssuePilot investigates and suggests. It never edits files, opens pull requests or
runs your repository's code.

## Development

```bash
python -m pip install pytest pyyaml
python -m pytest
```

The publish step uses only the Python standard library. CI runs the tests and
actionlint. Backtests run in this repository's Actions:
`python evals/backtest.py run --suite evals/cases --ref <branch>`.
[`AGENTS.md`](AGENTS.md) holds the rules every change follows,
[`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) where the project stands, and
[`CHANGELOG.md`](CHANGELOG.md) what each release brought.

## License

[MIT](LICENSE)
