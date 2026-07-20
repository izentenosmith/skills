# Deep Modules

Companion reference for the [tdd](SKILL.md) skill: how to design modules with maximum power behind minimum interface. Read this during the Planning step when you "identify opportunities for deep modules" and design interfaces.

From John Ousterhout's *A Philosophy of Software Design*.

## The core idea: benefit vs. cost

Every module has a **benefit** (the functionality it provides) and a **cost** (the interface you must understand to use it). The best modules maximize benefit and minimize cost.

- **Deep module** = small interface + lots of implementation. High benefit, low cost. **Prefer these.**
- **Shallow module** = large interface + little implementation. Low benefit, high cost. **Avoid these.**

```
   DEEP (good)                      SHALLOW (avoid)
┌─────────────────────┐      ┌─────────────────────────────────┐
│   small interface   │      │        large interface          │
├─────────────────────┤      ├─────────────────────────────────┤
│                     │      │  thin implementation            │
│                     │      └─────────────────────────────────┘
│  deep, complex      │       ↑ interface ≈ implementation:
│  implementation     │         the module barely earns its
│  hidden inside      │         keep — it just passes through.
│                     │
└─────────────────────┘
 ↑ a lot of complexity hidden behind a few simple methods
```

The unit of value is **how much complexity the interface hides**, not how much code is behind it. A 500-line class with 40 public methods can still be shallow.

## Why this matters for TDD

A deep module is the easiest thing in the world to test well:

- **Small interface → few, behavioral tests.** You test the handful of public methods against observable outcomes. There is little surface to over-test.
- **Hidden complexity → refactor-proof tests.** Because the hard logic lives behind the interface, you can rewrite it freely and the tests stay green. That is exactly the property [good-tests.md](good-tests.md) demands.
- **The smell works in reverse, too.** If you find yourself wanting to test internals, reach through to private methods, or assert on collaborators, the module is probably too shallow — its complexity is leaking through the interface. Deepen it instead of testing around it.

## Red flags (shallow modules)

- **Classitis** — many tiny classes/modules, each doing almost nothing; the complexity moves to the *connections between* them.
- **Pass-through / middle-man methods** — a method whose only job is to call another method with the same arguments (see *Middle Man* in [code-smells.md](../refactor-review/code-smells.md)).
- **Configuration overload** — pushing decisions onto the caller via dozens of options/flags instead of choosing sane defaults internally.
- **Leaky getters/setters** — exposing internal state so callers can manipulate it, rather than offering an operation that does the work.
- **Temporal decomposition** — splitting modules by *order of execution* (step1, step2, step3) instead of by *information hidden*.

## Before / after

```
# SHALLOW: caller must orchestrate every step and know the internals
raw       = reader.read(path)
parsed    = parser.parse(raw)
validated = validator.validate(parsed)
config    = builder.build(validated)

# DEEP: one call hides reading, parsing, validation, defaults
config = loadConfig(path)   # everything above is hidden inside
```

## Questions to ask when designing an interface

- Can I reduce the number of methods or parameters?
- Can I pick a good default instead of asking the caller to decide?
- Can I hide more complexity *inside* (errors, retries, ordering, edge cases)?
- Does each method do something genuinely useful, or is it just plumbing?
- Could a caller misuse this? A deep interface makes the common case easy and the wrong case hard.

For the mechanics of *making* an interface testable once you've decided it should be deep, see [interface-design.md](interface-design.md).
