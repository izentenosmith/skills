# Plan Reading — Four Engines

**Contents:** What to ask of every plan · PostgreSQL · SQL Server · Oracle · MySQL / MariaDB · Application-side evidence

> Where each engine shows what [`query-rubric.md`](query-rubric.md) needs: access vs filter predicates
> (theory §4.1), estimated vs actual rows, join methods, sorts and spills, pages visited, and the
> workload statistics that rank statements. Read a plan from the most indented node outward; the node
> where estimates first go wrong is the one to explain.

## What to ask of every plan

1. **Which predicates are access predicates?** Only they bound the index walk. Everything else is a
   filter, and its cost is rows read minus rows returned.
2. **Estimated vs actual rows, per node.** Multiply per-loop figures by the loop count.
3. **Join method and inner side.** Nested loops: is the inner join column indexed? Hash/merge: how big is
   the build side, and does it spill?
4. **Is there a sort?** Could an index deliver the order? Does a top-N stop early?
5. **Pages visited** (buffers, logical reads) — the load indicator that survives caching; elapsed time
   alone varies with what is warm.
6. **Where did the plan come from?** An estimated plan has no actual rows; a plan from a small database
   misleads about a large one.

## PostgreSQL

- **Get it:** `EXPLAIN (ANALYZE, BUFFERS) <statement>` — `ANALYZE` **executes** the statement (wrap DML
  in `BEGIN; … ROLLBACK;`); plain `EXPLAIN` shows estimates only. `auto_explain` captures plans of slow
  statements in production without running anything yourself.
- **Predicates:** `Index Cond:` lists the conditions passed to the index — but on a B-tree only the
  leading equality columns and the first range column actually bound the walk; conditions on later
  columns are checked inside the walk (compare with the index definition). `Filter:` is a table filter;
  `Rows Removed by Filter: n` is its waste. `Recheck Cond` / `Rows Removed by Index Recheck` belong to
  bitmap scans (lossy pages). PostgreSQL 18 reports `Index Searches` when skip scan probes an index
  several times.
- **Rows:** `(cost=… rows=E width=…) (actual time=a..b rows=A loops=L)` — `A` is per loop; total actual
  rows = `A × L`. Compare `E` with `A`.
- **Index-only scans:** `Heap Fetches: n` — fetches caused by pages not yet marked all-visible (vacuum
  the table).
- **Sorts and hashes:** `Sort Method: quicksort | top-N heapsort | external merge Disk: …kB` (a spill);
  `Hash … Batches: n` with `n > 1` (a spill); `Memory Usage`.
- **Buffers:** `shared hit` (from cache) and `read` (from disk); `temp read/written` means spills.
- **Workload:** `pg_stat_statements` (`calls`, `total_exec_time`, `mean_exec_time`, `rows`,
  `shared_blks_hit/read`; texts normalized with `$n`); `pg_stat_user_tables` (`seq_scan`, `n_tup_upd` vs
  `n_tup_hot_upd`); `pg_stat_user_indexes` (`idx_scan` — zero over a representative period suggests an
  unused index); `pg_stats` (`n_distinct`, `most_common_vals`, `correlation`); `pg_stat_activity`
  (`state = 'idle in transaction'`, `xact_start`, wait events).

## SQL Server

- **Get it:** the *actual* execution plan (`SET STATISTICS XML ON`, or SSMS "Include Actual Execution
  Plan"); `SET STATISTICS IO, TIME ON` for logical reads per table. Query Store holds plans and runtime
  statistics over time without re-running anything.
- **Predicates:** `Seek Predicates` are access predicates; `Predicate` on the same operator is a filter.
  A `Key Lookup` (clustered table) or `RID Lookup` (heap) per row is the table fetch — check its
  `Number of Executions`.
- **Rows:** `Estimated Number of Rows` vs `Actual Number of Rows` (per execution, times `Number of
  Executions` on the inner side of loops).
- **Warnings:** `PlanAffectingConvert` / `CONVERT_IMPLICIT` on a column (a type mismatch, often from the
  driver's parameter type); `SpillToTempDb` on sorts and hashes; `No join predicate`.
- **Missing-index suggestions** in the plan or `sys.dm_db_missing_index_*` are hints, not
  prescriptions: they ignore column order beyond equality vs inequality, overlap with existing indexes,
  and write cost. Weigh them against the workload (dbquery Step 4) before recommending one.
- **Workload:** Query Store (`sys.query_store_runtime_stats`; one `query_hash` with many `query_id`s or
  plans points to literals or sniffing); `sys.dm_exec_query_stats` (since the last restart only);
  `sys.dm_db_index_usage_stats` (seeks/scans/lookups vs updates per index; reset at restart);
  `sys.dm_exec_requests` and `sys.dm_tran_*` for blocking and long transactions.

## Oracle

- **Get it:** run with the `gather_plan_statistics` hint (or `statistics_level = ALL`), then
  `DBMS_XPLAN.DISPLAY_CURSOR(format => 'ALLSTATS LAST')`. `EXPLAIN PLAN` shows estimates only.
- **Predicates:** the *Predicate Information* section lists each operation's `access(…)` (access
  predicates) and `filter(…)` (filters) by operation id — the clearest of the four engines.
- **Rows:** `E-Rows` (estimate per start) vs `A-Rows` (actual, total), with `Starts`; `Buffers` per
  operation.
- **Access paths:** `INDEX RANGE SCAN` then `TABLE ACCESS BY INDEX ROWID [BATCHED]` (the fetch);
  `INDEX FAST FULL SCAN`; `TABLE ACCESS FULL`. All-NULL keys aren't stored in a single-column B-tree, so
  `col IS NULL` can't use one.
- **Workload:** `V$SQL` / `V$SQLSTATS` (executions, elapsed time, buffer gets); AWR and ASH reports where
  licensed.

## MySQL / MariaDB

- **Get it:** `EXPLAIN FORMAT=TREE` or `EXPLAIN ANALYZE` (MySQL 8.0.18+, executes the statement);
  classic `EXPLAIN` gives one row per table.
- **Classic columns:** `type` (`const` / `eq_ref` / `ref` / `range` good → `index` full index scan →
  `ALL` full table scan); `key` and **`key_len`** (how many bytes — so how many leading columns — of the
  index are access predicates); `rows` × `filtered` (estimated rows surviving the conditions).
- **`Extra`:** `Using index` (index-only); `Using index condition` (index condition pushdown — an index
  filter, not an access predicate); `Using where` (a table filter); `Using filesort` (a sort);
  `Using temporary` (a temporary table for `GROUP BY`/`DISTINCT`).
- **Engine notes:** InnoDB clusters every table on its primary key, so secondary-index lookups go through
  the PK — a wide PK widens every index. InnoDB indexes foreign keys automatically.
- **Workload:** `performance_schema.events_statements_summary_by_digest` (normalized statements with
  counts, total latency, rows examined vs sent); the slow query log with `log_queries_not_using_indexes`
  used carefully; `sys` schema views.

## Application-side evidence

- **ORM logs** with SQL and bind values (redact them) show N+1 shapes and transaction boundaries
  directly; count statements per request.
- **APM traces** give per-request statement counts and latencies — the business-unit ratio of Step 1.
- **Connection-pool metrics** (wait time, active connections) show when long transactions, not slow
  statements, are the bottleneck.
