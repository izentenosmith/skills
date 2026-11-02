# Indexes — Query Optimization & Write Overhead

> Criteria for grading `indexes.sql`. An index is a trade between read speed and write cost; legacy
> systems drift toward either **index starvation** or **index bloat**. We judge only what the DDL
> reveals — index *definitions*, and the predicates in view/procedure bodies that use them — not
> runtime *usage* (see the scope note in [`audit-lenses.md`](audit-lenses.md)). The mechanics — access
> vs filter predicates, column order, sargability — are defined in [`theory.md`](theory.md) §4.1.
> Severity per [`scoring.md`](scoring.md); detection commands and confidence tags (✅/⚠️/🔬) in
> [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- Every index serves a **named access path** — an FK navigated parent→child, a `UNIQUE` rule, or a
  visible `WHERE`/`JOIN`/`ORDER BY`.
- Composite keys ordered **equality → range → sort**, matching the predicates that use them.
- Clustered key (SQL Server, InnoDB) chosen deliberately — narrow, static, ideally ever-increasing,
  because it is copied into every secondary index.
- Foreign-key columns whose parent is deleted or key-updated, or that are navigated parent→child, lead
  some index.
- Selective subsets indexed with a **filtered/partial** index rather than the whole low-cardinality
  column.
- Fill factor matched to the table's write volatility, not a blanket value.
- No index merely duplicates or prefixes another.

## 🔴 Not well done

### Redundant index duplicating the clustered key
**What:** A non-clustered index on exactly the column(s) already covered by the clustered primary
key.
**Why:** Pure write overhead — every `INSERT`/`UPDATE`/`DELETE` maintains a second structure that the
optimizer will never prefer over the clustered key for those columns.
**Detect:** non-clustered index whose key list equals a clustered PK's key list on the same table. On
PostgreSQL (no clustered indexes): an index whose key list equals the PK's.
**Example:** `ATTRIBUTES_PK` is `UNIQUE CLUSTERED … (attribute_code)` and `IX_ATTRIBUTES` is
`NONCLUSTERED … (attribute_code)` on the same table — the second index is redundant. The shape tends to
repeat table after table once a generator or a habit introduced it.
**Severity:** Medium.

### Prefix redundancy
**What:** An index whose key list is a leading prefix of another index on the same table — `(a)` beside
`(a, b)`, and `(a, b)` beside `(a, b, c)` — and twin expression indexes serving one purpose
(`UPPER(x)` and `LOWER(x)`).
**Why:** The engine can seek the wider index by its leading prefix (theory §4.1), so the narrower one
adds write cost for no read benefit. Twin expressions exist because the code uses two functions for one
concept; unify the function and one index serves.
**Detect:** index key list = leading prefix of another index's key list on the same table.
**Not a finding:** the narrower index enforces a PK/`UNIQUE`, is filtered/partial, or uses a different
expression.
**Severity:** Medium.

### Heap — table with no clustered index ✅ *(SQL Server; InnoDB is always clustered)*
**What:** A SQL Server table that has neither a clustered primary key nor any clustered index.
**Why:** A transactional heap accumulates forwarded records on update and gives up range scans and
ordering on a clustering key. (A heap's secondary indexes are not slower — a clustered table's
secondary indexes pay an extra clustered-index traversal per row, which is why the clustering key must
be narrow.)
**Detect:** cross-reference `tables.sql` against `indexes.sql` — tables with no `CLUSTERED` index/PK.
**Engine scope:** n/a on PostgreSQL (every table is a heap; `CLUSTER` is a one-off reorder) and on
Oracle (heap by default; index-organized tables are opt-in).
**Severity:** Medium.

### Low-cardinality indexes 🔬
**What:** Indexes on columns with very few distinct values — boolean/`flag_*` / status.
**Why:** The planner tends to reject them in favour of a scan, leaving them as pure write tax. What
matters is **skew and which value is queried**: an index on the rare value of a skewed flag (`todo` vs
`done`) is useful, and is better expressed as a filtered (SQL Server) / partial (PostgreSQL) index on
that value. A filtered index is used only when the query states the predicate literally — a
parameterized `= @flag` cannot use it.
**Decidability:** true cardinality and skew are **not** in the DDL — a `flag_*`/`char(1)` key is only a
*candidate*. **Flag for data review (🔬 needs-data); do not grade as a defect** without a
`COUNT(DISTINCT)` and a value histogram on a live instance.
**Severity:** n/a (flag only).

### Missing foreign-key indexes
**What:** An FK column list that is not the **leading** prefix of any index or PK/`UNIQUE` key on the
child table.
**Why:** The index serves two things: nested-loop navigation from parent to child, and the referential
check when a parent row is deleted or its key updated — without it that check scans the whole child
table while holding locks. (Hash and merge joins gain nothing from it.) SQL Server, PostgreSQL and
Oracle do **not** index FKs automatically; MySQL/InnoDB does.
**Detect:** cross-reference declared `FOREIGN KEY` columns (in `tables.sql`) against index key lists (in
`indexes.sql`): covered only when the FK columns, in any order among themselves, lead an index. An FK
that is the second column of a composite index is **not** covered; one that leads the composite PK of an
intersection table **is**. A database with dozens of tables and an empty `indexes.sql` is an
index-starvation hotspot.
**Severity:** **High** when the parent is transactional — deletes or key updates on it appear in
`procedures.sql`/`triggers.sql`, or the FK is `ON DELETE CASCADE`/`SET NULL`; **Medium** when the parent
is a static lookup table. *How much* it hurts is 🔬.

### Non-sargable predicates
**What:** A predicate in a view or procedure body that hides an indexed column, so the index cannot
supply the start/stop of the scan (theory §4.1):
- a function on the column — `YEAR(col)`, `UPPER(col)`, `CONVERT(date, col)`, `LEFT(col, …)`,
  `ISNULL(col, …)`, `DATEADD(…, col)`, `TO_CHAR(col, …)`;
- an **implicit conversion on the column side** — a character column compared to a number
  (`code = 42`), a date compared through a string (`CONVERT(varchar, dt, 112) = '20240101'`): the engine
  converts every row's column, not the literal;
- arithmetic on the column (`col - 1000 > @x`) or combined columns (`first + ' ' + last = @name`);
- a **leading wildcard** — `LIKE '%term'`, `LIKE '%' + @p + '%'`, regex matches: only the characters
  before the first wildcard can bound a scan;
- `a = @x OR b = @x` across two columns of one composite index.
**Why:** A B-tree is ordered on the raw value; an expression is a black box to the optimizer, so the
condition is at best a filter predicate and the plan scans. Converting the column also makes the query
fail on one bad value.
**Fix:** move the work to the parameter side (`dt >= @d AND dt < DATEADD(day, 1, @d)`; `code = '42'`;
`col > @x + 1000`); store numbers and dates as their types (tables.md); `OR` → `UNION` of two sargable
branches; keyword search → full-text (SQL Server full-text + `CONTAINS`; PostgreSQL `tsvector` + GIN, or
`pg_trgm` for substrings). Only then an expression / computed-column index, one function per concept.
**Detect:** see detection-signals ✅ for the shape; cross-reference `indexes.sql` to know whether the
column leads an index (✅); hot-path-ness is 🔬.
**Severity:** High when the column leads an index; Medium otherwise.

### Composite key order mismatched to its predicates
**What:** A composite index whose order doesn't serve the bodies that query it: a range or sort column
(date, amount) ahead of an equality column (FK, status), or a leading column no predicate constrains.
**Why:** Only a leading prefix bounds the scan, and only one range column can be an access predicate;
after it the rest are filter predicates (theory §4.1). PostgreSQL 18's skip scan softens the
unconstrained-leading-column case but doesn't remove it.
**Detect:** ⚠️ for each composite index, collect the `WHERE`/`JOIN` predicates on its columns in
`views.sql`/`procedures.sql`; flag equality on column 2 with a range on column 1, or column 1 never
constrained.
**Severity:** Medium.

### Index-heavy table and index shotgun
**What:** A table carrying many secondary indexes — a single-column index on most of its columns, or
indexes on columns no visible predicate, join or sort uses (wide free text, measures like `hours`,
`amount`) — especially one that procedures or triggers write heavily.
**Why:** Every insert and delete maintains every index, and every update maintains every index on a
changed column; indexes pay off only for the queries that use them (theory §7). Indexing by guesswork,
not by query, is the defect.
**Detect:** ⚠️ count indexes per table; flag tables above the estate's 90th percentile or with more than
six non-unique secondary indexes (a house threshold), and index key columns that never appear in any
`WHERE`/`JOIN`/`ORDER BY` of the dumped code. Application SQL is usually not in the dumps and real usage
is 🔬 — never ✅.
**Severity:** Medium.

### Blanket fill factor *(SQL Server)*
**What:** Every index created with the same `FILLFACTOR` regardless of write pattern.
**Why:** `FILLFACTOR = 100` on a volatile table guarantees page splits; a low fill factor on a
read-only table wastes space.
**Detect:** uniform `FILLFACTOR = 100` across the dump, applied to volatile and static tables alike.
**Engine scope:** n/a on PostgreSQL, where heap fillfactor 100 is correct for insert-mostly tables and
B-tree indexes already default to 90 (physical-design §10).
**Severity:** Medium.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | No index duplicates its table's clustered/PK key | no `IX_*` equal to the PK key list |
| 2 | No prefix duplication | no index whose key list prefixes another's (unless unique or filtered) |
| 3 | No heaps (SQL Server) | every transactional table has a clustered index/PK; n/a elsewhere |
| 4 | FK columns lead an index | every FK on a transactional parent is the leading prefix of some index |
| 5 | Predicates are sargable | no function, implicit conversion or leading wildcard on an indexed column without a matching expression or full-text index |
| 6 | Fill factor matched to volatility (SQL Server) | not a blanket `FILLFACTOR = 100`; n/a elsewhere |
| 7 | Composite order matches the predicates | equality columns before the range column in every composite the code queries |

> Low-cardinality indexes are tracked as a 🔬 needs-data *flag*, not a scored checklist item;
> index-heavy tables are a ⚠️ finding, not a checklist item, because usage is not in the DDL.
