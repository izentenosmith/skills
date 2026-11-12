# harness — the rules the skills state, run by code

Eight harnesses and the tools they share. Each one runs a skill's judgment through headless `claude -p` calls and enforces in code everything that isn't judgment.

| Harness | Runs | Returns |
|---|---|---|
| [`pipeline.py`](pipeline.py) | development stages 2–7, from the design architect-deep-dive wrote | a branch of commits, the brief, the ledger, a GO / ESCALATED verdict and a report |
| [`loop.py`](loop.py) | development stages 5–7 and the fix loop | a GO / NO-GO / ESCALATED ledger |
| [`fix.py`](fix.py) | the hotfix lane, or incident-fix's fix phase | a committed branch and, with `--open-pr`, a draft PR |
| [`postmortem.py`](postmortem.py) | incident-fix's Phase 4 | a linted, blameless post-mortem and an owned follow-through |
| [`dbworkflow.py`](dbworkflow.py) | coordinates existing/new database workflows across the database skills | audit gate, design, Barker ER and relational diagrams, proposal, and acceptance-gated DDL artifacts |
| [`dbreview.py`](dbreview.py) | dbaudit's read-only audit and score gate | scored audit files, synthesis, and gate decision; usable directly |
| [`networkflow.py`](networkflow.py) | coordinates existing/new network workflows across the networking skills | audit gate, design + target topology, canonical draw.io views, proposal, and an acceptance-gated blueprint |
| [`netreview.py`](netreview.py) | netaudit's read-only audit, graph analysis and gate | redacted evidence, recovered topology, graph results, scored domains, synthesis, gate decision |
| [`prreview.py`](prreview.py) | one pull request through every `review` skill — pr-prep, code-xray, peer-review, test-review, concurrency-review, appsec, review-retro | a report with a computed recommendation, findings, a COMMENT-review payload; re-review rounds; a PR record, metrics and proposals |

## The closing loop — `loop.py`

The `development` skills describe a loop with hard rules: the teardown never runs the suite, every finding is adjudicated, a refuted finding stays refuted, an INCONCLUSIVE goes back for evidence once, three iterations at most, and the verdict follows from what's still open. In the skills those rules are prose that the agent is asked to follow — the model is both the worker and the referee.

This folder makes the referee a program. The model still does every judgment; the harness owns everything that isn't judgment.

```
                       ┌──────────── iteration n (≤ 3) ─────────────┐
 tdd (stages 1–4,  ──► │ refactor-review → devils-advocate → tyr    │ ──► GO        exit 0
 by hand, as now)      │      gate          3–9 read-only    verdict│ ──► ESCALATED exit 3
                       │    green/green     delegates + rank  + one │
                       │                    verifier per finding    │
                       └───────────── NO-GO: tdd on the slices ─────┘
```

| File | What it is |
|---|---|
| [`loop.py`](loop.py) | The orchestrator. Drives stages 5–7 and the loop back through tdd with headless `claude -p` calls. |
| [`ledger.py`](ledger.py) | The ledger's grammar as code: parser, checker, verdict arithmetic, and the only writer `loop.py` uses. Works on its own against a ledger the skills wrote by hand. |
| [`LEDGER.md`](LEDGER.md) | The grammar and the rules, for people. |
| [`redgreen.py`](redgreen.py) | Proves new tests were **red on the pre-fix code** and are green with the fix, for any language. `loop.py` uses it before closing a remediation slice; hotfix, tdd and incident-fix can call it directly. |
| [`incident.py`](incident.py) | The incident-fix log: entries stamped from the system clock, production actions refused without their own confirmation, a closing gate on contributing factors, and a timeline for the post-mortem. |
| [`fix.py`](fix.py) | Bug report → pull request. Discover, triage, root cause, red, fix, review, ship, each gated; `--profile incident` runs the full loop capped at two and adds a data-repair artifact. |
| [`postmortem.py`](postmortem.py) | Resolved incident log → post-mortem. Widens the git range, lints for blame and prescription, drafts the follow-through and waits for owners. |
| [`dbworkflow.py`](dbworkflow.py) | existing database → audit and gate → design → diagrams → proposal; new database → design → diagrams → proposal; accepted proposal → DDL in a separate run. |
| [`dbreview.py`](dbreview.py) | DDL or a read-only connection → audit, scored by formula in code → a per-database gate. |
| [`networkflow.py`](networkflow.py) | existing network → audit and gate → design → diagrams → proposal; new network → design → diagrams → proposal; accepted proposal → blueprint in a separate run. |
| [`netreview.py`](netreview.py) | network evidence → redaction → audit and recovered `topology.json` → graph metrics, scored by formula in code → a per-network gate. |
| [`netgraph.py`](netgraph.py) | `topology.json` → components, articulation points, bridges, Menger connectivity per critical pair, betweenness, robustness curves, CIDR overlap and flow exposure; `.drawio` views → the conventions cross-check. A symlink to [`skills/networking/netaudit/scripts/netgraph.py`](../skills/networking/netaudit/scripts/netgraph.py): the skills ship it, so they compute the same numbers without this folder. |
| [`prreview.py`](prreview.py) | One PR → readiness, history, finders and specialists, one verifier per candidate, a gap sweep, synthesis → a report whose recommendation is computed. `--re-review` verifies the fixes; `--retro` writes the record. |
| [`tests/`](tests) | `python3 -m unittest discover harness/tests` — the grammar, the rules, and the whole loop against a stub `claude`. |

