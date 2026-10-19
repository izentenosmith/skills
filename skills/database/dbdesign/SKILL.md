---
name: dbdesign
description: Design a new relational database or revise an existing database design from an audit, requirements, or domain model using relational theory, Codd's rules, normal forms, and physical-design guidance.
---

# dbdesign

Design the logical model before selecting physical implementation details. This skill can be used independently for a new design or after `dbaudit` to redesign an existing database. It proposes a design; it does not apply schema changes or migrations.

## Choose the mode

| Mode | Input | Output |
|---|---|---|
| New design | Requirements, domain description, or interview notes | Conceptual model, normalized relational model, and target DDL when the engine is known |
| Audited redesign | Audit report and source schema | Corrected model with each major change traced to audit evidence or a stated requirement |
| Design review | Existing ER model, relational schema, or DDL | Findings and improvement recommendations; rewrite only when requested |

If revising an existing database without an audit, say so. Proceed with the evidence available, mark unknowns, and recommend `dbaudit` when a defensible assessment is needed. Never claim runtime properties from static DDL.

## Method

1. Read relevant companion references: [theory.md](theory.md), [er-modeling.md](er-modeling.md), and [physical-design.md](physical-design.md). Use the modeling reference for entities, relationships, identifiers, normalization, history, subtypes, arcs, and mapping into relations.
2. State requirements, assumptions, unresolved questions, and the target database engine. Do not silently turn an assumption into a constraint.
3. Identify entities, attributes, candidate identifiers, mandatory/optional participation, relationship cardinalities, and functional dependencies. Use Barker notation for the conceptual ER model and review each applicable Codd rule, explaining limitations or justified exceptions. Assess applicable normal forms from dependencies, and explain deliberate denormalization and its trade-offs.
4. For an audited redesign, map each material change to audit findings and distinguish preserved behavior from intentional behavior changes.
5. Map the conceptual model into relations: primary and alternate keys, foreign keys, nullability, uniqueness, check constraints, and join tables for many-to-many relationships. Then apply physical-design guidance for the chosen engine.
6. Provide a concise validation checklist: key and relationship integrity, normal-form rationale, important business invariants, and questions that require domain-owner confirmation.

## Deliverable

Return a reviewable design with: scope and assumptions; conceptual entities and relationship sentences plus a Barker ER model when diagrammed; candidate/primary keys; relational table definitions; normal-form assessment with dependencies; constraints; engine-specific DDL if requested or useful; audit traceability for redesigns; and open questions. Keep the logical model separate from engine-specific choices.

When diagrams are requested or the workflow continues, hand the model to [dbdiagram](../dbdiagram/SKILL.md). A full recommendation that incorporates audit evidence and diagrams belongs to [dbpropose](../dbpropose/SKILL.md).
