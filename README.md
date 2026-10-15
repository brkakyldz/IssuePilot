# IssuePilot

IssuePilot is intended to be an autonomous AI agent that investigates newly opened
GitHub issues and posts evidence-based technical analysis and solution suggestions
directly to the original issue.

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
