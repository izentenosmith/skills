## 🔎 Code Review Checklist (New Changes Only)

### 🛑 Step 1: Smell Identification
*Identify the code smells present in this pull request by Type and Subtype.*

#### 🧩 Detected Smells:
- [ ] **Bloaters:** (Subtypes: Long Method, Large Class, Primitive Obsession, Long Parameter List, Data Clumps)
- [ ] **Object-Orientation Abusers:** (Subtypes: Switch Statements, Refused Bequest, Alternative Classes, Temporary Field)
- [ ] **Change Preventers:** (Subtypes: Divergent Change, Shotgun Surgery, Parallel Inheritance)
- [ ] **Dispensables:** (Subtypes: Comments, Duplicate Code, Data Class, Dead Code, Lazy Class, Speculative Generality)
- [ ] **Couplers:** (Subtypes: Feature Envy, Inappropriate Intimacy, Message Chains, Incomplete Library Class)

**Location & Observations:**
> **Type:** [e.g., Dispensables]  
> **Subtype:** [e.g., Comments]  
> **Line / File:** `newFeatureService.ts` lines 12-25  
> **Context:** *The calculation logic uses inline comments to explain how fields are updated instead of pulling it into an explicitly named helper function.*

---

### 🔧 Step 2: Refactoring Action Plan & Validation
*Prescribe the structural fixes while adhering to the Rules of Engagement.*

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
