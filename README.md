# Skills

A collection of repo-agnostic AI coding agent skills for taking a feature from a vague idea all the way to reviewed, tested code. Each skill lives in its own folder as a `SKILL.md` file with YAML frontmatter (`name` + `description`) that the agent loads on demand when the work matches.

Works with [Cursor](https://www.cursor.com/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## What's in here

The skills form one connected pipeline — design, specify, build, clean, then an adversarial close — plus the reference docs they lean on.

```
architect-deep-dive → agent-brief → tdd → refactor-review → devils-advocate → tyr-verdict
   (resolve design)    (the plan)   (build)  (clean up)      (assume broken)   (judge + fix loop)
```

The last three stages form a **loop**: if `tyr-verdict` returns NO-GO, its remediation slices feed back into `tdd → refactor-review → devils-advocate → tyr-verdict`, converging when the teardown finds nothing new and the verdict confirms nothing.

The pipeline keeps two files in the repo it's working on — `.workflow/brief.md` (the plan) and `.workflow/ledger.md` (findings, verdicts and carried smells across loop iterations). They're what let a later stage check an earlier stage's work, and what make the loop terminate.

| Stage | `brief.md` | `ledger.md` |
|---|---|---|
| architect-deep-dive | — (its charter feeds stage 2) | — |
| agent-brief | **creates** | — |
| tdd | reads; **revises** via the feedback edge; ticks criteria | closes remediation slices |
| refactor-review | reads (scope boundaries) | **re-rates** prior noted smells; appends new ones |
| devils-advocate | reads (criteria, edge cases, deferrals) | **appends findings** |
| tyr-verdict | reads | **appends verdicts and slices**; reads noted smells into the verdict |

Any stage can optionally hand its **read-only or fresh-context** work to a subagent. Delegation is most valuable at the ends of the pipeline — evidence-gathering before a design decision, and before a verdict — and least valuable in the middle, where the work is a sequential loop that learns from itself.

| Stage | Delegate | Keep in the main thread |
|---|---|---|
| architect-deep-dive | codebase inference behind **[inferred]** answers | the question-by-question dialogue |
| agent-brief | the prior-art hunt | writing and ordering the plan |
| tdd | convention lookups only | **every RED and GREEN — the whole loop** |
| refactor-review | smell identification on a large diff | prescribing and applying the refactors |
| devils-advocate | **the whole teardown** — fresh context is the point | ranking the findings |
| tyr-verdict | per-finding verification | **the severity, the slices, the GO/NO-GO** |

Each skill carries its own copy of the dispatch contract and the working-file rules it needs, so the folders stay independently copyable — see [Conventions](#conventions).

### How much pipeline does this change need?

Six stages on a two-line fix cost more than the fix. Pick a tier **once, up front**, and say which you picked:

| Tier | The change | Run |
|------|-----------|-----|
| **Trivial** | A localized fix behind an existing seam. No new behavior surface, no new boundary. | `tdd → refactor-review` (3–4) |
| **Standard** | A new capability inside existing structure. | `agent-brief → … → tyr-verdict` (2–6); add stage 1 if the design isn't already obvious |
| **Large / risky** | New subsystem, a change that crosses existing boundaries, or one touching data migration, money, permissions, or tenancy. | All six — and stage 1's decomposition splits it into increments that each run 2–6 |

Two rules that make the tiering honest:

- **Calibrate once, not stage by stage.** Deciding to skip a stage *while you're standing in front of it* is how the discipline erodes everywhere, because the stage you skip is always the one that looked unnecessary.
- **Stages 5–6 don't get dropped** on anything touching data, money, permissions, or tenancy — regardless of how small the diff is. Those are the failures a green suite is worst at catching, and a two-line diff is perfectly capable of causing one.

Stage numbers throughout the skills refer to position in the full pipeline, not to a requirement that all six run.

### Workflow skills

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time — options with trade-offs, a recommendation and its reversal cost — against a stated charter and a live question count. Infers answers from the codebase where it can. Run this first. |
| [agent-brief](agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. |
| [tdd](tdd/SKILL.md) | Test-driven development via the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to refactor-review. |
| [refactor-review](refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |
| [devils-advocate](devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. |
| [tyr-verdict](tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |

### Reference docs

These carry no workflow of their own — the skill in the same folder links into them.

| Doc | Used by |
|-----|---------|
| [clean-architecture](architect-deep-dive/clean-architecture.md) | architect-deep-dive — dependency direction, policy vs. detail, boundary placement (Martin) |
| [code-smells](refactor-review/code-smells.md) | refactor-review — the symptom catalog (Refactoring Guru / Fowler) |
| [refactoring-techniques](refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [comments](refactor-review/comments.md) | refactor-review — which comments earn their place (tdd carries the ladder inline) |
| [good-tests](tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](tdd/interface-design.md) | tdd — designing for testability |

Each doc lives in the folder of the skill that uses it, and nothing reaches across folders.

## Do they work?

[`evals/`](evals/README.md) holds the harness that measures it — seeded fixtures with planted defects (a rule that ignores its config, and a vacuous test that hides it), scored assertions, and the recorded result in [evals/benchmark.md](evals/benchmark.md).

Assertions are split: **capability** (does the stage do its job at all) from **delta** (does it do what a change to the skill added). Only the delta column is evidence an edit helped. Against the pre-session baseline over 36 runs: **0.98 vs 0.22** on delta, **0.96 vs 0.92** on capability.

## How to use

Each skill is a folder containing a `SKILL.md` entry point and any reference docs it needs. They work with both Cursor and Claude Code.

1. **Clone the repo** somewhere on your machine.

   ```bash
   git clone https://github.com/izentenosmith/skills.git
   ```

2. **Point your agent at the skills.**
   - **Cursor** — add the cloned directory as a skills source in your Cursor settings, or symlink individual skill folders into your project's `.cursor/skills/` directory.
   - **Claude Code** — point Claude at this directory as a skills source, or symlink skill folders into your user-level skills location. Each `SKILL.md`'s frontmatter `description` tells the agent *when* the skill applies.

3. **Invoke a skill** — either let the agent trigger it automatically when your request matches the description, or call it explicitly:

   ```
   /architect-deep-dive
   /agent-brief
   /tdd
   /refactor-review
   /devils-advocate
   /tyr-verdict
   ```

Every skill also works on its own — `tdd` plans from scratch when there's no brief, `refactor-review` reviews any diff, `devils-advocate` tears down a change it didn't build. The pipeline is the default, the tiers above say how much of it to run, and no stage requires the ones before it. What the descriptions note is where an earlier stage makes a later one sharper.

## Conventions

- **One skill per folder, and the folder stands alone.** Each folder contains a `SKILL.md` (the workflow) plus every reference doc it needs. **Copy any one folder into any project and it works** — no shared root docs, no reference doc outside its own folder. The only cross-folder links are the stage list and the handoff, which name the next skill; if it isn't installed, the prompt still tells you which one to run.
- **Self-containment beats DRY here.** The dispatch contract, the `.workflow/` file rules and the six-stage list are repeated across folders on purpose. That is real duplication with a real cost — change the pipeline's shape and you edit six files — and it buys the thing that matters more: a folder you can paste anywhere.
- **Every `SKILL.md` carries frontmatter** (`name`, `description`) so the agent can decide relevance.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let the agent figure out *how* against the live codebase. No hard-coded file paths or line numbers.

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.