Stdlib Python 3.10+, no dependencies. The skills don't need any of this — every skill folder still works copied on its own, in Cursor or Claude Code. The harness is an optional layer that enforces what they ask for when you want it enforced.

## The whole pipeline — `pipeline.py`

`loop.py` starts where tdd ends. `pipeline.py` starts where **you** end: you work the design with architect-deep-dive, in conversation, and it writes the design to its own file, `.workflow/designs/<YYYYMMDD-HHMM>-<slug>.md`. Everything after that runs without you.

```
 architect-deep-dive ──► .workflow/designs/… ──► agent-brief ─► acceptance-tests ─► tdd ─► loop.py ──► GO        exit 0
 (you, one question       Status: resolved        brief.md       red, on behavior    green,   stages 5–7  ESCALATED exit 3
  at a time)                                                                         committed
```

```bash
python3 path/to/skills/harness/pipeline.py --repo . --design .workflow/designs/20261112-1105-cutoff.md \
    --test-cmd ".venv/bin/python -m pytest -q"
```

**One file per design, nothing shared.** A repo holds several designs at once — parallel sessions, worktrees, branches that will merge — so each has a name made of when and what, and none overwrites or conflicts with another. `--design` picks the one to build; with a single `resolved` design in the folder it is found without being named, with several the harness lists them and asks, and it is remembered for the resume. On **GO** the design is marked `built` and the change's working files — brief, ledger, report, state — move to `.workflow/archive/<design name>/`, so the shared `brief.md` and `ledger.md` paths are empty again and two branches that each built something never meet in the same file. An ESCALATED change stays where it is, to be resumed.

Stage 1 stays a conversation on purpose: a design is decided with you, and a headless call can't ask you anything. The harness refuses a design that isn't `**Status:** resolved`.

| Stage | What the model does | What code checks |
|---|---|---|
| before anything | — | a resolved design; no brief or ledger left from other work; a clean tree; a green suite; a working branch (created as `pipeline/<slug>` when you start on the default branch) |
| brief | **agent-brief**, from the design file | nothing outside `.workflow/` changed; the brief has criteria. The assumptions it had to make are logged and put in the report. Status becomes `approved — from the resolved design … (no separate review)` |
| acceptance | **acceptance-tests** | a `**Command:**` is recorded; it is **red**; no line of its output is a load or import error |
| build | **tdd**, committing each green slice | suite and acceptance tests green, or tdd is called again with what is still red (`--build-attempts`, default 2); `**Base:**` written into the brief before the first slice; anything left uncommitted becomes one commit |
| loop | `loop.py`, unchanged, with save points | everything in the table below |

| Flag | |
|---|---|
| `--pause-at-brief` | stop once after the brief is written (exit 5) so you can read or edit it; re-run without the flag to build it |
| `--from-brief` | no design: build the `.workflow/brief.md` that is already there |
| `--skip-acceptance` | the Trivial tier: no stage 3 |
| `--design` | the design file to build (default: the only resolved one in `.workflow/designs/`) |
| `--branch`, `--build-attempts` | the working branch's name, tdd calls before giving up |
| `--dry-run` | write the next stage's prompt and call nothing |

