# Audit Lenses — Cross-Cutting Inspection

> The inspection lenses that span **all** object types. Where the object-type docs grade a single
> `tables.sql` or `procedures.sql`, these lenses grade a database or an estate as a whole. Theory terms
> (1NF, SSOT, ACID, functional dependency, ER constructs) are defined in [`theory.md`](theory.md).
>
> **Scope reminder:** this rubric judges **static DDL only**. Anything requiring a live server is out
> of scope — see [Explicitly excluded](#explicitly-excluded).

## 1. Structural & schema debt

- **Missing or absent constraints.** Tables with no primary key, or relationships that exist only by
  convention (matching column names) with **no declared `FOREIGN KEY`**. Legacy systems that enforce
  relationships in application code inevitably accumulate orphan rows. FK coverage is usually partial
  — grade per table, not per estate.
- **Under-normalization.** Wide tables with repeated columns (`address_1`, `address_2`, `address_3`),
  or atomic facts split across hardcoded slots → 1NF/2NF failure.
- **Unmodelled constructs.** Subtypes encoded as a type column with sparse column blocks, arcs encoded
  as `ref_type` + `ref_id`, M:M tables with no pair uniqueness, hierarchies as fixed level columns.
  Each is a modelling decision (theory §9; er-modeling.md) that the DDL got wrong or never made
  — catalogued with detection rules in [`tables.md`](tables.md).
- **Over-normalization.** Excessive splitting that forces many-way joins just to read a basic record,
  penalizing read paths.
- **The "God table".** A single table holding a large fraction of the system's data or business
  rules — a structural bottleneck and a magnet for lock contention. Detect by relative column count
  and by how many procedures/views reference it.
- **Dead and copy schemas.** Whole databases with no consumers, and databases that are copies of
  another (an SSOT violation decidable from the DDL by comparing object lists). Usage is not in the
  DDL — ask, or flag 🔬. Every object in a dead schema carries cost (backup, security surface,
  confusion) with zero value: archival/removal candidates.

## 2. Cross-database coupling

- **Three-part names** (`OTHER_DB..TABLE`, `OTHER_DB.dbo.fn…`) in procedures, triggers and views couple
  database lifecycles, defeat independent restore, and — combined with a collation split — create
  hidden performance cliffs. Every reference is an edge in the coupling graph that
  [dbpropose](../dbpropose/SKILL.md) uses to derive the target topology, so count them by source and
  target catalog, not just in total.
- **Collation split.** Text columns declared under different collations across databases that are
  joined → implicit conversion, suppressed indexes, collation-conflict errors. Count declarations per
  collation estate-wide.
- **Engine-era inconsistency.** Syntax from several engine generations side by side (e.g. `CREATE OR
  ALTER` beside pre-2005 constructs). Not a defect alone; a signal of uncontrolled multi-era evolution.

## 3. Performance & indexing health *(statically deducible only)*

Limited to what the DDL text reveals — index *definitions*, not index *usage*. **Canonical criteria
live in [`indexes.md`](indexes.md)**; this section only frames them at the estate level:

- Redundant/overlapping index definitions, heaps (no clustered index), and missing foreign-key
  indexes are write-overhead or scan risks deducible from the DDL.
- Low-cardinality and "hot-path" judgements are **needs-data** (🔬) — flagged, not graded. See the
  confidence convention in [`scoring.md`](scoring.md).

## 4. Data quality & "dark data"

- **Polymorphic / generic columns.** Columns named `data`, `value`, `payload`, `misc_data`,
  `config_blob` that store CSV, pipe-separated arrays, or unstructured JSON instead of typed,
  queryable columns → 1NF violation.
- **CSV / multivalued cells.** Repeating groups inside one column.
- **Type drift for a shared concept.** The same logical key typed differently across tables
  (`id` as `varchar` here, `int` there) — a join hazard and an implicit-conversion source.
- **Collation drift** — see §2 and [`tables.md`](tables.md).

## 5. Business-logic drift & configuration

- **Logic buried in the database.** Complex stored procedures, triggers, and views that hide data
  flow. Triggers in particular obscure *why* a value changed — incoming engineers can't trace the
  mutation. Catalogued in [`procedures.md`](procedures.md), [`triggers.md`](triggers.md),
  [`views.md`](views.md).
- **Hardcoded configuration in transactional tables.** Feature flags / system parameters mixed into
  business tables instead of a dedicated parameter store.

## 6. Security & data sensitivity

Personnel, attendance, payroll, payment and customer data are a real PII and financial footprint.
Security is a first-class lens, with the caveat that **server-side security objects (GRANTs, logins,
role memberships, encryption metadata) are usually absent from DDL dumps** and must be checked on the
instance, not here.

- **Untrusted / disabled constraints** — `WITH NOCHECK` / `NOCHECK CONSTRAINT` means referential or
  domain integrity is *defined but not enforced*; the optimizer also can't trust it. ✅ decidable.
- **Elevated execution context** — `EXECUTE AS` in procedures broadens the blast radius of any
  injection or logic flaw. ✅ decidable.
- **Plaintext secrets** — passwords, connection strings, or tokens embedded in procedure/view text,
  and password columns stored as plain `varchar`. ⚠️ proxy (grep, then read).
- **Injection surface** — dynamic `EXEC(@sql)` on concatenated input (canonical treatment in
  [`procedures.md`](procedures.md)).
- **PII / sensitive columns** — identify by name (national IDs, surnames, salary, payment); whether
  their handling is acceptable is contextual → 🔬 needs-data, flagged not graded.

See [`detection-signals.md`](detection-signals.md) for the grep commands.

## 7. TL;DR audit checklist *(static-DDL only)*

Four passes you can run against the dumps with `grep`-level tooling:

1. **Reconstruct relationships from the DDL.** Parse `CREATE TABLE` + constraint definitions. Tables
   with **no declared `PRIMARY KEY`** or expected-but-absent `FOREIGN KEY` are integrity gaps. (The
   classic "generate an ERD and look for missing lines" check, done from text.) Phrase each
   relationship as a two-way sentence (er-modeling §A1.3) — the ones you can't phrase, and the M:M,
   arcs and subtypes hiding in type columns, are where the model went wrong.
2. **Inventory every trigger.** List all `CREATE TRIGGER` across the dumps to surface "magic"
   autonomous mutations before they blindside you.
3. **List shadow/backup/copy artefacts and dead schemas.** Dated copy tables (`*_COPIA_*`),
   name-versioned duplicates (`*2`, `*_old`), and unused databases — archival candidates.
4. **Scan procedure/view bodies for hotspots.** `CURSOR` / `WHILE` (RBAR), dynamic `EXEC(...)`, and
   nested-view references — the structural anomalies that most often hide cost and risk.

## Explicitly excluded

These require a live instance and **cannot** be judged from static dumps, so they are out of this
rubric's scope:

- Slow query logs / actual execution plans.
- Table and index **on-disk size**, row counts, growth.
- **Fragmentation** and page-split statistics.
- Real index *usage* (vs. mere definition).

Where a concern has a static proxy (e.g. *redundant index definition* as a proxy for write overhead),
the proxy is used and labelled as such in the relevant object-type doc.
