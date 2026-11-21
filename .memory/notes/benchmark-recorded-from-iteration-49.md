---
name: benchmark-recorded-from-iteration-49
description: The benchmark's rows come from iteration 49 (a full re-run), with eval 59 from 48, the development evals 0–5, 27, 58, 60–63 from 55 64–75 from 57, and nine evals from 58; --record over 48, 49, 50, 55, 57, 58 is complete
type: fact
source: evals/benchmark.md, evals/scores.json, evals/aggregate.py, session 2026-11-19
verified: 2026-11-21
volatility: high
---

Iteration 49 re-ran evals 0–58 at three reps against a fresh baseline. `evals/benchmark.md` and
`evals/scores.json` were recorded with `aggregate.py --record` over iterations 48, 49 and 50,
oldest first: 48 holds only the held-out eval 59, and 50 holds eval 58 re-run after nexus changed.

This supersedes the part of [[eval-workspace]] that says to replace rows by hand and never
`--record`: that rule was about the deleted iterations 1–36, which no row depends on any more.
Since 2026-11-20 the record is `--record` over 48, 49, 50 and 55: iteration 55 re-ran evals 0–5, 27,
58 and the new 60–63 on the final development skills, and all 64 rows are present. Iterations 51–54
are superseded intermediate runs: never pass them. Since 2026-11-21 it is 48, 49, 50, 55, 57 (evals 64–75, first scored) and 58 (evals 5, 27, 58,
64, 65, 70–73 on the cut acceptance-tests, tyr-verdict and nexus text; runs on reverted cuts sit in
`iteration-58/reverted-cuts/`, which aggregate.py skips), with 76 rows. After the next partial re-run, pass those and the new iteration, and check
that all 76 rows are still there and that no row outside the re-run moved. The workspace is shared:
another branch's grader fix can re-grade an old iteration in place (eval 47 in iteration 49 on
2026-11-21), and a record taken then carries that change into an unrelated PR. Aggregate from a
scratch tree that re-grades such an eval with this branch's grader instead.
If iteration 49 is ever deleted for disk space, the
replace-rows rule applies again.
