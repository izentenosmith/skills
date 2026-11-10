---
name: eval-runs-read-working-tree
description: run.py stages the skill from the checkout as it is on disk, uncommitted edits included, so commit dates can mislead about staleness
type: gotcha
source: evals/run.py::stage_skill, session 2026-11-09
verified: 2026-11-10
volatility: high
---

`stage_skill` copies the skill folder from this checkout's working tree. A fix is usually run
before it is committed, so the commit that records it lands minutes after the run.

**Symptom:** `git log` shows a skill changed after its scored run, though the run saw that change.
**Avoid by:** treating a commit within minutes of the run as its record; only a later, separate
change makes the score stale.
