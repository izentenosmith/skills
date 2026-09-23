---
name: devils-advocate
description: Adversarial teardown that assumes everything just built is wrong and hunts concrete evidence for each defect. Use after refactor-review, before shipping — to red-team the diff, falsify passing tests, and surface unhandled edges. Over-reports on purpose; does not fix or judge.
---

# Devil's Advocate — assume it's broken, then prove it

Your job is to **dismantle the work**. Adopt the prior that the implementation is wrong, the tests are lying, and the feature does not do what it claims. Everything green is *guilty until proven innocent*. You are not here to be fair — you are here to find the failure that everyone else missed.

This skill is **stage 5 of a six-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [agent-brief](../agent-brief/SKILL.md) — turns those decisions into the pure-text plan TDD builds from
3. [tdd](../tdd/SKILL.md) — executes that plan red-green
4. [refactor-review](../refactor-review/SKILL.md) — cleans the structure once behavior is verified
5. **devils-advocate** (this skill) — assumes the result is wrong and hunts evidence for every defect
6. [tyr-verdict](../tyr-verdict/SKILL.md) — adjudicates your findings, cuts false claims, and enforces the fixes

**Upstream:** you receive a change that TDD built green and refactor-review cleaned. Treat that pedigree as *marketing*, not evidence. Read `.workflow/brief.md` where it exists — its acceptance criteria, edge cases and deferrals are the claims you are falsifying, and a deferral reported as a gap is a wasted finding. Where it doesn't exist (a standalone teardown, someone else's change), derive the claims from the diff and say that is what you did.

**Downstream:** your findings go into `.workflow/ledger.md` for [tyr-verdict](../tyr-verdict/SKILL.md) to adjudicate. You do not decide what is real — you gather the evidence and hand it over. Over-report; Tyr will cut the false claims.

> **On a loop iteration, read the ledger first.** Every finding Tyr already **REFUTED** carries a *Reopens only if* condition. Do not re-report one unless you have evidence that meets it — a re-reported refuted finding costs an adjudication and buys nothing, and it is how this loop stalls. New findings get new IDs; never reuse or renumber. Open by stating what you are carrying: *"Iteration 2 — F1 and F4 refuted, not revisited; attacking the three remediated slices and the surfaces they touch."*

> **The working files.** Both live in the repo under review. `.workflow/brief.md` holds the claims you are falsifying; `.workflow/ledger.md` holds the findings, verdicts and carried smells across iterations. The ledger is **append-only** — never rewrite a past iteration — and finding ids are stable and never reused.

## Mandate — invert the prior

- **A passing test is a claim, not a fact.** The claim is "this test would fail if the behavior broke." Falsify it: could the test pass even with the behavior removed or corrupted?
- **A satisfied acceptance criterion is a claim, not a fact.** The claim is "the system now does X." Falsify it: find the input or state where it does not.
- **Over-report, don't self-censor.** A suspicion you cannot yet prove still gets recorded (as unproven). It is cheaper for Tyr to cut a false positive than for a real defect to ship because you talked yourself out of it.
- **You do NOT fix.** Do not touch the implementation. Do not soften findings. Do not pre-judge which ones are "probably fine."
- **You do NOT run the suite.** It is green — [tdd](../tdd/SKILL.md) ran it and [refactor-review](../refactor-review/SKILL.md) ran it again — and a green run is the *claim* you are here to falsify, so running it a third time tells you nothing. Your evidence comes from reading the tests against the code. Execution — reproductions, mutation runs, booting the app, repeating a flaky test — is [tyr-verdict](../tyr-verdict/SKILL.md)'s verification step, which has one evidence re-run per finding for exactly this purpose. Hand Tyr the mutation to run; do not run it yourself.
- **You do NOT issue the verdict.** Confirmed/refuted is Tyr's call. Your call is only: *here is a suspicion, and here is the evidence I found for it.*

## Subagents — fan out by default

Delegation pays here for two reasons: bias, and wall time.

**Bias.** If you have just spent the session designing, building and cleaning this change, the transcript above you is a record of the agent making it work. "Assume the implementation is wrong and the tests are lying" is then an instruction fighting that history — and the history usually wins. **An agent that never watched the code get written owes it nothing.**

**Wall time.** The attack surfaces below are independent. A single delegate handed all of them works them one after another — measured runs of that shape take ten to fifty minutes, nearly all of it serial turns at a context that only grows. Several delegates working one surface each finish in the time of the longest slice.

**Default: fan out by attack surface.** One delegate per target below; on a small diff merge adjacent targets, but never below three delegates. Dispatch every delegate in **one message, in the background**, then do nothing but wait — collect all of them before you rank anything, the same rule [tyr-verdict](../tyr-verdict/SKILL.md) applies to its verifiers. A delegate that never returns is written into the ledger as an **unattacked surface**, not silently dropped.

**Exception — one whole-teardown delegate** only when the diff is a single module and its tests, small enough to read in a handful of calls. Anything larger fans out.

Three rules for every delegate:

- **Read-only.** The mandate stands for delegates: they gather evidence and do not touch the implementation.
- **No execution.** Delegates read tests against code; they do not run the suite, a single test, the app, or a database, and they do not mutate files to see what happens. A delegate that believes only execution can settle a claim records it **unproven** and names the exact run — that run is Tyr's to make. Say this in the dispatch verbatim; a delegate briefed on "find the failure" will otherwise reach for the test runner within its first few calls and spend most of its budget there.
- **Negative results are required.** Every delegate reports "attacked, found nothing" for its target when it found nothing. Silence reads identically to a delegate that ran out of budget, and an unattacked surface must never reach Tyr looking clean.

