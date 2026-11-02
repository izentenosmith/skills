# Stored Procedures & Functions — Business-Logic Isolation

> Criteria for grading `procedures.sql`. Usually the heaviest category in a legacy estate — hundreds
> of procedures per database is common. Legacy databases often act as an application framework rather
> than a storage engine; evaluate procedures for maintainability, hidden resource drains, wrong results
> and races under concurrency. Theory (relational algebra, three-valued logic, isolation anomalies) in
> [`theory.md`](theory.md) §3.2, §4, §5; severity per [`scoring.md`](scoring.md); detection commands and
> confidence tags (✅/⚠️/🔬) in [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- **Set-based** logic — one statement operates on a whole set, not row-by-row.
- Wrapped in `BEGIN TRY … BEGIN CATCH` with explicit transaction control and rollback.
- **Concurrency-safe writes** — invariants declared as constraints; read-modify-write done as one
  atomic `UPDATE … SET x = x - @n WHERE … AND x >= @n`; premises locked (`UPDLOCK, HOLDLOCK` /
  `FOR UPDATE`) or run `SERIALIZABLE` with retry; keys from `IDENTITY`/`SEQUENCE`.
- **Optimistic concurrency** for user conversations — a `rowversion`/version column checked in the
  `UPDATE … WHERE`, so no transaction spans user think-time.
- `SET NOCOUNT ON` at the top.
- Explicit column lists (no `SELECT *`, no `INSERT` without a column list); ANSI `JOIN` syntax.
- Dynamic SQL (when truly needed) parameterized via `sp_executesql`, never string-concatenated; dynamic
  identifiers whitelisted or quoted.
- Functions declared `WITH SCHEMABINDING` where deterministic, enabling caching and indexed-view use.
- No hardcoded cross-database three-part names.

## 🔴 Not well done — set processing and error handling

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

### Per-row hidden queries
**What:** A scalar function whose body contains `SELECT … FROM`, called in the select list or `WHERE`
of a view or procedure; a correlated scalar subquery in a select list.
**Why:** It runs once per row like a correlated subquery, but inside the function the optimizer can't
see it — no join reordering, no set processing; cost grows linearly with rows (theory §4).
**Detect:** ✅ `CREATE FUNCTION` bodies containing `FROM` × their call sites in views and procedures;
⚠️ select lists containing `(SELECT`.
**Fix:** inline it as a join, or an inline table-valued function / view.
**Severity:** Medium–High.

### No error handling around transactions
**What:** `BEGIN TRANSACTION … COMMIT` with no `TRY/CATCH`.
**Why:** On mid-transaction failure the transaction is neither caught nor rolled back cleanly →
locks/transaction leak, partial writes (ACID atomicity, theory §5).
**Detect:** `BEGIN TRAN`/`BEGIN TRANSACTION` without a surrounding `BEGIN TRY`. Count the files that
contain *any* `BEGIN TRY` — when it is a small minority, error handling is absent estate-wide.
**Severity:** High.

### Inflated transaction scope — waits, external calls, per-row commits
**What:** Loops, `WAITFOR`, remote/linked-server calls, mail/HTTP/shell calls (`sp_send_dbmail`,
`xp_cmdshell`, CLR), or error-message lookups between `BEGIN TRAN` and `COMMIT`; a transaction opened
in one procedure and committed in another call; `COMMIT` inside a per-row loop.
**Why:** Locks are held to the end of the transaction (theory §5.1), so external latency becomes lock
hold time — lock-scope inflation. External side effects can't be rolled back, which breaks atomicity.
Committing every row multiplies log flushes.
**Detect:** ⚠️ those calls, or a `CURSOR`/`WHILE`, between `BEGIN TRAN` and `COMMIT`; `COMMIT` inside a
`WHILE`/cursor block; a `BEGIN TRAN` without a matching `COMMIT`/`ROLLBACK` in the same body.
**Fix:** look up and validate before the transaction; roll back *before* querying error tables; commit
per set or batch; queue external work in an outbox row and act after commit.
**Severity:** Medium (High on hot tables).

### Distributed transaction / linked-server DML
**What:** `BEGIN DISTRIBUTED TRANSACTION`, or `INSERT`/`UPDATE`/`DELETE` against four-part names
(`SRV.DB.dbo.T`) or `OPENQUERY` inside a transaction (MSDTC two-phase commit).
**Why:** Two-phase commit blocks: a participant that has voted "prepared" holds its locks until the
coordinator decides, and a coordinator crash leaves transactions in doubt — locks held for minutes, or
until manual resolution. It couples the availability of both servers.
**Detect:** ✅ see detection-signals.
**Severity:** High in triggers; Medium in procedures.

## 🔴 Not well done — concurrency (theory §5.2)

### Dirty reads — `NOLOCK` / `READ UNCOMMITTED` ✅
**What:** `WITH (NOLOCK)` / `READUNCOMMITTED` table hints, or `SET TRANSACTION ISOLATION LEVEL READ
UNCOMMITTED`, in procedures, views or triggers.
**Why:** The read sees uncommitted writes that may roll back — values that never existed (dirty read).
On SQL Server an allocation-order scan under `NOLOCK` can also skip or double-read rows during page
splits. A result that *decides a write* (a stock check, a balance, a number) turns the dirty read into
stored corruption.
**Detect:** count per file — a blanket `NOLOCK` habit is an estate-level observation.
**Fix:** remove the hint; if it was there to stop readers blocking writers, turn on
`READ_COMMITTED_SNAPSHOT` instead. n/a on Oracle and PostgreSQL, which never serve dirty reads.
**Severity:** High when the read feeds an `INSERT`/`UPDATE`/`IF` in the same object or a financial/stock
decision; Medium in read-only reporting.

### Lost update — read-modify-write through a variable ⚠️
**What:** `SELECT @saldo = saldo FROM cuenta WHERE id = @id` … `UPDATE cuenta SET saldo = @saldo -
@monto WHERE id = @id` (the same for stock, counters, correlatives), with no lock on the read.
**Why:** Two callers read the same value and the second `UPDATE` overwrites the first — one movement
silently disappears. Default read committed doesn't prevent it.
**Detect:** a `SELECT @v = <col> FROM <t>` followed in the same body by `UPDATE <t> SET <col> = @v…`.
Clean if the read carries `WITH (UPDLOCK)` / `FOR UPDATE`, or the session is `SNAPSHOT` (conflict
raises error 3960, which must be retried).
**Fix:** one atomic statement — `UPDATE cuenta SET saldo = saldo - @monto WHERE id = @id AND saldo >=
@monto`, then check `@@ROWCOUNT`; or lock the read.
**Severity:** High; Critical when confirmed on a balance or stock column (silent loss of a movement).

### Check-then-act race — write skew and phantoms ⚠️
**What:** A procedure reads a premise and then writes on it, with nothing serializing concurrent
callers: `IF NOT EXISTS (SELECT … WHERE …) INSERT …`; `IF (SELECT COUNT(*) …) < @cupo INSERT …`;
`IF (SELECT SUM(…)) >= @monto UPDATE …`.
**Why:** Under read committed or snapshot isolation two callers both see the premise true and both
write — duplicate usernames, double-booked slots, over-quota enrolments, overdrawn balances. `IF NOT
EXISTS` has nothing to lock when the row is absent.
**Detect:** the guarded write has **no** `WITH (UPDLOCK, HOLDLOCK)` / `SERIALIZABLE` / `sp_getapplock`
**and** no `UNIQUE`/PK/exclusion constraint in `tables.sql` that would reject the duplicate. The
effective isolation level (`READ_COMMITTED_SNAPSHOT`, connection settings) is 🔬.
**Fix, in order:** declare the invariant (`UNIQUE`; in PG an exclusion constraint / `WITHOUT
OVERLAPS`) and let the second writer fail; else lock the premise rows; else `SERIALIZABLE` with retry.
For upserts, `MERGE … WITH (HOLDLOCK)` / PG `INSERT … ON CONFLICT`.
**Severity:** High for money, stock, bookings or identity; Medium otherwise.

### Manual key allocation — `MAX(id) + 1`, counter tables, renumbering ✅
**What:** New keys or document numbers computed as `SELECT @id = ISNULL(MAX(id), 0) + 1` (or
`COUNT(*) + 1`), by searching for the first unused value, or by a counter table read and then updated;
keys reassigned to close gaps (`SET IDENTITY_INSERT … ON`, `DBCC CHECKIDENT … RESEED`, `UPDATE … SET id
= …`).
**Why:** Two concurrent callers read the same maximum — a phantom (theory §5.2): with a PK/`UNIQUE` the
second insert fails; without one both rows get the same id. A read-then-update counter table serializes
every inserting session. Sequences allocate outside the transaction precisely so this can't happen,
which is why their gaps are normal; renumbering breaks every external reference and can hand a deleted
entity's id to a new one.
**Not a finding:** a *business* number that must be gapless by regulation (tax-authority invoice
folios) — a separate `UNIQUE` column allocated by one atomic counter update
(`UPDATE … SET n = n + 1 OUTPUT inserted.n`) inside the business transaction, never the PK.
**Detect:** see detection-signals; then check `tables.sql` for a PK/`UNIQUE` on the target column.
**Severity:** High when no PK/`UNIQUE` backs the column; Medium otherwise.

### Elevated isolation with no retry ⚠️
**What:** `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE|SNAPSHOT` (or PG `SERIALIZABLE`) in a body with
no retry on deadlock or serialization failure (1205, 3960; PG 40001, 40P01).
**Why:** Aborts are expected at these levels and must be retried — only those, never a constraint
violation — or they surface as user-facing errors.
**Severity:** Low–Medium.

## 🔴 Not well done — query shape and correctness

### NULL-unsafe predicates — three-valued-logic traps
**What:**
- `x NOT IN (SELECT col …)` where `col` is nullable → returns **no rows** once any `col` is NULL;
- `= NULL` / `<> NULL` comparisons (always UNKNOWN), and `col <> 'X'` on a nullable column where the
  NULL rows were meant to be included;
- on SQL Server, modules created under `SET ANSI_NULLS OFF`, where those comparisons "work" and change
  meaning if the module is re-created.
**Why:** Any comparison with NULL is UNKNOWN, never true (theory §3.2): the predicate silently selects
nothing, and an `UPDATE`/`DELETE` guarded by it silently does nothing. `IN` is unaffected, which hides
the bug.
**Fix:** `NOT EXISTS`, an outer join with `IS NULL`, or `EXCEPT`; `IS NULL` / `IS [NOT] DISTINCT FROM`
(PG; T-SQL 2022+).
**Detect:** ✅ `= NULL` in a predicate (not an assignment); ✅/⚠️ `NOT IN (SELECT` — ✅ when `tables.sql`
shows the column nullable, ⚠️ when it is an expression; ✅ `SET ANSI_NULLS OFF`.
**Severity:** High (silent wrong result); Critical when `NOT IN` over a nullable subquery drives a
`DELETE` or `INSERT … SELECT`.

### Catch-all optional-filter predicates ✅
**What:** One static statement serving every search combination by switching filters off at run time —
`WHERE (col = @p OR @p IS NULL)`, `col = ISNULL(@p, col)` / `COALESCE(@p, col)`, or a parameter compared
to a constant to pick a branch (`(@mode = 'GRP' AND …) OR (@mode = 'NIT' AND …)`).
**Why:** The cached plan must be valid for the case where every filter is off, so it scans even when an
index exists for the active filter (theory §4). The `col = COALESCE(@p, col)` form is also *wrong*: rows
where `col` is NULL never match, even with the filter "off".
**Fix:** build the statement with only the active predicates and bind the values (`sp_executesql`; PG
`EXECUTE format(…) USING`), or one statement per branch (`IF … ELSE`). `OPTION (RECOMPILE)` on the
statement is the SQL Server stop-gap.
**Severity:** High on search/list procedures; Medium elsewhere. How often it runs is 🔬.

### `COUNT(*)` as an existence test ✅
**What:** `IF (SELECT COUNT(*) FROM t WHERE …) > 0`, `SELECT @n = COUNT(*) … IF @n > 0 UPDATE …`, or a
count to choose between `INSERT` and `UPDATE`.
**Why:** Counting finds *every* match to answer a yes/no question, and check-then-act also doubles the
search and races (see *Check-then-act*).
**Fix:** `IF EXISTS (…)`; or perform the DML and test `@@ROWCOUNT`; `MERGE` / `INSERT … ON CONFLICT` for
upserts.
**Severity:** Medium (Low when the predicate is the PK).

### Offset pagination ⚠️
**What:** Paging by row count — `OFFSET n ROWS FETCH NEXT m`, `LIMIT m OFFSET n`, or
`ROW_NUMBER() OVER (ORDER BY …) … WHERE rn BETWEEN @start AND @end`.
**Why:** The engine produces and discards every row before the page, so page N costs O(N), and pages
drift when rows are inserted. If the `ORDER BY` is not unique, row order between pages is undefined.
**Fix:** keyset (seek) paging — remember the last row's sort key and `WHERE (k1, k2) < (@k1, @k2)` (on
SQL Server, `k1 <= @k1 AND (k1 < @k1 OR k2 < @k2)`), with a unique tie-breaker in both the `ORDER BY` and
the index.
**Detect:** also flag an `ORDER BY` whose columns include no PK/`UNIQUE` column.
**Severity:** Medium (the page depth reached is 🔬).

