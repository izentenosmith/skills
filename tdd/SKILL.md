---
name: tdd
description: Test-driven development via the red-green-refactor loop, building in vertical slices. Executes an agent-brief build plan when one exists (stage 3 of the six-stage workflow) and works standalone when it doesn't. Use when the user wants to build a feature or fix a bug test-first, mentions "red-green-refactor", wants integration tests, or is acting on a build plan or remediation slices.
---

# Test-Driven Development

## Where this fits

This is **stage 3 of a six-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [agent-brief](../agent-brief/SKILL.md) — turns those decisions into the pure-text plan TDD builds from
3. **tdd** (this skill) — executes that plan red-green
4. [refactor-review](../refactor-review/SKILL.md) — cleans the structure once behavior is verified
5. [devils-advocate](../devils-advocate/SKILL.md) — assumes the result is wrong and hunts evidence for every defect
6. [tyr-verdict](../tyr-verdict/SKILL.md) — adjudicates the findings, cuts false claims, and enforces the fixes

**You execute the agent brief's contract**, read from `.workflow/brief.md`. Its **Acceptance criteria** are already ordered as a build order (first = tracer bullet, then incremental slices, edge cases marked); its **Key interfaces (test seams)** and **Test seams & prior art** tell you where to test and what to mirror. Do not re-derive the plan — read it from the brief.

> **Feedback edge — the brief is a living contract.** If, while implementing, you find that the brief is wrong, incomplete, or contradicted by reality — a seam that doesn't exist, an edge case that can't behave as specified, an acceptance criterion that conflicts with another — **STOP. Do not silently code around it.** Surface the contradiction, **edit `.workflow/brief.md` in place** to match the new understanding, log the change in its **Revisions** section, then resume the loop against the corrected contract. Never fork the brief; the file stays the single authority.

> **The working files.** The pipeline keeps `.workflow/brief.md` (the plan you execute) and `.workflow/ledger.md` (findings and remediation slices across loop iterations) in the repo under review. The brief is revised in place, never forked; the ledger is append-only, and its finding IDs are stable — `F1` in iteration 1 is the same finding in iteration 3. Running standalone, neither file exists: work from what you have and say so.

> **Loop-back edge.** This stage also runs as the fix step of the closing loop: when [tyr-verdict](../tyr-verdict/SKILL.md) returns NO-GO, its confirmed defects arrive as remediation slices already shaped like acceptance criteria, in `.workflow/ledger.md` under **Remediation slices — open**. Execute them here red-green exactly as you would a fresh brief. As each one goes green, move it to **closed** with the test that verifies it — that record is how the loop proves it is making progress rather than circling. Then send the result back through refactor-review → devils-advocate → tyr-verdict.

## Philosophy

**Core principle**: Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification — "user can checkout with valid cart" tells you exactly what capability exists, and survives refactors because it ignores internal structure.

Before writing any test, read [good-tests.md](good-tests.md) — the 4 pillars of test quality and worked good-vs-bad examples. Judge every test you write against it.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This is "horizontal slicing" - treating RED as "write all tests" and GREEN as "write all code."

This produces **crap tests**:

- Tests written in bulk test _imagined_ behavior, not _actual_ behavior
- You end up testing the _shape_ of things (data structures, function signatures) rather than user-facing behavior
- Tests become insensitive to real changes - they pass when behavior breaks, fail when behavior is fine
- You outrun your headlights, committing to test structure before understanding the implementation

**Correct approach**: Vertical slices via tracer bullets. One test → one implementation → repeat. Each test responds to what you learned from the previous cycle. Because you just wrote the code, you know exactly what behavior matters and how to verify it.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
  ...
