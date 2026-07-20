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

## Mandate — the decisive hand

- **Judge the evidence, not the fear.** A finding is only as strong as the reproduction, failing-that-shouldn't test, or missing branch attached to it. A confidently-worded suspicion with no evidence is not a defect.
- **Cut without mercy.** A false or unproven claim that survives adjudication poisons the remediation plan and wastes the loop. If it doesn't hold, strike it and say why.
- **Enforce what holds.** A confirmed defect is not a note for later — it becomes a mandatory red→green slice, and the change does not ship until it is closed or explicitly waived by the user.

## Adjudication — one finding at a time

For each finding from the teardown, render exactly one verdict:

- **REFUTED** — the evidence doesn't hold up: the reproduction doesn't actually reproduce, the "vacuous" test does fail under mutation, the behavior is correct as designed, or an existing test already covers it. State the specific reason and cut it.
- **INCONCLUSIVE** — the finding is plausible but the evidence is insufficient to confirm or refute. Do **not** guess. Route it back to [devils-advocate](../devils-advocate/SKILL.md) for a deeper evidence pass (name what evidence would settle it), or escalate to the user for a decision. This is the feedback edge — an unresolved INCONCLUSIVE blocks a GO.
- **CONFIRMED** — the evidence holds: the defect is real. Assign a severity:
  - **blocker** — data loss/corruption, security or isolation breach, or a core acceptance criterion that does not actually hold.
  - **major** — a real defect on a supported path that a user will hit, but not catastrophic.
  - **minor** — a genuine but low-impact defect (narrow edge, cosmetic, degraded-but-correct).

Record each as:

```markdown
### Finding <id> — <CONFIRMED blocker | CONFIRMED major | CONFIRMED minor | REFUTED | INCONCLUSIVE>
- **Reason:** why the evidence does or doesn't hold (one or two sentences)
- **For INCONCLUSIVE:** the specific evidence that would settle it, and who gets it (devils-advocate re-run / the user)
```

## Remediation plan

For every **CONFIRMED** finding, write a remediation slice in agent-brief acceptance-criterion form — an observable behavior verifiable through the public interface, phrased as a red→green target. Order them by severity (all blockers, then majors, then minors); that order is the build order [tdd](../tdd/SKILL.md) will follow.

```markdown
## Remediation slices (red→green build order)
- [ ] [blocker] <observable behavior that must hold, stated as a spec sentence>
- [ ] [major]   <observable behavior that must hold>
- [ ] [minor]   <observable behavior that must hold>
```

## Merge verdict

Conclude with one explicit call:

- **GO** — no CONFIRMED blocker or major remains, and no INCONCLUSIVE finding is still open. Minors may ship as recorded, tracked follow-ups if the user accepts them.
- **NO-GO** — at least one CONFIRMED blocker/major, or an open INCONCLUSIVE. The change does not ship. The remediation slices above are the exit condition.

## The loop

A NO-GO does not end the workflow — it closes the loop:

1. Hand the remediation slices to **[tdd](../tdd/SKILL.md)** and build them red→green.
2. Re-run **[refactor-review](../refactor-review/SKILL.md)** on the fixes.
3. Re-run **[devils-advocate](../devils-advocate/SKILL.md)** on the new state.
4. Return here to re-adjudicate.

The loop **converges** when devils-advocate surfaces no new proven finding and this stage confirms nothing — then the verdict is GO.

## Handoff

- On **GO**, prompt the user:
  > Verdict: **GO**. All confirmed defects are closed (or accepted as tracked minors) and no findings are open. The change is done.
- On **NO-GO**, prompt the user:
  > Verdict: **NO-GO** — <n> confirmed defect(s) remain. Run **[tdd](../tdd/SKILL.md)** next against the remediation slices above, then re-run refactor-review → devils-advocate → tyr-verdict until the verdict is GO.
