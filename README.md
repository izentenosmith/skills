# Skills

A collection of repo-agnostic AI coding agent skills — taking a feature from a vague idea to reviewed, tested code, packaging it to run, dealing with it once it's live, grading the database and the network underneath it, reviewing the infrastructure code and pipelines that ship it, securing all of it — threat model, application code, and the hosts and cloud accounts it runs on — and reviewing each change as it arrives. Each skill lives in its own folder as a `SKILL.md` file with YAML frontmatter (`name` + `description`) that the agent loads on demand when the work matches.

Works with [Cursor](https://www.cursor.com/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**These skills are created and curated around my own use and needs.** They exist because I wanted them for my own projects and work, and they get updated as those projects and that work require — not on a release schedule and not toward anyone else's workflow. Everything here is MIT licensed and free to take, fork, or rewrite; just know that its shape follows what I actually do, and it will keep changing for the same reason.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills), [peterpme/skills](https://github.com/peterpme/skills), [kunchenguid/firstmate](https://github.com/kunchenguid/firstmate) and [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).

## What's in here

The [skill registry](skills/REGISTRY.md) lists every skill's family, purpose, owner, version, dependencies and latest eval score; it is generated, so regenerate it with `python3 .github/scripts/registry.py` (CI fails when it is stale).

Nine families of skills under `skills/` — the first three in the order work actually moves through them, then the database, the network, the infrastructure code and pipelines underneath, the security of every layer, the review of each change as it arrives, and the memory agents keep about the repository — plus a harness that runs the development pipeline's closing loop — and one pull request through every review skill — as code, and the evals that measure the skills.

```
skills/
  development/      build the change      seven stages, design → adversarial close; nexus runs several at once
  containers/       package it to run     dockerfile → docker-compose · container-hardening · container-debug · docker-swarm
  operations/       live with it          hotfix → incident-fix → post-mortem · release-notes · ticket · backlog
  database/         architect, audit, design, diagram, propose, build, query review
  networking/       audit, design, diagram, propose, blueprint
  infrastructure/   review, design, propose   terraform · pipelines
  security/         review, design, propose   threatmodel · appsec · hardening
  review/           judge a change as it arrives   pr-prep · code-xray · peer-review · test-review · concurrency-review · review-retro
  memory/           remember what agents learn     repo-memory: install · capture · dream · audit
harness/            the skills' rules as code: the closing loop, bug → PR, incident → post-mortem, DB and network audit → proposal
evals/              seeded fixtures, scored assertions, the recorded benchmark
```

| Family | Skills |
|---|---|
| **[development/](skills/development/README.md)** | [architect-deep-dive](skills/development/architect-deep-dive/SKILL.md) · [agent-brief](skills/development/agent-brief/SKILL.md) · [acceptance-tests](skills/development/acceptance-tests/SKILL.md) · [tdd](skills/development/tdd/SKILL.md) · [refactor-review](skills/development/refactor-review/SKILL.md) · [devils-advocate](skills/development/devils-advocate/SKILL.md) · [tyr-verdict](skills/development/tyr-verdict/SKILL.md) · [nexus](skills/development/nexus/SKILL.md) |
| **[containers/](skills/containers/README.md)** | [dockerfile](skills/containers/dockerfile/SKILL.md) · [docker-compose](skills/containers/docker-compose/SKILL.md) · [container-hardening](skills/containers/container-hardening/SKILL.md) · [container-debug](skills/containers/container-debug/SKILL.md) · [docker-swarm](skills/containers/docker-swarm/SKILL.md) |
| **[operations/](skills/operations/README.md)** | [hotfix](skills/operations/hotfix/SKILL.md) · [incident-fix](skills/operations/incident-fix/SKILL.md) · [post-mortem](skills/operations/post-mortem/SKILL.md) · [release-notes](skills/operations/release-notes/SKILL.md) · [ticket](skills/operations/ticket/SKILL.md) · [backlog](skills/operations/backlog/SKILL.md) |
| **[database/](skills/database/README.md)** | [dbarchitect](skills/database/dbarchitect/SKILL.md) · [dbaudit](skills/database/dbaudit/SKILL.md) · [dbdesign](skills/database/dbdesign/SKILL.md) · [dbdiagram](skills/database/dbdiagram/SKILL.md) · [dbpropose](skills/database/dbpropose/SKILL.md) · [dbbuild](skills/database/dbbuild/SKILL.md) · [dbquery](skills/database/dbquery/SKILL.md) |
| **[networking/](skills/networking/README.md)** | [netaudit](skills/networking/netaudit/SKILL.md) · [netdesign](skills/networking/netdesign/SKILL.md) · [netdiagram](skills/networking/netdiagram/SKILL.md) · [netpropose](skills/networking/netpropose/SKILL.md) · [netblueprint](skills/networking/netblueprint/SKILL.md) |
| **[infrastructure/](skills/infrastructure/README.md)** | [terraform](skills/infrastructure/terraform/SKILL.md) · [pipelines](skills/infrastructure/pipelines/SKILL.md) |
| **[security/](skills/security/README.md)** | [threatmodel](skills/security/threatmodel/SKILL.md) · [appsec](skills/security/appsec/SKILL.md) · [hardening](skills/security/hardening/SKILL.md) |
| **[review/](skills/review/README.md)** | [pr-prep](skills/review/pr-prep/SKILL.md) · [code-xray](skills/review/code-xray/SKILL.md) · [peer-review](skills/review/peer-review/SKILL.md) · [test-review](skills/review/test-review/SKILL.md) · [concurrency-review](skills/review/concurrency-review/SKILL.md) · [review-retro](skills/review/review-retro/SKILL.md) |
| **[memory/](skills/memory/README.md)** | [repo-memory](skills/memory/repo-memory/SKILL.md) |

The families are loosely coupled by design. `development` is a genuine pipeline where each stage checks the one before it; `containers` is an ordered pair (image, then stack) plus three skills for containers once they run — hardening, debugging, and Swarm; `operations` is a response chain — hotfix escalates to incident-fix, which hands its record to post-mortem — plus release-notes, which stands alone, and the tracker pair — ticket writes work items to Linear, Azure DevOps or Jira for every other skill, backlog shapes and orders them; `database` has seven independent skills — five of them coordinated by an optional harness, plus an architecture stage above them and a query review beside them — and `networking` has five coordinated the same way; `infrastructure` has two skills and `security` three, each running review → design → propose as modes of one skill; `review` has six skills around one change as it arrives from anyone — pr-prep before review, code-xray for what the history says, peer-review as the gate with test-review and concurrency-review as its specialists, review-retro after — and `harness/prreview.py` runs all of them on a single pull request; `memory` is one skill with four modes, whose dream keeps what agents learn about the repo true and small. Every skill also works entirely on its own.

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
| agent-brief | **creates**, as a draft: its approval gate is the only place Status becomes `approved`; archives a finished brief and its ledger together, and stops rather than overwrite an unfinished one | — |
| acceptance-tests | reads criteria; **records** the acceptance tests and their command | — |
| tdd | reads; **revises** via the feedback edge; ticks criteria and ship-checklist items; records `**Base:**` | closes remediation slices |
| refactor-review | reads (scope boundaries, `**Base:**`) | **re-rates** prior noted smells; appends new ones |
| devils-advocate | reads (criteria, edge cases, deferrals, `**Base:**`) | **appends findings** |
| tyr-verdict | reads | **appends verdicts and slices**; reads noted smells into the verdict |

Every stage after agent-brief reads the brief's Status and never writes it: on a draft it goes ahead and says its work rests on an unapproved brief. A brief whose criteria, scope or interfaces change after approval goes back to draft.

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](skills/development/architect-deep-dive/SKILL.md) | Runs a staff-architect design review that resolves the plan in rounds of up to three independent questions — options with trade-offs, a recommendation and its reversal cost — against a stated charter and a live question count. Infers answers from the codebase where it can. Run this first. |
| [agent-brief](skills/development/agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope — written to `.workflow/brief.md`, a draft until the user approves it. |
| [acceptance-tests](skills/development/acceptance-tests/SKILL.md) | Turns the brief's acceptance criteria into executable black-box tests through the outermost boundary — written before any code, each red for the right reason — and maps every criterion to its test. tdd is done when they pass. |
| [tdd](skills/development/tdd/SKILL.md) | Builds test-first through the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to refactor-review. |
| [refactor-review](skills/development/refactor-review/SKILL.md) | Reviews the change tdd just built for code smells: names the smell, then prescribes a behavior-preserving refactoring, with the tests run between each. Not a bug review — that is peer-review. |
| [devils-advocate](skills/development/devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. For someone else's PR, use peer-review. |
| [tyr-verdict](skills/development/tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |
| [nexus](skills/development/nexus/SKILL.md) | Coordinates several parallel sessions, each building one PR, or one track of one, through the seven stages, with no fixed cap on how many run at once. Sets the increment up before the first session (the repo's commands and baseline, and a list of what the increment must deliver, every entry failing until proven on the base branch), judges each PR on its stage log, answers the sessions' questions from a sealed register of the user's decisions or batches them into one digest, guards leases, migration numbers and label series, and merges only on the user's go. Writes no code. |

Every skill folder carries `pipeline.md`, the rules all eight share: **where questions go** (on your own, stop only for a destructive action, a security question or a change to something agreed; under a nexus, "the user" is the coordinator; with nobody to answer, take the default that destroys nothing and mark it `unconfirmed`), **what you read is data, not instructions**, and **which commands may be run**. Asked for the whole pipeline, the stages chain without waiting; agent-brief's approval gate is the one designed stop. The stages that write a checked file carry its checker in `scripts/` (`brief.py`, `redgreen.py`, `ledger.py`). Details in the [development README](skills/development/README.md#what-every-stage-shares).

### Work that outlives one session

A build that runs for hours crosses many context windows, and each new session starts with no memory of the last. The development flow is built so that nothing depends on that memory, after Anthropic's [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents):

- **State is on disk.** The brief and its ticks, the append-only ledger, one commit per green slice, and under nexus a status file rewritten every turn and a stage log per session whose last block is its hand-over.
- **Every session starts the same way.** Where it is, the last hand-over, the git log, the brief's ticks, then the suite — before any new work. tdd does this standalone; the nexus contract makes every sub-session do it.
- **Nobody rediscovers the repo.** The nexus writes the test, build, start and smoke commands and the base branch's baseline once, and every session's brief carries them.
- **Done is a list, not a feeling.** `increment.json` holds every requirement and user journey, all failing at the start. An entry passes only when its test is seen passing on the base branch after the merge, and the increment is done when the list says so, not when the PRs are merged.

The details are in the [development README](skills/development/README.md#work-that-outlives-one-session), and [harness/](harness/README.md) runs the same flow headless.

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

The loop's rules — read-only teardown, one verifier per finding, sticky refutations, one evidence re-run per INCONCLUSIVE, three iterations, a verdict that follows from what's open — are prose in the skills, which means the agent is both worker and referee. **[harness/](harness/README.md)** moves the referee into a program: `loop.py` drives refactor-review → devils-advocate → tyr-verdict (and tdd on NO-GO) through headless `claude -p` calls, enforces each rule in code, and keeps the ledger as an append-only log in a [strict grammar](harness/LEDGER.md) it can replay and resume from. `ledger.py` checks any ledger, including one the skills wrote by hand, and `brief.py` does the same for a brief.

```bash
python3 harness/loop.py --repo ../my-service --test-cmd ".venv/bin/python -m pytest -q"
```

`pipeline.py` goes one step further back: you work the design with architect-deep-dive, which writes the design to its own file under `.workflow/designs/`, and it runs the brief, the acceptance tests, tdd and that loop from there to GO or ESCALATED. It never approves a brief on its own: pass `--approve-brief`, or the run builds on the draft and says so in its report.

```bash
python3 harness/pipeline.py --repo ../my-service --design .workflow/designs/<file>.md --test-cmd ".venv/bin/python -m pytest -q"
```

The same folder holds three more: `fix.py` takes a bug report to a draft PR (the hotfix lane, or incident-fix's fix phase), `postmortem.py` turns a resolved incident log into a linted post-mortem with an owned follow-through, and the database and network workflow harnesses coordinate audit, design, diagram, and proposal stages. It's optional and Claude Code only; the skills don't depend on it.

---

## containers

Ordered: an image, then the stack around it — and, wherever the containers end up running, a review of how they run.

```
dockerfile → docker-compose        container-hardening · container-debug · docker-swarm
 (the image)  (the stack)          (how it runs · why it doesn't · the Swarm around it)
```

| Skill | What it does |
|-------|--------------|
| [dockerfile](skills/containers/dockerfile/SKILL.md) | Reads the stack off the repo, writes a multi-stage production Dockerfile — pinned base, non-root runtime, cache-correct layer order — and generates or repairs the `.dockerignore` that defines its build context. Verifies by building and running, not by reading. |
| [docker-compose](skills/containers/docker-compose/SKILL.md) | Detects the services the code actually connects to, wires them with named volumes, an isolated network and real health gates, and ships a documented `.env.example` plus a dev override. Verifies from cold, twice. |
| [container-hardening](skills/containers/container-hardening/SKILL.md) | Reviews how containers run — Compose, Kubernetes, Swarm or `docker run` — and the image supply chain: privileged mode, the Docker socket, host namespaces, root, capabilities, seccomp, read-only roots, limits, exposed ports, secrets, scanning. Scores 0–10 with the shared formula and a gate; Harden mode applies the fixes and proves the workload still runs. |
| [container-debug](skills/containers/container-debug/SKILL.md) | For a container that won't start, stay up or connect: captures the evidence before anything destroys it, reads the runtime's own record (exit code, `OOMKilled`, restart count, health log, events), matches the symptom against the container-specific failure modes, proves one hypothesis at a time, and routes the fix to the skill that owns it. Read-only in production. |
| [docker-swarm](skills/containers/docker-swarm/SKILL.md) | Reviews or designs a Swarm mode cluster and its stack files: quorum and manager count, autolock and backups, rolling-update and rollback settings, healthchecks as the rollout gate, stateful services on node-local volumes, overlays and the routing mesh, secrets and configs, placement — and the Compose keys `docker stack deploy` silently ignores. Says first whether Swarm is still the right tool. Scores 0–10 with the shared formula and a gate; read-only, never deploys or scales. |

**Run `dockerfile` first.** Compose orchestrates images; it cannot repair one. Most "compose is broken" reports are an image that doesn't start, doesn't answer its healthcheck, or dies on `SIGTERM`.

---

## operations

What happens around a system that's already running: fixing it when it breaks, recording what happened, telling people what changed, and keeping the tracker that holds the work honest.

```
hotfix ──escalates──► incident-fix ──hands its log to──► post-mortem      release-notes
 (urgent, not down)    (contain → diagnose → fix → learn)  (the record)     (stands alone)
      │                        │                               │
      └──── follow-ups, incident items ──► ticket ◄── changes ── backlog
                                    (Linear · Azure DevOps · Jira)  (map · refine · health · order)
```

| Skill | What it does |
|-------|--------------|
| [hotfix](skills/operations/hotfix/SKILL.md) | A fast lane for an urgent bug in a system that is **up**: discovers the repo's own commands and conventions, routes outages and design questions out, proves the bug red, fixes it once at the shared cause, runs one adversarial pass (strict on data, money, permissions and tenancy), and ships with recorded evidence. |
| [incident-fix](skills/operations/incident-fix/SKILL.md) | Production incidents end to end: contain first with ranked, reversible levers, diagnose read-only and size the impact with a reproducible count, fix through the review pipeline capped at two loops with data repair as its own artifact, then post-mortem and **follow-through** — every factor owned or explicitly accepted. Every production action waits for confirmation. |
| [release-notes](skills/operations/release-notes/SKILL.md) | Reads the change set from git, classifies every change (including an explicit **drop** bucket for anything with no user-visible effect), and translates each survivor from what was built into what the reader can now do. Depth matched to scope; breaking changes above the fold. |
| [post-mortem](skills/operations/post-mortem/SKILL.md) | Reconstructs a **resolved** incident into a blameless written record — timeline built from a git history date range plus incident docs and PDFs, quantified impact, and **contributing factors** rather than a single root cause. Ends with a pass over the prose hunting the blame that leaks in through grammar, a metadata block that makes incidents countable, and a review before publishing. |
| [ticket](skills/operations/ticket/SKILL.md) | Creates, updates, closes and logs time on work items in **Linear, Azure DevOps or Jira** — or a markdown log when there's no tracker — through one adapter per tool. Discovers types, states, required fields, sprints and labels at runtime into `.workflow/tracker.md`, reconciles against existing items before creating any, confirms the change set, and reads every write back. Owns the production-incident labels DORA metrics are built from. |
| [backlog](skills/operations/backlog/SKILL.md) | Shapes and audits a backlog, grounded in *User Story Mapping*, *Making Work Visible* and SRE: story maps with outcome-named release slices, refinement into thin stories with acceptance criteria, a scored 0–10 health check (oversized items, stale work, WIP, unplanned work, competing priorities, overdue follow-ups, error budget), and ordering by class of service and cost of delay. Reads the tracker; every change goes through ticket. |

`incident-fix` runs incidents the way *Site Reliability Engineering* describes: declared early, with a commander, exit criteria, a live state block above the append-only log, a register of temporary changes undone in steps, and impact sized against the error budget where an SLO exists.

`ticket` and `backlog` hardcode nothing about the team either: the tracker, its schema and its conventions are discovered and cached in `.workflow/tracker.md`, and every write waits for confirmation.

`hotfix` and `incident-fix` discover everything environment-specific at runtime — build and test commands as CI runs them, the merge convention, the tracker, rollback levers, observability — and cache it in `.workflow/env.md`, which both read. Neither hardcodes a stack, a CI product, a cloud or a ticket system.

`post-mortem` **documents; it does not prescribe.** The incident is already solved, so the skill reconstructs what happened and stops there — no remediation plan, no recommendations, no handoff into the build pipeline. That boundary is what keeps the record trustworthy: a document that reconstructs *and* prescribes has an incentive to shape the reconstruction toward the prescription. What to change next is a decision for whoever owns the system. Inside the response chain that decision is incident-fix's **follow-through** step — written after the record, as a separate artifact, so the record stays descriptive.

It needs inputs you supply: a **date range for the git history** and whatever **incident documentation** exists — the report, a vendor PDF, a chat export, alert emails. It reconstructs from artifacts, not from a description of the incident.

---

## database

Seven independent skills. Five of them — audit to build — are coordinated by [`harness/dbworkflow.py`](harness/dbworkflow.py) when the user wants a full or partial workflow; `dbarchitect` sits above them and `dbquery` beside them, and the harness runs neither.

```
Which stores, which flows:    dbarchitect → (one dbdesign per relational system of record)
Existing database: dbaudit → dbdesign → dbdiagram (Barker ER + relational) → dbpropose
New database:                 dbdesign → dbdiagram (Barker ER + relational) → dbpropose
Accepted proposal:                                       dbbuild
Running workload:  dbquery  (settles dbaudit's needs-data flags; index changes → dbpropose)
```

| Skill | What it does |
|-------|--------------|
| [dbarchitect](skills/database/dbarchitect/SKILL.md) | Decides which data stores a system needs and how data flows between them — system of record per fact, derived stores, data model, replication, partitioning, consistency per workflow — as decision records and a dataflow map, or reviews an existing architecture against the same rubric. |
| [dbaudit](skills/database/dbaudit/SKILL.md) | Audits existing databases with a repeatable score and evidence-backed strengths, weaknesses, and improvement opportunities. |
| [dbdesign](skills/database/dbdesign/SKILL.md) | Designs a new database or redesigns an audited one: requirements and a business-rule catalogue, a Barker model, functional dependencies, keys and normal forms, every rule mapped to its enforcing mechanism, and DDL that runs as written. |
| [dbdiagram](skills/database/dbdiagram/SKILL.md) | Produces editable draw.io ER (Barker) and relational model diagrams from a design or database structure, with semantic cell IDs, UID bars, alternate keys and inferred semantics labelled. |
| [dbpropose](skills/database/dbpropose/SKILL.md) | Turns the audit, design and diagrams into `proposal/proposal.md`: a decision register, expand/contract for breaking changes, and migration steps each with validation, rollback and blast radius, accepted before any DDL. |
| [dbbuild](skills/database/dbbuild/SKILL.md) | Generates reviewable DDL from an explicitly accepted proposal and its design; stops on an unaccepted proposal, mismatched inputs or an open structural decision. |
| [dbquery](skills/database/dbquery/SKILL.md) | Reviews the SQL a system actually runs — query text, execution plans and workload statistics — for cost, wrong results, races and injection, with prescriptions weighed against the whole workload and a 0–10 score. |

**The audit doesn't prescribe; design owns the model; proposal assembles the recommendation; dbbuild generates DDL only after proposal acceptance.** Conceptual ER diagrams use Barker notation throughout; relational diagrams keep table/key notation. The harness checks the required Barker page name/legend and diagram pair. The harness applies the 9.0 score threshold plus Critical/High, unused/copy, and unresolved needs-data ratio conditions. Structural iterations return through design, diagrams, and proposal before a revised proposal can be accepted for DDL generation. Skills remain independently usable outside the harness.

**The theory comes from the relational canon and its practitioners:** Codd; Date & Darwen (*The Third Manifesto*, *Database Explorations*); Silberschatz, Korth & Sudarshan; Ramakrishnan & Gehrke; Barker's CASE\*METHOD; Watt & Eng, Sharma et al. and Booth on design; Karwin's *SQL Antipatterns*; Winand's *SQL Performance Explained* and Faroult's *The Art of SQL*; Kleppmann's *Designing Data-Intensive Applications* and Petrov's *Database Internals*; and Obe & Hsu and Fontaine on PostgreSQL. Every term a finding cites is defined once in [theory.md](skills/database/dbaudit/theory.md), and its reference list says what each book contributes.

---

## networking

Five independent skills. Each ships `scripts/netgraph.py`, a standard-library Python script that computes the graph metrics and the address, flow and diagram checks, so an installed skill needs nothing from this repo. A clone adds an optional coordinator, [`harness/networkflow.py`](harness/networkflow.py), for a full or partial workflow.

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

**Two lenses carry the theory:** computer networking (Kurose & Ross; Tanenbaum & Wetherall) and network science (Newman; Barabási) — articulation points, Menger connectivity, betweenness and percolation make "single point of failure" and "blast radius" computable, and each skill computes them with its own `scripts/netgraph.py`. The optional harness adds secret redaction before any model reads evidence, runs the same script, scores by the database family's formula, and gates on score, open Critical/High findings, critical-pair connectivity ≥ 2, the 🔬 ratio, and usage. Blueprints need an explicitly accepted proposal, in a separate run.

---

## infrastructure

Two skills, each with three modes — **Review** (findings, a 0–10 score and a gate), **Design** (the target), **Propose** (a sequenced migration).

```
terraform   code · state · modules · versions · security · change safety · apply path
pipelines   flow · feedback · release · security & supply chain · environments · IaC delivery
```

| Skill | What it does |
|-------|--------------|
| [terraform](skills/infrastructure/terraform/SKILL.md) | Reviews Terraform/OpenTofu codebases across six domains, recovering a state map and module graph; designs layouts, state boundaries, module interfaces and environment models; proposes migrations where no resource is recreated by accident (`moved`/`import`/`removed`, expected plan of zero adds and destroys). Never touches a real backend. |
| [pipelines](skills/infrastructure/pipelines/SKILL.md) | Reviews CI/CD across flow, feedback, release, security, environments and IaC delivery, recovering the value stream from commit to production; designs the deployment pipeline (stage contracts, build-once promotion, release strategy, security model); proposes changes in an order that never takes the path to production down. Never triggers or approves a real CI run. |

**The theory comes from six books:** *Continuous Delivery*, *The DevOps Handbook*, *Site Reliability Engineering*, *Infrastructure as Code*, *The Terraform Book* and the AWS Terraform provider best practices — distilled into T1–T22 and P1–P22, and every finding cites one. Scoring uses the database and networking formula. The two skills meet at the apply path: terraform grades *whether* each root has a safe path to apply; pipelines designs it.

---

## security

Three skills, one per layer of defence, each with the same three modes — **Review**, **Design**, **Propose**.

```
threatmodel  what to protect, from whom    scope · adversaries · boundaries · policy · protocols · resilience
appsec       does the code enforce it      input · authentication · access · crypto · configuration · dependencies · logging · browser · api
hardening    is the platform locked down   identity · network · data · host · continuity · monitoring · governance · service
```

| Skill | What it does |
|-------|--------------|
| [threatmodel](skills/security/threatmodel/SKILL.md) | Reviews or builds a system's security design — system definition, assets, adversary classes and grades, a data-flow diagram with trust boundaries, threat tree and STRIDE per boundary, a hazard × mechanism matrix wanting two independent mechanisms per serious hazard, a risk register with owners, and security requirements traced to tests. Proposes risk treatment. Never attacks a live system. |
| [appsec](skills/security/appsec/SKILL.md) | Reviews application code on any stack across nine domains — browser trust boundary and APIs included — findings mapped to the current OWASP Top 10 and API Top 10 with `file:line` evidence, a score and a gate; designs a service's security controls; proposes remediation in risk order. Static by default; dynamic testing only against an environment you own and name. |
| [hardening](skills/security/hardening/SKILL.md) | Reviews hosts and cloud estates against a baseline — distro-agnostic and cloud-agnostic — recovering an asset register, exposure map and privilege map, with service-role overlays (web, mail, DNS, database, VPN); designs the baseline (control IDs, level per tier, per-platform mapping, a read-only check each); proposes a rollout where no step locks out its own operators. Never changes a host or account. |

**The theory comes from eighteen sources:** Anderson's *Security Engineering* (3rd ed.) as the spine; *The Art of Software Security Assessment* for design review; Hunt's *OWASP Top 10 for .NET developers*, Zalewski's *The Tangled Web*, McDonald's *Web Security for Developers* and Ball's *Hacking APIs* for application code; four LPI learning-material books; six Linux-hardening books (Rankin, Turnbull, Kalsi, Clinton and two shorter ones); and an anonymised production cloud-governance standard. *Secure by Design* (slides) is folded into the development pipeline instead — distilled into S1–S27, A1–A43 and H1–H30 that every finding cites. Scoring uses the shared formula. **First run (n=1, one eval per mode), out of 10:** threatmodel **10.0** vs 5.5 with no skill (its Propose eval re-run three times after a fix), appsec **10.0** vs 7.5, hardening **9.8** vs 7.0 (delta assertions; capability 10.0 for both arms).

---

## review

Six skills for a change as it arrives — a pull request, a branch, a diff — rather than work you are building inside the pipeline. Each works alone; [`harness/prreview.py`](harness/README.md#one-pull-request-through-every-review-skill--prreviewpy) runs them all on one PR.

```
pr-prep ─► code-xray ─► peer-review ◄─ test-review · concurrency-review · appsec ─► re-review ─► review-retro
readiness  history      lenses, verify,   specialists for lenses K, G and L          fixes        record, metrics,
                        report                                                       verified     proposals
```

| Skill | What it does |
|-------|--------------|
| [pr-prep](skills/review/pr-prep/SKILL.md) | The author's side, and a readiness check before anyone reviews. Author mode self-reviews with the omission checklist, checks size and shape (one concern, under ~400 lines), proposes a split, and writes the description: the claim, acceptance criteria, how to verify, risk, a reading order — annotated without priming the reviewer. Readiness mode restates someone's claim, classifies alignment (Exact / Missing / Tangling), lists process gaps, and says Ready, Ready with gaps, or Not ready. |
| [code-xray](skills/review/code-xray/SKILL.md) | Behavioural code analysis from git history (Tornhill), with a bundled read-only stdlib script: hotspots, rising hotspots, function-level X-rays, complexity trends and growth on a branch, change coupling and the missing co-change, clone twins, code age, and knowledge maps for routing reviews and spotting knowledge loss — never for rating people. PR mode feeds peer-review's risk map; codebase mode ranks refactoring targets by the interest they pay. |
| [peer-review](skills/review/peer-review/SKILL.md) | A senior-peer review built on Claude Code's built-in `/code-review` recipe (finder angles, a CONFIRMED/PLAUSIBLE/REFUTED verify pass, a gap sweep). It adds what the review literature says reviewers miss: the change against its claim (Exact / Missing / Tangling), omissions including the co-changes `git log` says should travel together, attention ranked by risk and hotspot in review units under 400 lines, security, test, concurrency and data lenses, and evolvability held apart from bugs. Comments state problem, evidence and fix. The report ends with a coverage statement and a recommendation a human makes, and a re-review verifies the fixes. Read-only unless asked to fix or post. |
| [test-review](skills/review/test-review/SKILL.md) | The specialist for peer-review's test lens: would each test fail if the behaviour broke, and does it test the requirement? Traces every claim and acceptance criterion to its tests (covered / weak / missing), names a mutation for each changed branch and shows whether an assertion catches it, and sweeps edges, error paths, determinism, doubles and clarity. A can't-fail claim is confirmed by a mutation probe in a scratch copy. |
| [concurrency-review](skills/review/concurrency-review/SKILL.md) | The specialist for peer-review's concurrency lens: shared state and lock scope, check-then-act, atomicity, deadlock, async pitfalls, pools, transactions and isolation, idempotency and at-least-once delivery, distributed locks, schedulers on many instances. Every finding's scenario is an interleaving; CONFIRMED needs a reproduction, re-run, because one green run proves nothing. |
| [review-retro](skills/review/review-retro/SKILL.md) | After review: a retrievable record of one PR (decisions, final outcomes, deferrals without an issue, answers that belong in the code), and over many reviews, metrics by type, severity, lens and area — never by person — plus checklist, rule and lint proposals a human approves. Nothing is applied. |

**The theory comes from six sources plus the built-in recipe:** *Best Kept Secrets of Peer Code Review* (the Cisco study), *Software Design X-Rays*, the *OWASP Code Review Guide* v2, *Clean Code*, Liddament's *Effective Code Review*, and *Rethinking Code Review in the Age of AI* (2026) — distilled into R1–R32 (peer-review), PP1–PP20 (pr-prep), X1–X22 (code-xray), TR1–TR22 (test-review), CR1–CR23 (concurrency-review) and RR1–RR17 (review-retro), and every finding cites one. **First run (n=3, 2026-11-03), out of 1.00 on delta:** peer-review **1.00** vs 0.29 with no skill, pr-prep **0.97** vs 0.31, code-xray **1.00** vs 0.40, test-review **1.00** vs 0.20, concurrency-review **1.00** vs 0.39, review-retro **1.00** vs 0.36 (re-run 2026-11-05 after it was made to stand alone, against a fresh baseline). Every eval is standalone: the run sees only the skill's own folder, with no harness and no sibling skills, as a single-skill install does. `harness/prreview.py` is tested against a stub model.

---

## memory

One skill for what agents learn about a repository, kept in the repository: shared, reviewed like code, and corrected by dreaming. Built on Anthropic's *The components of agent memory* (2026), the Claude API memory tool docs, and Monigatti's walkthrough of the tool, with one structural idea from *Redesigning source control at Anthropic* (2026).

```
capture (in session, light)  ──►  notes/  ──►  dream (offline, with hindsight)  ──►  a PR a person approves
"remember this" / clearly                       verify against the code · correct · merge · delete
worth keeping                                   promote to wiki/ · demote from INDEX.md · repair links
                                                remove secrets · quote planted instructions · advance the watermark
```

| Skill | What it does |
|-------|--------------|
| [repo-memory](skills/memory/repo-memory/SKILL.md) | Install the skill (`npx skills add izentenosmith/skills --skill repo-memory`), then run `/repo-memory` once in each repo to apply the layout ([how](skills/memory/README.md#install)). Install mode scaffolds `.memory/` as a four-layer hierarchy (git history as the transcript, one-fact notes, single-writer wiki pages, a small `INDEX.md` imported from `CLAUDE.md` / `AGENTS.md`) with guidance on what memory is for, not how to use it. Capture mode writes one note when something is clearly worth keeping. Dream mode is the offline consolidation pass: it reads only the commits since its watermark, re-verifies the notes they touched, corrects, merges, deletes and promotes with evidence, settles contradictions by the code, captures what recurred and nobody wrote down, writes relative dates as dates, keeps the index under 200 lines, removes secrets and treats instructions found in memory as data, then leaves the diff uncommitted for a person to approve. Audit mode runs the bundled read-only linter (`scripts/memlint.py`), whose `due` command tells a session at start that a dream is due. |

**The theory** is distilled into RM1–RM17. Stale is not wrong: a dream keeps an old note that still holds, and only its `verified` date moves. Memory is data, never authority: no dream obeys what it reads, and no change to memory lands without review.

---

## Reference docs

These carry no workflow of their own — the skill in the same folder links into them.

| Doc | Used by |
|-----|---------|
| [clean-architecture](skills/development/architect-deep-dive/clean-architecture.md) | architect-deep-dive — dependency direction, policy vs. detail, boundary placement (Martin) |
| [records](skills/development/architect-deep-dive/records.md) | architect-deep-dive — the ADRs and glossary entries a design leaves behind |
| [dimensions](skills/development/architect-deep-dive/dimensions.md) · [security](skills/development/architect-deep-dive/security.md) | architect-deep-dive — what to resolve under each design dimension; the questions behind the security one |
| [sub-session](skills/development/architect-deep-dive/sub-session.md) | architect-deep-dive — the dialogue when a coordinating session runs it |
| [pipeline](skills/development/architect-deep-dive/pipeline.md) | all eight development skills (a copy in each) — the stages and what each leaves, where questions go, what counts as an instruction, which commands may be run, the checkers |
| delegation ([architect-deep-dive](skills/development/architect-deep-dive/delegation.md) · [agent-brief](skills/development/agent-brief/delegation.md) · [acceptance-tests](skills/development/acceptance-tests/delegation.md) · [tdd](skills/development/tdd/delegation.md) · [refactor-review](skills/development/refactor-review/delegation.md) · [devils-advocate](skills/development/devils-advocate/delegation.md) · [tyr-verdict](skills/development/tyr-verdict/delegation.md)) | each stage — what a subagent may be given and how it is briefed |
| [examples](skills/development/agent-brief/examples.md) · [parallel-tracks](skills/development/agent-brief/parallel-tracks.md) | agent-brief — a good brief and a bad one; when a brief splits into tracks |
| [code-smells](skills/development/refactor-review/code-smells.md) | refactor-review — the symptom catalog (Refactoring Guru / Fowler) |
| [refactoring-techniques](skills/development/refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [comments](skills/development/refactor-review/comments.md) | refactor-review — which comments earn their place (tdd carries the ladder inline) |
| [good-tests](skills/development/tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](skills/development/tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](skills/development/tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](skills/development/tdd/interface-design.md) | tdd — designing for testability |
| [domain-primitives](skills/development/tdd/domain-primitives.md) | tdd — security-relevant values as validated, immutable types |
| [loop-and-tracks](skills/development/tdd/loop-and-tracks.md) | tdd — the loop-back pass on remediation slices, and building as one track |
| [targets](skills/development/devils-advocate/targets.md) | devils-advocate — what to trace on each of the ten attack-surface targets |
| [special-findings](skills/development/tyr-verdict/special-findings.md) | tyr-verdict — the extra rules for a security finding and a weakened check |
| ledger-format ([tdd](skills/development/tdd/ledger-format.md) · [refactor-review](skills/development/refactor-review/ledger-format.md) · [devils-advocate](skills/development/devils-advocate/ledger-format.md) · [tyr-verdict](skills/development/tyr-verdict/ledger-format.md) · [nexus](skills/development/nexus/ledger-format.md)) | the ledger's grammar and error codes — copies of [harness/LEDGER.md](harness/LEDGER.md) |
| [notes](skills/development/nexus/notes.md) · [contract](skills/development/nexus/contract.md) | nexus — the shared notes folder; the brief every sub-session gets |
| [setup](skills/development/nexus/setup.md) · [tracks](skills/development/nexus/tracks.md) · [after-merge](skills/development/nexus/after-merge.md) | nexus — setting up an increment and starting sessions; a tree of sessions per track; merging, cleanup and the end of the increment |
| [optimization](skills/containers/dockerfile/optimization.md) | dockerfile — base image trade-offs, layer order, cache mounts, secrets, signals |
| [dockerignore](skills/containers/dockerfile/dockerignore.md) | dockerfile — what to exclude and what each exclusion buys |
| [service-catalog](skills/containers/docker-compose/service-catalog.md) | docker-compose — per-service image, readiness probe, volume path, connection string |
| [environments](skills/containers/docker-compose/environments.md) | docker-compose — overrides, merge rules, `.env.example`, secrets |
| [theory](skills/containers/container-hardening/theory.md) | container-hardening — the principles every finding cites (C1–C13) |
| [controls](skills/containers/container-hardening/controls.md) | container-hardening — per-domain anti-patterns: what, why, detect, fix, cost, severity |
| [platforms](skills/containers/container-hardening/platforms.md) | container-hardening — each control in `docker run`, Compose, Kubernetes and Swarm; inspect templates; grep signals |
| [scoring](skills/containers/container-hardening/scoring.md) | container-hardening — severity, confidence, the 0–10 formula, the gate, templates |
| [symptoms](skills/containers/container-debug/symptoms.md) | container-debug — exit codes, and each symptom with its causes and the probe that tells them apart |
| [toolkit](skills/containers/container-debug/toolkit.md) | container-debug — read-only commands per platform, a shell for images that have none, keeping the evidence |
| [theory](skills/containers/docker-swarm/theory.md) | docker-swarm — the principles every finding cites (S1–S12): desired state, quorum, rolling updates, node-local state, the mesh |
| [controls](skills/containers/docker-swarm/controls.md) | docker-swarm — seven domains: what good looks like, each anti-pattern's what / why / detect / fix / severity, the scored checklists |
| [runbook](skills/containers/docker-swarm/runbook.md) | docker-swarm — read-only evidence commands, failure modes and their recovery, drills before go-live, the stack file skeleton |
| [scoring](skills/containers/docker-swarm/scoring.md) | docker-swarm — severity anchors and chains, confidence, the 0–10 formula, the go-live gate, templates |
| [anatomy](skills/operations/release-notes/anatomy.md) | release-notes — the six elements and the commit→outcome translation rules |
| [distribution](skills/operations/release-notes/distribution.md) | release-notes — depth to scope, when visuals earn their place, where to publish |
| [diagnosis](skills/operations/hotfix/diagnosis.md) | hotfix and incident-fix (a synced copy) — a red loop before any theory, minimise, ranked hypotheses, one probe at a time |
| [blameless-culture](skills/operations/post-mortem/blameless-culture.md) | post-mortem — why blameless is a data-collection strategy (Google SRE; Dekker) |
| [contributing-factors](skills/operations/post-mortem/contributing-factors.md) | post-mortem — past single-root-cause; the categories to sweep and where to stop |
| [evidence-sources](skills/operations/post-mortem/evidence-sources.md) | post-mortem — reading a git range, incident PDFs, chat exports and monitoring into a sourced timeline |
| [template](skills/operations/post-mortem/template.md) | post-mortem — the document's sections and the metadata block that makes incidents countable |
| [review-checklist](skills/operations/post-mortem/review-checklist.md) | post-mortem — the review before publishing, and reusing records afterwards |
| [roles](skills/operations/incident-fix/roles.md) | incident-fix — commander, operations, communications, planning; scaled to a small team; handoffs |
| [containment-levers](skills/operations/incident-fix/containment-levers.md) | incident-fix — ranked levers, overload and cascading-failure responses, the stepped ramp back |
| [adapters](skills/operations/ticket/adapters/azure-devops.md) | ticket — Azure DevOps, [Jira](skills/operations/ticket/adapters/jira.md), [Linear](skills/operations/ticket/adapters/linear.md) and a [local](skills/operations/ticket/adapters/local.md) markdown log |
| [profile](skills/operations/ticket/profile.md) | ticket — the `.workflow/tracker.md` project profile and where each value is discovered |
| [theory](skills/operations/backlog/theory.md) | backlog — the principles every finding cites, from story mapping, flow and SRE |
| [theory](skills/database/dbaudit/theory.md) | all seven database skills (copies outside dbaudit) — relational principles: relations vs tables, Codd's rules, FDs and keys, normal forms 1NF–6NF and decomposition, NULL and three-valued logic, isolation anomalies, SSOT vs derived data, constraint kinds, data/metadata separation, security |
| [er-modeling](skills/database/dbaudit/er-modeling.md) | all seven database skills (copies outside dbaudit) — CAP1–CAP4 pure modelling, reverse-engineering, notation crosswalk, 29 drills |
| [scoring](skills/database/dbaudit/scoring.md) | dbaudit; copied in dbquery — severity, confidence tags, the 0–10 formula, triage, output templates |
| [audit-lenses](skills/database/dbaudit/audit-lenses.md) | dbaudit — dead/copy schemas, coupling, dark data, security |
| [tables](skills/database/dbaudit/tables.md) · [indexes](skills/database/dbaudit/indexes.md) · [views](skills/database/dbaudit/views.md) · [procedures](skills/database/dbaudit/procedures.md) · [triggers](skills/database/dbaudit/triggers.md) | dbaudit — the per-object-type rubrics |
| [detection-signals](skills/database/dbaudit/detection-signals.md) | dbaudit; copied in dbquery — grep/regex per anti-pattern, with engine notes |
| [proposal](skills/database/dbpropose/proposal.md) | dbpropose; copied in dbbuild — input contract, verdicts, topology, translation, target-schema and remediation skeletons |
| [physical-design](skills/database/dbdesign/physical-design.md) | dbdesign; copied in dbpropose and dbbuild — the PostgreSQL 18 physical standard, including rule-enforcement tiers, concurrency and access design |
| [requirements](skills/database/dbdesign/requirements.md) | dbdesign — the requirements dossier: rule catalogue, data dictionary, access matrix |
| [query-rubric](skills/database/dbquery/query-rubric.md) · [plan-reading](skills/database/dbquery/plan-reading.md) | dbquery — statement, plan and workload anti-patterns with the scored checklist; each engine's plan vocabulary |
| [architecture-rubric](skills/database/dbarchitect/architecture-rubric.md) · [store-selection](skills/database/dbarchitect/store-selection.md) | dbarchitect — A1–A12; data model, engine, replication, consistency, partitioning and integration trade-offs |
| [theory](skills/networking/netaudit/theory.md) | netaudit, netdesign, netpropose, netblueprint — networking principles §1–§16 (Kurose & Ross; Tanenbaum & Wetherall) |
| [graph-theory](skills/networking/netaudit/graph-theory.md) | netaudit, netdesign, netpropose, netblueprint — the network-science lens G1–G12 (Newman; Barabási) |
| [topology-modeling](skills/networking/netaudit/topology-modeling.md) | all five network skills — the `topology.json` contract, reverse-engineering, drills |
| [scoring](skills/networking/netaudit/scoring.md) · [audit-lenses](skills/networking/netaudit/audit-lenses.md) · [detection-signals](skills/networking/netaudit/detection-signals.md) | netaudit — severity, confidence, formula, gate; cross-cutting lenses; grep per anti-pattern with platform notes |
| [addressing](skills/networking/netaudit/addressing.md) · [segmentation](skills/networking/netaudit/segmentation.md) · [routing](skills/networking/netaudit/routing.md) · [services](skills/networking/netaudit/services.md) · [resilience](skills/networking/netaudit/resilience.md) · [security](skills/networking/netaudit/security.md) | netaudit — the per-domain rubrics |
| [design-patterns](skills/networking/netdesign/design-patterns.md) | netdesign, netpropose — topology patterns, the addressing method, segmentation, routing, failure domains |
| [diagram-conventions](skills/networking/netdiagram/diagram-conventions.md) | netdiagram, netpropose, netblueprint — the canonical views, glyphs, IDs, validation |
| [proposal](skills/networking/netpropose/proposal.md) | netpropose — decisions by score band, cut-over sequencing |
| [blueprint](skills/networking/netblueprint/blueprint.md) | netblueprint — package layout, the IaC handoff contract, the `network-design.md` template |
| [theory](skills/infrastructure/terraform/theory.md) · [theory](skills/infrastructure/pipelines/theory.md) | terraform (T1–T22) and pipelines (P1–P22) — IaC, Continuous Delivery, DevOps Handbook and SRE principles |
| [review-rubric](skills/infrastructure/terraform/review-rubric.md) · [review-rubric](skills/infrastructure/pipelines/review-rubric.md) | terraform and pipelines — the six domains each: 🟢, 🔴 anti-patterns, checklists |
| [detection-signals](skills/infrastructure/terraform/detection-signals.md) · [detection-signals](skills/infrastructure/pipelines/detection-signals.md) | terraform (AWS/azurerm/google) and pipelines (GHA/GitLab/Azure/Jenkins/CircleCI) — grep per anti-pattern |
| [scoring](skills/infrastructure/terraform/scoring.md) · [scoring](skills/infrastructure/pipelines/scoring.md) | terraform and pipelines — severity, confidence, formula, gate, templates |
| [design-patterns](skills/infrastructure/terraform/design-patterns.md) · [design-patterns](skills/infrastructure/pipelines/design-patterns.md) | terraform (layouts, state, modules, environments) and pipelines (reference pipeline, release strategies, security model, IaC delivery) |
| [proposal](skills/infrastructure/terraform/proposal.md) · [proposal](skills/infrastructure/pipelines/proposal.md) | terraform (no-recreate rule) and pipelines (keep-prod-up sequencing) — decisions and migration order |
| [theory](skills/security/threatmodel/theory.md) · [theory](skills/security/appsec/theory.md) · [theory](skills/security/hardening/theory.md) | threatmodel (S1–S27), appsec (A1–A43) and hardening (H1–H30) — Anderson, TAOSSA, Hunt, Zalewski, McDonald, Ball, the LPI essentials, six Linux-hardening books and a generalised cloud-governance standard |
| [review-rubric](skills/security/threatmodel/review-rubric.md) · [review-rubric](skills/security/appsec/review-rubric.md) · [review-rubric](skills/security/hardening/review-rubric.md) | the six, nine and eight domains: 🟢, 🔴 anti-patterns, checklists |
| [detection-signals](skills/security/threatmodel/detection-signals.md) · [detection-signals](skills/security/appsec/detection-signals.md) · [detection-signals](skills/security/hardening/detection-signals.md) | design-artefact signals; grep per anti-pattern per stack; read-only checks per control per distro and per cloud |
| [scoring](skills/security/threatmodel/scoring.md) · [scoring](skills/security/appsec/scoring.md) · [scoring](skills/security/hardening/scoring.md) | severity, confidence, formula, gate, templates |
| [design-patterns](skills/security/threatmodel/design-patterns.md) · [design-patterns](skills/security/appsec/design-patterns.md) · [design-patterns](skills/security/hardening/design-patterns.md) | DFD, STRIDE, threat trees, adversary and access-control catalogues; per-stack control patterns; the baseline catalogue with distro and cloud mapping, naming, tagging and exceptions |
| [proposal](skills/security/threatmodel/proposal.md) · [proposal](skills/security/appsec/proposal.md) · [proposal](skills/security/hardening/proposal.md) | risk treatment; remediation in risk order; the no-lockout rollout |
| [theory](skills/review/peer-review/theory.md) | peer-review — the principles every finding cites (R1–R32): Cohen, Tornhill, OWASP, Martin, Liddament, Kamalı et al., and the built-in recipe |
| [lenses](skills/review/peer-review/lenses.md) | peer-review — the sixteen finder lenses A–P, each with what to look for and what it tends to miss; the omission checklist |
| [history-signals](skills/review/peer-review/history-signals.md) | peer-review — hotspots, change coupling and the missing co-change, clone twins, complexity growth, code age, knowledge maps, from `git log` |
| [security-lens](skills/review/peer-review/security-lens.md) | peer-review — the security pass every diff gets, the grep table, and the triggers that escalate to appsec |
| [heuristics](skills/review/peer-review/heuristics.md) | peer-review — Clean Code's chapter-17 heuristics beyond Fowler; the concurrency, failure-path and test checklists; contested advice |
| [comments](skills/review/peer-review/comments.md) | peer-review — the shape of a finding, labels, the usefulness filter, posting, pushback |
| [report](skills/review/peer-review/report.md) | peer-review — severity, verdicts, the recommendation rule, caps, the findings-tool mapping, the report and re-review templates |
| [theory](skills/review/pr-prep/theory.md) | pr-prep — the principles PP1–PP20: author preparation and its priming risk, the claim, size and shape, omissions |
| [description-template](skills/review/pr-prep/description-template.md) | pr-prep — the PR description template, with a filled example |
| [splitting](skills/review/pr-prep/splitting.md) | pr-prep — how to split or untangle a change, in which order, and when not to |
| [self-review](skills/review/pr-prep/self-review.md) | pr-prep — the author's checklist, one item at a time |
| [theory](skills/review/code-xray/theory.md) | code-xray — the principles X1–X22 from *Software Design X-Rays* |
| [analyses](skills/review/code-xray/analyses.md) | code-xray — each analysis: what it measures, how the script computes it, thresholds, false readings and data cleaning |
| [report](skills/review/code-xray/report.md) | code-xray — the PR-signals block and the codebase report with its ranked refactoring targets |
| [theory](skills/review/test-review/theory.md) | test-review — the principles TR1–TR22: tests as evidence, would it fail, F.I.R.S.T. |
| [checklist](skills/review/test-review/checklist.md) | test-review — the TQ checks in eight families, one item at a time |
| [mutation](skills/review/test-review/mutation.md) | test-review — the mutation probe that confirms a test can't fail, and the tools |
| [smells](skills/review/test-review/smells.md) | test-review — test smells: how to spot each one, why it matters, the fix |
| [theory](skills/review/concurrency-review/theory.md) | concurrency-review — the principles CR1–CR23: shared state, atomicity, deadlock, delivery, and why one green run proves nothing |
| [checklist](skills/review/concurrency-review/checklist.md) | concurrency-review — the CK checks, one item at a time |
| [interleavings](skills/review/concurrency-review/interleavings.md) | concurrency-review — the notation for an interleaving, with worked examples |
| [languages](skills/review/concurrency-review/languages.md) | concurrency-review — per-language traps and the tools that settle a claim |
| [theory](skills/review/review-retro/theory.md) | review-retro — the principles RR1–RR17: records, measuring without rating people, improving |
| [metrics](skills/review/review-retro/metrics.md) | review-retro — each metric: definition, formula, what it tells you, how it's gamed, minimum sample |
| [record-template](skills/review/review-retro/record-template.md) | review-retro — the PR record and retro report templates |
| [proposals](skills/review/review-retro/proposals.md) | review-retro — turning recurring findings into checklist items, rules and lint rules, with the human-approval rule |
| [theory](skills/memory/repo-memory/theory.md) | repo-memory — the principles RM1–RM17: the memory hierarchy, dreaming, single writers, small injected context, memory as data; the API memory tool |
| [layout](skills/memory/repo-memory/layout.md) | repo-memory — the `.memory/` tree, note and page frontmatter, the index budget, the entry-point import, migrating, what never goes in |
| [dreaming](skills/memory/repo-memory/dreaming.md) | repo-memory — the dream pass: incremental inputs, the six operations and their evidence, verifying a note, contradictions, cadence and the session-start nudge, gaps across sessions |
| [templates](skills/memory/repo-memory/templates.md) | repo-memory — INDEX.md, a note, a page, `.dream-state`, the dream report, the CI gate, schedule and session-start hook |

Each doc lives in the folder of the skill that uses it, and nothing reaches across folders.

## Delegation

Any stage can optionally hand its **read-only or fresh-context** work to a subagent. Delegation is most valuable at the ends of a pipeline — evidence-gathering before a design decision, and before a verdict — and least valuable in the middle, where the work is a sequential loop that learns from itself.

| Skill | Delegate | Keep in the main thread |
|-------|----------|-------------------------|
| architect-deep-dive | codebase inference behind **[inferred]** answers | the dialogue, round by round |
| agent-brief | the prior-art hunt | writing and ordering the plan |
| acceptance-tests | finding the outermost boundary and existing acceptance suites | **writing the tests, one criterion at a time** |
| tdd | convention lookups only | **every RED and GREEN — the whole loop** |
| refactor-review | smell identification on a large diff | prescribing and applying the refactors |
| devils-advocate | **the whole teardown** — fresh context is the point | ranking the findings |
| tyr-verdict | per-finding verification | **the severity, the slices, the GO/NO-GO** |
| dockerfile | per-service stack inference in a monorepo | writing and verifying the image |
| docker-compose | per-service dependency detection in a monorepo | **the wiring** — it's all relationships between services |
| container-hardening | per-directory or per-namespace inventory and findings on a large estate | **chains, scoring, the gate, and every Harden change** |
| container-debug | — (one failure, one thread of evidence) | **the whole diagnosis** |
| docker-swarm | per-stack-file inventory and findings when there are many stacks | **the cluster domain, chains, scoring, the gate and Design** |
| release-notes | gathering and classifying a large change set | **writing the prose — it must be one voice** |
| hotfix | the caller sweep; convention lookups | **the red→green and the fix** |
| incident-fix | evidence gathering in diagnosis, one delegate per source | **containment, every production action, and the fix decisions** |
| post-mortem | gathering and timeline reconstruction, split by source | the factors and the blamelessness pass |
| ticket | reconciliation searches over a long commit range | **drafting, confirmation and every write** |
| backlog | reading a large snapshot, per area or per board | **the map, the scores, the order and the change set** |
| dbaudit | per-database evaluation of each DDL file | **scoring and the synthesis** |
| dbdesign | requirements mapping and model review | **the modeling decisions and target structure** |
| dbdiagram | source-backed ER and relational views | **diagram semantics and layout** |
| dbpropose | audit/design/diagram inputs | **the recommendation and prioritization** |
| netaudit | per-network evidence reading and topology recovery | **scoring, the graph metrics, and the synthesis** |
| netdesign | requirements and inventory mapping | **zones, addressing, routing and redundancy decisions** |
| netdiagram | per-view drafting from the model | **view semantics and layout** |
| netpropose | audit/design/diagram inputs | **the recommendation and cut-over order** |
| terraform | per-codebase inventory and evaluation in an estate review | **scoring, the gate, state boundaries and the migration sequence** |
| pipelines | per-repo inventory and evaluation in an estate review | **scoring, the gate, the stage chain and the migration sequence** |
| threatmodel | evidence gathering from design docs and code | **the threat tree, the risk ratings and the treatment decisions** |
| appsec | per-module or per-service code reading in a large repo | **scoring, the gate and the remediation order** |
| hardening | per-account or per-host-role evidence collection | **scoring, the gate, the baseline and the rollout order** |
| peer-review | **every finder lens and every verifier** — fresh context is the point | **the claim, the risk map, severity, ranking and the recommendation** |

Each skill carries its own copy of the dispatch contract it needs, so the folders stay independently copyable — see [Conventions](#conventions).

## Do they work?

[`evals/`](evals/README.md) holds the harness that measures it — seeded fixtures with planted defects (a rule that ignores its config, and a vacuous test that hides it), scored assertions, and the recorded result in [evals/benchmark.md](evals/benchmark.md).

Assertions are split: **capability** (does the stage do its job at all) from **delta** (does it do what the skill instructs). The headline is the **outcome gain**, capability with the skill minus capability without it: across the 80 evals with a baseline it is **+0.12** (1.00 vs 0.88), against an instruction-following (delta) gain of +0.47. A baseline that never read the skill fails most delta assertions by construction, so delta gain overstates what a skill adds; and 58 of the 80 baselines already pass every capability assertion, so those evals can only catch a regression on outcome ([evals/README.md](evals/README.md#capability-vs-delta)). The figures below predate this framing and quote delta first. The seven `development` stages were re-run on 2026-11-03, after the security material landed in them. Each eval ran three times with the skill and once against the pre-session baseline, 28 runs in all. tdd, refactor-review and devils-advocate were then fixed and evals 2–4 re-run the same way (12 runs). All seven were re-run on 2026-11-11 (28 runs) after save points, the brief's approval gate, the bar-itself attack surface and the ship checklist were added, and score **0.99 vs 0.15** on delta and **0.99 vs 0.95** on capability.

**Scored: every skill.** The seven `development` stages carry the n=3 result above. The other skills' first run (2026-10-25) is one with-skill run each — three for evals 11–13, and evals 8–14 were re-run three times on 2026-11-03 — against a baseline with no skill at all, which is the honest comparison for a skill that did not exist at the baseline ref. The security family's first run (2026-11-02, evals 38–46, one per mode) is the same shape. The database family (evals 30–34, 47–48) was last re-run three times each on 2026-11-21, after a best-practice and security audit of all seven skills (iterations 60 and 62): **0.98 vs 0.65** on delta, **1.00 vs 0.97** on capability. The container family (evals 6, 28 and 35–37) has three with-skill runs per eval. Every run scored 1.00 on delta, against **0.51** on average for no skill; evals 6, 28, 36 and 37 were re-run on 2026-11-04/05 with traps for what the skills add over a bare agent, which had scored 0.75 against them before. The review family (2026-11-03, evals 49–54) has three standalone with-skill runs per eval, against no skill: **0.99 vs 0.31** on delta, **1.00 vs 0.92** on capability. The infrastructure, operations and security skills (terraform, pipelines, release-notes, threatmodel, appsec, hardening: evals 21–26, 29, 38–39, 41–46) were re-run three times each on 2026-11-05, after fixes to terraform and hardening and new assertions where a bare agent already scored 0.79 or more; evals 29, 39, 43 and 46 ran three times more on 2026-11-09 after fixes to release-notes, appsec and hardening: **0.99 vs 0.63** on delta, **1.00 vs 0.94** on capability. repo-memory (2026-11-07, eval 55) has three standalone with-skill runs against no skill: **1.00 vs 0.77** on delta, **1.00 vs 1.00** on capability. hotfix, incident-fix, post-mortem (evals 7–14) and repo-memory (55) were re-run three times each on 2026-11-09, after the SRE book update and repo-memory's later changes: every with-skill run scores 1.00, eval 7 at n=3 for the first time. ticket and backlog (2026-11-10, evals 56–57) have three standalone with-skill runs each against no skill: **1.00 vs 0.71** (ticket, after its 2026-11-10 rework) and **1.00 vs 0.69** (backlog) on delta, **1.00 vs 1.00** on capability. Across all 58 scored evals: **0.99 vs 0.49** on delta, **1.00 vs 0.90** on capability. Per eval in [evals/benchmark.md](evals/benchmark.md). Not in those figures: evals 60–63, added on 2026-11-20 for the development skills' newer rules (see [evals/README.md](evals/README.md#the-pipeline-harder-evals-6063)), were first scored on 2026-11-20. They and evals 0–5, 27 and 58 were run three times each as iteration 55 on the final text and recorded: 1.00 on delta in every one except eval 3 (0.96), and the four new evals score 1.00 against 0.83, 0.67, 0.50 and 0.38 without the skill.

The fixtures are seeded so a naive answer fails them: a compose fixture with a stale `ELASTICSEARCH_URL`, an incident whose trigger sits nine days before the outage, production levers that are stubs recording their calls (so "took no action without confirmation" is checked, not inferred), networks graded by parsing every CIDR and every draw.io cell, DDL executed in SQLite and probed with rows that must be refused, acceptance tests run against three mutants.

**Where the first run is weakest** — single runs, so a lone miss is a signal, not a verdict:

- `container-debug` **1.00 vs 0.58** is the smallest gain in the container family. A bare agent diagnoses an OOM kill, a `localhost` URL, CRLF line endings and even a 137 that is a stop timeout, not OOM. The skill adds the frame: the mode, rotation and redacted captures for an exposed secret, a root-cause note per symptom, a not-verified list, and each fix proven by the probe that found it. `dockerfile` (**1.00 vs 0.45**) first scored **0.79 vs 0.79** and then 1.00 vs 0.83, because its eval measured mostly what any competent repair does; it now also tests what the skill instructs and a bare agent skips. See [evals/README.md](evals/README.md#dockerfile-eval-28).
- `pipelines` Propose **0.93 vs 0.70** (n=3, up from 0.80; that miss was a grader false negative): two runs move a `Recreate` → rolling-update step ahead of build-once, which the order check reads as release safety coming first.
- `netblueprint` scores **1.00 vs 1.00**: its eval checks that it refuses an unaccepted proposal, which a bare agent also does.
- `repo-memory` **1.00 vs 0.77** (n=3): a bare agent asked to "dream" over the memory already re-verifies notes against the code, fixes the changed retry limit and the rename, keeps the stale-but-true note, merges the duplicate, repairs the broken link, shrinks the index, strips the password and advances the watermark. The skill adds two things: promoting the three Relay notes into one page, and reporting the instruction planted in a session log as data. The bare run deleted that log without saying so. The 2026-11-09 bare run also staged its changes in git, where the skill leaves them unstaged for a person to review.
- `ticket` **1.00 vs 0.71** (n=3, iteration 36). The first run scored 1.00 vs 0.92: a bare agent given the profile, a Jira export and no Jira access already reconciles every bug-bash finding correctly. So on 2026-11-10 the eval gained traps for what ticket's references instruct and a bare agent skips. These are a demo line on each story, acceptance criteria inside each story's own draft, a follow-up with an action type, due date and what's in place meanwhile, the profile corrected and its traps recorded, and the pending change-set file. One new trap, a required severity the repo can't supply, the fresh baseline also got right.
- `nexus` **1.00 vs 0.87** (n=3, iteration 50, with the start-of-session routine, `env.md`, `increment.json` and no fixed session cap; 0.96 vs 1.00 at iteration 49, where one run missed two assertions). Before those changes, **1.00 vs 1.00** (iteration 47; 1.00 vs 0.92 at its first run): the fixture is a coordination already mid-increment, so its notes folder, decisions register and earlier replies show a bare agent every convention it needs. The bare agent holds the stale-GO PR back, refuses the borrowed label and the loosened check, and questions a ruling given in a session's own window. It notices the silent session and routes the cross-slice aside. What the eval can't see is the setup: creating the folder, briefing each session with the contract, and splitting a brief into tracks. An eval that starts from an empty folder would measure that.
- `dbquery` **1.00 vs 0.86** (n=3, 2026-11-21): a bare agent already ranks by total time, finds the N+1 and weighs the indexes; the skill adds the 0–10 score with its base and cap, and a complete review every time. Its `EXPLAIN ANALYZE` rule now allows only a `SELECT` outside production.
- `dbdiagram` **1.00 vs 0.77** (n=3, 2026-11-21): the design it is handed is already written in Barker, so a bare agent draws most of it. Its first run's 0.83 was mostly grader false negatives (an invisible junction read as a Chen oval, a legend split across cells, key cells side by side). The skill now carries draw.io conventions, and the eval also checks UID bars, alternate keys, labelled FK paths and the validation report. Its notation-translation rules are not exercised by this fixture.
- `dbaudit` **0.95 vs 0.36** (n=3, 2026-11-21). It now writes a four-line gate, a recovered model of Barker sentences, a copied parent column as a ⚠️ 3NF candidate, and every secret as file:line with the value redacted (3/3 since the audit, 2/3 before). What still varies by run: a High finding resting on a needs-data claim, and a finding row missing a field.
- `dbdesign` **0.97 vs 0.54** (n=3, 2026-11-21). Its assumptions and open questions sit in two separate lists, and its DDL runs as written in an in-memory SQLite database. One run in three still maps the subtypes without naming the choice.
- `dbpropose` **0.97 vs 0.39**, `dbbuild` **1.00 vs 0.89** and `dbarchitect` **1.00 vs 0.73** (n=3, 2026-11-21). dbbuild's eval barely separates the skill from a bare agent, which already writes runnable DDL from an accepted proposal; it needs a harder fixture.

Two safety-critical skills had a safety rule slip in one of three runs, and now make those rules hard gates checked before any other action: `hotfix` routes an outage to incident-fix and writes nothing (eval 11 **0.83 → 1.00**), and `incident-fix` changes no code before containment (eval 12 **0.95 → 1.00**) and writes its impact query into the log, with a repair that is a dry run by default and backs itself up before any write (eval 13 **0.90 → 1.00**). Evals 8–10 and 14 held at 1.00 over three runs each.

Three skills were fixed after their first run and re-run three times each: `acceptance-tests` **0.75 → 1.00** (criteria that already hold are tested with their contrast; edges tested within seconds; one mapping line per criterion), `dbpropose` **0.61 → 0.92** (a `proposal.md` file, a step table with validation, rollback and blast radius, data before constraints, expand/contract, acceptance before dbbuild), and `dbdesign` **0.69 → 0.95** — most of whose first score was four grader false negatives (bold Barker sentences, a "Normal-form" heading, the intersection table's own column, an age-band lookup), fixed in `grade.py` with every control re-checked.

The 2026-11-03 re-runs of the seven `development` stages, before → after (evals 2–4 from the second re-run):

| eval | skill | delta | cap | cap base |
|---|---|---|---|---|
| 0 | architect-deep-dive | 0.91 (n=1) → **1.00** | 1.00 → 1.00 | 1.00 |
| 1 | agent-brief | 1.00 → **1.00** | 1.00 → 1.00 | 0.86 → 1.00 |
| 2 | tdd | 1.00 → **1.00**, new assertions; baseline 1.00 → 0.00 | 0.78 → **1.00** | 0.83 → 0.88 |
| 27 | acceptance-tests | 1.00 → **0.94** | 1.00 → 1.00 | 0.50 → 0.67 |
| 3 | refactor-review | 1.00 → 0.88 → **1.00** | 1.00 → 1.00 | 1.00 → 0.75 |
| 4 | devils-advocate | 0.92 → 0.87 → **1.00** | 1.00 → 1.00 | 1.00 |
| 5 | tyr-verdict | 1.00 → **1.00** | 1.00 → 1.00 | 0.83 |

tdd's 0.78 came from the grader. Every run wrote a boundary test, but one put it in a new test file the grader didn't read, and a relative venv path failed "suite is green" for every run, the baseline's included. Both are fixed in `grade.py`. After that fix, eval 2 no longer separated tdd from its baseline: the old skill also ticked the brief and logged a revision. Those checks are now capability. The delta now asks for what tdd instructs and a capable agent skips: each criterion ticked in place and naming the test that verifies it, each cycle's red recorded with the failure it showed, and the tracer bullet red on the missing behavior rather than a `TypeError` from the clock seam it needs. The old skill and a no-skill run both score 0/3 on these. refactor-review's 0.88 was one run that skipped the stopping rule, plus two grader false negatives ("the diff is small" wasn't read as calibration, and `blocking` was demanded of a pass with nothing blocking). devils-advocate's 0.87 was two runs whose ledgers named the settling run for every unproven finding but whose responses didn't. Both skills now state what the response must carry, and both are **1.00** over three runs. See [evals/README.md](evals/README.md#the-pipeline-fixture-evals-05). acceptance-tests stays at **0.94**.

## How to use

### Install as a Claude Code plugin

All 43 skills install as one plugin, `izentenosmith-skills`, from the marketplace this repo declares in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json). The plugin is the `skills/` folder alone: the [harness](harness/README.md) and the evals stay in a clone. On Claude Code 2.1.275 or later, one command in a session:

```
/plugin install izentenosmith-skills --marketplace izentenosmith/skills
```

Or from a shell, in two steps:

```bash
claude plugin marketplace add izentenosmith/skills
```

```bash
claude plugin install izentenosmith-skills@izentenosmith
```

- **It is all or nothing.** The plugin carries every skill, and their descriptions add about 8k tokens to every session. For a few skills or a bundle, use `npx` below.
- **Skills get the plugin's namespace** when you call them by hand: `/izentenosmith-skills:tdd`. Claude still picks them by description on its own.
- **It follows releases, not `main`.** The plugin's `version` in [`marketplace.json`](.claude-plugin/marketplace.json) is the release number in [CHANGELOG.md](CHANGELOG.md), and Claude Code updates an install only when that number changes.
- **It is for Claude Code only.** Cursor and other agents install with `npx`.

### Install with `npx`

Every skill installs by name through the [`skills` CLI](https://github.com/vercel-labs/skills) — nothing to clone. The CLI finds each `SKILL.md` in this repo by its frontmatter `name`, so commands name skills, never family folders. Run them from the root of the repo you want the skills in.

**This repo is public: no GitHub account or access is needed to install from it.** The CLI clones over HTTPS. On a machine that reaches GitHub only over SSH, give it the SSH URL directly: `npx skills add git@github.com:izentenosmith/skills.git --skill <name>`. In CI, a `GH_TOKEN` (or `GITHUB_TOKEN`) is optional; it only raises GitHub's rate limit for `npx skills update`, which checks for new versions.

**A whole workflow** — one command per family:

```bash
# development — the seven-stage pipeline
npx skills add izentenosmith/skills --skill architect-deep-dive agent-brief acceptance-tests tdd refactor-review devils-advocate tyr-verdict

# development — nexus, to run several of those pipelines at once (install it beside the seven)
npx skills add izentenosmith/skills --skill nexus

# containers — image, then stack, then how it runs
npx skills add izentenosmith/skills --skill dockerfile docker-compose container-hardening container-debug docker-swarm

# operations — the response chain, release-notes, and the tracker pair
npx skills add izentenosmith/skills --skill hotfix incident-fix post-mortem release-notes ticket backlog

# database — architect, audit, design, diagram, propose, build, query review
npx skills add izentenosmith/skills --skill dbarchitect dbaudit dbdesign dbdiagram dbpropose dbbuild dbquery

# networking — audit, design, diagram, propose, blueprint
npx skills add izentenosmith/skills --skill netaudit netdesign netdiagram netpropose netblueprint

# infrastructure — terraform and pipelines (review, design, propose)
npx skills add izentenosmith/skills --skill terraform pipelines

# security — threat model, application code, hardening (review, design, propose)
npx skills add izentenosmith/skills --skill threatmodel appsec hardening

# review — a change as it arrives
npx skills add izentenosmith/skills --skill pr-prep code-xray peer-review test-review concurrency-review review-retro

# memory — what agents learn about the repo, kept true by dreaming
npx skills add izentenosmith/skills --skill repo-memory
```

### Bundles

**By role** — the skills one kind of work reaches for, at most 20 per line, from [`skills/bundles.json`](skills/bundles.json). Every skill is in at least one bundle; a skill from another family is there because the role hands work to it (the manifest's `placed` says why for each).

```bash
# builder — the seven-stage pipeline and nexus, plus the tracker pair and release-notes
npx skills add izentenosmith/skills --skill architect-deep-dive agent-brief acceptance-tests tdd refactor-review devils-advocate tyr-verdict nexus backlog ticket release-notes repo-memory

# reviewer — the review family, plus the security family, where peer-review's security lens escalates
npx skills add izentenosmith/skills --skill pr-prep code-xray peer-review test-review concurrency-review review-retro threatmodel appsec hardening container-hardening repo-memory

# on-call — the response chain and the tracker pair, plus container-debug
npx skills add izentenosmith/skills --skill hotfix incident-fix post-mortem ticket backlog container-debug repo-memory

# platform — containers and infrastructure, plus hardening for the hosts and cloud underneath
npx skills add izentenosmith/skills --skill dockerfile docker-compose container-hardening container-debug docker-swarm terraform pipelines hardening repo-memory

# data — the database family
npx skills add izentenosmith/skills --skill dbarchitect dbaudit dbdesign dbdiagram dbpropose dbbuild dbquery repo-memory

# network — the networking family
npx skills add izentenosmith/skills --skill netaudit netdesign netdiagram netpropose netblueprint repo-memory

# security — the security family, plus container-hardening for the container layer
npx skills add izentenosmith/skills --skill threatmodel appsec hardening container-hardening repo-memory
```

`repo-memory` is on every line because every role benefits from what the last session learned; drop it from the line if you don't want it.

### Everything, or one skill

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
| | `npx skills add izentenosmith/skills --skill nexus` |
| containers | `npx skills add izentenosmith/skills --skill dockerfile` |
| | `npx skills add izentenosmith/skills --skill docker-compose` |
| | `npx skills add izentenosmith/skills --skill container-hardening` |
| | `npx skills add izentenosmith/skills --skill container-debug` |
| | `npx skills add izentenosmith/skills --skill docker-swarm` |
| operations | `npx skills add izentenosmith/skills --skill hotfix` |
| | `npx skills add izentenosmith/skills --skill incident-fix` |
| | `npx skills add izentenosmith/skills --skill post-mortem` |
| | `npx skills add izentenosmith/skills --skill release-notes` |
| | `npx skills add izentenosmith/skills --skill ticket` |
| | `npx skills add izentenosmith/skills --skill backlog` |
| database | `npx skills add izentenosmith/skills --skill dbarchitect` |
| | `npx skills add izentenosmith/skills --skill dbaudit` |
| | `npx skills add izentenosmith/skills --skill dbdesign` |
| | `npx skills add izentenosmith/skills --skill dbdiagram` |
| | `npx skills add izentenosmith/skills --skill dbpropose` |
| | `npx skills add izentenosmith/skills --skill dbbuild` |
| | `npx skills add izentenosmith/skills --skill dbquery` |
| networking | `npx skills add izentenosmith/skills --skill netaudit` |
| | `npx skills add izentenosmith/skills --skill netdesign` |
| | `npx skills add izentenosmith/skills --skill netdiagram` |
| | `npx skills add izentenosmith/skills --skill netpropose` |
| | `npx skills add izentenosmith/skills --skill netblueprint` |
| infrastructure | `npx skills add izentenosmith/skills --skill terraform` |
| | `npx skills add izentenosmith/skills --skill pipelines` |
| security | `npx skills add izentenosmith/skills --skill threatmodel` |
| | `npx skills add izentenosmith/skills --skill appsec` |
| | `npx skills add izentenosmith/skills --skill hardening` |
| review | `npx skills add izentenosmith/skills --skill pr-prep` |
| | `npx skills add izentenosmith/skills --skill code-xray` |
| | `npx skills add izentenosmith/skills --skill peer-review` |
| | `npx skills add izentenosmith/skills --skill test-review` |
| | `npx skills add izentenosmith/skills --skill concurrency-review` |
| | `npx skills add izentenosmith/skills --skill review-retro` |
| memory | `npx skills add izentenosmith/skills --skill repo-memory` |

Any mix works too — `--skill` takes as many names as you give it.

Useful flags:

| Flag | Effect |
|---|---|
| `-a claude-code` · `-a cursor` | Install for that agent only, instead of being asked. Takes several: `-a claude-code cursor`. |
| `-g` | Install at user level (every project) instead of into the current repo. |
| `-y` | Skip the confirmation prompts. |
| `--list` | Show every skill in this repo without installing. |

`npx skills update` pulls newer versions of what you installed; `npx skills remove <name>` takes one out.

The installer copies each skill folder whole, and every folder is self-contained: a reference doc several skills share is committed as a copy in each of them (see [Conventions](#conventions)), because the installer drops a symlink that leaves the skill folder. **It installs skills, not the [harness](harness/README.md)** — the Python orchestration in `harness/` (including `dbworkflow.py` and `networkflow.py`) needs a clone. The networking skills carry their one script, `scripts/netgraph.py`, inside each folder, and the development skills carry the checkers they run (`scripts/ledger.py`, `redgreen.py`, `brief.py`) the same way.

### Pinning a version

The commands above install whatever is on `main`. Releases are git tags (`v1.0.0` is the first); what each one changed, and what counts as a breaking change, is in [CHANGELOG.md](CHANGELOG.md). To install a release instead of `main`, put the tag after the repo with `@`:

```bash
npx skills add izentenosmith/skills@v1.0.0 --skill tdd refactor-review
```

The same form takes a full 40-character commit SHA. Checked against the pushed tag on 2026-11-22: `npx skills add izentenosmith/skills@v1.0.0 --list` reads the source as `@ v1.0.0` and finds all 43 skills. Whether `npx skills update` keeps a tag pin or moves to `main` is not verified; to change versions, run `add` again with the new tag.

Without the CLI, clone the tag and copy folders as in [Or copy by hand](#or-copy-by-hand):

```bash
git clone --branch v1.0.0 --depth 1 https://github.com/izentenosmith/skills
cp -r skills/skills/development/tdd my-project/.claude/skills/
```

### Or copy by hand

1. **Clone the repo** — it is public, so a plain `git clone` works.

   ```bash
   gh repo clone izentenosmith/skills
   # or: git clone git@github.com:izentenosmith/skills.git
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
   cp -RL skills/skills/database/dbarchitect    my-project/.claude/skills/
   cp -RL skills/skills/database/dbquery        my-project/.claude/skills/
   cp -RL skills/skills/networking/netaudit     my-project/.claude/skills/
   cp -RL skills/skills/networking/netdesign    my-project/.claude/skills/
   cp -RL skills/skills/networking/netdiagram   my-project/.claude/skills/
   cp -RL skills/skills/networking/netpropose   my-project/.claude/skills/
   cp -RL skills/skills/networking/netblueprint my-project/.claude/skills/
   cp -r  skills/skills/infrastructure/terraform my-project/.claude/skills/
   cp -r  skills/skills/infrastructure/pipelines my-project/.claude/skills/
   cp -r  skills/skills/security/threatmodel     my-project/.claude/skills/
   cp -r  skills/skills/security/appsec          my-project/.claude/skills/
   cp -r  skills/skills/security/hardening       my-project/.claude/skills/
   cp -r  skills/skills/memory/repo-memory       my-project/.claude/skills/
   ```

   **Copy the skill folder, not the category folder.** `development/`, `containers/`, `operations/`, `database/`, `networking/`, `infrastructure/`, `security/`, `review/` and `memory/` are scaffolding for reading this repo — the agent never sees them, and copying one wholesale just nests your skills a level too deep.

   Skill folders are self-contained: a reference doc several skills share is committed as a copy in each folder, so a plain `cp -r` is enough.

3. **Invoke a skill** — either let the agent trigger it when your request matches its `description`, or call it explicitly:

   ```
   /architect-deep-dive   /agent-brief      /acceptance-tests
   /tdd                   /refactor-review  /devils-advocate  /tyr-verdict
   /dockerfile            /docker-compose   /container-hardening   /container-debug   /docker-swarm
   /hotfix                /incident-fix
   /release-notes         /post-mortem      /ticket       /backlog
   /dbaudit       /dbdesign       /dbdiagram       /dbpropose       /dbbuild
   /dbarchitect   /dbquery
   /netaudit      /netdesign      /netdiagram      /netpropose      /netblueprint
   /terraform     /pipelines
   /threatmodel   /appsec         /hardening
   /repo-memory
   ```

   **repo-memory has a second step.** Installing the skill doesn't give a repo a memory. Run `/repo-memory` (or ask "add memory to this repo") once in each repository to scaffold `.memory/` and wire it into `CLAUDE.md` / `AGENTS.md`. See [memory/README.md](skills/memory/README.md#install).

Take one skill, take a family, or take them all. Every skill works on its own — `tdd` plans from scratch when there's no brief, `refactor-review` reviews any diff, `devils-advocate` tears down a change it didn't build, `post-mortem` reconstructs an incident in a system it has never seen. Where skills cross-link and the other one isn't installed, the prompt still names it, so you know what would have run.

Each family has its own README with more detail: [development](skills/development/README.md) · [containers](skills/containers/README.md) · [operations](skills/operations/README.md) · [database](skills/database/README.md) · [networking](skills/networking/README.md) · [infrastructure](skills/infrastructure/README.md) · [security](skills/security/README.md) · [review](skills/review/README.md) · [memory](skills/memory/README.md).

## Conventions

- **One skill per folder, and the folder stands alone.** Each folder contains a `SKILL.md` (the workflow) plus every reference doc it needs. **Copy any one folder into any project and it works** — no shared root docs, no reference doc outside its own folder. The only cross-folder links are the stage list and the handoff, which name the next skill; if it isn't installed, the prompt still tells you which one to run.
- **Families are scaffolding, not structure.** The family directories under `skills/` exist to make this repo readable; the agent selects on the frontmatter `description` and never sees a folder name. A family install is just a list of skill names, and no skill depends on its family's path — so families are free to reorganize, and skills are free to cross-link between them.
- **The harness is a layer, not a dependency.** `harness/` enforces the development pipeline's rules when you run it, and no skill needs it. The three checkers a stage runs on its own output (`ledger.py`, `redgreen.py`, `brief.py`) and the ledger grammar have their sources there and a committed copy in each skill folder that uses them. The grammar is the same one the skills write by hand — so a skill folder copied alone still produces a ledger the harness can check and resume.
- **No installer of its own.** Skills go into a target repo one folder at a time — by name through the external `skills` CLI, or by copying. A family command is a list of names, not a managed set that stays in sync; this is still a shelf you take things off.
- **Self-containment beats DRY here.** The dispatch contract and the seven-stage list are repeated across folders on purpose. That is real duplication with a real cost — change the pipeline's shape and you edit eight files — and it buys the thing that matters more: a folder you can paste anywhere. What the stages share word for word (`pipeline.md`, the ledger grammar) is one source with a synced copy per folder, below.
- **Every `SKILL.md` carries frontmatter** (`name`, `description`) so the agent can decide relevance.
- **Every skill carries a calibration tier and a stopping rule.** The tier says how much of the skill to run before starting; the stopping rule says when to stop, so a workflow with an open-ended quality goal terminates instead of iterating on taste.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let the agent figure out *how* against the live codebase. No hard-coded file paths or line numbers.
- **A shared reference doc has one source and committed copies.** Some docs (and `netgraph.py`) serve several skills — among them the development pipeline's `pipeline.md` (what every stage shares: where questions go, what counts as an instruction, which commands may be run) and its checkers `scripts/ledger.py`, `scripts/redgreen.py` and `scripts/brief.py` with `ledger-format.md`, whose sources are in `harness/` — and each skill folder carries its own copy, because `npx skills add` installs one folder at a time and drops any symlink that leaves it. [`skills/shared.json`](skills/shared.json) maps each source to its copies. Edit the source only, then run `python3 .github/scripts/sync_shared.py`, or install the pre-commit hook once per clone (`git config core.hooksPath .githooks`) and it syncs and stages the copies for you. CI fails if a copy drifts from its source; the script refuses to overwrite a copy that was edited directly and names the source the edit belongs in.
- **A change starts from an observed failure.** [SCOPE.md](SCOPE.md) says what gets in and what gets cut: a failure seen in a real session, no new skill where existing ones compose, a description under 500 characters and a SKILL.md body under 375 lines and 3,700 words. Ideas already turned down, and why, are in [.out-of-scope/](.out-of-scope/README.md).
- **CI checks structure, not quality.** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every PR and push to `main`, and calls no model. It checks every skill's frontmatter, that `skills/` has no symlinks and every shared copy matches its source, every relative link, and that `evals.json`, `grade.py` and the controls agree ([`check_repo.py`](.github/scripts/check_repo.py)). It also checks eval health: a skill with no eval fails, and a skill that changed since its last scored run gets a warning, found by comparing the skill's hash with the one its scored run recorded in [`evals/scores.json`](evals/scores.json) (see [Is a score still current?](evals/README.md#is-a-score-still-current)). It also runs `actionlint`, the harness unit tests on Python 3.13 and 3.14, and every eval control. Whether a skill *works* is still the job of a scored eval run. `main` is protected by the ruleset in [`.github/rulesets/main.json`](.github/rulesets/main.json), enforced by GitHub since the repo went public on 2026-11-20 (while it was private on GitHub Free the ruleset was only a record): changes arrive by pull request with all five CI checks green, no approving review is required, and nobody (admins included) can force-push or delete the branch. Auto-merge is switched off in the repo settings, so a green PR is still merged by hand. To re-apply it after editing, update the existing ruleset: `gh api -X PUT repos/izentenosmith/skills/rulesets/<id> --input .github/rulesets/main.json` (`gh api repos/izentenosmith/skills/rulesets` lists the id).

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.
