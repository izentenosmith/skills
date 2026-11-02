# Query Rubric — What the Statements, Plans and Workload Show

> The anti-patterns dbquery grades. Many share a name with an entry in dbaudit's
> [`procedures.md`](../dbaudit/procedures.md), [`views.md`](../dbaudit/views.md) or
> [`indexes.md`](../dbaudit/indexes.md): there they are static ⚠️ signals in stored code; here they are
> confirmed or refuted with a plan, a statistic or the application code, and they apply to SQL wherever
> it lives. Each entry gives the evidence that proves it (**Plan**, **Stats** or **Text**), the theory it
> violates ([`theory.md`](theory.md)), the fix, and the severity per [`scoring.md`](scoring.md). Plan
> vocabulary per engine is in [`plan-reading.md`](plan-reading.md).

## Q1. Access paths

### Filter predicates doing an index's work
**What:** An index scan whose index filter or table filter discards most of what it reads — PostgreSQL
`Rows Removed by Filter` ≫ rows returned, SQL Server a `Predicate` beside a narrow `Seek Predicates`, a
`Key Lookup` per row only to test a column.
**Why:** Only access predicates bound the leaf walk (theory §4.1); a filter predicate narrows nothing, so
the cost is every row visited and every table fetch.
**Evidence:** Plan ✅ (rows read vs returned at the node).
**Fix:** reorder or extend the index so the filtering column becomes an access predicate (equality
first, then the range); or an index-only scan when fetches are the cost.
**Severity:** High when the statement is a top share of the workload; Medium otherwise.

### Non-sargable predicate
**What:** A function, implicit conversion, arithmetic or combined columns on the indexed side; a leading
wildcard; `OR` across columns of one index (catalogue in dbaudit indexes.md *Non-sargable predicates*).
**Evidence:** Plan ✅ (a scan or a filter where an index on the raw column exists); Text ⚠️.
**Implicit conversion from the driver** is the case only a plan shows: the parameter arrives as a
different type from the column (a JDBC/.NET string sent as `nvarchar` against a `varchar` column on SQL
Server — `CONVERT_IMPLICIT` on the column side), so every row is converted and the index is skipped.
**Fix:** move the work to the parameter side; bind with the column's type; full-text or trigram indexes
for substring search; an expression index as the last resort.
**Severity:** High on a hot path; Medium otherwise.

### Misestimated cardinality
**What:** Estimated and actual rows differ by 10× or more at a node, and a bad plan choice (nested loop
over many rows, a hash over few, a scan) follows from it.
**Why:** The optimizer chooses from estimates; it uses only the statistics and constraints it has
(theory §4.1).
**Evidence:** Plan ✅ (with actual rows). Causes to name: stale statistics after a bulk load; correlated
columns (`city` and `postal_code`) treated as independent; skew on a column queried with a bind value
(plan-cache *sniffing* — the plan was compiled for an atypical value); a function or table variable the
planner can't see into.
**Fix:** `ANALYZE` / `UPDATE STATISTICS`; extended statistics (`CREATE STATISTICS` on PostgreSQL) for
correlated columns; a higher statistics target on a skewed column; separate statements, or a literal
where a value must steer the plan; `OPTION (RECOMPILE)` as a SQL Server stop-gap.
**Severity:** High when it causes the dominant cost; Medium otherwise.

### Index-only scan opportunity missed — or overreached
**What:** A many-row read whose cost is table fetches for one or two extra columns; or the reverse, an
`INCLUDE` index built for a query whose select list has since grown, so the index-only scan is gone.
**Evidence:** Plan ✅ (PostgreSQL `Heap Fetches`; SQL Server `Key Lookup` count).
**Fix:** add the columns as `INCLUDE` only when fetches are the measured cost; comment which query the
index serves. On PostgreSQL an index-only scan also needs a recently vacuumed table (visibility map).
**Severity:** Medium.

## Q2. Joins

### Nested loop with an unindexed inner side
**What:** A nested-loop join whose inner side is scanned once per outer row.
**Evidence:** Plan ✅ (loops × rows on the inner node).
**Fix:** index the inner join column (the FK column, usually); or let the optimizer pick a hash join by
fixing the estimate that led it to nested loops.
**Severity:** High when the outer side is large.

