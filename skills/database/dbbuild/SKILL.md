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
4. Check internal consistency: referenced tables and columns exist; keys and foreign keys agree with the model; nullability, uniqueness, checks, and relationship cardinalities match the design; every rule the design maps to a mechanism (physical-design §5.3) has it — the constraint, the partial unique index, the exclusion constraint, the named constraint trigger; engine syntax is appropriate; and scripts are ordered coherently. State any items that could not be verified.
4a. Emit **seed data** for lookup tables when the design defines their values, and **negative tests**: one statement per `NOT NULL`, `UNIQUE`, `CHECK`, FK and exclusion constraint that the database must reject, plus the verification query of every tier-4 rule. Put them in the project's test framework when it has one, or list them in the output inventory — never as a `.sql` file beside the DDL, because each is meant to fail and a runner executing the scripts in order would stop on it.
5. Treat user feedback as an iteration. If it changes entities, relationships, keys, constraints, or other structure, route the change through [dbdesign](../dbdesign/SKILL.md), regenerate both diagrams with [dbdiagram](../dbdiagram/SKILL.md), and revise the proposal with [dbpropose](../dbpropose/SKILL.md). The revised proposal must be accepted before generating its final DDL. For formatting or naming-only changes that do not change the approved structure, update the DDL and state that the design is unchanged.

## PostgreSQL target (PG18)

- **Order:** `CREATE SCHEMA … AUTHORIZATION <owner_role>` → `CREATE EXTENSION IF NOT EXISTS … WITH SCHEMA extensions` → types and domains → tables (PK and column `CHECK`s inline) → FKs and cross-table constraints → indexes → views, materialized views and their unique index → functions → triggers → `REVOKE`/`GRANT` and `ALTER DEFAULT PRIVILEGES` (physical-design §11) → `COMMENT ON` every table and every non-obvious column, from the data dictionary.
- **Pin name resolution.** Schema-qualify every reference; start each script with `SET search_path = …` naming the schemas it creates in; give every function — `SECURITY DEFINER` ones above all — its own `SET search_path`. Never depend on the session's path.
- **Ownership.** Objects are owned by a `NOLOGIN` owner role, never a person or `postgres`. Emit `ALTER … OWNER TO` only for a role the proposal names; otherwise mark it as an open decision.
- **Transactions.** PostgreSQL DDL is transactional: wrap each script in `BEGIN; … COMMIT;` so a failed script leaves nothing half-built. Statements that can't run in a transaction block — `CREATE/DROP INDEX CONCURRENTLY`, `REINDEX CONCURRENTLY`, `CREATE DATABASE`, `ALTER SYSTEM`, `VACUUM` — go in their own files, named and ordered as such, and the header says so. (`ALTER TYPE … ADD VALUE` may run in a transaction, but the new label can't be used before commit.)
- **Migrations** follow the proposal's lock-safe forms ([proposal.md](../dbpropose/proposal.md)): `NOT VALID` then `VALIDATE`, concurrent index builds, `SET lock_timeout` per step, batched backfills.
- **Identity seeding.** Seed rows into `GENERATED ALWAYS` columns with `OVERRIDING SYSTEM VALUE`, then `SELECT setval(pg_get_serial_sequence('t', 'id'), max(id)) FROM t`.
- **Materialized views** get the `UNIQUE` index `REFRESH … CONCURRENTLY` needs; a re-created one re-emits its indexes and grants.

## Output

Return the `.sql` artifact paths and a short inventory of the scripts, with the negative tests and verification queries. Identify assumptions, unverified engine details, and any iteration that requires renewed proposal acceptance. Never run the SQL or imply that the database has been changed.