### State accumulation, side effects & dynamic SQL
**What:** Procedures that create global/`##` temp tables, mutate session state, or build and `EXEC()`
SQL strings with values spliced in.
**Why:** Concatenating *values* into the string makes every value a new statement — a fresh parse and
plan per call — and opens SQL injection (code/data separation, theory §11). Dynamic SQL whose values
are bound (`sp_executesql` with parameters; PG `EXECUTE … USING`) is fine, and is the recommended fix
for optional filters. Parameters bind *values* only: table and column names, `ORDER BY` columns and
`ASC`/`DESC` can't be parameters, so a dynamic identifier must come from a whitelist or be quoted with
`QUOTENAME()` (PG `format('%I')`) — even inside `sp_executesql`. Values read back from the database and
spliced into a later statement are as untrusted as user input (second-order injection). Global temp
tables leak state across sessions.
**Detect:** a variable concatenated into the SQL string (`+ @`, `||`), not `EXEC(` alone; `##temp`;
identifiers concatenated without `QUOTENAME`.
**Severity:** High.

### DDL and permanent "work" tables at run time ✅
**What:** Procedures that `CREATE`/`ALTER`/`DROP` real (non-`#`) tables, or `TRUNCATE`-and-refill a
permanent table as scratch space.
**Why:** DDL takes dictionary-level locks, and a permanent work table is empty when statistics are
gathered, so the optimizer plans for zero rows. Structure belongs to design, not to operations.
**Fix:** set-based statements on the real tables; true temporary tables when staging is unavoidable.
**Severity:** Medium.

