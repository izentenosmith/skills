---
name: grader-fix-regrade
description: When a grade.py check wrongly fails a good run, re-grade every stored run of that eval and confirm only with-skill false negatives flip
type: convention
source: evals/grade.py, commit 046d626
verified: 2026-11-18
volatility: low
---

A grader fix is only accepted when, re-graded against every stored run of that eval across all
iterations, the only flips are the with-skill runs it was meant to fix, no baseline moves, and
`evals/controls/make_controls.py --only <id>` still separates every control. The commit message
and `evals/README.md` say which runs flipped.
