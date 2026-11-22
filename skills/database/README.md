# Database skills

Seven independently usable skills: one that decides which data stores a system needs, five that evaluate, design, diagram, propose and generate DDL for a relational database, and one that reviews the SQL it actually runs. For coordinated audit-to-build work, use [`harness/dbworkflow.py`](../../harness/dbworkflow.py); the harness lives in `harness/`, calls the five schema skills, and runs neither dbarchitect nor dbquery.

```text
Which stores, which flows:    dbarchitect → one dbdesign per relational system of record
Existing database: dbaudit → dbdesign → dbdiagram → dbpropose
New database:                dbdesign → dbdiagram → dbpropose
Accepted proposal:                                      dbbuild
Running workload:  dbquery — settles dbaudit's needs-data flags; index changes → dbpropose
```

| Skill | Purpose |
|---|---|
| [dbarchitect](dbarchitect/SKILL.md) | Decide the data stores and the dataflow: system of record per fact, derived stores fed by CDC or an outbox, data model per store, replication, partitioning and the consistency each workflow needs. Decision records and a dataflow map; Review mode grades an existing architecture against A1–A12. |
| [dbaudit](dbaudit/SKILL.md) | Evidence-based assessment of an existing database, with findings, strengths, weaknesses, improvements, and a reproducible 0–10 score. |
| [dbdesign](dbdesign/SKILL.md) | Design a new database or redesign an audited one: a requirements dossier and business-rule catalogue, a Barker conceptual model, functional dependencies, keys and the normal form of each relation, every rule mapped to the mechanism that enforces it, and DDL that runs as written (tested in an in-memory SQLite database when SQLite is the target). |
| [dbdiagram](dbdiagram/SKILL.md) | Produce editable draw.io ER (Barker) and relational models from a design or database structure, with semantic cell IDs, UID bars, alternate keys and inferred semantics labelled. |
| [dbpropose](dbpropose/SKILL.md) | Turn the audit, the design and its diagrams into `proposal/proposal.md`: a decision register citing audit findings, breaking changes planned as expand → migrate consumers → contract, and a migration sequence whose every step names its validation, rollback and blast radius. Nothing is applied before acceptance. |
| [dbbuild](dbbuild/SKILL.md) | After explicit proposal acceptance, generate reviewable DDL from the approved design; stops on an unaccepted proposal, mismatched inputs or an open structural decision. PostgreSQL and SQLite targets. |
| [dbquery](dbquery/SKILL.md) | Review query text, execution plans and workload statistics: rank statements by total time, read plans by access vs filter predicates and estimated vs actual rows, find wrong results, races and injection, and prescribe rewrites and index changes weighed against write cost. Scored 0–10 with dbaudit's formula. |

## Install

All seven, from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill dbarchitect dbaudit dbdesign dbdiagram dbpropose dbbuild dbquery
```

Or one at a time:

| Skill | Install |
|---|---|
| dbarchitect | `npx skills add izentenosmith/skills --skill dbarchitect` |
| dbaudit | `npx skills add izentenosmith/skills --skill dbaudit` |
| dbdesign | `npx skills add izentenosmith/skills --skill dbdesign` |
| dbdiagram | `npx skills add izentenosmith/skills --skill dbdiagram` |
| dbpropose | `npx skills add izentenosmith/skills --skill dbpropose` |
| dbbuild | `npx skills add izentenosmith/skills --skill dbbuild` |
| dbquery | `npx skills add izentenosmith/skills --skill dbquery` |

Each installed folder is self-contained: the shared companion references are committed as copies in every skill that reads them. It installs the skills only — `harness/dbworkflow.py` needs a clone. The repo is public, so no GitHub account is needed; the flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx).

## Coordinated workflow

Run `python3 harness/dbworkflow.py --help` for the harness interface. It supports existing-database and new-database runs, plus partial runs when prerequisite artifacts are available. Existing-database runs use the audit gate: a score at or above 9.0 is necessary for a good-enough result, but open Critical or High findings, unused/copy status, or too many unresolved needs-data flags still route the database to design, diagrams, and proposal. The gate and reasons are recorded.

The conceptual ER model uses Barker notation throughout; the relational model remains in table/key notation. The harness prompts for a Barker ER page and legend and checks the canonical editable draw.io pair before proposal and DDL stages. The harness orchestrates; it does not replace skill instructions. The proposal and DDL build are separate runs: DDL generation requires an explicit accepted-proposal input. Structural iteration routes through design, diagrams, and proposal again; the revised proposal needs acceptance before its DDL is generated. A skill invoked directly remains responsible for stating its evidence, assumptions, and missing prerequisites. Diagram outputs are editable `.drawio` files for both the **Barker ER model** and the **relational model**.

## Evals

Each skill has one eval in [`evals/`](../../evals/README.md): a PostgreSQL dump to audit whose Critical is the PostgreSQL form of the multi-row trigger defect and whose config carries a password the audit must never echo (30); requirements that ask for a stored age and a "list" that is really a many-to-many, graded by executing the design's DDL in SQLite (31); one shared estate for the next three — a design to draw, graded by parsing the draw.io XML for Barker notation and an intersection entity (32), a proposal whose orphan rows must be cleaned before the constraint is added (33), and an accepted proposal whose DDL is executed and probed with rows that must be refused (34); a production workload whose costliest statement isn't the slowest, with an N+1, a non-sargable lookup, a `NOT IN` that returns nothing, a lost update, a laptop plan and a developer's index list to weigh (47); and a ticketing relaunch with two writable homes for seat state, dual writes and a MongoDB proposal with no numbers (48). Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 30 31 32 33 34 47 48`).

