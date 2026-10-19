---
name: dbpropose
description: Prepare a reviewable recommendation for a database using audit evidence, a target design, and entity-relationship and relational draw.io diagrams.
---

# dbpropose

Turn evidence and a design into a clear recommendation for decision-makers and implementers. This skill can be used independently when the user supplies the needed artifacts, or as the final stage of the database workflow harness.

## Inputs

Use the available audit, proposed design, ER diagram, relational diagram, requirements, and target-engine preference. For an existing database, cite the audit's findings and score. If an audit or design is missing, identify the gap and limit conclusions accordingly; do not fabricate findings or imply that a diagram was generated. For a new database, use requirements and the proposed design as the evidence base.

## Prepare the proposal

Read [proposal.md](proposal.md) for the detailed decision rules and output structure. Cover:

- the recommendation and its rationale, including what is already good, what needs attention, and the expected improvement;
- a prioritized set of decisions or changes, with each major existing-database decision tied to an audit finding;
- the target design and the included **modelo entidad relación** and **modelo relacional** draw.io artifacts, with their paths;
- implementation or migration sequencing, dependencies, risks, validation, rollback considerations, and unresolved questions where relevant.

Keep facts, inferences, and decisions distinct. Treat unresolved runtime questions as open questions. A proposal is not authorization to change a database; never apply DDL or migrations as part of this skill.

## Handoff

For an existing database, the usual sequence is [dbaudit](../dbaudit/SKILL.md) → [dbdesign](../dbdesign/SKILL.md) → [dbdiagram](../dbdiagram/SKILL.md) → this proposal. For a new database, start at `dbdesign`. Each stage may also be run alone when its inputs are available.
