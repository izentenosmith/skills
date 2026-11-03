# Mutation: Name It, Read It, Probe It

> "Would this test fail if the behaviour broke?" is the whole of lens K in one question (TR1, TR3).
> This file makes it concrete in three steps. First **name** a plausible mutation of a changed
> production line. Then **read** the test to see whether an assertion would catch it. At Deep, or
> when a verifier settles a candidate, **probe** it: apply the mutation in a scratch copy and run
> the test. The same file covers the two other probes this skill relies on: the **regression probe**
> for a bug fix, and the **flakiness reproduction**.
>
> Mutation testing as a technique, its vocabulary (killed, survived, equivalent) and the tools in
> section 6 are **not from the sources**. The discipline that a claim needs execution evidence, run
> more than once, is (ACR p.18, TR21).

---

## 1. Mutation thinking: name the mutation

For each changed production branch, pick the mutation a real mistake would most likely produce.
Name it as a one-line edit at `file:line`. One mutation per branch is enough at Standard. Take the
one closest to the claim.

| Construct on the changed line | Mutations to name | What kills it |
|---|---|---|
| A comparison (`<`, `<=`, `==`, `>=`) | Shift the boundary (`<` → `<=`), negate it, swap the operands | A test at the exact edge value, asserting the outcome on each side (TR5) |
| A compound condition (`a and b`) | `and` → `or`, drop one clause, negate one clause | A test where exactly one clause is false |
| Arithmetic and indices | `+` ↔ `-`, `± 1`, `*` ↔ `/`, drop a rounding call | A test whose expected value is computed by hand, not by the code |
| A return | Return early, return a constant, return `None`/`null`/empty, return the input unchanged | An assertion on the specific returned value, not just its presence |
| A call with a side effect | Delete the call (the save, the emit, the audit log, the cache invalidation, the `close`) | An assertion on the observable effect: the record read back, the event received, the resource released |
| A validation or guard | Delete the guard, invert it | A test that sends the invalid input and asserts the specific refusal (TR6) |
| An error path (`raise`, `throw`, `return err`) | Replace it with `pass`, return success, catch and swallow | A test that forces the failure and asserts the specific error and the state after it |
| A default or constant | Flip the default, change the constant to the neighbouring value | A test that relies on the default without passing it |
| A loop | Skip the first or last iteration, break after one | A test with two or more elements whose result depends on every one |
| Collection order | Reverse it, drop the sort, drop the de-duplication | A test with out-of-order or duplicate input, asserting the order |
| Time and locale handling | Drop the time-zone conversion, use local time, drop the locale argument | A test pinned to a zone or locale where the two differ (section 4) |
| A lock or other synchronisation | Remove it (reason about this one, don't probe it) | Rarely any test. Report it to the concurrency review, citing TR8 |

**Equivalent mutants are not findings.** A mutation that can't change behaviour (`<` vs `<=` where
equality is impossible, a dropped call whose result is never used) proves nothing about the test.
Before you report a survivor, name an input on which the mutated code gives a different observable
result. If you can't name one, drop it.

---

## 2. Reading the test for a kill

A mutation is killed when three things hold. Check them in order, from the test body, and quote the
line that settles each.

1. **Reach.** Does any test execute the mutated line? Follow the test's call into the changed
   function. Check the double wiring (TQ-31): a patched-out function is not reached. A coverage
   report answers this one cheaply (TR19).
2. **Infect and propagate.** Does the mutated value change something the test can observe? A
   mutated value that is overwritten, discarded or swallowed before it reaches an output dies
   unseen.
3. **Detect.** Is there an assertion specific enough to tell the two results apart? `assert result`
   doesn't tell 41 from 42. `assert len(items) > 0` doesn't tell one item from two.

Write the result as one of:

- **Killed by** `test_name` at `file:line`, quoting the assertion that would go red.
- **Survives**, naming the step that fails (not reached, not propagated, not detected) and quoting
  the line that shows it.