The model, budget, cap and concurrency flags are `loop.py`'s. State is `.workflow/pipeline.json`: re-running resumes at the first stage not done, and once the loop has started the ledger is the state, as before. It ends with `pipeline-report.md` (in the archive folder on GO, in `.workflow/` otherwise) — the verdict, the commits, what was assumed for you, and the ship-checklist items still open. Nothing is pushed, merged or deployed. Exit 5 means it needs you: no resolved design, a brief that belongs to other work, a dirty tree, or the pause you asked for.

**What you give up by not pausing.** The brief's approval gate exists because the brief is the last cheap place to change your mind. Running straight through treats the design conversation as that approval, and the brief says so rather than looking reviewed. Use `--pause-at-brief` when the design left real latitude.

## What moved from prose into code

| Rule the skills state | Who enforces it now |
|---|---|
| devils-advocate fans out by attack surface, never below three delegates, all at once | `loop.py` dispatches 3 grouped delegates (10 on a diff over 400 changed lines) in parallel |
| The teardown reads the diff for **the bar itself** moving — a skipped or deleted test, a suppressed checker, a lowered threshold, unfinished work | `bar_signals()` scans the diff for those patterns and hands each hit to the delegate that owns the surface, as a lead to read (saved as `bar-i<n>.json`). Whether a hit is a finding stays the model's call; a loosened assertion or an edited acceptance test is still its to spot |
| The change is measured against the commit tdd started from, not against `HEAD` | `--base`, else the remembered base, else the brief's `**Base:**` line, else the merge-base with `main`. `HEAD` is pinned to a commit on first use, and a tree that doesn't differ from its base **stops the loop** instead of producing a clean teardown of nothing |
| Every green state is a save point | With `--save-points`, one commit after each tdd and refactor-review stage that passes its gates. The stages are told not to commit; the harness does it, and only on a working branch that started clean |
| A GO names the ship-checklist items still open | Read from the brief at GO and written into the verdict's reason. They never change the verdict |
| The teardown **does not execute** — no suite, no test, no mutation | Delegates get `--tools Read,Grep,Glob`. They *can't* run anything, rather than being asked not to |
| A delegate that never returns is an **unattacked surface**, not a clean one | Recorded under `### Surfaces` by the harness |
| A teardown nobody ran found nothing, which is not the same as a clean one | When **no** delegate returns, the loop stops with an error and writes nothing, so the next run retries the teardown — "no findings" from a teardown that never happened used to compute GO |
| tyr verifies each finding with a reproduction; verifiers don't fix | One verifier per finding, each in a throwaway copy of the repo |
| Collect every verifier before judging | `fan_out` waits on all of them; tyr's call is made once, on the whole slate |
| The suite is green before and after refactor-review, and after tdd | `--test-cmd` is run as a gate; red stops the loop (exit 4) |
| The ledger is append-only and only the running stage writes it | Agents never write it. The harness snapshots it, restores it if an agent edits it anyway, and appends through `ledger.render_*` |
| Every CONFIRMED gets a slice; REFUTED carries *Reopens only if*; INCONCLUSIVE carries what settles it | Validated on tyr's answer; one correction round, then the harness stops |
| A slice closes when its test exists | The tests tdd added are run against a snapshot of the pre-fix code (`redgreen.py`): if they pass there, or fail only because they can't load (an import or compile error), they don't capture the defect and **no slice closes**. Each test name tdd reports must also be found in the repo |
| One closing line per slice | A slice tdd reports more than once (once per test that verifies it) closes once, naming every test; two closing lines for one slice are a ledger error |
| Every carried smell is re-examined each pass | Missing decisions are recorded as "left, not re-examined" and logged |
| GO / NO-GO / ESCALATED, the three-iteration cap, the stall rule, one re-run per INCONCLUSIVE | `ledger.judge()` computes it. tyr states a verdict too; if they disagree the ledger records both and the computed one stands |

What stays with the model: which smells to fix, what's a defect, how severe, whether evidence holds, what each slice must make true. What stays with you: stage 1 — and stages 2–4 too, unless you run `pipeline.py` — and any ESCALATED decision.

## Running it

From a repo where stage 4 (tdd) has finished and the suite is green:

```bash
python3 path/to/skills/harness/loop.py --repo . --test-cmd ".venv/bin/python -m pytest -q"
```

The first run remembers `--test-cmd` and `--base` in `.workflow/harness.json`, so later runs are just `--repo .`. The **ledger is the state**: stop it any time — Ctrl-C, a red gate, a crash — and the next run picks up at the first stage the ledger doesn't show as done.

