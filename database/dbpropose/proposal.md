# Proposal — From Findings to Verdicts and a Target Design

> This runs **after** an audit — every per-DDL evaluation, every per-database summary and (for more
> than one database) the estate synthesis, as produced by `dbaudit`. It consumes the **scores and
> findings** and answers the real question: *what do we keep, what do we fix, what do we redesign, and what does the database look
> like afterwards?*
>
> Two possible deliverables, chosen in the skill's calibration step:
>
> - **Migration** → `target-schema.md`: verdicts, derived topology, modelled target schema (PostgreSQL 18
>   unless the user names another engine), migration plan. Steps 1–5 below.
> - **Remediate in place** → `remediation-plan.md`: verdicts and an ordered change register against the
>   current engine. Step 1, then [Step 6](#step-6--in-place-remediation-register).
>
> Standard of "good" to aim at: [`er-modeling.md`](er-modeling.md) for the model,
> [`physical-design.md`](physical-design.md) for the engine. Do not start this before the evaluations
> exist — its verdicts are only as trustworthy as the scores feeding them.

## Step 0 — Read the audit (the input contract)

What the proposal consumes, and how to read it. If any of this is missing, the audit is incomplete —
say which part, and don't fill the gap by guessing.

| Input | Where it comes from | What you need from it |
|---|---|---|
| **Per-DDL evaluations** | `<db>/analysis/<type>.md` | findings table (object · anti-pattern · confidence · theory · severity · file:line), checklist, **file score** with base and cap, coverage |
| **Per-database summaries** | `<db>/analysis/summary.md` | DB score, status (used / barely used / unused / copy of X), severity tally, 🔬 tally, systemic issues |
| **Estate synthesis** | `estate-analysis.md` (several DBs) | estate score, heatmap, cross-database findings, coupling counts by source → target |
| **🔬 needs-data flags** | every evaluation | each one becomes an open question unless the user resolves it |
| **Rubric and source version** | every header | quoted in the proposal so it can be re-checked |

**How to read the numbers.** Scores are 0–10 per file, weighted by object count per database and per
estate. **Caps** are what matter most: any open **Critical** finding caps a score at 2.0, any open
**High** at 6.0 — a 2.0 with a cap note means *one defect*, not *everything is bad*, so look for the
capping finding before deciding a rebuild. Confidence tags: ✅ decidable (proved from the DDL),
⚠️ proxy (judgement), 🔬 needs-data (not scored, never a fact).

**Severity**, for ordering any change list: **Critical** — silent data loss or corruption (the anchor:
a trigger that processes 1 of N rows); **High** — broad performance degradation or integrity gap
(missing PK, missing FK index, index-suppressing collation mismatch, generic arc); **Medium** —
maintainability cost or controlled redundancy; **Low** — style and naming.

## Step 1 — Reuse vs. rework decision

Classify every object (and every schema) into one of five verdicts. The **score sets the default**;
**findings override it**.

### Default verdict by score band

| Score band | Default verdict | Meaning |
|---|---|---|
| 9.0–10 (Exemplary) | **Reuse** | Port structure as-is; only translate types/syntax to the target |
| 7.0–8.9 (Good) | **Refactor** | Port, with targeted fixes (naming, types, add missing constraints/indexes) |
| 5.0–6.9 (Needs work) | **Rework** | Remodel and redesign the structure ([`er-modeling.md`](er-modeling.md), then [`physical-design.md`](physical-design.md)); **preserve the data and business rules** |
| 3.0–4.9 (Poor) | **Rebuild** | Re-derive from requirements; treat legacy as reference only |
| 0–2.9 (Critical) | **Rebuild** | As above; legacy structure is not trustworthy |
| any, dead schema | **Drop** | Do not migrate (unused databases, copy databases) |

### Override rules (findings beat scores)

- **Any open Critical finding** (e.g. the multi-row trigger data-loss defect) → that object is at
  least **Rework**, regardless of its file score.
- **Business logic buried in the DB** (procedures/triggers carrying app rules) → **Reimplement in the
  application/service layer**, not ported as a DB object. The DB keeps only true invariants.
- **Near-dead schema** (barely used) → default **Drop**; promote individual objects to Reuse/Refactor
  only if a live consumer is confirmed (🔬 needs-data — verify before keeping).
- **Shadow/backup tables** → **Drop**; their *authoritative* sibling is what migrates.

### Three reuse axes (decide each separately)

A verdict isn't one-dimensional — decide structure, data, and logic independently:

| Axis | Question |
|---|---|
| **Structure** | Does the table/relationship shape survive, or get redesigned? |
| **Data** | Do we migrate the rows (cleaned), or start empty? |
| **Logic** | Does the procedure/trigger/view logic port to PG, move to the app, or get dropped? |

Record all three per object in the register (template below). A common outcome: *structure = rework,
data = migrate-with-cleanup, logic = reimplement in app.*

## Step 2 — Topology, derived from the analysis (not assumed)

The target is **one PostgreSQL database** with **schemas grouped by the coupling the evaluation
actually found** — decided bottom-up, not declared upfront:

1. Build a **coupling graph**: nodes = active domains; edges = real cross-database references found in
   the dumps (three-part names `OTHER_DB..TABLE` / `OTHER_DB.dbo.fn…` in triggers/procedures, plus
   shared key columns and FK-by-convention across domains). The audit's estate synthesis should carry
   the counts; if it doesn't, collect them from the dumps (T-SQL shown — `@dblink` on Oracle,
   `otherdb.table` on MySQL):

   ```bash
   # every three-part reference, by file — then read each to get source and target catalog
   grep -noE "\b[A-Za-z_][A-Za-z0-9_]*\.(dbo)?\.[A-Za-z_][A-Za-z0-9_]*" */procedures.sql */triggers.sql */views.sql
   # edge list: <source db> <target catalog> <count>
   grep -oE "\b[A-Za-z_][A-Za-z0-9_]*\.(dbo)?\." */*.sql | sed -E 's#^([^/]+)/[^:]+:([^.]+)\..*#\1 \2#' | sort | uniq -c
   ```