### Hard-coded optimizer directives ✅
**What:** Index hints by name and plan-shape hints — `WITH (INDEX(ix_…))`, `OPTION (LOOP|HASH|MERGE
JOIN, FORCE ORDER, USE PLAN)`, Oracle `/*+ INDEX(…) */`, MySQL `FORCE INDEX`.
**Why:** A plan frozen for today's volumes and distribution goes wrong as the data changes, and a hint
naming an index breaks silently when the index is renamed or reordered. Outcome hints (`OPTION (FAST
n)`) are acceptable.
**Severity:** Low–Medium (the estate count is useful in the synthesis).

### Parameter sniffing / plan-cache trap 🔬 *(estate-level observation, not a per-proc defect)*
**What:** Cached plans compiled for an atypical parameter value, then reused for typical ones, can
time out.
**Why this is not a per-object grade:** statically you can only observe the *absence* of
`OPTION (RECOMPILE)` / `OPTIMIZE FOR` — which is usually true of essentially every procedure and says
nothing about which one actually suffers (that needs plan-cache telemetry). Grading it per procedure
would flag ~100% and add only noise. (A catch-all predicate is the decidable case and *is* graded.)
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
- `SELECT *`; `INSERT INTO t VALUES (…)` / `INSERT INTO t SELECT …` with no column list; `ORDER BY 1` —
  code that depends on column order, which a relation doesn't have (theory §1.1): an added column breaks
  it, and reordered columns of compatible type are silently misassigned. Medium when the table is a
  migration target (dbpropose, compatibility at every step); Low for a `#temp` created in the same
  procedure.
