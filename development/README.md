# development

Six skills that take a change from a vague idea to reviewed, tested code. They form a pipeline — each stage checks the one before it — but every one also works alone.

```
architect-deep-dive → agent-brief → tdd → refactor-review → devils-advocate → tyr-verdict
   (resolve design)    (the plan)   (build)  (clean up)      (assume broken)   (judge + fix loop)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time — options with trade-offs, a recommendation and its reversal cost — against a stated charter and a live question count. Infers answers from the codebase where it can. |
| [agent-brief](agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. |
| [tdd](tdd/SKILL.md) | Test-driven development via the red-green-refactor loop, in vertical slices rather than horizontal layers. |
| [refactor-review](refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |
| [devils-advocate](devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. |
| [tyr-verdict](tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |

## How to use them

**Copy the folders you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus every reference doc it needs — so one folder is a complete install of one skill. Nothing here reads a file outside its own directory.

Then either let the agent trigger a skill when your request matches its `description`, or call it by name:

```
/architect-deep-dive   /agent-brief      /tdd
/refactor-review       /devils-advocate  /tyr-verdict
```

If you copy only some of them, the cross-links between stages will point at folders that aren't there. That's survivable by design: the handoff text still names the next skill, so you know what would have run.

## How much of the pipeline to run

Six stages on a two-line fix cost more than the fix. Pick a tier **once, up front**, and say which you picked:

| Tier | The change | Run |
|------|-----------|-----|
| **Trivial** | A localized fix behind an existing seam. No new behavior surface, no new boundary. | `tdd → refactor-review` (3–4) |
| **Standard** | A new capability inside existing structure. | `agent-brief → … → tyr-verdict` (2–6); add stage 1 if the design isn't already obvious |
| **Large / risky** | New subsystem, a change crossing existing boundaries, or one touching data migration, money, permissions, or tenancy. | All six — and stage 1's decomposition splits it into increments that each run 2–6 |

Two rules that make the tiering honest:

- **Calibrate once, not stage by stage.** Deciding to skip a stage *while standing in front of it* is how the discipline erodes everywhere, because the stage you skip is always the one that looked unnecessary.
- **Stages 5–6 don't get dropped** on anything touching data, money, permissions, or tenancy — regardless of diff size. Those are the failures a green suite is worst at catching.

## The loop, and the two working files

The last three stages form a **loop**: if `tyr-verdict` returns NO-GO, its remediation slices feed back into `tdd → refactor-review → devils-advocate → tyr-verdict`, converging when the teardown finds nothing new and the verdict confirms nothing.

The pipeline keeps two files in the repo it's working on — `.workflow/brief.md` (the plan) and `.workflow/ledger.md` (findings, verdicts and carried smells across iterations). They're what let a later stage check an earlier stage's work, and what make the loop terminate.

| Stage | `brief.md` | `ledger.md` |
|---|---|---|
| architect-deep-dive | — (its charter feeds stage 2) | — |
| agent-brief | **creates** | — |
| tdd | reads; **revises** via the feedback edge; ticks criteria | closes remediation slices |
| refactor-review | reads (scope boundaries) | **re-rates** prior noted smells; appends new ones |
| devils-advocate | reads (criteria, edge cases, deferrals) | **appends findings** |
| tyr-verdict | reads | **appends verdicts and slices**; reads noted smells into the verdict |

Add `.workflow/` to the host repo's `.gitignore` unless you want the plan and the ledger in version control — both are legitimate choices, and committing them makes the loop's reasoning reviewable.

## Reference docs

Each lives in the folder of the skill that uses it.

| Doc | Used by |
|-----|---------|
| [clean-architecture](architect-deep-dive/clean-architecture.md) | architect-deep-dive — dependency direction, policy vs. detail, boundary placement |
| [code-smells](refactor-review/code-smells.md) | refactor-review — the symptom catalog |
| [refactoring-techniques](refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [comments](refactor-review/comments.md) | refactor-review — which comments earn their place |
| [good-tests](tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](tdd/interface-design.md) | tdd — designing for testability |

## Measured

These six are the only skills in this repo with a **scored** result behind them — 0.98 vs 0.22 on delta over 36 runs. See [`../evals/`](../evals/README.md) and [benchmark.md](../evals/benchmark.md). (`docker-compose` and `post-mortem` have fixtures and assertions but no scored run.)
