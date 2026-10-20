# Setting up IssuePilot

IssuePilot reads each new issue in your repository, investigates it with Claude Code
on your own Claude subscription, and posts one comment: the likely cause, where it is,
a suggested fix, and what it could not verify. It runs entirely in GitHub Actions; there
is no server and nobody else sees your token.

## What it does and does not do

- It **reads** your code, its git history, and your issues and pull requests.
- It **writes** exactly one comment per issue, and updates that comment on a re-run.
- It never edits files, opens pull requests, runs your code, or installs anything.
- Every file and line it cites is checked against your repository before the comment
  is posted; a citation that does not hold up is moved out of the evidence and lowers
  the stated confidence.

## Requirements

- A Claude Pro or Max subscription, and Claude Code installed locally (only to create
  the token).
- GitHub Actions enabled for the repository.

While IssuePilot's repository is private, only repositories owned by the same account
can use it.

## Install

1. **Create a token.** On your machine run `claude setup-token` and copy the token it
   prints.
2. **Add it as a secret.** In the repository: *Settings → Secrets and variables →
   Actions → New repository secret*, name `CLAUDE_CODE_OAUTH_TOKEN`. Or from a terminal:

   ```bash
   gh secret set CLAUDE_CODE_OAUTH_TOKEN
   ```

   Paste the token when asked. Leading or trailing spaces and newlines are stripped.
3. **Add the workflow.** Copy [`templates/issuepilot.yml`](../templates/issuepilot.yml)
   to `.github/workflows/issuepilot.yml` in your repository and commit it.

That is all. The next issue someone opens gets a comment within a minute or two. To
try it on an existing issue: *Actions → IssuePilot → Run workflow*, enter the issue
number.

## Options

Set these under `with:` in your copy of the workflow.

| Input | Default | Meaning |
|---|---|---|
| `language` | `English` | Language of the analysis. Comment labels exist in English and Turkish; other languages get English labels around the analysis. |
| `model` | `sonnet` | Claude model alias or name. |
| `max_cost_usd` | `0.5` | Upper bound on one run's spend at list-price equivalent; Claude Code stops the run there. |
| `max_tool_calls` | `40` | Upper bound on the agent's tool calls; past it the agent must answer, and ten calls later it is stopped. |
| `max_turns` | `60` | Claude Code's own turn limit; keep it above `max_tool_calls`. |
| `issue_number` | the opened issue | Set by the manual trigger; leave it as in the template. |

Issues opened by bots are skipped. To skip one issue, add the label
`issuepilot:skip` before it is opened (for example from an issue template).

The template pins `@v1`, which follows compatible releases. Pin a full tag such as
`@v1.0.0`, or a commit SHA, if you want updates only when you change the line yourself.

## Cost

One investigation takes about a minute of runner time and uses your subscription's
quota like a short Claude Code session: in our measurements, the equivalent of
US$0.08–0.14 at API list prices with Sonnet. Each run is bounded by a 15-minute job
timeout, `max_cost_usd` (US$0.50 by default) and `max_tool_calls`, and only one run per issue happens at a time.

## How it keeps your repository safe

IssuePilot runs in two jobs. The first runs Claude Code with a GitHub token that can
only read, no tools that can write files or post anything, and file access limited to
the checked-out repository, so it cannot reach the runner's environment where your
Claude token lives. It returns its analysis as JSON. The second job runs no AI: it
checks every cited file, line and quote against a fresh checkout, and posts the
comment. Issue text is treated as untrusted data; an issue that tries to give the
agent instructions gets nothing to act with.

Before posting, the second job scans the whole analysis for anything shaped like a
credential, and for a harmless marker value that only exists in the first job's
environment. If either appears, nothing from the analysis is posted, the job fails,
and the comment says why. The details are in [ADR 0001](decisions/0001-official-claude-code-action-with-read-only-agent-and-separate-publisher.md)
and [ADR 0002](decisions/0002-confine-agent-file-access-and-scan-output-for-secrets.md).

## Troubleshooting

The comment names the cause when an investigation fails. The common ones:

**"Could not sign in to Claude"** (a 401). The secret is missing, mistyped or expired.
Run `claude setup-token` again and replace the secret. If the same token works locally
and still fails here, two known upstream causes exist: a subscription that has hit its
usage limit can be reported as a sign-in failure, and some accounts see genuine 401s
from GitHub-hosted runners
([anthropics/claude-code-action#1614](https://github.com/anthropics/claude-code-action/issues/1614)).
Wait for the limit to reset and re-run; if it persists, follow that issue.

**"The Claude subscription's usage limit was reached."** Re-run the workflow by hand
once the limit resets.

**"The investigation hit its step limit"**. The issue was too broad for the step limits.
Raise `max_tool_calls` (and `max_turns` above it), or narrow the issue and re-run.

**"Claude finished the investigation but did not return a result"**. Re-run once; if it
repeats, open the run log's transcript artifact and report it.

**"The analysis was not published: it contained a value that looks like a secret."**
Something in the issue may have steered the agent towards a credential. Read the
transcript artifact of the run, and rotate the Claude token if it could have been
exposed. Nothing from that analysis reached the issue.

**The workflow does not start.** Check that Actions are enabled, that the file is in
`.github/workflows/`, and that the issue was not opened by a bot or with the
`issuepilot:skip` label.
