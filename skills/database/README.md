# database

Two skills for the database underneath everything else: grade it, then decide what to do with it.

```
dbaudit  →  dbpropose
 (grade)    (decide + design)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [dbaudit](dbaudit/SKILL.md) | Grades DDL — tables, indexes, views, procedures, triggers — against relational theory and ER-modelling rules, with a repeatable 0–10 formula, severity caps and ✅/⚠️/🔬 confidence tags. Produces per-file evaluations, per-database summaries and an estate synthesis with a cross-database coupling edge list. Evaluates and stops. |
| [dbpropose](dbpropose/SKILL.md) | Turns an audit into decisions: a reuse / refactor / rework / rebuild / drop verdict per object on structure, data and logic, a topology derived from real coupling, and either a modelled target schema (ER model → Table Instance Diagrams → PostgreSQL 18 DDL) with a migration plan, or an ordered in-place remediation register. Also designs or reviews a model from requirements. |

## How to use them

**Copy the folders you want into the repo you're working in**, alongside wherever that repo keeps its
agent skills. Each folder is self-contained — `SKILL.md` plus every reference doc it needs — so one
folder is a complete install of one skill.

```
/dbaudit   /dbpropose
```

**`dbaudit` needs DDL text** — dumps per object type (`tables.sql`, `procedures.sql`, …), a migrations
folder, or an export you produced. It reads; it never connects to or alters a database unless you tell
it to, and then read-only.

**`dbpropose` needs an audit** for any legacy database. Without one it says so and sends you to
`dbaudit`; the only modes that run without an audit are *design* (a new model from requirements) and
*design review* (someone else's model or schema).

## Why two skills

The split is the same boundary `post-mortem` keeps in `operations`: **an evaluation that also
prescribes has an incentive to shape its findings toward the prescription.** `dbaudit` reports
evidence, theory and a number; `dbpropose` makes the decisions and has to cite that evidence for each
one. Between them sit the files that let anyone re-check the chain — the per-file evaluations, with
line references, scores and their arithmetic.

Both keep the same scope discipline: anything that needs a live instance — row counts, index usage,
plans, whether a schema is still used — is a 🔬 needs-data flag. `dbaudit` never scores it;
`dbpropose` carries it as an open question rather than answering it by assumption.

## Shared material, duplicated on purpose

`theory.md` and `er-modeling.md` are byte-identical copies in both folders, so either can be copied
alone. Edit them together.

## Reference docs

| Doc | In | What it covers |
|-----|----|----------------|
| [theory](dbaudit/theory.md) | both | integrity, functional dependencies, normal forms, ACID, SSOT, ER vocabulary, literature (Codd; Connolly & Begg; Elmasri & Navathe; Barker; Winand) |
| [er-modeling](dbaudit/er-modeling.md) | both | CAP1–CAP4: entities, relationships, attributes, UIDs; normalization, recursion, roles, subtypes, arcs, history; ER → relational mapping and TIDs; reverse-engineering a legacy schema; 25 drills |
| [scoring](dbaudit/scoring.md) | dbaudit | severity taxonomy, confidence tags, the 0–10 formula, triage, output templates |
| [audit-lenses](dbaudit/audit-lenses.md) | dbaudit | dead/copy schemas, cross-database coupling, dark data, logic drift, security |
| [tables](dbaudit/tables.md) · [indexes](dbaudit/indexes.md) · [views](dbaudit/views.md) · [procedures](dbaudit/procedures.md) · [triggers](dbaudit/triggers.md) | dbaudit | per-object-type rubric: well done, anti-patterns, checklist |
| [detection-signals](dbaudit/detection-signals.md) | dbaudit | grep/regex per anti-pattern, confidence tag, engine notes |
| [proposal](dbpropose/proposal.md) | dbpropose | input contract, verdict rules, topology, translation table, migration plan, remediation register, `target-schema.md` skeleton |
| [physical-design](dbpropose/physical-design.md) | dbpropose | PostgreSQL 18 standard: keys, naming, integrity, arcs/subtypes/temporal keys, types, indexes, collation, where logic lives |

## Not measured

Neither skill has an eval fixture yet.
