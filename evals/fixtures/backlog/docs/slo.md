# Service level objectives

## Checkout availability

- **SLO:** 99.5% of checkout requests succeed, over a rolling 28 days.
- **Error budget:** 0.5% of checkout requests.
- **Status on 2026-11-08** (from the monitoring dashboard): 0.82% of checkout requests failed in the last 28 days, so **164% of the error budget is spent**. Main contributors: the 2026-11-07 deploy (L-38), and payment-provider timeouts that fail the order on the first try (most of the rest).

## Error-budget policy

Agreed by Marta and the team on 2026-07-01:

> When the 28-day checkout error budget is spent, feature work on the shop stops. The team pulls reliability work for checkout until the budget is back under 100%. Open incidents and security fixes are exempt.
