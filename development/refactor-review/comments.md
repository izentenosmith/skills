# 💬 Commenting Code

Companion reference for the [code review](SKILL.md) skill: when a comment earns its place, and what to do instead when it doesn't. Language-agnostic — examples are pseudocode; see [Mapping to your language](#mapping-to-your-language) for the construct each rule means in practice.

`Comments` is a **Dispensables** smell in [code-smells.md](code-smells.md), and `Extract Function` is its usual treatment in [refactoring-techniques.md](refactoring-techniques.md). This doc is the judgment call between them: which comments are the smell, and which are the ones worth keeping.

---

## The ladder: a comment is the last rung

Every explanatory comment is a confession that the code didn't say it. Work down the ladder and stop at the first rung that works:

```
1. NAME IT        → rename the variable, function, or type so the code states it
2. STRUCTURE IT   → extract the block into a named function; the name replaces the comment
3. TYPE IT        → encode the rule in the type system so it can't be violated
4. COMMENT IT     → only what none of the above can carry
```

Rungs 1–3 can't go stale — the compiler, the reader, and the call sites all enforce them. Rung 4 can, and eventually will. Reach for it only when the information genuinely isn't expressible as code.

```
# BAD — rung 4 used for a rung-2 problem
// check whether the order can still be cancelled: not shipped,
// within the 30-day window, and not already refunded
if order.shippedAt == null and daysSince(order.placedAt) <= 30 and order.refund == null:
    ...

# GOOD — rung 2: the name is the comment, and it can't go stale
if order.isCancellable():
    ...
```

---

## Core rules

1. **Explain WHY, not WHAT.** The reader can see the code. They can't see the reasoning, the constraint, or the alternative you rejected.
2. **Never restate a name.** If the comment says what a well-named function, variable, or type already says, delete it — including boilerplate doc comments like "Gets the total price."
3. **Keep a comment adjacent to its code.** Separated by a blank line or by unrelated statements, it drifts out of the reader's eye and goes stale unnoticed.
4. **Update the comment in the same commit as the code.** A stale comment is worse than no comment: it actively misleads, and it is trusted.
5. **Delete dead code; don't comment it out.** Version control is the archive. Commented-out blocks are noise that no tool checks and no one dares remove.
6. **Mark unfinished work and known defects** using whatever marker convention the repo already uses (commonly `TODO` and `FIXME`), each with a short note on what remains and, where one exists, a ticket reference.
7. **Comment density is not a quality metric.** Neither is its absence. A file with no comments and clear names is healthier than one padded to satisfy a lint rule.

```
# BAD — restates the code and the function name
total = price * quantity   // multiply price by quantity

/** Gets the total price. */
function getTotalPrice(items) -> Money

# GOOD — the inline comment carries a business rule; the doc comment carries scope
total = price * quantity   // gross: tax is applied later, at checkout

/** Sums unit prices of all items. Excludes tax and discounts. */
function getTotalPrice(items) -> Money
```

---

## What only a comment can carry

This is the whitelist. If what you're about to write isn't on it, go back to the ladder.

- **Why, not what** — the reason for this approach, and the alternative you rejected and why.
- **Why this looks wrong and is correct** — the seemingly-off constant, the deliberate ordering, the loop that must not be parallelized.
- **Invariants and preconditions** the type system can't express — "callers hold the lock", "sorted ascending on entry", "must run before the cache is warmed".
- **Units, ranges, and boundary semantics** — seconds vs. milliseconds, inclusive vs. exclusive, currency minor units.
- **Non-local coupling** — "kept in sync with the enum in the migration script"; the thing that breaks when this changes, if it lives somewhere the reader won't look.
- **External sources of truth** — the spec section, RFC, config key, or vendor quirk this encodes.
- **Workarounds** — what's broken upstream, the ticket tracking it, and the condition under which this can be deleted.
- **Deliberate performance or security reasoning** — why the obvious, cleaner formulation was rejected.

```
# GOOD — a workaround with an expiry condition
// The vendor API returns 200 with an empty body on rate-limit instead of 429.
// Treat an empty body as retryable. Remove once vendor ticket SUP-4821 ships.
if response.body.isEmpty():
    retry()
```

---

## Doc comments on the public surface

Whatever your language calls them — doc comments, docstrings, header comments — the rule is the same: **document the contract, not the mechanism.** The contract is what a caller must know without reading the body. The mechanism is free to change.

Write them for the **public surface**: exported/public types and their public members, and the module or package entry point. Skip them for trivially self-describing members and for overrides that don't change the inherited contract — but never skip one just to avoid explaining an unfamiliar domain term.

- **Module / package level** — one or two sentences on what this unit owns, and how it fits the wider system.
- **Type level** — its responsibility; its lifecycle or concurrency guarantees if it has any; and for an implementation of an interface, what *this* implementation contributes beyond the contract it satisfies. Don't restate what a decorator, annotation, or naming convention already tells the reader.
- **Member level** — the contract: what's required of the caller, what comes back, what can fail, and any side effect that isn't obvious from the name.

