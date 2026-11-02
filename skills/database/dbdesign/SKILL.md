---
name: dbdesign
description: Design a new relational database or revise an existing database design from an audit, requirements, or domain model using relational theory, Codd's rules, normal forms, and physical-design guidance.
---

# dbdesign

Design the logical model before selecting physical implementation details. When the question is still which stores the system needs — relational or not, how many, what is derived — run [dbarchitect](../dbarchitect/SKILL.md) first; this skill then designs each relational system of record it names, starting from its load parameters and consistency map. This skill can be used independently for a new design or after `dbaudit` to redesign an existing database. It proposes a design; it does not apply schema changes or migrations.

## Choose the mode

| Mode | Input | Output |
|---|---|---|
| New design | Requirements, domain description, or interview notes | Conceptual model, normalized relational model, and target DDL when the engine is known |
| Audited redesign | Audit report and source schema | Corrected model with each major change traced to audit evidence or a stated requirement |
| Design review | Existing ER model, relational schema, or DDL | Findings and improvement recommendations; rewrite only when requested |

If revising an existing database without an audit, say so. Proceed with the evidence available, mark unknowns, and recommend `dbaudit` when a defensible assessment is needed. Never claim runtime properties from static DDL.

## Method

1. Read relevant companion references: [theory.md](theory.md), [er-modeling.md](er-modeling.md), [physical-design.md](physical-design.md), and [requirements.md](requirements.md). Use the modeling reference for entities, relationships, identifiers, normalization, history, subtypes, arcs, and mapping into relations.
2. **Build the requirements dossier** ([requirements.md](requirements.md)) before any entity: scope and user views, a business-rule catalogue (`BR-nn`, each with its kind and source), a data dictionary, an access matrix, volumetrics and the main transactions and queries, and an open-questions log. Separate **fundamental** constraints (an id identifies one person) from **policy** constraints likely to change (one department per person), and model policy cardinalities so relaxing them is additive. State assumptions, unresolved questions, and the target database engine. Confirm the dossier with the domain owner when one is available. Do not silently turn an assumption into a constraint: a rule that isn't in the catalogue can't be traced to a constraint, and a constraint with no rule behind it is an assumption — say so.
3. Identify entities, attributes, candidate identifiers, mandatory/optional participation and relationship cardinalities. Use Barker notation for the conceptual ER model and review each applicable Codd rule, explaining limitations or justified exceptions. Explain deliberate denormalization and its trade-offs.
3a. **Derive the dependencies, then the keys, then the decomposition** (theory §2–§3):
   1. Write every catalogued rule of the form "each X has exactly one Y" as an FD `X → Y` — Barker sentences ending "one and only one" are FDs — and mark each fundamental or policy.
   2. Reduce them to a canonical cover.
   3. Derive the candidate keys by attribute closure over the **natural** attributes; surrogates are added afterwards and never count as the key during analysis.
   4. Test each relation for BCNF; on a violation, decompose and check that each split is lossless (the shared columns are a key of one side → PK there, FK on the other) and that every FD is preserved. Where BCNF would lose an FD that must be enforced, keep 3NF for that relation and record the controlled redundancy — or decompose and enforce the lost FD (physical-design §5.3).
   5. For every all-key relation with three or more attributes, ask whether the attribute groups vary independently (4NF split) or form a genuine n-ary fact (keep; er-modeling §A2.7).
   6. Report the FD list, the cover, the keys and the normal form of each relation. Any FD whose left side is not a key of some table is an unenforced invariant: list how it is enforced, or that it is not.
4. For an audited redesign, map each material change to audit findings and distinguish preserved behavior from intentional behavior changes.
5. Map the conceptual model into relations: primary and alternate keys, foreign keys, nullability (one documented meaning per nullable column), uniqueness, check constraints, and join tables for many-to-many relationships. Then apply physical-design guidance for the chosen engine, including its access design (physical-design §11).
6. Provide a concise validation checklist: key and relationship integrity, normal-form rationale, and **every business rule with its enforcement tier and mechanism** (physical-design §5.3) — the tier-4 and tier-5 rules by name, so nobody assumes the schema holds them — the invariants that must survive concurrent writers, and questions that require domain-owner confirmation.

## Deliverable

Return a reviewable design with: scope and assumptions; the requirements dossier (or the parts the inputs supported); conceptual entities and relationship sentences plus a Barker ER model when diagrammed; candidate/primary keys; relational table definitions; normal-form assessment with dependencies; constraints and the rule-to-mechanism map; a data dictionary; engine-specific DDL if requested or useful; audit traceability for redesigns; and open questions. Keep the logical model separate from engine-specific choices.

**The DDL runs as written** on the target engine and version, top to bottom: one script, statements only, in dependency order, no placeholders, bind parameters or other engines' syntax. Example queries — a report, an export, a parameterized lookup — go in their own section after the DDL, never inside it. When the engine is at hand (SQLite usually is), execute the script against a throwaway in-memory database and say that it ran; otherwise say it was not executed.

When diagrams are requested or the workflow continues, hand the model to [dbdiagram](../dbdiagram/SKILL.md). A full recommendation that incorporates audit evidence and diagrams belongs to [dbpropose](../dbpropose/SKILL.md).
