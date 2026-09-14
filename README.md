# Skills

A collection of repo-agnostic AI coding agent skills — taking a feature from a vague idea to reviewed, tested code, packaging it to run, and dealing with it once it's live. Each skill lives in its own folder as a `SKILL.md` file with YAML frontmatter (`name` + `description`) that the agent loads on demand when the work matches.

Works with [Cursor](https://www.cursor.com/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**These skills are created and curated around my own use and needs.** They exist because I wanted them for my own projects and work, and they get updated as those projects and that work require — not on a release schedule and not toward anyone else's workflow. Everything here is MIT licensed and free to take, fork, or rewrite; just know that its shape follows what I actually do, and it will keep changing for the same reason.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## What's in here

Three families, in the order work actually moves through them.

```
development/        build the change      six stages, design → adversarial close
containers/         package it to run     dockerfile → docker-compose
operations/         live with it          release-notes · post-mortem
```

| Family | Skills |
|---|---|
| **[development/](development/README.md)** | [architect-deep-dive](development/architect-deep-dive/SKILL.md) · [agent-brief](development/agent-brief/SKILL.md) · [tdd](development/tdd/SKILL.md) · [refactor-review](development/refactor-review/SKILL.md) · [devils-advocate](development/devils-advocate/SKILL.md) · [tyr-verdict](development/tyr-verdict/SKILL.md) |
| **[containers/](containers/README.md)** | [dockerfile](containers/dockerfile/SKILL.md) · [docker-compose](containers/docker-compose/SKILL.md) |
| **[operations/](operations/README.md)** | [release-notes](operations/release-notes/SKILL.md) · [post-mortem](operations/post-mortem/SKILL.md) |

The families are loosely coupled by design. `development` is a genuine pipeline where each stage checks the one before it; `containers` is an ordered pair; `operations` is two independent skills that happen to share an audience outside the code. Every skill also works entirely on its own.

**The family directories are scaffolding for reading this repo, nothing more.** The agent never sees them — it selects on each `SKILL.md`'s frontmatter `description`. When you take a skill, you take the skill folder; see [How to use](#how-to-use).

---

## development — the six-stage pipeline

Design, specify, build, clean, then an adversarial close.

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

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](development/architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time — options with trade-offs, a recommendation and its reversal cost — against a stated charter and a live question count. Infers answers from the codebase where it can. Run this first. |
| [agent-brief](development/agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. |
| [tdd](development/tdd/SKILL.md) | Test-driven development via the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to refactor-review. |
| [refactor-review](development/refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |
| [devils-advocate](development/devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. |
| [tyr-verdict](development/tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |

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

---

## containers

Ordered: an image, then the stack around it.

```
dockerfile → docker-compose
 (the image)  (the stack)
```

| Skill | What it does |
|-------|--------------|
| [dockerfile](containers/dockerfile/SKILL.md) | Reads the stack off the repo, writes a multi-stage production Dockerfile — pinned base, non-root runtime, cache-correct layer order — and generates or repairs the `.dockerignore` that defines its build context. Verifies by building and running, not by reading. |
| [docker-compose](containers/docker-compose/SKILL.md) | Detects the services the code actually connects to, wires them with named volumes, an isolated network and real health gates, and ships a documented `.env.example` plus a dev override. Verifies from cold, twice. |

**Run `dockerfile` first.** Compose orchestrates images; it cannot repair one. Most "compose is broken" reports are an image that doesn't start, doesn't answer its healthcheck, or dies on `SIGTERM`.

---

## operations

What happens around a system that's already running. Two independent skills — neither depends on the other, and both compose backwards into `development`.

| Skill | What it does |
|-------|--------------|
| [release-notes](operations/release-notes/SKILL.md) | Reads the change set from git, classifies every change (including an explicit **drop** bucket for anything with no user-visible effect), and translates each survivor from what was built into what the reader can now do. Depth matched to scope; breaking changes above the fold. |
| [post-mortem](operations/post-mortem/SKILL.md) | Reconstructs a **resolved** incident into a blameless written record — timeline built from a git history date range plus incident docs and PDFs, quantified impact, and **contributing factors** rather than a single root cause. Ends with a pass over the prose hunting the blame that leaks in through grammar. |

`post-mortem` **documents; it does not prescribe.** The incident is already solved, so the skill reconstructs what happened and stops there — no remediation plan, no recommendations, no handoff into the build pipeline. That boundary is what keeps the record trustworthy: a document that reconstructs *and* prescribes has an incentive to shape the reconstruction toward the prescription. What to change next is a decision for whoever owns the system.

It needs inputs you supply: a **date range for the git history** and whatever **incident documentation** exists — the report, a vendor PDF, a chat export, alert emails. It reconstructs from artifacts, not from a description of the incident.

---

## Reference docs

These carry no workflow of their own — the skill in the same folder links into them.

| Doc | Used by |
|-----|---------|
| [clean-architecture](development/architect-deep-dive/clean-architecture.md) | architect-deep-dive — dependency direction, policy vs. detail, boundary placement (Martin) |
| [code-smells](development/refactor-review/code-smells.md) | refactor-review — the symptom catalog (Refactoring Guru / Fowler) |
| [refactoring-techniques](development/refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [comments](development/refactor-review/comments.md) | refactor-review — which comments earn their place (tdd carries the ladder inline) |
| [good-tests](development/tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](development/tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](development/tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](development/tdd/interface-design.md) | tdd — designing for testability |
| [optimization](containers/dockerfile/optimization.md) | dockerfile — base image trade-offs, layer order, cache mounts, secrets, signals |
| [dockerignore](containers/dockerfile/dockerignore.md) | dockerfile — what to exclude and what each exclusion buys |
| [service-catalog](containers/docker-compose/service-catalog.md) | docker-compose — per-service image, readiness probe, volume path, connection string |
| [environments](containers/docker-compose/environments.md) | docker-compose — overrides, merge rules, `.env.example`, secrets |
| [anatomy](operations/release-notes/anatomy.md) | release-notes — the six elements and the commit→outcome translation rules |
| [distribution](operations/release-notes/distribution.md) | release-notes — depth to scope, when visuals earn their place, where to publish |
| [blameless-culture](operations/post-mortem/blameless-culture.md) | post-mortem — why blameless is a data-collection strategy (Google SRE; Dekker) |
| [contributing-factors](operations/post-mortem/contributing-factors.md) | post-mortem — past single-root-cause; the categories to sweep and where to stop |
| [evidence-sources](operations/post-mortem/evidence-sources.md) | post-mortem — reading a git range, incident PDFs, chat exports and monitoring into a sourced timeline |

Each doc lives in the folder of the skill that uses it, and nothing reaches across folders.

## Delegation

Any stage can optionally hand its **read-only or fresh-context** work to a subagent. Delegation is most valuable at the ends of a pipeline — evidence-gathering before a design decision, and before a verdict — and least valuable in the middle, where the work is a sequential loop that learns from itself.

| Skill | Delegate | Keep in the main thread |
|-------|----------|-------------------------|
| architect-deep-dive | codebase inference behind **[inferred]** answers | the question-by-question dialogue |
| agent-brief | the prior-art hunt | writing and ordering the plan |
| tdd | convention lookups only | **every RED and GREEN — the whole loop** |
| refactor-review | smell identification on a large diff | prescribing and applying the refactors |
| devils-advocate | **the whole teardown** — fresh context is the point | ranking the findings |
| tyr-verdict | per-finding verification | **the severity, the slices, the GO/NO-GO** |
| dockerfile | per-service stack inference in a monorepo | writing and verifying the image |
| docker-compose | per-service dependency detection in a monorepo | **the wiring** — it's all relationships between services |
| release-notes | gathering and classifying a large change set | **writing the prose — it must be one voice** |
| post-mortem | gathering and timeline reconstruction, split by source | the factors and the blamelessness pass |

Each skill carries its own copy of the dispatch contract it needs, so the folders stay independently copyable — see [Conventions](#conventions).

## Do they work?

[`evals/`](evals/README.md) holds the harness that measures it — seeded fixtures with planted defects (a rule that ignores its config, and a vacuous test that hides it), scored assertions, and the recorded result in [evals/benchmark.md](evals/benchmark.md).

Assertions are split: **capability** (does the stage do its job at all) from **delta** (does it do what a change to the skill added). Only the delta column is evidence an edit helped. Against the pre-session baseline over 36 runs: **0.98 vs 0.22** on delta, **0.96 vs 0.92** on capability.

**Scored:** the six `development` stages only.

**Fixtures and assertions, not yet run:** `docker-compose` (a service with RQ queues on Redis and a stale `ELASTICSEARCH_URL` for a dependency the code dropped) and `post-mortem` (a git history whose trigger sits nine days before the outage, plus four contradicting documents). Both assertion sets are checked against a naive answer first — a framework-habit compose file scores 6/6 capability and **0/9** delta; the incident report submitted verbatim scores **3/10**. That says the assertions discriminate; it says nothing yet about the skills.

`dockerfile` and `release-notes` have no eval.

## How to use

**There is no installer, and nothing here auto-installs.** Skills are meant to be copied, one at a time, into the repo you're working in.

1. **Clone or browse the repo.**

   ```bash
   git clone https://github.com/izentenosmith/skills.git
   ```

2. **Copy the skill folders you want** into wherever the target repo keeps its agent skills — `.claude/skills/` for Claude Code, `.cursor/skills/` for Cursor, or your user-level skills directory.

   ```bash
   cp -r skills/containers/dockerfile   my-project/.claude/skills/
   cp -r skills/operations/post-mortem  my-project/.claude/skills/
   ```

   **Copy the skill folder, not the category folder.** `development/`, `containers/` and `operations/` are scaffolding for reading this repo — the agent never sees them, and copying one wholesale just nests your skills a level too deep.

   Each skill folder is self-contained: `SKILL.md` plus every reference doc it needs, with no file outside its own directory. That is the point of the layout, and it is what makes copy-paste a complete install.

3. **Invoke a skill** — either let the agent trigger it when your request matches its `description`, or call it explicitly:

   ```
   /architect-deep-dive   /agent-brief      /tdd
   /refactor-review       /devils-advocate  /tyr-verdict
   /dockerfile            /docker-compose
   /release-notes         /post-mortem
   ```

Take one skill, take a family, take all ten. Every skill works on its own — `tdd` plans from scratch when there's no brief, `refactor-review` reviews any diff, `devils-advocate` tears down a change it didn't build, `post-mortem` reconstructs an incident in a system it has never seen. Where skills cross-link and the other one isn't installed, the prompt still names it, so you know what would have run.

Each family has its own README with more detail: [development](development/README.md) · [containers](containers/README.md) · [operations](operations/README.md).

## Conventions

- **One skill per folder, and the folder stands alone.** Each folder contains a `SKILL.md` (the workflow) plus every reference doc it needs. **Copy any one folder into any project and it works** — no shared root docs, no reference doc outside its own folder. The only cross-folder links are the stage list and the handoff, which name the next skill; if it isn't installed, the prompt still tells you which one to run.
- **Families are scaffolding, not structure.** The top-level directories exist to make this repo readable; the agent selects on the frontmatter `description` and never sees a folder name. Nothing installs a family, and no skill depends on its family's path — so families are free to reorganize, and skills are free to cross-link between them.
- **No installer, by design.** Skills are copied into a target repo one folder at a time. An install script implies a managed set that stays in sync; this is a shelf you take things off.
- **Self-containment beats DRY here.** The dispatch contract, the `.workflow/` file rules and the six-stage list are repeated across folders on purpose. That is real duplication with a real cost — change the pipeline's shape and you edit six files — and it buys the thing that matters more: a folder you can paste anywhere.
- **Every `SKILL.md` carries frontmatter** (`name`, `description`) so the agent can decide relevance.
- **Every skill carries a calibration tier and a stopping rule.** The tier says how much of the skill to run before starting; the stopping rule says when to stop, so a workflow with an open-ended quality goal terminates instead of iterating on taste.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let the agent figure out *how* against the live codebase. No hard-coded file paths or line numbers.

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.
