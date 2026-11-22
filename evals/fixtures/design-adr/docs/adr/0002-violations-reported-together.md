# 0002. Every rule violation is reported together, as codes on `Rejected`

**Status:** Accepted · 2026-02-23 · from the design review of Party-size limit

## Context
The booking widget and the partner API both show a refused booking's reasons. With one reason at a time, a guest fixed the party size, resubmitted, and only then learned the venue was closed at that hour.

## Decision
`Booking.validate` runs every active rule and returns every violation code. `BookingService.submit` raises a single `Rejected(codes)` carrying all of them. A rule returns a code string or `None`; it never raises. A new rule adds a new code.

## Options considered
- **Every code on one `Rejected`** — buys one round trip for the guest and one shape for every caller; costs running every rule even after one has failed; reversal: expensive — the partner API's contract lists the codes and partners switch on them.
- **The first violation only** — buys a cheaper check; rejected because guests fix one reason at a time.
- **An exception type per rule** — buys typed handling in Python callers; rejected because the partner API would need a new error shape for every rule.

## Consequences
Callers handle every refusal the same way, and a rule is added by adding a code. What would change our mind: a rule whose check is expensive enough that it must not run once a cheaper one has failed.
