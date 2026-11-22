# Ledger — per-account party-size limit

## Iteration 1

### Smells
- **N1** Dispensables / Duplicate Code at the two fakes in `tests/test_booking.py` and `tests/acceptance/test_party_size.py` — noted: two copies, a shared fixture module would be a third file for two users
  - **Promote if:** a third test module needs the same fakes

### Findings (unadjudicated)
#### F1
- **Target:** acceptance criterion 2 — a party exactly at the limit is accepted
- **Claim challenged:** a party of exactly 12 is accepted
- **Evidence:** the comparison could be `>=`; the boundary is easy to get wrong
- **Breaking case:** party of 12 with the default limit → expected accepted
- **Confidence:** unproven
- **Would be settled by:** submitting a party of exactly 12 under the default limit
- **Severity hint:** major

### Surfaces
- **Swept:** acceptance criteria — all four hold through `BookingService.submit`
- **Swept:** security & permissions — no new entry point; the limit is read from the caller's own account config

### Verdicts
#### F1 — REFUTED
- **Reason:** `check_party_size` compares with `>`; `test_party_at_the_limit_is_accepted_and_persisted` submits 12 and passes
- **Reopens only if:** the comparison in `check_party_size` changes

### Remediation slices
- none

### Verdict: GO
- **Reason:** nothing open
