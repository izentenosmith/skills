# Build Plan: Enforce a cancellation cutoff on bookings

**Status:** approved
**Category:** enhancement
**Summary:** Reject bookings submitted within the cutoff window of the slot start.

**Current behavior:**
`BookingService.submit` accepts any well-formed booking that passes the party-size
and opening-hours rules. Nothing checks how close the slot is, so a booking can be
submitted right up against the slot start time.

**Desired behavior:**
A booking whose slot starts within the cutoff window is rejected with violation code
`CUTOFF_WINDOW`. The window length is read from account config (`cutoff_minutes`),
defaulting to 120. Bookings outside the window proceed as today.

**Key interfaces (test seams):**
- `BookingService.submit` — the public seam tests drive; raises `Rejected` carrying
  the violation codes
- `reservations.rules` — the cutoff rule joins `ACTIVE_RULES` alongside the existing
  party-size and opening-hours rules, returning a code or `None` like its peers
- Account config — a `cutoff_minutes` field with a default of 120, overridable per
  account through `config_source.for_account`

**Acceptance criteria** (ordered — first is the tracer-bullet candidate, each one a single red→green slice):
- [x] Tracer bullet: a booking whose slot starts inside the cutoff window is rejected
      with violation code `CUTOFF_WINDOW` — verified by `test_booking_inside_cutoff_window_is_rejected`
- [x] A booking whose slot is outside the window is accepted and persisted — verified by
      `test_booking_outside_cutoff_window_is_accepted_and_persisted`
- [x] The window length reads from account config, not a hard-coded default — verified by
      `test_window_length_reads_from_account_config`
- [x] Edge case: a slot exactly at the window edge is accepted (the boundary is
      exclusive — resolved in architect-deep-dive) — verified by `test_slot_exactly_at_window_edge_is_accepted`
- [x] Edge case: a booking that violates both the cutoff and the party-size rule
      surfaces both codes, not just the first — verified by `test_cutoff_and_party_size_violations_surface_both_codes`

**Test seams & prior art:**
- Drive tests through `BookingService.submit`, mirroring `tests/test_booking.py`
- Mirror the table-driven parametrized style of `test_party_size_rule` for the
  boundary cases
- Use the existing `FakeStore` / `FakeConfig` doubles; do not introduce new ones

**Deferred by design** (constraints, not work):
- Persistence engine — deferred behind the `store.save` interface; the rule never
  sees storage. Forced when we need cross-account queries.
- Notifying the venue of a rejected booking — deferred behind the service seam.

**Out of scope:**
- Administrator override of the cutoff window
- Changing the existing party-size or opening-hours rules
- Any change to how `Rejected` is surfaced to HTTP callers

## Revisions
- 2026-11-15 (tdd): `BookingService` takes a `clock` (default `datetime.now`) and every rule takes `now`, so the window tests run on a fixed clock — a test seam, no behaviour change.
