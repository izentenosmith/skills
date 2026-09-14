# Clean Architecture

Companion reference for the [architect-deep-dive](SKILL.md) skill: how to resolve the *structural* dimensions — where policy lives, which way dependencies point, and where the lines go. Read this when working the **Policy vs. details** and **Dependency direction & boundaries** dimensions of the termination gate.

From Robert C. Martin's *Clean Architecture*, with the component principles from the same book.

## The one rule

> **Source code dependencies must point only inward, toward higher-level policy.**

Everything below is a consequence of that sentence. When a design decision is genuinely ambiguous, the tiebreaker is: which option keeps the arrows pointing at policy?

```
        ┌──────────────────────────────────────────┐
        │  details: web, DB, framework, devices    │  ← volatile, replaceable
        │   ┌──────────────────────────────────┐   │
        │   │  adapters: controllers,          │   │
        │   │  presenters, gateways            │   │
        │   │   ┌──────────────────────────┐   │   │
        │   │   │  use cases               │   │   │  ← app-specific policy
        │   │   │   ┌──────────────────┐   │   │   │
        │   │   │   │    entities      │   │   │   │  ← enterprise policy
        │   │   │   └──────────────────┘   │   │   │
        │   │   └──────────────────────────┘   │   │
        │   └──────────────────────────────────┘   │
        └──────────────────────────────────────────┘
              dependencies point ───────────▶ inward
```

Nothing in an inner ring may name anything in an outer ring — not a class, not a type, not a data format, not a config key.

## Policy vs. detail

Every system splits into two things:

- **Policy** — the business rules and procedures. This is where the value lives.
- **Detail** — everything needed to let humans, other systems, and programmers *talk to* the policy, but which does not change what the policy decides.

The database is a detail. The web is a detail — it's an IO device. The framework is a detail. The delivery mechanism, the wire format, the ORM, the message bus: details.

The goal is to make details **irrelevant** to policy, so decisions about them can be delayed. The longer a decision stays open, the more information you have when you finally make it.

**The distinction that trips people up:** the *data model* is architecturally significant; the *database* is not. How entities relate, who owns what, which invariants hold — that is policy, resolve it now. Whether it lands in Postgres or a flat file is a detail, defer it.

### Level

> **Level = distance from the inputs and outputs.**

The farther a policy sits from IO, the higher its level. Entities are highest — they'd hold true in a manual, paper-based version of the business. Use cases are lower: they describe how an *automated* system is operated, so they're closer to IO. Controllers, presenters and gateways are lower still.

Use cases depend on entities. Entities never depend on use cases.

This is what turns *"place the seam as high as possible"* into an operational rule: the highest seam is the one farthest from IO, and everything closer to IO plugs into it.

## Where the lines go

> **Boundaries are drawn where there is an axis of change.**

Not at feature edges, not where the folders already are. Components on opposite sides of a line change **at different rates and for different reasons**. Components that change together for the same reason belong on the same side.

So the real question for any candidate boundary is never *"are these two things different?"* — it's **"do these two things change for different reasons, at different times?"** If the answer is no, the line is ceremony.

### The two duplication traps

- **True duplication** — every change to one demands the same change to the other. Unify it.
- **Accidental duplication** — two things look alike today and will diverge. Unifying them is the expensive mistake, because separating them later is much harder than never joining them.

Two screens with similar structure, or a DB row that happens to match a view shape, are almost always accidental. Resist the knee-jerk unification. Copy the shape across the boundary.

### Boundary form

A full boundary is reciprocal interfaces in both directions, with its own input/output data structures. It isn't free — pay for it only where the axis of change is real. Cheaper options, in ascending cost:

| Form | What it is | When |
|---|---|---|
| **None** | Just keep the code honest | No axis of change yet, and no friction |
| **Facade** | One class listing the methods, dispatching to hidden implementations | You want a name for the seam and nothing more |
| **One-dimensional** | A single abstract interface (Strategy) — isolation one way only | The dependency needs inverting, but only one side varies |
| **Skip-the-last-step** | Full interfaces and data structures, still one deployable | You expect to split later and want the option now |
| **Full** | Reciprocal interfaces, independently deployable | The axis of change is proven and the sides evolve apart |

The decision isn't once-and-for-all. Watch for the first friction from a *missing* boundary, and implement it at the inflection point where the cost of building it drops below the cost of ignoring it.

### Decoupling mode

Independent of form, pick *how far apart* the sides sit:

- **Source level** — same address space, function calls, one deployable (a "monolith"). Boundaries are real even when invisible at deploy time.
- **Deployment level** — separate jars/DLLs/gems, independently redeployable.
- **Service level** — separate processes over a network, coupled only through data.

Default: **push the design to the point where a service *could* be formed, then leave the components in the same address space as long as possible.** Service boundaries cost real development time, force coarse granularity, and buy nothing until you actually need them. Reaching for service-level decoupling by default is the expensive mistake here.

And note the decoupling fallacy: services are *not* automatically decoupled. Two services sharing a data record are strongly coupled through it — add a field and every one of them changes together.

## Frameworks

The relationship is asymmetric: you make a huge commitment, the framework author makes none. So **use it, don't marry it.** Keep it in an outer ring. If it wants you to derive your business objects from its base classes, derive a proxy instead and plug that in.

An architecture built on a framework cannot be built on your use cases. Frameworks are options to be left open — the choice of framework, web server, and DB should stay deferrable well into the project.

## Screaming architecture

The top-level structure should name the *domain*, not the toolkit. Looking at it should say "vessel maintenance system," not "Rails" or "Spring." If a new reader's first impression is your framework, policy is in the wrong place.

## Testability as a structural signal

Tests are the outermost ring — they depend inward on everything and nothing depends on them.

Which makes them a hard architectural check: **if a business rule can't be tested without the web server running or the database connected, the boundary is in the wrong place.** Not a testing problem — a design problem. Don't mock around it; move the line.

Corollary: don't couple tests to volatile structure. A suite that drives business rules through the UI is fragile by construction, and fragile tests make the system *rigid*, because teams start refusing changes that break a thousand tests.

At each boundary expect a **Humble Object**: split the hard-to-test part down to its barest essence (the View, the raw SQL, the wire format) and put everything testable on the other side (the Presenter, the gateway, the interactor).

## For decomposition

When splitting into independently shippable increments, these govern where the component lines fall:

- **Common Closure** — gather what changes for the same reasons at the same times; separate what doesn't. (SRP at component scale.)
- **Common Reuse** — don't force a component to depend on things it doesn't use. Classes reused together belong together; classes not tightly bound don't.
- **Acyclic Dependencies** — no cycles in the component graph, ever. A cycle fuses the components into one effective unit, and everyone in it must move in lockstep.
- **Stable Dependencies** — depend in the direction of *stability*. A component with many incoming dependencies is hard to change; never let something volatile be depended on by something rigid.
- **Stable Abstractions** — a component should be as abstract as it is stable. Stability without abstraction is the rigid zone (a DB schema lives here); abstraction without dependents is dead code.

## The counterweight

Over-architecture fails as reliably as under-architecture, and it fails more expensively because the cost is paid up front and continuously.

> **Architecture must be flexible enough to adapt to the size of the problem.**

Architecting for the enterprise when the job needs a small tool is a recipe for failure. A boundary you don't need still costs interfaces to maintain, data structures to copy across, and indirection every reader must decode.

Which is why the decision is a *judgment about cost of change*, not a checklist to satisfy. The question is never "is this the clean way?" — it's **"which is cheaper: building this boundary now, or not having it later?"**
