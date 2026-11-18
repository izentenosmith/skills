# Theory: The Principles Every Test Finding Cites (TR1–TR22)

> A test finding cites the principle that makes it worth a reader's attention, and a process rule
> cites the principle that justifies it. Each principle gives **what it says**, **why it holds**,
> and **what ignoring it looks like** in a review. Sources by short name:
>
> | Short name | Source | Pages cited as |
> |---|---|---|
> | **CC** | Robert C. Martin, *Clean Code* (Prentice Hall, 2009). Chapter 9 "Unit Tests", chapter 17's test heuristics T1–T9, and the error-handling, boundaries and concurrency chapters | PDF pages (printed + 31) |
> | **BKS** | Jason Cohen et al., *Best Kept Secrets of Peer Code Review* (SmartBear, 2006) | printed pages |
> | **XR** | Adam Tornhill, *Software Design X-Rays* (Pragmatic, 2018) | PDF pages |
> | **ACR** | Kamalı, Tuna, Haratian & Tüzün, *Rethinking Code Review in the Age of AI: A Vision for Agentic Code Review* (arXiv 2605.17548v2, 2026) | PDF pages |
> | **ECR** | Dave Liddament, *Effective Code Review* (PHP Day talk) | slide titles |
>
> Clean Code's own test heuristics are cited as **CC T1** to **CC T9**. They are the book's IDs,
> not this skill's. This skill's principles are **TR**, and its checks are **TQ**
> ([checklist.md](checklist.md)).
>
> **Practical knowledge from outside these sources** is marked **(not from the sources)**. That
> covers mutation-testing tools and the mutation model, the test-double vocabulary (dummy, stub,
> spy, mock, fake), the smell names from Meszaros' *xUnit Test Patterns*, and flakiness tooling. It
> is stated as practice, with no page cite.
>
> **Repo conventions** come from this repo's `acceptance-tests`
> and `tdd` skills. They are cited by skill name. test-review checks
> that their records hold. It never contradicts them.

---

## Part A: What a test is worth

### TR1: A test is evidence for a claim, and it is worth what it would catch
**Says:** Judge a test by the defect it would catch, never by its existence, its count or its
coverage. A test is the change's evidence that a claimed behaviour holds. **Why:** "That seems like
enough" is the metric many programmers use, and a suite is insufficient while there are
conditions it hasn't explored or calculations it hasn't validated (CC T1, p.344). "Do the tests test
the required functionality?" is a review question in its own right (ECR). A finding in agentic review
is a claim, its evidence and a confidence level (ACR p.19). A test is the evidence half of the
author's claim, and evidence that can't distinguish right from wrong is no evidence. **Ignoring
it:** "Tests added ✓" as a review comment.

### TR2: Test the requirement, not the code path
**Says:** Map every claimed behaviour and acceptance criterion to the test that proves it, at the
boundary the claim names. A test of the code path that misses the requirement is weak evidence.
**Why:** Agentic review checks the change against the issue's acceptance criteria and reports what
is missing (ACR p.16–17). "The change actually implements the issue" and "tests show the algorithm
works as documented" are on the book's checklist (BKS p.112). The talk's T-junction example: the
cookie has to be dropped on the exit side, and a test that only checks a cookie was dropped passes
the wrong code (ECR). Repo convention: acceptance-tests records which test proves which criterion,
one line per criterion, and its tests assert the specific outcome. **Ignoring it:** Every test
passes, and the one criterion that mattered has no test.

### TR3: A test that can't fail proves nothing, and a named mutation shows it
**Says:** For every changed production branch, name a plausible mutation and find the assertion
that would go red. If none would, the test is a finding. **Why:** A suite should test everything
that could possibly break (CC T1, p.344). The book's own SerialDate review found the existing tests
all passed while large parts of the class were never exercised (CC p.299–300). Mutation analysis
makes the question concrete: change one operator, call or constant, and see whether the suite
notices (not from the sources). The same discipline runs through this repo's devils-advocate
("a passing test is a claim, not a fact"). **Ignoring it:** Green tests that would stay green with
the feature deleted.

### TR4: A bug fix needs a test that fails on the old code, and tests near the bug
**Says:** A fix carries a regression test that fails on the pre-fix code for the reported reason,
plus tests around the fix. **Why:** Bugs congregate. When you find one, test the function
exhaustively, because the bug probably wasn't alone (CC T6, p.345). A test written alongside its fix
can pass for the wrong reason, so the only proof that it captures the defect is running it against
the code without the fix (repo convention, `harness/redgreen.py`). **Ignoring it:** A fix "covered"
by a test that passed before the fix too.

### TR5: Boundaries are where code breaks
**Says:** Every new comparison, range, limit and index gets tests on both sides of its edge and on
the edge itself. **Why:** We often get the middle of an algorithm right and misjudge the boundaries
(CC T5, p.345). Developers seldom realise how complicated correct behaviour is, so look for every
boundary condition and write a test for it (CC G3, p.320). Splitting a muddled test by concept
exposed a missing case: adding a month to February 28th (CC p.163). Writing independent tests for
SerialDate found real boundary bugs (CC p.299–300). **Ignoring it:** Tests at 5 and 500 for a rule
that changes at 100.

