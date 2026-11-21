# Security in the design dialogue

> The questions behind the **Security & permissions** dimension, for when the security trigger
> fires. They are asked in the same rounds and the same four-section format as every other question,
> interleaved with the rest of the tree — not bolted on at the end. Sources: Bergh Johnsson &
> Deogun, *Secure by Design — Ideas and Techniques* (SecAppDev slide deck; cited by slide);
> Dowd, McDonald & Schuh, *The Art of Software Security Assessment* (TAOSSA; cited by printed page);
> Anderson, *Security Engineering* 3e (SE; cited by section).

## Contents

- [The premise: security is a property of the design, not a feature](#the-premise-security-is-a-property-of-the-design-not-a-feature)
- [The trigger](#the-trigger)
- [The questions](#the-questions)
- [What the brief needs from you](#what-the-brief-needs-from-you)

## The premise: security is a property of the design, not a feature

Most vulnerabilities are ordinary bugs in places where the bug has security consequences, and the
design decisions that prevent bugs prevent them (Secure by Design, slides 6–10). Treating security as
a separate feature, added late by someone else, is the pattern that produces them. That is why these
questions live here, inside the design review, and why the answers become ordinary acceptance
criteria downstream rather than a separate security pass.

A vulnerability is not always a bug: a program can do exactly what its spec says and still let
someone do something the security policy forbids (TAOSSA pp. 4–5). So the question is never only
"does it work?" but "what does it let someone do?"

## The trigger

Ask the security questions when the trigger fires. Its four conditions are listed once, in the
**Security & permissions** dimension of [SKILL.md](SKILL.md#termination-gate--design-dimension-checklist), so the two files cannot drift apart.

None of them? Mark the dimension **N/A — no trust boundary touched**, with that reason, and move on.
That is a legitimate end state, and the cost of these questions on a change that doesn't need them
is real.

## The questions

### 1. Assets and abuse — what must never happen

- What does this change expose or protect? Name the asset (an account balance, another tenant's
  records, a reset token, the ability to approve), not the component.
- **The abuse case** — the thing a hostile user, a curious insider or a compromised client must not
  be able to do — written as one sentence a test can check: *"a user cannot read an invoice that
  belongs to another account, even with its ID"*.
- **Business-rule circumvention.** For each rule the change adds, which *other* feature reaches the
  same outcome without passing the rule? TAOSSA's examples: draining one account below zero to force
  transfers out of an account that limits withdrawals; a "delegate my approvals" feature that lets
  users appoint themselves and approve their own expenses (pp. 26–27, 39). Ask it of every new role
  and delegation: *can someone grant it to themselves?*

### 2. Trust boundaries and entry points — where untrusted data comes in

- Draw the entry points on the same dependency picture the boundaries question uses. Each one is a
  place where data stops being trusted.
- **Trust boundaries tend to be module boundaries** — and a module that serves callers from more than
  one trust domain is a cohesion failure with a security cost: the check that one caller needs is the
  check the other caller skips (TAOSSA pp. 28, 32–33). Resolve which side of the line each module sits.
- **Transitive trust.** If this service trusts the one that calls it, and that one trusts the network,
  this one trusts the network (TAOSSA pp. 19–20; SE §21.1). Say what each hop verifies.
- **Second-order paths.** Data validated where it enters may be read back later — from the database,
  a queue, a report — by code that assumes it is clean (TAOSSA pp. 18–19). Name the readers.

### 3. Authorisation — who may do it, and where that is enforced

- Per new operation: the actors allowed, the condition (role, ownership, tenancy, state), and the
  **layer that enforces it** — at the handler or in the domain, server-side, on every path to the
  operation. A check on the menu but not on the handler is no check (TAOSSA pp. 38–39).
- **Every ID in a request names an object someone may not own.** Decide how ownership is checked:
  in the query's own `WHERE`, through a policy object, or through an indirect reference. The default
  is ownership in the query, because it cannot be forgotten by a later caller.
- **Deny by default.** A new route or field is inaccessible until a rule grants it.
- **Separation of duty.** For irreversible or high-value actions: does one person's approval suffice?
  (SE §12.2.4; §15.2.2.)

### 4. Domain primitives and sensitive values — make invalid states unrepresentable

- **Domain primitives.** Which security-relevant values become small, immutable, self-validating
  types — `AccountId`, `Money`, `EmailAddress`, `RelativePath` — that cannot be constructed invalid,
  instead of raw `String`/`int`/`double` passed across layers? Validation then happens once, at
  construction, and every later function that takes the type gets a valid value for free (Secure by
  Design, slides 15–18, 23). This is a data-model decision: resolve it with the data model.
- **Conceptual wholes over ambiguous parameter lists.** `pay(double, int)` lets a caller swap the
  amount and the recipient, or lose the currency; `pay(Money, Recipient)` does not (slide 19).
- **Invariants live in the type.** A rule that the operation must hold — currencies match, a range is
  ordered — is checked by the type's own method, not by every caller (slide 20).
- **Sensitive values.** Which fields must never reach a log line, an exception message, a
  `toString`, a serialised response or an analytics event? Those get an explicit type that masks
  itself and refuses serialisation — the *read-once* pattern for secrets that should be consumed once
  (slides 30–35). The leak this prevents is the field someone adds later to an entity that is already
  logged whole (slides 31–33).
- **Logging as a designed interface.** Security-relevant events (sign-in, permission change, approval,
  export) go through a typed, domain-named logging API rather than free text, so what gets logged is
  a design decision and user data is encoded on the way (slides 39–42).

### 5. Failure, degraded modes and cost

- **On a security failure: stop, log, say little.** Recovery logic designed for usability — retry
  with a weaker check, fall back to a default role — plays into an attacker's hands (TAOSSA
  pp. 35–36; SE §27.3.6).
- **Degraded modes.** When the dependency that enforces a control is down, what happens? A
  point-of-sale terminal that spools card data locally while the server is unreachable has made
  availability a confidentiality problem (TAOSSA pp. 48–49; SE §7.3.4). Decide fail-open or
  fail-closed per control, explicitly.
- **Algorithmic cost reachable from input.** A list the attacker sizes, a regex the attacker feeds, a
  sort over an unbounded set: the key algorithm predicts the denial of service (TAOSSA p. 27).

### 6. When to stop asking here and run threatmodel

The questions above cover a change inside a system whose threat model already exists (or doesn't
need to). Hand off to `threatmodel` when the change brings:

- a new trust boundary or a new external party;
- a new data class (personal, payment, health, credentials);
- a new kind of user, especially an anonymous or third-party one;
- anything that moves money, grants identity, holds keys, or cannot be undone.

Its output — assets, adversaries, the hazard × mechanism matrix, security requirements — comes back
as **resolved decisions** for this dialogue, marked with their source, and the requirements become
acceptance criteria in the brief.

## What the brief needs from you

The handoff carries a **security block**: the abuse cases (each one sentence), the authorisation rule
per operation with its enforcing layer, the domain primitives and their validity rules, the values
that must never be logged or echoed, and the fail-open/fail-closed decision per control.
`agent-brief` turns each into an acceptance criterion; a security decision
that never becomes a criterion never becomes a test.
