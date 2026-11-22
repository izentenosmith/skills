# Physical Design — PostgreSQL 18 Standard

**Contents:** 1. Realize the model, don't re-invent it · 2. Keys & identity · 3. Naming conventions and schema layout · 4. Normalization targets · 5. Integrity by construction · 6. Data types (PostgreSQL 18) · 7. Indexing strategy (Winand, applied to PG) · 8. Collation & encoding · 9. Where logic lives · 10. Views, materialized views, partitioning, scale · 11. Access design · 12. Modeling checklist

> How a modelled design becomes PostgreSQL 18 DDL: keys, naming, normalization targets, integrity,
> arcs/subtypes/history in the engine, rules no constraint can hold, types, indexes, collation, where
> logic lives, views and scale, access design. It realizes a model built with
> [`er-modeling.md`](er-modeling.md) — it never replaces one. Every "rework"/"rebuild" verdict in
> dbpropose's `proposal.md` means "remodel with `er-modeling.md`, then bring it up to
> this document." For another target engine, keep the model and translate these choices.

## 1. Realize the model, don't re-invent it

This turns a CAP3 design (er-modeling §A3) into PG18 DDL. If a physical choice changes **meaning**
(merges two entities, drops a relationship, stores a derived value), it goes back to the model and is
decided there.

## 2. Keys & identity

