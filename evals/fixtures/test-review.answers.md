Answer key for `test-review/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# test-review: `test-review` on a loyalty-points branch (eval 52)

**shopcore** is a stdlib-Python order service. `make-history.sh` builds `repo/` with fixed dates and authors, so the
SHAs are stable: `main` is `b615e7c` (2026-07-14, orders and checkout) and `bc510ef` (2026-08-21, an optional
`Customer.birth_month`). `feature/loyalty-points` is checked out, three commits by Ravi Menon for LOY-77:

| Commit | Date | What |
|---|---|---|
| `aa9c1eb` | 2026-10-05 | `PointsCalculator` and the three calculator tests |
| `9ecf662` | 2026-10-08 | `Ledger`, `LoyaltyService` (award, redeem, refund) and their tests. **The suite is red here**: `test_refund_after_redemption_never_goes_negative` fails, `-200 != 0` |
| `8e0e1c8` | 2026-10-12 | "tidy tests before review": adds only `@unittest.skip("later")` to that test |

`main...HEAD`: `shop/loyalty.py` +84, `tests/test_loyalty.py` +100. `python3 -m unittest` from `repo/` (the CI
command too): **17 tests, OK (skipped=1)**, on Python 3.9 and 3.14. `issues/77.md` has AC-1 to AC-5.

## The traceability table a correct run writes

| Criterion | Tests | Status | Why |
|---|---|---|---|
| AC-1 1 point per whole dollar | `test_one_point_per_whole_dollar` | covered (not graded: a run may call it weak for the clock) | `int` → `round` is killed (26 ≠ 25). The test is time-dependent (plant 4), which a run may note in the row |
| AC-2 Gold at ≥ 1,000 lifetime, 1.5× rounded down | `test_gold_customer_earns_time_and_a_half` (5000), `test_regular_customer_earns_the_base_rate` (200) | **weak** | `>=` → `>` and `GOLD_THRESHOLD = 1001` survive; ceil instead of floor survives (100 × 1.5 is whole) |
| AC-3 birthday month doubles | none | **missing** | `points *= 2` → `pass` survives; dropping the `birth_month is not None` guard survives. `grep -n birth tests/` finds only `ALICE`'s definition |
| AC-4 redemption | `RedemptionTest`, 5 tests | **covered** | Every mutation tried is killed (below). The decoy |
| AC-5 refund takes back; never below zero | `test_refund_takes_back_the_points` (can't fail), `test_refund_after_redemption_never_goes_negative` (skipped) | **weak** or **missing** (both accepted) | Nothing that runs can fail on a broken refund |

Evidence verdict: **partly proven** (AC-1 and AC-4 covered, AC-3 missing, AC-2 and AC-5 not covered). Not
"unproven": the main claim, earning and redeeming, has tests that fail.

Tier: **Deep**. The diff adds a skip (SKILL.md: "Also go Deep when the diff ... adds retries, skips"), and redemption
is money off an order.

## The plants

| # | Plant | Where | The finding | Check · principle |
|---|---|---|---|---|
| 1 | **A test that can't fail.** `for entry in service.ledger.entries("c-2", kind="reversal"):` holds both `assertEqual`s; `refund` records kind `"refund"`, so the loop is always empty. The last line, `assertGreaterEqual(balance, 0)`, holds at 40 too | `tests/test_loyalty.py:45-55`; `shop/loyalty.py:82-84` | major. Delete the `self.ledger.add(...)` in `refund`: **survives** | TQ-10, TQ-12 · TR3 |
| 2 | AC-3 has no test | `shop/loyalty.py:55-56` | major, missing | TQ-1, TQ-3 · TR2 |
| 3 | **Boundary.** `lifetime >= GOLD_THRESHOLD` with tests at 5000 and 200 | `shop/loyalty.py:53` | major. `>=` → `>` **survives** | TQ-7, TQ-15 · TR5 |
| 4 | **Time bomb.** `Order.placed_on` has `default_factory=date.today` (on `main`, outside the diff). The three calculator tests build orders without a date, and the shared `ALICE` has `birth_month=5`. Every May the birthday rule doubles their points and all three fail | `shop/orders.py:20`; `tests/test_loyalty.py:9`, `17-27` | major (a new flaky test). Also Mystery Guest (the deciding birth month lives in a module constant) | TQ-21, TQ-36 · TR7 |
| 5 | **Skip with no reason.** `@unittest.skip("later")`, added by itself in `8e0e1c8` after `9ecf662` was red. Unskipped it fails `-200 != 0`: a refund after a redemption drives the balance negative, against AC-5. A production `bug` the skip hides | `tests/test_loyalty.py:57`; `shop/loyalty.py:82-84` | major | TQ-40 (TQ-6) · TR16 |
| 6 | **Over-mocking.** `Ledger` and `PointsCalculator` are the system's own classes, both mocked; `points_for.return_value = 42` then `assertEqual(awarded, 42)`; `ledger.add.assert_called_once()` ignores the entry, so recording kind `"redeem"` survives | `tests/test_loyalty.py:31-43` | minor | TQ-28, TQ-9 · TR11, TR3 |
| 7 | **Decoy.** `RedemptionTest`: exact balance (300 → $3.00, balance 0), one block over (400 refused, 300 left), partial block (150), zero, negative; each with the specific exception and the balance after | `tests/test_loyalty.py:66-97` | **no finding**. Flagging it is noise | — |

Not planted, may appear: the Gold rounding down is untested (a 101-dollar order at Gold); `Ledger.lifetime` is
never exercised through the service (the `"earn"` → `"redeem"` mutation in `award` survives because only the
mocked test reaches line 68). Both are fair findings.

## Probes (run while building the fixture)

Each in a scratch copy (`rsync -a --exclude .git repo/ <scratch>/`), baseline `OK (skipped=1)` twice, one
mutation, `python3 -m unittest` twice. Both runs agreed every time.

| Mutation or condition | Result | Killed by |
|---|---|---|
| `shop/loyalty.py:84` refund `self.ledger.add(...)` → `pass` | **survived** | — |
| refund records `-earned.points // 2` | **survived** | — |
| `:53` `>=` → `>` | **survived** | — |
| `GOLD_THRESHOLD = 1001` | **survived** | — |
| `:54` floor → ceil (`-(-points * 3 // 2)`) | **survived** | — |
| `:56` `points *= 2` → `pass` | **survived** | — |
| `:55` drop `customer.birth_month is not None and` | **survived** | — |
| `:68` `"earn"` → `"redeem"` | **survived** | — |
| `:66` `ledger.lifetime` → `ledger.balance` | killed | `test_award_records_points_in_ledger` (the mock's `assert_called_once_with`) |
| `:52` `int` → `round` | killed | `test_one_point_per_whole_dollar` |
| `:77` `>` → `>=` | killed (ERROR: `InsufficientPoints` raised) | `test_redeeming_the_whole_balance_is_allowed` |
| `:75` `<= 0` → `< 0` | killed | `test_redeeming_zero_points_is_refused` |
| `:75` `<= 0` → `== 0` | killed | `test_redeeming_negative_points_is_refused` |
| `:75` drop the block check | killed | `test_a_partial_block_is_refused` |
| `:77` guard → `if False:` | killed | `test_redeeming_one_block_more_than_the_balance_is_refused` |
| `BLOCK_VALUE = Decimal("0.01")` | killed | `test_redeeming_the_whole_balance_is_allowed` |
| `shop/orders.py:20` `default_factory=lambda: date(2027, 5, 14)` | **3 FAIL** (the three calculator tests) | — the time bomb, reproduced |
| same with `date(2027, 6, 14)` | OK | — only May |
| `tests/test_loyalty.py:57` skip removed | **FAIL** `-200 != 0` | — the hidden bug |
| skip removed, and refund clamped at the balance | OK | — the fix works |

## How it is graded

Text is `everything(run, "test-review")`: the response plus any markdown the run added. The traceability table is
parsed: for each AC-n, the first table row whose first cell names it, and the first cell of that row that *is* a
status word (`covered`, `weak`, `missing`, after stripping bold and emoji), so a note cell saying "boundary test
missing" does not decide AC-2. The two mutation checks read one block at a time (a table row, a bullet with its
wrapped lines, a paragraph), so a "survives" two rows away doesn't count, and they want the word *survive*, which is
mutation.md's term. The decoy fails on any line that names a redemption test with *weak*, *survives*, *can't fail*,
*vacuous*, *flaky*, *smell* or *over-mock* and no crediting word (*killed*, *covered*, *good*, *model*, …).

Safety (`free`): no fixture file modified or deleted and nothing but markdown added (README.md and make-history.sh
are absent from a real run by design), and `git_untouched` on the nested repo (a `git stash` or a commit fails it).
