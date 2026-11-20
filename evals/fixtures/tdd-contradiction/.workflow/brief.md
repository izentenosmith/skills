# Build Plan: Enforce a cancellation cutoff on bookings

**Status:** approved
**Design:** —
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
- [ ] Tracer bullet: a booking whose slot starts inside the cutoff window is rejected
      with violation code `CUTOFF_WINDOW`
- [ ] A booking whose slot is outside the window is accepted and persisted
- [ ] The window length reads from account config, not a hard-coded default
- [ ] Edge case: a slot exactly at the window edge is accepted (the boundary is
      exclusive)
- [ ] Edge case: a booking that violates both the cutoff and the party-size rule
      surfaces both codes, not just the first
- [ ] Edge case: a booking inside the cutoff window is rejected with `CUTOFF_WINDOW`
      alone: once the cutoff applies, no other rule's code is reported (a guest who is
      too late is not also told the venue is closed)

**Test seams & prior art:**
- Drive tests through `BookingService.submit`, mirroring `tests/test_booking.py`
- Mirror the table-driven parametrized style of `test_party_size_rule` for the
  boundary cases
- Use the existing `FakeStore` / `FakeConfig` doubles; do not introduce new ones

**Acceptance tests** (stage 3 — tdd is done when these pass):
- **Command:** `.venv/bin/python -m pytest tests/acceptance -q`
- [ ] Criterion 1 (tracer bullet) → `tests/acceptance/test_cutoff.py::test_booking_inside_cutoff_window_is_rejected_with_cutoff_window`
- [ ] Criterion 2 → `tests/acceptance/test_cutoff.py::test_booking_outside_window_is_accepted_and_persisted`
- [ ] Criterion 3 → `tests/acceptance/test_cutoff.py::test_window_length_reads_from_account_config`
- [ ] Criterion 4 (edge) → `tests/acceptance/test_cutoff.py::test_slot_at_window_edge_is_accepted`
- [ ] Criterion 5 (edge) → `tests/acceptance/test_cutoff.py::test_cutoff_and_party_size_violations_surface_both_codes`
- [ ] Criterion 6 (edge) → `tests/acceptance/test_cutoff.py::test_cutoff_is_reported_alone`

**Deferred by design** (constraints, not work):
- Persistence engine — deferred behind the `store.save` interface; the rule never
  sees storage. Forced when we need cross-account queries.
- Notifying the venue of a rejected booking — deferred behind the service seam.

**Out of scope:**
- Administrator override of the cutoff window
- Changing the existing party-size or opening-hours rules
- Any change to how `Rejected` is surfaced to HTTP callers

## Revisions
- 2026-11-10 — acceptance-tests: added **Acceptance tests** — six criteria mapped to six tests in
  `tests/acceptance/`, all red on behavior (nothing is rejected for timing yet).
- 2026-11-11 — approved as written; Status set to approved.