**Dispatch contract.** A delegate starts with no history, so every dispatch carries six things:

1. The **prior** — the adversarial stance stated verbatim, because a subagent briefed neutrally reviews neutrally.
2. The **target** — which surface it owns, and that the others are covered.
3. The **context it cannot infer, pasted inline** — the acceptance criteria, the resolved edge cases, the **deferrals** (a delegate that doesn't know a decision was deliberately deferred reports it as a gap), and the ids and *Reopens only if* conditions of every refuted finding. Do **not** point it at `.workflow/brief.md`, `.workflow/ledger.md`, or the session transcript: the ledger is the history you are paying to escape and grows with every iteration, and the transcript is the build narrative itself. The diff is the only thing it should open, and it should open it once.
4. The **no-execution rule** above, verbatim.
5. A **budget** — around twenty-five tool calls. A delegate that runs out reports what it covered and what it did not, rather than reading on.
6. The **return shape** — the finding format below, verbatim, plus one line per surface swept clean — and an explicit *"report findings and evidence, not file excerpts."*

A delegate's report is evidence, not truth — weigh it the way Tyr will weigh yours. De-duplicate across delegates, rank, and append the findings to the ledger **as returned**; rewriting them costs a second generation of the same text and buys nothing.

## Attack surface — work one target at a time

Walk each of these deliberately. For each, state what you attacked and what you found (including "attacked, found nothing" — a negative result is a real result).

- [ ] **Acceptance criteria.** For each criterion in the brief: does the behavior actually hold, or does its test pass vacuously (asserting nothing meaningful, asserting on setup, or asserting a value that would be true even if the feature were deleted)?
- [ ] **Test integrity.** Would each test actually fail if the behavior broke? Mentally mutate the implementation (invert a condition, drop a branch, return a constant) — does a test go red? A test no mutation can break tests nothing.
- [ ] **Listed edge cases.** The unhappy paths the brief called out — are they genuinely handled, or stubbed/short-circuited to make a test pass?
- [ ] **Unlisted unhappy paths.** Empty/missing/null input, boundary and off-by-one values, concurrent access, ordering assumptions, partial failure and rollback, duplicate/retry.
- [ ] **Contracts & invariants.** Can a documented invariant be violated through the public interface? Did the change break a contract an existing caller depends on (backwards-compatibility)?
- [ ] **Security & permissions.** Missing authorization gate, an isolation/tenancy boundary that can be crossed, sensitive data exposed or logged.
- [ ] **Error handling.** Swallowed errors, errors surfaced at the wrong layer or with the wrong shape, failures that leave state half-written.
- [ ] **Coupling & state leakage.** Did the refactor introduce hidden shared state, order-dependence between tests, or a leak that only bites under real load?
- [ ] **Performance & scale.** Repeated work, fan-out, unbounded growth, or a hot path that is fine on fixture data and falls over at real volume.

## Evidence rule

Every finding must carry **concrete evidence**, not an assertion of doubt — and every kind of evidence here is produced by **reading**, never by running. Acceptable evidence, strongest first:

1. **A code path that contradicts the claim** — the branch, guard, or missing case, described behaviorally (what it does / fails to do), not by line number.
2. **A test that survives a mutation** — name the test, name the mutation (invert the condition, drop the branch, return a constant, delete the feature), and show from the test body why its assertions would still hold. Reasoned, not executed.
3. **A constructed breaking case** — specific inputs/state, traced through the code path, → what the code yields vs. what the claim says it should. Construct it; don't just describe it. Trace it; don't run it.
4. **A missing branch** — the input class that has no handling at all.

Where a claim genuinely cannot be settled by reading — timing, concurrency, behavior against a real database, a test that fails intermittently — do **not** start running things. Record the finding with confidence **unproven**, name the exact run that would settle it, and leave the run to Tyr. That is what the evidence re-run is for, and it is the single largest place a teardown loses time.

If you have a real suspicion but cannot yet produce any of the above, record it anyway with confidence **unproven** — do not drop it, and do not inflate it into a confirmed defect. But an unproven finding must name **what evidence would settle it**: the specific reproduction to attempt, the mutation to try, the caller to check. Tyr grants one evidence re-run per unsettled finding and then escalates it to the user, so a suspicion that arrives with no route to proof spends that re-run on nothing.

## Output — an unadjudicated findings list

Append to `.workflow/ledger.md` under the current iteration, labelled clearly as **unadjudicated** — these are suspicions with evidence, not confirmed defects. For each finding:

```markdown
### F<id>
- **Target:** which acceptance criterion / behavior / seam / test this challenges
- **Claim challenged:** the "fact" you are trying to falsify (e.g. "the cutoff check rejects same-day requests")
- **Evidence:** the contradicting path, mutation-surviving test, constructed breaking case, or missing branch (per the evidence rule)
- **Breaking case:** inputs/state → what the code yields vs expected, traced not executed (omit only if the finding is a pure missing-branch gap)
- **Confidence:** proven | unproven
- **Would be settled by:** (unproven only) the specific run or check that would confirm or refute it — this is what Tyr executes
- **Severity hint:** blocker | major | minor (a hint for Tyr, not a verdict)
```

Rank the list most-severe first. Do not summarize away the weak ones — Tyr needs the full slate.

Also record the attack surfaces you swept and found nothing on. A surface that never appears in the ledger is indistinguishable from one that was never attacked, and Tyr cannot tell a clean result from a gap.

## Handoff

After emitting the findings, prompt the user:

> The teardown is complete — <n> findings recorded in `.workflow/ledger.md`, unadjudicated. Run **[tyr-verdict](../tyr-verdict/SKILL.md)** next to weigh each against its evidence, cut the false claims, and turn what survives into fixes.
