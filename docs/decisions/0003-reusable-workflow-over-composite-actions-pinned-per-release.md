---
id: 0003
title: Distribute as a reusable workflow over two composite actions, pinned per release
date: 2026-10-21
status: accepted
deciders: [berke]
supersedes: []
---

## Context

Until M4 the workflow, prompt, schema and publish code were copied into each target
repository by a script. ADR 0001 left open how IssuePilot is distributed and how a
calling repository gets the prompt and code at the version it asked for.

Constraints found on 2026-10-21:

- GitHub has no built-in context that tells a reusable workflow its own commit. The
  known workaround reads `job_workflow_sha` from an OIDC token, which needs
  `id-token: write` ([nextstrain/.github workflow-context action](https://github.com/nextstrain/.github/blob/master/actions/workflow-context/action.yaml)).
- Even with that SHA, the caller's `GITHUB_TOKEN` cannot check out IssuePilot while
  IssuePilot is a private repository. GitHub does fetch actions and reusable workflows
  from a private repository for repositories of the same owner once the repository's
  Actions access level is `user`, which is now set.
- `uses:` refs are static; a reusable workflow cannot pass its own ref on to them.
- The two-job split (ADR 0001) only protects anything if the investigating job really
  gets a read-only token, so the job layout and permissions should not be left to
  each caller to get right.

## Decision

IssuePilot ships a reusable workflow, `.github/workflows/issuepilot.yml`, whose two jobs
use two composite actions from the same repository, `actions/investigate` and
`actions/publish`. Each action reads the prompt, schema and Python code from its own
directory (`github.action_path`), so files always match the action's ref. On main the
workflow refers to the actions `@main`; a release commit pins them to its own tag with
`scripts/pin_refs.py`, and callers use `@v1` (or a full tag or SHA).

## Rationale

- The reusable workflow fixes the job layout and per-job permissions; a caller only
  sets the ceiling (`contents: read, issues: write, pull-requests: read`) and passes
  the secret. Ten lines in `templates/issuepilot.yml`.
- Composite actions are downloaded by the runner with the action's own ref, also
  from a private repository, so no checkout of IssuePilot and no extra token is needed.
- Pinning refs in the release commit is one deterministic rewrite, guarded by a test
  and a `--check` mode, instead of an OIDC token in a job next to the agent.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep copying files into each repository | Every update is a manual copy; versions drift per repository |
| Reusable workflow that checks out IssuePilot at its own SHA (OIDC claim) | Needs `id-token: write`; impossible while IssuePilot is private |
| Composite actions only, caller writes the two jobs | Each caller must get the permissions right; a mistake hands the agent a write token |
| Reusable workflow with a `issuepilot_ref` input | The caller repeats the version and can make the two disagree |

## Consequences

- **Upside:** one file for users, versioned by tag, the security layout enforced
  centrally, and no IssuePilot code inside the user's repository.
- **Cost:** a branch can only be tested end to end from another repository after the
  workflow's refs point at it; day-to-day testing uses main (the sandbox calls `@main`)
  and the backtest workflow, which runs the actions from the same checkout.
- **Cost:** release is a two-step act (pin, tag) instead of tagging main directly;
  `scripts/pin_refs.py --check` guards it.
- **Cost:** while IssuePilot is private only repositories owned by the same account
  can call it. Making it public is a separate decision.
- **Cost to reverse:** low; the actions are the units, and either a different wrapper
  or a copied layout can call them.
