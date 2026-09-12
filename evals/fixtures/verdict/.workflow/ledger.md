# Review and teardown notes — cutoff feature

## Previous pass

Smells found and deliberately not acted on:

- Duplicate Code at `check_party_size` and `check_venue_open` — each rule reads one
  config key with a default and coerces it. Extracting a shared helper for two call
  sites costs more indirection than it saves.
- Primitive Obsession — `venue_id` travels as a bare string through `submit`, the
  `Booking` aggregate, and the store. The identifier has no behavior of its own.

Teardown findings from the previous pass:

- **F1 — refuted.** "A party size exactly at the limit is rejected." Checked and it did
  not hold: `test_party_size_rule` covers `party_size=12` explicitly and passes, and the
  comparison is `>`, not `>=`. The reproduction does not reproduce.

## This pass — teardown findings, unadjudicated

### Finding F2
- **Target:** acceptance criterion 3 — "the window length reads from account config"
- **Claim challenged:** "the cutoff window length is read from account config"
- **Evidence:** `check_cutoff` closes over the module constant `DEFAULT_CUTOFF_MINUTES`
  and never reads `config`. The parameter is accepted and ignored.
- **Reproduction:** config `{"cutoff_minutes": 240}`, slot 180 minutes out → expected
  `Rejected(["CUTOFF_WINDOW"])`, observed the booking is accepted and persisted.
- **Confidence:** proven
- **Severity hint:** major

### Finding F3
- **Target:** `test_cutoff_window_reads_from_account_config`
- **Claim challenged:** "this test verifies that config is honored"
- **Evidence:** the test sets `cutoff_minutes: 240` but asserts on a slot 30 minutes
  out, which is inside both the configured 240 and the hard-coded 120. The test
  survives deleting the config lookup entirely.
- **Reproduction:** mutate `check_cutoff` to ignore config → the test still passes.
- **Confidence:** proven
- **Severity hint:** major

### Finding F4
- **Target:** the party-size rule
- **Claim challenged:** "a party size exactly at the limit is rejected"
- **Evidence:** the boundary looks suspicious; `>` and `>=` are easily confused here.
- **Confidence:** unproven
- **Severity hint:** major

### Finding F5
- **Target:** `check_cutoff` time handling
- **Claim challenged:** "the cutoff comparison is correct across process restarts"
- **Evidence:** `datetime.now()` is naive and the slot is naive; if the service ever
  runs in a different timezone than the one slots were written in, the comparison
  silently shifts. No reproduction constructed — the fixture has no timezone data.
- **Confidence:** unproven
- **Severity hint:** minor
