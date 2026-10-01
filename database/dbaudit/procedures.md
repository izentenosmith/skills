# Stored Procedures & Functions — Business-Logic Isolation

> Criteria for grading `procedures.sql`. Usually the heaviest category in a legacy estate — hundreds
> of procedures per database is common. Legacy databases often act as an application framework rather
> than a storage engine; evaluate procedures for maintainability and hidden resource drains. Theory
> (relational algebra, ACID) in [`theory.md`](theory.md); severity per [`scoring.md`](scoring.md);
> detection commands and confidence tags (✅/⚠️/🔬) in [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- **Set-based** logic — one statement operates on a whole set, not row-by-row.
- Wrapped in `BEGIN TRY … BEGIN CATCH` with explicit transaction control and rollback.
- `SET NOCOUNT ON` at the top.
- Explicit column lists (no `SELECT *`); ANSI `JOIN` syntax.
- Dynamic SQL (when truly needed) parameterized via `sp_executesql`, never string-concatenated.
- Functions declared `WITH SCHEMABINDING` where deterministic, enabling caching and indexed-view use.
- No hardcoded cross-database three-part names.

## 🔴 Not well done

### RBAR (Row-By-Agonizing-Row)
**What:** Explicit `CURSOR` / `WHILE @@FETCH_STATUS = 0` loops doing work a single set-based statement
could do.
**Why:** Relational engines are optimized for set operations (theory §4); per-row loops serialize the
work and hold resources far longer.
**Detect:** `DECLARE … CURSOR`, `WHILE @@FETCH_STATUS`, `FETCH NEXT`. Report the count across the file
— it is the prevalence number the estate synthesis needs.
**Example:** a procedure that opens a cursor over an order-detail table and issues one
`UPDATE … WHERE detail_id = @id` per row inside a transaction — a single set-based
`UPDATE … FROM … JOIN` would replace the whole loop.
**Severity:** Medium–High (High on large tables).

### No error handling around transactions
**What:** `BEGIN TRANSACTION … COMMIT` with no `TRY/CATCH`.
**Why:** On mid-transaction failure the transaction is neither caught nor rolled back cleanly →
locks/transaction leak, partial writes (ACID atomicity, theory §5).
**Detect:** `BEGIN TRAN`/`BEGIN TRANSACTION` without a surrounding `BEGIN TRY`. Count the files that
contain *any* `BEGIN TRY` — when it is a small minority, error handling is absent estate-wide.
**Severity:** High.

### State accumulation, side effects & dynamic SQL
**What:** Procedures that create global/`##` temp tables, mutate session state, or build and `EXEC()`
raw SQL strings.
**Why:** Dynamic `EXEC(@sql)` bypasses compiled-plan caching and opens SQL-injection exposure; global
temp tables leak state across sessions.
**Detect:** `EXEC(` / `EXECUTE(` on a concatenated string; `##temp`.
**Severity:** High.

### Parameter sniffing / plan-cache trap 🔬 *(estate-level observation, not a per-proc defect)*
**What:** Cached plans compiled for an atypical parameter value, then reused for typical ones, can
time out.
**Why this is not a per-object grade:** statically you can only observe the *absence* of
`OPTION (RECOMPILE)` / `OPTIMIZE FOR` — which is usually true of essentially every procedure and says
nothing about which one actually suffers (that needs plan-cache telemetry). Grading it per procedure
would flag ~100% and add only noise.
**How to use it:** count the mitigations across the dumps and record it **once**, at the estate level,
in the synthesis.
**Severity:** n/a per object (estate note).

### Non-deterministic / non-schemabound functions
**What:** Scalar/table functions not declared `WITH SCHEMABINDING` where their logic is deterministic.
**Why:** Without schemabinding the engine can't guarantee determinism, blocking result caching and
indexed-view participation, and scalar functions in predicates serialize execution.
**Detect:** `CREATE FUNCTION` lacking `WITH SCHEMABINDING`; scalar functions called per row.
**Severity:** Medium.

### Hygiene
**What & detect:**
- `cast(col as varchar)` / `convert(varchar, col)` with **no length** → silent truncation to the
  default 30 chars.
- Old comma-style joins (`FROM a, b WHERE a.x = b.x`) instead of ANSI `JOIN`.
- `SELECT *`.
- Missing/partial `SET NOCOUNT ON`.
- Hardcoded cross-database calls (`OTHER_DB.dbo.<proc/fn>`) — couples catalogs (see
  [`audit-lenses.md`](audit-lenses.md)).
- No parameter validation; inconsistent header/author/version comment conventions; mixed
  `CREATE PROCEDURE` styling (parenthesized vs bare parameter lists) within the same file.
**Severity:** Low–Medium.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Set-based, not RBAR | no cursor/`WHILE` loop replaceable by one statement |
| 2 | Transaction safety | `TRY/CATCH` + rollback around every explicit transaction |
| 3 | Safe dynamic SQL | parameterized `sp_executesql`, never concatenated `EXEC()` |
| 4 | Functions schemabound where deterministic | `WITH SCHEMABINDING` present |
| 5 | Bounded, typed casts | every `cast(... as varchar(n))` has a length |
| 6 | ANSI joins + explicit columns | no comma-joins, no `SELECT *` |
| 7 | `SET NOCOUNT ON` | present at top |
| 8 | No hardcoded cross-DB names | no `OTHER_DB.dbo.*` references |

> Parameter-sniffing mitigation is **not** a per-file checklist item — it is a 🔬 estate-level
> observation recorded once in the synthesis.
