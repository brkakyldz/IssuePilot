# evals

Backtests of IssuePilot's investigation quality: cases whose right answer is known,
run through the real investigate action in GitHub Actions and scored. The case format,
the scoring and the M3 acceptance IDs are in
[`docs/contracts/backtest.md`](../docs/contracts/backtest.md).

- `cases/` — real closed issues replayed at the commit before their fix, plus fixtures.
- `backtest.py` — plan, run, score, and build a case from GitHub (`--help`).
- `field.py`, `field/` — field trials on real issues of well-known repositories, each
  comment reviewed by a separate model (`--help`).
- Results of measured runs: `docs/runs/`.

Run all cases on a branch and grade causes with a separate model:

```bash
python evals/backtest.py run --suite evals/cases --ref my-branch --judge opus --out .backtest-my-branch
```

Running needs the `CLAUDE_CODE_OAUTH_TOKEN` secret on this repository; each case
uses the subscription quota of one investigation.
