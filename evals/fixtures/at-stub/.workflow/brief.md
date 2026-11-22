# Build Plan: Check a booking without making it

**Category:** enhancement
**Status:** approved
**Summary:** Let a caller ask whether a booking would be accepted, and why not, without making it.

**Current behavior:**
The only way to learn whether a booking is acceptable is `BookingService.submit`, which
persists it when it passes. The booking widget wants to show "this table can't be
booked: party too large" while the guest is still choosing, before anything is saved,
and today it can only find out by booking.

**Desired behavior:**
A new `BookingService.check` runs the same rules `submit` runs, against the same
account config, and returns the violation codes, or an empty list when the booking
would be accepted. It never saves anything and never raises `Rejected`.

**Key interfaces (test seams):**
- `BookingService.check(account_id, venue_id, slot, party_size) -> list[str]` — new,
  public. Same arguments as `submit`; returns the violation codes, `[]` when the
  booking would be accepted. Does not raise `Rejected` and does not call `store.save`
- `BookingService.submit` — unchanged; the existing seam the tests already drive
- `Booking.validate` and `reservations.rules` — unchanged; `check` uses them exactly
  as `submit` does

**Acceptance criteria** (ordered — first is the tracer-bullet candidate, each one a single red→green slice):
- [ ] Tracer bullet: checking a booking that `submit` would accept returns an empty list
- [ ] Checking a booking that breaks a rule returns that rule's code (a party of 13
      returns `PARTY_TOO_LARGE`)
- [ ] The check reads the account's config, as `submit` does: an account whose
      `max_party_size` is 20 gets an empty list for a party of 13
- [ ] Edge case: a booking that breaks both the party-size and the opening-hours rule
      returns both codes, not just the first
- [ ] Edge case: a check never persists anything, even for a booking that would be
      accepted

**Test seams & prior art:**
- Drive tests through `BookingService`, mirroring `tests/test_booking.py`
- Use the existing `FakeStore` / `FakeConfig` doubles and the `slot()` helper; do not
  introduce new ones

**Deferred by design** (constraints, not work):
- Exposing the check over HTTP — deferred behind the service seam.
- Caching check results — deferred; every check runs the rules afresh.

**Out of scope:**
- Any change to `submit`, `Rejected` or the existing rules
- New rules (the cancellation cutoff is a separate brief)

## Revisions
- (none yet)