- `ORDER BY NEWID()` / `RAND()` / `random()` to pick a sample → sorts the whole set to keep one row;
  fine only on small, bounded tables.
- Missing/partial `SET NOCOUNT ON`.
- Hardcoded cross-database calls (`OTHER_DB.dbo.<proc/fn>`) — couples catalogs (see
  [`audit-lenses.md`](audit-lenses.md)).
- No parameter validation; inconsistent header/author/version comment conventions; mixed
  `CREATE PROCEDURE` styling (parenthesized vs bare parameter lists) within the same file.
**Severity:** Low–Medium.

## Engine notes — PostgreSQL (PL/pgSQL)

Criteria 4 and 7 below have no PostgreSQL equivalent and are n/a there (scoring.md): views always
record their dependencies, and there is no `NOCOUNT`. Criterion 2's `TRY/CATCH` half is n/a too — a
function runs inside its caller's transaction — so grade it on swallowed errors and on what runs inside
the transaction. The PostgreSQL defects instead:

- **Mislabeled volatility** — a function declared `IMMUTABLE` that reads tables or depends on settings
  (`now()`, `current_setting`, `TimeZone`, locale-sensitive `to_char`). The planner trusts the label: a
  falsely `IMMUTABLE` function in an expression index or partial-index predicate gives **wrong
  results** once its inputs change. ⚠️ an `IMMUTABLE` body containing `FROM`. High. (A pure function
  left at the default `VOLATILE` can't be indexed and is re-evaluated per row — Low.)
- **Unsafe dynamic SQL** — `EXECUTE '…' || p_name`. Use `EXECUTE format('… %I …', ident) USING value`
  (`%I` quotes identifiers, `%L` literals, `USING` binds values). ✅ High.
- **Swallowed errors** — `EXCEPTION WHEN OTHERS THEN NULL` (or only `RAISE NOTICE`): the failure is
  silently committed, and every `EXCEPTION` block costs a subtransaction. High.
- 🟢 Simple query helpers written `LANGUAGE sql` (or a SQL-standard `BEGIN ATOMIC` body), which the
  planner can inline and whose dependencies are tracked; PL/pgSQL is opaque to the planner.
- `SECURITY DEFINER` without a pinned `search_path`, or still executable by `PUBLIC` — canonical rule in
  [`audit-lenses.md`](audit-lenses.md) §6.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Set-based, not RBAR | no cursor/`WHILE` loop replaceable by one statement; no per-row hidden queries |
| 2 | Transaction safety | `TRY/CATCH` + rollback around every explicit transaction; no external calls or waits inside one |
| 3 | Safe dynamic SQL | values bound via `sp_executesql`/`USING`, never concatenated; identifiers whitelisted or quoted |
| 4 | Functions schemabound where deterministic | `WITH SCHEMABINDING` present |
| 5 | Bounded, typed casts | every `cast(... as varchar(n))` has a length |
| 6 | ANSI joins + explicit columns | no comma-joins, no `SELECT *`, no column-list-less `INSERT` |
| 7 | `SET NOCOUNT ON` | present at top |
| 8 | No hardcoded cross-DB names | no `OTHER_DB.dbo.*` references |
| 9 | Concurrency-safe writes | no dirty-read hint feeding a write; no unprotected read-modify-write or check-then-act; no `MAX()+1` keys |
| 10 | NULL-safe predicates | no `= NULL`; no `NOT IN` over a nullable subquery; no `ANSI_NULLS OFF` |
| 11 | Plan-stable search | no catch-all optional filters; no index hints by name |

> Parameter-sniffing mitigation is **not** a per-file checklist item — it is a 🔬 estate-level
> observation recorded once in the synthesis. Criteria 4 and 7 are n/a on PostgreSQL; criterion 2 is graded
> there on swallowed errors (`EXCEPTION WHEN OTHERS THEN NULL`) and transaction scope.