| Flag | Default | |
|---|---|---|
| `--base` | the brief's `**Base:**`, else the merge-base with `main` | what the diff is measured against; `HEAD` (pinned to its commit) when you're on the base branch itself with the change uncommitted |
| `--skills` | `../skills` next to this folder | where the `SKILL.md` folders are; the repo's `.claude/skills` is searched too |
| `--model`, `--delegate-model` | your Claude default | e.g. a stronger model for the stages that judge or write code, a cheaper one for delegates |
| `--concurrency` | 4 | parallel delegate calls |
| `--budget-usd` | none | spend cap per `claude` call |
| `--cap` | 3 | iterations |
| `--acceptance-cmd` | the **Command** stage 3 recorded in the brief | runs only the acceptance tests; every gate requires them green too (remembered) |
| `--save-points` | off | commit after each tdd and refactor-review stage that passes its gates. Refuses the default branch, a detached `HEAD` and a tree with uncommitted changes outside `.workflow/` — run it once tdd's slices are committed |
| `--once` | | run one stage and stop — to watch it step by step |
| `--dry-run` | | write the next stage's prompts to `.workflow/runs/…/calls/` and call nothing |

Each run leaves its prompts, raw model output and the diff each teardown saw in `.workflow/runs/<timestamp>/`. Ignore `.workflow/runs/` in the host repo; `ledger.md`, `brief.md` and `harness.json` are worth keeping if you commit `.workflow/` at all.

### When it stops

- **GO** (exit 0) — nothing open. Minors ship as tracked follow-ups; carried smells and any open **Ship checklist** items from the brief are named in the verdict's reason.
- **ESCALATED** (exit 3) — the decision has left the loop. Read the last `### Verdict` reason, then either fix by hand, take it back to agent-brief / architect-deep-dive, or accept the risk: append to the last iteration

  ```markdown
  ### Decisions
  - **F4** — waived: <why you accept it>
  ```

  and run `ledger.py check` — a waived finding stops counting as open.
- **Gate failed** (exit 4) — the suite was red where it had to be green. Nothing was recorded for that stage, so fixing the suite and re-running resumes at the same stage.
- **Error** (exit 1) — a malformed answer that survived its correction round, an unreadable ledger, a timeout. The message names it; the call's prompt and output are in the run folder.

### Without the orchestrator

The checker is useful on its own, against a ledger the skills wrote by hand:

```bash
python3 harness/ledger.py check  .workflow/ledger.md            # grammar + every loop rule
python3 harness/ledger.py check  .workflow/ledger.md --against old-ledger.md   # + append-only
python3 harness/ledger.py status .workflow/ledger.md            # computed verdict, what's open, next stage
```

### Proving a test red — `redgreen.py`

A test written alongside its fix can pass for the wrong reason. The only proof it captures the bug is running it against the code without the fix:

```bash
python3 harness/redgreen.py check --repo . --cmd "<test command>"            # test + fix uncommitted, base = HEAD
python3 harness/redgreen.py check --repo . --cmd "<cmd>" --base HEAD~1       # fix already committed
python3 harness/redgreen.py snapshot --repo .                                # pin "before" when the tree is already dirty
python3 harness/redgreen.py check --repo . --cmd "pytest {tests}" --expect "AssertionError"   # focused, and failing for the right reason
```

It checks out the base in a temporary worktree, copies in only the test files that changed (found by path shape across ecosystems, or given with `--tests`), runs the command there — it must **fail** — and runs it again in your tree, where it must **pass**. Your index and working tree are never touched. Verdicts: `red-green`, `not-red` (the test passes without the fix), `not-green`, `wrong-reason`, `no-tests`. `wrong-reason` means the before-run failed without testing the behavior: it doesn't match `--expect`, or — with no `--expect`, which is how `loop.py` calls it — the tests never ran because they couldn't be collected, imported, compiled or linked (pytest collection errors, `ImportError`, javac `cannot find symbol`, Node `Cannot find module`, `error TS…`, Go `[build failed]`, and so on). A test that imports a symbol the fix adds is red before the fix whether or not the behavior was ever broken; reach the new code through something that already exists, or pass `--expect` when the missing import *is* the bug.

### Keeping the incident log — `incident.py`

