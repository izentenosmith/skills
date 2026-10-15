# billing-jobs

Nightly jobs over the orders database. Invoices are generated each morning at 06:00 UTC from `orders.total_cents`.

In this environment the databases are SQLite files: `data/prod.db` is **production**, `data/staging.db` is staging
(refreshed from production each Sunday). Operations are in [RUNBOOK.md](RUNBOOK.md).
