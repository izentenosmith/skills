# Ledger — cancellation cutoff on bookings

## Iteration 1

### Smells
- **N1** Dispensables / Duplicate Code at `check_party_size` and `check_venue_open` — noted: two call sites, a shared helper costs more indirection than it saves
  - **Promote if:** a third rule reads a config key with a default

### Findings (unadjudicated)
#### F1
- **Target:** acceptance criterion 3 — the window length reads from account config
- **Claim challenged:** the cutoff window length is read from account config
- **Evidence:** `check_cutoff` closes over `DEFAULT_CUTOFF_MINUTES` and never reads `config`
- **Breaking case:** config `cutoff_minutes: 240`, slot 180 minutes out → accepted; expected `CUTOFF_WINDOW`
- **Confidence:** proven
- **Severity hint:** major
#### F2
- **Target:** `test_cutoff_window_reads_from_account_config`
- **Claim challenged:** this test verifies that config is honoured
- **Evidence:** it sets `cutoff_minutes: 240` and asserts on a slot 30 minutes out, inside both the configured and the default window
- **Breaking case:** delete the config lookup → the test still passes
- **Confidence:** proven
- **Severity hint:** major
#### F3
- **Target:** the party-size rule
- **Claim challenged:** a party size exactly at the limit is rejected
- **Evidence:** the boundary looks suspicious; `>` and `>=` are easily confused
- **Confidence:** unproven
- **Severity hint:** major
- **Would be settled by:** run `test_party_size_rule[12-expected1]`

### Surfaces
- **Swept:** acceptance criteria — criteria 1, 2, 4 and 5 hold by reading; criterion 3 is F1
- **Unattacked:** performance & scale — one rule, no I/O

### Verdicts
#### F1 — CONFIRMED major
- **Reason:** reproduced on a scratch copy: with `cutoff_minutes: 240` a slot 180 minutes out is accepted
#### F2 — CONFIRMED major
- **Reason:** the test passes with the config lookup deleted, so it cannot catch F1
#### F3 — REFUTED
- **Reason:** `test_party_size_rule` covers `party_size=12` and passes; the comparison is `>`
- **Reopens only if:** a failing test that submits a party of exactly 12 under the default config

### Remediation slices
- [ ] [major] F1 — a booking 180 minutes out is rejected with `CUTOFF_WINDOW` when the account's `cutoff_minutes` is 240
- [ ] [major] F2 — a test of the configured window fails when `check_cutoff` ignores config

### Verdict: NO-GO
- **Reason:** 2 confirmed majors open (F1, F2)

## Iteration 2

### Closed slices
- [x] F1 — verified by `test_window_length_reads_from_account_config`
- [x] F2 — verified by `test_window_length_reads_from_account_config`

### Smells
- **N1** — left: no third rule reads a config key yet

### Findings (unadjudicated)
#### F4
- **Target:** the party-size rule
- **Claim challenged:** a party size exactly at the limit is rejected
- **Evidence:** the `>` comparison at the limit still looks fragile
- **Confidence:** unproven
- **Severity hint:** major
- **Would be settled by:** run `test_party_size_rule[12-expected1]`
#### F5
- **Target:** `test_window_length_reads_from_account_config`
- **Claim challenged:** the replacement test catches a rule that ignores config
- **Evidence:** three of its four cases expect acceptance, which an ignored config could also produce
- **Confidence:** unproven
- **Severity hint:** minor
- **Would be settled by:** on a scratch copy, make `check_cutoff` use `DEFAULT_CUTOFF_MINUTES` and run the test

### Surfaces
- **Swept:** closed slices — F1's fix reads `cutoff_minutes` with the default; F2's replacement asserts on a slot between the default and the configured window
- **Swept:** acceptance criteria — read against the brief; nothing new found by reading
