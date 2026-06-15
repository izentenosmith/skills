---
name: code-smells
description: Reference catalog of code smells (Refactoring Guru / Fowler) grouped into Bloaters, OO Abusers, Change Preventers, Dispensables, and Couplers. Use to name the symptom during a code review before choosing a refactoring.
---

# 🧩 Code Smells Catalog

A **code smell** is a surface symptom that usually points to a deeper problem. Smells aren't bugs — the code works — but they make it harder to change. This catalog follows the five families from Refactoring Guru (Martin Fowler's *Refactoring*, 2nd ed.). Each entry: **what it looks like → why it hurts → treatment** (techniques live in [refactoring-techniques.md](refactoring-techniques.md)).

> Use this to *name* the symptom in Step 1 of the [code review](code-review.md). Naming precisely is half the fix — it tells you which treatment to reach for.

---

## 1. Bloaters

Code, methods, and classes that have grown so large they're hard to work with. They accumulate gradually — no one writes them this way on purpose.

### Long Method
A method with too many lines (rule of thumb: if you feel the urge to comment a block, that block wants to be its own method).
- **Why it hurts:** Hard to understand, reuse, and test; hides several responsibilities.
- **Treatment:** Extract Method; Replace Temp with Query; Introduce Parameter Object / Preserve Whole Object; Replace Method with Method Object; Decompose Conditional.

### Large Class
A class trying to do too much, with too many fields/methods.
- **Why it hurts:** Low cohesion, duplication, hard to navigate.
- **Treatment:** Extract Class; Extract Subclass; Extract Interface; Replace Data Value with Object.

### Primitive Obsession
Using primitives (strings, ints, maps) instead of small objects for simple tasks — e.g. a string for a currency, a pair of ints for a coordinate, constants for type codes.
- **Why it hurts:** No validation, no behavior, meaning is implicit; the same primitive logic gets duplicated.
- **Treatment:** Replace Data Value with Object; Replace Type Code with Class / Subclasses / State·Strategy; Introduce Parameter Object; Replace Array with Object.

### Long Parameter List
More than ~3–4 parameters.
- **Why it hurts:** Hard to call correctly, hard to read, often signals a missing object.
- **Treatment:** Replace Parameter with Method Call; Preserve Whole Object; Introduce Parameter Object.

### Data Clumps
The same group of variables travels together (e.g. `startDate, endDate` everywhere, or `host, port, user, password`).
- **Why it hurts:** Duplication of the grouping; changes ripple across every call site.
- **Treatment:** Extract Class (for fields); Introduce Parameter Object / Preserve Whole Object (for parameters).

---

## 2. Object-Orientation Abusers

Incomplete or incorrect application of object-oriented principles.

### Switch Statements
A `switch` (or long `if/else` chain) on a type code, especially the same one duplicated in several places.
- **Why it hurts:** Adding a new case means editing every switch (Shotgun Surgery waiting to happen).
- **Treatment:** Replace Conditional with Polymorphism; Replace Type Code with Subclasses / State·Strategy; Replace Parameter with Explicit Methods; Introduce Null Object.

### Temporary Field
A field that only holds a value some of the time (set only during a complex algorithm, otherwise empty).
- **Why it hurts:** Confusing — readers expect fields to always be meaningful; invites null checks.
- **Treatment:** Extract Class; Introduce Null Object; Replace Method with Method Object.

### Refused Bequest
A subclass uses only some of what it inherits; the rest is irrelevant or actively wrong.
- **Why it hurts:** Inheritance implies an "is-a" that doesn't hold; fragile hierarchy.
- **Treatment:** Replace Inheritance with Delegation; Extract Superclass (push shared bits up, stop inheriting the rest).

### Alternative Classes with Different Interfaces
Two classes do the same thing but have different method names/signatures.
- **Why it hurts:** Can't substitute one for the other; duplication hides behind different vocabulary.
- **Treatment:** Rename Method; Move Method / Add or Remove Parameter to unify; Extract Superclass.

---

## 3. Change Preventers

One change forces many other changes. Violates "a change should be local."

### Divergent Change
One class is changed for many different reasons (e.g. edited for new payment types *and* new report formats).
- **Why it hurts:** Low cohesion; every unrelated requirement touches the same file.
- **Treatment:** Extract Class (split the class along its axes of change); Move Method / Move Field.

### Shotgun Surgery
The opposite: one conceptual change forces tiny edits across many classes.
- **Why it hurts:** Easy to miss an edit; behavior is smeared across the codebase.
- **Treatment:** Move Method / Move Field to gather the scattered behavior; Inline Class.

