# Post-mortem: renewals charged twice (2026-09-22)

- **Incident item:** L-6 · **Severity:** SEV-2 (money taken from customers in error)
- **Impact:** 61 subscribers charged twice for their September renewal, £1,342 in total, all refunded by hand by 2026-09-24.
- **Detected by:** customer emails, 09:40 UTC. **Restored:** 2026-09-23 11:15 UTC (renewal job paused, its retry disabled).

## What happened

The renewal job calls the payment provider once per subscription. On 2026-09-22 the provider was slow; requests that timed out on our side had in fact succeeded on theirs. The job retried each timeout, and with no idempotency key the provider treated every retry as a new charge.

## Contributing factors

1. Renewal charges carry no idempotency key, so a retry is a new charge.
2. Nothing alerts on a subscription charged more than once in a day; customers found it.
3. The weekly payment reconciliation report (charges vs. orders) exists, but nobody reads it and nothing notices when it doesn't run. It would have shown the duplicates on the 22nd.

## Follow-ups

| # | Action | Type | Owner | Due | Item |
|---|---|---|---|---|---|
| FU-1 | Every renewal charge carries an idempotency key | prevent | (to assign at planning) | 2026-10-15 | L-31 |
| FU-2 | Alert when a subscription is charged twice in a day | mitigate | chen | 2026-10-31 | L-32 |
| FU-3 | Someone reads the payment reconciliation report every Monday, and an alert fires if it didn't run | process | dara | 2026-10-31 | (to create) |

Until FU-1 is done, the renewal job's retry stays disabled and every double charge it still produces is refunded by hand.
