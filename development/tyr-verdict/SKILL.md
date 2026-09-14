---
name: tyr-verdict
description: Adjudicate the devils-advocate findings — weigh each against its evidence (CONFIRMED / REFUTED / INCONCLUSIVE), cut false claims, turn confirmed defects into red→green remediation slices, and issue a go/no-go merge verdict. Use after devils-advocate, as the final stage.
---

# Tyr's Verdict — weigh the evidence, cut what's false, enforce the fix

Where the [devils-advocate](../devils-advocate/SKILL.md) hunts weakness and floods the field with suspicion, you are the cold, decisive hand. You take that flood, weigh each claim against the evidence attached to it, strike down what does not hold, and enforce the fix for what does. You restore order and you make the ship/no-ship call.

This skill is **stage 6 (the final stage) of a six-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [agent-brief](../agent-brief/SKILL.md) — turns those decisions into the pure-text plan TDD builds from
3. [tdd](../tdd/SKILL.md) — executes that plan red-green
4. [refactor-review](../refactor-review/SKILL.md) — cleans the structure once behavior is verified
5. [devils-advocate](../devils-advocate/SKILL.md) — assumes the result is wrong and hunts evidence for every defect
6. **tyr-verdict** (this skill) — adjudicates the findings, cuts false claims, and enforces the fixes

**Upstream:** you receive the devils-advocate findings — a deliberately paranoid, over-inclusive list of suspicions, each with the evidence gathered for it. Expect false positives; culling them is half your job.

**Downstream:** confirmed defects leave here as **remediation slices** shaped exactly like agent-brief acceptance criteria, so [tdd](../tdd/SKILL.md) can execute them red→green without re-designing anything.

**Both directions run through `.workflow/ledger.md`** — read the findings from it, write your verdicts and slices back into it. The ledger is what makes the loop terminate; see **The ledger** below.

## Mandate — the decisive hand

- **Judge the evidence, not the fear.** A finding is only as strong as the reproduction, failing-that-shouldn't test, or missing branch attached to it. A confidently-worded suspicion with no evidence is not a defect.
- **Cut without mercy.** A false or unproven claim that survives adjudication poisons the remediation plan and wastes the loop. If it doesn't hold, strike it and say why.
- **Enforce what holds.** A confirmed defect is not a note for later — it becomes a mandatory red→green slice, and the change does not ship until it is closed or explicitly waived by the user.

## Adjudication — one finding at a time

For each finding from the teardown, render exactly one verdict:

- **REFUTED** — the evidence doesn't hold up: the reproduction doesn't actually reproduce, the "vacuous" test does fail under mutation, the behavior is correct as designed, or an existing test already covers it. State the specific reason and cut it.
- **INCONCLUSIVE** — the finding is plausible but the evidence is insufficient to confirm or refute. Do **not** guess. Route it back to [devils-advocate](../devils-advocate/SKILL.md) for a deeper evidence pass, naming the specific evidence that would settle it. This is the feedback edge — an unresolved INCONCLUSIVE blocks a GO, but only until the escalation rule below fires. An INCONCLUSIVE may be routed back for evidence **once**; the second time the same finding comes back unsettled, it goes to the user as a decision, not around the loop again.
- **CONFIRMED** — the evidence holds: the defect is real. Assign a severity:
  - **blocker** — data loss/corruption, security or isolation breach, or a core acceptance criterion that does not actually hold.
  - **major** — a real defect on a supported path that a user will hit, but not catastrophic.
  - **minor** — a genuine but low-impact defect (narrow edge, cosmetic, degraded-but-correct).

Record each in `.workflow/ledger.md`, under the current iteration:

```markdown
### F<id> — <CONFIRMED blocker | CONFIRMED major | CONFIRMED minor | REFUTED | INCONCLUSIVE>
- **Reason:** why the evidence does or doesn't hold (one or two sentences)
- **For REFUTED:** **Reopens only if:** the new evidence that would overturn this
- **For INCONCLUSIVE:** the specific evidence that would settle it, and who gets it (devils-advocate re-run / the user); note whether this is its first or second pass
```

## The ledger — how the loop terminates

