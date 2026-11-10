---
name: eval-runs-read-working-tree
description: run.py stages the skill from the checkout as it is on disk, uncommitted edits included, so commit dates can mislead about staleness
type: gotcha
source: evals/run.py::stage_skill, session 2026-11-09
verified: 2026-11-10
volatility: high
---

`stage_skill` builds what it stages from this checkout's working tree: by default the skill as
`marketplace/agensi.py` packages it, or the folder itself. A fix is usually run before it is
committed, so the commit that records it lands minutes after the run. Runs since
`evals/scores.json` existed also record a `skill_hash`, which settles it.

**Symptom:** `git log` shows a skill changed after its scored run, though the run saw that change.
**Avoid by:** treating a commit within minutes of the run as its record; only a later, separate
change makes the score stale.
