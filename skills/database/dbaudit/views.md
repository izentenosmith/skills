# Views — Abstraction Layers & Performance

**Contents:** 🟢 Well done · 🔴 Not well done · Checklist

> Criteria for grading `views.sql`. Views are excellent for abstracting complex schemas, but they
> frequently **mask** underlying structural flaws, tank runtime efficiency, and — when they return
> duplicates or accept writes they can't show — return wrong answers. Severity per
> [`scoring.md`](scoring.md); detection commands and confidence tags (✅/⚠️/🔬) in
> [`detection-signals.md`](detection-signals.md). The query-shape anti-patterns of
> [`procedures.md`](procedures.md) — NULL-unsafe predicates, catch-all filters, dirty-read hints, offset
> paging — apply to view bodies too; grade them here when they live in a view.

## 🟢 Well done

- Shallow — a view selects from base tables, not from a stack of other views.
- Focused — serves one business concept with an explicit, minimal column list.
- **Every view has a key you can name** — it returns a relation, not a bag (theory §1.1).
- `UNION ALL` only between **provably disjoint** branches; `UNION` otherwise.
- Expensive, slowly-changing aggregations are **materialized** (indexed views; PostgreSQL materialized
  views) rather than recomputed on every call.
- Views that are written through carry `WITH CHECK OPTION` (theory §7.3).
- `SELECT *` avoided; columns named explicitly.

## 🔴 Not well done

### Nested view pyramids
**What:** Views that query other views, which query still other views.
**Why:** Deep nesting hides the true cost of a query — a simple `SELECT * FROM summary_view` may
silently expand into dozens of joined tables (theory §4: the optimizer receives a far larger algebra
tree than the query suggests). It also makes change risky: editing a base view ripples unpredictably
upward.
**Detect:** view definitions whose `FROM`/`JOIN` reference names that are themselves views; measure
nesting depth.
**Severity:** Medium–High.

### View re-joined to a table it already contains
**What:** A view or query that joins view V to table T where T already appears in V's `FROM`.
**Why:** Two passes over T, the same rows hit twice, and a view returning far more than the consumer
needs often can't be merged by the optimizer.
**Detect:** ⚠️ the consumer's `FROM`/`JOIN` list ∩ the referenced view's `FROM`/`JOIN` list ≠ ∅.
**Fix:** inline the view's SQL into the consumer and drop what isn't needed.
**Severity:** Medium.

### Monolithic "catch-all" views
**What:** A view joining most major tables to serve many distinct domains at once.
**Why:** Even if you select two columns, the optimizer must reason about the entire underlying logical
footprint; such views become a shared bottleneck and a coupling point.
**Detect:** views with very large `SELECT` lists and many joined tables; `UNION` of dissimilar
sources.
**Example:** two "calendar" views that each `UNION` two unrelated source tables (milestones and
inspection dates) into one wide projection serving several screens.
**Severity:** Medium.

### Bag view — a view that can return duplicate rows
**What:** A view whose result has no inferable key: it projects away every key of its sources without
`DISTINCT`/`GROUP BY`, or `UNION ALL`s branches that can contain the same row.
**Why:** A relation has no duplicate rows (theory §1.1). Consumers that count or sum the view
double-count, and nothing can safely reference or join on it. `UNION ALL` is right only when the
branches are **provably disjoint** — a distinct discriminator literal per branch, or keys made disjoint
by `CHECK` (the supertype view over separate subtype tables); then it is also the cheaper choice.
**Detect:** ⚠️ a select list containing no PK/`UNIQUE` column set of any source and no
`DISTINCT`/`GROUP BY`; ⚠️ `UNION ALL` with no branch-distinguishing literal column.
**Severity:** Medium.

### Fan-out aggregate — joining independent child sets before `SUM`/`COUNT`
**What:** One `GROUP BY` that joins a parent to two or more independent one-to-many children (order
lines *and* payments; fixed bugs *and* open bugs) and aggregates over the joined rows — often "fixed"
with `COUNT(DISTINCT …)`, `SUM(DISTINCT …)` or an outer `DISTINCT`.
**Why:** The join forms a product of the child sets (theory §4): 12 lines × 7 payments reports 84 of
each. `DISTINCT` hides the symptom for counts, is wrong for sums (equal amounts collapse), and costs a
sort.
**Detect:** ⚠️ `GROUP BY` with ≥ 2 joins to different child tables on the same parent key;
`SUM(DISTINCT` / `COUNT(DISTINCT` beside several joins.
**Fix:** aggregate each child in its own derived table or CTE, then join the one-row-per-parent results.
**Severity:** High (silent wrong totals) — as a ⚠️ finding it grades 🟡 at most (scoring.md).

