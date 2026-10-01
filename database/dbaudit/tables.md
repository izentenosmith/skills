# Tables — Schema Integrity & Storage Architecture

> Criteria for grading `tables.sql` (or the `CREATE TABLE` statements wherever they live). Tables are
> the foundation of the data model; evaluate them for violations of relational theory (see
> [`theory.md`](theory.md)), for modelling decisions that were never made (see
> [`er-modeling.md`](er-modeling.md)), and for signs of physical storage decay. Severity
> levels follow [`scoring.md`](scoring.md); each anti-pattern's detection command and confidence tag
> (✅ decidable / ⚠️ proxy / 🔬 needs-data) live in [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- Every table has a **primary key** (entity integrity); the key is stable and minimal.
- **Surrogate keys** (`IDENTITY`, `SEQUENCE`, or `uniqueidentifier`/`uuid`) used where natural keys
  are volatile, so foreign keys stay stable across business change.
- Columns are **typed to their domain** — narrowest correct type, `NOT NULL` wherever a value is
  logically required, `CHECK` constraints for bounded domains (domain integrity).
- Foreign keys declared (`FOREIGN KEY … REFERENCES`) so referential integrity is enforced by the
  engine, not by application convention.
- Each table reads back as a clean model: one entity, single-valued attributes, relationships you can
  phrase as sentences, subtypes and arcs mapped deliberately.
- **One collation** used consistently across everything that is joined.
- Naming is consistent for tables, columns, and constraints.

## 🔴 Not well done

### Missing primary key — entity-integrity violation
**What:** A table with no `PRIMARY KEY`. Rows are not uniquely identifiable; duplicates and orphans
become possible.
**Why:** Direct violation of entity integrity (theory §7). Breaks reliable updates, replication, and
FK targeting.
**Detect:** `CREATE TABLE` blocks with no `PRIMARY KEY` / `CONSTRAINT … PRIMARY KEY`.
**Example:** a sections table declared with `dept_code`, `section_code`, `description`, `flag_active`
and **no constraint at all** — usually beside a near-identical sibling that does have one.
**Severity:** High.

### Volatile natural keys instead of surrogate keys
**What:** Primary keys built on business-meaningful, changeable values (string codes, names, location
codes, personnel file numbers).
**Why:** The UID fails the *invariant* criterion (er-modeling §A1.5): when the business value
changes, every FK referencing it must change too — or silently breaks.
**Detect:** PKs on `char`/`varchar`/code columns rather than an `IDENTITY`/numeric surrogate.
**Example:** a department table keyed on `dept_code numeric(4,0)`; a personnel table keyed on the
employee's file number.
**Severity:** Medium.

### Nullability & "magic value" abuse
**What:** Columns nullable that logically shouldn't be, or sentinel values used to fake "missing":
`'9999-12-31'` / `'0000-00-00'` for dates, `''` for strings, `0` for unknown codes.
**Why:** Magic values defeat `NULL` semantics, corrupt aggregates and comparisons, and hide missing
data from integrity checks.
**Detect:** `DEFAULT ''`, `DEFAULT '9999…'`, broad `NULL` on columns that are conceptually mandatory.
**Example:** `flag_declares_hours char(1) DEFAULT 'S' NULL` — defaulted *and* nullable, typed `char(1)`
rather than a constrained domain.
**Severity:** Medium.

### Data-type mis-sizing
**What & why:**
- `char(n)` for variable-length text → blank-padding, surprising `=`/`LIKE`/`LEN` behaviour, wasted
  storage. Prefer `varchar`.
- `numeric(4,0)` / `float` used as identifiers and codes → `float` is inexact (never use for
  IDs/money); fixed `numeric` codes should be `int`.
- Uniform oversized `varchar(255)` applied by reflex to every text column → no domain meaning, larger
  row estimates.
- Legacy `datetime` where `datetime2` / `datetimeoffset` is correct (range, precision, time-zone).
- 🔬 *needs-data:* `INT` surrogate keys on high-growth tables approaching the 2.14B ceiling →
  migrate to `BIGINT`. Growth/row-count is not in the DDL — flag for data review, do not score.
**Detect:** `char(` on free text; `float`/`numeric(n,0)` on `*_id`/`cod_*`; bulk `varchar(255)`.
**Example:** `last_name char(20)`, `description char(50)`, a stock `QUANTITY float`.
**Severity:** Medium (High when `float` is used for money/quantities).

### Deprecated large-object types ✅
**What:** Columns typed `text`, `ntext`, or `image` (SQL Server; `LONG`/`LONG RAW` on Oracle).
**Why:** Deprecated (superseded by `varchar(max)`, `nvarchar(max)`, `varbinary(max)`); they block many
string functions, complicate replication, and signal a schema frozen in a pre-2005 era.
**Detect:** `text` / `ntext` / `image` column types.
**Severity:** Medium.

### Polymorphic / generic column trap
**What:** Generic columns (`payload`, `misc_data`, `config_blob`, `value`) storing CSV, pipe-arrays,
or JSON in a system that needs transactional querying.
**Why:** 1NF violation — non-atomic attributes. The data is unindexable and unjoinable without
parsing.
**Detect:** wide `varchar`/`text`/`image`/`varbinary` columns with generic names; values that are
clearly delimited.
**Severity:** High.

### Repeating groups — numbered column families (1NF)
**What:** A table carrying the same fact in numbered slots: `course_number_1`, `course_number_2`,
`course_number_3`; `phone1`/`phone2`; `boss_1`/`boss_2` for hierarchy levels.
**Why:** 1NF violation at the model level — the attribute is multi-valued, which means an **entity is
missing** (er-modeling §A1.4, §A2.1). The slot count is an arbitrary business limit, the slots
can't be indexed or joined as one set, and "is X in any slot?" needs an `OR` per slot.
**Detect:** column names that differ only by a trailing digit within one table.
**Severity:** High (the same defect as a CSV column, spread across columns instead of inside one).

### Generic arc / polymorphic foreign key
**What:** A pair of columns where one holds an id and the other says *which table* it points at
(`ref_type` + `ref_id`, `origin` + `origin_id`), so the "foreign key" targets a different table row by
row.
**Why:** er-modeling §A3.2 step 5 calls this a **generic arc**. Exclusivity is implicit, but
referential integrity **cannot be declared** — no engine can enforce an FK whose target varies per row,
so orphans accumulate. The explicit arc (one FK column per target + an exclusivity `CHECK`) keeps both
guarantees.
**Detect:** a `tipo_*`/`*_type`/`origin` column beside an `id_*` column that has no `FOREIGN KEY`; read
the procedures that write it to confirm the target varies.
**Severity:** High.

### Explicit arc with no exclusivity guarantee
**What:** Two or more nullable FK columns that the business says are mutually exclusive (`person_id`
**or** `company_id`), with no `CHECK` forbidding both or neither.
**Why:** The arc rule (er-modeling §A2.5) lives only in application code; a row holding both, or
neither, is storable.
**Detect:** ≥ 2 nullable FK columns on one table naming alternative holders; no `CHECK` over them.
⚠️ proxy — whether they are truly exclusive is a business fact.
**Severity:** Medium.

### Mis-mapped relationships — 1:1 without `UNIQUE`, mandatory recursion, duplicate pairs
**What & why:**
- A relationship the model says is **1:1** mapped as a plain FK with no `UNIQUE` — the database
  silently permits 1:M (er-modeling §A3.2 step 4).
- A **self-referencing FK declared `NOT NULL`** — a recursive relationship must be optional at both
  ends, or the hierarchy has no root (§A2.2). Usually papered over with a magic root row that
  references itself.
- An intersection table (resolved M:M) with **no uniqueness on its parent-key pair** — the same pair
  can be inserted twice.
**Detect:** self-referencing `FOREIGN KEY … REFERENCES <same table>` on a `NOT NULL` column ✅;
two-FK tables with no PK/`UNIQUE` over both FKs ✅; 1:1 intent is ⚠️ (needs the model or the code).
**Severity:** Medium (High for the intersection-table duplicate, which corrupts counts and sums).

### Stored derived attributes
**What:** Columns holding values computable from other rows — `total_*`, `qty_total`, `average_*`,
a `balance` next to the movements it sums — maintained by procedures or triggers.
**Why:** Derived attributes are redundant by definition (§A1.4). Every writer must keep them in step,
and the triggers that do it are where multi-row data-loss defects tend to live. Storing one can be a
valid *physical* choice, but only documented and kept consistent by mechanism.
**Detect:** aggregate-sounding names, then confirm a procedure/trigger recomputes them. ⚠️ proxy.
**Severity:** Medium.

### Hidden subtypes in a single table
**What:** One table holding several kinds of thing, flagged by a type column, with blocks of columns
that are only ever filled for one kind — and nothing enforcing which.
**Why:** A single-table subtype mapping (er-modeling §A3.2 step 6) is legitimate, but without a per-type `CHECK` the
subtype's mandatory attributes are unenforced and invalid combinations are storable.
**Detect:** a `tipo_*`/`*_type` column plus many nullable columns; no `CHECK` referencing the type.
⚠️ proxy.
**Severity:** Medium.

### Collation conflict / implicit conversion
**What:** Text columns declared under **different collations** across tables or databases that get
joined.
**Why:** A join on mismatched text collations forces the engine to apply a runtime implicit conversion
to one side, which **suppresses index usage** and forces a CPU-heavy scan — and can raise outright
collation-conflict errors.
**Detect:** compare declared `COLLATE` clauses across catalogs (`grep … | sort | uniq -c` — more than
one value across joined tables is the finding).
**Severity:** High.

### Shadow / ad-hoc backup tables — SSOT violation
**What:** Dated copy tables and name-versioned duplicates persisted in the live schema.
**Why:** Violates Single Source of Truth (theory §6) — the copies drift, and nobody can tell which is
authoritative.
**Detect:** names like `*_COPIA_<date>`, `*_BAK`, trailing `_`/`2`/`_old`, near-duplicate definitions.
**Example:** `STOCK_PROJECTS_COPY_20120605_B` (a years-old backup left in place); `PERSONNEL2` beside
`PERSONNEL`; `SECTIONS_` beside `SECTIONS`.
**Severity:** Medium (a whole *copy database* escalates this to an estate-level finding — see
[`audit-lenses.md`](audit-lenses.md)).

### Schema hygiene
**What:** Tooling junk and inconsistent naming.
**Detect / examples:** `dtproperties` (a SQL Server diagram-tooling table) persisted in the schema;
constraint naming that mixes conventions — `DEPARTMENTS_PK`, `PK_employee_master`, `pk_dtproperties`
all in one file.
**Severity:** Low.

## A note on normal forms

Of the normal forms in [`theory.md`](theory.md), only **1NF** is reliably checkable from static DDL —
non-atomic / CSV / polymorphic columns and numbered column families show up in the schema text.
**2NF, 3NF, BCNF, and 4NF** violations are transitive/partial/multivalued *dependencies among the
data*; confirming them requires data profiling, so they are 🔬 **needs-data**. This rubric flags likely
candidates (e.g. a `dept_name` next to a `dept_code` on an employee table) but does not grade deep
normalization from DDL alone.

## A note on the ER model behind the tables

Every table is the residue of a modelling decision (theory §9; er-modeling.md). When grading,
reverse-engineer the model as you go (er-modeling §A0): phrase each FK as a two-way relationship
sentence, test each PK against the UID criteria, and look for the constructs that were never modelled —
missing entities behind repeating groups, M:M resolved without uniqueness, arcs and subtypes encoded in
type columns. Those findings feed the rework verdicts in [dbpropose](../dbpropose/SKILL.md) directly.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Primary key present and minimal | every table has a declared PK |
| 2 | Surrogate key where natural key is volatile | no PK on changeable business values |
| 3 | No magic-value sentinels; correct nullability | NULL means missing; no `'9999…'`/`''` proxies |
| 4 | Right-sized types | `varchar` for variable text; `int`/`bigint` for IDs; no `float` IDs/money |
| 5 | No deprecated LOB types | no `text`/`ntext`/`image` |
| 6 | No polymorphic/CSV/JSON columns or repeating-group column families (1NF) | attributes atomic; no `x_1`/`x_2`/`x_3` slots |
| 7 | Single, consistent collation | one `COLLATE` across joined tables |
| 8 | No shadow/backup/versioned tables | no `*_COPIA_*` / `*2` / `*_old` in live schema |
| 9 | FK declared for real relationships, mapped to their model | referential integrity engine-enforced; no generic arcs; 1:1 FKs `UNIQUE`; recursive FKs nullable; intersection pairs unique |
| 10 | Consistent table/column/constraint naming | one convention |
