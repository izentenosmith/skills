# 0001. Booking-rule settings are configured per account

**Status:** Accepted · 2026-02-09 · from the design review of Party-size limit

## Context
The party-size rule needed a limit that differs between customers, and opening hours were about to follow. Settings could live on the account (the venue group that holds the contract) or on each venue, with the account as a fallback. Every account at the time ran all of its venues on the same values.

## Decision
Every setting a booking rule reads comes from the account's config, read once per submission through `config_source.for_account(account_id)`. Venues carry no rule settings of their own, and no rule looks a venue up.

## Options considered
- **Per account** — buys one lookup per submission, one place support edits a value, and no precedence rule; costs an account whose venues differ having to settle on one value; reversal: expensive — every rule, the config source and the support tooling read settings by account.
- **Per venue, falling back to the account** — buys venue-level variation; costs a second lookup on every submission, a precedence rule every reader must know, and a venue settings store with no owner; rejected because no account had asked for venue-level values.

## Consequences
Rules stay simple and the config source has one key. A venue-level value means superseding this record, not adding a lookup inside one rule. What would change our mind: an account whose venues need different values for the same rule.
