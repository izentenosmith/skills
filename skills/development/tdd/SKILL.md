---
name: tdd
description: Test-driven development via the red-green-refactor loop, building in vertical slices. Executes an agent-brief build plan when one exists (stage 4 of the seven-stage workflow, building until stage 3's acceptance tests pass) and works standalone when it doesn't. Use when the user wants to build a feature or fix a bug test-first, mentions "red-green-refactor", wants integration tests, or is acting on a build plan or remediation slices.
---

# Test-Driven Development

## Where this fits

This is **stage 4 of a seven-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [agent-brief](../agent-brief/SKILL.md) — turns those decisions into the pure-text plan the rest builds from
3. [acceptance-tests](../acceptance-tests/SKILL.md) — turns the plan's acceptance criteria into failing black-box tests, before any code
4. **tdd** (this skill) — builds it red-green until the acceptance tests pass
5. [refactor-review](../refactor-review/SKILL.md) — cleans the structure once behavior is verified
6. [devils-advocate](../devils-advocate/SKILL.md) — assumes the result is wrong and hunts evidence for every defect
7. [tyr-verdict](../tyr-verdict/SKILL.md) — adjudicates the findings, cuts false claims, and enforces the fixes

**You execute the agent brief's contract**, read from `.workflow/brief.md`. Its **Acceptance criteria** are already ordered as a build order (first = tracer bullet, then incremental slices, edge cases marked); its **Key interfaces (test seams)** and **Test seams & prior art** tell you where to test and what to mirror. Do not re-derive the plan — read it from the brief.

**The acceptance tests are your outer loop.** Where [acceptance-tests](../acceptance-tests/SKILL.md) ran, the brief's **Acceptance tests** section maps every criterion to a failing black-box test and names the command that runs them. Your red→green cycles are the inner loop; **you are done when that command passes**. Never edit an acceptance test to make it pass: if one encodes a wrong reading of the brief, that is the feedback edge — revise the brief first, log it, then change the test.

> **Feedback edge — the brief is a living contract.** If, while implementing, you find that the brief is wrong, incomplete, or contradicted by reality — a seam that doesn't exist, an edge case that can't behave as specified, an acceptance criterion that conflicts with another — **STOP. Do not silently code around it.** Surface the contradiction, **edit `.workflow/brief.md` in place** to match the new understanding, log the change in its **Revisions** section, then resume the loop against the corrected contract. Never fork the brief; the file stays the single authority.

> **The working files.** The pipeline keeps `.workflow/brief.md` (the plan you execute) and `.workflow/ledger.md` (findings and remediation slices across loop iterations) in the repo under review. The brief is revised in place, never forked; the ledger is append-only, and its finding IDs are stable — `F1` in iteration 1 is the same finding in iteration 3. Running standalone, neither file exists: work from what you have and say so.

> **Loop-back edge.** This stage also runs as the fix step of the closing loop: when [tyr-verdict](../tyr-verdict/SKILL.md) returns NO-GO, its confirmed defects arrive as remediation slices already shaped like acceptance criteria, in `.workflow/ledger.md` under the last iteration's `### Remediation slices`. Execute them here red-green exactly as you would a fresh brief. As each one goes green, close it by appending `- [x] F<id> — verified by <test name>` under `### Closed slices` in a new `## Iteration <n+1>` of the ledger — never tick or move the line tyr-verdict wrote, because the ledger is an append-only log and the opening line and the closing line together are the record. That record is how the loop proves it is making progress rather than circling. Each closed slice is its own save point, exactly as a criterion is (see **Save points**) — a remediation that breaks something else must be revertable without losing the ones that held. Then send the result back through refactor-review → devils-advocate → tyr-verdict.

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

Stages 1–3 already resolved the interface, chose and prioritized the behaviors, got the user's approval, and wrote the acceptance tests. Re-asking any of that reopens settled decisions and wastes the stages that settled them. Read `.workflow/brief.md` and take:

- [ ] **The interface** ← **Key interfaces (test seams)**. Test through the highest seam it names.
- [ ] **The build order** ← **Acceptance criteria**, top to bottom, first as the tracer bullet.
- [ ] **The conventions** ← **Test seams & prior art**. Mirror what it points at — new tests go in the test file it names, in the style it names, not a new file of your own. Every criterion marked **Edge case** gets its own test, named for the edge it pins (`…_boundary_is_exclusive`, `…_both_codes_surface`), so the suite reads as the brief's checklist.
- [ ] **The limits** ← **Out of scope** and **Deferred by design**. A deferred detail stays deferred; do not let a test commit to it.
- [ ] **The finish line** ← **Acceptance tests**: run the command once now and see every mapped test red. A tracer bullet that turns its criterion's acceptance test green is the clearest progress signal you have.
- [ ] **The things that aren't tests** ← **Ship checklist**, where the brief has one: the rollout, compatibility and observability work that no acceptance test can prove. Build the items that are code (the flag, the log event, the migration) as part of the slice they belong to, and tick each **in the file, naming where it landed**. Items that happen after merge stay unticked; they are not yours to tick.
- [ ] **The standing** ← **Status**: a brief still marked `draft — awaiting approval` has not been agreed. If the user sent you here to build it, that is the approval — set it to `approved` and log it under Revisions. Otherwise say it is unapproved before you build on it.

**When you were started for one track** of a brief that lists **Parallel tracks**, the brief belongs to the session that started you, and you build only your part of it:

- Build your track's criteria, in their order, and touch only your track's area. A criterion that needs a change in another track's area, or in a seam the brief fixed, is a question for that session. Don't make the edit.
- Read the brief at the path you were given, but don't write to it. Record your ticks, each naming the test that proves it, in your stage log. The owning session ticks the brief when it merges your track.
- Your Base is the commit you were started from: track 0's seams, already built.

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
- [ ] Where the brief names **domain primitives** or the change handles a security-relevant value, build those types first and test them the way [domain-primitives.md](domain-primitives.md) describes — normal, boundary, invalid and extreme input, immutability, and no raw value escaping into logs or errors

Design references for this step: [deep-modules.md](deep-modules.md) (power behind a small interface), [interface-design.md](interface-design.md) (shape it to be testable), [mocking.md](mocking.md) (what to leave real vs. substitute), [domain-primitives.md](domain-primitives.md) (security-relevant values as validated types, and the tests they need).

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

#### Red, for the right reason

Run each new test and **read the failure before writing any production code**. RED counts only when the test reaches the behavior and fails on it: an assertion on the outcome, `DID NOT RAISE`, the wrong code or value coming back.

- **A failure to load or call is not red.** `ImportError`, `NameError`, `AttributeError`, a `TypeError` from a signature or keyword that doesn't exist yet, a missing fixture — the test never reached the behavior, so it proves nothing about it. Add the least scaffolding that lets it get there (the seam, with a default that keeps today's behavior; the function, returning nothing), run it again, and go green only once it fails on the behavior.
- **A test that passes the first time it runs has not been red.** Either earlier code already does the job or the test doesn't test it. Break the code on purpose — invert the comparison, drop the rule — watch the test fail for the right reason, then restore it.

