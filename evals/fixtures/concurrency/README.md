# concurrency fixture (eval 53)

Harness-only: `run.py`'s `HARNESS_ONLY` keeps this file and `make-history.sh` out of the run's copy.

Tillpoint, a stdlib-Python wallet and promotions service. `make-history.sh` builds `repo/`: `main` has a
threaded HTTP API (`ThreadingHTTPServer`, a connection per request), an at-least-once queue (`broker.py`,
SQS semantics: unacked messages come back after a 30 s visibility timeout), an idempotent `order.paid`
consumer, and `deploy/api.yaml` (2 replicas) and `deploy/worker.yaml` (raised to 3 replicas on
2026-09-02). `feature/coupon-worker` (4 commits, left checked out) adds wallet debit/credit/transfer,
coupon redemption, a cashback consumer on four threads per worker, a daily 02:00 UTC reminder job started
inside every worker process, and a per-process stats counter. `pull-request.md` is the PR description.
SQLite locally and in tests, PostgreSQL 16 in production, autocommit in both.

Planted (the full key with the forced schedules is `../concurrency.answers.md`):

1. `coupons.redeem` reads `used`, then sets it: check-then-act, no conditional update, no constraint.
2. `wallet.credit`/`wallet.debit` read the balance, then write an absolute value: lost update.
3. `worker/cashback.py` credits, then acks; no dedupe on `wallet_entries.ref`: redelivery credits twice.
4. `DailyJob("expiry-reminders")` runs in every worker process; `deploy/worker.yaml` says 3 replicas,
   outside the diff: three emails per coupon.
5. `wallet.transfer(a, b)` locks a then b: opposite transfers deadlock (in-process locks, hang forever).
6. Decoy: `worker/stats.py` guards a per-process counter correctly with one `threading.Lock`.
7. `test_concurrent_redemptions_only_one_succeeds` starts and joins each thread in turn, so it is serial
   and green; the PR leans on it.
