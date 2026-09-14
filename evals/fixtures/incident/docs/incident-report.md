# INC-2026-0814 — Statement API outage

**Written:** 2026-08-05, during the follow-up call
**Author:** Tomas Lind, on behalf of the Ledger team
**Status:** resolved

## Summary

On 4 August the statement API became unavailable for roughly two and a half
hours. Every account was affected. The cause was an unbounded database query
introduced in the CSV export path, which saturated the connection pool on
db-primary.

## Timeline

- **14:22** — First noticed. Support escalated a customer complaint about
  statements timing out.
- **14:31** — Ana confirmed db-primary was at pool exhaustion.
- **14:40** — Status page updated.
- **15:02** — Revert deployed. Error rate began falling immediately.
- **15:18** — Error rate back to baseline. Considered mitigated.
- **18:47** — statement_timeout set on production as a follow-up.

## Cause

Priya's change on 26 July removed the LIMIT from the statement query so that
finance could run a full-history audit export. This was reviewed and approved,
but nobody modelled what an unbounded query would do on the large
reconciliation accounts — some of which carry several million entries.

Frankly Priya should have caught this in review. The 500-row limit had a
comment on it explaining exactly why it was there, and it was removed anyway.

## What we must do

1. **Add rate limiting to the export endpoint this sprint.** This cannot happen
   again and rate limiting is the obvious control.
2. Require a second reviewer on anything touching `statements.py`.
3. Ban unbounded queries in code review.

## Impact

Statement API unavailable 14:00–15:18 approximately. All accounts. We do not
have a precise figure for affected users — the metrics we would need are
outside the 14-day retention for the relevant dashboard.
