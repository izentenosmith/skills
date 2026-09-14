# Writing Good Tests

Companion reference for the [tdd](SKILL.md) skill: how to tell whether a test verifies **behavior** (good) or **structure** (bad). Read this during the Planning step before writing any test.

## The 4 Pillars of Test Quality

When writing or reviewing tests, evaluate them against the four foundational pillars of testing software engineering:

1. **Protection against regressions:** The test accurately catches bugs when behavior breaks.
2. **Resistance to refactoring:** The test continues to pass if the internal implementation changes but the observable behavior remains identical.
3. **Fast feedback:** The test runs quickly, allowing tight development loops.
4. **Maintainability:** The test is easy to read, understand, and update.

A test that sacrifices pillar 2 (resistance to refactoring) to gain pillar 1 is the classic trap: it couples to implementation and breaks on every refactor. Behavior-driven tests maximize all four at once.

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of internal parts.

```
# GOOD: Tests observable behavior
TEST "user can checkout with valid cart":
    cart = createCart()
    cart.add(product)
    result = checkout(cart, paymentMethod)
    assert result.status == "confirmed"
```

Characteristics:

- Tests behavior users/callers care about
- Uses public API only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```
# BAD: Tests implementation details
TEST "checkout calls paymentService.process":
    mockPayment = substitute(paymentService)
    checkout(cart, payment)
    assert mockPayment.process was called with cart.total
```

Red flags:

- Mocking internal collaborators
- Testing private methods
- Asserting on call counts/order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT
- Verifying through external means instead of interface

```
# BAD: Bypasses interface to verify
TEST "createUser saves to database":
    createUser({ name: "Alice" })
    row = <direct datastore lookup for name "Alice">
    assert row exists

# GOOD: Verifies through interface
TEST "createUser makes user retrievable":
    user = createUser({ name: "Alice" })
    retrieved = getUser(user.id)
    assert retrieved.name == "Alice"
```
