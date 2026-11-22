# Build Plan: Per-account party-size limit

**Status:** approved
**Design:** `.workflow/designs/20261102-1010-party-size-limit.md`
**Category:** enhancement
**Summary:** Reject bookings whose party is larger than the account's limit, read from account config.

**Current behavior:**
`BookingService.submit` accepts a booking of any party size that passes the opening-hours rule.
Venues with small rooms take parties they cannot seat.

**Desired behavior:**
A booking whose party is larger than the account's limit is rejected with `PARTY_TOO_LARGE`.
The limit is read from account config (`max_party_size`), default 12; a party exactly at the
limit is accepted. Several violations surface together. Security trigger: did not fire.

**Key interfaces (test seams):**
- `BookingService.submit` — the public seam; raises `Rejected` carrying the violation codes
- `reservations.rules` — `check_party_size` joins `ACTIVE_RULES`, returning a code or `None`
- Account config — `max_party_size`, default 12, through `config_source.for_account`

**Acceptance criteria** (ordered — first is the tracer-bullet candidate, each one a single red→green slice):
- [x] Tracer bullet: a party of 13 is rejected with `PARTY_TOO_LARGE` — verified by `test_party_over_the_limit_is_rejected_with_party_too_large`
- [x] A party exactly at the limit is accepted and persisted — verified by `test_party_at_the_limit_is_accepted_and_persisted`
- [x] The limit reads from account config `max_party_size`, default 12 — verified by `test_limit_reads_from_account_config`
- [x] Edge case: a booking that breaks the party-size and the opening-hours rules surfaces both codes — verified by `test_party_size_and_opening_hours_surface_both_codes`

**Test seams & prior art:**
- Drive tests through `BookingService.submit`, mirroring `tests/test_booking.py` and its `FakeStore` / `FakeConfig`

**Parallel tracks:** none — one rule behind one seam

**Deferred by design** (constraints, not work — carried from architect-deep-dive):
- Per-venue limits — deferred behind account config; forced when a venue group asks for different rooms

**Out of scope:**
- Changing the opening-hours rule
- Splitting a large party across tables

**Ship checklist** (what no acceptance test can prove — rollout, compatibility, observability; tdd ticks what the build delivers, tyr-verdict reports what is still open):
- [x] Rollout: no flag; the default limit of 12 applies on deploy
- [x] Rollback: revert the deploy

**Base:** `9c41e07`

**Acceptance tests** (stage 3 — tdd is done when these pass):
- **Command:** `.venv/bin/python -m pytest tests/acceptance -q`
- [x] Criterion 1 (tracer bullet) → `tests/acceptance/test_party_size.py::test_party_over_the_limit_is_rejected_with_party_too_large`
- [x] Criterion 2 → `tests/acceptance/test_party_size.py::test_party_at_the_limit_is_accepted_and_persisted`
- [x] Criterion 3 → `tests/acceptance/test_party_size.py::test_limit_reads_from_account_config`
- [x] Criterion 4 (edge) → `tests/acceptance/test_party_size.py::test_party_size_and_opening_hours_surface_both_codes`

## Revisions
- 2026-11-03 — agent-brief: approved as written; Status set to approved.
- 2026-11-03 — acceptance-tests: added **Acceptance tests** — four criteria mapped to four tests in `tests/acceptance/`, all red on behavior.
- 2026-11-05 — tdd: built the four criteria red→green and ticked them, naming their tests.
