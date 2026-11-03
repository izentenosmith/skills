# Smells: Test Smells, How to Spot Them, What to Do

> A test smell is a pattern in test code that usually costs something: a defect it lets through, a
> flake, or a test nobody can change. Like any smell it is a heuristic. A finding names the smell
> **and its cost in this diff**: the mutation that survives, the run that flips, the next change
> that has to edit twelve tests. A smell with no cost is taste, and taste is dropped.
>
> **Where the names come from.** Most names below come from Gerard Meszaros, *xUnit Test Patterns*
> (2007), or from the test-smell research that followed it (van Deursen et al., 2001; the tsDetect
> catalogue). Those names are **not from the sources**. Where Clean Code or Software Design X-Rays
> describe the same problem, the cite is given. A few names are this skill's own, marked *(here)*.
>
> Each smell links to the check that finds it ([checklist.md](checklist.md)) and the principle the
> finding cites ([theory.md](theory.md)).

---

## 1. Smells that let defects through

These are the ones that matter most, because each can make a test pass while the behaviour is broken.
Report them as `test` findings, usually `major` on a changed branch.

| Smell | How to spot it | Why it matters | The fix | Check · principle |
|---|---|---|---|---|
| **The Liar** *(folk name)* | The test passes, but no assertion depends on the behaviour its name claims | It is counted as evidence and is none. The feature could be deleted | Assert the specific outcome the name promises. Confirm with a mutation probe | TQ-7, TQ-8 · TR3 |
| **Empty Test** / **No Assertion** | A body that only calls the code, or asserts nothing about the result | It catches crashes only. Fine as a named smoke test, wrong as a behaviour test | Add the assertion, or rename it `smoke_*` and test the behaviour elsewhere | TQ-8 · TR1 |
| **Mock Tautology** *(here)* | A stub returns X, the code forwards it, and the test asserts X came back | The test checks the stub's configuration. The real logic is never on the path | Use a real collaborator or a fake. Assert on what the code adds to the value | TQ-9 · TR3 |
| **Unreachable Assertion** *(here)* | An `assert` in a loop over a collection that is empty in this test, in a callback that never fires, after an early `return`, or in an un-awaited promise | The test passes because the check never runs | Assert the collection's size first, await the promise, assert the callback was invoked with the expected value | TQ-10 · TR3 |
| **Swallowed Assertion** *(here)* | A `try`/`except` or catch-all around the assertion, or a broad expected-exception check (`raises(Exception)`, `toThrow()` with no matcher) | An assertion failure, or the wrong exception, is caught and the test goes green | Remove the catch. Expect the specific error type and code | TQ-11 · TR3 |
| **Self-Fulfilling Oracle** *(here)* | The expected value is computed by calling the code under test, re-implementing its formula, or comparing a value with itself | A wrong formula yields a wrong expected value and agrees with itself | Write the expected value by hand, from the requirement, for a worked case | TQ-12 · TR3 |
| **Weak Oracle** *(here)* | `assert result`, `is not None`, `len(x) > 0`, `status != 500` where the exact value is known | Most wrong answers pass. An off-by-one can't fail it | Assert the exact value, or the exact property the requirement states | TQ-12 · TR1 |
| **Blind Snapshot** *(here)* | A snapshot or golden file regenerated in the same diff as the behaviour change, too large for the reviewer to read | It approves whatever the code now does, the bug included | Keep snapshots small and focused. Review the snapshot diff as code. Assert key fields explicitly | TQ-13 · TR3 |
| **Phantom Test** *(here)* | The test never runs: a file or function name the runner doesn't collect, a missing annotation, a marker CI excludes, a `.only` elsewhere | It reads as coverage and executes nothing | Match the runner's pattern. Run it once and see it fail on purpose | TQ-14, TQ-41 · TR1 |
| **Happy-Path Only** *(here)* | Tests for valid input; no test forces the new error branch | The error branch, often the one that corrupts state, has no evidence | One test per failure branch, asserting the specific error and the state after it (CC p.136–137) | TQ-17 · TR6 |
| **Middle-of-the-Range** *(here)* | Test inputs far from every boundary, such as 5 and 500 for a rule at 100 | Inclusive/exclusive mistakes survive (CC T5, CC G3) | Test just below, at and just above each edge | TQ-15 · TR5 |
| **Stale Test** *(here)* | Behaviour changed, the test that usually changes with it didn't, and it still passes | It tests the old rule, or nothing that changed. Tests age (XR p.50, p.84) | Update the test to the new rule. If it still passes unchanged, find out why it never pinned the old one | TQ-43, TQ-6 · TR17 |

