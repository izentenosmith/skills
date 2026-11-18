# billing

The new billing service. Invoices, lines and surcharges are loaded from the legacy
`ledger2008` database (SQL Server 2008) by the ETL in `etl/`, compared against legacy by
`compare/`, and served through `api/`. Migrations live in `db/migrations/` (Flyway, `V<n>__<name>.sql`).