**Keep a cycle record as you go** — one row per slice, in build order — and put it in your response. The quoted failure is the evidence that each slice was its own red→green, and that the red was the missing behavior:

```markdown
| # | Criterion | Test | Red — the failure, quoted | Green — what made it pass |
|---|---|---|---|---|
| 1 | Tracer: a late invoice is charged a fee | `test_late_invoice_is_charged_a_fee` | first run `TypeError: unexpected keyword 'today'` — not red, added the seam; then `assert 0 == 15` | `late_fee` joins the charge rules |
| 2 | The rate reads from the plan | `test_fee_rate_reads_from_plan` | `assert 15 == 50` | `late_fee` reads `plan.rate` |
| 3 | Edge case: no fee on the due date | `test_no_fee_on_due_date_is_exclusive` | passed on first run; with `>=` → `assert 15 == 0` | already held — restored `>` |
```

#### Save points — one commit per green slice

When a slice goes green — its test, the code that passes it, and nothing else — **commit it before writing the next test**. A red you cannot get past on slice 4 should cost you slice 4, not slices 1–3: with a commit behind every green, "back to the last state that worked" is one command instead of a reconstruction, and the loop's later iterations fix a tree they can always return to.

- **Record where you started, before the first test.** Write the current commit into the brief as `**Base:** <sha>`. It is what refactor-review, devils-advocate and the harness diff the change against — once you commit, `HEAD` stops meaning "before the change".
- **Never on the default branch.** If you are on it, create a working branch first, named the way the repo names them.
- **One slice, one commit.** Stage the files that slice touched, by name — never `git add -A`, which sweeps in work that isn't yours. The message states the behavior the slice added, in the criterion's words. `.workflow/` goes in only if the repo already tracks it.
- **Only on green.** A commit is a state someone can return to; a red one is a trap. Scaffolding that let a test reach the behavior goes in with the slice it served.
- **Structure and behavior never share a commit.** A refactor step is its own commit, made on a green suite.
- **Local only.** Do not push, squash, amend or rebase — what happens to these commits before merge is the user's call.

