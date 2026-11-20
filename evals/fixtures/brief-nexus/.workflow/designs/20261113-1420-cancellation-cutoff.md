# Design: Cancellation cutoff on bookings

**Status:** resolved
**Solving:** a booking can be submitted right up against its slot start, so venues get parties they cannot staff for.
**Why now:** three venue groups have made it a condition of renewing in January.
**Done looks like:** a booking too close to its slot is refused with a code the caller can show, and every account can set how close is too close.
**Calibration:** medium — a new rule inside the existing rule seam
**Questions:** ~8 to resolve (policy, data model, interfaces, failure modes, scope, back-compat, rollout, testability) — 6 resolved, 1 deferred, 2 carried open

## Decisions
- **Policy vs. details — where the rule lives:** a cutoff rule joins `ACTIVE_RULES` in `reservations.rules` and returns `CUTOFF_WINDOW` or `None`, like its peers — the rules module is already the one place a constraint is decided. Rejected: a check inside `BookingService.submit`, which would be a second place. [inferred]
- **Data model — the window length:** read from account config as `cutoff_minutes`, default 120 — venues differ and config is already per account. Rejected: a constant, which forces a deploy to change one venue group's window.
- **API / interface contracts — what the caller sees:** the existing `Rejected(codes)` carrying `CUTOFF_WINDOW` — callers already switch on codes. Rejected: a new exception type, which every caller would have to learn.
- **Failure modes — several violations at once:** every violated rule's code surfaces, the cutoff's among them — a caller fixes all of them in one round trip. Rejected: first violation only.
- **Scope — administrator override:** out of this slice (DEC-1).
- **Testability:** the rule is verified through `BookingService.submit` with the existing `FakeStore` / `FakeConfig` doubles — no framework, no storage.
- **Failure modes — a slot exactly at the window edge:** unresolved. Asked as question 6; the session was cut short before an answer was recorded.
- **Migration & rollout — bookings already stored inside the window:** unresolved when this was written (13 Nov): are they re-validated when the rule ships, or left alone?

## Security
- N/A — no trust boundary touched: no new entry point, and the window is read from the caller's own account config.

## Operability
- Backwards-compatibility: a booking outside the window behaves exactly as today; `Rejected` keeps its shape.
- Observability: N/A in this slice — rejections are already counted by code.
- Migration & rollout: no flag; the default window applies on deploy. Stored bookings: see the open decision above.

## Decomposition
- N/A — one increment

## Deferred
- Notifying the venue of a rejected booking — behind the service seam; forced when a venue asks to see refused demand.

## N/A
- Scale & performance — one comparison per submission.

## Records
- none