```bash
python3 harness/incident.py new docs/incidents/2026-10-15-checkout.md --title "checkout 5xx" --severity SEV2 \
    --why "30% of checkouts failing" --detected-by "alert — checkout-5xx-rate"
python3 harness/incident.py log  <log> proposed "disable flag new-pricing — undo in 30 s"
python3 harness/incident.py log  <log> confirmed "user approved: disable new-pricing"
python3 harness/incident.py log  <log> "action[prod]" "ops/flags set new-pricing off"
python3 harness/incident.py log  <log> impact-start "first 5xx in the logs" --at 2026-10-15T14:07:02Z
python3 harness/incident.py factor <log> "no canary for flag rollouts" --follow-up "flag rollouts start at 1%" --owner platform --due 2026-11-01
python3 harness/incident.py check <log>
python3 harness/incident.py timeline <log>      # the post-mortem's spine, with time to detect / mitigate / resolve
```

Every time comes from the system clock except backfilled `impact-start` and `change` entries. `log` **refuses** a production action with no `confirmed` entry of its own since the last one, and refuses `closed` while any contributing factor lacks an owner and date or an accepted-risk reason — or while a human-detected incident has no follow-up for the missing alert. The format is the one in the incident-fix skill's `incident-log.md`, so a log written by hand checks the same way.

## Bug report → PR — `fix.py`

```bash
python3 harness/fix.py --repo . --report "invoice totals are a cent low on discounted items"
python3 harness/fix.py --repo . --report @report.md --open-pr                   # push + open a DRAFT PR
python3 harness/fix.py --repo . --report @incident.md --profile incident --incident-log docs/incidents/x.md
```

| Stage | What the model does | What code checks |
|---|---|---|
| discover | the discovery checklist → `.workflow/env.md` | reuses the profile while its recorded commit and sources are unchanged; no test command → exit 5 with one question file |
| triage | hotfix, incident or design; strict or not | anything but hotfix → exit 6, nothing touched |
| root cause | the three-line note and the caller sweep | **no file changed**; a caller needing different behavior → exit 6 (design) |
| red | the failing test, nothing else | only test files changed; the test fails on the unfixed code |
| fix | the minimal fix at the shared place | suite and every discovered lint command green; `redgreen` proves red→green against a snapshot of the pre-fix tree |
| review | hotfix: one devils-advocate + tyr-verdict pass; incident: the full loop, cap 2 | hotfix fixes blockers (and majors when strict) **once**, red→green; the rest become follow-ups; what can't be fixed → exit 3, leave the lane |
| repair | incident profile, when data was written wrong: the repair artifact | the artifact exists and the suite (with its test) is green — it is **never run** |
| ship | — | a branch off the default branch, a commit of declared files only, the record as PR body; with `--open-pr`, push and a **draft** PR through `gh`, `glab` or `az repos`, picked from the remote |

State lives in `.workflow/<profile>-<slug>/` — re-running resumes at the first stage not done. With `--incident-log`, findings, the red→green proof and the commit are logged through `incident.py`, and the log gets its own commit. Nothing is ever merged or deployed.

Exit: 0 ready (or PR opened) · 1 error · 3 leave the lane · 4 gate failed · 5 needs your input · 6 routed out.

## Resolved incident → post-mortem — `postmortem.py`

```bash
python3 harness/postmortem.py --repo . --log docs/incidents/2026-10-15-checkout.md --docs docs/incidents/checkout/
# record each factor's owner and date (or accepted risk) with incident.py factor, then:
python3 harness/postmortem.py --repo . --log docs/incidents/2026-10-15-checkout.md --close [--create-items]
```

