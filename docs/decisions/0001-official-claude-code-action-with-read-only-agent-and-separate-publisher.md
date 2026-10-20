---
id: 0001
title: Official Claude Code action on the user's subscription, read-only agent, separate publisher
date: 2026-10-16
status: accepted
deciders: [berke]
supersedes: []
---

## Context

IssuePilot investigates newly opened GitHub issues and posts an evidence-based
analysis as an issue comment. The first README draft assumed a custom Python agent
loop with bring-your-own API keys. Research on 2026-10-16
(`reports/research/2026-10-16_claude-code-actions-subscription.md`) found that the
official `anthropics/claude-code-action@v1` accepts a Claude Pro/Max subscription
token (`CLAUDE_CODE_OAUTH_TOKEN`), and that its `--json-schema` flag returns a
validated JSON result as the step output `structured_output`.

Constraints: no server of our own, each user runs it in their own repository with
their own subscription, and issue text is untrusted input that may carry injected
instructions.

## Decision

The investigation runs as unmodified Claude Code through the official action, in a
job whose GitHub token can only read, and it returns its analysis as JSON; a second
job with no Claude in it checks that JSON and writes the issue comment.

## Rationale

- Claude Code already has the tools an investigation needs (file reading, search,
  git, `gh`). Writing our own agent loop would rebuild them and move us onto API
  billing, which the product intent rules out.
- Running the official action with the user's own token keeps us on the documented
  side of the subscription terms: we distribute a workflow, we never hold anyone's
  credentials.
- Asking for JSON instead of letting Claude post the comment removes every write
  tool from the agent. An injected instruction in an issue then has nothing to act
  with. The JSON also lets deterministic code verify cited files and lines before
  anything is published, and keeps the comment format identical across runs.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Custom Python agent loop + Anthropic API keys | Rebuilds Claude Code's tools; API billing instead of the user's subscription |
| Official action posting the comment itself (tag mode, sticky comment) | Agent needs `issues: write`; no place to verify evidence before it is public |
| One job, agent and publisher together | GitHub token permissions are per job, so the agent would hold the write token |
| Hosted IssuePilot service / GitHub App | Needs a server and would hold users' subscription tokens, which the terms disallow |

## Consequences

- **Upside:** small attack surface, verifiable evidence, no server, per-user cost
  on the user's own subscription.
- **Cost:** two jobs per run (extra runner start-up, roughly half a minute), and
  the JSON schema becomes a contract every later change must respect.
- **Cost:** we depend on the official action's behaviour and release cadence.
- **Open, to be verified in M1:** that `--json-schema` works with the OAuth token on
  an `issues` event, that the action runs with a read-only `github_token`, and how
  long and how much quota one run takes.
- **Decided at packaging (M4), ADR 0003:** distribution as a reusable workflow over
  two composite actions that carry the prompt and scripts at their own ref.
- **Cost to reverse:** medium. The prompt and schema would survive a move to the
  Agent SDK; the workflow wiring would not.
