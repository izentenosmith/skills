# Heuristics — Evolvability, Concurrency, Errors, Tests, Names

> The catalogue lenses **G** (concurrency), **F** (failure paths), **K** (tests), **M**
> (readability) and **N** (design) read against. The IDs are Clean Code's chapter-17 IDs, so a
> finding can cite `CC G31` and anyone can look it up. Page numbers are PDF pages of *Clean Code*
> (Martin, 2009). The printed page is the PDF page − 31. See [theory.md](theory.md).
>
> **These are heuristics with a cost model, not laws.** The book calls itself one school of thought
> and says readers will disagree with some of it (CC p.44). A finding names the heuristic **and
> the cost in this diff**: what the next reader misreads, or what the next change has to touch. A
> heuristic match with no cost is taste, and taste is dropped in Phase 3.
>
> Fowler's smell catalogue (Long Method, Feature Envy, Shotgun Surgery…) belongs to
> `refactor-review`. Name a Fowler smell when it fits,
> but hand the structural fix to that skill. This file holds what Clean Code adds beyond Fowler.

---

## 1. Correctness hiding in "style"

Several of Clean Code's heuristics look like style and are correctness checks. Raise these as `bug`
findings whenever the failure is real, not as evolvability:

| ID | Heuristic | What it looks like in a diff | Why it's a bug risk |
|---|---|---|---|
| G2 | Obvious behaviour is unimplemented | A function fails a case its name promises (`parseDay("MONDAY")` rejects lower case) | Callers trust the name and don't read the body (CC p.320) |
| G3 | Incorrect behaviour at the boundaries | Off-by-one, empty, single, maximum, end-of-iteration, untested | Intuition fails at the corners (CC p.320) |
| G4 | Overridden safeties | A suppressed warning, a disabled or skipped test, a bypassed check, with no reason given | A green build bought with future debugging (CC p.320) |
| G21 | Understand the algorithm | Extra `if`s and flags added until the tests passed | "Works" isn't "known to be correct" (CC p.328) |
| G22 | Make logical dependencies physical | A module hard-codes a size, format or default that another module owns | It breaks silently when the owner changes (CC p.329–330) |
| G26 | Be precise | Assumes the first match is the only one, floats for money, no lock "because a race is unlikely", an unchecked nullable return | Each imprecision is an undecided case (CC p.332) |
| G31 | Hidden temporal coupling | Methods that must be called in order, but nothing in their signatures enforces it | Out-of-order calls fail at runtime (CC p.333–334) |
| G33 | Encapsulate boundary conditions | `+1`/`-1` scattered across the code | One of the copies will be wrong (CC p.335) |
| N7 | Names should describe side effects | `getX()` that creates, `checkPassword()` that starts a session | Hidden effects mislead every caller (CC p.75, p.344) |
| G20 | Function names say what they do | `date.add(5)`: days? Does it mutate? | The fix (`plusDays`) often settles a real question (CC p.311, p.328) |
| C2 | Obsolete comment | A comment this diff made false, or one promising behaviour the code doesn't have | A misleading comment is worse than none (CC p.94, p.317) |

Renames in the book's case studies **found real bugs**. Renaming `suffixIndex` to `suffixLength`
exposed a branch that could never run (CC p.293). Don't dismiss a naming finding as cosmetic until
you've checked whether the better name changes what the code means.

---

## 2. The evolvability catalogue

Evolvability findings default to `minor`, or `major` in a hotspot or a public interface. Beck's
ordering sets their relative weight: tests > no duplication > expresses intent > fewest elements
(CC p.203, p.207). Rank "too many classes" findings lowest.

### Functions
| ID | Signal in the diff | Cost |
|---|---|---|
| F1 | Three or more parameters, and growing | Combinations multiply. Prefer a parameter object, not hidden fields (see §6) |
| F2 | An argument mutated as output (`appendFooter(report)`) | Readers assume arguments are inputs |
| F3 / G15 | A boolean, enum or int that selects behaviour (`render(true)`) | One function doing two things. Split it |
| G30 / G34 | Visible sections in one function (declare, loop, filter, act), or high-level intent mixed with low-level detail | Separating the levels often reveals bugs (CC p.335–336) |
| G28 / G29 | Compound or negated conditions inline (`!x.shouldNotCompact()`) | Extract an intention-revealing predicate |
| G19 | An opaque calculation with no named intermediate values | Name the steps |
| G25 | Magic numbers and strings, in tests too | Unsearchable and unexplained |

