# IssuePilot

IssuePilot is an AI agent that investigates newly opened GitHub issues and posts
evidence-based technical analysis and solution suggestions directly to the original
issue. It runs in GitHub Actions on the repository owner's own Claude subscription.

## Use it

Add one workflow file and one secret to your repository; every new issue then gets a
comment with the likely cause, where it is, a suggested fix and what IssuePilot could
not verify. See [docs/setup.md](docs/setup.md).

```yaml
jobs:
  issuepilot:
    uses: brkakyldz/IssuePilot/.github/workflows/issuepilot.yml@v1
    permissions: {contents: read, issues: write, pull-requests: read}
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

The full file is [templates/issuepilot.yml](templates/issuepilot.yml). How it stays
safe with untrusted issue text: [ADR 0001](docs/decisions/0001-official-claude-code-action-with-read-only-agent-and-separate-publisher.md),
[ADR 0002](docs/decisions/0002-confine-agent-file-access-and-scan-output-for-secrets.md).
How its quality is measured: [evals/](evals/README.md).

## Product intent

The product direction is GitHub Actions + Claude Code, with each user using their
own Claude subscription. The intended experience requires no separate server and
is straightforward for repository owners to adopt and use themselves.

The agent should go beyond the issue description: investigate source code, the
repository structure, past issues, pull requests, and other relevant context. It
should independently direct its research and explain its findings, supporting
evidence, proposed solutions, and remaining uncertainties in the issue comment.

The goal is a reliable, affordable agent useful in real software projects, with
clear limits and honest communication about what it could and could not verify.

## Initial scope

Investigate issues and suggest solutions. Automatic code changes, pull request
creation, and execution of repository code are outside the initial scope.

## Development approach

Build in small, explainable steps so Berke can follow and understand the project
from beginning to end without having to write all the code himself. Discuss each
step before implementation, then inspect its behavior together. Define what a
useful analysis looks like through concrete issue examples.
