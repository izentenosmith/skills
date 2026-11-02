# Proposal — From Audit and Design to a Decision

This reference governs the recommendation stage. It consumes an audit and a separately reviewed design
when those artifacts apply. **Do not perform the audit, redesign the model, or redraw diagrams here.**
The companion stages are [dbaudit](../dbaudit/SKILL.md), [dbdesign](../dbdesign/SKILL.md), and
[dbdiagram](../dbdiagram/SKILL.md); their outputs remain independently reviewable.

When the proposal changes the model, it needs both diagrams: the conceptual ER diagram in Barker notation
(see [er-modeling.md](er-modeling.md) and [dbdiagram](../dbdiagram/SKILL.md)) and the relational diagram in
table/key notation. A proposal for a model change whose ER diagram is absent or in another notation is not
complete: name the gap and route it to `dbdiagram`. An in-place remediation that leaves the model as it is
(an index, a trigger fix, a data repair) doesn't need either diagram.

## Inputs and limits

For an existing database, use the per-file evaluations, the per-database summary and the estate synthesis
when available. `scores.json` and `gate.md` exist only when the harness ran. Without them, read the score,
its cap and the gate reasons from the audit summary. For a redesign or migration, also use the design
document, the **modelo entidad relación** draw.io file and the **modelo relacional** draw.io file. For a
new database, use the requirements, design and both diagrams. If a needed artifact is absent, identify the
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

A score capped by a single Critical is not a structural verdict. Say what the uncapped score is, and
whether the posture follows the cap or the structure underneath it.

An open Critical finding requires an explicit corrective decision even when the overall score is high.
Business logic placement, dead/copy schemas, and cross-database coupling should follow the audit
evidence. Name the finding behind each material recommendation; do not turn unknown consumers or data
profiles into assumed facts.

Every register row cites the audit finding it answers, by the audit's own id. A row no finding asked for
says **no audit finding** and names its driver: a requirement, a design decision, a stakeholder request.
Never coin an id the audit doesn't contain.

For new databases, summarize why the supplied design fits the requirements and surface the decisions
that need stakeholder confirmation. Do not invent a legacy score or audit findings.

## Breaking changes and their consumers

A change breaks someone when it removes, renames, retypes or newly constrains something a consumer reads
or writes. Before sequencing, list the consumers of each such change, from the audit, the design, the
requirements and the code you were given: the application, reports, add-ons and plug-ins, ETL jobs,
views, other databases. If you can't establish who the consumers are, raise it as an open question.

A breaking change with a known consumer ships in three steps, never one:

1. **Expand.** Add the new shape beside the old one (the new columns, table or view) and keep both in
   step: write both, or derive the old from the new.
2. **Migrate consumers.** Move each named consumer to the new shape. Each consumer is its own
   dependency, with its own owner and its own evidence that it has moved.
3. **Contract.** Remove the old shape, **gated on every named consumer having moved**. Name the
   consumer in the gate. "When nobody uses it" is not a gate.

## Ordering rules

- **Containment first.** An open Critical that is still producing bad data gets stopped before any
  structural work.
- **Data before the constraint it unblocks.** Resolve orphans before declaring the foreign key, remove
  duplicates before the unique key, map invalid values before the check constraint. Count them in a
  pre-check, and decide what happens to them (repair, quarantine, archive), never silent deletion.
- **Parents before children** when tables are rebuilt.
- **Expand before contract,** as above.
- **Each step is independently reversible**, or the proposal says plainly that it isn't and what
  protects it (a backup, a gate that aborts the whole run).

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

Write the sequence as a table, first in its section: mechanism notes, dependencies and risks go below it.
Every column is filled for every step; a step whose rollback is "restore the backup" says which backup:

```markdown
| Step | Change | Finding | Pre-check | Validation | Rollback | Blast radius |
|---|---|---|---|---|---|---|
| 1 | Back up the database file | — | free disk ≥ 2× file size | backup opens and row counts match | n/a (read-only) | none |
| 2 | Move order lines with no matching order to `order_line_quarantine` | DB-REF-02 | count the orphans | live table has 0 orphans; moved = counted | move the rows back from quarantine | order history screens, for the orphaned lines only |
| 3 | Rebuild `order_line` with its FK to `orders` | DB-REF-02 | step 2's count is 0 | `foreign_key_check` returns no rows | restore step 1's backup | every write to `order_line` during the rebuild |
| 4 | Expand: add `customer.given_name`, `family_name`, filled from `full_name` | DB-NRM-03 | names that don't split cleanly | both shapes agree on every row | drop the two new columns | none: nothing reads them yet |
| 5 | Contract: drop `customer.full_name`, **gated on the invoicing export having moved** | DB-NRM-03 | the export reads only the new columns | export run diffs clean | re-add and backfill `full_name` | the invoicing export |
```

For in-place remediation, order proposed changes Critical-first and by dependency, in the same table.
All changes are proposals for review; this skill never applies them.

## Deliverable

Write the proposal to `proposal/proposal.md`, or the path the user gives, and cite every artifact it relies
on by path. It includes, in this order:

1. **Executive recommendation:** scope, source versions, target engine, the audit score and its cap, and
   the posture with its reasoning.
2. **What is good, what needs attention,** and the expected improvement.
3. **Decision register:** one row per object or group, with the finding id (or "no audit finding" and
   its driver) and separate structure / data / logic decisions in the band vocabulary.
4. **Target design and diagrams:** the design path and both draw.io paths, what each diagram shows,
   and any mismatch with where it was routed.
5. **Migration or remediation sequence:** the step table above, then dependencies and risks.
6. **Open questions:** each unresolved needs-data flag, unknown consumer or assumption, with the
   decision it blocks.
7. **Acceptance:** close with the line that this proposal needs explicit acceptance before
   [dbbuild](../dbbuild/SKILL.md) generates DDL from it, and that a structural change sends it back
   through dbdesign and dbdiagram.

Do not paste large DDL or diagram XML into the proposal when the artifacts can be linked. Keep the
proposal reviewable and make each referenced artifact path unambiguous.
