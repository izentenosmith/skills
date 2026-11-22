---
name: eval-workspace-shared-across-sessions
description: Several sessions write into the one eval workspace at once; run.py --iteration N does not check that another run already owns N, and a grade in one branch rewrites grading files another branch records
type: gotcha
source: skills-workspace/iteration-60 and iteration-60-run.log, iteration-49/eval-47, session 2026-11-21
verified: 2026-11-21
volatility: high
---

The workspace beside the main checkout ([[eval-workspace]]) is shared by every worktree, so by
every session working in this repo. On 2026-11-21 two sessions ran into `iteration-60` seven minutes
apart: a database-skills run had started there (eval 34 and 48), and a development run given
`--iteration 60` by number wrote its twelve evals beside them, overwrote their dispatch.json, and
graded their runs at its end. The same day another branch's eval 47 grader fix re-graded
`iteration-49/eval-47` in place, and a `--record` taken in an unrelated branch picked that change up.

**Symptom:** an iteration holds evals you did not run, its dispatch.json disagrees with its
`iteration-N-run.log`, or a recorded row outside the evals you ran moves.

**Avoid by:** right before launching, list the workspace and any `iteration-*-run.log` and pick a
number nothing uses (`run.py`'s default "next unused" is only safe if nothing else starts at the same
moment); never hand two jobs the same number. Before keeping a `--record`, diff `evals/benchmark.md`
and check that no row outside your evals moved. When one did because another branch re-graded it,
record from a scratch tree that symlinks the iterations and holds a re-graded copy of that eval
(the way [[benchmark-recorded-from-iteration-49]] describes), and leave the shared folder as that
branch left it. A collision is repaired by moving your evals to a fresh iteration and rebuilding
the other run's dispatch.json from its run log.
