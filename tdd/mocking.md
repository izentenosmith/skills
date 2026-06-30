# When to Mock

Companion reference for the [tdd](SKILL.md) skill: what to substitute in a test and what to leave real. Over-mocking is the most common way good intentions produce [bad tests](good-tests.md) — tests that pass when the system is broken and break when it isn't.

## The one rule: mock only at the system boundary

Substitute a dependency **only** when it crosses out of your system. A dependency qualifies if it is:

- **Out of process** — external APIs (payment, email), third-party SDKs, message brokers
- **Nondeterministic** — time, randomness, generated IDs (better: inject them — see [interface-design.md](interface-design.md))
- **Slow or unavailable in tests** — sometimes the network or file system
- **Not under your control** — code you can't change and shouldn't depend on the internals of

Everything else is your own code. Exercise it for real.

| Mock these (boundaries) | Never mock these (your system) |
|---|---|
| External / third-party APIs | Your own classes and modules |
| Time, randomness | Internal collaborators |
| Message brokers, email/SMS | Domain logic, value objects |
| File system / network *(sometimes)* | Anything you wrote and control |
| Databases *(prefer a real test DB)* | Pure functions |

## Prefer real over fake over mock

Reach for the least-substituted option that keeps the test fast and deterministic:

1. **Real** — use the actual code (a real test/in-memory DB, a temp directory). Highest confidence.
2. **Fake** — a working lightweight implementation (in-memory repository, stub gateway that records nothing). Good for boundaries you own the contract for.
3. **Mock** — a stand-in you configure per test. Last resort; the most coupling.

A test against a **real database** catches schema, query, and mapping bugs a mocked repository never will. Mock the DB only when a real one is genuinely impractical.

## Never assert on interactions

The deepest mocking trap: verifying *that a collaborator was called* (call counts, argument order, "was `process()` invoked?"). That couples the test to implementation — rename or reorder internals and it breaks though behavior is identical.

```typescript
// BAD: tests HOW it works — breaks on refactor
expect(paymentService.process).toHaveBeenCalledWith(cart.total);

// GOOD: tests WHAT happened — survives refactor
const result = await checkout(cart, fakePayment);
expect(result.status).toBe("confirmed");
```

Verify **state and observable output** (what the caller can see), not the conversation between internals. See the red flags in [good-tests.md](good-tests.md).

## Designing for mockability

When you *do* substitute a boundary, design it to be substituted cleanly.

**1. Use dependency injection.** Pass the boundary in rather than constructing it inside.

```typescript
// Easy to substitute
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard — the client and its config are welded in
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. Prefer SDK-style interfaces over a generic fetcher.** One named function per operation, not one do-everything method with conditional logic.

```typescript
// GOOD: each operation is independently substitutable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: substituting requires conditional logic inside the fake
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The SDK approach means each fake returns one specific shape, no branching in test setup, clear visibility of which endpoints a test exercises, and type safety per operation.

## Decision checklist

Before substituting anything, ask: *is it out of process, nondeterministic, slow/unavailable, or not mine?* If **no** to all four — don't mock it. Exercise the real code.