2. **Cluster** tightly-coupled domains into a shared schema; keep loosely-coupled domains as separate
   schemas in the same database (cross-schema FKs are trivial in PostgreSQL — the main reason to
   collapse many catalogs into one database).
3. **Drop** dead schemas; **fold** near-dead survivors into the schema of their consumer.
4. Output a **schema map**: `legacy catalog → target schema (or dropped/folded)`, with the coupling
   evidence justifying each grouping.

Decision is recorded, with its evidence, in `target-schema.md` — not pre-committed here.

## Step 3 — Translation decisions (SQL Server → PostgreSQL 18)

Translate against the *good* target in [`physical-design.md`](physical-design.md), not
literally. Key mappings:

| SQL Server legacy | PostgreSQL 18 target |
|---|---|
| `IDENTITY` | `GENERATED ALWAYS AS IDENTITY`, or `uuid` PK via `uuidv7()` |
| `char(n)` text / `varchar(255)` reflex | `text` (or bounded `varchar(n)` only with a real limit) |
| `numeric(n,0)` / `float` IDs | `integer` / `bigint` |
| `float`/`money` amounts | `numeric(p,s)` |
| `datetime` | `timestamptz` |
| `char(1)` flags `'S'/'N'` | `boolean`, or `enum`/lookup table |
| `text`/`ntext`/`image` | `text` / `bytea` |
| `uniqueidentifier` | `uuid` |
| Mixed `Modern_Spanish_CI_AS` / `SQL_Latin1…` | single encoding + one collation; `citext`/nondeterministic collation only where CI is truly needed |
| Stored procedure (set-based data op) | PL/pgSQL function/procedure |
| Stored procedure (business rule) | **application/service layer** |
| Cursor/`WHILE` RBAR | set-based `UPDATE … FROM` / `INSERT … SELECT` |
| Trigger (hidden side-effect) | app/service layer (visible, testable) |
| Trigger (true invariant) | constraint if possible, else set-based, multi-row-safe PG trigger |
| Multi-row-unsafe trigger (`SELECT @x = … FROM DELETED`) | set-based statement trigger over transition tables |
| View `TOP 100 PERCENT … ORDER BY` | plain view; ordering moves to the query |
| Expensive on-the-fly view | **materialized view**, refreshed `CONCURRENTLY` |
| Cross-DB three-part name | cross-**schema** reference (same DB), or `postgres_fdw` only if a domain stays external |
| Disabled/untrusted constraint (`WITH NOCHECK`) | enforced constraint; load via `NOT ENFORCED` then `VALIDATE` |
| Repeating-group columns (`x_1`, `x_2`, `x_3`) | child / intersection table (er-modeling CAP1 §A1.4) |
| Generic arc (`tipo_ref` + `id_ref`) | explicit FK per target + `CHECK (num_nonnulls(…) = 1)` (er-modeling §A3.2 step 5) |
| `tipo_*` single table with unenforced subtype columns | subtype mapping chosen per er-modeling §A3.2 step 6; per-type `CHECK`s, or supertype + subtype tables |
| Fixed hierarchy-level columns (`jefe_1`, `jefe_2`) | nullable self-referencing FK; walks via `WITH RECURSIVE` (er-modeling §A2.2) |
| History as overwritten columns / unconstrained `desde`/`hasta` | history table with a range column and `WITHOUT OVERLAPS` key (er-modeling §A2.6; physical-design §5.2) |
| Stored derived totals kept by triggers | computed in query, generated column, or materialized view (er-modeling §A1.4) |

## Step 4 — Draft the tentative schema

