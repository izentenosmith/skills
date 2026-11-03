# Answer key — eval 53, concurrency-review on `concurrency/`

Outside the fixture folder on purpose: a run never sees it.

**Review target:** `repo/` on `feature/coupon-worker` (4 commits over `main`, 14 files, +410/-2).
**Tier:** Deep. The `invariants` family hits (`balance`, `credit`, `debit`, `coupon`, `redeem`,
`transfer`) together with `threads`, `locks`, `messaging` and `schedule`; a consumer and a scheduler are
added (SKILL.md, Calibrate).
**Runtime:** Python 3, `ThreadingHTTPServer` (a thread and a connection per request) in the API;
the worker runs the `orders` consumer, four `cashback` consumer threads, a heartbeat and the
`DailyJob` thread. SQLite locally and in tests, PostgreSQL 16 in production, both **autocommit**
(`tillpoint/db.py`), so each statement is its own transaction; PostgreSQL's default READ COMMITTED.
Broker: at-least-once, 30 s visibility timeout, order not guaranteed (`tillpoint/broker.py`).
**Topology (outside the diff):** `deploy/api.yaml:9` `replicas: 2`; `deploy/worker.yaml:9`
`replicas: 3` (raised from 1 by commit "deploy: run the worker with 3 replicas", 2026-09-02). So: API =
2 pods × a thread per request; worker = 3 pods × 4 cashback threads = 12 concurrent cashback consumers;
**3 `DailyJob` threads**, one per worker pod.

## Findings

| # | Site | Check | Severity | Planted line | Fix |
|---|---|---|---|---|---|
| 1 | `coupons.used` row | CK-3 / CK-24 / CK-35 (security) | blocker | `coupons.py:27` reads `used`, `:38` `UPDATE … WHERE code = ?` | `UPDATE coupons SET used = 1, … WHERE code = ? AND used = 0` and check `rowcount == 1` before crediting, in one transaction with the credit; or a unique `coupon_redemptions(code)` row |
| 2 | `wallets.balance_cents` row | CK-23 / CK-35 | blocker | `wallet.py:14` read, `:22`/`:29` absolute write | `UPDATE wallets SET balance_cents = balance_cents - ? WHERE user_id = ? AND balance_cents >= ?` + rowcount; `balance_cents + ?` for credit; or `BEGIN IMMEDIATE` (SQLite) / `SELECT … FOR UPDATE` in a transaction (PostgreSQL) |
| 3 | `promotions.order-paid` message → wallet | CK-29 / CK-31 | blocker | `cashback.py:22` credit, `:40` ack; `wallet_entries.ref` has no unique constraint | idempotency key `order:<id>` (or the event id) inserted under a UNIQUE constraint in the same transaction as the credit; skip on conflict |
| 4 | `coupons.reminder_sent` / outbound email | CK-33 (+CK-3 inside the job) | major | `worker/__main__.py:46` starts `DailyJob` in every worker process; `jobs.py:12` select then `:18` mark after the send | one runner: a Kubernetes CronJob with `concurrencyPolicy: Forbid`, or a lease/leader, or claim the period atomically (`INSERT INTO job_runs(job, day)` under a unique key); and claim each coupon with `UPDATE … SET reminder_sent = 1 WHERE code = ? AND reminder_sent = 0` before sending |
| 5 | `wallet._locks` (two per-wallet `threading.Lock`s) | CK-9 | major (blocker under normal load) | `wallet.py:46-47` locks `from_user` then `to_user` | take both locks in one order (`sorted((a, b))`), or drop the in-process locks for a DB-level atomic update |
| — | `worker/stats.py` `Stats` | CK-1/CK-2 | **not a finding** | `self._lock` around every read and write (`:16`, `:20`, `:24`) | none: per-process by design (docstring), each replica logs its own |
| — | `tests/test_coupons.py:46-47` | CK-36 | test finding / evidence trap | `t.start(); t.join()` in the loop: the 20 "concurrent" threads run one at a time | Barrier/Event at the gap (between `coupons.py:27` and `:38`), all threads started before any joins |

Reasonable extras a good run may also report (not graded): the in-process transfer locks don't
coordinate with the other API pod or with the worker's `credit` (CK-1/CK-32); `redeem` and `transfer`
run their two writes without a transaction, so a failure between them leaves a coupon used and nothing
credited, or a debit with no credit (CK-28/CK-15); `cashback.consume` retries a message forever after a
failure that follows the credit; the four consumer threads share nothing but the `Stats`.

## Interleavings (what the graded block looks like)

```text
INTERLEAVING  double redemption
actors     A, B = two POST /coupons/redeem for WELCOME10 (double-click, or a script), any API pod
shared     coupons[WELCOME10].used=0, wallet(u1)=0
invariant  each coupon credits its amount once

 #  actor  step                                         shared after
 1  A      SELECT … used → 0          (coupons.py:27)    used=0, wallet=0
 2  B      SELECT … used → 0          (coupons.py:27)    used=0, wallet=0
 3  A      UPDATE coupons SET used=1  (coupons.py:38)    used=1, wallet=0
 4  A      credit 1000                (coupons.py:39)    used=1, wallet=1000
 5  B      UPDATE coupons SET used=1  (coupons.py:38)    used=1, wallet=1000
 6  B      credit 1000                (coupons.py:39)  ! used=1, wallet=2000

result     1000 credited twice for one coupon
needs      two requests inside the gap; ≥ 2 request threads (ThreadingHTTPServer) or the 2 api replicas
confirm    Barrier(2) after the SELECT in both; assert one CouponAlreadyUsed; 3 runs
```

## Forced schedules run while building the fixture (3 of 3 red each)

`$S/ev53/verify/force.py` against a scratch copy of `repo/` (`python3 -I force.py <copy>`), three runs,
identical results each time:

| Scenario | Seam | Result (3/3) |
|---|---|---|
| double redemption | connection proxy waits on `Barrier(2)` after the coupons `SELECT` | both redeem: `[1000, 1000]`, 2000 credited, want 1000 |
| lost update | proxy waits after the wallets `SELECT`; debits 300 and 500 from 1000 | balance 700, want 200 (both accepted) |
| deadlock | per-wallet lock wrapper waits on `Barrier(2)` after the first acquire | both `transfer` threads still blocked after 2 s |
| redelivery | credit, no ack, clock + 31 s, second delivery | `attempts=2`, balance 400, want 200, two `wallet_entries` rows |
| 3 replicas | three `send_expiry_reminders` on separate connections, `Barrier(3)` in the first `send` | three emails to `u1`, want one |
| decoy | 16 threads × 20,000 `handled()` | exactly 320,000. Not a refutation on its own (CR3): the quoted `self._lock` is |

The fixture's own suite (`python3 -m unittest discover -s tests -t .`) is 14/14 green, including
`test_concurrent_redemptions_only_one_succeeds`. That green run is the evidence trap.
