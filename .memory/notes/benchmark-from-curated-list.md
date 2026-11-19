---
name: benchmark-from-curated-list
description: evals/benchmark.md is rebuilt from the iteration list in evals/README.md, not from run.py's automatic aggregate over every iteration
type: gotcha
source: evals/run.py::main, evals/aggregate.py, evals/README.md
verified: 2026-11-19
volatility: high
---

After grading, `run.py` aggregates every `iteration-*` folder in the workspace into the
workspace's own `benchmark.md`. That set includes iterations the recorded benchmark leaves out
(superseded re-runs, and runs from before the ledger grammar), so it is not the committed result.

**Avoid by:** running `evals/aggregate.py` on exactly the iterations listed in `evals/README.md`
("`benchmark.md` was aggregated from iterations …"), oldest first, plus the new one, then copying
the output to `evals/benchmark.md`. The list should reproduce the committed file before you add to it.

**Since 2026-11-19 the curated list is one iteration.** Every row comes from iteration 49, a full
re-run ([[eval-iterations-1-36-missing]]); the long list in `evals/README.md` describes the history
before it. The rule is unchanged: aggregate iteration 49 plus the new iterations, never the
workspace's every-iteration aggregate.
