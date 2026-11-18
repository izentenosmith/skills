# Lenses — The Finder Angles

> Each lens is one reader with one question. Lenses A–E and O–P come from Claude Code's built-in
> `/code-review` recipe (CCR). F–N add what the review literature says that recipe leaves to
> chance. Each lens lists what to **look for**, what it **tends to miss** (the hand-off to another
> lens), and the principles it serves ([theory.md](theory.md)). Which lenses run at which tier is
> in the table in [SKILL.md](SKILL.md#phase-2-find-candidates-through-independent-lenses).
>
> Every candidate is `file:line · claim · lens · failure scenario or cost · evidence`. Pass on
> every candidate you can name a failure scenario for. The verifier cuts the false ones.

---

## Correctness

### A — Line by line
Read every hunk, then **the whole enclosing function**. A bug in an unchanged line of a touched
function is in scope, because the change re-exposes it or fails to fix it. For every line, ask what
input, state, timing or platform makes it wrong.
- **Look for:** inverted or wrong conditions; off-by-one at a boundary the code doesn't exclude;
  null, undefined or `None` dereferenced where adjacent lines show the value can be absent; a
  missing `await`; falsy-zero checks (`if (count)`); wrong-variable copy-paste; an error swallowed
  in a catch that should propagate; regex metacharacters left unescaped; loop conditions (they
  draw the most defects, BKS p.54).
- **Tends to miss:** anything that needs code outside the hunk. That's C's job.
- **Serves:** R6, R7.

### B — Removed behaviour
For every line the diff **deletes or replaces**, name the invariant or behaviour it enforced. Then
find where the new code re-establishes it.
- **Look for:** a removed guard, a dropped error path, narrowed validation, a deleted test that
  covered a real case, a removed `finally` or cleanup, a lost default, a removed log of a
  security-relevant event, moved or extracted code that dropped a check or an anchor.
- **Tends to miss:** behaviour that was never there. That's J's job.
- **Serves:** R11, R14.

### C — Cross-file tracer and change impact
For each function, type, endpoint, schema, configuration key or event the diff changes, find its
**callers and consumers** (grep the symbol, the route, the key). Check whether the change breaks
them: a new precondition, a changed return shape, a new exception or error code, a timing or
ordering dependency, a changed default. Check the callees too. Does a parallel change in the same
PR make a call unsafe?
- **Classify each impact** as behavioural, interface or operational, and its scope as local, module,
  cross-module or cross-service. A small diff that changes a default timeout, a serialisation format,
  an error contract or a feature-flag default is **high impact**, whatever its size (ACR p.17).
- **Tends to miss:** consumers outside the repo, such as other services, mobile clients and stored
  data. Name them as a question when you can't see them.
- **Serves:** R6, R19.

### D — Language and framework pitfalls
The classic traps of the diff's stack:
- **JavaScript/TypeScript:** falsy zero and empty string, `==` coercion, a closure capturing a loop
  variable, an unhandled promise, `forEach` with `async`, `Date` month off by one, mutation of a prop
  or state.
- **Python:** a mutable default argument, late-binding closures, `is` against literals, a bare
  `except`, iterator exhaustion, a naive or aware `datetime` mix-up.
- **Go:** writing to a nil map, capturing the range variable (before 1.22), shadowed `err`, a
  goroutine leak, a deferred call in a loop.
- **Java/C#:** `==` on strings or boxed values, `equals` without `hashCode`, disposal without
  `using`/try-with-resources, `async void`.
- **SQL:** NULL in `NOT IN`, implicit casts that defeat indexes, missing `ORDER BY` relied on for
  order.
- **Everywhere:** timezone and DST drift, float equality and floats for money, integer overflow,
  locale-sensitive case and number formatting.
- **Tends to miss:** project-specific traps. P and the project's own patterns cover those.
- **Serves:** R24.

### E — Wrappers and proxies
When the diff adds or changes a type that wraps another (cache, proxy, decorator, adapter,
retrying client), check that **every method routes to the wrapped instance**. It must not route
back through a registry, session or global, which would re-enter the wrapper or recurse. Check that
it forwards every method callers actually use, and preserves errors, cancellation and context.
- **Serves:** R19.

### F — Failure paths
Run the failure-path checklist in [heuristics.md](heuristics.md#4-failure-path-checklist-lens-f):
errors that vanish, the try as a transaction, context in errors, failure distinguishable from
success, early rejection of invalid input, checked return values, safe degraded modes, and bounded,
idempotent retries.
- **Tends to miss:** races between the failure and a concurrent success. That's G's job.
- **Serves:** R10, R11.

### G — Concurrency and state
Run the concurrency checklist in [heuristics.md](heuristics.md#3-concurrency-checklist-lens-g)
whenever state is reachable from more than one thread, task, request, worker or async continuation.
Also check idempotency under redelivery, ordering assumptions in consumers, and read-modify-write
in transactions.
- **Serves:** R22.

### H — Data and contracts
- **Migrations:** Are they reversible, or is the irreversibility stated? Are they safe to run
  against a live table (locks, rewrites, backfills in batches)? Do they deploy in the order the code
  needs (expand, then migrate, then contract)? Is a new non-null column given a default or a
  backfill?
- **Transactions:** Is every write that must be atomic in one transaction? Is there external I/O
  inside one?
- **Serialisation and wire formats:** Are renamed or removed fields still read by consumers or by
  stored data? Do enums gain values that old readers can't parse?
- **API compatibility:** Is a breaking change versioned, announced, or behind a flag?
- **Tends to miss:** the data already in production. Ask what existing rows look like.
- **Serves:** R19.

---

## Intent and omission

### I — Intent alignment
Restate the claim from Phase 0. Then walk it, criterion by criterion:
- For each thing the description or ticket says the change does: **where in the diff is it
  done?** A claim with no implementation is **Missing**.
- For each hunk: **which claim does it serve?** A hunk that serves none is **Tangling**: an
  unrelated refactor, a reformat, a drive-by fix, a debug leftover (ACR p.10, p.16–17).
- Classify the change: **Exact**, **Missing**, **Tangling**, or **Missing + Tangling**. That
  classification opens the report.
- **Contradictions are findings.** If the description says "no behaviour change" and a default
  flipped, say so. If the alignment is exact but the impact is cross-service, surface the tension;
  don't smooth it over (ACR p.19).
- **Misrouting.** If the change touches a domain the description doesn't mention, such as auth,
  money or a schema, flag it. A mis-described change gets the wrong reviewer (ACR p.25).
- **Serves:** R3, R4, R8, R18.

### J — Omissions
The checklist. Take one item at a time and sweep every review unit for it (BKS p.133). These are
the defects a reader of only what's present cannot see (BKS p.63, p.111):

- [ ] **Missing co-changes.** Files the history says usually change with a changed file, absent
  from this diff ([history-signals.md](history-signals.md#12-change-coupling-and-the-missing-co-change)).
  This includes the test that usually changes with its code.
- [ ] **Clone twins.** A near-duplicate of an edited function that didn't receive the same edit
  ([history-signals.md](history-signals.md#13-clone-twins-the-forgotten-update)).
- [ ] **Every caller updated.** A changed signature, contract or default has every call site
  updated, including those in other packages, scripts, jobs and tests.
- [ ] **Validation** of every new input, at the boundary.
- [ ] **Error paths** for every new call that can fail, and cleanup on each.
- [ ] **Tests** for new branches, boundaries and error cases. A regression test for a bug fix.
- [ ] **Migration, backfill or data fix** for a schema or semantics change, plus the rollback
  story.
- [ ] **Configuration** in every environment: new keys in the example env, the deployment manifests,
  the secrets store, and feature-flag defaults per environment.
- [ ] **Docs and user-facing text:** README, API docs, changelog, help, error messages, translations.
- [ ] **Observability:** logs, metrics or alerts for the new failure mode; the security events
  (authentication failures, denials, admin actions).
- [ ] **Permissions:** a new action added to the authorisation model, roles and policies; a new
  route added to the auth middleware.
- [ ] **Cleanup** of what the change made obsolete: flags, dead code, old config, old docs.
- [ ] **Version or build bumps** the project requires (BKS p.63).
- [ ] **The un-happy siblings.** A fix for one case of a pattern, and the other cases of the
  same pattern elsewhere in the diff.

When an omission can't be settled from the diff, such as a manifest in another repo or a consumer
you can't see, word it as a question with the evidence, not as a defect.
- **Serves:** R10, R11.

---

## Tests

### K — Tests
Run the test checklist in [heuristics.md](heuristics.md#5-test-checklist-lens-k). Start from the
question **"would this fail if the behaviour broke?"**, and mutate the code in your head to answer
it. Read the tests early, because long setup points at a design that's hard to use (XR p.43).
- **Tends to miss:** tests that aren't there. That's J's job.
- **Serves:** R20.

---

## Security

### L — Security
Run [security-lens.md](security-lens.md). Set the context (reachability, data class, boundary),
run the diff checklist, and use the grep table on added lines to find candidates, then trace each
one from source to sink. Escalate per section 4 of that file.
- **Serves:** R21.

---

## Evolvability

These findings are real and default to `minor`, raised to `major` in a hotspot or on a public
interface. They are always held apart from bugs (R2), and every one states its cost.

### M — Readability
- **The six-month test.** Will a reader understand this without the PR thread (ECR)? If you misread
  it, that's the finding (R12).
- **Names.** Do they say what the thing is and does, including side effects (N7)? Do they match the
  domain's language and the project's existing names (G11, N3)? Are they free of noise words and
  encodings (N1–N6)? Does the method name match its siblings, such as a `findBy*` among `search*`
  (ECR)? Check whether the better name changes what the code means. Renames have exposed real bugs
  (CC p.293).
- **Explicitness.** No magic values (G25; "what does `1` mean?", ECR). Types where a primitive
  carries a domain concept, such as `EmailAddress` instead of `string` (ECR; XR p.77). Explanatory
  variables for opaque expressions (G19).
- **Comments match the code** (C2), explain *why* rather than *what*, and say where a workaround
  came from (R31). Every new TODO names a ticket (ECR).
- **Defensive coding** at the boundaries: an enum-like string parameter (`setStatus('started')`)
  with no check that the value is valid (ECR).
- **Serves:** R12, R24, R31.

### N — Design and altitude
- **Altitude.** Is the fix at the right depth? A special case layered on shared infrastructure, or a
  new conditional patched into a general mechanism for one caller, usually means the fix isn't deep
  enough. Name the change to the underlying mechanism (CCR; R23).
- **Clean Code heuristics** in [heuristics.md](heuristics.md#2-the-evolvability-catalogue): flag and
  selector arguments, mixed abstraction levels, misplaced responsibility, hidden temporal coupling,
  repeated switches, boundary types leaking through public signatures.
- **History.** New complexity in a hotspot, complexity growth over 10% on the branch, surprising
  coupling ([history-signals.md](history-signals.md)).
- **Fowler smells** (Long Method, Shotgun Surgery, Feature Envy…). Name them and hand the structural
  fix to `refactor-review`.
- **Not here:** ugliness in cold code (R26), and redesigns the change didn't ask for. A real design
  question goes to the "Questions" section, not the findings.
- **Serves:** R23, R26.

### O — Reuse, simplicity, efficiency
- **Reuse.** New code that re-implements something the codebase already has. Grep shared and utility
  modules and the files next to the change, and name the existing helper to call instead.
- **Simplicity.** Redundant or derivable state, copy-paste with slight variation, deep nesting, dead
  code left behind. Name the simpler form that does the same job.
- **Efficiency.** Redundant computation or repeated I/O (including N+1 queries), independent
  operations run one after another, blocking work added to startup or a hot path, unbounded memory
  on large inputs (BKS p.113). Long-lived objects built from closures that capture a large scope,
  which leaks memory. Name the cheaper alternative. Never trade readability for speed without a
  measurement (BKS p.113).
- **Serves:** R2, R23.

### P — Conventions
- **Governing rules.** Find the CLAUDE.md, AGENTS.md and CONTRIBUTING files that govern each changed
  path. The user-level file applies everywhere; a directory's file applies at and below it. Flag a
  violation only when you can **quote the exact rule and the exact line** that breaks it. No "spirit
  of the doc" inferences. Name the file in the finding.
- **The project's own patterns.** When the change does something the codebase already does one way
  (error handling, logging, dependency injection, naming), and does it another way, that's a G11
  inconsistency. Cite the existing pattern by `file:line`. A local pattern that looks unusual to you
  may be legitimate here, so check before calling it an anti-pattern (ACR p.24–25).
- **Not here:** anything the linter or formatter enforces (R25). If no rules file applies and the
  change follows the local patterns, this lens returns nothing.
- **Serves:** R25.
