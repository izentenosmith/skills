---
name: benchmark-recorded-from-iteration-49
description: The benchmark's rows come from iteration 49 (a full re-run), with eval 59 from 48 and the development evals 0–5, 27, 58, 60–63 from 55; --record over 48, 49, 50, 55 is complete
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
are superseded intermediate runs: never pass them. After the next partial re-run, pass 48, 49, 50,
55 and the new iteration, and check that all 64 rows are still there before keeping the result.
If iteration 49 is ever deleted for disk space, the
replace-rows rule applies again.

Since 2026-11-21 iteration 56 (the database evals 30–34, 47 and 48, re-run after the skill audit)
is part of the record, and so is iteration 60 (evals 34 and 48 again, after dbbuild gained `skills/database/dbbuild/theory.md`
and dbarchitect a new description), and so is iteration 62 (evals 30–34 and 47 after five fixes).
Iterations 60 and 61 are shared with another branch, whose development evals (0–5, 27, 58, 60–63)
landed in them by `--iteration` collision; 57–59 are wholly that branch's. Never pass 57–61 whole:
record from a scratch folder named `iteration-60` holding symlinks to only `eval-34-*` and `eval-48-*`,
plus `iteration-62`, after 48, 49, 50, 55 and 56, and check all 64 rows and that only database rows
moved.
