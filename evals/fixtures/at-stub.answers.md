Answer key for eval 65, which runs `acceptance-tests` on the `at-stub/` fixture. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# at-stub — `acceptance-tests` when the public interface does not exist yet (eval 65)

The fixture is the reservations service of the `tdd` fixture with a different, approved brief: a new public method `BookingService.check(account_id, venue_id, slot, party_size) -> list[str]` that runs the rules `submit` runs, against the account's config, and returns the violation codes (`[]` when the booking would be accepted) without saving and without raising. The method does not exist. The code is unchanged from `tdd`; the pre-existing suite is 4 passed.

The rule under test is SKILL.md Step 3, "A failure to load is not red": *where the public interface itself doesn't exist yet (a new library function, a new class), declare it — the signature the brief's Key interfaces name, failing with a not-implemented error — so the tests reach it and fail on behavior. That stub is the only production code this stage writes.* Eval 27 cannot exercise it: there `submit` and `Rejected` already exist and nothing needs declaring (its trap 6).

| # | Planted | Where | Catches a run that… |
|---|---|---|---|
| 1 | **The interface is missing.** Calling `svc.check(...)` fails with `AttributeError: 'BookingService' object has no attribute 'check'` | `reservations/api.py`, brief Key interfaces | writes the tests and reports them red. They fail, but on a missing attribute, which proves nothing about the behavior: a bare agent's usual answer |
| 2 | **The implementation is two lines.** `Booking(...)` then `validate(config)` | `reservations/api.py` | implements `check` "while it's there", so the tests pass now |
| 3 | **A stub that answers.** `return []` declares the method, but the tracer and never-saves criteria then pass today | the stub's body | declares a stub that returns instead of raising `NotImplementedError` |
| 4 | **Never persists, for an acceptable booking.** A check that saves only when nothing is violated is caught only by checking a booking that would be accepted | brief criterion 5 | asserts nothing was saved after a *rejected* check, which a saving `check` also passes |
| 5 | **Both codes.** `validate` already returns every code; a check that keeps the first is the mutant | brief criterion 4 | tests the two-code case through `Booking.validate` (green today, and an internal) |
| 6 | **The account's config.** `max_party_size` 20 lets a party of 13 through | brief criterion 3 | tests the criterion with an account whose config changes nothing for the party it submits, so a check that ignores the config passes too |

**What a correct run does.** It states the Standard tier, declares `BookingService.check` in `reservations/api.py` with the brief's arguments and a body that only raises `NotImplementedError`, and writes five tests through `BookingService` reusing `FakeStore`, `FakeConfig` and `slot()`. All five fail on `NotImplementedError`; the four pre-existing tests stay green; nothing else in `reservations/` changes. It adds an **Acceptance tests** section to the brief whose **Command:** runs only the new tests, maps each criterion once, logs a Revisions entry, and hands off to tdd.

**How it is graded (executed, like eval 27).** The new tests are found by comparing pytest's collection with the fixture's, then run three ways, at local noon:

- On the run's own code: every new test fails, on `NotImplementedError`, an assertion or `Rejected`. `AttributeError`, an import error or a collection error does not count.
- With a correct `check` laid over `reservations/api.py` (the fixture's file plus the method): every new test passes.
- With each of three mutant `check`s: one that saves an acceptable booking, one that keeps only the first code, one that validates against `{}` instead of the account's config. Some test green on the reference must fail each. These are tagged capability.

Static checks: `BookingService.check` exists with arguments `self, account_id, venue_id, slot, party_size` and a body (docstring aside) that is a single `raise NotImplementedError…` (delta); `api.py` minus that method is the fixture's AST, `booking.py`, `rules.py` and `__init__.py` are untouched, and a probe calling `check` for a party of 13 does not get `PARTY_TOO_LARGE` back (delta, the safety invariant); no import of `reservations.rules` or `reservations.booking` and no `.validate` in the tests (AST); the doubles reused; the command collects exactly the new tests; each of the five criteria mapped once to a test the run added; a Revisions entry; the handoff to tdd.
