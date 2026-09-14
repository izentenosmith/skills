---
name: agent-brief
description: Turn resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. Use after architect-deep-dive and before tdd, when a feature or fix needs a detailed spec to build against.
---

# Agent Brief — the plan TDD builds from

An agent brief is the authoritative **build plan** for a feature or fix. Its output is **pure text** — a structured plan, not code and not a code change. It is the contract the TDD stage executes against: read top-to-bottom, its acceptance criteria are already a red→green build order.

**Write it to `.workflow/brief.md`** in the repo being worked on, not just into the conversation. Three stages downstream read it — TDD checks criteria off against it and revises it when reality contradicts it, the teardown needs its edge cases and deferrals, and a subagent can only be pointed at a path. In a loop that runs a stage more than once, a plan that exists only in scrollback stops being authoritative around the second iteration. (Writing a plan file is not a code change — the rule against emitting code stands.)

### The working files

The pipeline keeps two files in the repo under review. You create the first; the closing stages create the second.

```
.workflow/
  brief.md    — this plan (you write it; TDD executes and revises it)
  ledger.md   — findings, verdicts and carried smells across loop iterations
```

Three rules make them trustworthy:

- **The brief is revised in place, never forked.** When TDD's feedback edge finds it wrong, the fix edits this file and appends a line to its **Revisions** section. A second copy means neither is authoritative.
- **Delegates read these files; only the running stage writes them.** Two subagents appending to one file interleave into nonsense.
- **A stage running standalone needs neither file** and should say so rather than stopping.

They are working artifacts, not deliverables — gitignore them, or commit them as the change's design record.

This skill is **stage 2 of a six-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. **agent-brief** (this skill) — turns those decisions into the plan TDD builds from
3. [tdd](../tdd/SKILL.md) — executes that plan red-green
4. [refactor-review](../refactor-review/SKILL.md) — cleans the structure once behavior is verified
5. [devils-advocate](../devils-advocate/SKILL.md) — assumes the result is wrong and hunts evidence for every defect
6. [tyr-verdict](../tyr-verdict/SKILL.md) — adjudicates the findings, cuts false claims, and enforces the fixes

