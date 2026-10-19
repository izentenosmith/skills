---
name: dbdiagram
description: Generate editable draw.io entity-relationship and relational-model diagrams from a database design, DDL, or other database structure.
---

# dbdiagram

Create two clear, editable draw.io diagrams: the **modelo entidad relación** (conceptual entities, attributes, identifiers, and relationships) and the **modelo relacional** (tables, columns, keys, constraints, and foreign-key links). This skill can run independently from a supplied design or database structure, or consume the output of `dbdesign`.

## Inputs and evidence

- Prefer an approved conceptual/logical design when provided. Otherwise reverse-engineer the available DDL or structure and label inferred semantics.
- Preserve source names and clearly distinguish facts extracted from the source from inferred entities, cardinalities, optionality, or business meaning.
- If the input lacks information needed for the ER model, diagram the supported facts and annotate the unknowns; do not invent certainty.
- Read [er-modeling.md](er-modeling.md) when translating between conceptual and relational forms.

## Diagram content

**ER model:** entities and meaningful attributes; primary/candidate identifiers; named relationships with cardinality and optionality at both ends; associative entities for resolved many-to-many relationships; and explicit subtype, recursive, or exclusive-arc structures where present.

**Relational model:** one table per relation; columns and useful data types; PK, FK, alternate/unique keys, nullability, and checks where known; labeled FK paths; and schema boundaries when they aid comprehension. Use consistent identifiers across both views so a reader can trace each entity into its table mapping.

For both diagrams, include a title, a compact legend, and a provenance note naming the input and any assumptions. Keep the layout legible and avoid decorative details that obscure cardinalities or key markers.

## Output and validation

- Save both outputs as native, editable `.drawio` files in the requested output location. Use names that distinguish `er-model` from `relational-model`.
- Author valid diagrams.net XML with stable semantic cell IDs; include all required geometry for vertices and edges. Do not deliver flattened images as a substitute for the editable files.
- Validate that each file is well-formed XML and that referenced cell IDs, PK/FK labels, and relationship endpoints are present and consistent with the supplied model. If a draw.io renderer is available, inspect the rendered pages for overlap, clipping, and unreadable labels; report when visual rendering could not be checked.
- When updating an existing diagram, preserve its layout and styles where practical and explain any semantic ambiguity that affects the drawing.

The diagrams are inputs to [dbpropose](../dbpropose/SKILL.md) when preparing a complete recommendation. For specialized draw.io authoring, editing, or export workflows, use the available draw.io skill or tooling.