**Latest (2026-11-21, n=3 each against no skill, after the best-practice and security audit):**

| Eval | Skill | With skill | No skill | Iteration |
|---|---|---|---|---|
| 30 | dbaudit | 0.95 | 0.36 | 62 |
| 31 | dbdesign | 0.97 | 0.54 | 62 |
| 32 | dbdiagram | 1.00 | 0.77 | 62 |
| 33 | dbpropose | 0.97 | 0.39 | 62 |
| 34 | dbbuild | 1.00 | 0.89 | 62 |
| 47 | dbquery | 1.00 | 0.86 | 62 |
| 48 | dbarchitect | 1.00 | 0.73 | 60 |

Delta scores; capability is 1.00 for every with-skill run. The misses left are single runs on assertions that have varied before. dbbuild and dbquery gain least because a bare agent already does most of what their fixtures test; both need a harder eval, and every skill needs two more to reach three.

**Triggering** ([`evals/trigger/`](../../evals/trigger/README.md)): six cases per skill, three that should pick it and three near-misses that belong to a neighbour. On Sonnet at three reps, every database skill fires on all its held-out should-trigger cases and never on a should-not case. On train, six of seven fire 6/6; dbdesign answers a one-table "is this in 3NF?" question directly instead (3/6). dbarchitect went from 0/6 to 6/6 when its description was rewritten to lead with when to use it.

## Companion references

A shared companion reference has one canonical file and a committed copy in each skill that reads it, listed in [`skills/shared.json`](../shared.json). Edit the canonical file, then run `python3 .github/scripts/sync_shared.py` (or let the pre-commit hook do it); CI fails if a copy drifts. Copying one skill folder by hand (`cp -r skills/database/dbdesign /target/skills/`) carries everything it needs.

| Reference | Home / use |
|---|---|
| Theory and ER modeling | Canonical files in `dbaudit/`; every other database skill carries copies of both. Used for evaluation and conceptual/logical design. |
| Scoring and detection signals | Canonical in `dbaudit/`; `dbquery/` carries copies of both — it scores with the same formula and greps the same query shapes. |
| Query rubric and plan reading | `dbquery/`; statement, plan and workload anti-patterns, and each engine's plan vocabulary. |
| Architecture rubric and store selection | `dbarchitect/`; A1–A12 and the model, engine, replication, consistency, partitioning and integration trade-offs. |
| Scoring, audit lenses, object rubrics, detection signals | `dbaudit/`; audit-only guidance. |
| Physical design | Canonical file in `dbdesign/`; `dbpropose/` carries a copy for proposal decisions and `dbbuild/` one for the DDL it realizes. |
| Requirements dossier | `dbdesign/requirements.md`; the rule catalogue, data dictionary and access matrix the design starts from. |
| Diagram conventions | `dbdiagram/`; notation, provenance, and XML validation. |
| Proposal rules and templates | Canonical file in `dbpropose/`; `dbbuild/` carries a copy for the proposal structure and its lock-safe migration forms. |
