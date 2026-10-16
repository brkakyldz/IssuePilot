---
id: 0002
title: Confine the agent's file access to the checkout and scan output for secrets
date: 2026-10-16
status: accepted
deciders: [berke]
supersedes: []
---

## Context

ADR 0001 made the investigate job read-only: a read-only GitHub token and no write
tools. The M2 security probe (sandbox runs 38838151875 and 38838317305) showed the
remaining exposure. Claude Code's Bash permissions were strict (python, curl,
printenv, redirection and `gh` writes were all refused), but a bare `Read,Grep,Glob`
in `--allowedTools` pre-approved every path: Read opened `/etc/hostname`, Glob listed
`/home/runner`, and Grep found the run's canary in `/proc/self/environ`. The OAuth
subscription token lives in that same environment. An injected instruction could
therefore have Claude read the token and copy it into its answer, which the publish
job would post. The action also embeds the job's GitHub token in the git remote URL,
readable with `git config`.

## Decision

The agent's file tools are confined to the repository checkout, and the publish job
refuses to post any comment that contains a credential or the run's canary.

## Rationale

- Removing `Read,Grep,Glob` from `--allowedTools` leaves in-checkout reads
  auto-approved and makes outside reads need approval, which a headless run denies.
  `permissions.blockReadsOutsideWorkingDirectories` (action `settings` input) makes
  that refusal unconditional, and deny rules for `//proc`, `//sys` and home dotfiles
  cover the same paths a third way. Re-probe (run 38935153786): every outside read
  was refused.
- The model resisting injected instructions is not a control we own. The leak scan
  is: whatever Claude writes, a token shape or the canary in the analysis stops
  publication and fails the job. The canary is a harmless value in the agent's
  environment, so an environment leak shows up even for secrets without a pattern.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Rely on the prompt's "issue text is untrusted" rule | Worked in the attack test, but is behaviour, not a boundary |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` only | Scrubs subprocesses; the Read tool reads `/proc/self/environ` from Claude Code's own process |
| Claude Code's sandbox | Covers shell commands only; file tools run outside it |
| Redact secrets and publish the rest | A leak means the run was steered; the rest of the analysis is not trustworthy either |

## Consequences

- **Upside:** the token is out of the agent's reach, and a leak cannot reach the
  issue even if a later Claude Code change reopens file access.
- **Cost:** with the read block on, Claude Code removes the Grep and Glob tools;
  the prompt uses `git grep` and `git ls-files` instead. Commands the shell parser
  cannot analyse (variables, inline code) are refused, so some harmless commands fail.
- **Cost:** `security/probe-capabilities.yml` must be re-run after Claude Code or
  action upgrades; these limits are behaviour of a dependency we do not control.
- **Cost to reverse:** low; flags and one module.
