---
name: acceptance-tests
description: Turn a build plan's acceptance criteria into executable black-box acceptance tests — written before any implementation, through the system's outermost public boundary, each one failing for the right reason — and record which test proves which criterion. Stage 3 of the seven-stage workflow, between agent-brief and tdd; tdd's work is done when these pass. Use when a feature or fix has acceptance criteria and should be proven from the outside, for "acceptance tests", "ATDD", "end-to-end tests from the spec", "executable specification".
---

# ✅ Acceptance Tests

## Where this fits

This is **stage 3 of a seven-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [agent-brief](../agent-brief/SKILL.md) — turns those decisions into the pure-text plan the rest builds from
3. **acceptance-tests** (this skill) — turns the plan's acceptance criteria into failing black-box tests, before any code
4. [tdd](../tdd/SKILL.md) — builds it red-green until the acceptance tests pass
5. [refactor-review](../refactor-review/SKILL.md) — cleans the structure once behavior is verified
6. [devils-advocate](../devils-advocate/SKILL.md) — assumes the result is wrong and hunts evidence for every defect
7. [tyr-verdict](../tyr-verdict/SKILL.md) — adjudicates the findings, cuts false claims, and enforces the fixes

**Why a separate stage.** tdd's tests are written by the hand that writes the code, one cycle ahead of it — which is what makes them good design pressure and bad independent evidence. A test written alongside its implementation tends to assert what the implementation does, and a criterion can come out "tested" by a test that would pass with the feature deleted. Acceptance tests are written **from the brief, before the code exists**, by a stage that cannot see an implementation to agree with. They are the outer loop; tdd's cycles are the inner one. **The change is done when these pass** — not when tdd's own tests do.

**Upstream:** `.workflow/brief.md` — its **Acceptance criteria** (happy path and edge cases), **Key interfaces**, **Test seams & prior art**, **Deferred by design** and **Out of scope**. Without a brief, there is nothing to accept against: say so, and send the user to [agent-brief](../agent-brief/SKILL.md), or take the criteria from the user and write them into a brief first.

**Downstream:** [tdd](../tdd/SKILL.md) builds until every acceptance test is green, and [tyr-verdict](../tyr-verdict/SKILL.md) does not call GO while one is red.

## 📐 Calibrate

Say which you picked:

- **Trivial tier** (a localized fix behind an existing seam) — this stage is skipped; tdd's red test is the proof.
- **Standard** — one acceptance test per acceptance criterion.
- **Large / risky** — the same, per increment, plus one end-to-end scenario per user journey the increment completes.

## 🔎 Step 1: Find the outermost boundary

The boundary a user, a caller or another system actually meets: an **HTTP or RPC API**, a **CLI**, a **UI**, a **message or event consumer**, a **library's public API**. Prefer the repo's own conventions:

- [ ] **An acceptance, end-to-end or integration suite already exists** → write into it, in its style, with its runner. Read the brief's prior art and the suite before inventing anything.
- [ ] **None exists** → use the outermost seam the repo's test tooling can drive **without production infrastructure**: an in-process server with a test client, the CLI invoked as a subprocess, the library imported by its public name only. External systems the feature calls (payment providers, mail, other services) get fakes **at that boundary**, never mocks of your own internals.
- [ ] **Record the command that runs them** — and only them — e.g. a directory, a tag, a marker, a test-name pattern. The harness and tdd run this command on its own.

## ✍️ Step 2: One test per criterion

For each acceptance criterion in the brief, in order:

- [ ] **Name the test after the criterion** — the reader should find the criterion from the test name and back.
- [ ] **Given / When / Then**, through the boundary only: set up state the way a user or caller could (or with the system's own fixtures), act through the public entry point, assert on what comes back out — the response, the output, the persisted record *as read back through the system*, the emitted event.
- [ ] **No internals.** No imports beyond the public entry point, no reaching into private state, no assertions on how the result was computed. If the criterion can only be checked from inside, it isn't an acceptance criterion — mark it so (Step 4) and leave it to tdd.
- [ ] **Edge-case criteria get their own tests** — the unhappy paths are where independent tests earn their keep.
- [ ] **Respect the deferrals.** A test must not commit to a decision the brief deferred — no asserting on a storage engine, a framework, or a wire format the architect left open.
- [ ] **Assert the specific outcome, not just success.** "Returns 422 with code `CUTOFF_WINDOW`", not "returns an error". A test that passes for any failure tests nothing.

## 🔴 Step 3: Red, for the right reason

Run the acceptance command. **Every new test must fail**, and fail because **the behavior is missing** — an assertion on the outcome, a 404 from a route that doesn't exist yet, an unknown-command exit from the CLI.

- [ ] **A failure to load is not red.** An import error, a missing module, a compile error, a test that never ran — those prove nothing about the behavior. Where the public interface itself doesn't exist yet (a new library function, a new class), **declare it** — the signature the brief's Key interfaces name, failing with a not-implemented error — so the tests reach it and fail on behavior. That stub is the only production code this stage writes, and it is tdd's first target.
- [ ] **A test that passes now is a finding**, not a success: either the behavior already exists (the brief is wrong — feedback edge) or the test doesn't test the criterion (rewrite it).
- [ ] **The rest of the suite stays green.** This stage adds failing acceptance tests and nothing else.

Where a red/green checker is available, record its output now and run it again once tdd is done.

## 🗂️ Step 4: Record the mapping in the brief

Add or update this section of `.workflow/brief.md`, and log it under **Revisions**:

```markdown
**Acceptance tests** (stage 3 — tdd is done when these pass):
- **Command:** `<the command that runs only these>`
- [ ] Criterion 1 (tracer bullet) → `<test id>`
- [ ] Criterion 2 → `<test id>`
- [ ] Edge case: <criterion> → `<test id>`
- Not acceptance-testable: <criterion> — <why>; covered by tdd at <seam>
```

**Every criterion appears exactly once** — mapped to a test, or listed as not acceptance-testable with its reason. Nothing silently dropped.

## 🛑 Stopping rule

Stop when all four hold:

- [ ] Every acceptance criterion is mapped to one test, or explicitly marked not acceptance-testable with a reason.
- [ ] Every mapped test **fails on behavior** — none fails to load, none passes.
- [ ] The command that runs only the acceptance tests is recorded in the brief.
- [ ] Nothing else changed: no implementation beyond declared-but-unimplemented interfaces, the existing suite green.

Then stop. **Do not start making them pass** — that is tdd's job, and doing it here throws away the independence this stage exists for.

## Rules of Engagement

1. **From the brief, before the code.** The tests encode what was agreed, not what got built.
2. **Black box.** Through the outermost public boundary; fakes only for systems outside it.
3. **Red for the right reason.** Missing behavior, not a missing import.
4. **One criterion, one test, one name.** The mapping is the contract tdd and tyr-verdict check against.
5. **Acceptance tests change only through the brief.** If tdd finds one encodes a wrong reading, the fix is a brief revision first, then the test — never a test edited to go green.

## Subagents — optional

**The prior-art and boundary lookup delegates** — which suites exist, how they start the system, what fixtures they use: read-only, and it floods context with file excerpts. **Writing the tests stays here**, one criterion at a time against the brief. **Dispatch contract:** the prior, the target (described behaviorally), the context it cannot infer, the return shape, and *"report conclusions, not file excerpts."*

## Handoff

> `<n>` acceptance tests written and red for the right reason, `<m>` criteria marked not acceptance-testable. Run them with `<command>`. Run **[tdd](../tdd/SKILL.md)** next — it builds until every one of them passes.