### TR6: Error paths are behaviour, and they need tests too
**Says:** Each new failure branch gets a test that forces it and asserts the specific error and the
state left behind. **Why:** "Tests cover errors and invalid parameters" is a checklist item
because it is so often missing (BKS p.112). Write tests that force exceptions, and treat a `try`
like a transaction: the catch must leave the program in a consistent state (CC p.136–137).
**Ignoring it:** A happy-path suite, and the first timeout in production.

## Part B: A signal you can trust

### TR7: A test gives the same answer every time, anywhere, in any order
**Says:** Tests are Independent and Repeatable: no test sets up the next, they run in any order,
and they pass in any environment, including offline. Control time, randomness and the environment
instead of reading them. **Why:** When tests depend on each other, the first failure cascades and
hides downstream defects (CC p.163). Tests that aren't repeatable always come with an excuse for
failing (CC p.163). Martin's own retrospective on a timer test: mock the timing functions to get
"absolute control over the time" (CC p.153). Depending on an interface makes a deterministic test
implementation possible (CC p.180–181). **Ignoring it:** A test that fails at midnight UTC, on the
CI runner in another time zone, or only when run after its neighbour.

### TR8: A flaky test is a defect report, and one run is not evidence
**Says:** An intermittent failure is a finding to reproduce, not noise to retry. Never cite one red
run as proof or one green run as safety. **Why:** A single run may not reflect stable behaviour.
Multi-run aggregation or explicit flakiness classification must come before results count as
evidence. The main root causes are async waits, concurrency and order dependency (Luo et al., in
ACR p.18). Spurious failures are candidate threading bugs, and "one-offs" don't exist (CC p.218). A
naive race test can need a vast number of iterations to fail, so a passing concurrency test is weak
evidence (CC p.370–372). **Ignoring it:** `@retry(3)` as the fix, and the race ships.

### TR9: A test passes or fails on its own
**Says:** The test's output is a boolean. Nobody reads a log or diffs two files by hand to know.
**Why:** If tests aren't Self-validating, failure becomes subjective and running them needs a long
manual evaluation (CC p.163). **Ignoring it:** A test that prints the result and always passes.

### TR10: Slow tests get dropped, and tests that need ceremony don't get run
**Says:** Unit tests are fast. All tests run with one command. **Why:** A slow test is a test that
won't get run, and when things get tight the slow ones are dropped (CC T9, p.345). Slow tests aren't
run often, so problems aren't found early (CC p.163). You should be able to run all the unit tests
with one command (CC E2, p.318). **Ignoring it:** A `sleep(5)` per test, and a suite people stop
running locally.

## Part C: Test doubles

### TR11: Substitute at the boundary. Excess mocking tests the mechanism
**Says:** Use doubles for what crosses out of the system (the network, time, randomness, third-party
services) and real code for what you own. A test that asserts on calls to your own collaborators
tests how, not what. **Why:** Excess mocking breaks encapsulation and tests a mechanism rather than
a behaviour. Each time the implementation changes, the test has to change too, and the suite loses
its value as a true regression suite (XR p.43). Repo convention: tdd's mocking guide says mock only
at the system boundary and verify state and observable output, not the conversation between
internals. **Ignoring it:** A test that mirrors the implementation line by line, and passes while
the real collaborator is broken.

### TR12: Depend on what you control, and pin what you don't with a boundary test
**Says:** Where the code relies on third-party behaviour, a boundary or contract test exercises the
real thing the way production does. A double of a third-party API encodes an assumption, and that
assumption needs its own test. **Why:** Learning tests call the third-party API the way the
application expects to use it, and they show when an upgrade changes behaviour (CC p.147–149).
Without outbound boundary tests that exercise the interface the same way production does, teams
avoid upgrades (CC p.149). Few places should know third-party particulars: depend on something you
control (CC p.151). **Ignoring it:** A mock that returns the shape the author believes the API
returns, and a suite that stays green when the API changes.

## Part D: Clean tests

### TR13: Test code gets the same bar as production code
**Says:** Review test code for clarity, duplication and design with the same care as production
code. **Why:** Dirty tests are equivalent to, if not worse than, no tests: they get harder to change
until the team discards them, and then the production code rots out of fear of change
(CC p.154–155). Test code "often receives considerably less love at code reviews", and some of the
worst hotspots are tests (XR p.45, p.55). The dual standard: test code may be less efficient than
production code, never less clean (CC p.158–161). **Ignoring it:** Waving through a 300-line test
because "it's only a test".

