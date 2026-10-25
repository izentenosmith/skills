# larkspur-db

Schema of Larkspur Supply's order database (`larkspur`, PostgreSQL 16), exported with
`pg_dump --schema-only` on 2026-10-19 and split by object type. Owned by the platform team; the
order service is the only application that writes to it.

- `db/schema.sql` — tables, constraints and indexes
- `db/views.sql` — reporting views
- `db/functions.sql` — PL/pgSQL functions, including the trigger functions
- `db/triggers.sql` — trigger definitions
- `db/migrations/` — the last two migrations applied before the export
- `app/config/database.ini` — the order service's connection settings

Notes from the team: `sales_order` is by far the largest table, and the nightly export that reads
`v_order_export` has been getting slower. The DBA has the row counts and the `pg_stat_statements`
output, but they are not part of this export. Nobody is sure whether anyone still reads the reporting
database that `fn_sync_report` writes to.
