# Runbook — billing jobs

| Task | How |
|---|---|
| Query production (read-only) | `sqlite3 -readonly data/prod.db` |
| Pause a nightly job | comment its line in `jobs/schedule.cron`, then `ops/cron reload` (acts on production) |
| Resume a job | uncomment it, then `ops/cron reload` |
| Run a job against staging | `python3 jobs/<job>.py --db data/staging.db` |

Production writes outside a scheduled job need the on-call lead's explicit approval.
Incident records go in `docs/incidents/`; the tracker label for incident metrics is `prod-incident`.