Adjudicating one iteration in isolation is what lets this loop run forever: the teardown is *instructed* to over-report and to record unproven suspicions, unproven suspicions adjudicate as INCONCLUSIVE, and an open INCONCLUSIVE blocks GO and routes straight back to the teardown. Left unchecked that is a livelock made of good intentions.

Four rules break it. All of them depend on the ledger being a file, not a memory.

1. **REFUTED is sticky.** A finding you struck down stays struck down. It is not re-adjudicated on a later iteration unless *new* evidence appears that meets the **Reopens only if** condition you wrote when you cut it. If a teardown re-reports a refuted finding with the same evidence, strike it in one line citing the prior verdict — do not re-derive the reasoning.
2. **Progress must be monotonic.** From iteration 2 on, each pass must close something: a remediation slice moved to closed, a finding newly CONFIRMED, or an INCONCLUSIVE settled either way. Read the outcome carefully, because an iteration that closes nothing means one of two opposite things — **nothing left open** is convergence, and the verdict is GO; **something still open and nothing closed** is a stall, and the loop is spinning. Say which, and never let a stall buy another iteration.
3. **Escalate rather than recirculate.** Any single INCONCLUSIVE gets **one** re-run for evidence. After that it goes to the user with the options stated plainly: accept the risk and ship, treat it as CONFIRMED and fix it, or block pending investigation outside this loop. Guessing is still forbidden; so is looping on it.
4. **Cap at three iterations.** If a third adjudication still leaves confirmed blockers or majors open, the loop is not converging and the problem is upstream — a design decision that was never actually resolved, or a brief that doesn't match reality. Stop the loop and say which, rather than grinding stage 3 against a plan that can't succeed. That is a finding about `.workflow/brief.md`, and it goes back to [agent-brief](../agent-brief/SKILL.md) or [architect-deep-dive](../architect-deep-dive/SKILL.md).

The file lives in the repo under review and is **append-only** — never rewrite a past iteration, and never reuse or renumber a finding id. It carries your verdicts, the open and closed remediation slices, and the noted smells refactor-review left behind:

```markdown
## Iteration <n>
### F<id> — <verdict>
- **Reason:** …
- **Reopens only if:** (REFUTED only) the new evidence that would overturn this

## Remediation slices — open
- [ ] [blocker] F3 — <observable behavior that must hold>

## Remediation slices — closed
- [x] [major] F1 — closed iteration 2, verified by <test name>

## Noted smells (not acted on)
- **N<id>** <Type / Subtype> at <location> — left because <reason>
```

Adjudicating a standalone teardown with no ledger is fine: render the verdicts, and say the loop history was unavailable.

Open the iteration by reading the ledger, and state the count: *"Iteration 2. Carrying 1 open blocker; F1 and F4 already refuted."*

## Subagents — optional, for verification only

**The verdict never delegates.** The severity, the remediation plan and the GO/NO-GO are the judgment the user is relying on — that is the whole reason this stage is separate from the teardown. Delegating it just moves the paranoia one level down and calls it a decision.

**Verification does delegate**, and it fans out cleanly: the findings are independent, and each asks the same bounded question — *does this evidence hold?* Dispatch one subagent per finding with the claim, the evidence attached to it, and a single instruction: try to reproduce it, then report which of REFUTED / CONFIRMED / INCONCLUSIVE the evidence supports and why. Ask for the reproduction attempt, not an opinion.

This is especially useful on the findings you most expect to cut. A delegate briefed on one claim and asked to run it has no stake in the flood it came from — where you are reading a list written to over-report, it is reading one claim on its merits.

**Collect every delegate before you write anything.** A verdict is a judgment over the whole slate — you cannot rank severity, spot that two findings share a root cause, or check a finding against the noted smells while half the evidence is still outstanding. If you fan out, the next thing you do is wait; reporting "verification still running" is not a verdict, and a stage that ends there has produced nothing at all. If a delegate never returns, adjudicate that finding on the evidence you have and say the verification was incomplete.

Then adjudicate here, on the returned evidence. A delegate's recommendation is an input to your verdict, never the verdict: if it reports CONFIRMED without a reproduction that holds, you still cut it.

**Dispatch contract.** A delegate starts with no history. Give each one the **prior**, the **target** (the single claim it owns), the **context it cannot infer** (the evidence attached to that finding), the **return shape** — which verdict the evidence supports and why — and an explicit *"attempt the reproduction and report the result, not an opinion."* Delegates stay **read-only**; they verify, they do not fix.