### TR14: Readability is the first property of a test
**Says:** A test shows its build, operate and check steps, keeps only the details that matter to
it, and reads in the domain's language. **Why:** What makes a clean test is "readability,
readability, and readability" (CC p.155). The refactored FitNesse tests make the Build-Operate-Check
pattern obvious and drop the details that obscure intent (CC p.157–158). A domain-specific testing
language grows out of refactoring tests (CC p.158). Don't over-abstract tests, though: they lose
their value as documentation (XR p.64). **Ignoring it:** The reader has to run the test in their
head to learn what it checks.

### TR15: One concept per test
**Says:** Each test checks one concept, with as few assertions per concept as it needs. Assertion
count alone is not a finding. **Why:** The single-assert rule is "a good guideline", but the better
rule is one concept per test (CC p.161–163). A test that checks one thing after another forces the
reader to work out why each section is there, and splitting it by concept exposed the missing
February 28th case (CC p.162–163). **Ignoring it:** A `test_everything` that fails for one of six
reasons, or a nit demanding one assert.

### TR16: An ignored test is a question, and a disabled safety needs a reason
**Says:** A skipped, ignored or commented-out test in the diff carries its reason and its tracking
issue. **Why:** An ignored test expresses a question about an ambiguous requirement (CC T4, p.344).
Overriding safeties, disabled failing tests included, trades a green build for later debugging
(CC G4, p.320). **Ignoring it:** `@skip` with no reason, and nobody remembers why a year later.

## Part E: History and coverage

### TR17: A test should change with its code, and unrelated tests shouldn't change together
**Says:** A production file whose test usually changes with it, changed without it, is a stale-test
candidate. Unrelated tests that keep changing together hide duplication. **Why:** A unit test that
changes with its code under test is expected, and its absence should worry you, because it means the
tests aren't kept up to date (XR p.50). A cluster of unrelated tests that change together usually
hides duplicated assertion blocks and a missing test-data abstraction (XR p.54–55). Same-commit
coupling misses tests committed separately from their code (XR p.54). **Ignoring it:** Behaviour
changed, the old tests still pass, and nobody asks why they didn't need to change.

### TR18: Tests age, so a passing old test is weaker evidence than it looks
**Says:** A test written for an earlier version of the behaviour may no longer exercise the case
that matters now. **Why:** Old code tends to get more stable, but test cases grow old in the sense
that they become less likely to find failures, and they must evolve with the system to stay
relevant (XR p.84). Test suites that don't grow with the application are cost sinks (XR p.74).
Compare the trends of application code and test code per component to catch abandoned tests
(XR p.115). **Ignoring it:** "Existing tests still pass" offered as proof for new behaviour.

### TR19: Coverage shows what never ran, not what was checked
**Says:** Use coverage to find untested branches and catch bodies. Never read it as proof that the
covered lines are verified. **Why:** Use a coverage tool: it shows the `if` and `catch` bodies no
test has executed (CC T2, p.344). The pattern of what passing tests do and don't execute is a clue to
why failing tests fail (CC T8, p.345). SerialDate's tests executed only about half its statements,
and the gaps hid a wrong algorithm (CC p.299–300). A line counts as covered when it runs, whether or
not any assertion depends on its result. Mutation score measures the second (not from the sources).
**Ignoring it:** "Coverage is 92%" as the answer to "would these tests fail?".

### TR20: Prove a claim at the level where it lives
**Says:** A claim about what a user or caller sees is proven through that boundary. A claim about a
calculation is proven with a unit test. Each level catches what the other misses. **Why:** Running
only the unit tests missed behaviour that only the acceptance tests pinned (CC p.255). Maintainable
end-to-end tests don't depend on details of the rendered UI (XR p.74). Generated UI layout is QA's
job, not review's (BKS p.122). Repo convention: acceptance-tests drives the outermost public
boundary with fakes only outside it. **Ignoring it:** An API contract "proven" by a unit test that
mocks the HTTP layer, or every rounding rule tested through a browser.

## Part F: Discipline

### TR21: Run the probe outside the tree before you call a test vacuous
**Says:** A claim that a test can't fail, or is flaky, becomes CONFIRMED only when a probe shows it:
the named mutation survives in a scratch copy, or the flake reproduces under a controlled clock,
zone, seed or order. Run each probe twice. Reasoning alone gives PLAUSIBLE, with the probe named.
**Why:** Execution evidence replaces speculation, and single runs aren't trustworthy (ACR p.18).
A fabricated finding produces an invalid patch, and the human ends up untangling the noise
(ACR p.23–24). **Ignoring it:** "This test can't fail" asserted confidently about a test that does.

### TR22: Sweep for missing tests with a checklist, one item at a time
**Says:** Missing tests are omissions, so hunt them with a short list, one item across the whole
change before the next. **Why:** Omissions are the hardest defects to see (BKS p.63). A checklist is
most effective at catching them: it reminds the reviewer that "unit tests have been created", and if
the author forgot, the reviewer probably will too (BKS p.111). One item across the whole product
beats every item line by line (BKS p.133–134). Long test setup is itself a signal: the longer the
setup, the harder the code under test is to use (XR p.43). **Ignoring it:** Reading the tests that
are there, and never asking which ones aren't.