### Hash or sort spilling to disk
**What:** A hash join or aggregate in several batches, or a sort that spills (PostgreSQL `Batches: >1`,
`Sort Method: external merge`; SQL Server spill warnings).
**Why:** The build side is wider or larger than memory allows — often because the select list carries
columns nobody uses, or the estimate was low.
**Fix:** narrow the select list; filter before joining; fix the estimate; raise the memory setting only
after the rest.
**Severity:** Medium.

### Fan-out join — wrong totals
**What:** Two or more independent one-to-many children joined to a parent before `SUM`/`COUNT`, often
"fixed" with `DISTINCT` (dbaudit views.md *Fan-out aggregate*).
**Evidence:** Text ⚠️; Plan ✅ when the join's actual rows exceed the parent's by the product of the
child counts.
**Fix:** aggregate each child separately, then join.
**Severity:** High — a silent wrong result.

## Q3. Sorting, limits and paging

### Sort not pipelined; top-N that can't stop early
**What:** `ORDER BY … LIMIT/FETCH FIRST` that sorts the whole set because no index delivers that order
after the equality columns.
**Evidence:** Plan ✅ (a `Sort` or `Top N heapsort` over many rows under a `Limit`).
**Fix:** an index on the equality columns followed by the sort columns (theory §4.1).
**Severity:** Medium (High on list pages called per request).

### Offset paging; non-deterministic page order
**What:** `OFFSET n`, `LIMIT m OFFSET n`, `ROW_NUMBER() … BETWEEN`; an `ORDER BY` with no unique
tie-breaker (dbaudit procedures.md *Offset pagination*).
**Evidence:** Plan ✅ (rows produced and discarded grow with the page); Text ⚠️.
**Fix:** seek (keyset) paging on a unique sort key.
**Severity:** Medium.

## Q4. Statement shape

These have full entries in dbaudit [`procedures.md`](../dbaudit/procedures.md) and
[`views.md`](../dbaudit/views.md); grade them here with the evidence a plan or the code adds:

| Anti-pattern | Theory | Severity here |
|---|---|---|
| NULL-unsafe predicates — `NOT IN` over a nullable column, `= NULL` | §3.2 | High; Critical when it drives a write |
| Catch-all optional filters — `(col = @p OR @p IS NULL)` | §4 | High on search endpoints (the plan scans with the filter "on") |
| `COUNT(*)` as an existence test; check-then-act round trips | §4, §5.2 | Medium |
| `DISTINCT` as a join fix | §1.1 | Medium |
| Correlated subquery or scalar function run per row | §4 | Medium–High (Plan ✅: a `SubPlan` or function call per row) |
| `SELECT *` in application code | §1.1 | Low–Medium: it defeats index-only scans, widens hashes and sorts, and breaks on column changes |
| Random sampling by sort (`ORDER BY random()`) | §4 | Low on small tables; Medium on large |
| Non-grouped columns in `GROUP BY` (MySQL without `ONLY_FULL_GROUP_BY`) | §1.1 | High — the value returned is arbitrary |

## Q5. Workload and application patterns

### N+1 queries
**What:** One statement to load a list, then one statement per row of it — an ORM lazy-loading a
relationship inside a loop, a report calling a lookup per line.
**Evidence:** Stats ✅ (a statement whose calls track another statement's returned rows; calls per
request growing with data); ORM logs ✅; Text ⚠️ (a query inside a loop over a result set).
**Fix:** one join or one `IN`/`ANY` batch query; eager loading for that path.
**Severity:** High when on a request path; Medium in batch.

### Row-by-row work from the application
**What:** Fetch-then-update per row, per-row inserts with per-row commits, filtering or aggregating in
application code after fetching everything.
**Why:** Set processing belongs in SQL (theory §4; physical-design §9); every round trip and commit has a
fixed cost.
**Fix:** one set-based statement; batched inserts (`COPY`, multi-row `INSERT`, bulk APIs); commit per
batch.
**Severity:** Medium–High.

### Literals instead of bind parameters
**What:** Values spliced into the SQL text, so every value is a new statement.
**Evidence:** Stats ✅ (many entries whose normalized text is identical — SQL Server one `query_hash`
with many plans; a plan cache full of single-use plans; high parse/compile time); Text ✅.
**Why:** A fresh parse and plan per call, and an injection surface (theory §11).
**Fix:** bind every value. A literal is right only where a value must steer the plan (a heavily skewed
column, partition pruning).
**Severity:** High (injection outranks the parse cost — Q7).

