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
- **Data/metadata confusion** (theory §10). EAV tables that store attribute names as rows, generic
  arcs that store table names as data, and the inverse — per-year or per-tenant clone tables and
  columns, value lists frozen in `CHECK`/`ENUM` for a fluid domain. Each moves a constraint the engine
  could enforce into application code; catalogued in [`tables.md`](tables.md).
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
- **Query-shape prevalence.** Count the query-shape anti-patterns in view and procedure bodies
  estate-wide — non-sargable predicates, leading-wildcard `LIKE`, catch-all `@p IS NULL OR` filters,
  `NOT IN (SELECT`, offset paging, optimizer hints — and the distribution of index count per table.
  Report prevalence once per estate; the individual findings live in the object-type docs.

## 4. Data quality & "dark data"

- **Polymorphic / generic columns.** Columns named `data`, `value`, `payload`, `misc_data`,
  `config_blob` that store CSV, pipe-separated arrays, or unstructured JSON instead of typed,
  queryable columns → 1NF violation.
- **CSV / multivalued cells.** Repeating groups inside one column.
- **Type drift for a shared concept.** The same logical key typed differently across tables
  (`id` as `varchar` here, `int` there) — a join hazard and an implicit-conversion source. ✅ decidable
  when the drifting columns are linked by a declared FK; ⚠️ when linked only by name.
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
Security is a first-class lens (theory §11). What a dump contains depends on the engine:

- **SQL Server / Oracle:** server-side security objects (GRANTs, logins, role memberships, encryption
  metadata) are usually **absent** from DDL dumps and must be checked on the instance, not here.
- **PostgreSQL:** a default `pg_dump --schema-only` **includes** owners (`ALTER … OWNER TO`), `GRANT`/
  `REVOKE`, `ALTER DEFAULT PRIVILEGES`, row-level-security policies and function `SECURITY DEFINER` /
  `SET search_path` clauses — audit them statically (✅). If the dump was taken with `-O`/`-x`, say so and
  mark privilege findings 🔬. Roles and memberships live in the cluster globals
  (`pg_dumpall --roles-only`); request it.

- **Untrusted / disabled constraints** — `WITH NOCHECK` / `NOCHECK CONSTRAINT` means referential or
  domain integrity is *defined but not enforced*; the optimizer also can't trust it. ✅ decidable.
- **Elevated execution context** — `EXECUTE AS` in procedures broadens the blast radius of any
  injection or logic flaw. ✅ decidable.
- **Plaintext secrets** — passwords, connection strings, or tokens embedded in procedure/view text.
  ⚠️ proxy (grep, then read).
- **Recoverable credentials** — a password column whose stored value can be turned back into the
  password: plaintext, reversible encryption (`ENCRYPTBYPASSPHRASE`/`DECRYPTBYKEY`, `AES_ENCRYPT`,
  `pgp_sym_encrypt`), an unsalted hash, or a fast general-purpose hash (`MD5`, `SHA1`, plain
  `SHA2_256`). The target is a per-row-salted **slow** hash computed in the application (theory §11); a
  procedure that compares `password = @password` or hashes inside SQL (`HASHBYTES('SHA2_256', @pwd)`) is
  evidence of plaintext in transit. A short `varchar` is a shape signal, not proof — a hash is a
  `varchar` too. High. Password **reset** stores a random, expiring token, never a recoverable password.