### `SELECT DISTINCT` as a join fix
**What:** A top-level `DISTINCT` over a multi-table join whose purpose is an existence test ("customers
who bought…").
**Why:** It costs a sort or hash over the whole join, hides a missing join condition, and merges distinct
entities that share the projected values (two customers with the same name).
**Detect:** ⚠️ `SELECT DISTINCT` in a body with ≥ 2 sources.
**Fix:** express the test as `EXISTS`/`IN` (a semi-join) and project the key.
**Severity:** Medium.

### `UNION ALL` over per-value clones
**What:** A view that `UNION ALL`s same-shaped tables whose names differ by a year, tenant or region.
**Why:** The view papers over per-value clones (tables.md) — keys and FKs undeclarable across the set,
and a view edited every period.
**Detect:** ✅ branch tables whose names share a stem and differ by a value token. On SQL Server this may
be a deliberate *partitioned view* with a disjoint `CHECK` per member — confirm before grading.
**Severity:** Medium (the finding itself lives on the tables).

### Updatable view without `WITH CHECK OPTION` — Assignment Principle
**What:** A view with a restricting `WHERE` or join that the engine treats as updatable (PostgreSQL
auto-updatable views; SQL Server single-base-table views), written through by code, and declared
without `WITH [CASCADED] CHECK OPTION`.
**Why:** The Assignment Principle (theory §7.3): after a write through a view, the view must show it.
Without `CHECK OPTION`, an insert through "London suppliers" can create a Madrid supplier that vanishes
from the view — the write succeeds and the result contradicts it.
**Detect:** ✅ `CREATE VIEW … WHERE …` with no `CHECK OPTION`; ⚠️ "written through" — the view is an
`INSERT INTO`/`UPDATE`/`DELETE FROM` target in procedures, or has an `INSTEAD OF` trigger.
**Severity:** Medium (High when the view is the only write path for a role).

### `INSTEAD OF` trigger on a view — an undeclared update mapping
**What:** A view made writable by an `INSTEAD OF` trigger.
**Why:** The trigger decides procedurally what an update *means*; it can drop or redirect rows so the
view doesn't reflect the write (theory §7.3), and it is often row-at-a-time.
**Detect:** ✅ `INSTEAD OF` in `triggers.sql` naming a view.
**Severity:** Medium; 🟢 when set-based, documented, and paired with a check that the view shows what
was written. (On PostgreSQL this is the right replacement for `CREATE RULE`.)

### Missing materialization
**What:** Expensive views (aggregations, multi-join rollups) recomputed on the fly every call when
the underlying data changes only periodically.
**Why:** Wasted compute on every read.
**Fix (SQL Server):** convert to an **indexed view** (`WITH SCHEMABINDING` + a unique clustered
index) — the SQL Server equivalent of a materialized view — refreshed on a controlled basis.
**Fix (PostgreSQL):** a `MATERIALIZED VIEW` with a `UNIQUE` index (required for
`REFRESH … CONCURRENTLY`), its source and accepted staleness documented (theory §6).
**Detect:** heavy aggregate/`GROUP BY`/multi-join views with no materialized counterpart.
**Severity:** Medium.

### The `TOP 100 PERCENT … ORDER BY` hack
**What:** `SELECT TOP 100 PERCENT … ORDER BY …` inside a view definition.
**Why:** A legacy workaround for SQL Server's prohibition of `ORDER BY` in views. The modern
optimizer **ignores** the sort, so the ordering is not guaranteed — consumers that rely on it get
nondeterministic results, and the clause wastes parsing. (A PostgreSQL *materialized* view may use
`ORDER BY` to set its physical order at each refresh; that is not this defect.)
**Detect:** `TOP 100 PERCENT` co-occurring with `ORDER BY` in a view body.
**Severity:** Medium.

### Hygiene
**What & detect:**
- `SELECT *` in views → fragile to base-table changes.
- `UNION` where the branches are provably disjoint → a needless dedupe sort (the reverse of *Bag view*).
- No `SCHEMABINDING` (SQL Server) → base tables can change underneath the view and break it silently.
  n/a on PostgreSQL, where views always record their dependencies.
- PostgreSQL views over row-level-security tables without `WITH (security_invoker = true)` (PG15+) run
  with the owner's rights and bypass the caller's policies — a security finding, High (audit-lenses §6).
- Era-mismatched DDL — `CREATE OR ALTER VIEW` (a 2016+ feature) alongside much older syntax in the
  same file; an internal-consistency smell of uncontrolled, multi-era evolution.
**Severity:** Low–Medium (except as noted).

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Shallow (no view-on-view pyramids) | `FROM`/`JOIN` reference base tables |
| 2 | Focused, not catch-all | bounded column list, single domain |
| 3 | Expensive aggregations materialized | indexed / materialized view where data changes slowly |
| 4 | No `TOP 100 PERCENT … ORDER BY` | no fake in-view sorting |
| 5 | `UNION ALL` only between disjoint branches | every `UNION ALL` branch carries a discriminator or disjoint key; no needless `UNION` |
| 6 | Explicit columns, schemabound where stable | no `SELECT *`; `WITH SCHEMABINDING` where apt (SQL Server; n/a elsewhere) |
| 7 | Returns a relation | every view has a nameable key; no fan-out aggregate; no `DISTINCT` join fix |
| 8 | Write paths keep the Assignment Principle | updatable views written through carry `WITH CHECK OPTION` |