The UID criteria in [er-modeling §A1.5](er-modeling.md#a15-unique-identifiers-uid) — never null, unique, invariant, short,
numeric — are why the default is a surrogate key.

- **Default to surrogate keys.** A short, stable, meaningless primary key decouples identity from
  business meaning so foreign keys never break when a code changes.
  - Sequential: `GENERATED ALWAYS AS IDENTITY` (preferred over legacy `serial`, whose sequence is a
    separate object with its own grants and accepts app-supplied ids). `ALWAYS` also makes the key
    non-updatable. Use `BY DEFAULT` only where imports must supply ids. Values are unique — not
    gapless, and not commit order; never read business meaning or event order into them.
  - Keys minted by several writers (offline clients, merges, multi-region): `uuid`, whose value is
    uniqueness without coordination. Seed it with PostgreSQL 18's **`uuidv7()`**: its time prefix makes
    inserts land at the right edge of the B-tree — fewer page splits, a hot cache — where random
    `uuidv4()` scatters inserts across every leaf. uuidv7 order is the generating node's clock: don't
    use it as event or audit order, and remember it reveals the creation time.
- **Natural keys become `UNIQUE` constraints**, not the primary key — the candidate/alternate UIDs of
  the model. The surrogate never replaces them: that constraint is where the business identity lives,
  and without it the same entity can be inserted twice. A natural key with a nullable component needs
  `NULLS NOT DISTINCT` if "missing" must count as a value; otherwise duplicates hide behind NULLs.
- **Declare every candidate key** (theory §2.1) and keep each irreducible.
- **Dependent and intersection entities** (UID includes a relationship) may keep a composite PK of
  their parents' keys, or take a surrogate PK plus a `UNIQUE` on the composite — choose one rule per
  schema. Never drop the composite uniqueness.
- Every table declares a primary key. (Every PostgreSQL table is heap-organized and the PK is a unique
  B-tree; the SQL Server *heap* finding has no PG equivalent, and `CLUSTER` is a one-off reorder.)

## 3. Naming conventions and schema layout

- `snake_case` for all identifiers; one language and one pluralization rule, applied everywhere
  (entities are singular in the model; this guide's examples use singular tables).
- Names trace back to the model (er-modeling §A3.2 steps 1–2); one abbreviation per concept; no reserved words.
- Name the PK for its entity (`bug_id`, not `id`) and reuse that name in FKs unless the FK names a role.
- Constraints named by role: `pk_*`, `fk_*_*`, `uq_*`, `ck_*`, `ix_*`. (Replaces the typical legacy
  mix of `DEPARTMENTS_PK` / `PK_employee_master` / `pk_dtproperties` in one schema.)
- Self-referencing FKs named for the **role** (`manager_id`, `parent_component_id`), not `id2`.
- **No name-versioning.** `_2`, `_old`, `_copia_20120605` are SSOT violations — they don't exist in a
  clean model; history belongs in a history table (er-modeling §A2.6) or VCS, not in object names. No
  data values in names either (`sales_2023`): the value is a column, the split is `PARTITION BY`.
- **Schema-qualify** (`purchasing.purchase_order`): one schema per bounded domain, plus a dedicated
  `extensions` schema; keep application objects out of `public`. Schema-per-tenant moves isolation into
  name resolution — prefer a tenant key + row-level security unless regulation demands physical
  separation.

## 4. Normalization targets

- **3NF is the floor; BCNF the default** wherever the decomposition preserves every FD
  ([er-modeling §A2.1](er-modeling.md#a21-normalization-applied-to-the-er-model); theory §3.1). Where
  BCNF would lose a dependency, either stay at 3NF with the redundancy controlled by a key, or decompose
  and enforce the lost FD explicitly (§5.3) — and record which.
- **4NF/5NF**: an all-key table with three or more parents is checked for independent multi-valued facts
  and cyclic rules (er-modeling §A2.7).
- **6NF for history**: one history table per independently changing attribute (§5.2).
- **1NF is non-negotiable**: no CSV/pipe-delimited strings, no numbered column families, no
  polymorphic `value`/`payload` columns, no EAV. Use a proper child table, or — only when the data is
  genuinely schemaless and not constrained or joined element-wise — `jsonb` (typed, indexable) rather
  than a delimited string.
- **Denormalize only deliberately**: against a *proven* read path, documented, and kept consistent by
  the engine (generated column, materialized view, or a controlled trigger) — controlled redundancy
  (theory §7), never by accident. This is where a derived attribute (er-modeling §A1.4) may become
  stored.

## 5. Integrity by construction

Let the database enforce what the database can enforce (theory §7.1):

- **Referential integrity**: declare every real relationship as a `FOREIGN KEY` to a candidate key.
  Write the action explicitly: `ON DELETE RESTRICT` by default; `CASCADE` only when the child truly
  cannot outlive the parent (the dependent-entity case of er-modeling §A1.5); `NO ACTION` + `DEFERRABLE`
  only where a transaction must pass through a temporarily inconsistent state (swaps, cycles —
  theory §7.2). (PostgreSQL's own default is `NO ACTION`, checked at end of statement; `RESTRICT` is
  checked immediately and can't be deferred.) A composite FK over nullable columns uses `MATCH FULL`.
- **Domain integrity**: `NOT NULL` wherever the attribute is mandatory (`*`) in the model. Choose where
  a value list lives by **how it changes**:
  - **closed by definition** (either/or pairs, a calendar unit, an ISO code set you never edit) →
    `CHECK` or `boolean`; a PG `enum` only for small, code-owned sets (a state machine's states) where
    declaration order is wanted — enum labels can be added and renamed but **never removed**, and carry
    no attributes;
  - **business-volatile** (statuses, categories, document types — anything a user or a release could
    add, rename or retire) → a **lookup table + `FOREIGN KEY`**, with an `is_active` column to retire
    values without deleting history, and optional label and sort columns;
  - replace legacy `char(1)` `'S'/'N'` flags with `boolean`.
- **Every nullable column has exactly one documented meaning** (theory §3.2). *Not applicable* →
  subtype or optional-relationship table, or a type-keyed `CHECK`; *not yet* → a state column +
  `CHECK`; *open-ended* → an unbounded range bound; *unknown* → a nullable column only if that is its
  sole meaning. Never sentinels (`'9999-12-31'`, `''`, `0`, `-1`). A `CHECK` passes on UNKNOWN, so pair
  it with `NOT NULL` when the attribute is mandatory.
- **`CHECK` is deterministic and same-row.** Never a `CHECK` that calls a function reading another table
  (it runs only when *this* row changes), and never a time-relative `CHECK` (`d >= current_date`):
  PostgreSQL assumes `CHECK` conditions are immutable, so the next restore or `VALIDATE` rejects rows
  that were valid when written. Both are §5.3 rules.
- **Migration aid**: add `CHECK` / `FOREIGN KEY` (PG18: also `NOT NULL`) as **`NOT VALID`**. New writes
  are checked at once and legacy rows are left alone; clean the legacy rows, then run
  `ALTER TABLE … VALIDATE CONSTRAINT`, which does not block writes. Never ship a constraint that stays
  `NOT VALID`.
- PG18 **`NOT ENFORCED`** (`CHECK` and FK only) is *not* a migration aid: the engine never checks it, for
  old or new rows, and it can't be validated — switching it on (`ALTER CONSTRAINT … ENFORCED`, for FKs)
  re-checks every row. Use it only to declare a relationship enforced elsewhere (data owned by another
  system), and record who enforces it.

### 5.1 Arcs and subtypes in PG18

- **Arcs** → explicit FK columns + `CHECK (num_nonnulls(individual_id, company_id) = 1)` (`<= 1` if
  the arc is optional). No generic `ref_type` + `ref_id` pairs. When the arc's targets are kinds of one
  concept, remove the arc instead: one FK to the supertype table (er-modeling §A3.2 step 5).
- **Subtypes** → choose per er-modeling §A3.2 step 6. In a single table, enforce each subtype's mandatory columns
  with a `CHECK` keyed on the type column. In supertype + subtype tables, give the supertype a
  `UNIQUE (id, kind)` and have each subtype table reference `(id, kind)` with its `kind` fixed by a
  `CHECK` — exclusivity is then enforced by the database. `UNIQUE (id, kind)` is a deliberate FK-target
  superkey, not a reducible key. **Completeness** (every supertype row has its subtype row) is not
  enforced by it — that is a §5.3 rule.

### 5.2 History and time

- Validity periods as **range types** (`daterange`, `tstzrange`) rather than loose from/to pairs, in
  canonical `[)` form. **Open-ended periods use an unbounded bound** — `daterange(start, NULL)` =
  `[start,)` — never a nullable `valid_to` (an *unknown* end and *until further notice* become
  indistinguishable) and never `'9999-12-31'`.
- **PG18 temporal constraints**: `PRIMARY KEY (part_id, valid_during WITHOUT OVERLAPS)` /
  `UNIQUE (… WITHOUT OVERLAPS)` forbid overlapping periods for the same key, and
  `FOREIGN KEY (part_id, PERIOD valid_during) REFERENCES …` checks the child's period is covered by the
  **union** of the matching parent periods — so parent history may be split across rows. (Scalar
  columns in these constraints need the `btree_gist` extension.)
- **Other non-equality rules** use an exclusion constraint: `EXCLUDE USING gist (room_id WITH =, slot
  WITH &&)` (double booking), optionally with a `WHERE` (only confirmed bookings).
- **"One current row per key"** — a **partial unique index**: `CREATE UNIQUE INDEX uq_price_current ON
  price (product_id) WHERE valid_to IS NULL` (or `WHERE upper_inf(valid_during)`). Its predicate may use
  only immutable expressions, and queries must repeat it to use the index.
- **`WITHOUT OVERLAPS` forbids contradiction, not circumlocution.** Adjacent periods with identical
  values (`[Jan,Mar)` and `[Mar,Jun)`, same price) are accepted, so one fact is stated twice and "when
  did the price change?" lies. Merge on write (extend the existing period when the new value equals the
  old), or flag them with a check query using `-|-` on equal values.
- **Query history packed**: `unnest(range_agg(valid_during))` grouped by key and value, never by
  comparing raw rows.
- **No-gap** rules (er-modeling §A2.6, drills 12 and 24) are not expressible as a key. Enforce them in
  the write path — and serialize writers first: lock the parent (`SELECT … FROM part WHERE part_id = $1
  FOR UPDATE`) or run the transaction `SERIALIZABLE` with retry, *then* close the previous period and
  open the next in that one transaction. "Same transaction" alone is not enough under read committed or
  snapshot isolation (theory §5.2, write skew). Verify with a check query comparing
  `range_agg(valid_during)` per key with the entity's lifetime (one contiguous range expected).
- **One history table per independently changing attribute (6NF)**; group attributes into one history
  table only when they always change together.

### 5.3 Rules no declarative constraint can hold

Classify every catalogued business rule (dbdesign's requirements dossier; theory §7.1) and enforce it
at the **lowest tier that holds it**. Every tier-4 and tier-5 rule appears in the design's validation
checklist with its mechanism, so nobody assumes the schema holds it.

| Tier | Rule shape | PG18 mechanism |
|---|---|---|
| 1 Column/row | a value or same-row predicate | `CHECK`, domain (§6) — deterministic expressions only |
| 2 Key | "at most one …", "no overlap" | `UNIQUE`; partial unique index (`… (copy_id) WHERE returned_at IS NULL` = one open loan per copy); `EXCLUDE` / `WITHOUT OVERLAPS` |
| 3 Restructure | cross-table equality ("same region", "the subtype kind matches") | an **overlapping composite FK**: carry the shared attribute and reference a `UNIQUE (id, attr)` on the parent (`FOREIGN KEY (counsellor_id, region_code) REFERENCES staff (staff_id, region_code)`) — the same device as §5.1's `(id, kind)` |
| 4 Aggregate / cross-row / equality dependency | counts, sums, comparisons across rows; a parent with ≥ 1 child; subtype completeness; a mandatory-both-ends 1:1 | a named `CREATE CONSTRAINT TRIGGER … DEFERRABLE INITIALLY DEFERRED` (fires at commit, so it sees the final state of a multi-statement change) that **locks the parent row** (`SELECT … FOR UPDATE`) or runs under `SERIALIZABLE` — otherwise two concurrent transactions each pass (write skew) — **plus** a named verification query in the test suite |
| 5 Process / authorization | workflow, notifications, who may change what | application or service layer; authorization by `GRANT`/RLS (§11) |

- Prefer moving a rule *up* the table (tier 4 → 3 → 2) by restructuring; each step up removes code. A
  mandatory-both-ends 1:1 usually becomes one table.
- **Invariants under concurrency.** For every invariant, pick the first that fits: (1) declare it; (2)
  one atomic statement — `UPDATE … SET qty = qty - $1 WHERE id = $2 AND qty >= $1` (check the row
  count), `INSERT … ON CONFLICT` for upserts, never read-modify-write in application code or an ORM;
  (3) lock the premise with `SELECT … FOR UPDATE` on the parent row the invariant hangs on; (4)
  `SERIALIZABLE` with a bounded retry on SQLSTATE 40001/40P01 — only those, never a constraint
  violation; (5) materialize the conflict (a slot/lock table to `FOR UPDATE`) as a last resort.
- **Idempotency key** for any command that may be retried end to end (payments, transfers, order
  submission): a client-generated `request_id` with a `UNIQUE` constraint, inserted in the same
  transaction as the effect, so a retried request fails instead of applying twice.
- **Transition rules** (status never moves backwards; a posted entry is immutable) → a `BEFORE UPDATE`
  trigger comparing `OLD`/`NEW`, or no `UPDATE` grant at all (reversals as new rows).
- A rule left to "the app" is recorded as such in the decision register, not silently dropped.

### 5.4 Hierarchies

The model is a recursive relationship (er-modeling §A2.2); the encoding is chosen by the operations
the application needs:

| Encoding | Ancestors / subtree | Insert / move | RI | Use when |
|---|---|---|---|---|
| **Adjacency list** (`parent_id` FK, indexed) + `WITH RECURSIVE` | easy | easy | yes | **Default.** Add a `CYCLE` clause or a no-cycle check on writes |
| **Closure table** (`ancestor_id`, `descendant_id`, `depth`; both FKs; PK on the pair) | easy, indexable | easy, more rows | yes | heavy subtree aggregates or permission checks; a node in several hierarchies (BOM DAGs) |
| **Path enumeration** (`ltree`, materialized path) | easy | easy | **no** | breadcrumbs and sorting; derived from the adjacency list, never the only source |
| **Nested sets** (`lft`, `rgt`) | easy | hard — every insert renumbers other rows | **no** | read-mostly trees only |

Never encode depth as fixed columns (`level1_id`, `level2_id`) or fixed self-joins.

## 6. Data types (PostgreSQL 18)

| Use | Not |
|---|---|
| `text` (or `varchar(n)` only with a real business bound) | `char(n)` padding; reflexive `varchar(255)` |
| `integer` / `bigint` for identifiers and codes | `numeric(n,0)` or `float` as IDs |
| `numeric(p,s)` + a currency-code column for money and exact quantities | `float`/`real` for money; the `money` type (output depends on `lc_monetary`, no currency) |
| `timestamptz` for points in time; plus an IANA zone name (`text`) when local wall-clock time matters (store hours, schedules) | naive `timestamp`/legacy `datetime`; `timetz`; assuming `timestamptz` stores the zone (it stores UTC) |
| `daterange` / `tstzrange` for validity periods; unbounded bounds or `'infinity'` for "no end" | separate `desde`/`hasta` columns with no constraint; `'9999-12-31'` sentinels |
| `date` for dates | dates as `char(8)`/`int` (`YYYYMMDD`) |
| `boolean` for flags | `char(1)` `'S'/'N'` |
| `uuid` for surrogate keys (via `uuidv7()`) | `uniqueidentifier`-as-string |
| `bytea` in-row (TOAST) for documents that must share the row's transaction, backup and privileges; an external object store only with a documented lifecycle (hash, size, media type, orphan cleanup, backup pairing) | bare path strings with no lifecycle; deprecated `text`/`ntext`/`image` |
| `jsonb` for genuinely schemaless data | `json` (re-parsed on every access, no GIN, keeps duplicate keys); JSON/CSV stuffed in a `text` column |
| **Generated columns**: `VIRTUAL` (the PG18 default) for computed display values; **`STORED`** when the value must be indexed, unique or referenced (a virtual column can't be) | hand-maintained denormalized copies |
| `CREATE DOMAIN` per shared business concept (`email_address`, `postal_code`, `money_amount`) carrying the base type and `CHECK` once | the same concept re-declared with different types, lengths or `CHECK`s per table |

- **One concept, one definition.** The same concept has the same name, domain and length in every
  table; an FK has exactly the referenced key's type. Keep `NOT NULL` on the column, not in the domain
  (outer joins and defaults can bypass a domain's `NOT NULL`). SQL domains are not true types —
  PostgreSQL will still compare a `postal_code` with any other `text` — they buy one definition of
  representation and constraint, not type safety.
- **External code standards beat home-grown codes** for shared reference data: ISO 3166-1 (country),
  ISO 4217 (currency), ISO 639 (language; say which part), E.164 (phone). Store the code as the lookup's
  natural key (`UNIQUE`) and say which standard and version.
- **The data dictionary lives in the catalogue**: `COMMENT ON TABLE` / `COLUMN` from the dossier's
  definitions, so the schema describes itself (Codd rule 4).

## 7. Indexing strategy (Winand, applied to PG)

- **Every index names the access path it serves** — an FK, a `UNIQUE` rule, or a named query's
  `WHERE`/`JOIN`/`ORDER BY`. An index with no named path isn't created. Every index is a write tax, and
  on PostgreSQL the tax is per update too: an update that changes any indexed column, or can't stay on
  its page, writes a new entry in *every* index. Don't index columns that change often on update-hot
  tables, and leave page headroom (§10) so updates stay HOT.
- **Foreign keys**: index every FK column whose parent is deleted or key-updated, or that is navigated
  parent→child. An FK that already leads another index (typically the intersection table's composite
  PK) needs no extra index; one that is the *second* column of a composite does. PostgreSQL does not
  create FK indexes automatically.
- **Composite column order: equality → range → sort.** Only one range column can bound a scan; "most
  selective first" is a myth (theory §4.1). If a query has `ORDER BY`, put the sort columns right after
  the equality columns so the index serves it pipelined and top-N stops early. PostgreSQL 18's B-tree
  skip scan relaxes some leftmost-prefix penalties, but deliberate order still wins.
- **Index the raw column, one expression per concept.** Prefer rewriting the predicate (explicit date
  ranges) to an expression index; when one is needed (`lower(email)`), use the same function everywhere
  so one index serves.
- **Partial indexes** (`WHERE`) for selective subsets — the right answer to many low-cardinality flags
  instead of indexing the whole column. They are used only by queries that state the predicate
  literally: `WHERE processed = false` matches `processed = false`, not `processed = $1`.
- **Covering indexes** (`INCLUDE`) only for a demonstrated table-access bottleneck on a many-row read.
  `INCLUDE` columns can't be access predicates, and adding one column to the query's select list
  silently loses the index-only scan — comment which query the index serves.
- **Physical correlation** decides range-scan cost: time-ordered keys (identity, `uuidv7()`) keep
  insertion order correlated with key order; check `pg_stats.correlation` before adding `INCLUDE`
  columns.
- **Index methods.** B-tree is the default and the only one for PK/`UNIQUE`. **GIN** for "contains"
  searches — `jsonb` (`@>`, `?`; `jsonb_path_ops` when only `@>` is queried), arrays (`&&`, `@>`),
  `tsvector` full text, `pg_trgm`; queries must use the indexable operator (`col @> ARRAY[x]`, not
  `x = ANY(col)`). **GiST** for ranges, exclusion constraints and geometry. **BRIN** for very large
  append-only tables whose key follows insertion order (event time, ledger id) — tiny and cheap, useless
  once rows are updated or arrive out of order.
- **Text search.** `LIKE 'abc%'` uses a plain B-tree only under a `C`/`C.UTF-8` collation; otherwise add
  an index with `text_pattern_ops`. A leading `%`, `ILIKE` or regex needs `pg_trgm` (GIN) or full text
  (`tsvector` generated `STORED` column + GIN) — never `LIKE '%…%'` on a hot path.
- **Multicolumn vs separate.** The planner can combine single-column indexes with bitmap scans; reserve
  composites for predicate sets known to recur, and keep them narrow.
- **GiST** indexes back range/temporal constraints (§5.2); recursive FKs get a plain B-tree so
  `WITH RECURSIVE` hierarchy walks stay cheap.
- No index that merely duplicates or prefixes another (unless it is unique or partial).

## 8. Collation & encoding

- One database, `UTF-8` encoding, **one** collation strategy — ending any legacy collation split
  (e.g. `Modern_Spanish_CI_AS` beside `SQL_Latin1_General_CP1_CI_AS`) that suppresses cross-domain
  joins.
- Pick the provider **at `CREATE DATABASE`** — it can't be changed afterwards (create from
  `template0`). Default to `LOCALE_PROVIDER builtin`, `BUILTIN_LOCALE 'C.UTF-8'` (or PG18's
  `PG_UNICODE_FAST`, which adds full Unicode case mapping): code-point order, immune to glibc/ICU
  version changes, and plain B-trees serve `LIKE 'abc%'`. Code-point order is **not** linguistic — for
  Spanish, accented letters and `ñ` sort after `z` — so where people read the order (names, product
  lists), put an **ICU collation on that column or in that `ORDER BY`** (`COLLATE "es-CL-x-icu"`), not
  as the database default.
- With an ICU or libc default, record `pg_collation_actual_version()` and plan a `REINDEX` after any
  collation-library upgrade.
- For case-insensitive matching, use an ICU **nondeterministic collation** (`deterministic = false`)
  on the specific columns that need it — they can't be a database default; PG18 supports `LIKE` on them
  but not regular expressions, and a B-tree on such a column can't serve prefix `LIKE`. The portable
  alternative for case-insensitive uniqueness is `CREATE UNIQUE INDEX … (lower(col))` with every query
  written as `lower(col) = …`. Not `citext`, and not a blanket CI collation across the estate.

## 9. Where logic lives

- **Business decisions → application/service layer; data processing → set-based SQL.** The database
  is not an application framework, and it is not a dumb store either: filtering, joining, gap-filling
  and window calculations belong in the query, not in application loops over fetched rows.
- **The database enforces invariants** (constraints, §5.3) and performs **set-based data operations**
  (views, set-based functions).
- **Triggers only for true data invariants** that no declarative constraint can hold, written
  **set-based and multi-row-safe** (PostgreSQL fires statement-level and row-level triggers; prefer
  statement-level set logic with transition tables, and never assume a single affected row). No hidden
  side-effects mutating unrelated tables, and no external I/O (mail, HTTP) — those move to the service
  layer, or to an outbox row acted on after commit, where they are visible and testable.
- **Derived attributes** are computed by query, a generated column or a materialized view — not by a
  trigger keeping a `total_*` column in step.
- **Cursors/RBAR → set-based SQL.** A loop that updates row-by-row becomes one `UPDATE … FROM …`.
  Hierarchy walks become `WITH RECURSIVE`.

## 10. Views, materialized views, partitioning, scale

- **Views** for abstraction; shallow, explicit column lists, no fake `TOP 100 PERCENT … ORDER BY`.
  Ordering belongs in the consuming query. Views are also how a single-table subtype design exposes
  each subtype, and how a separate-tables design exposes the supertype (`UNION ALL` between disjoint
  branches, read-only). Every view has a nameable key. Single-table views written through are
  auto-updatable — give them `WITH CHECK OPTION`; multi-table write paths use `INSTEAD OF` triggers,
  never `CREATE RULE`. Views over RLS-protected tables use `WITH (security_invoker = true)`.
- **Materialized views** for expensive, slowly-changing aggregates; refresh `CONCURRENTLY` on a
  schedule — which requires a `UNIQUE` index on the materialized view. A materialized view is derived
  data (theory §6): document its source, its refresh schedule and the staleness its readers accept, and
  never write to it by any other path. Changing its definition means `DROP` + `CREATE`, so the DDL must
  re-emit its indexes and grants. PostgreSQL never refreshes one automatically.
- **Declarative partitioning** for large/time-series tables (attendance, time logs, ledgers, audit
  history) — by range (date) or list (domain) — never `INHERITS` + `CHECK`, and never hand-made
  per-year or per-tenant clones. Partition only for a stated goal (pruning, cheap archival by
  detach/drop); choose the key from the dominant predicates, since pruning happens only when a query
  constrains it as a bounded range. A partitioned table's PK/`UNIQUE` **must include the partition
  key**, so decide the key before the uniqueness model. Partitioning is not sharding: it is one node, and
  time-range partitions concentrate current writes in one partition.
- **Fillfactor**: heap `fillfactor` below 100 (say 70–90) only on update-heavy tables whose updated
  columns aren't indexed, so updates stay HOT; leave insert-mostly and append-only tables at 100 (not a
  legacy smell on PostgreSQL; B-tree indexes already default to 90). PostgreSQL 18's asynchronous I/O
  speeds large scans and vacuum without schema changes.
- **`UNLOGGED`** only for data you can rebuild (sessions, staging) — it is wiped after a crash and
  absent on replicas.

## 11. Access design

Designed from the access matrix in the requirements dossier and delivered with the DDL (theory §11).

- **Roles, not logins.** One `NOLOGIN` **owner** role owns every object and runs migrations. The
  application connects as a **runtime** role with only the DML it needs — never the owner. Add
  reporting/read-only roles and one role per job function; grant to roles, grant roles to logins.
- **Close the defaults.** `REVOKE ALL ON DATABASE … FROM PUBLIC`; `REVOKE CREATE ON SCHEMA public FROM
  PUBLIC` (the default since PG15 — state it for upgraded clusters); `REVOKE EXECUTE ON ALL FUNCTIONS
  IN SCHEMA … FROM PUBLIC`; `GRANT USAGE ON SCHEMA` to each consumer role; `ALTER DEFAULT PRIVILEGES FOR
  ROLE <owner> IN SCHEMA …` so new objects follow the matrix.
- **External schemas = views per audience**, granted instead of the base tables — also logical data
  independence (Codd rule 9). `security_barrier` for row-filtering views.
- **Column level**: `GRANT SELECT (col, …)` or a view. **Row level**: `ENABLE` + `FORCE ROW LEVEL
  SECURITY` with policies (the owner and `BYPASSRLS` roles bypass unless forced).
- **`SECURITY DEFINER` functions** pin `SET search_path` and `REVOKE EXECUTE … FROM PUBLIC`.
- **Separation of duties**: whoever manages roles doesn't need to read the data.
- **Secrets**: passwords hashed with a slow one-way function in the application, never encrypted or
  plain; column encryption (`pgcrypto`) only with real key management; TLS in transit.
- **Identifiers are not authorization.** A sequential or time-ordered surrogate exposed in a URL is
  guessable; authorize every access, and use a separate random public id where one is exposed.
- **Sensitivity** classes from the data dictionary decide which columns get column grants, masking
  views or RLS.

## 12. Modeling checklist

| # | The model… | Good = 🟢 |
|---|---|---|
| 1 | passed conceptual → logical → physical | not grown table-by-table; an ER model exists per domain |
| 2 | reads aloud | every relationship has a two-way sentence; no *related to* / *associated with*; every table has a one-sentence predicate |
| 3 | has no unresolved M:M | every M:M is an intersection entity with mandatory relationships out of it |
| 4 | has no derived attributes in the model | totals/counts/averages computed, or stored by a documented physical decision; event-time facts kept |
| 5 | uses UIDs that meet er-modeling §A1.5; surrogate PKs; natural keys are `UNIQUE` | no volatile-natural-key or intelligent-key PKs; every candidate key declared and irreducible |
| 6 | is BCNF where dependency-preserving, ≥ 3NF otherwise; 1NF strict | no CSV/polymorphic/EAV columns, no numbered column families; lost FDs enforced and recorded |
| 7 | models recursion, subtypes and arcs explicitly | recursive FKs optional; arcs = explicit FKs + `CHECK` or a supertype FK; subtype mapping chosen and justified |
| 8 | models history only where the user asked for it | time in the UID; overlaps forbidden by constraint; open ends unbounded; gap rule stated |
| 9 | enforces FK / CHECK / NOT NULL | integrity in the DB, not the app; every model rule no FK expresses has a named mechanism (§5.3) |
| 10 | gives every nullable column one documented meaning | no `'9999…'`/`''`/`0` sentinels |
| 11 | uses correct PG18 types | per the type table above; one domain per shared concept |
| 12 | indexes FKs; sargable predicates | every index names its access path; no suppressed indexes, no redundancy |
| 13 | one encoding + one collation strategy | no collation split |
| 14 | keeps business logic in the app layer | DB enforces, app decides |
| 15 | consistent `snake_case` + role-named constraints | no name-versioning; one abbreviation per concept |
| 16 | is documented with TIDs for core tables | key type, `NN`/`U` marks and sample rows agree |
| 17 | has an access design | owner/runtime role split; no `PUBLIC` grants; views or RLS for restricted data |
| 18 | survived the phase hand-offs | every PK, `NN`/`U` mark and FK type in the DDL matches the TID and data dictionary; differences listed as decisions, not drift |
| 19 | is safe under concurrency | every invariant mapped to a declared constraint, an atomic statement, a lock or `SERIALIZABLE` (§5.3) |