- **PostgreSQL privilege defects** (✅ from a default dump): `SECURITY DEFINER` functions without a
  pinned `SET search_path` (a caller can plant objects that run with the owner's rights) or still
  executable by `PUBLIC` (functions get `EXECUTE` to `PUBLIC` by default) — High; untrusted procedural
  languages (`plpython3u`, `plperlu`, `C`) — High with `SECURITY DEFINER`; broad grants to `PUBLIC` and
  `CREATE` on schema `public` — Medium–High; objects owned by a superuser or a person's login rather than
  a `NOLOGIN` owner role — Medium; a `CREATE POLICY` on a table without `ENABLE ROW LEVEL SECURITY`, or
  `ENABLE` without `FORCE` when the application connects as the owner — High; views over RLS tables
  without `security_invoker` — High.
- **Integrity switched off in scripts** — `ALTER TABLE … DISABLE TRIGGER ALL` (disables FK enforcement
  on PostgreSQL) or `SET session_replication_role = replica` in migrations or procedures. Codd rule 12
  (nonsubversion). ✅ High.
- **Injection surface** — dynamic `EXEC(@sql)` on concatenated input (canonical treatment in
  [`procedures.md`](procedures.md)).
- **PII / sensitive columns** — identify by name (national IDs, surnames, salary, payment); whether
  their handling is acceptable is contextual → 🔬 needs-data, flagged not graded.

See [`detection-signals.md`](detection-signals.md) for the grep commands.

## 7. Concurrency

Procedures and triggers that write are graded for the anomalies of theory §5.2, not only for their
structure. Canonical entries: dirty-read hints, lost updates, check-then-act races, `MAX()+1` numbering
and elevated isolation without retry in [`procedures.md`](procedures.md); emulated constraints and
cross-row validation triggers in [`triggers.md`](triggers.md). At estate level record: the count of
`NOLOCK`/`READ UNCOMMITTED` uses, how many invariants are enforced only by procedural checks, and
whether `READ_COMMITTED_SNAPSHOT` (SQL Server) is known — it changes what the default level permits, so
when it can't be established it is a 🔬 flag on every check-then-act finding.

## 8. Derived data & integration plumbing

Classify every redundant structure as *system of record* or *derived* (theory §6) and check the three
legitimacy conditions — named source, one-way, rebuildable. Static signals:

- **Undeclared derived tables** — `*_cache`, `*_resumen`, `*_snapshot`, `*_consolidado`, `*_acum`
  tables written by jobs or procedures, with no stated source or rebuild path. ⚠️; source and rebuild
  path are 🔬 / ask.
- **Copied parent attributes** — a non-key column on a child matching a non-key column of the
  FK-referenced parent by name and type (`pedido.nombre_cliente` vs `cliente.nombre`). ⚠️: a
  **point-in-time fact** (legitimate) or a drifting copy (2NF/SSOT)?
- **Sync-state columns** — `sincronizado`, `enviado`, `procesado`, `fecha_sync`, `pendiente_*`: an
  integration whose ordering and retry behaviour live outside the DDL. 🔬 — record as a dataflow
  question (who consumes, what happens on failure, can it be replayed).
- **Trigger-maintained change logs** — triggers inserting into `*_log`/`*_audit`/`*_cambios`/queue
  tables. Legitimate CDC/outbox when written in the same transaction; record the lock-scope cost and
  that the log is now a system of record for its consumers.
- **Dual writes across databases** — triggers or procedures writing to another catalog: no atomic commit
  across the two, so a partial failure leaves them diverged. Escalates the coupling finding in §2.
- **Read replicas, materialized views, warehouses** are derived data, **not** copy schemas — grade them
  on the three conditions, never as an SSOT violation.

## 9. TL;DR audit checklist *(static-DDL only)*

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
4. **Scan procedure/view bodies for hotspots.** `CURSOR` / `WHILE` (RBAR), dynamic `EXEC(...)`,
   nested-view references, catch-all `@p IS NULL OR` predicates, non-sargable predicates,
   `NOT IN (SELECT`, `NOLOCK` and `MAX()+1` — the anomalies that most often hide cost, wrong results
   and races.

## Explicitly excluded

These require a live instance and **cannot** be judged from static dumps, so they are out of this
rubric's scope:

- Slow query logs / actual execution plans.
- Table and index **on-disk size**, row counts, growth.
- **Fragmentation** and page-split statistics.
- Real index *usage* (vs. mere definition).

Where a concern has a static proxy (e.g. *redundant index definition* as a proxy for write overhead),
the proxy is used and labelled as such in the relevant object-type doc.
