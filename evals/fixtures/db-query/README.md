# brightcart — order service database

Brightcart's order service on PostgreSQL 17 (`brightcart`). The schema is in `db/schema.sql`; the
service's data-access code is `app/repository.py`.

What the team has collected for this review:

- `perf/pg_stat_statements.csv` — production, statistics reset 2026-09-28, exported 2026-10-28.
- `perf/pg_stat_user_tables.csv`, `perf/pg_stat_user_indexes.csv` — production, same period.
- `perf/plans/` — `EXPLAIN (ANALYZE, BUFFERS)` output. Plans 01–04 were captured on **staging**, which
  holds a full copy of production restored on 2026-10-27. Plan 05 was captured by a developer on their
  laptop.
- `perf/blocked_customer_profile.txt` — a profiling query run on staging.
- `perf/proposed-indexes.md` — indexes a developer wants to add before Black Friday.
- `audit/summary.md` — the needs-data flags from last month's schema audit.

Complaints from the business: support says looking a customer up by email "takes ages"; the marketing
export has come back empty every night since the CRM import on 2026-10-20; the monthly sales report is
"the slowest thing we run".

`scripts/psql-staging` runs a statement against the staging copy.
