---
name: eval-workspace
description: Every eval run, grading and baseline lives in ../skills-workspace next to the main checkout, outside git
type: reference
source: evals/run.py::default_workspace
verified: 2026-11-10
volatility: low
---

`default_workspace` puts runs in `skills-workspace/` beside the main checkout (shared by every
worktree), as `iteration-N/eval-<id>-<name>/{with_skill/repK,old_skill}/`. It is the only copy of
the run outputs and their grading files, so it can't be rebuilt from the repo.