### Placement and abstraction
| ID | Signal in the diff | Cost |
|---|---|---|
| G6 / G7 | Implementation detail in a base class or interface, or a base class naming its subclasses | A misplaced abstraction can't be faked away |
| G8 | A wider public surface than callers need | Coupling. Every public member is a promise |
| G13 | A general enum or helper declared inside a specific class | Unrelated modules end up depending on it |
| G17 | Code placed where it was convenient, not where a reader would look | Least surprise |
| G18 | A static that works on one object's data or may need polymorphism | Blocks substitution and testing |
| G35 | Defaults or configuration buried in low-level functions | Config belongs at the top, passed down |
| G23 | A second switch on the same type code | One switch per type, in a factory (CC p.330) |
| G36 | Navigation through objects (`a.getB().getC().do()`) | Callers learn the object graph. A Law of Demeter issue only for objects, not plain data (CC p.129) |
| G1 | SQL, HTML or shell in host-language strings | Also a security-lens signal (injection) |
| G11 | The same concept done or named differently from its siblings | Predictability. Checked against the project, not taste |
| G5 | Duplication, including duplicated *implementation* of a derivable fact | Each copy is a future omission (also see [history-signals.md](history-signals.md#13-clone-twins-the-forgotten-update)) |

### Dispensables (when the diff adds or orphans them)
C1 change-log or author comments · C3 redundant comments · C5 commented-out code · F4 / G9 dead
functions and branches · G12 clutter. One grouped `nit` unless dead code hides a removed behaviour
(lens B).

### Boundaries (CC ch.8)
- Third-party or framework types (`Map`, SDK models, ORM entities) leaking through **public**
  signatures across many modules. Prefer a narrow wrapper that speaks the app's language (CC
  p.145–146). Don't demand wrapping every use (CC p.146).
- A new third-party dependency with no boundary test that pins the behaviour relied on. Upgrades
  then become guesswork (CC p.147–149).

### Environment
E1 the build needs more than one step · E2 the tests need more than one step. A diff that adds a
manual step to either gets a `process` finding (CC p.318).

---

## 3. Concurrency checklist (lens G)

Run it whenever the diff touches state that can be reached from more than one thread, task,
request, worker or async continuation. A concurrency bug doesn't repeat on demand, so it gets
dismissed as a one-off (CC p.211). Treat every item as a question you answer from the code:

- [ ] **Shared mutable state.** Is any new or changed field, static, singleton, cache, handler
  instance field or captured variable reachable from two threads? What guards it, or confines it?
  Count the places that mutate it (CC p.212–213).
- [ ] **Non-atomic operations.** `++`/`--` on shared fields, read-modify-write, check-then-act.
  None of these is atomic (CC p.357).
- [ ] **Compound actions on a shared object.** `containsKey` then `put`, `hasNext` then `next`,
  `exists` then `create`. Each call being synchronized does not make the pair safe. Prefer one
  atomic server-side operation (`putIfAbsent`, `getNextOrNull`, an upsert, a conditional update)
  over the client holding a lock (CC p.216, p.359–364).
- [ ] **Lock scope.** Is every critical section guarded, and no more than that? Calling one locked
  section from inside another is a red flag (CC p.216, p.222).
- [ ] **Lock order.** Two paths that take the same two locks or pooled resources in opposite orders
  can deadlock. The book's example is create taking MQ then DB, and update taking DB then MQ.
  Require one global order (CC p.366–370).
- [ ] **Non-thread-safe types shared.** Date formatters, connections, plain collections, any type
  whose docs don't promise thread safety (CC p.359).
- [ ] **Unbounded concurrency.** A new thread or task per request with no limit. Prefer a pool or
  executor with a bound (CC p.350, p.357).
- [ ] **Shutdown.** Does every worker, consumer and scheduler stop cleanly? What happens to work in
  flight (CC p.217)?
- [ ] **The claim.** "Faster with threads" only holds for work that waits on I/O. Check what the
  work actually is (CC p.349).
- [ ] **Tests.** A flaky test near concurrent code is a probable race, not noise, and a "retry" is
  not a fix. A passing concurrency test is weak evidence (CC p.217–218, p.370–372).

The same checks apply beyond threads: shared state across an `await`, check-then-act across a
suspension point, read-modify-write in a database transaction without the right isolation or a
conditional write, message consumers that assume ordering, and handlers that aren't idempotent
under retry.

---

## 4. Failure-path checklist (lens F)

- [ ] **Errors don't vanish.** No empty catch, no catch that only logs and carries on as if the call
  succeeded, no broad catch that swallows programming errors. If an error is ignored on purpose,
  there's a comment saying why (CC p.91; BKS p.112).
- [ ] **The try is a transaction.** After the catch, is state consistent? Partial writes rolled back
  or compensated, resources released on every path, locks released in error paths (CC p.136; BKS
  p.112–113).
- [ ] **Errors carry context.** The operation that failed and how, without leaking secrets or
  personal data (CC p.138; [security-lens.md](security-lens.md)).
- [ ] **Callers can tell failure from success.** No error code or `null` a caller can silently
  ignore. Absence is explicit in the type, or a special-case object, or an empty collection (CC
  p.141–143). Follow the codebase's own error model: `Result` types and Go-style returns are
  idiomatic. Don't demand exceptions.
- [ ] **Invalid input is rejected early**, at the top of the function or the boundary, not
  half-way through a write (BKS p.112).
- [ ] **Return values of calls are checked**, especially I/O, parsing and anything that can return
  `null` or an error (BKS p.112).
- [ ] **Degraded modes are safe.** On a timeout or a dependency failure, does the code fall back to
  something weaker, such as a default role, "allow", or stale data presented as fresh?
- [ ] **Retries are bounded and idempotent**: backoff, a cap, and no duplicate side effects.

---

## 5. Test checklist (lens K)

The first question is always: **would this test fail if the behaviour it names broke?** Mentally
mutate the code: invert the condition, drop the branch, return a constant. If no test goes red, the
test tests nothing.

- [ ] **The requirement is tested**, not just the code path. Tests check the behaviour the
  description claims, at the boundary named in the ticket. "Drop a cookie" passes a test that never
  checks which side of the junction it's on (ECR; BKS p.112).
- [ ] **New branches and calculations have tests** (T1). Boundaries are tested (T5). Error paths and
  invalid input are tested (BKS p.112).
- [ ] **A bug fix comes with a test that fails without the fix**, and with tests for the bug's
  neighbours, because bugs congregate (T6).
- [ ] **Skipped or ignored tests carry a reason**, and an ignored test is a question about an
  ambiguity (T4, G4).
- [ ] **F.I.R.S.T.** Tests are fast (no sleeps, no network in unit tests), independent (no order
  dependence), repeatable (offline, any machine), self-validating (no log reading) and timely
  (CC p.163–164).
- [ ] **One concept per test**, readable as build-operate-check. Assert counts don't matter (CC
  p.161–163).
