# test-review fixture (eval 52)

Harness-only: `run.py` keeps this file and `make-history.sh` out of a run's copy (`HARNESS_ONLY`).
The full answer key, with line numbers and every probe result, is
[../test-review.answers.md](../test-review.answers.md).

`make-history.sh` builds `repo/`: **shopcore**, a stdlib-Python order service (`python3 -m unittest`).
`main` has orders, checkout totals and an optional customer birth month. `feature/loyalty-points` (checked out)
adds `shop/loyalty.py` and `tests/test_loyalty.py` for LOY-77 in three commits. `issues/77.md` is the ticket,
with five acceptance criteria (AC-1 to AC-5). The suite is green: 17 tests, 1 skipped.

| Planted | Where | Catches a run that… |
|---|---|---|
| A refund test that can't fail: its assertions loop over `entries(kind="reversal")`; `refund` records `"refund"` | `tests/test_loyalty.py:45-55` | counts AC-5 as covered, or doesn't name the deleted-reversal mutation that survives |
| AC-3 (birthday month doubles) has no test | `shop/loyalty.py:55-56` | misses the missing criterion |
| The Gold threshold `>= 1000` tested only at 5000 and 200 | `shop/loyalty.py:53` | calls AC-2 covered, or doesn't name `>=` → `>` |
| A time bomb: `Order.placed_on` defaults to `date.today()`, `ALICE` has `birth_month=5`, so three calculator tests fail every May | `shop/orders.py:20`, `tests/test_loyalty.py:9-27` | passes the determinism sweep |
| `@unittest.skip("later")`, added in the last commit after the test failed; unskipped it exposes a negative balance | `tests/test_loyalty.py:57` | ignores the skip, or the bug it hides |
| The award test mocks `Ledger` and `PointsCalculator` and asserts the stub's 42 | `tests/test_loyalty.py:31-43` | treats it as evidence |
| A decoy: `RedemptionTest` is good (exact balance, one block over, partial, zero, negative; exact errors, balance unchanged) | `tests/test_loyalty.py:66-97` | flags it as weak |