A survivor is a candidate with check TQ-7 (or TQ-8 to TQ-14 when a test-body defect is the cause).
Its scenario names the mutation, why the test still passes, and the probe that would confirm it.

---

## 3. The manual mutation probe

A probe turns a reasoned survivor into a CONFIRMED one. Run it only where the tier or the verifier
calls for it, never in the work tree, and never with a change to the user's environment.

- [ ] **Make a scratch copy.** Copy the tree into the scratch directory without `.git`, for example
  `rsync -a --exclude .git <repo>/ <scratch>/probe-<id>/`. For committed code only,
  `git archive HEAD | tar -x -C <scratch>/probe-<id>/` works too. Don't use `git worktree add` or
  `git stash`: both write to the repository's shared git state.
- [ ] **Run the baseline first, twice.** Run only the targeted test, unmutated. It must pass both
  times. If it fails, or passes once, the probe is void: record the flake (section 4) instead.
- [ ] **Apply exactly one mutation.** Make the one-line edit you named. Save it as a diff so the
  report can quote it.
- [ ] **Run the targeted test twice.** Use the project's own runner from its existing environment.
  Don't install packages. If the runner isn't available without installing something, write a
  plain script that imports the unit and calls it the way the test does, or record "probe not run,
  and why" and leave the finding PLAUSIBLE.
- [ ] **Check how it failed.** A failure only counts as a kill when an assertion fails. An import
  error, a compile error or a collection error means the mutation broke the build, not that the
  test detected it. Make a smaller mutation and run again.
- [ ] **Record it.** Note the mutation diff, the command, and the summary line of each run.
- [ ] **Delete the scratch copy.**

| Baseline | Mutated, run 1 | Mutated, run 2 | Means |
|---|---|---|---|
| pass, pass | pass | pass | **Survived.** The test can't detect this mutation: CONFIRMED |
| pass, pass | fail (assertion) | fail (assertion) | **Killed.** The candidate is REFUTED |
| pass, pass | fail | pass, or the reverse | **Flaky.** Report a flakiness finding and reproduce it (section 4). The mutation result is void |
| fail, or mixed | any | any | **Void.** The test is broken or flaky before any mutation. Report that instead |

**The regression probe** is the same procedure in reverse, for a bug fix (TQ-4, TR4). In the scratch
copy, revert only the production hunks of the fix and keep the new tests. Run the new regression
test twice. It must fail on an assertion that matches the reported bug. If it passes, the test
doesn't capture the defect: CONFIRMED. If it fails only to load because it imports something the fix
added, that is the wrong reason, so the probe hasn't shown anything yet. Where this repo's harness is
installed, `harness/redgreen.py check` does the regression probe mechanically, with the same
wrong-reason rule.

---

## 4. Flakiness reproductions

A determinism finding (TQ-21 to TQ-27) is PLAUSIBLE from reading. It is CONFIRMED by a run that makes
the hidden input explicit and shows the outcome changes. Run every reproduction in a scratch copy,
twice in each condition. The commands below are common forms (not from the sources). Use the
project's runner's own equivalent.

