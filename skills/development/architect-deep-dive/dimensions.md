# The design dimensions — read a dimension's entry when you open its question

> Companion to [architect-deep-dive](SKILL.md). The skill's termination gate names each dimension and its test; this file says what to resolve under each. The structural ones are worked out in `clean-architecture.md`, the security one in `security.md`.

## Policy vs. details

Which parts are business policy (the rules that would hold even in a manual version of this process) and which are details serving it — database, delivery mechanism, framework, wire format, external services. Policy gets resolved now; details get **deferred** behind a boundary. Note that the *data model* is policy while the *database* is a detail. See `clean-architecture.md`.

## Dependency direction & boundaries

Where the lines fall and which way the arrows cross them. Source-code dependencies must point inward, toward higher-level policy — never from policy out to a detail. For each proposed line, resolve:

- Is there a real **axis of change** — do the two sides change at different rates, for different reasons?
- What **form** does it take (none / facade / one-dimensional / full)?
- What **decoupling mode** (source, deployment, service)? Default to source-level and design so a service *could* be extracted later.

See `clean-architecture.md`.

## Scope boundaries

What is in scope and, just as importantly, out of scope. For every adjacent capability that *seems* related, ask whether it belongs here or is explicitly excluded. Nothing built later should be a surprise; nothing skipped should be a regression. Where two things look alike, resolve whether the duplication is **true** (changes always travel together — unify) or **accidental** (they'll diverge — keep them apart, and resist unifying them now).

## Data model

New/changed entities, relationships, ownership, and invariants. Migration of existing data. Entities carry the rules; they must not depend on the use cases that operate them.

## API / interface contracts

The seams the feature is exposed through — endpoints, service methods, component contracts, request/response shapes. Prefer existing seams; place any new seam as high as possible, where **highest = farthest from inputs and outputs**, with everything closer to IO plugging into it. Data crossing a boundary is a simple structure owned by the inner side — never a framework type, DB row, or entity passed outward.

## Failure modes & edge cases

Walk the unhappy paths one at a time: empty/missing inputs, boundary values, concurrent access, partial failures, and any state the happy path doesn't cover. Resolve the expected behavior for each — these become the edge-case acceptance criteria downstream.

## Security & permissions

The trigger is in the skill. When it fires, resolve each of these as its own question — the questions behind each are in `security.md`:

- **Assets and abuse.** What the change exposes or protects, and the abuse we refuse to allow, stated as a sentence a test can check. Ask of every new rule *which other feature defeats it*, and of every new role or delegation *can someone grant it to themselves*.
- **Trust boundaries and entry points.** Where untrusted data enters, and which module ends up serving more than one trust domain — that module is where validation goes missing.
- **Authorisation decision.** Who may perform each new operation, where the check is enforced (server-side, at the handler or below — never only in the UI), and how ownership/tenancy is checked on every object an ID names.
- **Domain primitives and sensitive values.** Which security-relevant values become validated, immutable types instead of raw strings and ints, and which sensitive fields must never reach a log, an exception message or a serialised response.
- **Failure and degraded modes.** What happens when a dependency is down — a fallback that skips a control is a vulnerability — and whether any input can make the work grow without bound.
- **Hand off when it's big.** A new trust boundary, a new data class, a new kind of user, or anything that moves money, grants identity, holds keys or can't be undone: run `threatmodel` on it and carry its security requirements back in as resolved decisions, rather than modelling threats round by round here. Where that skill is not installed, work the `security.md` questions here and say in the design file's Security section that the full threat model was not run.

## Scale & performance

Expected volumes, hot paths, query/lookup cost, caching, repeated-work and fan-out risks.

## Backwards-compatibility

Existing interface contracts callers depend on, data already persisted, isolation/tenancy invariants, and behavior current consumers rely on — what must NOT break.

## Observability

What needs logging, metrics, or tracing to operate and debug the feature.

## Testability

Can each resolved business rule be verified without the web server running, the database connected, or the framework booted? If not, the boundary is in the wrong place — move the line rather than planning to mock around it. Name the level each rule is testable at, so TDD doesn't drive policy through volatile UI. The test to apply: a rule you can only reach by booting the framework is a rule whose boundary is in the wrong place — the dependency points outward, from policy to a detail, and mocking around it hides the error rather than fixing it.

## Migration & rollout

Data backfill, feature-flagging, sequencing, and how the change ships safely.

## Decomposition (large efforts only)

How the effort splits into independently shippable increments, each of which can become its own brief → acceptance-tests → TDD → refactor-review → devils-advocate → tyr-verdict pass. Group into one increment what changes for the same reasons at the same times; split what changes for different reasons. Dependencies between increments must be acyclic and point toward the more stable side — never let a rigid, widely-depended-on piece depend on a volatile one. The component principles behind this are in `clean-architecture.md` (section "For decomposition").
