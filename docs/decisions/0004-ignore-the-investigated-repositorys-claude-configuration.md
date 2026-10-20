---
id: 0004
title: Ignore the investigated repository's Claude Code configuration
date: 2026-10-21
status: accepted
deciders: [berke]
supersedes: []
---

## Context

Claude Code loads project configuration from the directory it runs in:
`.claude/settings.json` (permissions, hooks), `.claude/settings.local.json`, and the MCP
servers in `.mcp.json`. In the investigate job that directory is the repository being
investigated. The first backtest on real repositories (run 39509333942) investigated
python-caldav/caldav, which ships a `UserPromptSubmit` hook: Claude Code ran the hook's
shell command inside the investigate job, the command failed, and the prompt was
blocked, so no analysis came out.

A hook is the repository's code running next to the OAuth token, and project settings
can widen permissions (`permissions.allow`) or enable project MCP servers. The scope
rule is that IssuePilot never executes the investigated repository's code, and ADR 0002
assumes the agent's limits come only from IssuePilot.

## Decision

The investigate action runs Claude Code with `--setting-sources user` and
`--strict-mcp-config`: only the settings IssuePilot writes (the action stores its
`settings` input in the user settings file) and the action's own MCP configuration
apply. Nothing under the repository's `.claude/` or `.mcp.json` is loaded.

## Rationale

- claude-code-action documents `--setting-sources user` for exactly this purpose ("to
  avoid in-repo configs", `base-action/src/parse-sdk-options.ts` at v1.0.255).
- The repository's CLAUDE.md and AGENTS.md stay readable as files; the prompt already
  tells the agent to read them, as data about the project.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Delete `.claude/` and `.mcp.json` from the checkout before the run | The evidence check runs on a fresh checkout, but the agent would then see a tree that differs from the commit it cites |
| `disableAllHooks` in our settings | Covers hooks only; project permissions and MCP servers would still load |
| Trust the owner's repository | Hooks may be written for a developer's machine (this one was) and fail or misbehave in CI; and the scope rule forbids running repository code |

## Consequences

- **Upside:** the agent's tools, permissions and hooks are IssuePilot's alone, whatever
  the repository contains. The backtest case `security-repo-claude-config-ignored`
  (a repository whose hooks block every prompt) guards it.
- **Cost:** project skills, commands and subagents the repository defines for Claude
  Code are not available to the investigation.
- **Cost to reverse:** low; two flags.
