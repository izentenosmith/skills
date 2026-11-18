---
name: eval-workspace
description: The eval workspace (../skills-workspace) — where every run lives, which iterations still exist, and how evals/benchmark.md is updated from it
type: entity
verified: 2026-11-18
volatility: high
---

# The eval workspace

**What it is.** The only copy of every eval run, its grading files and its baseline. It is outside
git, so it can't be rebuilt from the repo.

**Where it lives.** `skills-workspace/` beside the main checkout, shared by every worktree
(`evals/run.py::default_workspace`), as `iteration-N/eval-<id>-<name>/{with_skill/repK,old_skill}/`.

**How it behaves.** After grading, `run.py` aggregates every `iteration-*` folder into the
workspace's own `benchmark.md`. That is not the committed result. `evals/benchmark.md` follows the
curated list in `evals/README.md` ("`benchmark.md` was aggregated from iterations …"), which leaves
out superseded re-runs.

**Traps.**
- **`iteration-1` to `iteration-36` are gone.** The user deleted them on 2026-11-12 to free disk
  space, on purpose. The workspace held `iteration-37` to `iteration-48` on 2026-11-18. For evals
  not re-run since, the recorded rows are the only record. `aggregate.py --record` over the curated
  list would write a benchmark with only the re-run evals and silently drop every other row.
  **Avoid by:** aggregating the new iterations without `--record`, then replacing only the
  re-scored evals' rows in `evals/benchmark.md` and their entries in `evals/scores.json`, and
  recomputing the two overall lines from the table.
- Old iterations may be deleted again. Check which folders exist before any rebuild.

**Sources.** `evals/run.py::main`, `evals/aggregate.py`, `evals/README.md`, user 2026-11-12. Absorbed
the notes eval-workspace, benchmark-from-curated-list and eval-iterations-1-36-missing.
