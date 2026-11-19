# development

Seven skills that take a change from a vague idea to reviewed, tested code, and an eighth, **nexus**, for running several of those pipelines at once. The seven form a pipeline — each stage checks the one before it — but every one also works alone.

```
architect-deep-dive → agent-brief → acceptance-tests → tdd → refactor-review → devils-advocate → tyr-verdict
   (resolve design)    (the plan)   (the finish line)  (build)  (clean up)     (assume broken)   (judge + fix loop)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time — options with trade-offs, a recommendation and its reversal cost — against a stated charter and a live question count. Infers answers from the codebase where it can. |
| [agent-brief](agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. |
| [acceptance-tests](acceptance-tests/SKILL.md) | Turns the brief's acceptance criteria into executable black-box tests through the outermost boundary — written before any code, each red for the right reason — and maps every criterion to its test. tdd is done when they pass. |
| [tdd](tdd/SKILL.md) | Test-driven development via the red-green-refactor loop, in vertical slices rather than horizontal layers. Each test is seen red for the right reason, and each criterion is ticked with the test that proves it. |
| [refactor-review](refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |
| [devils-advocate](devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. |
| [tyr-verdict](tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |
| [nexus](nexus/SKILL.md) | Coordinates several parallel sessions, one PR each through the seven stages. Writes no code: judges each PR on its stage log, answers questions from a register of the user's decisions or brings them to the user as packets, guards shared resources (leases, migration numbers, label series), routes findings that cross slices, and merges only on the user's go. |

## How to use them

Install the whole pipeline from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill architect-deep-dive agent-brief acceptance-tests tdd refactor-review devils-advocate tyr-verdict
```

To run several pipelines at once — one session per PR, or per track of a PR — add the coordinator:

```bash
npx skills add izentenosmith/skills --skill nexus
```

Or one stage at a time:

| Skill | Install |
|---|---|
| architect-deep-dive | `npx skills add izentenosmith/skills --skill architect-deep-dive` |
| agent-brief | `npx skills add izentenosmith/skills --skill agent-brief` |
| acceptance-tests | `npx skills add izentenosmith/skills --skill acceptance-tests` |
| tdd | `npx skills add izentenosmith/skills --skill tdd` |
| refactor-review | `npx skills add izentenosmith/skills --skill refactor-review` |
| devils-advocate | `npx skills add izentenosmith/skills --skill devils-advocate` |
| tyr-verdict | `npx skills add izentenosmith/skills --skill tyr-verdict` |
| nexus | `npx skills add izentenosmith/skills --skill nexus` |

