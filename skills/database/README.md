# Database skills

Five independently usable skills for evaluating, designing, diagramming, proposing, and generating DDL for relational databases. For coordinated work, use [`harness/dbworkflow.py`](../../harness/dbworkflow.py); the harness lives in `harness/` and calls the skills here.

```text
Existing database: dbaudit → dbdesign → dbdiagram → dbpropose
New database:                dbdesign → dbdiagram → dbpropose
Accepted proposal:                                      dbbuild
```

| Skill | Purpose |
|---|---|
| [dbaudit](dbaudit/SKILL.md) | Evidence-based assessment of an existing database, with findings, strengths, weaknesses, improvements, and a reproducible 0–10 score. |
| [dbdesign](dbdesign/SKILL.md) | Design a new database or revise an audited one using relational theory, Codd’s rules, normal forms, and the companion references. |
| [dbdiagram](dbdiagram/SKILL.md) | Produce editable draw.io ER and relational models from a design or database structure. |
| [dbpropose](dbpropose/SKILL.md) | Assemble the recommendation, incorporating audit evidence, design decisions, and diagrams. |
| [dbbuild](dbbuild/SKILL.md) | After explicit proposal acceptance, generate reviewable DDL from the approved design. |

## Install

All five, from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill dbaudit dbdesign dbdiagram dbpropose dbbuild
```

Or one at a time:

| Skill | Install |
|---|---|
| dbaudit | `npx skills add izentenosmith/skills --skill dbaudit` |
| dbdesign | `npx skills add izentenosmith/skills --skill dbdesign` |
| dbdiagram | `npx skills add izentenosmith/skills --skill dbdiagram` |
| dbpropose | `npx skills add izentenosmith/skills --skill dbpropose` |
| dbbuild | `npx skills add izentenosmith/skills --skill dbbuild` |

The installer dereferences the companion-reference symlinks, so each installed folder is self-contained. It installs the skills only — `harness/dbworkflow.py` needs a clone. Flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx).

## Coordinated workflow

Run `python3 harness/dbworkflow.py --help` for the harness interface. It supports existing-database and new-database runs, plus partial runs when prerequisite artifacts are available. Existing-database runs use the audit gate: a score at or above 9.0 is necessary for a good-enough result, but open Critical or High findings, unused/copy status, or too many unresolved needs-data flags still route the database to design, diagrams, and proposal. The gate and reasons are recorded.

The conceptual ER model uses Barker notation throughout; the relational model remains in table/key notation. The harness prompts for a Barker ER page and legend and checks the canonical editable draw.io pair before proposal and DDL stages. The harness orchestrates; it does not replace skill instructions. The proposal and DDL build are separate runs: DDL generation requires an explicit accepted-proposal input. Structural iteration routes through design, diagrams, and proposal again; the revised proposal needs acceptance before its DDL is generated. A skill invoked directly remains responsible for stating its evidence, assumptions, and missing prerequisites. Diagram outputs are editable `.drawio` files for both the **modelo entidad relación** and **modelo relacional**.

## Evals

Each skill has one eval in [`evals/`](../../evals/README.md) (evals 30–34): a PostgreSQL dump to audit whose Critical is the PostgreSQL form of the multi-row trigger defect and whose config carries a password the audit must never echo; requirements that ask for a stored age and a "list" that is really a many-to-many, graded by executing the design's DDL in SQLite; and one shared estate for the last three — a design to draw (graded by parsing the draw.io XML for Barker notation and an intersection entity), a proposal whose orphan rows must be cleaned before the constraint is added, and an accepted proposal whose DDL is executed and probed with rows that must be refused. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 30 31 32 33 34`). **First runs (n=1), against no skill:** dbaudit 0.86 vs 0.36, dbdiagram 0.83 vs 0.75, dbbuild 1.00 vs 0.78. After fixes, re-run three times: dbdesign 0.95 vs 0.54 (DDL that runs as written; most of its first 0.69 was grader false negatives, now fixed) and dbpropose 0.90 vs 0.46 (a `proposal.md` file, a step table with validation, rollback and blast radius, data cleanup before constraints, expand/contract, acceptance before dbbuild).

## Companion references

Shared companion references use relative symlinks to one canonical copy in this skill tree. When installing a single skill folder outside this repository, dereference its links during copy (for example, `cp -RL skills/database/dbdesign /target/skills/`).

| Reference | Home / use |
|---|---|
| Theory and ER modeling | Canonical files in `dbaudit/`; `dbdesign/`, `dbdiagram/`, and `dbpropose/` link to them. Used for evaluation and conceptual/logical design. |
| Scoring, audit lenses, object rubrics, detection signals | `dbaudit/`; audit-only guidance. |
| Physical design | Canonical file in `dbdesign/`; `dbpropose/` links to it for proposal decisions. |
| Diagram conventions | `dbdiagram/`; notation, provenance, and XML validation. |
| Proposal rules and templates | `dbpropose/`; recommendations and implementation planning. |
