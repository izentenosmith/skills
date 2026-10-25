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
- implementation or migration sequencing as a step table — each step with its validation, rollback and blast radius; data cleanup before the constraint it would violate; expand/contract for anything an existing consumer reads — plus dependencies, risks and unresolved questions;
- that the proposal needs explicit acceptance before [dbbuild](../dbbuild/SKILL.md) generates DDL.

Save it as `proposal.md` (location in [proposal.md](proposal.md#deliverable)) and give its path in the response.

Keep facts, inferences, and decisions distinct. Treat unresolved runtime questions as open questions. A proposal is not authorization to change a database; never apply DDL or migrations as part of this skill.

The ER diagram must use Barker notation; the relational diagram uses table/key notation. Confirm that both
diagrams correspond to the supplied design and describe any mismatch. Do not redraw or silently repair
either artifact in the proposal.

## Handoff

For an existing database, the usual sequence is [dbaudit](../dbaudit/SKILL.md) → [dbdesign](../dbdesign/SKILL.md) → [dbdiagram](../dbdiagram/SKILL.md) → this proposal. For a new database, start at `dbdesign`. Each stage may also be run alone when its inputs are available.
