# reports/

The project's **research store** — where delegated web research and
context-gathering output lands so a future session reads it back instead of
searching the internet again. Created by the `reports-architecture` skill.

| Folder | Contents | Written by |
|---|---|---|
| `research/` | Dated research reports, `YYYY-MM-DD_<slug>.md` | the `research` skill (`/research`) |

That is the entire architecture. This folder is not a working record.

## What does *not* go here

- **Durable facts and notes** → the second brain vault.
- **Decisions that are expensive to reverse** → `docs/decisions/` (`adr` skill).
- **Open work, session logs, compaction checkpoints** → the vault; PreCompact
  dumps land in `.claude/precompact/` and are gitignored.

## Rules

- One file per research run. Sources linked inline, dates next to anything perishable.
- Reports are **immutable** — a report is what was believed on that date. A
  correction is a newer report that references the old one, never an edit.

---

## Snippet to add to CLAUDE.md

```markdown
## Research

Web research and context-gathering output goes to `reports/research/` as
`YYYY-MM-DD_<slug>.md` (the `research` skill). Read what's already there before
researching a topic again. Reports are immutable — correct one by writing a
newer report that references it.
```
