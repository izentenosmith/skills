# Reservations service

Bookings are submitted through `BookingService.submit` (the public seam). Constraint
rules live in `reservations/rules.py` and are run by the `Booking` aggregate.
Tests drive the service through the handler and use fakes for the store and config.

## Conventions
- Rules return a violation code string or `None`.
- Violations surface to callers as `Rejected(codes)`.
- Config is read per-account via `config_source.for_account`.