**Upstream (from architect-deep-dive):** every dimension the architect resolved is your raw material — pull directly from it. Its **charter** (what we're solving, why now, what done looks like) becomes your **Summary** and **Desired behavior**; carry the *why now* rather than dropping it, because it is what tells TDD which criterion matters when two conflict. Its interface decisions become your **Key interfaces**; its resolved failure modes and edge cases become your **edge-case criteria**; its user-facing behaviors become your **happy-path criteria**; its scope boundaries become your **Out of scope**. If a dimension was left implicit, you are missing input — go back to architect-deep-dive rather than guessing.

Two of its outputs are **constraints on the plan rather than work in it**. Its resolved boundaries and dependency directions bound where the behavior may live — carry them into **Key interfaces** so TDD builds inward-pointing seams instead of rediscovering them. Its **deliberately deferred** decisions (database engine, framework, delivery mechanism) stay deferred: record each one with the boundary that protects it, and do not let an acceptance criterion commit to it. A criterion that names a deferred detail has quietly resolved a decision the architect chose to leave open.

**Downstream (into TDD):** the TDD stage's planning step needs four things before it can write a single test — the public interface/seams, a *prioritized* list of behaviors to test, what is explicitly *not* tested, and prior art for similar tests. Shape this brief so all four fall out of it directly. See **Tangling to TDD** below.

## Principles

### Behavioral, not procedural

Describe **what** the system should do, not **how** to implement it. The TDD stage explores the codebase fresh and makes its own implementation decisions. Name types, signatures, and contracts — not file paths or line numbers, which go stale and pre-empt design.

- **Good:** "When a request targets a resource inside the cutoff window, it is rejected with error code `CUTOFF_WINDOW`."
- **Bad:** "Open the request handler and add an `if` that compares the target date to now."
- **Good:** "The `ChangeRequest` aggregate should expose a `Validate(config)` method returning the list of constraint violations."
- **Bad:** "Add a switch statement in the request-service source around line 80."

### Complete, testable acceptance criteria

TDD needs to know when it's done. Every criterion must be concrete and independently verifiable through the public interface.

- **Good:** "The change-request endpoint returns a rejection with error code `CUTOFF_WINDOW` when the target is inside the cutoff window."
- **Bad:** "Cutoff should work correctly."

### Explicit scope boundaries

State what is out of scope. This prevents TDD from gold-plating or drifting into adjacent features that were deliberately deferred during architect-deep-dive.

## Tangling to TDD

The TDD stage's planning step asks: *"What should the public interface look like? Which behaviors are most important to test?"* and then builds vertically — one test, one slice, tracer-bullet first. A plan that ignores this forces TDD to re-derive itself from scratch. Shape the plan so TDD planning is a lookup, not a re-design:

- **Name seams, not internals.** TDD tests behavior through the *highest public seam* available and prefers existing seams to new ones. In **Key interfaces**, describe the public entry points (endpoints, service methods, component contracts) tests will target — not private collaborators. If a new seam is needed, say so and place it as high as possible.
- **Prioritize the acceptance criteria.** TDD does NOT test everything — it focuses on critical paths and complex logic. Order the criteria so the first is the **tracer-bullet candidate**: the single most important end-to-end behavior that proves the path works. Everything after it is one incremental red→green slice. The list must read top-to-bottom as a build order.
- **State criteria as observable behavior.** Each criterion must be verifiable through the public interface and read like a spec sentence.
- **Separate edge-case criteria from happy-path.** Carry the unhappy paths resolved during architect-deep-dive (empty/missing input, boundaries, permission failures, partial failures, isolation/tenancy quirks) into their own clearly-marked criteria so TDD writes the edge-case slices it would otherwise skip.
- **Supply prior art.** TDD's planning step looks for similar tests already in the codebase. Point at the closest existing test suites/patterns (e.g. table-driven constraint tests, public-entry-point handler tests, component-contract tests, boundary/gateway tests) so TDD matches conventions instead of inventing them.

## Subagents — optional

Writing the plan is yours: the ordering of the acceptance criteria *is* the build order, and it takes the whole design in view to get right.

The **prior-art hunt** is not. "Point at the closest existing test suites and patterns" is a read-only search across a codebase you may not know, and it is the one part of this brief that can flood your context with file excerpts while you are trying to write prose. Dispatch it: hand a subagent the seams you're testing through and ask which existing suites test comparable behavior, what conventions they follow, and what harness they use. Take back the names and the conventions, and write them into **Test seams & prior art** yourself.

**Dispatch contract.** A subagent starts with no history. Give it five things: the **prior** (the stance to adopt), the **target** (described behaviorally, not as file paths), the **context it cannot infer** (the seams you're testing through), the **return shape** you want back, and an explicit *"report conclusions, not file excerpts."* Keep delegates read-only, and cap the fan-out.

## Template (output this as pure text)

```markdown
# Build Plan: <feature/fix name>

**Category:** bug / enhancement
**Summary:** one-line description of what needs to happen

**Current behavior:**
Describe what happens now. For bugs, this is the broken behavior.
For enhancements, this is the status quo the feature builds on.

**Desired behavior:**
Describe what should happen after the work is complete.
Be specific about edge cases and error conditions.

**Key interfaces (test seams):**
- `TypeName` — what needs to change and why
- `functionName()` return type — what it currently returns vs what it should return
- Public entry point the behavior is observable through (endpoint / service method / component contract) — the seam tests should target
- Config shape — any new configuration options needed

**Acceptance criteria** (ordered — first is the tracer-bullet candidate, each one a single red→green slice):
- [ ] Tracer bullet: the most important end-to-end behavior that proves the path works
- [ ] Next most important behavior
- [ ] Next most important behavior
- [ ] Edge case: <unhappy path — empty/missing input, boundary, permission failure, partial failure, isolation/tenancy quirk>
- [ ] Edge case: <unhappy path>

**Test seams & prior art:**
- Highest existing seam to test through (prefer existing seams to new ones)
- Closest existing test suite/pattern in the codebase to mirror for conventions

**Deferred by design** (constraints, not work — carried from architect-deep-dive):
- <decision left open> — deferred behind <the boundary that protects it>; forced by <signal>

**Out of scope:**
- Thing that should NOT be changed or addressed here
- Adjacent feature that might seem related but is separate

## Revisions
- (empty at creation; TDD's feedback edge appends here)
```

## Handoff

After writing the plan to `.workflow/brief.md`, prompt the user:

> The build plan is written to `.workflow/brief.md`. Run the **[tdd](../tdd/SKILL.md)** skill next — its acceptance criteria are ordered as a red→green build order, with the first as the tracer bullet.

## Examples

### Good build plan (enhancement)

```markdown
# Build Plan: Enforce a cutoff window on change requests

**Category:** enhancement
**Summary:** Reject change requests submitted within the cutoff window of the target.

**Current behavior:**
The change-request endpoint accepts any well-formed request against a
target resource. There is no check on how close the target is, so a
request can be submitted right up against the target's start time.

**Desired behavior:**
A request whose earliest affected target starts within the cutoff window
(a default window, configurable per account) is rejected. Requests whose
targets are all outside the window proceed as today.

**Key interfaces (test seams):**
- `ChangeRequest` aggregate — should expose validation that returns
  constraint violations rather than raw booleans
- The constraint validator seam that checks a proposed request against
  active rules — the cutoff rule joins the existing rules here
- The change-request handler — the public seam tests drive; on a cutoff
  violation it returns a rejection carrying error code `CUTOFF_WINDOW`
- Account config — a `cutoff_window` field (with a default) tests can override

**Acceptance criteria** (ordered — first is the tracer-bullet candidate):
- [ ] Tracer bullet: a request for a target inside the cutoff window is
      rejected with error code `CUTOFF_WINDOW`
- [ ] A request whose targets are all outside the window is accepted and persists
- [ ] The window boundary is inclusive/exclusive per the resolved rule
      (a target exactly at the window edge behaves as decided in architect-deep-dive)
- [ ] The window length reads from account config, not a hard-coded default
- [ ] Edge case: a multi-part request where only one part is inside the window
      is rejected as a whole
- [ ] Edge case: a request referencing a target owned by another account is
      rejected before the cutoff check (isolation boundary)

**Test seams & prior art:**
- Drive tests through the change-request handler using the project's
  existing request-driving test harness, mirroring the current handler tests
- Mirror the table-driven constraint tests (e.g. the existing rules) for the
  validator-level cases
- For the persistence path, use the project's integration-test setup

**Out of scope:**
- Administrator overrides of the cutoff window
- Notifying the counterpart of a rejected request
- Changing the default window length
```

### Bad build plan

```markdown
# Build Plan: Fix the request bug

**What to do:**
The request thing is broken. Look at the main handler and fix it.
The function around line 80 has the issue.

**Files to change:**
- the request handler source (line 80)
- the request domain source (line 42)
```

This is bad because:
- No category, no current-vs-desired behavior
- Vague description ("the request thing is broken")
- References file paths and line numbers that go stale and pre-empt design
- No acceptance criteria — nothing for TDD to slice into red→green cycles
- No prioritization or tracer bullet, so no build order
- No test seams or prior art, forcing TDD to re-design the test plan
- No scope boundaries
