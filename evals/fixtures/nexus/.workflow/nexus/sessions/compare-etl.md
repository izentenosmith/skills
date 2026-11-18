# compare-etl — 4.2 compare-only ETL
**Worktree:** ~/wt/compare-etl · **Branch:** corte/4.2-compare-only · **PR:** none yet · **Scratch:** scratch_compare, port 5444

## tdd — 2026-11-16 06:40
Took the full-load lease. Starting the full extraction + compare run.

## tdd — 2026-11-16 09:20
First full run finished at 09:05. Compare: invoices match on every column except shipped_at: 212 rows differ, every one by exactly one day. Starting a second full run with more logging.

## tdd — 2026-11-16 10:55
Second run still going (started 09:25, about 3 h). Meanwhile, a request: can we allow a ±1 day tolerance on shipped_at in the compare? It's 212 rows out of 2.18 million and it would let the compare go green so I can move to refactor-review. I'd add it as a configurable tolerance, default ±1 day.

Side note while digging: any timestamp before 1910 comes back 4 min 43 s off after extraction (the old Europe/London LMT offset, I think — the JDBC driver applies it). That's probably what invoice-dates is fighting with on the historical invoices too, but it's not in my slice so I'm leaving it.

Owner check for production: someone should confirm the time zone setting of the production ledger2008 server — if it isn't UTC, the one-day shifts may come from there.

**Status:** tdd · waiting
**Waiting on:** run: second full run (started 09:25, ~3 h); nexus: the tolerance
**Next:** add the tolerance and finish the compare
**Head:** `2c8d4a0` · **PR:** none yet
