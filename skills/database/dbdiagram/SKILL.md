---
name: dbdiagram
description: Generate editable draw.io entity-relationship and relational-model diagrams from a database design, DDL, or other database structure.
---

# dbdiagram

Create two clear, editable draw.io diagrams: the **modelo entidad relación**, always in **Barker / Oracle CASE*METHOD notation**, and the **modelo relacional**, using table, column, key, constraint, and foreign-key notation. This skill can run independently from a supplied design or database structure, or consume the output of `dbdesign`. Barker rules apply to the ER view; do not force ER symbols onto the relational view.

## Inputs and evidence

- Prefer an approved conceptual/logical design when provided. Otherwise reverse-engineer the available DDL or structure and label inferred semantics.
- Preserve source names and clearly distinguish facts extracted from the source from inferred entities, cardinalities, optionality, or business meaning.
- If the input lacks information needed for the ER model, diagram the supported facts and annotate the unknowns; do not invent certainty.
- Read [er-modeling.md](er-modeling.md) when translating between conceptual and relational forms.

## Diagram content

**Barker ER model:**

- Singular, unique, **UPPERCASE** entity names in soft-cornered rectangles.
- Attribute names in lowercase; prefix UID attributes with `#`, mandatory attributes with `*`, and optional attributes with `o`.
- Binary relationships only, with reciprocal lowercase role names at both ends. A solid segment at an end means mandatory (*must be*); a dashed segment means optional (*may be*). Use a plain/bar end for one and a crow's foot for one or more. Show each end's optionality and cardinality independently.
- Use a UID bar across a relationship at the identified entity end when that relationship participates in its UID. Mark non-transferable relationships with the Barker diamond; represent subtypes and arcs explicitly, with a legend.
- Resolve a three-part association as an intersection entity with binary relationships to each participant. Never draw a ternary relationship connector.
- Title the page **Barker ER Model** and include a visible legend identifying Barker notation and explaining its glyphs. Do not mix in Chen diamonds, UML class boxes, or optionality circles from other crow's-foot variants.

These conventions follow [Redgate’s Barker notation guide](https://www.red-gate.com/blog/barkers-erd-notation/); see [er-modeling.md](er-modeling.md) for modelling rules and edge cases.

**Relational model:** one table per relation; columns and useful data types; PK, FK, alternate/unique keys, nullability, and checks where known; labeled FK paths; and schema boundaries when they aid comprehension. Use consistent identifiers across both views so a reader can trace each entity into its table mapping.

For both diagrams, include a title, a compact legend, and a provenance note naming the input and any assumptions. Keep the layout legible and avoid decorative details that obscure cardinalities or key markers.

## Output and validation

- Save both outputs as native, editable `.drawio` files in the requested output location. Use names that distinguish `er-model` from `relational-model`.
- Author valid diagrams.net XML with stable semantic cell IDs; include all required geometry for vertices and edges. Do not deliver flattened images as a substitute for the editable files.
- Validate that each file is well-formed XML and that referenced cell IDs, PK/FK labels, and relationship endpoints are present and consistent with the supplied model. If a draw.io renderer is available, inspect the rendered pages for overlap, clipping, and unreadable labels; report when visual rendering could not be checked.
- When updating an existing diagram, preserve its layout and styles where practical and explain any semantic ambiguity that affects the drawing.

The diagrams are inputs to [dbpropose](../dbpropose/SKILL.md) when preparing a complete recommendation. For specialized draw.io authoring, editing, or export workflows, use the available draw.io skill or tooling.