## 2. Smells that make results untrustworthy

A test that fails at random trains a team to ignore red. Report these as `test` findings, `major`
when the test is new in this diff. Confirm them with a reproduction ([mutation.md](mutation.md#4-flakiness-reproductions)).

| Smell | How to spot it | Why it matters | The fix | Check · principle |
|---|---|---|---|---|
| **Erratic Test** (flaky) | Passes and fails on the same code. Retries, `@flaky` or reruns added in the diff | Root causes are async waits, concurrency and order dependency (Luo et al., in ACR p.18). A flake near concurrent code is a probable race (CC p.218) | Find the hidden input and control it. A retry is not a fix | TQ-21 to TQ-26 · TR8 |
| **Interacting Tests** | A test passes alone and fails after another, or the reverse. Shared module state, a singleton, an env var, a DB row left behind | The first failure cascades and hides later ones (CC p.163) | Fresh state per test. Tear down what you set up | TQ-23 · TR7 |
| **Time Bomb** *(here)* | `now()` read directly, or a hard-coded date that will pass into the past | It fails at midnight, at month end, at DST, or on a date next year | Inject or freeze the clock (CC p.153) | TQ-21 · TR7 |
| **Unseeded Random** *(here)* | Random inputs, UUIDs, set or hash order decide the outcome, and no seed is recorded | A failure can't be reproduced | Seed it and log the seed, or remove the randomness | TQ-22 · TR7 |
| **Sleepy Test** | `sleep()` used to wait for work to finish | Slow on fast machines, flaky on slow ones (CC T9) | Wait on the condition, with a deadline | TQ-25 · TR8, TR10 |
| **Works on My Machine** *(here)* | The outcome depends on the zone, the locale, path separators, case sensitivity, CPU count or the author's directory layout | It is not Repeatable in any environment (CC p.163) | Pin the environment inside the test, or make the code independent of it | TQ-26 · TR7 |
| **Resource Optimism** | A unit test calls a real service, the internet, or a file or port it assumes exists | It fails offline and is slow. It's not Repeatable (CC p.163) | A fake at the boundary, plus one contract test for the real thing | TQ-24 · TR7, TR12 |
| **Manual Intervention** | The test prints output for someone to read, or writes a file for someone to compare | It is not Self-validating, and failure is a matter of opinion (CC p.163) | Assert on the output | TQ-27 · TR9 |

## 3. Smells in the use of doubles

| Smell | How to spot it | Why it matters | The fix | Check · principle |
|---|---|---|---|---|
| **Over-Mocking** | Many doubles of the system's own classes; assertions on call counts and argument order to internal collaborators | It tests the mechanism, breaks on every refactor, and stops being a regression suite (XR p.43) | Real collaborators. Doubles only at the boundary. Assert on outcomes | TQ-28 · TR11 |
| **Mocking What You Don't Own** *(folk name)* | A third-party client mocked to the shape the author expects, with no boundary test | The mock encodes an assumption, and the suite stays green when the API changes (CC p.147–149) | Wrap the third party in your own interface and fake that. Add a learning or contract test against the real one | TQ-29 · TR12 |
| **Divergent Fake** *(here)* | An in-memory fake missing what the test relies on: unique constraints, transactions, ordering, case rules, error shapes | The test passes against behaviour production doesn't have | Run the fake and the real thing through one shared contract test, or use a real test database | TQ-30 · TR12 |
| **Misdirected Patch** *(here)* | The patch targets the name where it is defined, not where the code under test looks it up; or a stub nobody calls | The real dependency runs, or the test exercises nothing | Patch where it is used. Delete unused stubs | TQ-31 · TR3 |
| **Mocked Subject** *(here)* | The class under test is partly mocked or spied, so its own methods are stand-ins | The test proves the stand-in works | Test the real subject. Split the class if a part of it has to be replaced | TQ-32 · TR11 |

## 4. Smells that make tests hard to read and change

These are evolvability findings: real, ranked below the defect smells, usually `minor`
(TR13, CC p.154–155).

| Smell | How to spot it | Why it matters | The fix | Check · principle |
|---|---|---|---|---|
| **Eager Test** | One test checks several unrelated behaviours | The reader has to work out what each section is for, and a missing case hides among the others (CC p.162–163) | One concept per test | TQ-33 · TR15 |
| **Assertion Roulette** | Many bare assertions with no messages, so a failure doesn't say which one | Diagnosis needs a debugger | Assertion messages, or one custom assertion per concept | TQ-37 · TR14 |
| **Mystery Guest** | The input that decides the outcome lives in a shared fixture, a data file or a helper's defaults | The reader can't see why the expected value is right | Put the deciding values in the test, and keep incidental ones in a builder | TQ-36 · TR14 |
| **General Fixture** | A large shared setup that every test uses a slice of | Changing it breaks unrelated tests. Setup hides what each test needs | Per-test setup, or small builders with explicit overrides | TQ-36 · TR14 |
| **Obscure Test** | Noise (parsing, plumbing, casting) drowns the build, operate and check steps | The FitNesse example in Clean Code: a swarm of details before the test makes sense (CC p.155–157) | Extract a domain-specific testing language (CC p.158) | TQ-35 · TR14 |
| **Conditional Test Logic** | `if`, loops or `try` inside a test, or expected values computed in the test | The test has its own bugs, and nobody tests the test | Straight-line tests. Parametrise instead of looping | TQ-35 · TR14 |
| **Misleading Name** *(here)* | The name says one behaviour and the body asserts another, or the name says only `test_1` | The name is the specification a reader trusts | Name the behaviour, the condition and the outcome | TQ-34 · TR14 |
| **Magic Values** | Unexplained numbers and strings as inputs or expected values (CC G25) | The reader can't tell an essential value from an arbitrary one | Named constants, or a comment for a worked example | TQ-36 · TR14 |
| **Long Setup** | Many lines of arrangement before the action | It is "the messenger" that the code under test is hard to use (XR p.43) | Raise it as a design question for peer-review's design lens, not only a test fix | TQ-45 · TR22, TR13 |
| **Giant Test File** | A test file of thousands of lines that keeps growing | Some of the worst hotspots are tests (XR p.36, p.45) | Split by behaviour. Extract test-data builders | TQ-45 · TR13 |
| **Duplicated Assertion Block** | The same group of assertions copied across tests. In history, unrelated tests that change together | Every criterion change becomes shotgun surgery across tests (XR p.54–55) | A test-data object and a custom assertion | TQ-44 · TR17 |
| **Over-Abstracted Test** *(here)* | Helpers so generic that a test reads as `run_case(7)` | Tests lose their value as documentation (XR p.64) | Inline the deciding inputs. Keep the helpers for the plumbing | TQ-36 · TR14 |

## 5. Smells in the suite's shape

| Smell | How to spot it | Why it matters | The fix | Check · principle |
|---|---|---|---|---|
| **Ignored Test** | `skip`, `@Ignore`, `xfail`, `xit` or a commented-out test, with no reason | An ignored test is a question about an ambiguity (CC T4). A disabled safety trades a green build for debugging (CC G4) | A reason and a tracking issue, or delete it | TQ-40 · TR16 |
| **Focused Test** *(folk name)* | `.only`, `fit`, `fdescribe` committed | Every other test in the file, sometimes the suite, silently stops running | Remove it. Add a lint rule (`no-only-tests` or the runner's forbid-only flag) as a process fix | TQ-40 · TR16 |
| **Slow Tests** | Unit tests that sleep, boot the app or call the network | A slow test won't get run (CC T9) | Move the slow part behind a boundary. Keep the slow tests in a separate, still-required suite | TQ-39 · TR10 |
| **Wrong-Level Test** *(here)* | An API contract proven by a unit test that mocks the HTTP layer; every arithmetic rule tested through a browser | The first misses integration defects (CC p.255). The second is slow and brittle (XR p.74) | Prove each claim at its level | TQ-38 · TR20 |
| **Coverage Theatre** *(here)* | A coverage number cited as proof; tests written to touch lines without asserting on them | Line coverage counts execution, not checking (TR19) | Ask the mutation question of the covered lines | TQ-42 · TR19 |
