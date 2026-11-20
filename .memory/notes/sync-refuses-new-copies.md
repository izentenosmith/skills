---
name: sync-refuses-new-copies
description: sync_shared.py reports a brand-new, never-committed copy as "edited directly" when its source changes; copy the file by hand, then --check
type: gotcha
source: .github/scripts/sync_shared.py, session 2026-11-20
verified: 2026-11-20
volatility: low
---

`sync_shared.py` decides a copy was hand-edited when it differs from `HEAD:<copy>`. A copy added in
the same uncommitted change has no `HEAD` version, so once it exists and its source changes again,
the script refuses to overwrite it ("was edited directly").

**Symptom:** after adding entries to `skills/shared.json` and syncing once, a second edit to the
source (seen with `harness/LEDGER.md` and `skills/development/architect-deep-dive/pipeline.md`)
leaves every new copy stale and the sync prints one "edited directly" line per copy.
**Avoid by:** `cp` the source over each new copy, then `sync_shared.py --check` (exit 0). After the
copies are committed the script behaves normally. See [[shared-docs-are-copies]].
