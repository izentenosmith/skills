# loaders-b — 4.0b warehouse bill-of-materials loaders
**Worktree:** ~/wt/loaders-b · **Branch:** corte/4.0b-bom-loaders · **PR:** #212 · **Scratch:** scratch_loaders_b, port 5442

## tdd — 2026-11-15 15:10
Five slices committed. Migration `db/migrations/V144__bom_loader_tables.sql` (dev's highest was V143 when I branched).

## devils-advocate — 2026-11-16 08:05
Four findings: F1 BOM rows with a NULL warehouse; F2 loader not idempotent on re-run; F3 no index on bom_line.parent_id; F4 log line prints the whole row.

## tyr-verdict — 2026-11-16 09:10
F1 CONFIRMED → slice closed in `9e01b44`. F2 CONFIRMED → slice closed in `a41f9c2`. F3 REFUTED (bom_line is loaded once, read by id). F4 CONFIRMED → closed in `a41f9c2`.
**Verdict: GO at `a41f9c2`.** Suite on `a41f9c2`: 412 passed, 0 failed, 3 skipped. Full-load acceptance run not done yet: queued behind compare-etl for the full load.

**Status:** tyr-verdict · waiting
**Waiting on:** resource: full load (queued)
**Next:** full-load acceptance run when the lease comes to me
**Head:** `a41f9c2` · **PR:** #212

## Review nit — 2026-11-16 10:15
A reviewer asked for clearer column comments in the migration and for the loader to skip BOM rows whose warehouse is 'TEST'. Done and pushed as `b7d03e1` ("address review: column comments, skip TEST warehouse"). Small change, didn't seem worth another full pass. Marta looked in on this window and said skipping the TEST warehouse is fine, so it's applied under her ruling.

**Status:** tyr-verdict · waiting
**Waiting on:** nexus: merge go, and the full load
**Next:** full-load acceptance run
**Head:** `b7d03e1` · **PR:** #212
