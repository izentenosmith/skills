# Nexus — billing cutover, increment 4
**Updated:** 2026-11-16 09:30 · **Base:** dev at `7c1e9a2` · **Running:** 6 of 4 (runbook-docs finishing) · **Free disk:** 61 GB

| Session | Slice | PR | Stage | Waiting on | Next |
|---|---|---|---|---|---|
| loaders-a | 4.0a invoice loaders | #209 merged at `5d2be70` | done | nothing | archive |
| loaders-b | 4.0b warehouse bill-of-materials loaders | #212 at `a41f9c2` | tyr-verdict | nothing | report verdict |
| dual-mode | 4.1 dual mode | #214 | refactor-review | nothing | devils-advocate |
| compare-etl | 4.2 compare-only ETL | none yet | tdd | run: full load | finish compare |
| invoice-dates | 4.3 invoice date fix | none yet | architect-deep-dive | nothing | design |
| text-fix | S-fix: extraction keeps trailing characters | #215 at `c3e8f10` | tyr-verdict | nothing | report verdict |
| personnel-etl | 4.4 personnel ETL | none yet | tdd | nothing | slice 4 |
| runbook-docs | nightly-diff runbook | #213 merged by the user | done? | nothing | confirm clean |

## Waiting on the user
- none

## Leases
- full load — compare-etl since 2026-11-16 06:40, limit 08:40; queue: text-fix, loaders-b

## Archived
- none this increment
