# Data repair — fixing what the bug wrote

The code fix stops new damage. It does nothing for the rows, files or documents the bug already wrote. That repair is **its own artifact** — a script, migration or job, reviewed and versioned separately — because it has different risks: it runs once, against production data, and a mistake in it is a second incident.

## Before writing it

- [ ] **The affected set is a query, not a description.** The same reproducible query from Phase 2, with its count, its text written in the incident log (hard gate 2). If the repair touches anything outside that set, the repair is wrong.
- [ ] **Decide what "correct" is for each record**, and where the correct value comes from: recomputed from source data, restored from a backup, taken from an audit trail, or unknowable (then the record is flagged, not guessed).
- [ ] **Downstream copies.** Caches, search indexes, exports, reports, emails already sent, figures already reported. Each one is either repaired too, or listed as outstanding.

## The artifact

- [ ] **Dry-run mode, by default.** Without `--apply`, it opens the data read-only and reports what it *would* change — counts, and a sample of before/after values — and changes nothing. `--apply` is the only switch to writing (hard gate 3): it may refuse without the expected count, but a downstream precondition is a confirmed step of its own, not another flag.
- [ ] **Backup first, by the artifact itself.** Every `--apply` writes a backup of exactly the records it will change and reads it back *before* its first write — not a documented step beside it that someone can skip. A repair without a way back is a gamble with someone else's data.
- [ ] **Before and after counts**, printed on every run: records matched, changed, skipped, and failed.
- [ ] **Idempotent.** Running it twice changes nothing the second time. Select by the defect's signature, not by "everything since X", so a re-run finds nothing to do.
- [ ] **Bounded.** Batches, a limit, and a stop on the first unexpected error, rather than a single transaction over everything or a loop that keeps going.
- [ ] **Reviewed like code**, with a test against a small fixture holding both affected and unaffected records.

## Running it

1. **Dry run** against production data (read-only), and compare its count with Phase 2's. A mismatch stops everything until it's explained.
2. **Run for real in a non-production environment** with production-like data, when one exists. Verify with the Phase 2 query: the count of affected records is zero.
3. **Production, only with explicit confirmation** — state the command, the count it will change, where the backup is, and how to restore. Log the `confirmed` and `action[prod]` entries.
4. **Verify in production**: the Phase 2 query returns zero, a sample of repaired records is correct, the unaffected-records count is unchanged.
5. **Record it in the incident log**: the artifact, the backup's location, the counts, and anything left outstanding.