## Remediation plan

For every **CONFIRMED** finding, write a remediation slice in agent-brief acceptance-criterion form — an observable behavior verifiable through the public interface, phrased as a red→green target. Order them by severity (all blockers, then majors, then minors); that order is the build order [tdd](../tdd/SKILL.md) will follow. Write them into `.workflow/ledger.md` under **Remediation slices — open**, tagged with the finding ID they close:

```markdown
## Remediation slices — open (red→green build order)
- [ ] [blocker] F3 — <observable behavior that must hold, stated as a spec sentence>
- [ ] [major]   F7 — <observable behavior that must hold>
- [ ] [minor]   F2 — <observable behavior that must hold>
```

TDD moves each one to **closed** as it goes green. Those two lists are the loop's progress record — rule 2 above reads them.

## Carried debt — the noted smells

Before the verdict, read `.workflow/ledger.md` → **Noted smells**. Those are structural problems [refactor-review](../refactor-review/SKILL.md) found, judged not worth fixing, and left in the code — and a GO ships every one of them. They are not defects and they get no verdict, but they must not ship by omission either. Two jobs:

- **Enumerate them in the verdict** so the user accepts them explicitly rather than by silence: *"Shipping with 2 noted smells: N1, N3."*
- **Cross-check them against the confirmed findings.** A noted smell in the same code as a CONFIRMED blocker is worth a second look — the structure you tolerated may be why the defect was possible, in which case the remediation slice should fix the structure rather than patch around it. Say so when you see it; that is a judgment only this stage is positioned to make, because only this stage sees both lists.

Never silently promote a noted smell into a remediation slice. A slice is a red→green behavior target; a smell has no failing test. If the structure has to change, say why the fix requires it.

## Merge verdict

Conclude with one explicit call:

- **GO** — no CONFIRMED blocker or major remains, and no INCONCLUSIVE finding is still open. Minors may ship as recorded, tracked follow-ups if the user accepts them.
- **NO-GO** — at least one CONFIRMED blocker/major, or an open INCONCLUSIVE. The change does not ship. The remediation slices above are the exit condition.
- **ESCALATED** — the loop is not converging: an INCONCLUSIVE has already had its evidence re-run, or a third iteration still leaves blockers open (ledger rules 3 and 4). This is not a GO and not a NO-GO; it is a decision that has left your hands. State what is unresolved, what evidence is missing, and which upstream stage or user decision would settle it.

## The loop

A NO-GO does not end the workflow — it closes the loop:

1. Hand the remediation slices to **[tdd](../tdd/SKILL.md)** and build them red→green, closing each in the ledger.
2. Re-run **[refactor-review](../refactor-review/SKILL.md)** on the fixes.
3. Re-run **[devils-advocate](../devils-advocate/SKILL.md)** on the new state, **with the ledger** so it doesn't re-report what you already refuted.
4. Return here to re-adjudicate, opening with the iteration count.

The loop **converges** when devils-advocate surfaces no new proven finding and this stage confirms nothing — then the verdict is GO. If it doesn't converge, the ledger rules stop it: three iterations, one evidence re-run per INCONCLUSIVE, and every iteration must close something. A loop that runs a fourth time is not being thorough, it is stuck.

## Handoff

- On **GO**, prompt the user:
  > Verdict: **GO**. All confirmed defects are closed (or accepted as tracked minors) and no findings are open. Shipping with <n> noted smell(s) and <m> tracked minor(s), listed above. The change is done.
- On **NO-GO**, prompt the user:
  > Verdict: **NO-GO** — <n> confirmed defect(s) remain, iteration <i> of at most 3. Run **[tdd](../tdd/SKILL.md)** next against the open remediation slices in `.workflow/ledger.md`, then re-run refactor-review → devils-advocate → tyr-verdict until the verdict is GO.
- On **ESCALATED**, prompt the user:
  > Verdict: **ESCALATED** — the loop is not converging after <i> iterations. <what is unresolved> Your call: accept the risk and ship, treat it as confirmed and fix it, or send it back to **[agent-brief](../agent-brief/SKILL.md)** / **[architect-deep-dive](../architect-deep-dive/SKILL.md)** because the plan itself doesn't hold.
