# Tables — Schema Integrity & Storage Architecture

> Criteria for grading `tables.sql` (or the `CREATE TABLE` statements wherever they live). Tables are
> the foundation of the data model; evaluate them for violations of relational theory (see
> [`theory.md`](theory.md)), for modelling decisions that were never made (see
> [`er-modeling.md`](er-modeling.md)), and for signs of physical storage decay. Severity
> levels follow [`scoring.md`](scoring.md); each anti-pattern's detection command and confidence tag
> (✅ decidable / ⚠️ proxy / 🔬 needs-data) live in [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- Every table has a **primary key** (entity integrity); the key is stable and irreducible, and every
  other candidate key is declared `UNIQUE` (theory §2.1).
- **Surrogate keys** (`IDENTITY`, `SEQUENCE`, or `uniqueidentifier`/`uuid`) used where natural keys
  are volatile — with the natural key kept as `UNIQUE`, so foreign keys stay stable and the same
  entity can't be inserted twice.
- Columns are **typed to their concept** — narrowest correct type, one declared type per concept across
  tables, `NOT NULL` wherever a value is logically required, `CHECK` constraints for bounded domains
  (domain integrity).
- Every nullable column has **one documented meaning** for NULL (theory §3.2).
- Foreign keys declared (`FOREIGN KEY … REFERENCES`) so referential integrity is enforced by the
  engine, not by application convention.
- Each table reads back as a clean model: one entity, single-valued attributes, a predicate you can
  write as one sentence, relationships you can phrase as sentences, subtypes and arcs mapped
  deliberately.
- Data and metadata are separate: no attribute names stored as rows, no data values in table or column
  names (theory §10).
- **One collation** used consistently across everything that is joined.
- Naming is consistent for tables, columns, and constraints.

## 🔴 Not well done

### Missing primary key — entity-integrity violation
**What:** A table with no `PRIMARY KEY`. Rows are not uniquely identifiable; duplicates and orphans
become possible.
**Why:** Direct violation of entity integrity (theory §7) — the table is not a relation (§1.1). It breaks
reliable updates and FK targeting, and replication: a row-based change log identifies updated and
deleted rows by primary key, so without one every change must log the whole old row (PostgreSQL logical
replication refuses `UPDATE`/`DELETE` without a replica identity) and no CDC consumer can match rows.
**Detect:** `CREATE TABLE` blocks with no `PRIMARY KEY` / `CONSTRAINT … PRIMARY KEY`.
**Example:** a sections table declared with `dept_code`, `section_code`, `description`, `flag_active`
and **no constraint at all** — usually beside a near-identical sibling that does have one.
**Severity:** High.

### Reducible key — a primary or unique key that is a proper superkey
**What:** A PK or `UNIQUE` whose column set strictly contains another declared PK/`UNIQUE` on the same
table (`PRIMARY KEY (emp_id, dept_id)` beside `UNIQUE (emp_id)`), or a composite PK one of whose
components the business says is unique on its own, with no single-column `UNIQUE`.
**Why:** Keys are irreducible (theory §2.1). A reducible PK either duplicates a real key (a redundant
index, a wrong FK target) or *replaces* it — then the true key is unenforced and duplicates of it are
storable.
**Detect:** ✅ a PK/`UNIQUE` column set that is a strict superset of another on the same table **and**
is not itself an FK target (an FK-target superkey like `UNIQUE (id, kind)` is a deliberate device —
physical-design §5.1). ⚠️ a composite PK with no single-column `UNIQUE` where a component is named like
the table's own identifier (`<table>_id`, `codigo`).
**Severity:** Medium (High when the true key is unenforced).

### Surrogate key with no alternate key
**What:** A table whose only uniqueness is an `IDENTITY`/`SEQUENCE`/`uuid` PK while the entity has a
natural identifier (a code, a document number, name + date) that carries no `UNIQUE`.
**Why:** Entity integrity of the *thing* is lost — the same customer can be inserted twice under two
ids — and dependency analysis over the surrogate is meaningless (theory §2.1).
**Detect:** ✅ structural: a surrogate PK and no `UNIQUE` constraint or unique index on the table. ⚠️
judgement: whether a natural identifier exists (er-modeling §A1.5).
**Severity:** Medium (High for master and reference entities).

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
`'9999-12-31'` / `'0000-00-00'` for dates, `''` for strings, `0` or `-1` for unknown numbers — and
**placeholder parent rows** (an `UNASSIGNED` account, id `0`) created so a `NOT NULL` FK always has
something to point at.
**Why:** A sentinel is a NULL that also lies (theory §3.2): it compares, sorts and sums as a real value,
corrupts aggregates, and hides missing data from integrity checks. A placeholder parent means the FK
should be nullable — NULL there means "not yet assigned".
**Detect:** `DEFAULT ''`, `DEFAULT '9999…'`, `DEFAULT -1`; `*_id … NOT NULL DEFAULT 0|-1`; a parent row
inserted by a seed script with id `0`/`-1`; broad `NULL` on conceptually mandatory columns.
**Not a finding (⚠️, Low):** `'9999-12-31'` as the open end of a validity-period pair is a recognized
convention — grade it "prefer an unbounded range" (physical-design §5.2), not 🔴. On Oracle `''` *is*
NULL, so an empty-string sentinel can't exist there.
**Example:** `flag_declares_hours char(1) DEFAULT 'S' NULL` — defaulted *and* nullable, typed `char(1)`
rather than a constrained domain.
**Severity:** Medium.

### Overloaded or unexplained NULL
**What:** A nullable column whose NULL must stand for more than one thing — unknown *and* not
applicable *and* not yet — or whose meaning is undocumented: typically a nullable column meaningful only
for some values of a `tipo_*` column, or a nullable `fecha_fin`/`hasta` meaning both "still open" and
"not recorded".
**Why:** The table's predicate becomes a disjunction (theory §3.2): queries silently mix the cases
(`IS NULL` counts "unknown" with "n/a"), some questions become unanswerable, and three-valued logic
makes `NOT IN`, `<>`, `CHECK` and outer-join results surprising.
**Detect:** ⚠️ a nullable column beside a type column with no `CHECK` relating them; a nullable end
date beside a start date; procedures that `COALESCE`/`ISNULL` the same column to different defaults in
different places. 🔬 the intended meaning needs the business.
**Severity:** Medium.

### Constraints that don't hold what they say
**What & why:**
- **Partial-NULL composite FK** ✅ — a multi-column `FOREIGN KEY` whose columns are nullable
  independently, with no `MATCH FULL` (PG) or `CHECK (num_nulls(a, b) IN (0, 2))`. Under the default
  `MATCH SIMPLE` one NULL column disables the whole check (theory §3.2).
- **`CHECK` on a nullable column meant to be mandatory** ⚠️ — the `CHECK` passes on UNKNOWN, so NULL is
  admitted as a valid value.
- **`CHECK` delegating to a cross-table function** ⚠️ — `CHECK (posted = 0 OR dbo.sum_entries(id) =
  0)`. It is evaluated only when *this* row changes, never when the rows the function reads change, and
  it isn't concurrency-safe: integrity independence (Codd rule 10) is faked. It is an aggregate rule
  (theory §7.1) for physical-design §5.3.
- **Time-relative `CHECK`** ✅ — `CHECK (due_date >= GETDATE())`. A constraint must be a property of the
  stored data; this one is a property of *when the row was written*, so `VALIDATE`, re-enabling with
  `WITH CHECK`, or a PostgreSQL restore (which recreates `CHECK`s before loading) rejects rows that were
  valid when written. "Not in the past when entered" belongs in the write path.
**Severity:** High for the partial-NULL FK and the cross-table `CHECK` (gaps that look enforced);
Medium for the others.

### Data-type mis-sizing
**What & why:**
- `char(n)` for variable-length text → blank-padding, surprising `=`/`LIKE`/`LEN` behaviour, wasted
  storage. Prefer `varchar`/`text`; `char(n)` is defensible only for a truly fixed-length code.
- `numeric(4,0)` / `float` used as identifiers and codes → `float` is inexact (never use for
  IDs/money); fixed `numeric` codes should be `int`.
- `float`/`real`/`double` on money or quantity columns → values like 59.95 aren't representable;
  errors accumulate in `SUM` and compound in repeated multiplication, and equality tests in code fail.
  On Oracle `FLOAT` is an exact decimal; the inexact types there are `BINARY_FLOAT`/`BINARY_DOUBLE`.
- Uniform oversized `varchar(255)` applied by reflex to every text column → no domain meaning, larger
  row estimates.
- Legacy `datetime` where `datetime2` / `datetimeoffset` is correct (range, precision, time-zone); on
  PostgreSQL a naive `timestamp` for an event instant instead of `timestamptz`.
- 🔬 *needs-data:* `INT` surrogate keys on high-growth tables approaching the 2.14B ceiling →
  migrate to `BIGINT`. Growth/row-count is not in the DDL — flag for data review, do not score.
**Detect:** `char(` on free text; `float`/`numeric(n,0)` on `*_id`/`cod_*`; `float`/`real` on
money/quantity-named columns; bulk `varchar(255)`.
**Example:** `last_name char(20)`, `description char(50)`, a stock `QUANTITY float`.
**Severity:** Medium (High when an inexact type holds money or quantities).

### Representation-typed column and type drift
**What:** A column typed by how its value happens to be written rather than what it is — dates as
`char(8)`/`int` (`YYYYMMDD`), times as `varchar`, booleans as `char(1)`, amounts as `varchar` — and the
same concept declared with different names, types or lengths across tables (`zip char(5)` here,
`postal_code varchar(10)` there), including an FK whose type differs from the key it references.
**Why:** Domain integrity (theory §7): a type is its values and the operations that make sense on them.
A date stored as text permits `'20241399'`, sorts and compares as text, and pushes conversion into
every query — an implicit conversion on the column side suppresses its index (indexes.md, *Non-sargable
predicates*). Two names for one concept also hide that a relationship exists (er-modeling §A0).
**Detect:** ⚠️ date/time-named columns typed `char`/`varchar`/`int`/`numeric`; group `(column, type)`
pairs across every `CREATE TABLE` by name or known synonym (`zip|postal|cp|codigo_postal`) and list
names with more than one type or length. ✅ an FK column whose type or length differs from the
referenced key column.
**Severity:** Medium (High for a join key or for dates and amounts used in range predicates).

### Deprecated large-object types ✅
**What:** Columns typed `text`, `ntext`, or `image` (SQL Server; `LONG`/`LONG RAW` on Oracle).
**Why:** Deprecated (superseded by `varchar(max)`, `nvarchar(max)`, `varbinary(max)`); they block many
string functions, complicate replication, and signal a schema frozen in a pre-2005 era. On PostgreSQL
`text` is the recommended type — this finding does not apply.
**Detect:** `text` / `ntext` / `image` column types in SQL Server dumps.
**Severity:** Medium.

### Polymorphic / generic column trap — hidden lists (1NF)
**What:** Generic columns (`payload`, `misc_data`, `config_blob`, `value`) storing CSV, pipe-arrays,
or JSON in a system that needs transactional querying — and lists of foreign ids under ordinary names
(`account_id varchar(500)` holding `12,15,40`).
**Why:** 1NF — the column hides a set of facts that must be keyed, referenced and queried element by
element (theory §3). The elements can't be indexed, joined, typed or given a foreign key, and every
query has to parse them.
**Detect:** wide `varchar`/`text`/`image`/`varbinary` columns with generic names; an `*_id`/`id_*`/
`cod_*` column typed as a string wider than any key it could hold, or named `*_ids`/`*_list`/`lista_*`;
in code, list parsing on that column (`CHARINDEX(','`, `STRING_SPLIT`, `LIKE '%,' + … + ',%'`,
`FIND_IN_SET`, `string_to_array`).
**Not a finding:** a list received from and returned to an external system verbatim, never queried by
element; a `jsonb` document nothing constrains or joins element-wise.
**Severity:** High.

### Entity–Attribute–Value (EAV, "open schema") table
**What:** A table that stores attributes as rows: an entity FK, an attribute-name column (`attr_name`,
`property`, `field_name`, `atributo`) and a generic value column (`attr_value`, `valor`, or
`value_int`/`value_date`/`value_str` siblings), so each "column" of the real entity is a row whose name
is a string.
**Why:** Metadata stored as data (theory §10), and the value column means something different on every
row (1NF, theory §3). Every guarantee the engine gives a column is lost: no `NOT NULL` for a mandatory
attribute, no type (dates stored as text in any format), no `FOREIGN KEY` on one attribute's values, no
control of attribute spelling. Rebuilding one entity row needs one outer join per attribute.
**Detect:** ⚠️ a table whose non-key columns are only {entity FK, name column, value column(s)}; in
code, many `attr_name = '<literal>'` filters, `MAX(CASE WHEN attr_name = …)` or `PIVOT` over it.
**Not a finding (Low):** a small parameter/settings table keyed by setting name with a fixed,
documented set of keys (audit-lenses §5).
**Severity:** High; Medium when confined to genuinely user-defined attributes nothing queries
relationally.

### Repeating groups — numbered column families (1NF)
**What:** A table carrying the same fact in numbered slots: `course_number_1`, `course_number_2`,
`course_number_3`; `phone1`/`phone2`; `boss_1`/`boss_2` for hierarchy levels.
**Why:** 1NF violation at the model level — the attribute is multi-valued, which means an **entity is
missing** (er-modeling §A1.4, §A2.1). The slot count is an arbitrary business limit, the slots
can't be indexed or joined as one set, and "is X in any slot?" needs an `OR` per slot.
**Detect:** column names that differ only by a trailing digit within one table; in code,
`col1 = @x OR col2 = @x OR …` or `@x IN (col1, col2, col3)`.
**Not a finding:** columns that point at the same table but play **different roles** (`reported_by`,
`assigned_to`, `verified_by`) — each is its own relationship (er-modeling §A2.3). The test is *same
meaning in numbered slots* vs *different meaning per column*.
**Severity:** High (the same defect as a CSV column, spread across columns instead of inside one).

### Per-value clones — tables or columns named by a data value
**What:** One logical table split into same-shaped live tables named by a data value (`ventas_2022`,
`ventas_2023`; `orders_acme`, `orders_globex`; `cliente` / `cliente_vip`), or one column split into
columns named by a value (`revenue2002`, `revenue2003`).
**Why:** Data promoted to metadata (theory §10) and a physical split leaking into the logical schema
(Codd rule 8). New data needs new DDL; a row can sit in the wrong clone, or in two — the tables'
predicates overlap (*orthogonal design*); keys are unique per clone, not across the set; **no foreign
key can reference the set**; every cross-period query is a `UNION` edited each year; clones drift apart
in columns. Distinct from shadow copies (SSOT): these are all live and written.
**Detect:** ⚠️ `CREATE TABLE` names ending in a year, year-month, quarter, or a tenant/region/tier token,
shared by ≥ 2 tables with near-identical column lists; columns differing only by a year; a view that
`UNION ALL`s them; dynamic SQL building a table name from a variable. ✅ no `CHECK` on the splitting
column in each clone.
**Not a finding:** PostgreSQL declarative partitions (`CREATE TABLE … PARTITION OF …`); a SQL Server
*partitioned view* whose members each carry a disjoint `CHECK` (confirm before grading); a documented
archive never queried with the live table; a deliberate database-per-tenant topology.
**Severity:** High when a clone is an FK parent or child (RI undeclarable); otherwise Medium.

### Volatile value list frozen in the column definition
**What:** A business category (status, state, type, category) restricted by `CHECK (col IN (…))`,
`ENUM(…)`, a domain or a validating trigger, where the business can add, rename or retire values.
**Why:** The set of valid values is information living in metadata (theory §10): it can't be listed
with a `SELECT`, every new value is a DDL change, retired values can't be marked obsolete, and
application copies of the list drift. Integrity is enforced — this is a maintainability defect.
**Detect:** ⚠️ `CHECK … IN (` / `ENUM(` / `CREATE TYPE … AS ENUM` on columns named `*status*`,
`*state*`, `*type*`, `*category*`, `estado`, `tipo`; the same literal list repeated in procedure
`IF … NOT IN (…)` checks.
**Not a finding:** two-valued or definitionally closed sets (a calendar unit, an ISO code set you
never edit).
**Severity:** Low (Medium when the same list is duplicated in code).

### Relationship by convention — no declared foreign key
**What:** A column that refers to another table's key (`id_department`, `customer_code`, a column named
like another table's PK) with no `FOREIGN KEY` declared.
**Why:** Referential integrity left to flawless code (theory §7; Codd rule 10). Every writer must check
the parent, the check-then-write race needs locks (theory §5.2), and orphans accumulate — later "fixed"
by cleanup queries that can't always say which parent an orphan should have. A schema that *can't*
take FKs is often a clue to EAV or a generic arc.
**Detect:** ⚠️ two-pass: collect each table's PK column names; flag columns elsewhere with the same name
(or `<table>_id` / `id_<table>` / `cod_<table>`) that appear in no `FOREIGN KEY`. Corroborate with code:
`IF EXISTS (SELECT … FROM <parent>)` before an `INSERT`, and orphan-cleanup
`DELETE … LEFT JOIN … WHERE <parent key> IS NULL`.
**Severity:** High.

### Generic arc / polymorphic foreign key
**What:** A pair of columns where one holds an id and the other says *which table* it points at
(`ref_type` + `ref_id`, `origin` + `origin_id`, `commentable_type` + `commentable_id`), so the "foreign
key" targets a different table row by row.
**Why:** er-modeling §A3.2 step 5 calls this a **generic arc** — metadata stored as data (theory §10).
Exclusivity is implicit, but referential integrity **cannot be declared** — no engine can enforce an FK
whose target varies per row, so orphans accumulate. The fix depends on what the targets share
(er-modeling §A3.2 step 5): often a missing supertype, sometimes an explicit arc.
**Detect:** a `tipo_*`/`*_type`/`*able_type`/`origin` column beside an `id_*` column that has no
`FOREIGN KEY`; a `CHECK` listing table names; read the procedures that write it to confirm the target
varies.
**Severity:** High.

### Explicit arc with no exclusivity guarantee
**What:** Two or more nullable FK columns that the business says are mutually exclusive (`person_id`
**or** `company_id`), with no `CHECK` forbidding both or neither.
**Why:** The arc rule (er-modeling §A2.5) lives only in application code; a row holding both, or
neither, is storable.
**Detect:** ≥ 2 nullable FK columns on one table naming alternative holders; no `CHECK` over them.
⚠️ proxy — whether they are truly exclusive is a business fact.
**Severity:** Medium.

### Mis-mapped relationships — 1:1 without `UNIQUE`, mandatory recursion, duplicate pairs, trees without RI
**What & why:**
- A relationship the model says is **1:1** mapped as a plain FK with no `UNIQUE` — the database
  silently permits 1:M (er-modeling §A3.2 step 4). On SQL Server a nullable `UNIQUE` admits only one
  NULL, so an *optional* 1:1 mapped that way fails after the first unmatched row — it needs a filtered
  unique index (`WHERE col IS NOT NULL`).
- A **self-referencing FK declared `NOT NULL`** — a recursive relationship must be optional at both
  ends, or the hierarchy has no root (§A2.2). Usually papered over with a magic root row that
  references itself.
- An intersection table (resolved M:M) with **no uniqueness on its parent-key pair** — the same pair
  can be inserted twice.
- A tree stored as **nested sets** (`lft`/`rgt`) or a **path string** (`path`, `lineage`,
  `hierarchyid`) with no adjacency FK — the database can't check that the path names real nodes;
  record it as a deliberate encoding and ask what keeps it correct (physical-design §5.4).
**Detect:** self-referencing `FOREIGN KEY … REFERENCES <same table>` on a `NOT NULL` column ✅;
two-FK tables with no PK/`UNIQUE` over both FKs ✅; 1:1 intent is ⚠️ (needs the model or the code);
`lft`/`rgt`/`path`/`hierarchyid` columns with no parent FK ⚠️.
**Severity:** Medium (High for the intersection-table duplicate, which corrupts counts and sums).

### All-key multi-parent table — a 4NF/5NF candidate
**What:** A table whose PK spans *all* its columns, with ≥ 3 columns and ≥ 2 FKs to different parents
(`(person_id, skill_id, language_id)`).
**Why:** BCNF by construction, but the shape of an MVD or join-dependency violation (theory §3): if
skills and languages vary independently, every combination is stored. If it is a genuine three-way fact
it is correct (er-modeling §A2.7).
**Detect:** ⚠️ the PK column list equals the table's column list and has ≥ 3 entries. Confirmation is a
question for the domain owner.
**Severity:** Medium.

### Stored derived attributes
**What:** Columns holding values computable from other rows — `total_*`, `qty_total`, `average_*`,
a `balance` next to the movements it sums — maintained by procedures or triggers; and **unstable
attributes** whose value drifts with the calendar (`age`, `edad`, `antiguedad`, `days_overdue`) stored
next to the stable date they derive from.
**Why:** Derived attributes are redundant by definition (§A1.4); redundancy kept in step by procedures
is **uncontrolled** (theory §7). Every writer must keep them in step, and the triggers that do it are
where multi-row data-loss defects tend to live. Storing one is a valid *physical* choice only when
documented and kept consistent by the engine. An unstable attribute is wrong the day after it is
written.
**Not a finding:** a value **captured at event time** — the unit price charged, the tax rate applied,
the due date granted — is a fact of the transaction, not a derived copy (theory §6).
**Detect:** aggregate-sounding names, then confirm a procedure/trigger recomputes them; age/seniority
names beside a date column. ⚠️ proxy.
**Severity:** Medium.

### Hidden subtypes in a single table
**What:** One table holding several kinds of thing, flagged by a type column, with blocks of columns
that are only ever filled for one kind — and nothing enforcing which.
**Why:** A single-table subtype mapping (er-modeling §A3.2 step 6) is legitimate, but without a per-type
`CHECK` the subtype's mandatory attributes are unenforced, invalid combinations are storable, and the
NULLs mean "not applicable" without saying so (theory §3.2). A column whose *meaning* depends on a flag
(`pay_amount` = salary or hourly rate) is the same defect.
**Detect:** a `tipo_*`/`*_type` column plus many nullable columns; no `CHECK` referencing the type.
⚠️ proxy.
**Severity:** Medium.

### History table that allows overlapping periods
**What:** A history table whose PK/`UNIQUE` is `(entity_id, valid_from)` or `(entity_id, valid_from,
valid_to)`, with no `EXCLUDE`/`WITHOUT OVERLAPS` (or an engine equivalent) and no
`CHECK (valid_from < valid_to)`.
**Why:** Putting the period columns in the key makes rows unique but still lets periods overlap: two
"current" prices, two titles for one course on one date — the temporal FD (theory §3.1) is violated
silently. A nullable `valid_to` meaning "current" is also an overloaded NULL.
**Detect:** ⚠️ PK/`UNIQUE` containing `*_from`/`*_to`/`desde`/`hasta`/`inicio`/`fin`/`valid*`/
`effective*`, and no exclusion constraint or partial unique index for the current row on the table.
**Severity:** Medium–High (High for prices, rates and contracts).

### Model rule with no enforcement
**What:** A *must* on the parent side ("each order must have one or more lines"), a mandatory-both-ends
1:1, or a complete subtype set that the model or the business asserts, with no constraint trigger,
write-path rule or verification query anywhere.
**Why:** These are equality dependencies (theory §7.1); a foreign key enforces only one direction, so
childless parents and subtype-less supertype rows are storable.
**Detect:** ⚠️ needs the model or the business; 🔬 confirm with a count of parents having no children.
**Severity:** Medium.

### External files referenced by path
**What:** Columns holding a filesystem path or object-store URL (`*_path`, `*_file`, `ruta`, `archivo`,
`*_url`) for content the business treats as part of the row (scans, photos, contracts).
**Why:** The file is outside every guarantee the row has (theory §5): deleting the row doesn't delete
the file, rollback doesn't restore it, backups don't include it, `GRANT`s don't cover it, and nothing
checks the path exists.
**Detect:** ⚠️ path/URL-named `varchar` columns. Whether it matters depends on: how files are backed up
and restored *with* the database, what removes orphans, who enforces access. Unclear answers are the
finding.
**Severity:** Low (🔬 flag when the lifecycle can't be established from the DDL).

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
**Why:** Violates Single Source of Truth (theory §6) — the copies are derived from nothing, they drift,
and nobody can tell which is authoritative.
**Detect:** names like `*_COPIA_<date>`, `*_BAK`, trailing `_`/`2`/`_old`, near-duplicate definitions.
**Example:** `STOCK_PROJECTS_COPY_20120605_B` (a years-old backup left in place); `PERSONNEL2` beside
`PERSONNEL`; `SECTIONS_` beside `SECTIONS`.
**Severity:** Medium (a whole *copy database* escalates this to an estate-level finding — see
[`audit-lenses.md`](audit-lenses.md)).

### Schema hygiene
**What:** Tooling junk and inconsistent naming.
**Detect / examples:** `dtproperties` (a SQL Server diagram-tooling table) persisted in the schema;
constraint naming that mixes conventions — `DEPARTMENTS_PK`, `PK_employee_master`, `pk_dtproperties`
all in one file; every PK named plain `id`, which obscures joins.
**Severity:** Low.

## Engine notes — PostgreSQL dumps

The anti-patterns above hold on PostgreSQL; these are the PG-specific forms (signals in
[`detection-signals.md`](detection-signals.md)):

- **`serial`/`bigserial` keys** — legacy: the sequence is a separate object with its own grants, keeps
  its old name when the table is renamed, and accepts app-supplied ids. Prefer
  `GENERATED ALWAYS AS IDENTITY`. Low.
- **Naive `timestamp` for an instant**, **`timetz`**, **`money`** (output depends on `lc_monetary`, no
  currency code), **`json`** instead of `jsonb` — Medium.
- **`CREATE UNLOGGED TABLE`** holding business data — truncated after a crash and absent on replicas.
  High if the data can't be rebuilt.
- **Inheritance partitioning** (`INHERITS` + per-child `CHECK`) — PK, `UNIQUE` and FKs don't propagate
  to children, so uniqueness across the set is unenforced. Medium–High.
- **Rewrite rules** (`CREATE RULE`) — hidden query rewriting; replace with `INSTEAD OF` triggers or
  auto-updatable views. Medium.

## A note on normal forms

Of the normal forms in [`theory.md`](theory.md), **1NF** is reliably checkable from static DDL —
non-atomic / CSV / polymorphic columns, EAV and numbered column families show up in the schema text.
**2NF, 3NF, BCNF, 4NF and 5NF** violations are violations of *dependencies the business asserts*
(theory §2): data profiling can **refute** a suspected dependency or suggest one, but only the business
rule confirms it. Flag the likely candidate as ⚠️ from the DDL (a `dept_name` next to a `dept_code`; a
parent's non-key column copied beside the FK that reaches it). Name the normal form it breaks: a
dependency on a non-key column is **transitive, a 3NF candidate**. 2NF applies only when the column
depends on part of a composite key. A profile that would refute it is 🔬;
confirmation is an open question for the domain owner, carried by dbpropose. The exception is a
dependency implied by **declared** constraints — a reducible key — which is ✅.

## A note on the ER model behind the tables

Every table is the residue of a modelling decision (theory §9; er-modeling.md). When grading,
reverse-engineer the model as you go (er-modeling §A0): write each table's predicate, phrase each FK as
a two-way relationship sentence, test each PK against the UID criteria, and look for the constructs
that were never modelled — missing entities behind repeating groups, M:M resolved without uniqueness,
arcs and subtypes encoded in type columns. Those findings feed the rework verdicts in
[dbpropose](../dbpropose/SKILL.md) directly.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Primary key present and minimal | every table has a declared PK |
| 2 | Surrogate key where natural key is volatile | no PK on changeable business values |
| 3 | No magic-value sentinels; correct nullability | NULL means one documented thing; no `'9999…'`/`''`/`-1` proxies or placeholder parents |
| 4 | Right-sized types, one type per concept | `varchar` for variable text; `int`/`bigint` for IDs; no `float` IDs/money; no representation-typed dates; FK type = key type |
| 5 | No deprecated LOB types | no `text`/`ntext`/`image` (SQL Server) |
| 6 | No polymorphic/CSV/JSON columns or repeating-group column families (1NF) | attributes atomic; no `x_1`/`x_2`/`x_3` slots; no id lists in strings |
| 7 | Single, consistent collation | one `COLLATE` across joined tables |
| 8 | No shadow/backup/versioned tables | no `*_COPIA_*` / `*2` / `*_old` in live schema |
| 9 | FK declared for real relationships, mapped to their model | referential integrity engine-enforced; no relationship by convention; no generic arcs; 1:1 FKs `UNIQUE`; recursive FKs nullable; intersection pairs unique |
| 10 | Consistent table/column/constraint naming | one convention |
| 11 | Keys irreducible; every candidate key declared | no reducible key; a natural key `UNIQUE` beside every surrogate where one exists |
| 12 | Data and metadata separate (theory §10) | no EAV; no per-value clone tables or columns; no fluid value list frozen in a `CHECK`/`ENUM` |
| 13 | Constraints hold what they say | no partial-NULL composite FK; no cross-table or time-relative `CHECK`; history tables forbid overlaps |
