---
name: refactor-review
description: Review the current diff for code smells and prescribe structural refactorings. Use after a TDD cycle or before merging to catch smells the green-bar didn't. Reviews new changes only; structural fixes are behavior-preserving.
---

# 🔎 Code Review Checklist (New Changes Only)

## Where this fits

This is **stage 4 of a six-stage workflow**:

1. [architect-deep-dive](../architect-deep-dive/SKILL.md) — resolves the design tree, scope, and edge cases
2. [agent-brief](../agent-brief/SKILL.md) — turns those decisions into the pure-text plan TDD builds from
3. [tdd](../tdd/SKILL.md) — executes that plan red-green
4. **refactor-review** (this skill) — cleans the structure once behavior is verified
5. [devils-advocate](../devils-advocate/SKILL.md) — assumes the result is wrong and hunts evidence for every defect
6. [tyr-verdict](../tyr-verdict/SKILL.md) — adjudicates the findings, cuts false claims, and enforces the fixes

TDD gets you to verified behavior; this stage gets you to clean structure. It runs on a GREEN suite and keeps it GREEN.

This is the **guideline** that drives a review. It leans on two reference catalogs:

- [code-smells.md](code-smells.md) — how to *name* what's wrong (the symptom)
- [refactoring-techniques.md](refactoring-techniques.md) — how to *fix* it (the treatment)
- [comments.md](comments.md) — which comments are the smell and which earn their place (used for the `Dispensables / Comments` finding)

Reviews target **new changes only**. Refactorings are **behavior-preserving** — no new features, no bug fixes mixed in.

---

## 📐 Calibrate the pass

Match the review to the diff, and say which you picked:

- **Small diff** (one module, a handful of functions) — one inline pass over Step 1, then act. Don't produce a formal findings table for three functions.
- **Large diff** (several modules, or a new subsystem) — work Step 1 by smell category, optionally fanned out to subagents, then reconcile before prescribing anything.

Where `.workflow/brief.md` exists, read its **Out of scope** and **Deferred by design** sections first. Speculative Generality and a deliberately deferred decision look identical in a diff, and so do Duplicate Code and a duplication the architect ruled *accidental* and chose to keep apart. Both are smells you would otherwise "fix" straight through a resolved decision.

---

## 🛑 Step 1: Smell Identification

*Identify the code smells present in this pull request by Type and Subtype.* See [code-smells.md](code-smells.md) for the full catalog and how to recognize each one.

#### 🧩 Detected Smells:
- [ ] **Bloaters:** (Long Method, Large Class, Primitive Obsession, Long Parameter List, Data Clumps)
- [ ] **Object-Orientation Abusers:** (Switch Statements, Temporary Field, Refused Bequest, Alternative Classes with Different Interfaces)
- [ ] **Change Preventers:** (Divergent Change, Shotgun Surgery, Parallel Inheritance Hierarchies)
- [ ] **Dispensables:** (Comments, Duplicate Code, Data Class, Dead Code, Lazy Class, Speculative Generality)
- [ ] **Couplers:** (Feature Envy, Inappropriate Intimacy, Message Chains, Middle Man, Incomplete Library Class)

**Location & Observations:**
> **Type:** [e.g., Dispensables]
> **Subtype:** [e.g., Comments]
> **Location:** the new-feature service module, in the field-calculation block
> **Context:** *The calculation logic uses inline comments to explain how fields are updated instead of pulling it into an explicitly named helper function.*
> **Severity:** [blocking | worthwhile | noted]

### Severity — what makes a smell worth acting on

A found smell is not automatically a smell to fix. Rate each one by **what it costs the next change**, not by how much it offends:

