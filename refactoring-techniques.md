---
name: refactoring-techniques
description: Reference catalog of behavior-preserving refactorings (Refactoring Guru / Fowler) across Composing Methods, Moving Features, Organizing Data, Simplifying Conditionals, Simplifying Method Calls, and Generalization. Use to pick a treatment once a smell is named.
---

# 🔧 Refactoring Techniques Catalog

**Refactoring** = changing the internal structure of code without changing its observable behavior. Each technique below is a *named, mechanical* transformation: a recipe with a known before/after. This catalog follows the six groups from Refactoring Guru (Martin Fowler's *Refactoring*, 2nd ed.). Use it to pick a *treatment* once [code-smells.md](code-smells.md) has named the symptom, then drive it through the [code review](code-review.md) checklist.

> **The one rule:** behavior is frozen. Have tests green before you start, take small steps, and re-run tests after each step. If behavior changed, it wasn't a refactor.

---

## 1. Composing Methods

Streamline methods, remove duplication, make code self-explanatory. The backbone of most refactoring.

- **Extract Method** — Move a code fragment into its own well-named method; replace the fragment with a call. The single most-used refactoring. Treats Long Method, Duplicate Code, Comments.
- **Inline Method** — When a method body is as clear as its name, put the body inline and delete the method. Treats Middle Man / needless indirection.
- **Extract Variable** — Put a complex expression (or part of it) into a named local. Makes conditionals readable.
- **Inline Temp** — Replace a temp that's just assigned a simple expression with the expression itself. Often a prelude to Replace Temp with Query.
- **Replace Temp with Query** — Extract the expression behind a temp into a method; call it where the temp was used. Lets the value be reused and enables Extract Method.
- **Split Temporary Variable** — A temp assigned more than once for different purposes → one variable per responsibility.
- **Remove Assignments to Parameters** — Use a local instead of reassigning a parameter. Avoids confusion about what the parameter means.
- **Replace Method with Method Object** — Turn a long method full of tangled locals into its own class, with locals as fields. Lets you then Extract Method freely. Treats Long Method.
- **Substitute Algorithm** — Replace a convoluted algorithm with a clearer one. Treats Duplicate Code / complexity.

---

## 2. Moving Features Between Objects

Distribute responsibilities so behavior lives with the data it uses.

- **Move Method** — Move a method to the class it uses most. Treats Feature Envy, Shotgun Surgery, Inappropriate Intimacy.
- **Move Field** — Move a field to the class that uses it most.
- **Extract Class** — Split one class doing two jobs into two classes. Treats Large Class, Divergent Change, Data Clumps, Temporary Field.
- **Inline Class** — Fold a class that does too little into another. Treats Lazy Class, Speculative Generality.
- **Hide Delegate** — Add a method on the server so clients don't navigate a chain (`a.getB().doX()` → `a.doX()`). Treats Message Chains.
- **Remove Middle Man** — When a class just forwards calls, let clients call the delegate directly. Treats Middle Man (the inverse of Hide Delegate).
- **Introduce Foreign Method** — Add a needed method to a client class when you can't edit the library class. Treats Incomplete Library Class.
- **Introduce Local Extension** — Subclass or wrap a library class to add several missing methods. Treats Incomplete Library Class.

---

## 3. Organizing Data

Make data structures cleaner and decouple classes from their representations.

- **Self Encapsulate Field** — Access fields through getters/setters even inside the class.
- **Replace Data Value with Object** — Turn a primitive that has behavior/validation into its own class. Treats Primitive Obsession.
- **Change Value to Reference** / **Change Reference to Value** — Switch between many identical instances vs. a single shared one (and back, for immutable value objects).
- **Replace Array with Object** — When array elements mean different things, use an object with named fields. Treats Primitive Obsession.
- **Change Unidirectional Association to Bidirectional** / **...to Unidirectional** — Add or drop a back-pointer between classes as access needs change. Dropping treats Inappropriate Intimacy.
- **Encapsulate Field** — Make a public field private and expose accessors. Treats Data Class.
- **Encapsulate Collection** — Return a read-only view of a collection; add/remove via methods. Treats Data Class.
- **Replace Magic Number with Symbolic Constant** — Name a literal with semantic meaning.
- **Replace Type Code with Class** — Replace a numeric/string type code with a class (when the code has no behavioral variation).
- **Replace Type Code with Subclasses** — When behavior varies by type code and the code is immutable, use subclasses. Treats Switch Statements, Primitive Obsession.
- **Replace Type Code with State/Strategy** — When the type code can change at runtime, delegate to a State/Strategy object. Treats Switch Statements.

---

## 4. Simplifying Conditional Expressions

Conditionals get complicated over time; these untangle them.

- **Decompose Conditional** — Extract the condition, the then-branch, and the else-branch into named methods. Treats Long Method.
- **Consolidate Conditional Expression** — Combine several conditionals that yield the same result into one, then extract it.
- **Consolidate Duplicate Conditional Fragments** — Move code that's identical in every branch out of the conditional.
- **Remove Control Flag** — Replace a `done`/`found` boolean flag with `break`, `continue`, or `return`.
- **Replace Nested Conditional with Guard Clauses** — Flatten nesting by returning early on special cases. The standard fix for arrow-shaped code.
- **Replace Conditional with Polymorphism** — Move each branch of a type-based conditional into an overriding method on a subclass. The premier treatment for Switch Statements.
- **Introduce Null Object** — Replace repeated `if (x == null)` checks with a null object that has do-nothing/default behavior. Treats Temporary Field, Switch Statements.
- **Introduce Assertion** — Make an implicit assumption explicit with an assertion. Can replace a comment.

---

## 5. Simplifying Method Calls

Make interfaces easier to understand and use.

- **Rename Method** — Give a method a name that reveals its purpose. Treats Comments, Alternative Classes with Different Interfaces.
- **Add Parameter** / **Remove Parameter** — Add data a method needs; remove what it no longer uses. Remove treats Dead Code / Speculative Generality.
- **Separate Query from Modifier** — Split a method that both returns a value *and* changes state into two methods. (Command–query separation.)
- **Parameterize Method** — Merge several near-identical methods into one that takes a parameter for the varying part.
- **Replace Parameter with Explicit Methods** — The inverse: when a parameter just selects between distinct behaviors, make separate methods. Treats Switch Statements.
- **Preserve Whole Object** — Pass the whole object instead of pulling several values out of it first. Treats Long Parameter List, Data Clumps.
- **Replace Parameter with Method Call** — Let the callee fetch a value itself instead of receiving it. Treats Long Parameter List.
- **Introduce Parameter Object** — Replace a recurring group of parameters with a single object. Treats Long Parameter List, Data Clumps.
- **Remove Setting Method** — Drop setters for fields that must not change after construction. Treats Data Class.
- **Hide Method** — Make a method private/protected when no other class uses it.
- **Replace Constructor with Factory Method** — Use a factory when construction needs logic or should return subtypes.
- **Replace Error Code with Exception** / **Replace Exception with Test** — Swap numeric error returns for exceptions; or, where a simple precondition check suffices, swap an exception for a test.

---

## 6. Dealing with Generalization

Reorganize inheritance hierarchies — moving behavior up, down, in, and out.

- **Pull Up Field** / **Pull Up Method** — Move a field/method shared by subclasses into the superclass. Treats Duplicate Code.
- **Pull Up Constructor Body** — Move common constructor code into the superclass constructor.
- **Push Down Field** / **Push Down Method** — Move a member used by only one subclass down into it.
- **Extract Subclass** — Create a subclass for features used only in some instances. Treats Large Class, Temporary Field.
- **Extract Superclass** — Create a superclass for two classes with common features. Treats Duplicate Code, Alternative Classes.
- **Extract Interface** — Pull a common interface out of classes that share part of their API. Treats Large Class, Duplicate Code.
- **Collapse Hierarchy** — Merge a subclass and superclass that are barely distinct. Treats Lazy Class, Speculative Generality.
- **Form Template Method** — When subclasses have similar methods with the same steps in the same order, pull the skeleton up and let subclasses override the varying steps. Treats Duplicate Code.
- **Replace Inheritance with Delegation** — When a subclass uses only part of its superclass, hold an instance instead of inheriting. Treats Refused Bequest, Inappropriate Intimacy.
- **Replace Delegation with Inheritance** — The inverse: when a class delegates *everything* to another, inherit instead. Treats Middle Man.

---

## How to Apply a Refactoring Safely

1. **Green first.** Confirm tests pass before touching anything.
2. **One technique at a time.** Don't interleave two transformations.
3. **Smallest viable step.** Extract, then move; don't extract-and-move in one leap.
4. **Re-run tests after each step.** A red bar means *undo*, not *push on*.
5. **Commit per refactor.** Each commit is one behavior-preserving transformation, reviewable on its own.
6. **No behavior changes.** New features and bug fixes belong in separate commits — never smuggled inside a refactor.
