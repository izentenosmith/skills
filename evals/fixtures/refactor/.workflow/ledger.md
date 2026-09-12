# Review and teardown notes — cutoff feature

## Previous pass

Smells found and deliberately not acted on:

- Duplicate Code at `check_party_size` and `check_venue_open` — each rule reads one
  config key with a default and coerces it. Extracting a shared helper for two call
  sites costs more indirection than it saves.
- Primitive Obsession — `venue_id` travels as a bare string through `submit`, the
  `Booking` aggregate, and the store. The identifier has no behavior of its own and
  nothing validates its shape.

Teardown findings from the previous pass:

- Party-size boundary off-by-one: checked and it did not hold. `test_party_size_rule`
  covers `party_size=12` explicitly and passes; the comparison is `>`, not `>=`.