| Suspicion | Reproduction | Confirmed when |
|---|---|---|
| Wall clock (TQ-21) | Freeze or fake the clock at the edge the code cares about: 23:59:59 and 00:00:00 UTC, the last day of a month, February 29th, a DST transition. Use the project's time-faking library if it has one | The outcome differs across the frozen times |
| Time zone (TQ-26) | Run with `TZ=UTC`, then a zone with a large or fractional offset, such as `TZ=Pacific/Kiritimati` or `TZ=Asia/Kolkata` | Passes in one zone, fails in another |
| Locale (TQ-26) | Run with `LC_ALL=C.UTF-8`, then `tr_TR.UTF-8` (case mapping of `i`) or `de_DE.UTF-8` (decimal comma) | Same |
| Unseeded randomness (TQ-22) | Run with several different seeds, or many repetitions. Record the seed that fails | A recorded seed reproduces the failure |
| Order dependence and shared state (TQ-23) | Run the test alone, then the file in reverse or random order: `pytest -p randomly` (pytest-randomly), `go test -shuffle=on`, `rspec --order random`, `jest --randomize`, JUnit 5's random `MethodOrderer` | Passes alone and fails in some order, or the reverse |
| Async waits and sleeps (TQ-25) | Repeat the test many times (`go test -count=200`, `pytest --count 200` with pytest-repeat), then repeat under CPU load or with parallel workers | Fails in some of the runs |
| Network or filesystem (TQ-24) | Run with the network unavailable, or with a different working directory and `HOME` | Fails without the network, or outside the author's directory layout |
| Concurrency (TQ-19) | Many iterations with a race detector where there is one (`go test -race`), or injected yield points in the code (CC p.219–221) | Any failure. A pass is weak evidence and stays PLAUSIBLE (TR8) |

A flaky test near concurrent code is a probable race in the code, not only a defect in the test
(CC p.218). Report the test finding here and pass the race to the concurrency review.

---

## 5. What a probe result means

| Claim | CONFIRMED by | PLAUSIBLE when | REFUTED by |
|---|---|---|---|
| A test can't fail on a named mutation (TQ-7, TQ-9 to TQ-12) | The mutation survived two runs in a scratch copy, with a clean baseline | Reading shows the survivor, but the probe wasn't run. Name the probe | A kill: the assertion that goes red, quoted, or the probe's failing run |
| A test can't fail, from its text alone (no assertion, a swallowed `except`, a skipped or focused test) | Quoting the line. It is a fact about the text | | The assertion or reason the reader missed, quoted |
| A behaviour has no test (TQ-1, TQ-3) | The search: the symbol, route or message searched for, the test directories searched, nothing reaching it | A test may reach it indirectly through code you couldn't trace | The test that reaches it and the assertion that would catch a mutation |
| A regression test doesn't capture the bug (TQ-4) | The regression probe: the new test passes on the pre-fix code | The probe wasn't run | The probe: it fails on the pre-fix code, on an assertion that matches the bug |
| A test is flaky (TQ-21 to TQ-27) | A reproduction from section 4 that flips the outcome | The mechanism is visible but no reproduction was run. Name the run | The reproduction run in each condition, passing every time, *and* the mechanism shown not to affect the outcome |

Under the PR harness, the finder never runs any of this. It names the mutation and the probe in the
candidate's scenario, and a separate verifier with a scratch copy runs it.

---

## 6. Mutation tools (not from the sources)

A tool runs hundreds of mutations where a reviewer names a handful. Use it at Deep on the riskiest
unit when the project already has it configured, or when a run in a scratch copy needs no new
installs. Scope it to the changed files, because a whole-repo run is slow.

| Ecosystem | Tool | Scope it with |
|---|---|---|
| Python | mutmut, Cosmic Ray | mutmut's paths-to-mutate setting; Cosmic Ray's module path in its config |
| JavaScript, TypeScript | StrykerJS | `--mutate` with the changed file globs |
| C# | Stryker.NET | `--mutate` file patterns |
| Java, JVM | PIT (pitest) | `targetClasses` and `targetTests` |
| Go | go-mutesting | the changed package paths |
| Rust | cargo-mutants | `--file`, or `--in-diff` with the diff |
| PHP | Infection | `--filter` with the changed files |
| Ruby | mutant | the subject expression for the changed classes |
| C, C++ | Mull | the changed translation units |

Read the results with the same rules as a manual probe:

- **A survivor is a candidate, not a finding.** Check it for equivalence (section 1) before you
  report it.
- **A mutation score is a hint, like a coverage number.** Don't report the number as a finding, and
  don't ask for a target score. Report the survivors that matter to the claim.
- **Timeouts and crashes are not kills.** Treat them as void, the way a compile error is void.
