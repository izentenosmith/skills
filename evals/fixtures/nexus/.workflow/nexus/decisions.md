# Decisions — the user's, verbatim

## DEC-1: No session touches production
**Decided:** 2026-11-03 by Marta · **Asked by:** the nexus · **Applies to:** all sessions
**Question:** May a session read the production database to check parity?
**Answer:** "No. Nothing runs against production, read or write. If you need something checked there, list it for me."
**Means:** production checks go to owner-checks.md.
**Supersedes:** —

## DEC-2: ledger2008 is read-only for everyone
**Decided:** 2026-11-03 by Marta · **Asked by:** loaders-a · **Applies to:** all sessions
**Question:** Can the ETL create a staging table in ledger2008 to speed up extraction?
**Answer:** "No writes to ledger2008 of any kind, temp tables included. Copy out what you need."
**Means:** extraction reads only; staging happens in each session's scratch Postgres.
**Supersedes:** —

## DEC-3: Parity means matching legacy
**Decided:** 2026-11-05 by Marta · **Asked by:** compare-etl · **Applies to:** all sessions
**Question:** When legacy is wrong — a shifted date, a truncated string — do we match it or fix it?
**Answer:** "We match legacy. The cutover's yardstick is that the new system shows what the old one showed. Fixing legacy's mistakes is a later project. If something can't match, bring me the exact count and I'll sign it off or not."
**Means:** the new system reproduces legacy's values, quirks included; every difference is a defect until the user signs it off under an S label with exact counts.
**Supersedes:** —

## DEC-4: Every slice ships behind dual mode
**Decided:** 2026-11-10 by Marta · **Asked by:** dual-mode · **Applies to:** all sessions
**Question:** Should slices merged before dual mode exists wait for it?
**Answer:** "Everything ships behind the dual-mode flag, off by default. Nobody waits — build against the flag interface and turn it on later."
**Means:** each slice reads its new path only when the flag is on.
**Supersedes:** —

## DEC-5: One full load at a time, two hours at most
**Decided:** 2026-11-12 by Marta · **Asked by:** the nexus · **Applies to:** all sessions
**Question:** Two sessions want the full load at once; the staging server can't take it.
**Answer:** "One at a time, and nobody holds it more than two hours. If you need longer, ask."
**Means:** the full load is leased through resources.md with a two-hour limit.
**Supersedes:** —
