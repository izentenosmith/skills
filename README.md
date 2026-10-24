# Skills

A collection of repo-agnostic AI coding agent skills — taking a feature from a vague idea to reviewed, tested code, packaging it to run, dealing with it once it's live, and grading the database and the network underneath it. Each skill lives in its own folder as a `SKILL.md` file with YAML frontmatter (`name` + `description`) that the agent loads on demand when the work matches.

Works with [Cursor](https://www.cursor.com/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**These skills are created and curated around my own use and needs.** They exist because I wanted them for my own projects and work, and they get updated as those projects and that work require — not on a release schedule and not toward anyone else's workflow. Everything here is MIT licensed and free to take, fork, or rewrite; just know that its shape follows what I actually do, and it will keep changing for the same reason.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## What's in here

Five families of skills under `skills/` — the first three in the order work actually moves through them, the last two for the database and the network underneath — plus a harness that runs the development pipeline's closing loop as code, and the evals that measure the skills.

```
skills/
  development/      build the change      seven stages, design → adversarial close
  containers/       package it to run     dockerfile → docker-compose
  operations/       live with it          hotfix → incident-fix → post-mortem · release-notes
  database/         audit, design, diagram, propose
  networking/       audit, design, diagram, propose, blueprint
harness/            the skills' rules as code: the closing loop, bug → PR, incident → post-mortem, DB and network audit → proposal
evals/              seeded fixtures, scored assertions, the recorded benchmark
```

| Family | Skills |
|---|---|
| **[development/](skills/development/README.md)** | [architect-deep-dive](skills/development/architect-deep-dive/SKILL.md) · [agent-brief](skills/development/agent-brief/SKILL.md) · [tdd](skills/development/tdd/SKILL.md) · [refactor-review](skills/development/refactor-review/SKILL.md) · [devils-advocate](skills/development/devils-advocate/SKILL.md) · [tyr-verdict](skills/development/tyr-verdict/SKILL.md) |
| **[containers/](skills/containers/README.md)** | [dockerfile](skills/containers/dockerfile/SKILL.md) · [docker-compose](skills/containers/docker-compose/SKILL.md) |
| **[operations/](skills/operations/README.md)** | [hotfix](skills/operations/hotfix/SKILL.md) · [incident-fix](skills/operations/incident-fix/SKILL.md) · [post-mortem](skills/operations/post-mortem/SKILL.md) · [release-notes](skills/operations/release-notes/SKILL.md) |
| **[database/](skills/database/README.md)** | [dbaudit](skills/database/dbaudit/SKILL.md) · [dbdesign](skills/database/dbdesign/SKILL.md) · [dbdiagram](skills/database/dbdiagram/SKILL.md) · [dbpropose](skills/database/dbpropose/SKILL.md) · [dbbuild](skills/database/dbbuild/SKILL.md) |
| **[networking/](skills/networking/README.md)** | [netaudit](skills/networking/netaudit/SKILL.md) · [netdesign](skills/networking/netdesign/SKILL.md) · [netdiagram](skills/networking/netdiagram/SKILL.md) · [netpropose](skills/networking/netpropose/SKILL.md) · [netblueprint](skills/networking/netblueprint/SKILL.md) |

The families are loosely coupled by design. `development` is a genuine pipeline where each stage checks the one before it; `containers` is an ordered pair; `operations` is a response chain — hotfix escalates to incident-fix, which hands its record to post-mortem — plus release-notes, which stands alone; `database` and `networking` each have five independent skills coordinated by an optional harness. Every skill also works entirely on its own.

**The family directories are scaffolding for reading this repo, nothing more.** The agent never sees them — it selects on each `SKILL.md`'s frontmatter `description`. When you take a skill, you take the skill folder; see [How to use](#how-to-use).

---

## development — the seven-stage pipeline

Design, specify, write the finish line, build, clean, then an adversarial close.

```
architect-deep-dive → agent-brief → acceptance-tests → tdd → refactor-review → devils-advocate → tyr-verdict
   (resolve design)    (the plan)   (the finish line)  (build)  (clean up)     (assume broken)   (judge + fix loop)
```

The last three stages form a **loop**: if `tyr-verdict` returns NO-GO, its remediation slices feed back into `tdd → refactor-review → devils-advocate → tyr-verdict`, converging when the teardown finds nothing new and the verdict confirms nothing.

The pipeline keeps two files in the repo it's working on — `.workflow/brief.md` (the plan) and `.workflow/ledger.md` (findings, verdicts and carried smells across loop iterations). They're what let a later stage check an earlier stage's work, and what make the loop terminate.

| Stage | `brief.md` | `ledger.md` |
|---|---|---|
| architect-deep-dive | — (its charter feeds stage 2) | — |
| agent-brief | **creates** | — |
| acceptance-tests | reads criteria; **records** the acceptance tests and their command | — |
| tdd | reads; **revises** via the feedback edge; ticks criteria | closes remediation slices |
| refactor-review | reads (scope boundaries) | **re-rates** prior noted smells; appends new ones |
| devils-advocate | reads (criteria, edge cases, deferrals) | **appends findings** |
| tyr-verdict | reads | **appends verdicts and slices**; reads noted smells into the verdict |

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](skills/development/architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time — options with trade-offs, a recommendation and its reversal cost — against a stated charter and a live question count. Infers answers from the codebase where it can. Run this first. |
| [agent-brief](skills/development/agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. |
| [acceptance-tests](skills/development/acceptance-tests/SKILL.md) | Turns the brief's acceptance criteria into executable black-box tests through the outermost boundary — written before any code, each red for the right reason — and maps every criterion to its test. tdd is done when they pass. |
| [tdd](skills/development/tdd/SKILL.md) | Test-driven development via the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to refactor-review. |
| [refactor-review](skills/development/refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |
| [devils-advocate](skills/development/devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. |
| [tyr-verdict](skills/development/tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |

### How much pipeline does this change need?

Seven stages on a two-line fix cost more than the fix. Pick a tier **once, up front**, and say which you picked:

| Tier | The change | Run |
|------|-----------|-----|
| **Trivial** | A localized fix behind an existing seam. No new behavior surface, no new boundary. | `tdd → refactor-review` (4–5) |
| **Standard** | A new capability inside existing structure. | `agent-brief → … → tyr-verdict` (2–7); add stage 1 if the design isn't already obvious |
| **Large / risky** | New subsystem, a change that crosses existing boundaries, or one touching data migration, money, permissions, or tenancy. | All seven — and stage 1's decomposition splits it into increments that each run 2–7 |

Two rules that make the tiering honest:

- **Calibrate once, not stage by stage.** Deciding to skip a stage *while you're standing in front of it* is how the discipline erodes everywhere, because the stage you skip is always the one that looked unnecessary.
- **Stages 6–7 don't get dropped** on anything touching data, money, permissions, or tenancy — regardless of how small the diff is. Those are the failures a green suite is worst at catching, and a two-line diff is perfectly capable of causing one.

Stage numbers throughout the skills refer to position in the full pipeline, not to a requirement that all seven run.

### Running the closing loop as code

The loop's rules — read-only teardown, one verifier per finding, sticky refutations, one evidence re-run per INCONCLUSIVE, three iterations, a verdict that follows from what's open — are prose in the skills, which means the agent is both worker and referee. **[harness/](harness/README.md)** moves the referee into a program: `loop.py` drives refactor-review → devils-advocate → tyr-verdict (and tdd on NO-GO) through headless `claude -p` calls, enforces each rule in code, and keeps the ledger as an append-only log in a [strict grammar](harness/LEDGER.md) it can replay and resume from. `ledger.py` checks any ledger, including one the skills wrote by hand.

```bash
python3 harness/loop.py --repo ../my-service --test-cmd ".venv/bin/python -m pytest -q"
```

The same folder holds three more: `fix.py` takes a bug report to a draft PR (the hotfix lane, or incident-fix's fix phase), `postmortem.py` turns a resolved incident log into a linted post-mortem with an owned follow-through, and the database and network workflow harnesses coordinate audit, design, diagram, and proposal stages. It's optional and Claude Code only; the skills don't depend on it.

---

## containers

Ordered: an image, then the stack around it.

```
dockerfile → docker-compose
 (the image)  (the stack)
```

| Skill | What it does |
|-------|--------------|
| [dockerfile](skills/containers/dockerfile/SKILL.md) | Reads the stack off the repo, writes a multi-stage production Dockerfile — pinned base, non-root runtime, cache-correct layer order — and generates or repairs the `.dockerignore` that defines its build context. Verifies by building and running, not by reading. |
| [docker-compose](skills/containers/docker-compose/SKILL.md) | Detects the services the code actually connects to, wires them with named volumes, an isolated network and real health gates, and ships a documented `.env.example` plus a dev override. Verifies from cold, twice. |

**Run `dockerfile` first.** Compose orchestrates images; it cannot repair one. Most "compose is broken" reports are an image that doesn't start, doesn't answer its healthcheck, or dies on `SIGTERM`.

---

## operations

What happens around a system that's already running: fixing it when it breaks, recording what happened, and telling people what changed.

```
hotfix ──escalates──► incident-fix ──hands its log to──► post-mortem      release-notes
 (urgent, not down)    (contain → diagnose → fix → learn)  (the record)     (stands alone)
```

| Skill | What it does |
|-------|--------------|
| [hotfix](skills/operations/hotfix/SKILL.md) | A fast lane for an urgent bug in a system that is **up**: discovers the repo's own commands and conventions, routes outages and design questions out, proves the bug red, fixes it once at the shared cause, runs one adversarial pass (strict on data, money, permissions and tenancy), and ships with recorded evidence. |
| [incident-fix](skills/operations/incident-fix/SKILL.md) | Production incidents end to end: contain first with ranked, reversible levers, diagnose read-only and size the impact with a reproducible count, fix through the review pipeline capped at two loops with data repair as its own artifact, then post-mortem and **follow-through** — every factor owned or explicitly accepted. Every production action waits for confirmation. |
| [release-notes](skills/operations/release-notes/SKILL.md) | Reads the change set from git, classifies every change (including an explicit **drop** bucket for anything with no user-visible effect), and translates each survivor from what was built into what the reader can now do. Depth matched to scope; breaking changes above the fold. |
| [post-mortem](skills/operations/post-mortem/SKILL.md) | Reconstructs a **resolved** incident into a blameless written record — timeline built from a git history date range plus incident docs and PDFs, quantified impact, and **contributing factors** rather than a single root cause. Ends with a pass over the prose hunting the blame that leaks in through grammar. |

`hotfix` and `incident-fix` discover everything environment-specific at runtime — build and test commands as CI runs them, the merge convention, the tracker, rollback levers, observability — and cache it in `.workflow/env.md`, which both read. Neither hardcodes a stack, a CI product, a cloud or a ticket system.

`post-mortem` **documents; it does not prescribe.** The incident is already solved, so the skill reconstructs what happened and stops there — no remediation plan, no recommendations, no handoff into the build pipeline. That boundary is what keeps the record trustworthy: a document that reconstructs *and* prescribes has an incentive to shape the reconstruction toward the prescription. What to change next is a decision for whoever owns the system. Inside the response chain that decision is incident-fix's **follow-through** step — written after the record, as a separate artifact, so the record stays descriptive.

It needs inputs you supply: a **date range for the git history** and whatever **incident documentation** exists — the report, a vendor PDF, a chat export, alert emails. It reconstructs from artifacts, not from a description of the incident.

---

## database

Five independent skills, coordinated by [`harness/dbworkflow.py`](harness/dbworkflow.py) when the user wants a full or partial workflow.

```
Existing database: dbaudit → dbdesign → dbdiagram (Barker ER + relational) → dbpropose
New database:                 dbdesign → dbdiagram (Barker ER + relational) → dbpropose
Accepted proposal:                                       dbbuild
```

| Skill | What it does |
|-------|--------------|
| [dbaudit](skills/database/dbaudit/SKILL.md) | Audits existing databases with a repeatable score and evidence-backed strengths, weaknesses, and improvement opportunities. |
| [dbdesign](skills/database/dbdesign/SKILL.md) | Designs a new database or revises an audited design using relational theory, Codd's rules, normal forms, and physical-design guidance. |
| [dbdiagram](skills/database/dbdiagram/SKILL.md) | Produces editable draw.io ER and relational model diagrams from a design or database structure. |
| [dbpropose](skills/database/dbpropose/SKILL.md) | Assembles the recommendation from available audit, design, and diagram artifacts. |
| [dbbuild](skills/database/dbbuild/SKILL.md) | Generates reviewable DDL from an explicitly accepted proposal and its design. |

**The audit doesn't prescribe; design owns the model; proposal assembles the recommendation; dbbuild generates DDL only after proposal acceptance.** Conceptual ER diagrams use Barker notation throughout; relational diagrams keep table/key notation. The harness checks the required Barker page name/legend and diagram pair. The harness applies the 9.0 score threshold plus Critical/High, unused/copy, and unresolved needs-data ratio conditions. Structural iterations return through design, diagrams, and proposal before a revised proposal can be accepted for DDL generation. Skills remain independently usable outside the harness.

---

## networking

Five independent skills, coordinated by [`harness/networkflow.py`](harness/networkflow.py) when the user wants a full or partial workflow.

```
Existing network: netaudit → netdesign → netdiagram (L3 + zones/flows [+ L1/L2]) → netpropose
New network:                 netdesign → netdiagram (L3 + zones/flows [+ L1/L2]) → netpropose
Accepted proposal:                                                    netblueprint
```

| Skill | What it does |
|-------|--------------|
| [netaudit](skills/networking/netaudit/SKILL.md) | Audits existing networks — IaC, device configs, k8s/compose networking, IP plans — recovering a `topology.json`, with a repeatable score and evidence-backed findings. |
| [netdesign](skills/networking/netdesign/SKILL.md) | Designs a new network or revises an audited one: zones and flows, addressing plan, routing, services, failure domains. |
| [netdiagram](skills/networking/netdiagram/SKILL.md) | Produces the canonical editable draw.io views — logical L3, segmentation, and physical L1/L2 when on-prem. |
| [netpropose](skills/networking/netpropose/SKILL.md) | Assembles the recommendation, with cut-over sequencing, validation and rollback. |
| [netblueprint](skills/networking/netblueprint/SKILL.md) | After acceptance, produces the final diagrams, a companion `network-design.md`, and the accepted `topology.json` for a separate IaC skill. Writes no IaC. |

**Two lenses carry the theory:** computer networking (Kurose & Ross; Tanenbaum & Wetherall) and network science (Newman; Barabási) — articulation points, Menger connectivity, betweenness and percolation make "single point of failure" and "blast radius" computable. The harness redacts secrets before any model reads evidence, computes the graph metrics and address/flow checks in code (`netgraph.py`), scores by the database family's formula, and gates on score, open Critical/High findings, critical-pair connectivity ≥ 2, the 🔬 ratio, and usage. Blueprints need an explicitly accepted proposal, in a separate run.

---

## Reference docs

These carry no workflow of their own — the skill in the same folder links into them.

| Doc | Used by |
|-----|---------|
| [clean-architecture](skills/development/architect-deep-dive/clean-architecture.md) | architect-deep-dive — dependency direction, policy vs. detail, boundary placement (Martin) |
| [code-smells](skills/development/refactor-review/code-smells.md) | refactor-review — the symptom catalog (Refactoring Guru / Fowler) |
| [refactoring-techniques](skills/development/refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [comments](skills/development/refactor-review/comments.md) | refactor-review — which comments earn their place (tdd carries the ladder inline) |
| [good-tests](skills/development/tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](skills/development/tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](skills/development/tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](skills/development/tdd/interface-design.md) | tdd — designing for testability |
| [optimization](skills/containers/dockerfile/optimization.md) | dockerfile — base image trade-offs, layer order, cache mounts, secrets, signals |
| [dockerignore](skills/containers/dockerfile/dockerignore.md) | dockerfile — what to exclude and what each exclusion buys |
| [service-catalog](skills/containers/docker-compose/service-catalog.md) | docker-compose — per-service image, readiness probe, volume path, connection string |
| [environments](skills/containers/docker-compose/environments.md) | docker-compose — overrides, merge rules, `.env.example`, secrets |
| [anatomy](skills/operations/release-notes/anatomy.md) | release-notes — the six elements and the commit→outcome translation rules |
| [distribution](skills/operations/release-notes/distribution.md) | release-notes — depth to scope, when visuals earn their place, where to publish |
| [blameless-culture](skills/operations/post-mortem/blameless-culture.md) | post-mortem — why blameless is a data-collection strategy (Google SRE; Dekker) |
| [contributing-factors](skills/operations/post-mortem/contributing-factors.md) | post-mortem — past single-root-cause; the categories to sweep and where to stop |
| [evidence-sources](skills/operations/post-mortem/evidence-sources.md) | post-mortem — reading a git range, incident PDFs, chat exports and monitoring into a sourced timeline |
| [theory](skills/database/dbaudit/theory.md) | dbaudit and dbdesign — relational principles including Codd's rules, FDs, normal forms, ACID, SSOT |
| [er-modeling](skills/database/dbaudit/er-modeling.md) | dbaudit and dbdesign; copied in dbdiagram — CAP1–CAP4 pure modelling, reverse-engineering, 25 drills |
| [scoring](skills/database/dbaudit/scoring.md) | dbaudit — severity, confidence tags, the 0–10 formula, triage, output templates |
| [audit-lenses](skills/database/dbaudit/audit-lenses.md) | dbaudit — dead/copy schemas, coupling, dark data, security |
| [tables](skills/database/dbaudit/tables.md) · [indexes](skills/database/dbaudit/indexes.md) · [views](skills/database/dbaudit/views.md) · [procedures](skills/database/dbaudit/procedures.md) · [triggers](skills/database/dbaudit/triggers.md) | dbaudit — the per-object-type rubrics |
| [detection-signals](skills/database/dbaudit/detection-signals.md) | dbaudit — grep/regex per anti-pattern, with engine notes |
| [proposal](skills/database/dbpropose/proposal.md) | dbpropose — input contract, verdicts, topology, translation, target-schema and remediation skeletons |
| [physical-design](skills/database/dbdesign/physical-design.md) | dbdesign — the PostgreSQL 18 physical standard |
| [theory](skills/networking/netaudit/theory.md) | netaudit, netdesign, netpropose, netblueprint — networking principles §1–§16 (Kurose & Ross; Tanenbaum & Wetherall) |
| [graph-theory](skills/networking/netaudit/graph-theory.md) | netaudit, netdesign, netpropose, netblueprint — the network-science lens G1–G12 (Newman; Barabási) |
| [topology-modeling](skills/networking/netaudit/topology-modeling.md) | all five network skills — the `topology.json` contract, reverse-engineering, drills |
| [scoring](skills/networking/netaudit/scoring.md) · [audit-lenses](skills/networking/netaudit/audit-lenses.md) · [detection-signals](skills/networking/netaudit/detection-signals.md) | netaudit — severity, confidence, formula, gate; cross-cutting lenses; grep per anti-pattern with platform notes |
| [addressing](skills/networking/netaudit/addressing.md) · [segmentation](skills/networking/netaudit/segmentation.md) · [routing](skills/networking/netaudit/routing.md) · [services](skills/networking/netaudit/services.md) · [resilience](skills/networking/netaudit/resilience.md) · [security](skills/networking/netaudit/security.md) | netaudit — the per-domain rubrics |
| [design-patterns](skills/networking/netdesign/design-patterns.md) | netdesign, netpropose — topology patterns, the addressing method, segmentation, routing, failure domains |
| [diagram-conventions](skills/networking/netdiagram/diagram-conventions.md) | netdiagram, netpropose, netblueprint — the canonical views, glyphs, IDs, validation |
| [proposal](skills/networking/netpropose/proposal.md) | netpropose — decisions by score band, cut-over sequencing |
| [blueprint](skills/networking/netblueprint/blueprint.md) | netblueprint — package layout, the IaC handoff contract, the `network-design.md` template |

Each doc lives in the folder of the skill that uses it, and nothing reaches across folders.

## Delegation

Any stage can optionally hand its **read-only or fresh-context** work to a subagent. Delegation is most valuable at the ends of a pipeline — evidence-gathering before a design decision, and before a verdict — and least valuable in the middle, where the work is a sequential loop that learns from itself.

| Skill | Delegate | Keep in the main thread |
|-------|----------|-------------------------|
| architect-deep-dive | codebase inference behind **[inferred]** answers | the question-by-question dialogue |
| agent-brief | the prior-art hunt | writing and ordering the plan |
| acceptance-tests | finding the outermost boundary and existing acceptance suites | **writing the tests, one criterion at a time** |
| tdd | convention lookups only | **every RED and GREEN — the whole loop** |
| refactor-review | smell identification on a large diff | prescribing and applying the refactors |
| devils-advocate | **the whole teardown** — fresh context is the point | ranking the findings |
| tyr-verdict | per-finding verification | **the severity, the slices, the GO/NO-GO** |
| dockerfile | per-service stack inference in a monorepo | writing and verifying the image |
| docker-compose | per-service dependency detection in a monorepo | **the wiring** — it's all relationships between services |
| release-notes | gathering and classifying a large change set | **writing the prose — it must be one voice** |
| hotfix | the caller sweep; convention lookups | **the red→green and the fix** |
| incident-fix | evidence gathering in diagnosis, one delegate per source | **containment, every production action, and the fix decisions** |
| post-mortem | gathering and timeline reconstruction, split by source | the factors and the blamelessness pass |
| dbaudit | per-database evaluation of each DDL file | **scoring and the synthesis** |
| dbdesign | requirements mapping and model review | **the modeling decisions and target structure** |
| dbdiagram | source-backed ER and relational views | **diagram semantics and layout** |
| dbpropose | audit/design/diagram inputs | **the recommendation and prioritization** |
| netaudit | per-network evidence reading and topology recovery | **scoring, the graph metrics, and the synthesis** |
| netdesign | requirements and inventory mapping | **zones, addressing, routing and redundancy decisions** |
| netdiagram | per-view drafting from the model | **view semantics and layout** |
| netpropose | audit/design/diagram inputs | **the recommendation and cut-over order** |

Each skill carries its own copy of the dispatch contract it needs, so the folders stay independently copyable — see [Conventions](#conventions).

## Do they work?

[`evals/`](evals/README.md) holds the harness that measures it — seeded fixtures with planted defects (a rule that ignores its config, and a vacuous test that hides it), scored assertions, and the recorded result in [evals/benchmark.md](evals/benchmark.md).

Assertions are split: **capability** (does the stage do its job at all) from **delta** (does it do what a change to the skill added). Only the delta column is evidence an edit helped. Against the pre-session baseline over 36 runs: **0.98 vs 0.22** on delta, **0.96 vs 0.92** on capability.

**Scored:** the six `development` stages only.

**Fixtures and assertions, not yet run:** `docker-compose` (a service with RQ queues on Redis and a stale `ELASTICSEARCH_URL` for a dependency the code dropped) and `post-mortem` (a git history whose trigger sits nine days before the outage, plus four contradicting documents). Both assertion sets are checked against a naive answer first — a framework-habit compose file scores 6/6 capability and **0/9** delta; the incident report submitted verbatim scores **3/10**. That says the assertions discriminate; it says nothing yet about the skills.

**Also not yet run:** `hotfix` (evals 8–11 — a Node service, a JVM service with no build tool, a Python script with no tests, and an outage it must route out) and `incident-fix` (evals 12–14 — a web app with feature flags, a batch job that corrupted rows, a library with no deploy step). Every production lever in those fixtures is a stub that records its calls, so "took no action without confirmation" is checked, not inferred.

`acceptance-tests`, `dockerfile`, `release-notes`, the five database skills and the five networking skills have no eval.

## How to use

### Install with `npx`

Every skill installs by name through the [`skills` CLI](https://github.com/vercel-labs/skills) — nothing to clone. The CLI finds each `SKILL.md` in this repo by its frontmatter `name`, so commands name skills, never family folders. Run them from the root of the repo you want the skills in.

**A whole workflow** — one command per family:

```bash
# development — the seven-stage pipeline
npx skills add izentenosmith/skills --skill architect-deep-dive agent-brief acceptance-tests tdd refactor-review devils-advocate tyr-verdict

# containers — image, then stack
npx skills add izentenosmith/skills --skill dockerfile docker-compose

# operations — the response chain plus release-notes
npx skills add izentenosmith/skills --skill hotfix incident-fix post-mortem release-notes

# database — audit, design, diagram, propose, build
npx skills add izentenosmith/skills --skill dbaudit dbdesign dbdiagram dbpropose dbbuild

# networking — audit, design, diagram, propose, blueprint
npx skills add izentenosmith/skills --skill netaudit netdesign netdiagram netpropose netblueprint
```

**Everything:**

```bash
npx skills add izentenosmith/skills --skill '*'
```

**One skill:**

| Family | Command |
|---|---|
| development | `npx skills add izentenosmith/skills --skill architect-deep-dive` |
| | `npx skills add izentenosmith/skills --skill agent-brief` |
| | `npx skills add izentenosmith/skills --skill acceptance-tests` |
| | `npx skills add izentenosmith/skills --skill tdd` |
| | `npx skills add izentenosmith/skills --skill refactor-review` |
| | `npx skills add izentenosmith/skills --skill devils-advocate` |
| | `npx skills add izentenosmith/skills --skill tyr-verdict` |
| containers | `npx skills add izentenosmith/skills --skill dockerfile` |
| | `npx skills add izentenosmith/skills --skill docker-compose` |
| operations | `npx skills add izentenosmith/skills --skill hotfix` |
| | `npx skills add izentenosmith/skills --skill incident-fix` |
| | `npx skills add izentenosmith/skills --skill post-mortem` |
| | `npx skills add izentenosmith/skills --skill release-notes` |
| database | `npx skills add izentenosmith/skills --skill dbaudit` |
| | `npx skills add izentenosmith/skills --skill dbdesign` |
| | `npx skills add izentenosmith/skills --skill dbdiagram` |
| | `npx skills add izentenosmith/skills --skill dbpropose` |
| | `npx skills add izentenosmith/skills --skill dbbuild` |
| networking | `npx skills add izentenosmith/skills --skill netaudit` |
| | `npx skills add izentenosmith/skills --skill netdesign` |
| | `npx skills add izentenosmith/skills --skill netdiagram` |
| | `npx skills add izentenosmith/skills --skill netpropose` |
| | `npx skills add izentenosmith/skills --skill netblueprint` |

Any mix works too — `--skill` takes as many names as you give it.

Useful flags:

| Flag | Effect |
|---|---|
| `-a claude-code` · `-a cursor` | Install for that agent only, instead of being asked. Takes several: `-a claude-code cursor`. |
| `-g` | Install at user level (every project) instead of into the current repo. |
| `-y` | Skip the confirmation prompts. |
| `--list` | Show every skill in this repo without installing. |

`npx skills update` pulls newer versions of what you installed; `npx skills remove <name>` takes one out.

The installer copies each skill folder whole, dereferencing the database and networking skills' shared-doc symlinks, so every installed folder is self-contained. **It installs skills, not the [harness](harness/README.md)** — the Python orchestration in `harness/` (including `dbworkflow.py` and `networkflow.py`) needs a clone.

### Or copy by hand

1. **Clone or browse the repo.**

   ```bash
   git clone https://github.com/izentenosmith/skills.git
   ```

2. **Copy the skill folders you want** into wherever the target repo keeps its agent skills — `.claude/skills/` for Claude Code, `.cursor/skills/` for Cursor, or your user-level skills directory.

   ```bash
   cp -r skills/skills/containers/dockerfile   my-project/.claude/skills/
   cp -r skills/skills/operations/post-mortem  my-project/.claude/skills/
   cp -RL skills/skills/database/dbaudit        my-project/.claude/skills/
   cp -RL skills/skills/database/dbdesign       my-project/.claude/skills/
   cp -RL skills/skills/database/dbdiagram      my-project/.claude/skills/
   cp -RL skills/skills/database/dbpropose      my-project/.claude/skills/
   cp -RL skills/skills/database/dbbuild        my-project/.claude/skills/
   cp -RL skills/skills/networking/netaudit     my-project/.claude/skills/
   cp -RL skills/skills/networking/netdesign    my-project/.claude/skills/
   cp -RL skills/skills/networking/netdiagram   my-project/.claude/skills/
   cp -RL skills/skills/networking/netpropose   my-project/.claude/skills/
   cp -RL skills/skills/networking/netblueprint my-project/.claude/skills/
   ```

   **Copy the skill folder, not the category folder.** `development/`, `containers/`, `operations/`, `database/` and `networking/` are scaffolding for reading this repo — the agent never sees them, and copying one wholesale just nests your skills a level too deep.

   Skill folders are self-contained when installed. The database and networking skill trees share companion docs through relative symlinks; use `cp -RL` for those folders so each installed skill contains the referenced files.

3. **Invoke a skill** — either let the agent trigger it when your request matches its `description`, or call it explicitly:

   ```
   /architect-deep-dive   /agent-brief      /acceptance-tests
   /tdd                   /refactor-review  /devils-advocate  /tyr-verdict
   /dockerfile            /docker-compose
   /hotfix                /incident-fix
   /release-notes         /post-mortem
   /dbaudit       /dbdesign       /dbdiagram       /dbpropose       /dbbuild
   /netaudit      /netdesign      /netdiagram      /netpropose      /netblueprint
   ```

Take one skill, take a family, or take them all. Every skill works on its own — `tdd` plans from scratch when there's no brief, `refactor-review` reviews any diff, `devils-advocate` tears down a change it didn't build, `post-mortem` reconstructs an incident in a system it has never seen. Where skills cross-link and the other one isn't installed, the prompt still names it, so you know what would have run.

Each family has its own README with more detail: [development](skills/development/README.md) · [containers](skills/containers/README.md) · [operations](skills/operations/README.md) · [database](skills/database/README.md) · [networking](skills/networking/README.md).

## Conventions

- **One skill per folder, and the folder stands alone.** Each folder contains a `SKILL.md` (the workflow) plus every reference doc it needs. **Copy any one folder into any project and it works** — no shared root docs, no reference doc outside its own folder. The only cross-folder links are the stage list and the handoff, which name the next skill; if it isn't installed, the prompt still tells you which one to run.
- **Families are scaffolding, not structure.** The family directories under `skills/` exist to make this repo readable; the agent selects on the frontmatter `description` and never sees a folder name. A family install is just a list of skill names, and no skill depends on its family's path — so families are free to reorganize, and skills are free to cross-link between them.
- **The harness is a layer, not a dependency.** `harness/` enforces the development pipeline's rules when you run it, and nothing in a skill folder refers to it. Its ledger grammar is the same one the skills write by hand — so a skill folder copied alone still produces a ledger the harness can check and resume.
- **No installer of its own.** Skills go into a target repo one folder at a time — by name through the external `skills` CLI, or by copying. A family command is a list of names, not a managed set that stays in sync; this is still a shelf you take things off.
- **Self-containment beats DRY here.** The dispatch contract, the `.workflow/` file rules and the seven-stage list are repeated across folders on purpose. That is real duplication with a real cost — change the pipeline's shape and you edit six files — and it buys the thing that matters more: a folder you can paste anywhere.
- **Every `SKILL.md` carries frontmatter** (`name`, `description`) so the agent can decide relevance.
- **Every skill carries a calibration tier and a stopping rule.** The tier says how much of the skill to run before starting; the stopping rule says when to stop, so a workflow with an open-ended quality goal terminates instead of iterating on taste.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let the agent figure out *how* against the live codebase. No hard-coded file paths or line numbers.

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.