```

## Subagents — do not delegate the loop

**The red→green cycle stays in the main thread.** This is the one stage in the workflow where delegation actively damages the output. Each cycle is *supposed* to respond to what the previous one taught you — that is the whole argument against horizontal slices above. Hand the loop to a subagent working from the brief and you get several tests written in bulk against imagined behavior: horizontal slicing with extra steps.

What you may delegate is **lookup**, never construction:

- A prior-art or convention search when the brief's pointer turns out to be stale or missing.
- A read-only sweep for existing callers of a seam you are about to change, when back-compat is in question.

Take the answer, then write the test yourself.

**Dispatch contract**, if you do delegate a lookup: give the subagent the **prior**, the **target** (behavioral, not file paths), the **context it cannot infer**, the **return shape**, and an explicit *"report conclusions, not file excerpts."* Keep it read-only — a delegate must never edit the tree while you are mid-cycle in it.

## Workflow

### 1. Planning

**First action — load the project's development criteria** for the area you're touching (typically a per-app "dev-criteria" skill or doc named after the service/module), plus its domain glossary and any ADRs covering that area. Load each relevant one if the work spans several areas. If [architect-deep-dive](../architect-deep-dive/SKILL.md) already loaded them, reload only what covers ground it didn't. This skill stays repo-agnostic on purpose: the *process* lives here, the *project-specific rules* live in those criteria. Test names and interface vocabulary follow the glossary.

**Then planning takes one of two shapes.** Which one depends on whether a brief exists — do not run both.

#### With a brief — planning is a lookup, not a design session

Stages 1 and 2 already resolved the interface, chose the behaviors, prioritized them, and got the user's approval. Re-asking any of that reopens settled decisions and wastes the two stages that settled them. Read `.workflow/brief.md` and take:

- [ ] **The interface** ← **Key interfaces (test seams)**. Test through the highest seam it names.
- [ ] **The build order** ← **Acceptance criteria**, top to bottom, first as the tracer bullet.
- [ ] **The conventions** ← **Test seams & prior art**. Mirror what it points at.
- [ ] **The limits** ← **Out of scope** and **Deferred by design**. A deferred detail stays deferred; do not let a test commit to it.

Then verify the brief is actually executable before writing a test — that the named seams exist, and that no criterion depends on one that doesn't. **A gap here is the feedback edge, not a licence to re-plan:** fix `.workflow/brief.md` and log the revision. Confirm with the user only where the brief is silent or self-contradictory.

#### Without a brief — standalone TDD

No upstream stage ran, so reconstruct the minimum before writing any code:

- [ ] Confirm with user what interface changes are needed
- [ ] Confirm with user which behaviors to test, in priority order
- [ ] List the behaviors to test (not implementation steps)
- [ ] Get user approval on the plan

Ask: "What should the public interface look like? Which behaviors are most important to test?" **You can't test everything** — focus on critical paths and complex logic, not every possible edge case, and confirm with the user which behaviors those are.

#### Either way

- [ ] Identify opportunities for [deep modules](deep-modules.md) (small interface, deep implementation)
- [ ] [Design interfaces for testability](interface-design.md)
- [ ] Decide what (if anything) needs to be substituted — [mock only at system boundaries](mocking.md)

Design references for this step: [deep-modules.md](deep-modules.md) (power behind a small interface), [interface-design.md](interface-design.md) (shape it to be testable), [mocking.md](mocking.md) (what to leave real vs. substitute).

### 2. Tracer Bullet

Write ONE test that confirms ONE thing about the system:

```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

This is your tracer bullet - proves the path works end-to-end.

### 3. Incremental Loop

For each remaining behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:

- One test at a time
- Only enough code to pass current test
- Don't anticipate future tests
- Keep tests focused on observable behavior

### 4. Refactor

After all tests pass, look for refactor candidates:

- [ ] Extract duplication
- [ ] [Deepen modules](deep-modules.md) (move complexity behind simple interfaces)
- [ ] Apply SOLID principles where natural
- [ ] Consider what new code reveals about existing code
- [ ] Replace explanatory comments with better names, extractions, or types. Every explanatory
      comment is a confession that the code didn't say it — work down this ladder and stop at the
      first rung that works, because rungs 1-3 cannot go stale and rung 4 eventually will:
      **1. name it** (rename the variable, function or type) → **2. structure it** (extract the
      block into a named function; the name replaces the comment) → **3. type it** (encode the rule
      so it can't be violated) → **4. comment it** (only what none of the above can carry —
      rationale, boundary semantics, a non-obvious "why")
- [ ] Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

### 5. Definition of Done

The loop is finished when every one of these holds:

- [ ] Every **acceptance criterion in `.workflow/brief.md`** is implemented and has a test that verifies it — check each one off in the file, so the record survives the next loop iteration. (Running standalone: every behavior agreed in Planning.)
- [ ] On a loop-back pass: every **remediation slice** you were handed is moved to **closed** in `.workflow/ledger.md`, naming the test that verifies it
- [ ] The full suite is GREEN

Then the structure gets cleaned, in [refactor-review](../refactor-review/SKILL.md) — that is stage 4, not a checklist item here, and it has its own severity rules and stopping rule. Invoke it against the new changes only, apply what it prescribes as **structural-only** changes, and keep the suite GREEN through every step.

The division of labor is strict: **TDD gets you to verified behavior, refactor-review gets you to clean structure.** Do not skip it.

## Handoff — into the adversarial close

Green tests and a clean diff are a *claim* of correctness, not proof of it. Once the suite is GREEN, the change goes through the rest of the pipeline:

1. Run **[refactor-review](../refactor-review/SKILL.md)** (stage 4) — clean the structure on a green suite.
2. Run **[devils-advocate](../devils-advocate/SKILL.md)** (stage 5) — assume everything you built is wrong and hunt evidence for each defect.
3. Run **[tyr-verdict](../tyr-verdict/SKILL.md)** (stage 6) — adjudicate those findings and issue a go/no-go verdict.

If tyr-verdict returns **NO-GO**, its remediation slices come back to this skill as a new red→green build order (see the loop-back edge above). The loop converges when devils-advocate turns up nothing new and tyr-verdict confirms nothing.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```
