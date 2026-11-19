---
name: benchmark-recorded-from-iteration-49
description: Since 2026-11-19 the benchmark's train rows come from iteration 49, a full re-run (eval 58 from 50, held-out eval 59 from 48), so --record over 48, 49, 50 is complete
type: fact
source: evals/benchmark.md, evals/scores.json, evals/aggregate.py, session 2026-11-19
verified: 2026-11-19
volatility: high
---

Iteration 49 re-ran evals 0–58 at three reps against a fresh baseline. `evals/benchmark.md` and
`evals/scores.json` were recorded with `aggregate.py --record` over iterations 48, 49 and 50,
oldest first: 48 holds only the held-out eval 59, and 50 holds eval 58 re-run after nexus changed.

This supersedes the part of [[eval-workspace]] that says to replace rows by hand and never
`--record`: that rule was about the deleted iterations 1–36, which no row depends on any more.
After a partial re-run, pass 48, 49, 50 and the new iteration, and check that all 60 rows are
still there before keeping the result. If iteration 49 is ever deleted for disk space, the
replace-rows rule applies again.
