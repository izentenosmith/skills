---
name: eval-fixtures-per-checkout
description: Eval fixture git histories and venvs are gitignored build output, so each new worktree must run evals/setup.sh first
type: gotcha
source: evals/setup.sh, evals/run.py::fixture_built, session 2026-11-09
verified: 2026-11-10
volatility: low
---

`evals/setup.sh` builds the nested fixture repos (each fixture's history script, e.g. `evals/fixtures/incident/make-history.sh`) and the pipeline venvs; git
ignores both, so a fresh worktree has none of them.

**Symptom:** `run.py` exits with "run ./setup.sh first — not built: …" (or `--dry-run` warns).
**Avoid by:** running `./evals/setup.sh` once in each new checkout before any eval run.
