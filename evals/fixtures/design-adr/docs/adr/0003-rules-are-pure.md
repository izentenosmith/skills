# 0003. Booking rules are pure functions of the booking and its config

**Status:** Accepted · 2026-03-02 · from the design review of Opening hours

## Context
The opening-hours rule first read the venue's timetable from the store inside the rule, and its tests needed a database. The question was where the things a rule needs, beyond the booking itself, come from.

## Decision
A rule is a function of `(booking, config)` and nothing else: no store, no network, no clock. Anything else a rule needs is gathered by `BookingService.submit` and handed to the rules with the config.

## Options considered
- **Pure rules, inputs gathered by the service** — buys rules testable with a dict and a dataclass; costs the service knowing what each rule needs; reversal: moderate — each impure rule would need its own fakes.
- **Rules given services to call** — buys rules that fetch what they need; rejected because every rule test then needs fakes for the store and the clock.

## Consequences
Every rule is tested without the service, the store or the time of day. What would change our mind: a rule whose input is too large to gather for every submission.
