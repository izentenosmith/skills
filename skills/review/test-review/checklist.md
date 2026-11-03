# Checklist: The Test Checks (TQ-1–TQ-45)

> Apply this one item at a time. Take an item, sweep every changed test and every changed production
> unit for it, then move to the next. When a new class of defect turns up, re-check what you have
> already swept for that class (TR22, BKS p.133–134). Each item is a true/false question. Each item
> names the principle a finding cites. **Tier** says where the item first runs: **Q** Quick,
> **S** Standard, **D** Deep. Higher tiers run everything below them.
>
> The list is long because it is eight short lists. Within one family, keep to the items that apply
> to the change in front of you. A family that doesn't apply is recorded as swept with "n/a" and the
> reason, never silently skipped.
>
> **Evidence for each verdict** is set out in [mutation.md](mutation.md#5-what-a-probe-result-means).
> Smell names used below are defined in [smells.md](smells.md).

---

## 1. Traceability: is every claim backed by a test?

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-1** | Every claimed behaviour and acceptance criterion (AC-n) maps to at least one test that exercises it at the boundary the claim names. Record each as **covered**, **weak** or **missing** in the traceability table | S | TR2 |
| **TQ-2** | Where `.workflow/brief.md` has an **Acceptance tests** mapping, it holds: each mapped test exists under that name, its name leads back to its criterion, it asserts the criterion's specific outcome, and it wasn't edited in this diff without a logged brief revision | S | TR2 |
| **TQ-3** | Each new branch, calculation, public entry point, config option and feature flag state has a test that reaches it (CC T1) | S | TR1 |
| **TQ-4** | A bug fix carries a regression test that reproduces the reported trigger and fails on the pre-fix code, plus tests near the fix (CC T6) | Q | TR4 |
| **TQ-5** | A criterion that says what stays allowed is tested with its contrast: the refusal and the permitted case in one test. Authorisation is tested as actor × operation, the refusal included | S | TR2 |
| **TQ-6** | Changed or removed behaviour: the old tests were updated to the new rule, not deleted or loosened until green. A deleted assertion is a removed guarantee, so find where it is re-established | Q | TR3 |

**Status rules for the traceability table.**

- **covered**: a test reaches the behaviour through the claimed boundary, and a named, plausible
  mutation of the implementing line would turn one of its assertions red.
- **weak**: a test exists, but a named mutation survives it; or it asserts success without the
  specific outcome; or it tests at the wrong level (TQ-38); or it tests only one side of a boundary
  or contrast.
- **missing**: no test reaches the behaviour. Say what you searched: the symbol, the route, the
  message, the test directories.

A criterion that can only be checked from inside is not a defect when the brief marks it "not
acceptance-testable" and names the tdd seam that covers it. Check that the named seam's test
exists.

---

## 2. Would it fail? Mutation thinking

Run TQ-7 on every changed production branch at Standard and Deep. Run TQ-8 to TQ-14 on every
changed test body at every tier. The mutation operators are in
[mutation.md](mutation.md#1-mutation-thinking-name-the-mutation).

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-7** | For each changed production branch, a named, plausible mutation (flip the condition, drop the call, shift the boundary, return early, swallow the error) would turn some assertion red. Name the mutation and the assertion, or record the survivor | S | TR3 |
| **TQ-8** | The test asserts something about the outcome. No assertion, or only "no exception was raised", is a smoke test, and it has to be named as one | Q | TR1 |
| **TQ-9** | The assertion isn't on the double's own canned value: a stub returns X and the test asserts X came back, through code that only forwards it | Q | TR3 |
| **TQ-10** | Every assertion is reachable: not inside a loop over a collection that is empty in this test, not in a callback that never fires, not after an early `return`, not in an async block the test doesn't await or return | Q | TR3 |
| **TQ-11** | No assertion is swallowed: no `try`/`except: pass` or catch-all around it, no expected-exception check broad enough to accept any error (`pytest.raises(Exception)`, `toThrow()` with no matcher, `@Test(expected = Exception.class)`) | Q | TR3 |
| **TQ-12** | The oracle is independent and specific: not truthiness, not-null or "length > 0" where a value is known; not a value compared with itself; not an expected value computed by calling the code under test or re-implementing its formula | Q | TR3 |
| **TQ-13** | Snapshot and golden files that changed in this diff were changed on purpose, and the reviewer can see the content change. A snapshot regenerated alongside a behaviour change approves whatever the code now does | Q | TR3 |
| **TQ-14** | The test runs the changed code at all: right import, right module patched, not the mock module, and a file name and test name the runner collects | Q | TR1 |

---

## 3. Edges and errors

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-15** | Each new comparison, range or limit is tested just below, at and just above its edge, so an inclusive/exclusive mistake fails a test (CC T5, CC G3) | S | TR5 |
| **TQ-16** | The degenerate inputs the code can receive are tested: empty, null or absent, zero, one, many, maximum, negative, very long, non-ASCII | S | TR5 |
| **TQ-17** | Each new failure branch has a test that forces it and asserts the specific error (type, code, message key) and the state left behind (nothing half-written, resources released) | S | TR6 |
| **TQ-18** | Code that handles dates, times, money or text is tested where it breaks: time zones, DST transitions, month ends, leap days, rounding half-cases, locale-specific formatting and case rules | S | TR5 |
| **TQ-19** | Concurrent code has a test that exercises the concurrency, and the review treats its pass as weak evidence (TR8). No test for a race is a question for the concurrency review, not a pass | D | TR8 |
| **TQ-20** | Input from outside the trust boundary has a test that sends invalid, malformed and hostile values and asserts the specific refusal. A gap here is also a security-lens question | S | TR6 |

---

## 4. Determinism (F.I.R.S.T.)

The F.I.R.S.T. rules are Fast, Independent, Repeatable, Self-validating and Timely (CC p.163–164).
A determinism finding is PLAUSIBLE until a reproduction confirms it
([mutation.md](mutation.md#4-flakiness-reproductions)).

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-21** | No wall clock: the code under test or the test reads the current time directly (`now()`, `Date.now()`, `time.time()`, `Instant.now()`) instead of an injected or frozen clock, and the outcome depends on it | Q | TR7 |
| **TQ-22** | No unseeded randomness: random values, generated IDs, UUIDs, hash or set iteration order, or property-based inputs without a recorded seed decide the outcome | Q | TR7 |
| **TQ-23** | Tests are independent: no module-level or class-level state mutated across tests, no singleton, environment variable, registry or database row left behind, no test that passes only after another | Q | TR7 |
| **TQ-24** | No real network, external service or shared filesystem path in a unit test; no fixed port. A temporary directory or an in-process fake is fine | Q | TR7 |
| **TQ-25** | No sleep used as synchronisation, no polling without a deadline, no async work left un-awaited. Wait on the condition, with a timeout | Q | TR8 |
| **TQ-26** | The outcome doesn't depend on the machine: time zone, locale, CPU count, path separator, case-insensitive filesystem, line endings, or the order the runner discovers tests in | Q | TR7 |
| **TQ-27** | The test is self-validating: pass or fail without a person reading a log or comparing files | Q | TR9 |

---

## 5. Test doubles

Vocabulary (not from the sources): a **dummy** fills a parameter; a **stub** returns canned
answers; a **spy** records calls; a **mock** is pre-programmed with expectations it verifies; a
**fake** is a working lightweight implementation, such as an in-memory repository.

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-28** | Doubles stand in only for boundaries (network, time, randomness, third-party services, sometimes the filesystem or database). The test doesn't mock the system's own collaborators or assert on their calls | S | TR11 |
| **TQ-29** | A double of something you don't own has a boundary or contract test behind it that exercises the real thing the way production does, or the review names the assumption the double encodes | S | TR12 |
| **TQ-30** | A fake behaves like the real thing in what this test relies on: uniqueness, transactions and rollback, ordering, case sensitivity, null handling, error shapes. SQLite standing in for Postgres, or a dict standing in for a cache with expiry, are the usual divergences | D | TR12 |
| **TQ-31** | Every double is wired in and used: the patch targets the name the code under test looks up (in Python, where it is used, not where it is defined), and no stub is configured that the test never exercises | S | TR3 |
| **TQ-32** | The subject under test is not itself partly mocked or spied so that the test exercises a stand-in for the code it claims to test | S | TR11 |

---

## 6. Clarity

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-33** | Each test checks one concept. Several assertions about one outcome are fine; several unrelated behaviours in one test are not (CC p.161–163) | Q | TR15 |
| **TQ-34** | The name states the behaviour, the condition and the expected outcome, and it matches what the body asserts | Q | TR14 |
| **TQ-35** | Build, operate and check are visible, and the test has no logic of its own (`if`, loops, computed expected values) that could hide a bug | Q | TR14 |
| **TQ-36** | The inputs that decide the outcome are visible in the test, not buried in a shared fixture, a helper's defaults, or a data file (Mystery Guest). No unexplained magic values (CC G25) | Q | TR14 |
| **TQ-37** | When it fails, the test says what went wrong: which value, expected against actual. A custom assertion helper doesn't hide which check failed | S | TR14 |

---

## 7. Level and cost

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-38** | The claim is proven at the level where it lives: a cross-boundary claim (an HTTP contract, a CLI's exit code, a persisted record read back) through that boundary; a calculation in a unit test | S | TR20 |
| **TQ-39** | Unit tests are fast: no sleeps, no real network, no large fixtures, no full-application boot for a pure function (CC T9) | Q | TR10 |
| **TQ-40** | No test in the diff is skipped, ignored, marked expected-to-fail or commented out without a reason and a tracking issue. No focused test (`.only`, `fit`, `fdescribe`, `@Only`) that switches off the rest of the suite (CC T4, CC G4) | Q | TR16 |
| **TQ-41** | The new tests actually run in CI: in a path and file pattern the runner collects, not excluded by a marker, tag or profile that CI doesn't select, and the CI step that runs them wasn't removed or made non-blocking | Q | TR1 |

---

## 8. Suite health

| ID | Check | Tier | Principle |
|---|---|:-:|---|
| **TQ-42** | Where a coverage report exists, every changed branch and `catch` body is executed by some test. An uncovered changed line is a TQ-3 candidate. A covered one still needs TQ-7, because line coverage doesn't show an assertion depends on it (CC T2, CC T8) | S | TR19 |
| **TQ-43** | A production file whose test usually changes with it, changed here without it, is a stale-test candidate. Ask whether the old tests still describe the new behaviour | D | TR17 |
| **TQ-44** | Unrelated tests that keep changing together, in history or in this diff, share a duplicated assertion block or setup that wants a test-data object and a custom assertion | D | TR17 |
| **TQ-45** | The test code isn't becoming the hotspot: long setup, a test file growing past what a reader can hold, duplicated fixtures, or test code flat while application code grows in the same component | D | TR13 |

---

## Severity hints for test findings

Use peer-review's anchors ([report.md](../peer-review/report.md#severity)). For tests they read:

| Severity | Test findings |
|---|---|
| **blocker** | The merge switches off tests beyond the diff: a focused test, a collection or CI change that drops tests, a step made non-blocking. Or the only evidence for a security, money or data-integrity criterion can't fail, *and* the behaviour is unproven by anything else |
| **major** | New behaviour or a claimed criterion with no test (missing); a test that can't fail (a surviving mutation on a changed branch); a bug fix with no regression test, or one that passes on the old code; a new flaky test; a skipped test with no reason; a stale test co-change with strong history |
| **minor** | A weak oracle where a stronger one is easy; a missing edge case on a non-critical path; a mock of an internal collaborator; mystery data; a slow unit test; a name that doesn't match the body |
| **nit** | Naming polish, assertion-message wording, test ordering |

Raise one step when the code under test is a hotspot, a public interface, or on a Deep trigger
(money, auth, tenancy, personal data, crypto, migrations, concurrency). Lower one step for test
helpers and fixtures nobody else uses.
