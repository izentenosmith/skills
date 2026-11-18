# Production checks that are Marta's

| # | Check | Why | From | Since | Done |
|---|---|---|---|---|---|
| 1 | The production Flyway history table has no failed V139 entry | a failed row blocks every later migration | loaders-a | 2026-11-08 | ☐ |
| 2 | The nightly diff job's cron on the production scheduler is 02:00, not 00:00 | at 00:00 it races the legacy close-of-day | runbook-docs | 2026-11-12 | ☐ |