The Trivial tier below needs only `--skill tdd refactor-review`. The repo is private: you need read access and GitHub auth first. That setup, and the flags (`-a`, `-g`, `-y`), are in the [root README](../../README.md#install-with-npx).

Or **copy the folders you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus every reference doc it needs — so one folder is a complete install of one skill. Nothing here reads a file outside its own directory.

Then either let the agent trigger a skill when your request matches its `description`, or call it by name:

```
/architect-deep-dive   /agent-brief      /acceptance-tests
/tdd                   /refactor-review  /devils-advocate  /tyr-verdict
```

If you copy only some of them, the cross-links between stages will point at folders that aren't there. That's survivable by design: the handoff text still names the next skill, so you know what would have run.

## How much of the pipeline to run

Seven stages on a two-line fix cost more than the fix. Pick a tier **once, up front**, and say which you picked:

| Tier | The change | Run |
|------|-----------|-----|
| **Trivial** | A localized fix behind an existing seam. No new behavior surface, no new boundary. | `tdd → refactor-review` (4–5) |
| **Standard** | A new capability inside existing structure. | `agent-brief → … → tyr-verdict` (2–7); add stage 1 if the design isn't already obvious |
| **Large / risky** | New subsystem, a change crossing existing boundaries, or one touching data migration, money, permissions, or tenancy. | All seven — and stage 1's decomposition splits it into increments that each run 2–7 |

Two rules that make the tiering honest:

- **Calibrate once, not stage by stage.** Deciding to skip a stage *while standing in front of it* is how the discipline erodes everywhere, because the stage you skip is always the one that looked unnecessary.
- **Stages 6–7 don't get dropped** on anything touching data, money, permissions, or tenancy — regardless of diff size. Those are the failures a green suite is worst at catching.

## The loop, and the two working files

The last three stages form a **loop**: if `tyr-verdict` returns NO-GO, its remediation slices feed back into `tdd → refactor-review → devils-advocate → tyr-verdict`, converging when the teardown finds nothing new and the verdict confirms nothing.

The pipeline keeps two files in the repo it's working on — `.workflow/brief.md` (the plan) and `.workflow/ledger.md` (findings, verdicts and carried smells across iterations). They're what let a later stage check an earlier stage's work, and what make the loop terminate.

| Stage | `brief.md` | `ledger.md` |
|---|---|---|
| architect-deep-dive | — (its charter feeds stage 2) | — |
| agent-brief | **creates**, as a draft the user approves; archives a finished brief and its ledger together, and stops rather than overwrite an unfinished one | — |
| acceptance-tests | reads criteria; **records** the acceptance tests and their command | — |
| tdd | reads; **revises** via the feedback edge; ticks criteria and ship-checklist items; records `**Base:**` | **appends** closed slices |
| refactor-review | reads (scope boundaries) | **re-rates** prior noted smells; appends new ones |
| devils-advocate | reads (criteria, edge cases, deferrals) | **appends findings** |
| tyr-verdict | reads | **appends verdicts and slices**; reads noted smells into the verdict |

Stage 1 leaves a file of its own per design, `.workflow/designs/<YYYYMMDD-HHMM>-<slug>.md` — a name no other design takes, so parallel sessions, worktrees and merging branches never share or conflict on one. architect-deep-dive writes the charter to it before the first question, appends each decision as it resolves, and marks it `resolved` at handoff. agent-brief reads the design from there, so it survives a new session — and [harness/pipeline.py](../../harness/README.md) can run stages 2–7 from it without you.

The ledger is an **append-only log** in a strict grammar — every stage appends its own section to the current iteration, and state (what's open, what's closed, which smells are carried) is read by replaying it. The grammar is in each writing skill, and in [harness/LEDGER.md](../../harness/LEDGER.md) for the whole picture; [harness/](../../harness/README.md) can check a ledger, or run stages 5–7 and the loop itself.

Three things keep the build honest between those files and the code. **Save points:** tdd commits each green slice on a working branch and records the commit it started from as `**Base:**` in the brief, so a slice that goes wrong costs that slice and every later stage knows what the change is measured against. **The bar itself:** devils-advocate reads the diff for a check that got weaker — a skipped or deleted test, a suppressed checker, a lowered threshold, an acceptance test edited without a brief revision — and tyr-verdict does not accept a green suite as the refutation. **The ship checklist:** rollout, rollback, observability and documentation decisions that no test can prove are checkboxes in the brief; a GO names the ones still open.

Add `.workflow/` to the host repo's `.gitignore` unless you want the plan and the ledger in version control — both are legitimate choices, and committing them makes the loop's reasoning reviewable.

## Several pipelines at once — nexus

An increment that stage 1 decomposes into several PRs can be built in parallel: one session per PR, each running the seven stages in its own worktree, and one more session — the [nexus](nexus/SKILL.md) — over them. The nexus writes no product code. Each session attacks its own work through devils-advocate and tyr-verdict; the nexus judges only the evidence they leave, and it is the only one who sees across sessions: two PRs that took the same migration number, the base branch moving underneath, two branches that pass alone and fail together, a finding in one slice that breaks another.

Everything they share lives in one notes folder outside the worktrees ([notes.md](nexus/notes.md)): a status file the nexus rewrites every turn, so it survives compaction; an environment profile written once, so no session rediscovers how to test and start the repo, with the base branch's baseline; `increment.json`, the increment's requirements and user journeys, every one failing until its test passes on the base after the merge — the increment is done when that list says so, not when the PRs are merged; a register of the user's decisions that every session reads before asking; findings that cross slices; the label series and their next free ids; leases on exclusive resources; production checks that only the user can do; and one stage log per session. Each session gets [the contract](nexus/contract.md) in its first message: start every session — first, resumed or compacted — by reading its own hand-over and the git log and re-running the suite before any new work, end every turn with a status block, ask in a fixed packet (options, recommendation, cost of reversing, the decisions checked), report cross-slice findings as their own block, and never loosen a check, take a migration number, coin a label series or hold a resource without a lease. architect-deep-dive sends its questions in that packet when it runs as a sub-session.

Within one PR, a brief whose criteria split into **parallel tracks** (agent-brief names them only when each has its own write area and needs nothing another builds) can be built the same way, one level down. The session that owns the brief builds the shared seams first. It then starts a child session per track, each running tdd through tyr-verdict to its own GO. It merges each track and runs devils-advocate and tyr-verdict once more on the combined diff before the PR goes up. The tree has one root: registries, the register and the user stay with the top nexus.

The user answers in one place, the nexus's digest, and every ruling gets an id that sessions cite. The user sees only decisions and merges, each already checked against the record and integrated with the latest base, with what wasn't verified said plainly.

The nexus sets **no fixed cap on how many sessions run at once**: every slice that is ready starts, and one is held back only for a reason the nexus can name — it needs what another slice builds, the disk is short, or the user set a limit, recorded as a decision.

## Work that outlives one session

A long build crosses many context windows: usage limits, compactions, crashes, a closed window. Each new session starts with no memory of the last, and the two ways that goes wrong are trying to do everything at once and running out of context mid-feature, and seeing some progress and declaring the job done. Anthropic's [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) names both and describes the fixes. This is where each one lives here:

| The article's practice | Here |
|---|---|
| An initializer session sets up the environment before any coding session | The nexus's first turn, [Before the first session](nexus/SKILL.md#before-the-first-session--set-up-the-increment): decompose, create the notes folder, write `env.md`, record the baseline, write `increment.json`. Standalone, stages 1–3 play that part: the design, the brief, and acceptance tests that are all red |
| A feature list, every entry failing, where only the pass flag may change | `increment.json` for the increment: entries are never removed or reworded, and only the nexus sets `passes`, after the merge, from a test seen passing on the base. Per PR, the brief's criteria and the acceptance tests mapped to them |
| One feature at a time | tdd's vertical slices: one criterion, one red→green cycle, one commit |
| A progress file and git history, so the next session doesn't guess | Each session's stage log, whose last status block is its hand-over; `status.md`, rewritten every nexus turn; the append-only ledger; one commit per green slice and the brief's `**Base:**` |
| A start-up routine: where am I, what happened, is it still working | The contract's [Start of every session](nexus/contract.md#start-of-every-session) and tdd's step 0: the directory and branch, the last hand-over, `git log` and uncommitted work, the brief's ticks, then the suite and the acceptance command before anything new. A test that was green and is red is fixed first |
| An `init.sh`, so no session works out how to run the app | `env.md`: the test, lint, build, start and smoke commands, taken from the repo's instructions and CI, with the base branch's suite counts. Every brief carries them |
| Never remove or edit a test to get green | Acceptance tests change only through a brief revision; devils-advocate reads the diff for the bar itself moving; the contract's "never loosen a check" |
| Mark a feature passing only after testing it as a user would | A tick names its test, `redgreen.py` proves the test was red on the old code, a GO is pinned to the head commit, and the nexus judges the record, not the chat |

**What is not there yet.** Nothing requires driving the running app through a browser for a user-facing change: acceptance tests go through the outermost seam the test tooling can drive, which is usually in-process. The harness guards the ledger against edits but only counts the brief's criteria, and `pipeline.py` hands the whole brief to one tdd call, not one criterion per fresh call. A standalone run keeps no progress note between stages 2 and 4 beyond the brief's ticks and its commits.

## Security runs through the pipeline, not after it

Security is not an eighth stage. Most vulnerabilities are ordinary defects in places where a defect has security consequences, so each stage carries its part, gated by one **security trigger** — the change adds an entry point, crosses a trust boundary, changes who may do what, or handles identity, money, secrets, personal data, paths, queries or URLs:

| Stage | What it adds when the trigger fires |
|---|---|
| architect-deep-dive | Abuse cases, trust boundaries, the authorisation rule and where it's enforced, domain primitives, never-logged values, fail-open/closed per control — or a handoff to [threatmodel](../security/threatmodel/SKILL.md) for anything large |
| agent-brief | Each of those as an acceptance criterion: abuse cases as refusals, authorisation for the allowed and the refused actors, domain primitives as key interfaces |
| acceptance-tests | Refusals tested from outside with their contrast; an actor × operation authorisation matrix with two real identities; refusals that don't leak |
| tdd | Domain primitives built first, tested normal / boundary / invalid / extreme |
| refactor-review | A security-smell family; at a trust boundary those are blocking, never noted |
| devils-advocate | The security surface split into delegates: authorisation bypass, source-to-sink tracing including second-order paths, interface assumptions, leaks, degraded modes |
| tyr-verdict | Security findings refuted only on a code path, never downgraded for being hard to reach, and closed only by a slice with an abuse test |

When the trigger doesn't fire, each stage says so in one line and moves on. For a whole-codebase review rather than a change, use [appsec](../security/appsec/SKILL.md).

## Reference docs

Each lives in the folder of the skill that uses it.

| Doc | Used by |
|-----|---------|
| [clean-architecture](architect-deep-dive/clean-architecture.md) | architect-deep-dive — dependency direction, policy vs. detail, boundary placement |
| [records](architect-deep-dive/records.md) | architect-deep-dive — when a decision earns an ADR, the ADR and glossary formats, where they go |
| [security](architect-deep-dive/security.md) | architect-deep-dive — the security trigger, the questions behind the Security & permissions dimension, when to hand off to threatmodel |
| [code-smells](refactor-review/code-smells.md) | refactor-review — the symptom catalog |
| [refactoring-techniques](refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [comments](refactor-review/comments.md) | refactor-review — which comments earn their place |
| [good-tests](tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](tdd/interface-design.md) | tdd — designing for testability |
| [domain-primitives](tdd/domain-primitives.md) | tdd — security-relevant values as validated, immutable types; validation order; the tests they need; read-once secrets |
| [notes](nexus/notes.md) | nexus — the shared notes folder: status, the environment profile, the increment list, decisions register, cross-slice findings, label series, leases and numbered files, owner checks, stage logs |
| [contract](nexus/contract.md) | nexus — the brief every sub-session gets: the start-of-session routine, status block, question packet, cross-slice findings, what it never does |

## Measured

The seven stages carry the repo's deepest scored result: **0.99 vs 0.15** on delta and **0.99 vs 0.95** on capability, with three runs per eval against the pre-session skills (iteration 37, re-run after save points, the brief's approval gate, the bar-itself attack surface and the ship checklist were added; those four are not yet graded by an assertion of their own). tdd's eval checks what it adds over a capable agent: each criterion ticked with the test that verifies it, each red recorded with the failure it showed, and a tracer bullet that is red on the behavior, not on the seam it needs. All of it was re-run as iteration 49 (2026-11-19, n=3, with the rest of the repo): 1.00 on delta for architect-deep-dive, agent-brief, tdd, devils-advocate, tyr-verdict and acceptance-tests, and 0.92 for refactor-review, where two of three runs recorded a carried smell without its promotion condition. tdd's 1.00 is with its new step 0. `nexus` scored 0.96 against 1.00 there and, re-run as iteration 50 once the session cap was removed, 1.00 on all three runs against 0.87 for a bare agent, on a fixture that shows every convention it needs; the start-of-session routine, `env.md` and `increment.json` have no assertion of their own yet. See [`../evals/`](../../evals/README.md) and [benchmark.md](../../evals/benchmark.md). `acceptance-tests` has eval 27, on the `tdd` fixture: the tests it writes are run against the unchanged code, a correct implementation and three mutants, so a test that is red for the wrong reason or cannot fail is caught by execution, not by reading. Its controls separate as intended. **0.75 against 0.25 for no skill on its first run** — two tests passed on the unimplemented code and the edge had a minute of slack — and **1.00 on all three runs** after the fix: criteria that already hold are tested with their contrast, and edges within seconds.
