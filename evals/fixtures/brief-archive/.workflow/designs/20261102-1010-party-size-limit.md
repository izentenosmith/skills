# Design: Per-account party-size limit

**Status:** resolved
**Solving:** venues with small rooms take parties they cannot seat.
**Why now:** two venue groups turned away parties of fourteen last month after accepting the booking.
**Done looks like:** a booking above the account's limit is refused with a code the caller can show.
**Calibration:** small — one rule inside the existing rule seam
**Questions:** ~5 to resolve (policy, data model, interfaces, failure modes, scope) — 5 resolved

## Decisions
- **Policy vs. details — where the rule lives:** `check_party_size` joins `ACTIVE_RULES` in `reservations.rules` and returns `PARTY_TOO_LARGE` or `None`. Rejected: a check in `BookingService.submit`. [inferred]
- **Data model — the limit:** account config `max_party_size`, default 12 — accounts differ. Rejected: a constant.
- **API / interface contracts — what the caller sees:** `Rejected(codes)` carrying `PARTY_TOO_LARGE`. Rejected: a new exception type.
- **Failure modes — a party exactly at the limit:** accepted; the limit is the largest party allowed.
- **Scope — splitting a party across tables:** out.

## Security
- N/A — no trust boundary touched.

## Operability
- Backwards-compatibility: a party within the limit behaves exactly as today.
- Observability: N/A — rejections are already counted by code.
- Migration & rollout: no flag; the default applies on deploy.

## Decomposition
- N/A — one increment

## Deferred
- Per-venue limits — behind account config; forced when a venue group asks for different rooms.

## Records
- none
