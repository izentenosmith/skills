---
name: eval-iterations-1-36-missing
description: Iterations 1-36 were deleted from ../skills-workspace to free disk space, so benchmark.md can't be rebuilt from the curated list; replace rows instead
type: gotcha
source: evals/README.md, evals/aggregate.py, user 2026-11-12
verified: 2026-11-12
volatility: high
---

The user deleted `iteration-1` to `iteration-36` from `skills-workspace/` on 2026-11-12 to free disk
space on their notebook; it holds `iteration-37` onward. It was deliberate, and they are not coming
back: the recorded rows for the evals not re-run since are the only record of those scores.

**Symptom:** `aggregate.py --record` over the curated list writes a benchmark with only the evals
that were re-run since iteration 37, silently dropping every other row.
**Avoid by:** never running `--record` over the list while those folders are missing. Aggregate the
new iterations without `--record`, then replace only the re-scored evals' rows in
`evals/benchmark.md` and their entries in `evals/scores.json`; recompute the two overall lines from
the table. [[benchmark-from-curated-list]] no longer applies to iterations before 37. Old iterations
may be deleted again for space, so check which folders exist before any rebuild.
