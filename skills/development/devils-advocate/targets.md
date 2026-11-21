# Attack-surface targets — read each entry as you attack it

> Companion to [devils-advocate](SKILL.md). The skill lists the ten targets; this file says what to trace on each. Everything here is done by reading, never by running. Source cited: TAOSSA = Dowd, McDonald & Schuh, *The Art of Software Security Assessment* (Addison-Wesley), printed page numbers.

## Acceptance criteria

For each criterion in the brief: does the behavior actually hold, or does its test pass vacuously — asserting nothing meaningful, asserting on setup, or asserting a value that would be true even if the feature were deleted? That includes the **acceptance tests** the brief maps to each criterion: were any edited since stage 3 wrote them, and does each still fail if its criterion breaks?

## Test integrity

Would each test actually fail if the behavior broke? Mentally mutate the implementation (invert a condition, drop a branch, return a constant) — does a test go red? A test no mutation can break tests nothing.

## The bar itself

An agent that hits a red check takes the cheapest road to green, and the cheapest road is often to move the check. Read the diff for the bar getting lower rather than the code getting better — every one of these is visible in the diff alone:

- **A test got easier.** A skip, `xfail`, `.only` or disabled marker added; a test or test file deleted; assertions removed from a test that stayed, or loosened (an exact value to a truthiness check, a specific error to any error).
- **A checker got silenced.** A new suppression — `noqa`, `type: ignore`, `eslint-disable`, `@ts-ignore`, `@SuppressWarnings`, `nosemgrep`, `pragma: no cover`, `istanbul ignore`, a secret-scanner allow — or a rule switched off in the linter, type-checker or scanner configuration.
- **A threshold moved.** A coverage floor, a size or time budget, a severity level, or a CI step removed, made optional or allowed to fail.
- **An acceptance test changed after stage 3 wrote it** with no matching entry in the brief's **Revisions**. An acceptance test changes only through the brief.
- **Work left unfinished behind a green bar.** A stub that raises not-implemented on a path a criterion needs, an empty `catch`/`except` that turns a failure into silence, a `TODO` where the handling should be.

How each one found is weighed — a finding, unless the brief explains it, unless that explanation arrived in the same change — is in the skill, beside the target.

## Listed edge cases

The unhappy paths the brief called out — are they genuinely handled, or stubbed/short-circuited to make a test pass?

## Unlisted unhappy paths

Empty/missing/null input, boundary and off-by-one values, concurrent access, ordering assumptions, partial failure and rollback, duplicate/retry.

## Contracts & invariants

Can a documented invariant be violated through the public interface? Did the change break a contract an existing caller depends on (backwards-compatibility)?

## Security & permissions

On a change the brief marks as security-triggered, or one that adds an entry point or touches identity, money, secrets or personal data, split this into its own delegates — one per line below — rather than one sweep. Read it the way an attacker reads it: infer what the developer intended, then construct the input they didn't anticipate (TAOSSA pp. 20–21, 92).

- **Authorisation bypass.** Every path to each protected operation — other handlers, other HTTP methods, other API versions, batch and export endpoints — and every ID the request carries (path, query, body, nested objects, arrays) checked for ownership and tenancy. A role or delegation someone can grant themselves.
- **Untrusted data source-to-sink.** Each input traced to where it is used — query, command, template, file path, redirect, outbound request, header — including **stored and second-order paths**: data validated where it entered and read back later by code that assumes it is clean (TAOSSA pp. 18–19).
- **Assumptions at interfaces.** "Only our client calls this", "the gateway already validated it", "the UI hides that button" — each is a candidate defect; find the caller that breaks it.
- **Leaks.** Secrets or personal fields in logs, exception messages, error responses, serialised entities or analytics; refusals that reveal whether an object or account exists. Cite the location and the kind of secret; never copy the value itself into the ledger or your response.
- **Failure and degraded modes.** A dependency down, a timeout, a partial write: does the code fall back to a weaker check, a default role, or "allow"? Input that makes work grow without bound.

A passing suite does not clear any of these: black-box tests miss paths that only a specific input reaches (TAOSSA pp. 11–12). The evidence is the path, the breaking case and, where it can only be settled by running, the exact request to send — which is Tyr's to make, against a test environment only.

## Error handling

Swallowed errors, errors surfaced at the wrong layer or with the wrong shape, failures that leave state half-written.

## Coupling & state leakage

Did the refactor introduce hidden shared state, order-dependence between tests, or a leak that only bites under real load?

## Performance & scale

Repeated work, fan-out, unbounded growth, or a hot path that is fine on fixture data and falls over at real volume.
