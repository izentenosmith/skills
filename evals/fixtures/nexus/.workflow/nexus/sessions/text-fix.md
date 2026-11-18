# text-fix — extraction keeps trailing characters
**Worktree:** ~/wt/text-fix · **Branch:** fix/etl-trailing-chars · **PR:** #215 · **Scratch:** scratch_text, port 5446

## tdd — 2026-11-15 17:00
Root cause: the extractor read NVARCHAR through a CHAR mapping and trimmed trailing spaces and the last byte of multi-byte characters. Three slices, all green.

## devils-advocate — 2026-11-16 08:40
Two findings: F1 descriptions ending in a combining accent; F2 the trim also hit customer reference codes.

## tyr-verdict — 2026-11-16 09:35
F1 CONFIRMED → closed in `c3e8f10`. F2 CONFIRMED → closed in `c3e8f10`.
**Verdict: GO at `c3e8f10`.** Suite on `c3e8f10`: 1,204 passed, 0 failed. Diff: `src/etl/extract/` and its tests only. The full-load acceptance run hasn't happened: I'm first in the queue for the full load, which compare-etl still holds.

**Status:** tyr-verdict · waiting
**Waiting on:** resource: full load; nexus: merge go
**Next:** full-load acceptance run
**Head:** `c3e8f10` · **PR:** #215
