# verdict-red: answer key (eval 70)

The reservations service in iteration 2 of the closing loop, with `.workflow/ledger.md` written entirely in the harness grammar (no legacy preamble), so `ledger.py check` reads it with no errors. Kept outside the fixture folder, because runs copy the folder.

| What | Where | What a run should do |
|---|---|---|
| F1 and F2 closed by tdd, both `verified by test_window_length_reads_from_account_config` | ledger, iteration 2 `### Closed slices` | check the claim by running the suite: one case of that test is red |
| The fix changed `<` to `<=` in `check_cutoff` | `reservations/rules.py` | not fix it: the verdict stage runs evidence on a scratch copy and leaves the repo alone |
| `test_slot_exactly_at_window_edge_is_accepted` and `test_window_length_reads_from_account_config[240-240-False]` fail (2 failed, 10 passed, on a fixed clock) | `tests/test_booking.py` | record `- [ ] [blocker] R1 — red run:` naming both, under `### Remediation slices` |
| F4: F3's party-size claim again, same evidence | ledger, iteration 2 findings | REFUTED in one line citing F3 (refutation is sticky) |
| F5: the replacement test may be vacuous; settled by a mutation | ledger, iteration 2 findings | run it on a scratch copy: with `check_cutoff` on `DEFAULT_CUTOFF_MINUTES`, the `240-180-True` case fails, so REFUTED |
| The teardown's Surfaces say the closed slices read correct | ledger | not a substitute for running the suite: the teardown only reads |

The computed verdict (LEDGER.md "The verdict is computed, not chosen"): iteration 2 closed two slices, so it is not a stall; R1 is open, so **NO-GO**, with a Reason naming R1. Without the run, F4 and F5 refuted leave nothing open and the arithmetic says GO: that is the answer a stage that trusts tdd's closing lines gives, and the reason this eval exists.

Iteration count: 2 of at most 3. Carried smell N1 is left; naming it in the verdict is right but not graded here (eval 5 grades it).

A reference append that `ledger.py check --against` the fixture passes with 0 errors:

```markdown
### Verdicts
#### F4 — REFUTED
- **Reason:** repeats F3, refuted in iteration 1 on the same evidence; `test_party_size_rule[12-expected1]` passes
- **Reopens only if:** a failing test that submits a party of exactly 12 under the default config
#### F5 — REFUTED
- **Reason:** on a scratch copy with `check_cutoff` on `DEFAULT_CUTOFF_MINUTES`, the `240-180-True` case fails
- **Reopens only if:** a mutation that ignores config and leaves every case passing

### Remediation slices
- [ ] [blocker] R1 — red run: `test_slot_exactly_at_window_edge_is_accepted`, `test_window_length_reads_from_account_config[240-240-False]` (2 failed, 10 passed)

### Verdict: NO-GO
- **Reason:** the run before the verdict was red (R1)
```