- **blocking** — the smell will make the next change to this code dangerous or wrong. Change Preventers live here almost by definition (Divergent Change, Shotgun Surgery), as does any smell that hides behavior: a Long Method with several exit paths, a Switch Statement that will need a new arm on every extension, duplication that will silently diverge. Fix before handing off.
- **worthwhile** — a clear, cheap, behavior-preserving improvement with an obvious treatment. Fix while it stays cheap.
- **noted** — real but low-value to act on now: a smell in code that is stable and unlikely to be touched, or one whose fix costs more than the smell does. **Record it and leave it** — with the condition that would change the answer (see below).

Order the findings blocking → worthwhile → noted. That is the order Step 2 works them in.

### Noted smells — record the promotion condition, then re-read it

A `noted` rating is a bet about the future: *this code won't be touched*, or *the fix costs more than the smell*. Bets come due. The remediation slices from [tyr-verdict](../tyr-verdict/SKILL.md) land in exactly the code the loop is having trouble with, which is disproportionately the code you rated stable — and a second instance of a duplication you tolerated once changes the arithmetic on the fix.

So a noted smell is not filed and forgotten. It is filed **with the condition that promotes it**:

```markdown
- **N1** Dispensables / Duplicate Code at the two constraint validators — noted iteration 1,
  left because the architect ruled the duplication accidental and the two will diverge
  - **Promote if:** a third instance appears, or a change has to be made in both at once
```

**Every pass after the first begins by re-reading `.workflow/ledger.md` → Noted smells**, and for each entry does exactly one of three things:

- [ ] **Promote** it — its condition has fired. The commonest trigger by far: *this iteration's changes touched that code*, which retires the "stable, won't be touched" justification outright. Re-rate it `blocking` or `worthwhile` and work it in Step 2 like any other finding.
- [ ] **Leave** it — the condition has not fired. One line, no re-derivation: `N1 — still noted, condition not met.` You are not re-litigating a judgment you already made.
- [ ] **Retire** it — the smell is gone, because a refactor or a remediation slice removed it. Strike it with the reason.

This is what stops the section becoming a graveyard. A noted smell that is never re-read is not a decision, it's a shrug with a timestamp — and the honest alternative would be to not write it down at all.

**The ledger.** `.workflow/ledger.md`, in the repo under review, is where the closing stages record findings, verdicts and carried smells across loop iterations. It is **append-only** — never rewrite a past iteration, because an erased decision gets re-argued from scratch — and its ids are stable (`N1` stays `N1`). Your section looks like this:

```markdown
## Noted smells (not acted on)
- **N<id>** <Type / Subtype> at <location> — noted iteration <n>, left because <reason>
  - **Promote if:** the condition that would make this worth fixing
```

Running standalone on a diff, the file won't exist — review what's in front of you and say the carried smells were unavailable.

---

## 🔧 Step 2: Refactoring Action Plan & Validation

*Prescribe the structural fixes while adhering to the Rules of Engagement.* See [refactoring-techniques.md](refactoring-techniques.md) for the mechanics of each technique and which smell it treats.

- [ ] **Extract Function / Method** (Breaks down Long Methods / removes explanatory Comments)
- [ ] **Extract Class / Module / Parameter Object** (Resolves Large Classes, Data Clumps, and Divergent Change)
- [ ] **Move Method / Field** (Corrects Feature Envy or Inappropriate Intimacy)
- [ ] **Introduce Guard Clauses / Polymorphism** (Flattens nesting and addresses Switch Statements)
- [ ] **Inline / Prune Code** (Cleans out Dead Code, Lazy Classes, and Speculative Generality)
- [ ] **Prune / Rewrite Comments** (Deletes restatement and commented-out code; keeps rationale — see [comments.md](comments.md))

**Execution Standards Check:**
- [ ] This change contains **zero** new behavior, features, or bug fixes (structural improvement only).
- [ ] The change results in a measurably cleaner, more maintainable code file.
- [ ] **Pre-Refactor Check:** Relevant tests were executed and passed successfully before modifying the issue.
- [ ] **Post-Refactor Check:** Relevant tests were executed and passed successfully after modifying the issue.
- [ ] *Note:* Any test failures that occurred in files/lines completely outside the scope of this review were safely ignored.

