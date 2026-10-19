---
name: dbbuild
description: Generate reviewable database DDL from an explicitly accepted proposal and its approved database design; revise the design workflow when structural changes are requested.
---

# dbbuild

Generate DDL as a reviewable artifact from an accepted proposal and its corresponding design. This is the final database-workflow stage. It creates SQL files; it does not connect to a database, apply DDL, or run migrations.

## Required inputs

- An explicitly accepted proposal.
- The design artifact that the proposal refers to, including target engine/version.
- The proposal's Barker ER diagram and relational diagram, for cross-checking the approved structure.
- The requested output location and any naming or migration-script conventions.

If the proposal and design disagree, stop and describe the mismatch. If the target engine or required design details are missing, ask for the missing decision or mark the DDL as incomplete; never fill a structural gap silently.

## Generate and iterate

1. Confirm that the accepted proposal, design, Barker ER diagram, and relational diagram are the same versions being used. Treat the proposal's decisions and the design's logical/physical structure as authoritative.
2. Generate readable, ordered `.sql` files for the target engine: schemas/namespaces, types or lookup structures, tables, keys and constraints, indexes, views/functions/triggers when included, and any explicitly requested migration or seed scripts. Keep object dependencies executable in order and annotate non-obvious constraints briefly.
3. Include a header with the proposal/design source paths, target engine/version, generation date, and whether the script creates a new schema or migrates an existing one. Do not include credentials or environment-specific secrets.
4. Check internal consistency: referenced tables and columns exist; keys and foreign keys agree with the model; nullability, uniqueness, checks, and relationship cardinalities match the design; engine syntax is appropriate; and scripts are ordered coherently. State any items that could not be verified.
5. Treat user feedback as an iteration. If it changes entities, relationships, keys, constraints, or other structure, route the change through [dbdesign](../dbdesign/SKILL.md), regenerate both diagrams with [dbdiagram](../dbdiagram/SKILL.md), and revise the proposal with [dbpropose](../dbpropose/SKILL.md). The revised proposal must be accepted before generating its final DDL. For formatting or naming-only changes that do not change the approved structure, update the DDL and state that the design is unchanged.

## Output

Return the `.sql` artifact paths and a short inventory of the scripts. Identify assumptions, unverified engine details, and any iteration that requires renewed proposal acceptance. Never run the SQL or imply that the database has been changed.
