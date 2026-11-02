# Payouts runbook

## fraud-score is slow or down
Payouts keep flowing — the service proceeds without a score (see architecture, payout flow step 2).
Page the risk team during business hours; no action needed out of hours.

## Payout stuck in `approved`
Check `bank-gateway` logs for the payment file; re-send with `payoutsctl resend <id>`.

## Testing the partner API against staging
Use the shared staging partner key:

    curl -H "X-Api-Key: tm-eval-fake-stg-key-0001" https://partner.staging.bazaar.test/partner/v1/payouts

## Webhook replays from the bank
The bank sometimes sends the same settlement twice. `payouts-svc` applies the latest status it receives.
