# Interface Design for Testability

Companion reference for the [tdd](SKILL.md) skill: how to shape an interface so a test can drive it with minimal setup and assert on observable output. Read this during the Planning step when you "design interfaces for testability."

A testable interface and a *good* interface are usually the same thing. If something is painful to test, the pain is signal — the design is leaking. These principles remove the pain at the source instead of papering over it with mocks.

## 1. Accept dependencies, don't create them

Pass collaborators in. Code that `new`s up its own dependencies (or reads globals/env directly) can only be exercised with the real thing.

```
# Testable — swap in a fake gateway from the test
function processOrder(order, paymentGateway): ...

# Hard to test — the gateway is welded in
function processOrder(order):
    gateway = new PaymentGateway()   # constructed internally
```

## 2. Return results, don't (only) produce side effects

A function that returns a value is verified by reading its output. A function that mutates hidden state forces the test to go *find* the effect.

```
# Testable — assert on the return value
function calculateDiscount(cart) -> Discount: ...

# Hard to test — must inspect cart afterward to see what happened
function applyDiscount(cart):          # returns nothing
    cart.total = cart.total - discount
```

Keep **commands** (do something, return nothing) and **queries** (return something, change nothing) separate. Mixed methods are the hardest to test.

## 3. Make inputs and outputs explicit and precise

The narrower the types, the fewer the edge cases a test has to cover. Push validation to the boundary so the core works with already-valid data ("parse, don't validate").

```
# Loose — every consumer must re-check; tests must cover the bad states
function ship(order)          # order.status might be anything, or absent

# Precise — illegal states are unrepresentable; no test needed for them
function ship(order: PaidOrder)   # only an already-paid order can be passed
```

## 4. Inject nondeterminism

Time, randomness, and generated IDs make tests flaky unless they're inputs. Pass them in (a `clock`, a `now`, an `idGenerator`) rather than reading the system clock or a global random source inside.

```
# Deterministic — the test controls "now"
function isExpired(token, now):
    return token.expiresAt < now
```

## 5. Small surface area

- Fewer methods = fewer tests needed.
- Fewer parameters = simpler test setup.
- A small interface is also a [deep module's](deep-modules.md) defining trait — design for both at once.

## Smell check: is the interface leaking?

If testing a unit requires any of these, the interface is leaking and should be reshaped — not mocked around:

- Reaching into a real database, file system, or network for something that isn't the boundary under test
- Freezing or monkey-patching the system clock / global state
- Setting environment variables to steer logic
- Asserting on *how* collaborators were called instead of *what* came out

Only genuine system boundaries should be substituted in a test — and for those, design for it deliberately ([mocking.md](mocking.md)).