### Long or idle transactions
**What:** Transactions held open across user think-time, HTTP calls or application work — PostgreSQL
`idle in transaction` sessions, long `xact_start` ages; ORM sessions spanning a request handler.
**Why:** Locks are held to commit (theory §5.1), and on PostgreSQL an old snapshot also stops vacuum from
removing dead rows, so every table bloats.
**Evidence:** Stats ✅ (`pg_stat_activity` snapshots, blocking chains); Text ⚠️ (transaction scope in
code).
**Fix:** open the transaction at the first write and close it before any external call; optimistic
concurrency (a version column) for user conversations; `idle_in_transaction_session_timeout`.
**Severity:** High when it blocks others; Medium otherwise.

### Races in application code
**What:** The concurrency anomalies of theory §5.2 written in application code: an ORM loads a row,
changes a counter or balance in memory and saves it (lost update); `if not exists(…): insert(…)`
without a unique constraint (write skew); `max(id) + 1` numbering; a retry loop that retries constraint
violations, or that re-applies a command whose commit succeeded but whose acknowledgement was lost.
**Evidence:** Text ⚠️; the constraint check against the schema ✅.
**Fix:** physical-design §5.3 — declare the invariant, one atomic statement, lock the premise, or
`SERIALIZABLE` with bounded retry on serialization failures only; an idempotency key for retried
commands.
**Severity:** High; Critical when confirmed on money or stock.

## Q6. Writes

### Index write cost not weighed
**What:** A proposed index (or an existing one with no reader in the workload) on a write-heavy table; an
update path that changes an indexed column on every write, defeating PostgreSQL HOT updates.
**Evidence:** Stats ✅ (index scan counts of zero over a representative period —
`pg_stat_user_indexes.idx_scan`, `sys.dm_db_index_usage_stats`; write rates per table); the period must
cover month-end and batch jobs before an index is called unused.
**Fix:** drop or don't create indexes no statement uses; keep frequently updated columns out of indexes
on update-hot tables.
**Severity:** Medium.

### Bulk work done as OLTP
**What:** A large load or backfill run as one statement or one transaction, or row by row through the
application with every index and trigger active.
**Fix:** batches by key range, each idempotent; `COPY`/bulk APIs; build secondary indexes after a load
into a new table (dbpropose ordering rules).
**Severity:** Medium.

## Q7. Safety

- **Injection** — values or identifiers concatenated into SQL text in application code, ORM raw-query
  escapes, report definitions; second-order injection from stored values (theory §11). Text ✅. High.
- **Credentials and personal data in SQL text or logs** — plaintext passwords in statements, bind values
  with personal data in slow-query logs shipped elsewhere. Text/Stats ✅. High.
- **SQL echoed to users** — database error text, including the statement, returned to clients. Text ⚠️.
  Medium.
- **Unchecked results** — a write whose affected-row count or error is ignored, so a guarded `UPDATE …
  WHERE … AND qty >= @n` that touched nothing is treated as success. Text ⚠️. High when it guards money
  or stock.

## Checklist

Grade over the statements reviewed (in-scope = statements the criterion can apply to).

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Access predicates do the filtering | no top-workload statement whose filter predicates discard most rows read |
| 2 | Predicates are sargable | no function, conversion or leading wildcard on an indexed column; parameters bound with the column's type |
| 3 | Estimates hold | no node misestimated ≥ 10× driving the plan choice |
| 4 | Joins fit their indexes | no nested loop over an unindexed inner side; no fan-out aggregate |
| 5 | Sorts and paging are pipelined | top-N served by an index; seek paging on a unique key |
| 6 | Results are correct under NULLs | no `NOT IN` over nullable columns; no `= NULL` |
| 7 | Set-based, not chatty | no N+1; no row-by-row application loops on a request path |
| 8 | Values bound | no literal or concatenated values; identifiers whitelisted |
| 9 | Short, race-free transactions | no transaction across external calls or think-time; no lost update, check-then-act or `MAX()+1` |
| 10 | Every index earns its writes | every index (existing or proposed) on a written table serves a statement in the workload |
