# Domain primitives — security-relevant values as types

> When the brief names a domain primitive, or the slice handles a value an attacker controls
> (an ID, an amount, an e-mail, a path, a URL, a query fragment), build the type first and drive it
> with the tests below. Source: Bergh Johnsson & Deogun, *Secure by Design — Ideas and Techniques*
> (SecAppDev slide deck, cited by slide). The test categories follow the same authors' book
> (*Secure by Design*, Manning) and are stated here as practice.

## What one is

A **domain primitive** is a small value object that **cannot exist in an invalid state**: it
validates in its constructor, has no setters, and carries the operations that must preserve its
invariants (slides 15–20). Once one exists, every function that takes it gets a valid value without
re-checking — validation moves from every call site to one place, and the attack surface shrinks to
semantically valid input (slide 23).

```
# Before — a raw primitive crosses every layer, validated (or not) at each call site
def transfer(amount: float, to_account: str): ...

# After — invalid values can't be constructed, so they can't arrive
class AccountId:          # validated once: format, length, charset
class Money:              # amount + currency, non-negative, fixed precision; add() refuses mixed currencies
def transfer(amount: Money, to: AccountId): ...
```

Two smaller rules come with it:

- **Conceptual wholes over ambiguous parameter lists.** Two adjacent parameters of the same primitive
  type can be swapped by a caller and no test notices; an amount without its currency can be summed
  with the wrong one (slide 19).
- **Invariants live in the type.** "Currencies match" is checked by `Money.add`, not by every caller
  of it (slide 20).

## Validate in this order

Cheapest and most hostile-input-resistant checks first, so expensive parsing never runs on garbage
(*Secure by Design*, ch. 4 — practice):

1. **Origin** — did this come from somewhere allowed to send it?
2. **Size** — reject oversize input before reading it.
3. **Lexical content** — only the allowed characters.
4. **Syntax** — the format parses.
5. **Semantics** — the value makes sense in this domain (the account exists, the date is in range).

## The tests a domain primitive needs

Write them red-green like any other behaviour — through the type's public constructor and methods.

| Category | What it proves | Example for `AccountId` |
|---|---|---|
| **Normal** | Valid values construct and behave | a well-formed ID constructs; equal IDs are equal |
| **Boundary** | The edges are where the rule says | shortest and longest allowed length construct; one past each is refused |
| **Invalid** | Each class of invalid input is refused at construction | wrong charset, empty, whitespace-padded, wrong checksum — one test each |
| **Extreme** | Hostile input fails fast and cheaply | a 10 MB string, control characters, mixed encodings, `null` — refused without hanging or partially constructing |
| **Invariant** | Operations preserve validity | `Money.add` with mixed currencies is refused; results stay non-negative |
| **Immutability** | Validity can't be undone later | no setter exists; a returned collection can't be mutated to change the value |

**The refusal is specific.** Assert *which* rule refused the value, not just that construction
failed — otherwise a test for "too long" passes when the real refusal was "bad charset".

**The error doesn't echo the input.** An exception message that quotes the rejected value carries
attacker-controlled text into logs and error pages. Assert that it names the rule, not the value.

## Sensitive values: read-once and masked

For a secret the code should consume once (a reset token, a one-time code, a password on its way to
the hash function), use a **read-once** wrapper: the first read returns the value and clears it, a
second read fails loudly, `toString` is masked, and serialisation is refused (slides 30–35). Its
tests:

- first read returns the value; a second read fails;
- `str()` / `toString()` / string interpolation shows a mask, never the value;
- serialising the object (to JSON, to a log formatter) fails or emits the mask.

The leak this prevents is the field someone adds later to an entity that is already logged whole
(slides 31–33). A test that a whole entity's log line contains no sensitive field catches it the day
it happens.

## Introducing primitives into existing code

Don't replace a raw type across a codebase in one slice. Three steps, each green on its own
(slides 24–29):

1. **Observe** — at the boundary, construct the primitive alongside the raw value and *log* (without
   the value) when it would have been refused. Real data tells you whether the rule is right before
   anything is rejected.
2. **Enforce at the border** — change the public signature to take the primitive; the boundary now
   refuses invalid input.
3. **Trickle inward** — replace the raw type in the layers behind the border, one call path per slice.

Each step is its own red→green slice, and the suite stays green between them.
