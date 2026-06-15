---
name: code-review
description: Review the current diff for code smells and prescribe structural refactorings. Use after a TDD cycle or before merging to catch smells the green-bar didn't. Reviews new changes only; structural fixes are behavior-preserving.
---

# 🔎 Code Review Checklist (New Changes Only)

This is the **guideline** that drives a review. It leans on two reference catalogs:

- [code-smells.md](code-smells.md) — how to *name* what's wrong (the symptom)
- [refactoring-techniques.md](refactoring-techniques.md) — how to *fix* it (the treatment)

Reviews target **new changes only**. Refactorings are **behavior-preserving** — no new features, no bug fixes mixed in.

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
> **Line / File:** `newFeatureService.ts` lines 12-25
> **Context:** *The calculation logic uses inline comments to explain how fields are updated instead of pulling it into an explicitly named helper function.*

---

## 🔧 Step 2: Refactoring Action Plan & Validation

*Prescribe the structural fixes while adhering to the Rules of Engagement.* See [refactoring-techniques.md](refactoring-techniques.md) for the mechanics of each technique and which smell it treats.

- [ ] **Extract Function / Method** (Breaks down Long Methods / removes explanatory Comments)
- [ ] **Extract Class / Module / Parameter Object** (Resolves Large Classes, Data Clumps, and Divergent Change)
- [ ] **Move Method / Field** (Corrects Feature Envy or Inappropriate Intimacy)
- [ ] **Introduce Guard Clauses / Polymorphism** (Flattens nesting and addresses Switch Statements)
- [ ] **Inline / Prune Code** (Cleans out Dead Code, Lazy Classes, and Speculative Generality)

**Execution Standards Check:**
- [ ] This change contains **zero** new behavior, features, or bug fixes (structural improvement only).
- [ ] The change results in a measurably cleaner, more maintainable code file.
- [ ] **Pre-Refactor Check:** Relevant tests were executed and passed successfully before modifying the issue.
- [ ] **Post-Refactor Check:** Relevant tests were executed and passed successfully after modifying the issue.
- [ ] *Note:* Any test failures that occurred in files/lines completely outside the scope of this review were safely ignored.

**Action Items:**
1. Fix...
2. Clean up...

---

## Rules of Engagement

1. **Behavior is frozen.** A refactor that changes observable behavior is a bug, not a refactor.
2. **Tests are the safety net.** Green before, green after — see the Pre/Post checks above. Never refactor without coverage.
3. **Small steps.** Apply one technique, run tests, commit. Don't batch unrelated refactors.
4. **Name the smell first.** Don't refactor on vibes; map symptom → treatment via the two catalogs.
5. **New code only.** Pre-existing smells outside the diff are out of scope unless they block the change.
