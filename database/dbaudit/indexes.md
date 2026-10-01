# Indexes — Query Optimization & Write Overhead

> Criteria for grading `indexes.sql`. An index is a trade between read speed and write cost; legacy
> systems drift toward either **index starvation** or **index bloat**. We judge only what the DDL
> reveals — index *definitions*, not runtime *usage* (see the scope note in
> [`audit-lenses.md`](audit-lenses.md)). Severity per [`scoring.md`](scoring.md); detection commands
> and confidence tags (✅/⚠️/🔬) in [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- Clustered key chosen deliberately (narrow, static, ideally ever-increasing).
- Non-clustered indexes cover real access paths and don't overlap each other.
- Foreign-key columns are indexed (engines do **not** index FKs automatically).
- Fill factor matched to the table's write volatility, not a blanket value.
- No index merely duplicates the key it sits on.

## 🔴 Not well done

### Redundant index duplicating the clustered key
**What:** A non-clustered index on exactly the column(s) already covered by the clustered primary
key.
**Why:** Pure write overhead — every `INSERT`/`UPDATE`/`DELETE` maintains a second structure that the
optimizer will never prefer over the clustered key for those columns.
**Detect:** non-clustered index whose key list equals a clustered PK's key list on the same table.
**Example:** `ATTRIBUTES_PK` is `UNIQUE CLUSTERED … (attribute_code)` and `IX_ATTRIBUTES` is
`NONCLUSTERED … (attribute_code)` on the same table — the second index is redundant. The shape tends to
repeat table after table once a generator or a habit introduced it.
**Severity:** Medium.

### Leftmost-prefix redundancy
**What:** A standalone index on `(a)` when a composite index on `(a, b)` already exists.
**Why:** The engine can seek the composite index by its leftmost prefix `(a)`, so the standalone
index adds write cost for no read benefit.
**Detect:** single-column index whose column is the leading column of a wider composite index on the
same table.
**Severity:** Medium.

### Heap — table with no clustered index ✅
**What:** A table that has neither a clustered primary key nor any clustered index (SQL Server).
**Why:** A heap stores rows unordered; range scans and lookups suffer, forwarded records accumulate on
update, and there is no clustering key for nonclustered indexes to reference efficiently. Almost always
undesirable for a transactional table.
**Detect:** cross-reference `tables.sql` against `indexes.sql` — tables with no `CLUSTERED` index/PK.
**Severity:** Medium–High.

### Low-cardinality indexes 🔬
**What:** Indexes on columns with very few distinct values — boolean/`flag_*` / status.
**Why:** The planner tends to reject them in favour of a scan, leaving them as pure write tax.
**Decidability:** true cardinality is **not** in the DDL — a `flag_*`/`char(1)` key is only a
*candidate*. **Flag for data review (🔬 needs-data); do not grade as a defect** without a
`COUNT(DISTINCT)` on a live instance.
**Severity:** n/a (flag only).

### Missing foreign-key indexes
**What:** A table with FK relationships but no index on the FK column(s).
**Why:** Joins and cascading deletes on that column degrade to table scans.
**Detect:** cross-reference declared `FOREIGN KEY` columns (in `tables.sql`) against index keys (in
`indexes.sql`); flag FK columns with no covering index. A database with dozens of tables and an empty
`indexes.sql` is an index-starvation hotspot worth checking against its FK/join columns first.
**Severity:** High for the structural gap (the FK column genuinely has no index ✅); *how much it
hurts* depends on join frequency, which is 🔬 needs-data.

### Function-based index suppression
**What:** Predicates that wrap an indexed column in a function — `WHERE YEAR(col) = …`,
`WHERE LOWER(col) = …`, `CONVERT(...)` on the indexed side.
**Why:** A standard B-tree is ordered on the raw column value; wrapping it in a function defeats the
seek and forces a scan unless a **computed-column / expression index** exists.
**Detect:** scan `views.sql` / `procedures.sql` bodies for function calls on columns that appear as
index keys; check whether a matching computed-column index is defined.
**Severity:** High (on hot paths).

### Blanket fill factor
**What:** Every index created with the same `FILLFACTOR` regardless of write pattern.
**Why:** `FILLFACTOR = 100` on a volatile table guarantees page splits; a low fill factor on a
read-only table wastes space.
**Detect:** uniform `FILLFACTOR = 100` across the dump, applied to volatile and static tables alike.
**Severity:** Medium.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | No index duplicates its table's clustered/PK key | no `IX_*` equal to the PK key list |
| 2 | No leftmost-prefix duplication | no single-col index that prefixes a composite |
| 3 | No heaps | every transactional table has a clustered index/PK |
| 4 | FK columns indexed | every FK has a covering index |
| 5 | Predicates are sargable | no `FUNCTION(col)` filters without a matching computed-column index |
| 6 | Fill factor matched to volatility | not a blanket `FILLFACTOR = 100` |

> Low-cardinality indexes are tracked as a 🔬 needs-data *flag*, not a scored checklist item.
