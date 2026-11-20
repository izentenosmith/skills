# Design: Cancellation cutoff on bookings

**Status:** in progress
**Solving:** a booking can be submitted right up against its slot start, so venues get parties they cannot staff for. Nothing in `BookingService.submit` looks at how close the slot is.
**Why now:** three venue groups have made it a condition of renewing in January.
**Done looks like:** a booking too close to its slot is refused with a code the caller can show, and how close is too close is a setting, not a deploy.
**Calibration:** medium — a new rule inside the existing rule seam
**Questions:** ~7 to resolve (policy vs. details, data model, interface contracts, failure modes, scope, backwards-compatibility, migration & rollout) — 0 resolved, 0 deferred

## Decisions
- (none yet)

## Security
- (not reached)

## Operability
- (not reached)

## Decomposition
- N/A — one increment

## Deferred
- (none yet)

## N/A
- Scale & performance — one comparison per submission.
- Observability — rejections are already counted by code.

## Records
- none