**Format** — open with a one-line summary fragment. Every doc tool and editor tooltip extracts that first line and shows it standalone, so it must stand alone: a noun or verb phrase, capitalized and punctuated as a sentence, with no leading "This function…". Put the rest in later paragraphs.

```
# BAD — mechanism leaks into the contract; changing the implementation invalidates the doc
/** Uses a concurrent hash map plus a background thread that sweeps every 60s. */
class SessionCache

# GOOD — responsibility and guarantee, which the caller actually depends on
/**
 * Tracks active user sessions for a request-processing window.
 *
 * Expired sessions are removed automatically. Safe for concurrent use.
 */
class SessionCache
```

### The member contract

Cover, in whatever tag or prose convention the language uses: **each parameter** (including what makes it invalid), **the return value**, **each failure mode**, **side effects**, and **deprecation with its replacement**. Give every one of them a description — a bare tag with no text is worse than omitting it, because it looks documented. Collapse the whole comment to one line when it has no such clauses and fits.

```
/**
 * Returns the item with the lowest unit price among the candidates.
 *
 * @param items  non-empty; unit prices must be in the same currency
 * @returns      the cheapest item; the first, if several tie
 * @throws       EmptyInput if items is empty
 */
function getCheapestItem(items) -> Item
```

---

## Let the language carry the meaning

Rung 3. Every language has features that make a comment unnecessary by making the rule unviolable — use them first.

- **Absence** — express "may be missing" in the return type (option/maybe/nullable, or a documented sentinel), never as a plain value plus a comment warning about it.
- **Immutability** — mark what isn't reassigned or mutated with whatever the language provides (`const`, `final`, `readonly`, frozen, immutable-by-default records/structs).
- **Domain types over primitives** — a named type or enum instead of a bare string, int, or boolean when the value carries meaning. This is the `Primitive Obsession` smell in [code-smells.md](code-smells.md).
- **Constrained types over documented ranges** — a type whose constructor rejects invalid values, instead of a comment listing the valid ones.
- **Don't re-explain generated or declarative code** — what a macro, annotation, decorator, code generator, or builder already establishes needs no prose restatement.

```
# BAD — the contract only exists in the comment, and nothing enforces it
// Returns nothing if no matching order is found.
function findOrder(id) -> Order

# GOOD — the signature is the contract; the caller can't ignore it
function findOrder(id) -> Option<Order>
```

Constants follow the same principle: a precise name first, then a short comment only for the unit, the business rule, or the source of truth the name can't carry.

```
// Events beyond this horizon are excluded from the solver.
// Source: config key "solver.look-ahead-threshold-hours".
const LOOK_AHEAD_THRESHOLD_HOURS = 72
```

---

## Inline comments

Place them on their own line, above the code they describe. End-of-line comments are for short clarifications only — a unit, a bound — and they push lines long and get truncated in diffs.

Use them for units, boundary conditions, and the reason a seemingly wrong choice is right. Not to narrate control flow line by line: a comment before every block is rung 2 asking to be used.

```
# GOOD — states the unit and pins down an off-by-one risk
// Seconds remaining. The 60s grace period is already subtracted,
// so this boundary is inclusive.
sessionTimeRemaining = sessionEnd - now
```

---

## Delete on sight

- Restatements of the name, and boilerplate doc comments on obvious accessors.
- Commented-out code.
- Change logs, author names, and dates — version control owns these.
- Section banners inside a long function; that's `Long Method`, and extracting is the fix.
- Comments contradicted by the code next to them. Confirm which is right, fix the code or the comment, don't leave both.
- Comments explaining a bad name, when renaming is available.

---

## Mapping to your language

The rules above are the same everywhere; only the construct changes.

| Concept | Where to look in your language |
|---|---|
| Doc comment | Javadoc/KDoc, docstring, JSDoc/TSDoc, rustdoc, XML doc, godoc, `#'` roxygen |
| Module-level doc | package doc file, module docstring, crate/module doc, package comment |
| Absence in the type | `Optional`/`Option`/`Maybe`, union with `null`/`None`, `(value, ok)` pair |
| Immutability marker | `final`, `const`, `readonly`, `val`, frozen, immutable record/struct |
| Domain type | value object, newtype, enum, branded/opaque type, literal union |
| Generated code to not re-explain | annotations, decorators, macros, builders, codegen, ORM mappings |

---

## Review checklist

Feed these into Step 1 of the [code review](SKILL.md) — findings here are `Dispensables / Comments`, and the treatment is usually `Extract Function`, `Rename`, or plain deletion.

```
[ ] No comment restates a name or the line below it
[ ] Every explanatory comment failed rungs 1-3 first, for a stated reason
[ ] Every kept comment says WHY, and appears on the whitelist above
[ ] No commented-out code, change logs, or section banners in the diff
[ ] Comments touched by this diff still match the code they sit next to
[ ] Public surface added in this diff documents its contract, not its mechanism
[ ] Doc summary lines stand alone and don't restate the member name
[ ] Absence, immutability, and domain rules are in the types, not in prose
[ ] TODO/FIXME markers say what remains and reference a ticket where one exists
```
