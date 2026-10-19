# Physical Design — PostgreSQL 18 Standard

> How a modelled design becomes PostgreSQL 18 DDL: keys, naming, normalization targets, integrity,
> arcs/subtypes/history in the engine, types, indexes, collation, where logic lives, views and scale.
> It realizes a model built with [`er-modeling.md`](er-modeling.md) — it never replaces one. Every
> "rework"/"rebuild" verdict in [`proposal.md`](proposal.md) means "remodel with `er-modeling.md`, then
> bring it up to this document." For another target engine, keep the model and translate these
> choices.

## 1. Realize the model, don't re-invent it

This turns a CAP3 design (er-modeling §A3) into PG18 DDL. If a physical choice changes **meaning**
(merges two entities, drops a relationship, stores a derived value), it goes back to the model and is
decided there.

## 2. Keys & identity

The UID criteria in [er-modeling §A1.5](er-modeling.md#a15-unique-identifiers-uid) — never null, unique, invariant, short,
numeric — are why the default is a surrogate key.

- **Default to surrogate keys.** A short, stable, meaningless primary key decouples identity from
  business meaning so foreign keys never break when a code changes.
  - Sequential: `GENERATED ALWAYS AS IDENTITY` (preferred over legacy `serial`).
  - Distributed / time-ordered / merge-friendly: **`uuid` seeded by PostgreSQL 18's native
    `uuidv7()`** — time-sortable UUIDs that index far better than random `uuidv4()`.
- **Natural keys become `UNIQUE` constraints**, not the primary key — the candidate/alternate UIDs of
  the model. You keep the business uniqueness guarantee without coupling FKs to a volatile value.
- **Dependent and intersection entities** (UID includes a relationship) may keep a composite PK of
  their parents' keys, or take a surrogate PK plus a `UNIQUE` on the composite — choose one rule per
  schema. Never drop the composite uniqueness.
- Every table has a primary key. No heaps.

## 3. Naming conventions

- `snake_case` for all identifiers; one language and one pluralization rule, applied everywhere
  (entities are singular in the model; this guide's examples use singular tables).
- Names trace back to the model (er-modeling §A3.2 steps 1–2); one abbreviation per concept; no reserved words.
- Schema-qualify (`purchasing.purchase_order`), never rely on a single `dbo`-style catch-all.
- Constraints named by role: `pk_*`, `fk_*_*`, `uq_*`, `ck_*`, `ix_*`. (Replaces the typical legacy
  mix of `DEPARTMENTS_PK` / `PK_employee_master` / `pk_dtproperties` in one schema.)
- Self-referencing FKs named for the **role** (`manager_id`, `parent_component_id`), not `id2`.
- **No name-versioning.** `_2`, `_old`, `_copia_20120605` are SSOT violations — they don't exist in a
  clean model; history belongs in a history table (er-modeling §A2.6) or VCS, not in object names.

## 4. Normalization targets

- **3NF is the default** ([er-modeling §A2.1](er-modeling.md#a21-normalization-applied-to-the-er-model)). Every non-key attribute
  depends on the key, the whole key, and nothing but the key.
- **BCNF** where a relation has overlapping candidate keys.
- **1NF is non-negotiable**: atomic columns. No CSV/pipe-delimited strings, no numbered column
  families, no polymorphic `value`/`payload` columns. Use a proper child table, or — only when the
  data is genuinely schemaless and not queried relationally — `jsonb` (typed, indexable) rather than a
  delimited string.
- **Denormalize only deliberately**: against a *proven* read path, documented, and kept consistent by
  a clear mechanism (generated column, materialized view, or controlled trigger) — never by accident.
  This is where a derived attribute (er-modeling §A1.4) may become stored.

## 5. Integrity by construction

Let the database enforce what the database can enforce:

- **Referential integrity**: declare every real relationship as a `FOREIGN KEY`. Choose cascade
  behavior explicitly (`ON DELETE RESTRICT` by default; `CASCADE` only when the child truly cannot
  outlive the parent — the dependent-entity case of er-modeling §A1.5).
- **Domain integrity**: `NOT NULL` wherever the attribute is mandatory (`*`) in the model; `CHECK`
  constraints for bounded domains; lookup tables or `enum` types for categoricals (replacing `char(1)`
  flags).
- **NULL means missing** — never sentinel magic values (`'9999-12-31'`, `''`, `0`).
- **Migration aid**: PostgreSQL 18 lets you declare constraints `NOT ENFORCED`, then `VALIDATE` them
  later — load legacy data fast, then turn integrity on once cleaned. Use this deliberately, and
  don't ship a schema that stays `NOT ENFORCED`.

### 5.1 Arcs and subtypes in PG18

- **Arcs** → explicit FK columns + `CHECK (num_nonnulls(individual_id, company_id) = 1)` (`<= 1` if
  the arc is optional). No generic `ref_type` + `ref_id` pairs.
- **Subtypes** → choose per er-modeling §A3.2 step 6. In a single table, enforce each subtype's mandatory columns
  with a `CHECK` keyed on the type column. In supertype + subtype tables, give the supertype a
  `UNIQUE (id, kind)` and have each subtype table reference `(id, kind)` with its `kind` fixed by a
  `CHECK` — exclusivity is then enforced by the database.

### 5.2 History and time

- Validity periods as **range types** (`daterange`, `tstzrange`) rather than loose from/to pairs.
- **PG18 temporal constraints**: `PRIMARY KEY (part_id, valid_during WITHOUT OVERLAPS)` /
  `UNIQUE (… WITHOUT OVERLAPS)` forbid overlapping periods for the same key, and
  `FOREIGN KEY (part_id, PERIOD valid_during) REFERENCES …` checks the child's period is covered by the
  parent's. (Scalar columns in these constraints need the `btree_gist` extension.)
- **No-gap** rules (er-modeling §A2.6, drills 12 and 24) are not expressible as a key; enforce them in the write path
  (close the previous period in the same transaction that opens the next) and verify with a check query.

## 6. Data types (PostgreSQL 18)

| Use | Not |
|---|---|
| `text` (or `varchar(n)` only with a real business bound) | `char(n)` padding; reflexive `varchar(255)` |
| `integer` / `bigint` for identifiers and codes | `numeric(n,0)` or `float` as IDs |
| `numeric(p,s)` for money and exact quantities | `float`/`real` for money |
| `timestamptz` for points in time | naive `timestamp`/legacy `datetime` |
| `daterange` / `tstzrange` for validity periods | separate `desde`/`hasta` columns with no constraint |
| `boolean` for flags | `char(1)` `'S'/'N'` |
| `uuid` for surrogate keys (via `uuidv7()`) | `uniqueidentifier`-as-string |
| `bytea` for binary; `text` for long text | deprecated `text`/`ntext`/`image` |
| `jsonb` for genuinely schemaless data | JSON/CSV stuffed in a `text` column |
| **Generated columns** (PG18 supports `STORED` and `VIRTUAL`) for derived values | hand-maintained denormalized copies |

## 7. Indexing strategy (Winand, applied to PG)

- **Index every foreign key column** — PostgreSQL does not do it automatically.
- **Composite column order**: equality predicates first, then range/sort columns. (Note: PostgreSQL
  18's **B-tree skip scan** relaxes some leftmost-prefix penalties, but deliberate order still wins.)
- **Covering indexes** via `INCLUDE` for hot, read-only projections.
- **Partial indexes** (`WHERE`) for selective subsets — the right answer to many low-cardinality
  flags instead of indexing the whole column.
- **Expression indexes** for functional predicates (`lower(email)`), so filters stay sargable instead
  of suppressing the index.
- **GiST** indexes back range/temporal constraints (§5.2); recursive FKs get a plain B-tree so
  `WITH RECURSIVE` hierarchy walks stay cheap.
- Don't over-index: every index is a write tax. No index that merely duplicates the primary key.

## 8. Collation & encoding

- One database, `UTF-8` encoding, **one** collation strategy — ending any legacy collation split
  (e.g. `Modern_Spanish_CI_AS` beside `SQL_Latin1_General_CP1_CI_AS`) that suppresses cross-domain
  joins.
- Pick a provider deliberately: PostgreSQL's `builtin` `C.UTF-8` (fast, stable, version-independent)
  for ordering, or `ICU` for locale-aware sorting.
- For case-insensitive matching, use a **nondeterministic collation** or `citext` on the specific
  columns that need it — not a blanket CI collation across the whole estate.

## 9. Where logic lives

- **Business logic → application/service layer.** The database is not an application framework.
- **The database enforces invariants** (constraints) and performs **set-based data operations**
  (views, set-based functions).
- **Triggers only for true data invariants**, written **set-based and multi-row-safe** (PostgreSQL
  fires statement-level and row-level triggers; prefer statement-level set logic, and never assume a
  single affected row). No hidden side-effects mutating unrelated tables — those move to the service
  layer where they are visible and testable.
- **Derived attributes** are computed by query, a generated column or a materialized view — not by a
  trigger keeping a `total_*` column in step.
- **Cursors/RBAR → set-based SQL.** A loop that updates row-by-row becomes one `UPDATE … FROM …`.
  Hierarchy walks become `WITH RECURSIVE`.

## 10. Views, materialized views, partitioning, scale

- **Views** for abstraction; shallow, explicit column lists, no fake `TOP 100 PERCENT … ORDER BY`.
  Ordering belongs in the consuming query. Views are also how a single-table subtype design exposes
  each subtype, and how a separate-tables design exposes the supertype (`UNION ALL`, read-only).
- **Materialized views** for expensive, slowly-changing aggregates; refresh `CONCURRENTLY` on a
  schedule.
- **Declarative partitioning** for large/time-series tables (attendance, time logs, ledgers, audit history)
  — by range (date) or list (domain), enabling partition pruning and cheap archival.
- PostgreSQL 18's **asynchronous I/O** improves large scan/maintenance throughput; design large
  tables (partitioning, fillfactor tuned to write volatility) to take advantage rather than carrying
  the legacy blanket `FILLFACTOR = 100`.

## 11. Modeling checklist

| # | The model… | Good = 🟢 |
|---|---|---|
| 1 | passed conceptual → logical → physical | not grown table-by-table; an ER model exists per domain |
| 2 | reads aloud | every relationship has a two-way sentence; no *related to* / *associated with* |
| 3 | has no unresolved M:M | every M:M is an intersection entity with mandatory relationships out of it |
| 4 | has no derived attributes in the model | totals/counts/averages computed, or stored by a documented physical decision |
| 5 | uses UIDs that meet er-modeling §A1.5; surrogate PKs; natural keys are `UNIQUE` | no volatile-natural-key or intelligent-key PKs |
| 6 | is ≥ 3NF (BCNF where keys overlap); 1NF strict | no CSV/polymorphic columns, no numbered column families |
| 7 | models recursion, subtypes and arcs explicitly | recursive FKs optional; arcs = explicit FKs + `CHECK`; subtype mapping chosen and justified |
| 8 | models history only where the user asked for it | time in the UID; overlaps forbidden by constraint; gap rule stated |
| 9 | enforces FK / CHECK / NOT NULL | integrity in the DB, not the app |
| 10 | uses NULL, never magic values | no `'9999…'`/`''`/`0` sentinels |
| 11 | uses correct PG18 types | per the type table above |
| 12 | indexes FKs; sargable predicates | no suppressed indexes, no redundancy |
| 13 | one encoding + one collation strategy | no collation split |
| 14 | keeps business logic in the app layer | DB enforces, app decides |
| 15 | consistent `snake_case` + role-named constraints | no name-versioning; one abbreviation per concept |
| 16 | is documented with TIDs for core tables | key type, `NN`/`U` marks and sample rows agree |
