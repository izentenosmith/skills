# Triggers — Invisible Dependencies & Locking

> Criteria for grading `triggers.sql`. Triggers are the most dangerous objects in a legacy database:
> they execute silently, obscure data lineage, and run inside the invoking transaction. Transaction,
> locking and isolation background in [`theory.md`](theory.md) §5; constraint kinds in §7.1; severity
> per [`scoring.md`](scoring.md); detection commands and confidence tags (✅/⚠️/🔬) in
> [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- **Set-based and multi-row-safe** — operate over the whole `INSERTED`/`DELETED` pseudo-tables
  (PostgreSQL: statement-level triggers with `REFERENCING NEW TABLE … OLD TABLE …`).
- Minimal logic; no cursors, no per-row scalar-function calls.
- Exists only for what no declarative constraint can hold — a **transition** or **multi-table** rule
  (theory §7.1) — written set-based or as a deferred constraint trigger, named for the rule it enforces.
- No writes to unrelated tables; no hardcoded cross-database targets; no external I/O.
- Fires only on real changes (`UPDATE OF col`, PG `WHEN (…)`).
- Cannot recurse or cascade uncontrollably.
- `SET NOCOUNT ON`; intent documented.

## 🔴 Not well done

### Multi-row safety — CRITICAL correctness / data-loss defect
**What:** Assigning from `INSERTED`/`DELETED` into a scalar variable:
`SELECT @x = col FROM DELETED`.
**Why:** **SQL Server triggers fire once per statement, not once per row.** When a statement affects
N rows, `DELETED`/`INSERTED` contain all N. A scalar assignment captures **one arbitrary row** and
silently ignores the rest — a 50-row `UPDATE`/`DELETE` processes 1 row and **loses the other 49**.
This is data loss/corruption, not a performance issue.
**Detect:** `SELECT @var = … FROM DELETED` / `FROM INSERTED` (scalar assignment from a pseudo-table).
**Example:** an order-header `AFTER DELETE` trigger beginning `SELECT @ORDER_ID = A.ORDER_ID FROM
DELETED A`, then cleaning up child rows for that one id; a project trigger doing
`SELECT @PROJ = PROJECT_CODE, @DIV = DIVISION_CODE FROM DELETED`.
**Fix:** rewrite set-based, joining the base table to `INSERTED`/`DELETED`.
**Engine note:** row-level engines (Oracle `FOR EACH ROW`, MySQL) don't have this exact defect — see
[`detection-signals.md`](detection-signals.md) for what to look for instead.
**Severity:** **Critical** (the calibration anchor for the Critical tier in [`scoring.md`](scoring.md)).

### Trigger-emulated constraint
**What:** A trigger that re-implements a declarative constraint: `IF NOT EXISTS (SELECT … FROM parent
…) ROLLBACK/RAISERROR` (an FK), `DELETE child WHERE fk IN (SELECT … FROM DELETED)` (`ON DELETE
CASCADE`), `IF EXISTS (… duplicate …) ROLLBACK` (`UNIQUE`), a range or flag test (`CHECK`).
**Why:** Integrity independence (Codd rule 10): the rule isn't in the catalog, so tools, the optimizer
and readers can't see it. It is also **not concurrency-safe** — the trigger's lookup can't see a
concurrent transaction's uncommitted row, so two conflicting writes both pass (write skew, theory
§5.2), whereas declared PK/`UNIQUE`/FK constraints are checked against the current state and can't be
raced.
**Detect:** ⚠️ in a trigger body, `EXISTS`/`NOT EXISTS` on another table followed by `ROLLBACK`/
`RAISERROR`/`THROW`; a `DELETE`/`UPDATE` of a child table keyed on `DELETED`. Cross-check whether a
matching `FOREIGN KEY` or `UNIQUE` exists (if it does, the trigger is redundant).
**Fix:** declare the FK / `UNIQUE` / `CHECK` / `EXCLUDE` and drop the trigger.
**Severity:** High (an integrity gap under concurrency); Medium if a matching declared constraint also
exists.

### Cross-row validation trigger without serialization
**What:** A trigger that queries *other rows* to validate a rule no constraint declares — an overlap
check, a quota, a sum — and rolls back on failure, with no `UPDLOCK`/`HOLDLOCK`/`SERIALIZABLE`/
`TABLOCKX` hint and no lock on the parent row the rule hangs on.
**Why:** Two inserts that conflict each pass, because neither sees the other's uncommitted row — write
skew through the trigger (theory §5.2). It looks like enforcement and isn't, under concurrency.
**Detect:** ⚠️ `IF EXISTS (…)` with `ROLLBACK|RAISERROR|THROW` in the branch and no locking hint.
**Fix:** a declarative constraint (`UNIQUE`; PG exclusion constraint or `WITHOUT OVERLAPS`); otherwise
lock the parent row before checking (physical-design §5.3).
**Severity:** High.

