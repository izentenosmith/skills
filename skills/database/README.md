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

## Coordinated workflow

Run `python3 harness/dbworkflow.py --help` for the harness interface. It supports existing-database and new-database runs, plus partial runs when prerequisite artifacts are available. Existing-database runs use the audit gate: a score at or above 9.0 is necessary for a good-enough result, but open Critical or High findings, unused/copy status, or too many unresolved needs-data flags still route the database to design, diagrams, and proposal. The gate and reasons are recorded.

The conceptual ER model uses Barker notation throughout; the relational model remains in table/key notation. The harness prompts for a Barker ER page and legend and checks the canonical editable draw.io pair before proposal and DDL stages. The harness orchestrates; it does not replace skill instructions. The proposal and DDL build are separate runs: DDL generation requires an explicit accepted-proposal input. Structural iteration routes through design, diagrams, and proposal again; the revised proposal needs acceptance before its DDL is generated. A skill invoked directly remains responsible for stating its evidence, assumptions, and missing prerequisites. Diagram outputs are editable `.drawio` files for both the **modelo entidad relación** and **modelo relacional**.

## Companion references

Shared companion references use relative symlinks to one canonical copy in this skill tree. When installing a single skill folder outside this repository, dereference its links during copy (for example, `cp -RL skills/database/dbdesign /target/skills/`).

| Reference | Home / use |
|---|---|
| Theory and ER modeling | Canonical files in `dbaudit/`; `dbdesign/`, `dbdiagram/`, and `dbpropose/` link to them. Used for evaluation and conceptual/logical design. |
| Scoring, audit lenses, object rubrics, detection signals | `dbaudit/`; audit-only guidance. |
| Physical design | Canonical file in `dbdesign/`; `dbpropose/` links to it for proposal decisions. |
| Diagram conventions | `dbdiagram/`; notation, provenance, and XML validation. |
| Proposal rules and templates | `dbpropose/`; recommendations and implementation planning. |