**Where you can't commit** — the directory is not a git work tree, the user or the repo's rules say not to, or a harness is driving this stage and makes the save points itself — say so in one line and carry on. Do not create a repository to satisfy this rule; the cycle record above is then the only trail.

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

- [ ] Every **acceptance criterion in `.workflow/brief.md`** is implemented and has a test that verifies it — check each one off **in the file, in place, naming that test**: `- [x] <the criterion, as written> — verified by <test name>` (on a criterion that wraps, append to its last line). The tick is what the next loop iteration, devils-advocate and tyr-verdict read to find which test proves which criterion, so a bare `[x]` is a claim with nothing to check it against. (Running standalone: every behavior agreed in Planning.)
- [ ] On a loop-back pass: every **remediation slice** you were handed is closed in `.workflow/ledger.md` — one `### Closed slices` line per slice, naming the test that verifies it
- [ ] **The acceptance tests are GREEN** — the command in the brief's **Acceptance tests** section passes, and each mapped criterion is ticked there. (No acceptance stage ran: skip this line and say so.)
- [ ] The full suite is GREEN
- [ ] **Every green slice is committed**, the brief's `**Base:**` names the commit the work started from, and the tree holds no uncommitted change — or you have said, in one line, why this build has no save points
- [ ] Every **Ship checklist** item this build delivers is ticked in the brief, naming where it landed; the ones left open are listed in your response, so they reach the verdict as a count and not as a silence

Then the structure gets cleaned, in [refactor-review](../refactor-review/SKILL.md) — that is stage 5, not a checklist item here, and it has its own severity rules and stopping rule. Invoke it against the new changes only, apply what it prescribes as **structural-only** changes, and keep the suite GREEN through every step.

The division of labor is strict: **TDD gets you to verified behavior, refactor-review gets you to clean structure.** Do not skip it.

## Handoff — into the adversarial close

Green tests and a clean diff are a *claim* of correctness, not proof of it. Once the suite is GREEN, the change goes through the rest of the pipeline:

1. Run **[refactor-review](../refactor-review/SKILL.md)** (stage 5) — clean the structure on a green suite.
2. Run **[devils-advocate](../devils-advocate/SKILL.md)** (stage 6) — assume everything you built is wrong and hunt evidence for each defect.
3. Run **[tyr-verdict](../tyr-verdict/SKILL.md)** (stage 7) — adjudicate those findings and issue a go/no-go verdict.

If tyr-verdict returns **NO-GO**, its remediation slices come back to this skill as a new red→green build order (see the loop-back edge above). The loop converges when devils-advocate turns up nothing new and tyr-verdict confirms nothing.

## Checklist Per Cycle

```
[ ] Security trigger: refusal tested alongside the permitted case
[ ] Seen red on the behavior — the failure read and recorded, not a load error
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
[ ] Green slice committed on its own (or said once why this build has no save points)
```