### Hidden side-effects / magic mutations
**What:** Triggers that automatically alter records in *unrelated* tables.
**Why:** Hidden autonomous mutation makes debugging a nightmare — engineers don't realize the
database is changing data on its own. From the writer's side it breaches the Assignment Principle
(theory §7.3): the statement asked for one change and the database made others. A compensatory action
is legitimate only when declared (`ON DELETE CASCADE`, a documented constraint trigger) and known to
every role with write access.
**Detect:** `UPDATE`/`INSERT`/`DELETE` inside a trigger targeting a table other than the one the
trigger is on.
**Example:** the order-header delete trigger above also deletes from an order-requests table and
updates a virtual-stock table via a cursor — none of them the trigger's own table.
**Severity:** High.

### Non-transactional side effects
**What:** A trigger that sends mail, calls HTTP, writes files or runs a shell (`sp_send_dbmail`,
`xp_cmdshell`, CLR, PostgreSQL untrusted languages such as `plpython3u`, `dblink`/`http` calls).
**Why:** Triggers run inside the invoking transaction. If it rolls back, the data change is undone but
the email has already gone — atomicity broken across the boundary (theory §5).
**Fix:** write an outbox row in the same transaction and let a worker act after commit (PG:
`LISTEN/NOTIFY` or a polling worker).
**Detect:** ✅ those calls in a trigger body.
**Severity:** High.

### Transaction-scope inflation
**What:** Heavy work inside the trigger — cursor loops, per-row scalar-function calls, large
validation — all running within the invoking statement's transaction.
**Why:** Locks are held until the *transaction* ends (strict 2PL, theory §5.1), so a heavy trigger
lengthens the transaction and widens its lock footprint — more tables locked, in an order the trigger
chooses. The result is blocking, and deadlocks wherever another path locks the same tables in a
different order: lock-scope inflation, the concurrency cost of isolation.
**Detect:** `CURSOR` / `WHILE` / scalar-function calls inside a trigger body; on PostgreSQL, row-level
triggers that run a query per row on bulk-written tables (use `FOR EACH STATEMENT` with transition
tables).
**Example:** a delete trigger running a `CURSOR` that calls a quantity-pending scalar function per row
while the delete's locks are held.
**Severity:** High.

### Cascading / recursive loops
**What:** A trigger whose writes fire other triggers, potentially cycling back.
**Why:** Cyclical trigger chains can exhaust the nesting/recursion limit or lock critical tables.
**Detect:** trigger A writes a table that has trigger B that writes A's table; check `RECURSIVE_TRIGGERS`
assumptions and nesting depth.
**Severity:** High.

### Cross-database coupling and dual writes
**What:** Hardcoded three-part writes to other catalogs (`OTHER_DB..TABLE`), or four-part writes to a
linked server.
**Why:** Couples database lifecycles and defeats independent restore. A trigger that copies every change
into another database is a dual write with no atomic commit across the two — a partial failure leaves
them diverged, and the copy is an undeclared derived store (theory §6). Linked-server writes pull in
two-phase commit (procedures.md).
**Example:** `DELETE FROM SALES_DB..ORDER_REQUESTS …` inside a trigger.
**Severity:** Medium–High (High for linked-server DML).

### Trigger fires on restore, bulk load or replica apply ⚠️
**What:** Side-effect triggers (audit rows, stock moves, outbound queue rows) with no
`NOT FOR REPLICATION` (SQL Server), no replica-role guard (PG `session_replication_role`), and no
documented disable step for bulk loads.
**Why:** Replaying data re-executes the side effect.
**Severity:** Low–Medium.

## Engine notes — PostgreSQL

- **Values set in an `AFTER` row trigger are ignored** — an `AFTER … FOR EACH ROW` function assigning
  `NEW.col := …`. Changes to `NEW` take effect only in `BEFORE` triggers, so the intended invariant never
  holds. ⚠️ match each function assigning `NEW.` with its `CREATE TRIGGER … AFTER`. High.
- **Order-dependent triggers** — several triggers on one table and event whose logic depends on each
  other: PostgreSQL fires them in **alphabetical order of trigger name**, so a rename changes behaviour.
  ⚠️ count `CREATE TRIGGER … ON t` per (table, timing, event) > 1. Medium.
- **Inventory also** `CREATE EVENT TRIGGER` (fires on DDL) and `CREATE RULE` (tables.md) — hidden
  behaviour that lineage reviews miss.
- A PG trigger function can be attached to many tables: audit the function once and list its
  attachments.
- `SET NOCOUNT ON` (checklist 6, first half) is n/a.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Multi-row safe (no scalar assign from `INSERTED`/`DELETED`) | logic joins the pseudo-tables |
| 2 | No hidden mutations of unrelated tables | trigger touches only its own table / declared scope |
| 3 | Lightweight transaction scope | no cursors / per-row function calls |
| 4 | No cascading/recursive trigger chains | writes don't re-fire the same trigger |
| 5 | No hardcoded cross-database writes | no `OTHER_DB..TABLE` |
| 6 | `SET NOCOUNT ON` + documented intent | present (the `NOCOUNT` half is n/a on PostgreSQL) |
| 7 | Invariants declared, not emulated | no trigger re-implements an FK/`UNIQUE`/`CHECK`/cascade; cross-row checks lock what they read |
| 8 | No non-transactional side effects | no mail/HTTP/file/shell calls; external work goes through an outbox |
