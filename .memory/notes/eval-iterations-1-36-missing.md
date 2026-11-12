---
name: eval-iterations-1-36-missing
description: Iterations 1-36 are gone from ../skills-workspace, so benchmark.md can't be rebuilt from the curated list; replace rows instead
type: gotcha
source: evals/README.md, evals/aggregate.py, session 2026-11-12
verified: 2026-11-12
volatility: high
---

On 2026-11-12 `skills-workspace/` held only `iteration-37` onward; on 2026-11-11 the curated list
still reproduced the committed `evals/benchmark.md`. No script in this repo removes iteration folders,
and the cause was not found.

**Symptom:** `aggregate.py --record` over the curated list writes a benchmark with only the evals
that were re-run since iteration 37, silently dropping every other row.
**Avoid by:** never running `--record` over the list while those folders are missing. Aggregate the
new iterations without `--record`, then replace only the re-scored evals' rows in
`evals/benchmark.md` and their entries in `evals/scores.json`; recompute the two overall lines from
the table. [[benchmark-from-curated-list]] holds again only if the folders are restored.