**Action Items** (in severity order — one technique per item, tests run between each):
1. `[blocking]` <smell at location> → <technique> — <what the structure looks like afterwards>
2. `[worthwhile]` <smell at location> → <technique> — <what the structure looks like afterwards>
3. `[noted]` <smell at location> → recorded, not acted on: <reason>

---

## 🛑 Stopping rule — when the structure is clean enough

There is no such thing as a diff with no smells left, so the pass needs an exit condition rather than an aesthetic one. Stop when all four hold:

- [ ] **No `blocking` smell remains** in the new code.
- [ ] **Every remaining smell is recorded** with a one-line reason for leaving it and its promotion condition — nothing is silently tolerated.
- [ ] **Every prior noted smell has been promoted, left, or retired** — the section carries no unexamined entry from an earlier iteration.
- [ ] **The last pass surfaced no new `blocking` finding.** If applying the treatments exposed one, work it and re-check; if a pass produces only `noted` findings, you are done.

Then stop, even if the code could still be prettier. **A refactor that doesn't reduce the cost of the next change is a diff for its own sake** — it costs review attention, it costs a re-run of the suite, and it puts behavior at risk for no return. Iterating for taste is how this stage turns into an infinite loop, and the pipeline already has one loop.

---

## Subagents — optional

Worth it on a **large diff**, unnecessary on a small one.

**Step 1 (Smell Identification) delegates.** It is a read-only pass over a bounded diff, and it splits cleanly along the five smell types — dispatch one subagent per type on a diff too large to hold in view at once, each told which type it owns and asked to return the same `Type / Subtype / Location / Context` block used above (including "none found", so a silent delegate is distinguishable from a clean category). Assemble and de-duplicate the findings here.

**Step 2 does not delegate.** Prescribing the treatment needs the whole smell list in view — several smells often share one root and one fix — and applying it is a write with a test run between every step (Rules of Engagement 3). Keep it single-threaded.

**Dispatch contract.** A subagent starts with no history. Give each one the **prior**, the **target** (which smell category it owns, and that the others are covered so it neither duplicates nor apologises for the gap), the **context it cannot infer** (the brief's scope boundaries), the **return shape** — the same `Type / Subtype / Location / Context / Severity` block used above, including "none found" so a silent delegate is distinguishable from a clean category — and an explicit *"report conclusions, not file excerpts."* Delegates stay **read-only**: two agents editing one tree clobber each other.

## Rules of Engagement

1. **Behavior is frozen.** A refactor that changes observable behavior is a bug, not a refactor.
2. **Tests are the safety net.** Green before, green after — see the Pre/Post checks above. Never refactor without coverage.
3. **Small steps.** Apply one technique, run tests, commit. Don't batch unrelated refactors.
4. **Name the smell first.** Don't refactor on vibes; map symptom → treatment via the two catalogs.
5. **New code only.** Pre-existing smells outside the diff are out of scope unless they **block** the change — and "blocks" has a test: *the new code cannot be made clean without touching it.* In practice that means one of two things — you would have to duplicate the old code to avoid it, or the new code has to work around it in a way that is itself a smell. Anything else is merely adjacent: name it, record it as `noted`, and leave it. Scope creep dressed as tidiness is the most common way a behavior-preserving refactor stops being behavior-preserving.

## Handoff

Clean structure on a GREEN suite is not the same as correct behavior. Once the diff is structurally clean, prompt the user:

> The structure is clean and the suite is GREEN — <n> smell(s) fixed, <m> noted and carried. Run **[devils-advocate](../devils-advocate/SKILL.md)** next — it assumes everything we built is wrong and hunts evidence for each defect before we call this done.

State the carried count out loud. Anything shipping un-refactored has to reach the verdict as a number the user can see, and [tyr-verdict](../tyr-verdict/SKILL.md) reads the same section when it makes the call.
