# Coupons, wallet transfers and the promotions worker

`feature/coupon-worker` → `main` · Ines Calder, Ravi Menon, Dana Whitlock

## What

- **Coupon redemption**, `POST /coupons/redeem`: checks the coupon, marks it used and credits its amount
  to the redeemer's wallet.
- **Wallet debit and transfer**, `POST /wallet/debit` (checkout's pay-with-wallet) and
  `POST /wallet/transfer` (gift credit to a friend).
- **Cashback**: 5 % of every paid order back to the wallet, consumed from `promotions.order-paid` on four
  threads per worker.
- **Expiry reminders**: every day at 02:00 UTC the worker emails holders whose coupon expires within
  24 hours.

## Notes for reviewers

- Concurrency: redemption is covered by `test_concurrent_redemptions_only_one_succeeds` (20 threads, one
  wins). Green locally and in CI.
- Transfers take a per-wallet lock, so two transfers on the same wallet can't interleave.
- The reminder job runs inside the worker, so there's no separate CronJob to deploy or forget.
- The heartbeat counters are thread-safe.

## Rollout

Merge, then deploy the api and the worker as usual. Marketing sends the first batch of 40,000 welcome
coupons on 2026-11-10.
