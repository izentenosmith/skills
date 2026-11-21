# Design: Cancellation cutoff on bookings

**Status:** resolved
**Solving:** a booking can be submitted right up against its slot start, so venues get parties they cannot staff for.
**Why now:** three venue groups have made it a condition of renewing in January.
**Done looks like:** a booking too close to its slot is refused with a code the caller can show, and every account can set how close is too close.
**Calibration:** medium — a new rule inside the existing rule seam
**Questions:** ~8 to resolve (policy, data model, interfaces, failure modes, scope, back-compat, rollout, testability) — 7 resolved, 1 deferred

## Decisions
- **Policy vs. details — where the rule lives:** a cutoff rule joins `ACTIVE_RULES` in `reservations.rules` and returns `CUTOFF_WINDOW` or `None`, like its peers — the rules module is already the one place a constraint is decided. Rejected: a check inside `BookingService.submit`, which would be a second place. [inferred]
- **Data model — the window length:** read from account config as `cutoff_minutes`, default 120 — venues differ and config is already per account. Rejected: a constant, which forces a deploy to change one venue group's window.
- **API / interface contracts — what the caller sees:** the existing `Rejected(codes)` carrying `CUTOFF_WINDOW` — callers already switch on codes. Rejected: a new exception type, which every caller would have to learn.
- **Failure modes — several violations at once:** every violated rule's code surfaces, the cutoff's among them — a caller fixes all of them in one round trip. Rejected: first violation only.
- **Failure modes — a slot exactly at the window edge:** exclusive — a slot exactly `cutoff_minutes` from now is accepted, so "two hours" means what the venue's sign says. Rejected: inclusive.
- **Scope — administrator override:** out of this slice; venues have not asked for it.
- **Migration & rollout — bookings already stored inside the window:** left alone; the rule applies to new submissions only. Rejected: re-validating stored bookings, which would cancel parties already confirmed.
- **Testability:** the rule is verified through `BookingService.submit` with the existing `FakeStore` / `FakeConfig` doubles — no framework, no storage.

## Security
- N/A — no trust boundary touched: no new entry point, and the window is read from the caller's own account config.

## Operability
- Backwards-compatibility: a booking outside the window behaves exactly as today; `Rejected` keeps its shape.
- Observability: N/A in this slice — rejections are already counted by code.
- Migration & rollout: no flag; the default window applies on deploy; stored bookings are not re-validated.

## Decomposition
- N/A — one increment

## Deferred
- Notifying the venue of a rejected booking — behind the service seam; forced when a venue asks to see refused demand.

## N/A
- Scale & performance — one comparison per submission.

## Records
- none