1. The log must check and be **resolved**; otherwise nothing is written.
2. The git range opens **14 days before** the earliest change, impact or detection, and one day past resolution — the trigger is often older than the outage.
3. The post-mortem skill (or incident-fix's fallback template) writes the record from the log's timeline, the range and the documents.
4. The record is **linted**: counterfactuals and "human error", prescription ("we need to", action items), any git author's name next to a failure word, and the required sections. Blockquoted source text is exempt. One correction round, then exit 4.
5. The follow-through is drafted as proposed outcomes with the exact `incident.py factor` command for each — **owners and dates are never invented**. Until every factor is recorded, exit 5.
6. `--close` logs `closed` through `incident.py` (which re-checks every closing rule); `--create-items` opens one tracker item per follow-up with the remote's CLI.

## Database workflow — `dbworkflow.py`

The coordinator lives here in `harness/`; the five independently usable skills and their references live in `skills/database/`.

```bash
python3 harness/dbworkflow.py --mode existing --ddl sales=db/sales/ --ddl hr=db/hr.sql --out review/
python3 harness/dbworkflow.py --mode new --requirements docs/order-domain.md --out design-review/
python3 harness/dbworkflow.py --mode new --requirements docs/order-domain.md --stages design,diagram --out design-review/
python3 harness/dbworkflow.py --mode new --stages build \
  --proposal-input design-review/proposal/proposal.md --proposal-accepted \
  --design-input design-review/design/design.md --out design-review/
```

Stages are `audit,design,diagram,propose,build`. A new database skips audit. An existing database runs the read-only `dbreview.py` audit first; a passing gate ends the default workflow without redesign artifacts, while an open gate routes the database into design, diagrams, and proposal. The harness never builds DDL in the same run that creates a proposal: proposal review and acceptance happen first, then a separate `build` run requires `--proposal-input`, `--proposal-accepted`, and the approved diagram pair. An explicit `--stages` list supports partial work, and stages that need prior artifacts stop with a clear missing-input message. Use `--audit-input`, `--design-input`, `--proposal-input`, and repeat `--diagram-input` once for each approved diagram to continue from artifacts produced elsewhere.

Outputs are written under `--out`: `audit/`, `design/`, `diagrams/` (Barker ER and relational `.drawio` files), `proposal/`, `ddl/` (ordered `.sql` files), plus `gate.md` and `workflow.json` as applicable. The harness requires canonical `er-model.drawio` and `relational-model.drawio` files and checks that the ER page is identified as Barker and includes a visible notation legend before proposal/build. Structural iteration goes back through design, diagrams, and proposal; the revised proposal must be accepted before its DDL is generated. Formatting or naming-only DDL changes can be iterated without changing the approved structure.

### Audit-only scoring and gate — `dbreview.py`

```bash
python3 harness/dbreview.py --ddl sales=db/sales/ --ddl hr=db/hr.sql --out audit-review/ --audit-only
SALES_DB_URL=postgresql://reader@db/sales python3 harness/dbreview.py --dsn-env SALES_DB_URL --out audit-review/ --audit-only
```

- **Acquisition is read-only.** A connection string is read from the environment variable you name — never from the command line — and used only to dump the schema: `pg_dump --schema-only` in a read-only transaction, `mysqldump --no-data` with the password in the environment, SQLite opened `mode=ro`. SQL Server: export the DDL and pass `--ddl`. The connection string appears in no log or output file.
- **One read-only audit agent per database** reports, per criterion, how many in-scope objects satisfy it, plus findings with severity and confidence. **The harness computes the score** — p per criterion, 🟢2 / 🟡1 / 🔴0, the base, the Critical (2.0) and High (6.0) caps, object-weighted database and estate means — and writes the arithmetic into every evaluation. 🔬 needs-data never moves a score; a ⚠️ proxy alone never grades 🔴.
- **The gate, per database.** Passing requires a capped score ≥ `--good-enough` (9.0 by default), no open Critical or High finding, usage other than unused/copy, and 🔬 flags no more than `--max-flag-ratio` (10%) of objects. The coordinator records the reasons either way. Migration intent routes every database to design/proposal.
- **dbreview.py** is the audit-stage harness. `dbworkflow.py` invokes it with `--audit-only`, then runs `dbdesign`, `dbdiagram`, and `dbpropose` only where the gate/workflow calls for them. The separate `build` stage calls `dbbuild` only after explicit proposal acceptance; it creates SQL files and never applies them.

## Network workflow — `networkflow.py`

The coordinator lives here in `harness/`. The five independently usable skills and their references live in `skills/networking/`.

```bash
python3 harness/networkflow.py --mode existing --evidence prod=infra/ --evidence branch=configs/branch/ --out review/
python3 harness/networkflow.py --mode new --requirements docs/landing-zone.md --out design-review/
python3 harness/networkflow.py --mode new --requirements docs/landing-zone.md --stages design,diagram --out design-review/
python3 harness/networkflow.py --mode new --stages blueprint \
  --proposal-input design-review/proposal/proposal.md --proposal-accepted \
  --design-input design-review/design/ --out design-review/
python3 harness/networkflow.py --mode new --requirements docs/landing-zone.md --out x/ --dry-run   # prompts only
```

**Stages** are `audit,design,diagram,propose,blueprint`. A new network skips audit. An existing network runs the read-only `netreview.py` audit first. A passing gate ends the default workflow, and an open gate routes the network into design, diagrams and proposal.

**Design** returns `design.md` and a target `topology.json`. It is validated, and `netgraph.py` runs on it (`design/graph.json`).

**Diagram** must return `logical-topology.drawio` and `segmentation.drawio`, plus `physical-topology.drawio` when the model has L2 links. `validate_diagram_set()` checks each one in code:
- the exact page names;
- an uncompressed `mxfile`;
- a visible legend naming *Network diagram conventions*;
- every network cell labelled with the model's CIDR;
- every non-`deco-` cell ID a `topology.json` ID;
- every zone and critical-pair endpoint drawn.

**Blueprint** never shares a run with the proposal. It requires `--proposal-input`, `--proposal-accepted` and `--design-input`, and must return `network-design.md`, an accepted `topology.json` and conforming diagrams. No stage writes IaC or touches a network.

Outputs under `--out`: `audit/`, `design/`, `diagrams/`, `proposal/`, `blueprint/`, plus `gate.md`, `gate-status.json` and `workflow.json` as applicable.

### Audit, graph and gate — `netreview.py` and `netgraph.py`

```bash
python3 harness/netreview.py --evidence prod=infra/ --evidence dc1=configs/dc1/ --out audit-review/ --audit-only
python3 harness/netgraph.py analyze audit-review/audit/prod/topology.json --md
```

- **Evidence is files you name.** Nothing connects to a device, controller or cloud API.
- **Secrets never reach a model.** Every file is copied into `--out/evidence/` with enable secrets, type-7 and cleartext passwords, SNMP communities, PSKs, key strings, private keys and secret-looking IaC values masked in place. Line numbers are preserved, so `file:line` evidence stays exact. Audit agents run inside the redacted copy. Each masked secret becomes a High finding that names its kind and weakness, never its value.
- **One read-only `netaudit` agent per network** returns per-criterion counts, findings and the recovered `topology.json`. The model must validate, with one correction round.
- **`netgraph.py` computes the structure.** It finds articulation points and bridges (with `shared_fate` groups contracted and `managed_ha` platform constructs never cut), node and edge connectivity per critical pair by unit-capacity max-flow, Brandes betweenness, hub concentration, and seeded robustness curves under random vs degree- vs betweenness-targeted removal. It checks CIDR overlap between reachable networks, subnet containment and duplicates. Its flow checks are any-any allows, internet → management ports, and zones with no default-deny. Its findings join the agent's.
- **The harness computes the score** by `dbreview.py`'s formula, per domain (addressing, segmentation, routing, services, resilience, security), then object-weighted network and estate means with the Critical (2.0) and High (6.0) caps.
- **The gate, per network.** It passes only when all of these hold:
  - the capped score is ≥ `--good-enough` (9.0);
  - no Critical or High finding is open;
  - every declared critical pair has node connectivity ≥ `--min-connectivity` (2), and a network with none declared fails;
  - 🔬 flags are ≤ `--max-flag-ratio` (10%);
  - usage is neither decommissioned nor duplicate.

  Migration intent routes every network to a proposal.

## One pull request through every review skill — `prreview.py`

The `review` skills each work alone. This runs all of them on one change and keeps every rule they state about each other.

```bash
python3 harness/prreview.py --repo . --pr 482                     # a GitHub PR through gh, read-only
python3 harness/prreview.py --repo . --base main --body @pr.md     # the current branch as the change
python3 harness/prreview.py --repo . --pr 482 --post              # + one COMMENT review on the PR
python3 harness/prreview.py --repo . --pr 482 --re-review         # after new commits: verify each finding
python3 harness/prreview.py --repo . --pr 482 --retro             # the PR record, metrics, proposals
python3 harness/prreview.py --repo . --pr 482 --dry-run           # prompts up to the finders, nothing called
```

| Stage | Who | What code checks |
|---|---|---|
| acquire | `gh`, `git` | the PR's head and base, the merge-base, the diff; **meaningful lines** leave out lockfiles, generated, vendored and minified files; PR text, linked issues and threads are kept as **untrusted data** |
| readiness | **pr-prep**, readiness mode | read-only; returns the claim, acceptance criteria, alignment, concerns, a split plan, a reading order, gaps. Not ready is recorded, never a stop |
| history | **code-xray**'s script — no model | hotspots, complexity growth on the branch, missing co-changes, clone twins, knowledge loss, suggested reviewers; a failure is a coverage note, never fatal |
| plan | code | the **tier** from size and the Deep triggers (money, auth, tenancy, personal data, crypto, migrations, concurrency, public API, a hotspot); **review units** ≤ 400 lines with tests beside their code, by risk; **routing**: test-review when code or tests changed, concurrency-review on a concurrency trigger, appsec (PR tier) on an escalation trigger. A missing specialist folds its lens back into peer-review's groups |
| find | **peer-review** lens groups + the specialists, in parallel | `Read,Grep,Glob` only. Quick is one pass (A, B, I, J, L); Standard is five groups; Deep runs the line-level groups once per unit. A finder that never returns is an **unreviewed surface** |
| verify | one fresh verifier per candidate | each in a throwaway copy of the head (`--no-exec`: read-only); REFUTED is dropped; PLAUSIBLE stays at Deep, and below Deep only when a maintainer would act on it; a verifier that never returns leaves the candidate **unverified** — in Coverage, never in Findings |
| gap | peer-review's gap sweep | Standard and Deep; up to 8 new candidates, verified the same way |
| synthesis | peer-review's main thread | every kept candidate classified exactly once (or merged into a duplicate); each comment opens with its severity label; one correction round |
| report | code | **PR-n ids**, ranking (severity, then bugs and security first), the **cap** (Quick 5 · Standard 10 · Deep 20 above nit; a blocker is never cut), and the **recommendation by report.md's rule**. The synthesis states one too; if they differ, both are written and the computed one stands |

Facts the harness computes itself become findings without a verifier, because the evidence is the computation: **instruction-like text in the PR text** (a security major — the text was fenced and never obeyed), an empty PR description, and a change over ~400 lines.

**Outputs**, in `--out` (default `<repo>/.review/<pr-n or branch>/` — ignore `.review/` in the host repo): `report.md`, `findings.json`, `comments.json` (the COMMENT review, inline where the line is in the diff), `readiness.json`, `xray.json` / `xray.md`, `plan.json`, every stage's cache, and `runs/<timestamp>/` with each call's prompt and raw output. A re-run on the same head reuses every finished stage; a new head refuses to overwrite the old review until you pass `--re-review` or `--fresh`.

**Re-review.** Every open finding gets one verifier on the new head: fixed, partly fixed, not fixed, withdrawn (with the quoted code that shows it), or deferred — and a deferral without a tracked issue is recorded as **not fixed**. The fix delta goes through the finders again; new defects take new ids, never an old one. `rereview-<sha>.md` holds the table, and `findings.json` keeps each finding's history.

**Retro.** Metrics are computed in code across every review folder in `--out` — findings per kLOC, by type, severity, lens and area, fix-verification and usefulness rates, recurring defect classes (≥ 3 times across ≥ 2 PRs is a candidate) — and never by person: no author is read. review-retro writes the record and the proposals; `proposals.md` says on its first line that nothing is applied.

**Posting** needs `--pr` and `--post`, and happens once per head as a single `COMMENT` review — never an approval or a request for changes. The recommendation is in its text; a person approves and merges.

Exit: 0 Approve or Approve with nits · 1 error · 2 usage · 3 Needs discussion · 4 Request changes — so CI can gate on it, or not.

## Trade-offs worth knowing

- **It's Claude Code only.** The skills stay portable; this layer drives `claude -p`. Calls run with `--strict-mcp-config --setting-sources project --disable-slash-commands`, so your user-level hooks, plugins and MCP servers don't load into them — that's what keeps each call's context (and bill) small.
- **Write stages and verifiers run with `acceptEdits` and Bash.** tdd and refactor-review edit your working tree, as they would by hand. Verifiers work in a copy under your temp dir, with `.venv` / `node_modules` symlinked back rather than copied.
- **The harness can't make a judgment better** — only make sure it happens, on the right inputs, and is recorded in a shape the next stage can trust.
- **Stages 1–4 are not in the loop.** architect-deep-dive is a conversation with you, acceptance-tests writes the finish line, and tdd's first pass is the build itself. The harness starts at stage 5, and only re-enters tdd for remediation slices.
