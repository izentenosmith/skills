# Triggers — Invisible Dependencies & Locking

> Criteria for grading `triggers.sql`. Triggers are the most dangerous objects in a legacy database:
> they execute silently, obscure data lineage, and run inside the invoking transaction. ACID/Isolation
> background in [`theory.md`](theory.md); severity per [`scoring.md`](scoring.md); detection commands
> and confidence tags (✅/⚠️/🔬) in [`detection-signals.md`](detection-signals.md).

## 🟢 Well done

- **Set-based and multi-row-safe** — operate over the whole `INSERTED`/`DELETED` pseudo-tables.
- Minimal logic; no cursors, no per-row scalar-function calls.
- No writes to unrelated tables; no hardcoded cross-database targets.
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

### Hidden side-effects / magic mutations
**What:** Triggers that automatically alter records in *unrelated* tables.
**Why:** Hidden autonomous mutation makes debugging a nightmare — engineers don't realize the
database is changing data on its own.
**Detect:** `UPDATE`/`INSERT`/`DELETE` inside a trigger targeting a table other than the one the
trigger is on.
**Example:** the order-header delete trigger above also deletes from an order-requests table and
updates a virtual-stock table via a cursor — none of them the trigger's own table.
**Severity:** High.

### Transaction-scope inflation
**What:** Heavy work inside the trigger — cursor loops, per-row scalar-function calls, large
validation — all running within the invoking statement's transaction.
**Why:** The row/table locks taken by the original statement are held for the entire trigger
duration, causing blocking and deadlocks under concurrency (Isolation impairment, theory §5).
**Detect:** `CURSOR` / `WHILE` / scalar-function calls inside a trigger body.
**Example:** a delete trigger running a `CURSOR` that calls a quantity-pending scalar function per row
while the delete's locks are held.
**Severity:** High.

### Cascading / recursive loops
**What:** A trigger whose writes fire other triggers, potentially cycling back.
**Why:** Cyclical trigger chains can exhaust the nesting/recursion limit or lock critical tables.
**Detect:** trigger A writes a table that has trigger B that writes A's table; check `RECURSIVE_TRIGGERS`
assumptions and nesting depth.
**Severity:** High.

### Cross-database coupling
**What:** Hardcoded three-part writes to other catalogs (`OTHER_DB..TABLE`).
**Why:** Couples database lifecycles and defeats independent restore.
**Example:** `DELETE FROM SALES_DB..ORDER_REQUESTS …` inside a trigger.
**Severity:** Medium–High.

## Checklist

| # | Criterion | Pass = 🟢 |
|---|---|---|
| 1 | Multi-row safe (no scalar assign from `INSERTED`/`DELETED`) | logic joins the pseudo-tables |
| 2 | No hidden mutations of unrelated tables | trigger touches only its own table / declared scope |
| 3 | Lightweight transaction scope | no cursors / per-row function calls |
| 4 | No cascading/recursive trigger chains | writes don't re-fire the same trigger |
| 5 | No hardcoded cross-database writes | no `OTHER_DB..TABLE` |
| 6 | `SET NOCOUNT ON` + documented intent | present |
