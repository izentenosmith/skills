# Views — Abstraction Layers & Performance

> Criteria for grading `views.sql`. Views are excellent for abstracting complex schemas, but they
> frequently **mask** underlying structural flaws and tank runtime efficiency. Severity per
> [`scoring.md`](scoring.md); detection commands and confidence tags (✅/⚠️/🔬) in
> [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- Shallow — a view selects from base tables, not from a stack of other views.
- Focused — serves one business concept with an explicit, minimal column list.
- Expensive, slowly-changing aggregations are **materialized** (indexed views) rather than recomputed
  on every call.
- `UNION ALL` used unless duplicate elimination is genuinely required.
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

### Monolithic "catch-all" views
**What:** A view joining most major tables to serve many distinct domains at once.
**Why:** Even if you select two columns, the optimizer must reason about the entire underlying logical
footprint; such views become a shared bottleneck and a coupling point.
**Detect:** views with very large `SELECT` lists and many joined tables; `UNION` of dissimilar
sources.
**Example:** two "calendar" views that each `UNION` two unrelated source tables (milestones and
inspection dates) into one wide projection serving several screens.
**Severity:** Medium.

### Missing materialization
**What:** Expensive views (aggregations, multi-join rollups) recomputed on the fly every call when
the underlying data changes only periodically.
**Why:** Wasted compute on every read.
**Fix (SQL Server):** convert to an **indexed view** (`WITH SCHEMABINDING` + a unique clustered
index) — the SQL Server equivalent of a materialized view — refreshed on a controlled basis.
**Detect:** heavy aggregate/`GROUP BY`/multi-join views with no schemabinding/indexed-view backing.
**Severity:** Medium.

### The `TOP 100 PERCENT … ORDER BY` hack
**What:** `SELECT TOP 100 PERCENT … ORDER BY …` inside a view definition.
**Why:** A legacy workaround for SQL Server's prohibition of `ORDER BY` in views. The modern
optimizer **ignores** the sort, so the ordering is not guaranteed — consumers that rely on it get
nondeterministic results, and the clause wastes parsing.
**Detect:** `TOP 100 PERCENT` co-occurring with `ORDER BY` in a view body.
**Severity:** Medium.

### Hygiene
**What & detect:**
- `SELECT *` in views → fragile to base-table changes.
- `UNION` where `UNION ALL` is correct → a needless dedupe sort.
- No `SCHEMABINDING` → base tables can change underneath the view and break it silently.
- Era-mismatched DDL — `CREATE OR ALTER VIEW` (a 2016+ feature) alongside much older syntax in the
  same file; an internal-consistency smell of uncontrolled, multi-era evolution.
**Severity:** Low–Medium.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Shallow (no view-on-view pyramids) | `FROM`/`JOIN` reference base tables |
| 2 | Focused, not catch-all | bounded column list, single domain |
| 3 | Expensive aggregations materialized | indexed view where data changes slowly |
| 4 | No `TOP 100 PERCENT … ORDER BY` | no fake in-view sorting |
| 5 | `UNION ALL` unless dedupe needed | no needless `UNION` sort |
| 6 | Explicit columns, schemabound where stable | no `SELECT *`; `WITH SCHEMABINDING` where apt |