- [ ] **The test co-change.** Production code changed and its usual test didn't. Ask whether the
  tests went stale ([history-signals.md](history-signals.md#12-change-coupling-and-the-missing-co-change)).
- [ ] **Test smells.** Long setup means the code under test is hard to use. Heavy mocking tests
  mechanism, not behaviour. Duplicated assertion blocks are missing a test-data abstraction.
  Test code gets the same bar as production code (XR p.43, p.45, p.54).
- [ ] **Tests for generated UI layout** are QA's job, not review's. Don't spend review effort on
  pixel coordinates (BKS p.122).

---

## 6. Where the advice is contested: apply as a heuristic

| Advice | Reviewer stance |
|---|---|
| Functions "hardly ever 20 lines" (CC p.65) | Flag mixed abstraction levels and visible sections (G30, G34), never a raw line count. The author admits no research backs it |
| Minimise arguments, even by moving them into fields (CC p.71, p.81) | The book's own example creates hidden state and temporal coupling (G31). Prefer a parameter object. A pure function with three parameters is not a defect by itself |
| "Comments are always failures" (CC p.85) | Rationale, invariants, warnings and references to non-obvious library behaviour earn their place. A workaround the reviewer needed explained belongs in a comment (BKS p.29) |
| One assert per test | One *concept* per test |
| Polymorphism over switch | Flag the *repeated* switch. One in a factory or at a boundary is fine |
| Exceptions over error codes, unchecked over checked, never return null | Follow the language and the codebase's error model. Require that absence and failure are handled, not a particular mechanism |
| Wildcard imports (J1), `I`-prefixes, file length, line length | Defer to the linter and ecosystem convention (G24). Not findings |
| Many small classes | Rule 4 of simple design warns against too many. Flag god classes *and* one-method interfaces that exist for no caller |
