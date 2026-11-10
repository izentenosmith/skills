---
name: zip-edits-via-patches
description: Text that only a marketplace zip should lose goes in marketplace/patches.json, not the skill, so eval scores stay valid
type: decision
source: marketplace/patches.json, marketplace/agensi.py::drop_section
verified: 2026-11-10
volatility: low
---

Each skill's eval score is only valid for the text it was run against, and an edit to `skills/`
needs an eval re-run before the listing is re-uploaded.

**Chosen:** harness-only text is removed at package time by `marketplace/patches.json`
(`old`/`new` edits and `drop_section`), which `marketplace/agensi.py::apply_patches` applies.
**Rejected:** editing the skill, which would make its score stale for a change buyers can't see.
**Because:** the review family's evals scored with those sections present; dropping them changes nothing a standalone install runs.
