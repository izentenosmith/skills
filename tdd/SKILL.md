---
name: tdd
description: Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development.
---

# Test-Driven Development

## Where this fits

This is **stage 4 (the final stage) of a four-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [product-requirement-document](../product-requirement-document/SKILL.md) — synthesizes those decisions into a PRD
3. [agent-brief](../agent-brief/SKILL.md) — writes the authoritative behavioral spec on the issue
4. **tdd** (this skill) — executes that spec red-green-refactor

**You execute the agent brief's contract.** Its **Acceptance criteria** are already ordered as a build order (first = tracer bullet, then incremental slices, edge cases marked); its **Key interfaces (test seams)** and **Test seams & prior art** tell you where to test and what to mirror. Do not re-derive the plan — read it from the brief.

> **Feedback edge — the brief is a living contract.** If, while implementing, you find that the brief (or the PRD behind it) is wrong, incomplete, or contradicted by reality — a seam that doesn't exist, an edge case that can't behave as specified, an acceptance criterion that conflicts with another — **STOP. Do not silently code around it.** Surface the contradiction, revise the agent brief (and the PRD if the decision changed) to match the new understanding, then resume the loop against the corrected contract.

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

## Workflow

### 1. Planning

**First action — load the project's development criteria.** Before exploring or writing anything, check whether the repo defines area-specific development criteria for the part of the codebase you're touching (typically a per-app "dev-criteria" skill or doc named after the service/module). If one exists, invoke it first — it carries the conventions, constraints, and lessons learned that the tests and implementation must respect. If the work spans more than one area, load each relevant one. This skill stays repo-agnostic on purpose: the *process* lives here, the *project-specific rules* live in those criteria.

When exploring the codebase, use the project's domain glossary so that test names and interface vocabulary match the project's language, and respect ADRs in the area you're touching.

Before writing any code:

- [ ] Confirm with user what interface changes are needed
- [ ] Confirm with user which behaviors to test (prioritize)
- [ ] Identify opportunities for [deep modules](deep-modules.md) (small interface, deep implementation)
- [ ] [Design interfaces for testability](interface-design.md)
- [ ] Decide what (if anything) needs to be substituted — [mock only at system boundaries](mocking.md)
- [ ] List the behaviors to test (not implementation steps)
- [ ] Get user approval on the plan

Design references for this step: [deep-modules.md](deep-modules.md) (power behind a small interface), [interface-design.md](interface-design.md) (shape it to be testable), [mocking.md](mocking.md) (what to leave real vs. substitute).

Ask: "What should the public interface look like? Which behaviors are most important to test?"

**You can't test everything.** Confirm with the user exactly which behaviors matter most. Focus testing effort on critical paths and complex logic, not every possible edge case.

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
- [ ] Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

### 5. Review & Definition of Done

Once the cycle is complete and all tests are GREEN, run the structural review pass before considering the work done.

**Structural review — `/refactor-review`** (catches smells the green bar didn't):

- [ ] Invoke the `/refactor-review` skill against the new changes only
- [ ] Work through Step 1 (Smell Identification) and Step 2 (Refactoring Action Plan & Validation)
- [ ] Apply prescribed refactors as **structural-only** changes — zero new behavior
- [ ] Re-run the full test suite after each refactor; tests must stay GREEN

**Definition of done** — the work is not done until:

- [ ] Every **acceptance criterion in the agent brief** is implemented and has a test that verifies it (check each one off against the brief)
- [ ] The structural review is complete and its actionable findings resolved
- [ ] The full suite is GREEN

The handoff is strict: **TDD gets you to verified behavior, `/refactor-review` gets you to clean structure.** Do not skip it.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```