### Parallel Inheritance Hierarchies
Every time you add a subclass to one hierarchy, you must add one to another.
- **Why it hurts:** Duplicated structure; the two hierarchies drift.
- **Treatment:** Move Method / Move Field to fold one hierarchy into the other.

---

## 4. Dispensables

Something whose absence would make the code cleaner. Pointless and removable.

### Comments
Comments that explain *what* convoluted code does (as opposed to *why* a non-obvious decision was made).
- **Why it hurts:** A comment is often deodorant for bad code; it rots out of sync with the code.
- **Treatment:** Extract Method (and name it well); Rename Method; Introduce Assertion. Keep comments that capture intent/rationale, not narration.

### Duplicate Code
The same (or nearly the same) code in more than one place.
- **Why it hurts:** Fixes and changes must be repeated; they get missed.
- **Treatment:** Extract Method; Pull Up Method (for sibling classes); Form Template Method; Substitute Algorithm; Extract Superclass.

### Lazy Class
A class that no longer does enough to justify its existence.
- **Why it hurts:** Maintenance and cognitive overhead for no payoff.
- **Treatment:** Inline Class; Collapse Hierarchy.

### Data Class
A class with only fields and getters/setters — no behavior.
- **Why it hurts:** Behavior that *should* live with the data lives elsewhere (often Feature Envy in the callers).
- **Treatment:** Move Method (pull behavior in); Encapsulate Field / Encapsulate Collection; Remove Setting Method where fields shouldn't change.

### Dead Code
Variables, parameters, methods, or branches that are never used.
- **Why it hurts:** Noise; readers waste time reasoning about it.
- **Treatment:** Delete it (Inline Method/Class first if partly used; Remove Parameter for unused params). Version control is your archive.

### Speculative Generality
Machinery added "in case we need it" — unused abstract classes, hooks, parameters.
- **Why it hurts:** Complexity with no current user; YAGNI violation.
- **Treatment:** Collapse Hierarchy; Inline Class; Remove Parameter; Rename to something concrete.

---

## 5. Couplers

Excessive coupling between classes (or, in Middle Man, too much delegation in place of real work).

### Feature Envy
A method is more interested in another class's data than its own.
- **Why it hurts:** Logic lives away from the data it operates on; signals misplaced responsibility.
- **Treatment:** Move Method; Extract Method then Move Method for the envious part.

### Inappropriate Intimacy
Two classes reach into each other's private parts.
- **Why it hurts:** Tight coupling; can't change one without the other.
- **Treatment:** Move Method / Move Field; Extract Class; Hide Delegate; Change Bidirectional Association to Unidirectional; Replace Inheritance with Delegation.

### Message Chains
`a.getB().getC().getD().doThing()` — a client navigates a chain of objects.
- **Why it hurts:** Client is coupled to the structure of the whole chain; any link change breaks it.
- **Treatment:** Hide Delegate; Extract Method + Move Method.

### Middle Man
A class that delegates almost everything to another class.
- **Why it hurts:** Pointless indirection.
- **Treatment:** Remove Middle Man; Inline Method; (if it adds a little, consider Replace Delegation with Inheritance).

### Incomplete Library Class
A library class lacks a method you need, but you can't (or shouldn't) modify it.
- **Why it hurts:** You end up with awkward workarounds scattered around.
- **Treatment:** Introduce Foreign Method (small additions); Introduce Local Extension (subclass/wrapper for several additions).

---

## Quick Reference: Smell → Primary Treatment

| Smell | Reach first for |
|-------|-----------------|
| Long Method | Extract Method |
| Large Class | Extract Class |
| Primitive Obsession | Replace Data Value with Object / Replace Type Code |
| Long Parameter List | Introduce Parameter Object |
| Data Clumps | Extract Class / Introduce Parameter Object |
| Switch Statements | Replace Conditional with Polymorphism |
| Temporary Field | Extract Class / Introduce Null Object |
| Refused Bequest | Replace Inheritance with Delegation |
| Divergent Change | Extract Class |
| Shotgun Surgery | Move Method / Move Field |
| Comments | Extract Method + Rename |
| Duplicate Code | Extract Method / Pull Up Method |
| Data Class | Move Method (pull behavior in) |
| Dead Code | Delete |
| Speculative Generality | Collapse Hierarchy / Inline Class |
| Feature Envy | Move Method |
| Inappropriate Intimacy | Move Method / Hide Delegate |
| Message Chains | Hide Delegate |
| Middle Man | Remove Middle Man |