1. **Seed from the good parts.** Tables scoring 🟢 Reuse/Refactor (proper PK/FK, normalized, sane
   types) are the backbone — port them first; they're proof the domain *can* be modeled well.
2. **Model before you redesign.** For every rework/rebuild domain, **reverse-engineer the conceptual
   model** from the legacy tables ([`er-modeling.md`](er-modeling.md) §A0), then correct it with CAP1–CAP2: resolve M:M,
   remove derived attributes, re-choose UIDs that meet the invariance criterion, make subtypes, arcs,
   recursion and history explicit, and run the CAP4 drills against it. Rebuilds re-derive the model
   from requirements, using the legacy model as reference only.
3. **Map the corrected model** with CAP3's six steps and document the core tables as **Table Instance
   Diagrams** (key type, `NN`/`U` marks, sample rows drawn from the legacy data).
4. **Apply [`physical-design.md`](physical-design.md)**: surrogate keys,
   1NF splits into child tables, magic values → `NULL` + `CHECK`, the FKs that were convention-only
   declared, explicit arcs with exclusivity `CHECK`s, temporal keys for history, one collation.
5. **Place logic**: integrity → constraints; set-based data ops → views/functions; everything else →
   the application layer. Note each relocation.
6. Express the result as **PG18 DDL** in `target-schema.md`, grouped by the Step 2 schema map.

## Step 5 — Data migration & integrity plan

- Deduplicate shadow/backup tables to their authoritative source before load.
- Load with constraints `NOT ENFORCED`, clean data (magic values → `NULL`, collation/type
  normalization, orphan resolution), then `VALIDATE` to switch integrity on.
- Carry every unresolved 🔬 needs-data flag forward as an explicit open question (e.g. confirm
  near-dead schema consumers; confirm INT→`bigint` thresholds by row count).

---

## Step 6 — In-place remediation register

When the target is the **current engine**, Step 1's verdicts become an ordered change list instead of a
new schema. Order by severity (Critical first), then by dependency (a PK before the FKs that reference
it; a constraint before the cleanup that makes it validate):

| # | Finding (file:line) | Severity | Change | DDL / code patch | Data step | Risk & blast radius | Rollback |
|---|---|---|---|---|---|---|---|
| 1 | multi-row-unsafe trigger `trg_x` (triggers.sql:12) | Critical | rewrite set-based over the pseudo-tables | `ALTER TRIGGER …` | none | every delete on the table | previous definition |

Rules: every row cites the finding it fixes; constraints are added untrusted/`NOCHECK` (or the engine's
equivalent) only as a staging step with a dated follow-up to validate; logic moving to the application
is listed as a change with an owner, not silently dropped; each patch is a proposal for review, never
applied by this skill.

---

## Output skeleton — `target-schema.md`

The migration proposal produces this single file. Skeleton:

```markdown
# Target Schema — PostgreSQL v18 (derived from analysis)
> Built from per-database summaries + estate synthesis (rubric v1.1).
> Source dumps as of <date/commit>. Standard: er-modeling.md + physical-design.md.

## 1. Executive summary
<estate score → migration posture; how much reuse vs rebuild; headline risks>

## 2. Reuse / rework register
| Domain | Object (or group) | Score | Verdict | Structure | Data | Logic | Rationale (finding/theory) |
|--------|-------------------|------:|---------|-----------|------|-------|----------------------------|
| sales  | …                 |  x.x  | Rework  | redesign  | migrate+clean | app | … |

## 3. Target topology (schema map, derived)
| Legacy catalog | Target schema | Action | Coupling evidence |
|----------------|---------------|--------|-------------------|
<one DB; schemas grouped by observed coupling; dead = dropped; near-dead = folded>

## 4. Conceptual model per domain (er-modeling.md)
<per target schema: entities with one-line descriptions; relationship sentences; the subtypes, arcs,
 recursion and history decisions taken, and which legacy constructs they replace; CAP4 drills passed>

## 5. Translation decisions
<type/feature/logic mappings actually adopted; deviations from the default table>

## 6. Tentative PostgreSQL 18 schema (DDL)
<CREATE SCHEMA … ; core tables with PG18 types, surrogate keys, FKs, CHECKs, indexes;
 views/matviews; the few invariant triggers; functions kept in-DB>

<core tables also as Table Instance Diagrams (CAP3 §A3.1) where the shape changed>

## 7. Data migration & integrity plan
<NOT ENFORCED → VALIDATE; shadow-table dedupe; repeating groups unpivoted into child rows; generic-arc
 ids split into explicit FKs; cleanup; cutover notes>

## 8. Open questions (carried 🔬 needs-data flags)
<each unresolved data-dependent item blocking a final decision>
```

> Scope honesty: deep normal-form (2NF–4NF) redesign and some reuse decisions depend on data
> profiling (🔬 needs-data) — `target-schema.md` proposes the structure and flags where a data check
> must confirm it before the design is final.
