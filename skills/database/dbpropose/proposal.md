# Proposal — From Audit and Design to a Decision

This reference governs the recommendation stage. It consumes an audit and a separately reviewed design
when those artifacts apply. **Do not perform the audit, redesign the model, or redraw diagrams here.**
The companion stages are [dbaudit](../dbaudit/SKILL.md), [dbdesign](../dbdesign/SKILL.md), and
[dbdiagram](../dbdiagram/SKILL.md); their outputs remain independently reviewable.
The conceptual ER diagram must use Barker notation as defined in
[er-modeling.md](../dbaudit/er-modeling.md) and [dbdiagram](../dbdiagram/SKILL.md); keep the relational
diagram in table/key notation. Do not call a proposal complete if its ER diagram uses another notation
or is absent. Identify the mismatch and route it back through `dbdiagram`.

## Inputs and limits

For an existing database, use the per-file evaluations, per-database summary, estate synthesis when
available, `scores.json`, and `gate.md`. For a redesign or migration, also use the design document,
the **modelo entidad relación** draw.io file, and the **modelo relacional** draw.io file. For a new
database, use the requirements, design, and both diagrams. The ER diagram must use Barker notation. If a needed artifact is absent, identify the
gap and scope the proposal accordingly; never imply a missing design or diagram exists.

Treat audit findings and scores as evidence, not as a substitute for judgment. Read the score cap and
gate reasons: an open Critical caps the audit score at 2.0; an open High caps it at 6.0. A score of 9.0
or more meets the score threshold, while the overall gate also considers Critical/High findings,
unused/copy status, and the unresolved needs-data flag ratio. Carry runtime-dependent questions forward
as open questions.

## Recommendation decisions

For each in-scope existing object or coherent group, record a decision on **structure, data, and logic**
separately. Use the score band as a starting point, then explain evidence-based overrides:

| Score band | Starting posture |
|---|---|
| 9.0–10 | Reuse |
| 7.0–8.9 | Refactor |
| 5.0–6.9 | Rework |
| 0–4.9 | Rebuild |
| Unused or copy database | Consider drop; state the usage evidence and any confirmation needed |

An open Critical finding requires an explicit corrective decision even when the overall score is high.
Business logic placement, dead/copy schemas, and cross-database coupling should follow the audit
evidence. Name the finding behind each material recommendation; do not turn unknown consumers or data
profiles into assumed facts.

For new databases, summarize why the supplied design fits the requirements and surface the decisions
that need stakeholder confirmation. Do not invent a legacy score or audit findings.

## Build and migration plan

Use the supplied design as the source of target entities, relationships, keys, constraints, and DDL.
Check that its version is clear and that both diagrams correspond to it. If a discrepancy is found,
describe it and route the correction to `dbdesign` or `dbdiagram` rather than silently changing the model
inside this proposal.

For migrations, document the source-to-target mapping, order of work, data cleanup, constraint
validation, cutover and rollback approach, dependencies, and validation evidence. Cover shadow-table
deduplication, orphan resolution, magic-value handling, repeating-group conversion, and other audit
findings where applicable. Keep every unresolved needs-data flag as an open question and say which
decision it affects.

For in-place remediation, order proposed changes Critical-first and by dependency. Each register row
names the finding, change, patch or DDL outline, data step, risk/blast radius, validation, and rollback.
All changes are proposals for review; this skill never applies them.

## Deliverable

Write a concise proposal that includes:

1. Executive recommendation, scope, source versions, and target engine when relevant.
2. What is good, what needs attention, and expected improvements.
3. A prioritized decision register with evidence and separate structure/data/logic decisions where
   applicable.
4. The target-design artifact path and the paths to both editable draw.io diagrams. Briefly explain
   what each diagram communicates and note any known model/diagram discrepancy.
5. Migration or remediation sequence, dependencies, risks, validation, and rollback.
6. Open questions, especially unresolved audit flags, with the decision each blocks.

Do not paste large DDL or diagram XML into the proposal when the artifacts can be linked. Keep the
proposal reviewable and make each referenced artifact path unambiguous.
