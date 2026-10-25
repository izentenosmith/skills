Answer key for eval 27, which runs `acceptance-tests` on the shared `tdd/` fixture. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# tdd — `acceptance-tests` on the cutoff build plan (eval 27)

The fixture is the reservations service with `.workflow/brief.md`: five acceptance criteria for a cancellation cutoff that does not exist yet. Nothing was added to the fixture for this eval. Its traps are in what the brief asks for and in what the code already does.

| # | Planted | Where | Catches a run that… |
|---|---|---|---|
| 1 | **Criteria 2 and 4 already hold today.** With no cutoff, every slot is accepted, so "outside the window is accepted" and "exactly at the edge is accepted" pass on the unimplemented code | brief criteria 2, 4; `rules.py` | writes acceptance-only tests that are green now and would stay green with the feature deleted. The skill says a passing test is a finding, and its stopping rule says none passes. The right test first shows the window in force (a slot just inside is rejected), then the acceptance |
| 2 | **The vacuous config test.** The default window is 120 minutes. A config test with `cutoff_minutes: 240` and a slot 30 minutes out passes whether or not the config is read. This is the test the `teardown` fixture plants | brief criterion 3 | proves criterion 3 with a slot inside both windows. The right test puts the slot between the default and the configured window (240 and 180 out, or 60 and 90 out) |
| 3 | **The edge on a moving clock.** Rules read `datetime.now()` and there is no clock seam | brief criterion 4 | gives the edge a minute of slack, which tests criterion 2 again. Within a few seconds of the edge is testable from outside. A test that builds the slot at exactly `now + 120 min` is accepted by the grader's reference, which reads `now` to the second |
| 4 | **Both codes.** `validate` already collects every violation, so criterion 5 needs only the cutoff to exist | brief criterion 5 | asserts only `"CUTOFF_WINDOW" in codes`, or any failure |
| 5 | **Internals named in the brief.** Key interfaces mention `reservations.rules` and `ACTIVE_RULES` | brief, Key interfaces | unit-tests `check_cutoff` or `Booking.validate` directly. Those fail on `AttributeError` today (red for the wrong reason) and are not black-box |
| 6 | **Nothing to declare.** `BookingService.submit` and `Rejected` already exist | `reservations/api.py` | invents a public name (`CutoffPolicy`, a `CUTOFF_WINDOW` constant) and fails on `ImportError`. The only production code this stage may write is a declared stub, and none is needed here |
| 7 | **The prior art.** `FakeStore` and `FakeConfig` in `tests/test_booking.py`. The brief says to reuse them | `tests/test_booking.py` | introduces new doubles or mocks |
| 8 | **Opening hours vs `datetime.now()`.** The venue is open 11:00 to 23:00. A slot built from now collides with it at night | `rules.check_venue_open` | is red for `VENUE_CLOSED`, not for the cutoff, when run at night. **Not graded:** every pytest the grader starts runs at local noon. A careful run opens every hour in `FakeConfig` |

**What a correct run does.** It states the Standard tier and writes five tests through `BookingService.submit`. They reuse the fakes and import only `reservations.api` (plus the fakes). All five are red on behavior: `DID NOT RAISE Rejected`, or `['PARTY_TOO_LARGE'] != [...]`. The four pre-existing tests stay green and no cutoff rule is written. The run then adds an **Acceptance tests** section to the brief. Its **Command:** runs only the new tests, and its mapping lists each criterion exactly once, by test id or as not acceptance-testable with a reason. It logs a Revisions entry and hands off to tdd.

**How it is graded (executed).** The grader identifies the tests the run added by comparing them with the fixture's pytest collection, then runs them three ways:

- On the run's own code, they must all fail, and fail on an assertion, `DID NOT RAISE` or `Rejected`. A collection or import error does not count.
- With a correct cutoff rule laid over the repo, they must all pass. The reference reads `cutoff_minutes` with a default of 120 and treats the boundary as exclusive. It is appended to `ACTIVE_RULES`, or put first if the tests expect that order.
- With each of three mutants laid over the repo, some test that passed on the reference must fail. The mutants are a hard-coded 120-minute window, a whole-minute inclusive boundary, and a `validate` that returns only the first violation.

Every pytest runs with `TZ` set so that local time is noon.
