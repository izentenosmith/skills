# Findings that cross slices

## X-1: `slot()` in tests/test_booking.py builds slots from the wall clock
**Found by:** party-limits, tdd, 2026-11-13 · **Affects:** cutoff, hours-holidays · **Status:** routed
**Evidence:** `tests/test_booking.py` `slot()` uses `datetime.now()`; a test that puts a slot at a closed hour depends on nothing else, but one that needs a slot "soon" has to open the venue's hours in its config or it fails at night.
**Routed:** 2026-11-13 to cutoff and hours-holidays — open the hours in the config of any test that builds a slot close to now.
