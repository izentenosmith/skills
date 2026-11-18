# Theory Foundations

> The conceptual backbone of the audit rubric and of the proposals built on it. Every theoretical term
> a finding, a verdict or a design decision cites is defined **here once** and only referenced
> elsewhere. Read this first. §9 adds the entity–relationship vocabulary used by
> [`er-modeling.md`](er-modeling.md) (CAP1–CAP4); §10–§11 add the data/metadata and security anchors.

## 1. The relational model (Codd, 1970)

Modern relational databases descend from E. F. Codd's *A Relational Model of Data for Large Shared
Data Banks* (1970). Codd treats data as mathematical **relations** over **attributes**, enforcing
**data independence** — decoupling *how data is queried* from *how it is physically stored*. When we
grade a schema, we are ultimately asking how faithfully it honours that model: are facts represented
as well-formed relations, or has physical/ad-hoc structure leaked into the logical design?

### 1.1 Relations, relvars, predicates

| Term | Meaning |
|---|---|
| **Relation** | A *value*: a heading (a set of attribute name/type pairs) and a body (a **set** of tuples). No duplicate tuples, no tuple order, no attribute order, exactly one value of the declared type per attribute per tuple — hence no NULLs. |
| **Relvar** | A *variable* whose value at any time is a relation. A base table is a real relvar; a view is a virtual one. Keys, FDs and normal forms are properties of **relvars** — of every value they are permitted to hold — not of the rows present today. |
| **Predicate** | The table's meaning: a sentence with one placeholder per column ("Employee *E* works in department *D* since *S*"). Each row is a true proposition; under the **Closed World Assumption** a plausible row that is absent is false. |
| **Information Principle** | All information is represented one way only: as values in columns of rows — never in row order, column position, hidden row ids, object names (`sales_2023`), or the presence of a sentinel. |

**An SQL table is not a relation.** It departs in three ways the audit watches: it may hold
**duplicate rows** (no key; a view that projects every key away or `UNION ALL`s overlapping sets); it
may hold **NULLs**, which are not values (§3.2); and SQL lets code depend on **column order**
(`INSERT … VALUES` with no column list, `SELECT *`, `ORDER BY 1`). A table is relationally faithful
when it declares a key, every nullable column has one documented meaning, and no code depends on
column position.

### Codd's rules (Codd, 1985)

The 0–12 rules come from Codd's 1985 *Computerworld* articles, not the 1970 paper. Use them as a
design and review lens for relational behavior, not as a claim that every SQL product implements every
ideal perfectly. Check applicability and evidence; distinguish a logical design defect from an engine
limitation.

| Rule | Principle |
|---|---|
| 0 — Foundation | A system presented as relational manages data through relational capabilities. |
| 1 — Information | All information is represented as values in relations (§1.1, the Information Principle). |
| 2 — Guaranteed access | Each atomic value is reachable by relation, key, and attribute. |
| 3 — Systematic treatment of nulls | Missing or inapplicable information has a consistent treatment, independent of data type. |
| 4 — Dynamic catalog | Metadata is represented relationally and queryable through the data language. |
| 5 — Comprehensive language | One relational language supports definition, views, manipulation, integrity, authorization, and transactions. |
| 6 — View updating | All theoretically updatable views are updatable. |
| 7 — High-level insert, update, delete | Set-level operations work on relations, not only one row at a time. |
| 8 — Physical independence | Storage changes do not require application changes. |
| 9 — Logical independence | Certain logical schema changes do not force application changes. |
| 10 — Integrity independence | Integrity constraints — entity and referential integrity at least — are declarative and stored in the catalog, not hidden only in applications. |
| 11 — Distribution independence | Data distribution does not require application changes. |
| 12 — Nonsubversion | Lower-level access cannot bypass relational integrity rules. |

- **Rule 3** is Codd's; Date & Darwen reject nulls and three-valued logic entirely. This skill family
  takes the middle path of §3.2: NULL is allowed, each nullable column carries one meaning, and designs
  where that meaning is structural are preferred.
- **Rule 6** rests on "theoretically updatable", which Codd never defined. The workable test is §7.3:
  a view is updatable subject to its constraints, and an update through it must satisfy the
  Assignment Principle. The audit question is whether writes *through* a view can produce a row the
  view doesn't show.

## 2. Functional dependencies (FDs)

A **functional dependency** `X → Y` holds on relation schema `R` when, in **every legal instance** of
`R`, any two tuples that agree on `X` also agree on `Y`. An FD is a **business rule** about the schema,
not an observation about today's rows. Data can **refute** an FD (two rows agree on `X` and differ on
`Y`) or suggest a candidate; it can never **establish** one — only the business rule (the table's
predicate) does. FD theory assumes determinants are never NULL; NULLs in a key-like column void the
analysis.

FDs are the tool for discovering the *true* keys of the data: if a non-key column determines another
column, you have found redundancy that threatens integrity.

### Armstrong's axioms

The inference rules (sound and complete) that derive every FD implied by a set `F`:

- **Reflexivity** — if `Y ⊆ X` then `X → Y` (a **trivial** FD).
- **Augmentation** — if `X → Y` then `XZ → YZ`.
- **Transitivity** — if `X → Y` and `Y → Z` then `X → Z`.

Derived rules: **union** (`X → Y`, `X → Z` ⇒ `X → YZ`), **decomposition** (`X → YZ` ⇒ `X → Y`),
**pseudotransitivity** (`X → Y`, `WY → Z` ⇒ `WX → Z`). Transitivity is the one that exposes 3NF
violations: `key → A → B` means `B` is stored against the wrong key and will exhibit update anomalies.

### 2.1 Keys

- **Superkey** — a column set `K` with `K → R`: no two rows may share it.
- **Candidate key** (key) — an **irreducible** superkey: no proper subset is also unique. An attribute
  in some candidate key is **prime**. A table may have several keys (a roster: `{day, hour, gate}` and
  `{day, hour, pilot}`); declare **all** of them — one `PRIMARY KEY`, the rest `UNIQUE`. Primary vs
  alternate is a convenience; a foreign key may reference any candidate key.
- **The engine enforces uniqueness only.** Declaring `PRIMARY KEY (a, b)` when `{a}` alone is unique
  leaves `{a}` unenforced — a declared key can be a proper superkey. The exception is a deliberate
  FK-target superkey such as `UNIQUE (id, kind)` (physical-design §5.1).
- Key columns are never NULL. SQL `UNIQUE` admits NULLs (many in standard SQL and PostgreSQL unless
  `NULLS NOT DISTINCT`; one in SQL Server), so a nullable `UNIQUE` is not a key.
- An empty key `{}` means "at most one row" — the correct model of a singleton settings table.
- **Surrogate keys normalize nothing.** Run dependency analysis over the natural attributes and UIDs,
  then add the surrogate. A table whose only key is an `IDENTITY` passes every key-based test formally
  while keeping every redundancy it had — and admits the same entity twice unless its natural key is
  `UNIQUE`.

### 2.2 Reasoning with FDs

- **Attribute closure `X⁺`** — start with `X`; for each FD `β → γ` with `β ⊆` result, add `γ`; repeat
  until nothing changes. `X` is a superkey ⇔ `X⁺ = R`; `X → Y` holds ⇔ `Y ⊆ X⁺`. Never compute `F⁺`
  by hand; use closures.
- **Canonical (minimal) cover `Fc`** — an equivalent FD set with no extraneous attribute on either side
  and no two FDs sharing a left side: the smallest set of rules to design from and to enforce.
  `A ∈ X` is extraneous in `X → Y` if `(X − A)⁺ ⊇ Y`.
- **Candidate-key derivation** — an attribute on no right-hand side is in *every* key. Start from that
  set, add attributes until the closure is `R`, then remove attributes while it stays `R`. Finding all
  keys can be exponential, which is why testing 3NF is NP-hard and testing BCNF is not.

## 3. Normalization

Normalization uses dependencies to remove **insertion, update, and deletion anomalies**. Every form is
judged against the dependencies **the business asserts** (§2), not against sample data.

| Form | Requirement | Removes |
|---|---|---|
| **1NF** | The table is a relation (§1.1): a key, one value of the declared type per column per row, and no column hiding a set of facts that must be keyed, referenced, constrained or queried element by element | CSV/piped lists, numbered slots, arrays/JSON of foreign ids, EAV value columns, polymorphic ids |
| **2NF** | No non-key column depends on a proper subset of a key | Redundancy from partial keys (historical; not a design target) |
| **3NF** | For every non-trivial `X → A`: `X` is a superkey **or** `A` is prime | Transitive dependencies (one fact repeated per row) |
| **BCNF** | For every non-trivial `X → Y`: `X` is a superkey | All FD-detectable redundancy; differs from 3NF only with overlapping composite candidate keys |
| **4NF** | For every non-trivial MVD `X ↠ Y` (`Y ⊄ X`, `X ∪ Y ≠ R`): `X` is a superkey | Independent multi-valued facts about one key in one table (person × skill × language) |
| **5NF** (PJ/NF) | Every non-trivial join dependency is implied by the keys | A cyclic three-way rule stored as one ternary (if S supplies P, P is used by J, and S supplies J, then S supplies P to J) |
| **6NF** | No non-trivial join dependency at all — in practice key + at most one other column | Redundancy among *independently varying* attributes; the natural form for history tables and optional facts |

*Atomicity* has no absolute meaning (a string has characters, a date has parts), so the 1NF test is
about hidden sets of facts, not indivisibility: a `jsonb` or array the database never needs to
constrain or join element-wise is not a 1NF defect. *ETNF* (Darwen, Date & Fagin, 2012) sits between
4NF and 5NF and is the weakest form that guarantees no redundant rows; *DKNF* (every constraint follows
from domains and keys) is a theoretical ideal, not an audit target.

Industry practice stops at **3NF/BCNF**; a rigorous legacy audit also looks at 4NF and 5NF. A good ER
model yields 4NF automatically — MVDs come from an M:M or a multivalued attribute squeezed into one
table — so a 4NF/5NF violation is a **modelling defect** (er-modeling §A2.7), not a subtlety.

### 3.1 Decomposition

- **Lossless join** — joining the parts gives back exactly the original; a lossy split *adds* spurious
  rows. Binary test: the shared columns `R1 ∩ R2` are a superkey of `R1` or of `R2`. **For DDL:** they
  become the PK/`UNIQUE` of the side they determine and an FK on the other side — those two constraints
  are what make the split safe.
- **Dependency preservation** — every FD can be checked inside one part. A lost FD turns a one-table key
  into a multi-table rule the engine can't declare.
- **BCNF decomposition** (while some part has `X → Y` with `X` not a superkey, split it into `X ∪ Y` and
  `R − Y`) is always lossless but **may lose a dependency**. **3NF synthesis** (one table per FD in
  `Fc`, plus a key table if none holds a key) is always lossless *and* dependency-preserving.
- **The trade-off.** BCNF, losslessness and dependency preservation can't always be had together.
  Classic case: `(student, dept) → advisor`, `advisor → dept` is 3NF, not BCNF, and the BCNF split loses
  `(student, dept) → advisor`. Either stop at 3NF and state the controlled redundancy, or take BCNF and
  enforce the lost FD explicitly (physical-design §5.3). Record which — it is a design decision.
- **Decomposition creates constraints.** Every split introduces inclusion dependencies (the FKs between
  the parts) and sometimes **equality dependencies** (`A{k} = B{k}`) that no FK expresses (§7.1).
- **Temporal FDs.** Once history is kept, `course_id → title` no longer holds over the table — only at
  each point in time (§9 *Historical entity*).

### 3.2 Missing information and three-valued logic

NULL is not a value. Any comparison with NULL is UNKNOWN; `AND`/`OR`/`NOT` extend to three values;
`WHERE` keeps only TRUE rows; arithmetic with NULL yields NULL; `DISTINCT`, `GROUP BY` and set operators
treat NULLs as equal while predicates don't. Familiar tautologies fail (`p OR NOT p` is not always true).
A nullable column turns the table's predicate into a disjunction ("… lives in *C*, OR we don't know
where, OR has no address"). Consequences the audit and the design rely on:

- **`CHECK` passes on UNKNOWN** — `CHECK (status IN ('A','B'))` and `CHECK (end_date > start_date)`
  admit NULL. A mandatory attribute needs `NOT NULL` as well.
- **`UNIQUE` admits NULLs** (§2.1), so it is not a key over a nullable column.
- **Composite FK, `MATCH SIMPLE`** (the SQL default) — if *any* FK column is NULL the row satisfies the
  constraint, so a half-filled composite reference is never checked.
- **`x NOT IN (subquery)`** returns no rows once the subquery yields a NULL; `= NULL` is never true.

**The rule this family adopts** (a practical form of Darwen's decomposition approach): every nullable
column has **exactly one documented meaning**, and the design where that meaning is structural is
preferred.

| NULL would mean… | Design instead (preferred) | A nullable column is acceptable if… |
|---|---|---|
| **Not applicable** — the fact can't exist for this kind of row | Subtype or optional-relationship table; in a single-table subtype, a `CHECK` keyed on the type column | never as an undeclared rule |
| **Not yet** — workflow state (unclosed, unapproved) | A state column + `CHECK ((state = 'closed') = (closed_at IS NOT NULL))` | the state rule is declared |
| **Unknown** — exists, not recorded | A nullable column, if this is its *only* meaning; a reason column or table if unknown and n/a must be told apart | it is the sole, documented meaning |
| **Unbounded** — "until further notice" | An unbounded range bound (`[2024-01-01,)`) or `'infinity'` | — use the range |

**Sentinels are never acceptable**: a sentinel is a NULL that also lies — it compares, sorts and sums
as a real value. Candidate-key columns are never nullable.

## 4. Relational algebra vs. relational calculus

**Relational algebra** is the operator language — selection `σ`, projection `π`, union `∪`,
difference `−`, product `×`, rename `ρ`, with join derived from them. **Relational calculus** is the
declarative counterpart (what you want, not how). SQL is declarative; the optimizer turns it into
algebra and searches **equivalent** expressions — reordered joins, pushed-down selections — so the
written join order does not bind it. What defeats it is what it cannot rewrite or see: functions and
implicit conversions on indexed columns, correlated subqueries it cannot decorrelate, scalar functions
that hide queries, and missing or stale statistics. That is why query shape and schema still matter.

### 4.1 Access paths (index mechanics)

- **An index lookup has three steps:** tree traversal (logarithmic and bounded), a walk along the leaf
  chain, then one table fetch per hit. Only the first is bounded; a "slow index" is a wide leaf walk
  plus many fetches, not a broken tree — rebuilds rarely fix it.
- **Access predicate** — a condition that sets the start and stop of the leaf walk. **Filter predicate**
  — evaluated row by row inside the walk (index filter) or after the fetch (table filter); it narrows
  nothing. A predicate is **sargable** when it can be an access predicate: the raw indexed column
  compared with `=`, a range, or a prefix `LIKE`.
- **Concatenated index:** only a leading prefix of the key columns can be access predicates — equality
  columns first, then at most **one** range column. "Most selective column first" is a myth.
- **Pipelined execution:** an index whose order matches `ORDER BY`/`GROUP BY` after the equality
  columns returns rows without a sort, so top-N stops early.
- **The optimizer uses only what is declared.** Statistics and constraints (`NOT NULL`, `UNIQUE`, FK,
  `CHECK`) feed it; rules that live in triggers or application code are invisible to it.

## 5. Transactions, isolation and concurrency

- **Atomicity** — all or nothing: on any fault the transaction aborts and its writes are discarded, so
  it can be retried. A failed statement, a trigger error, or a deadlock victim is rolled back. A retry
  is not idempotent if the commit succeeded but its acknowledgement was lost — see *idempotency key*
  (physical-design §5.3).
- **Consistency** — the **application's** invariants hold before and after each transaction. The
  database enforces only the invariants that are **declared** (keys, FKs, `CHECK`, exclusion /
  `WITHOUT OVERLAPS`); every other invariant is the programmer's job and is unprotected against
  concurrent writers unless isolation or locking covers it. An invariant that lives only in code is a
  finding (Codd rule 10), not something ACID gives us. Constraints should hold at every statement
  boundary; deferral is a documented exception (§7.2).
- **Isolation** — formally **serializability**: the outcome equals *some* serial order. Engines default
  to weaker levels that permit named anomalies (§5.2); "ACID-compliant" says nothing about which.
- **Durability** — committed data survives failure (WAL on one node; acknowledged replicas in a
  replicated system). Asynchronous replication can lose acknowledged writes on failover.

### 5.1 Serializability and locking

- A schedule is **conflict-serializable** when its precedence graph has no cycle. (View
  serializability is broader but NP-complete to test, so engines enforce conflict serializability.)
- **Two-phase locking** guarantees conflict serializability, not freedom from deadlock. Commercial
  engines use **strict / rigorous 2PL**: locks are held until the **transaction** ends, not the
  statement.
- **Deadlock** — a cycle in the wait-for graph; the engine rolls back a victim. Prevention in code you
  control: take locks in one global order, keep transactions short, retry victims.
- **MVCC / snapshot engines** (PostgreSQL, Oracle, SQL Server with RCSI or `SNAPSHOT`) let readers not
  block writers; only write–write conflicts wait.
- **Lock-scope inflation** — heavy trigger or procedure logic lengthens the transaction and widens its
  lock footprint: every lock is held longer, more tables are locked, and in an order the trigger
  chooses. The result is blocking, and deadlocks wherever another path locks the same tables in a
  different order. This is the **cost of enforcing isolation**, not a weakening of it; the trigger and
  procedure rubrics lean on it. Isolation is actually weakened by the anomalies below.

### 5.2 Isolation levels and anomalies

| Anomaly | What happens | Prevented by |
|---|---|---|
| **Dirty write** | Overwrites another transaction's uncommitted write | Every level |
| **Dirty read** | Reads an uncommitted write that may roll back | Read committed and above |
| **Read skew** (non-repeatable read) | Sees different parts of the database at different points in time | Snapshot isolation / repeatable read |
| **Lost update** | Two read-modify-write cycles; the second overwrites the first | One atomic `UPDATE … SET x = x + …`, an explicit row lock, or SI with automatic detection (PG `REPEATABLE READ`, SQL Server `SNAPSHOT`, Oracle; **not** MySQL InnoDB RR) |
| **Write skew** | Each transaction reads a premise and writes a different row; together they break an invariant (two withdrawals each keeping the combined balance ≥ 0; `MAX(n)+1` numbering) | Serializable — or a **declared constraint**, or locking the rows the premise read |
| **Phantom** | A concurrent insert/delete changes the result of a predicate read (often the premise of write skew: "no booking overlaps") | Serializable (predicate / index-range locks, SSI), a constraint, or materializing the conflict |

Declared PK, `UNIQUE`, FK and exclusion constraints are checked against the **current** state, not a
snapshot — which is why a declared constraint catches what a procedural check on a snapshot misses.

**Engine names are not portable.** PostgreSQL: `READ COMMITTED` (default), `REPEATABLE READ` =
snapshot isolation, `SERIALIZABLE` = SSI (true serializable; aborts with SQLSTATE 40001 and must be
retried), `READ UNCOMMITTED` behaves as read committed. SQL Server: `READ COMMITTED` (default;
lock-based unless `READ_COMMITTED_SNAPSHOT` is on), `SNAPSHOT` = SI, `NOLOCK`/`READ UNCOMMITTED` =
dirty reads. Oracle: `SERIALIZABLE` = snapshot isolation (write skew possible), no dirty reads. An audit
names the **anomaly**, not the vendor's level name.

## 6. Single Source of Truth — system of record vs derived data

Every fact has **one system of record**: the place it is first written and that is authoritative when
copies disagree. Everything else that holds the fact is **derived data** — indexes, materialized views,
generated columns, caches, search indexes, read replicas, the warehouse, a stored `total_*`. Derived
data is redundant by design and legitimate when all three hold:

1. **Named source** — the system of record it derives from is stated.
2. **One-way** — nothing writes the derived copy except the derivation (generated column, refresh, CDC
   consumer, trigger); no user path edits it.
3. **Rebuildable** — it can be dropped and recomputed from the source.

An **SSOT violation** is a copy that fails any of these: shadow/backup tables (`*_COPIA_20120605`,
`*_2`, `*_old`) derived from nothing, reference data edited in two places, a copy database that some
consumers write to. Those drift, and nobody can say which copy is right. SSOT is the formal anchor for
the **dead/copy-schema** finding and the shadow-table anti-pattern.

A value **captured at event time** — the unit price on an order line, the tax rate applied, the
address on a shipped invoice — is a fact of the event, not a copy of the current value, and is not an
SSOT or normal-form defect.

**"Consistency" has four meanings — name which one:** (1) ACID consistency, the application invariants
of §5; (2) replica / eventual consistency, how stale a copy may be; (3) CAP consistency =
linearizability, every read sees the latest write; (4) "consistent hashing", a partitioning scheme. For
derived data split it in two: **timeliness** (how stale a reader may see it — violations heal by
waiting) and **integrity** (no loss, no contradiction — violations are permanent and need repair).
Derived data may relax timeliness; it may never relax integrity.

## 7. Main criteria of a good database design

The positive rubric the object-type docs grade against.

### Data integrity
- **Entity integrity** — every table has a primary key, never null; every row is uniquely
  identifiable, and every candidate key is declared (§2.1).
- **Referential integrity** — every foreign key matches an existing **candidate key** (PK or `UNIQUE`)
  or is null where permitted. Under `MATCH SIMPLE` a partly-null composite FK is not checked at all
  (§3.2).
- **Domain integrity** — columns are typed to the concept (a type is its values *and* the operations
  that make sense on them: a date stored as `char(8)` is not a date), with `CHECK` and `NOT NULL` so
  only valid data can be stored. One concept, one declared type, everywhere it appears.

### Redundancy: none, or controlled
- Each fact stored once — BCNF for FD-based redundancy (3NF where a dependency would otherwise be lost,
  §3.1), 4NF/5NF for multi-valued and join dependencies. Changing a customer's address touches **one**
  row.
- Redundancy is **controlled** when it is declared, known to its users, and kept consistent by the DBMS
  (generated column, engine-refreshed materialized view, a constraint tying the copies). Redundancy kept
  in step by application code or by hand is **uncontrolled** — the defect.

### Performance & scalability
- **Smart indexing** of the columns on critical `WHERE` / `JOIN` / `ORDER BY` paths (§4.1); every index
  serves a named access path.
- **Right-sized data types** — the smallest correct type, to minimize I/O and memory footprint.

### Flexibility & maintainability
- The schema absorbs business-logic change without massive refactoring.
- **Consistent naming** for tables, columns, and constraints.

### Completeness
- Every catalogued requirement and business rule is represented — as structure, a declared constraint,
  or a named enforcement mechanism (§7.1).

### Security
- **Confidentiality** (only authorized readers), **integrity** (only authorized writers),
  **availability** (authorized users aren't denied) — the anchor for audit-lenses §6 and
  physical-design §11; principles in §11.

**Rank the criteria per system.** They conflict (integrity vs efficiency; flexibility vs usability). A
design states the ranking it took from the requirements, and every deliberate deviation names the
criterion it trades.

### 7.1 Constraints: kinds, the Golden Rule, and where each lives in SQL

A constraint is a truth-valued expression the database must satisfy. **The Golden Rule:** no statement
may leave the database violating a declared constraint; their conjunction is the database's *total
constraint*, the criterion for accepting any update. Every business rule lands in one row below; a rule
with no row and no mechanism is an integrity gap.

| Kind | Example | SQL / PG18 mechanism | Gap |
|---|---|---|---|
| **Type** (domain) | a national id is 7–8 digits + check digit | column type, `CREATE DOMAIN … CHECK` | SQL domains constrain a base type; they are not true types |
| **Tuple** (one row) | `end > start`; subtype columns per `kind` | `CHECK` — deterministic, same-row only | passes on UNKNOWN (§3.2) |
| **Single table, many rows** | keys; non-overlapping periods; "one open loan per copy" | `PRIMARY KEY`/`UNIQUE`, partial unique index, `EXCLUDE` / `WITHOUT OVERLAPS` | an FD not implied by a key → normalize, else trigger |
| **Inclusion dependency** | every order line's product exists | `FOREIGN KEY` to a candidate key | a target restricted to one subtype needs the `(id, kind)` superkey device |
| **Equality dependency** | every supertype row has a subtype row; a parent must have ≥ 1 child; a mandatory-both-ends 1:1 | none declarative — deferred constraint trigger + verification query | no `CREATE ASSERTION` in mainstream engines |
| **General multi-table / aggregate** | Σ debits = Σ credits; ≤ 180 credit points; salary ≤ manager's | deferred constraint trigger that locks the parent row, or `SERIALIZABLE`, plus a verification query | same; races without a lock (§5.2 write skew) |
| **Transition** | status never moves backwards; a posted entry is immutable | `BEFORE UPDATE` trigger comparing `OLD`/`NEW`, or revoke `UPDATE` | not declarable |

Constraints are checked at statement end; a rule no single statement can satisfy is checked at commit
with `DEFERRABLE INITIALLY DEFERRED` (§7.2). The enforcement tiers for design are physical-design §5.3.

### 7.2 Multiple assignment, and deferral as its SQL stand-in

Some correct changes are impossible one statement at a time: inserting both halves of a 1:1 cycle,
swapping two key values, entries that must balance. Relational theory solves this with **multiple
assignment** (several updates as one operation, constraints checked once at the end). SQL has none;
PostgreSQL approximates it with `DEFERRABLE INITIALLY DEFERRED` constraints or a single statement using
data-modifying CTEs; SQL Server has no deferral, so such rules need triggers inside one transaction.
Deferral widens the window in which a transaction sees an inconsistent state — use it only where a rule
cannot be met statement by statement.

### 7.3 View updating

- **The Assignment Principle** — after assigning `v` to `V`, `V = v` must hold. A row inserted through a
  filtered view that the view then doesn't show breaks it (`WITH CHECK OPTION` prevents it).
- **Compensatory action** — an extra update the system performs to keep a constraint (a cascade delete).
  Legitimate only when declared (`ON DELETE CASCADE`, a documented constraint trigger) and known to
  every writer; a procedural trigger doing it out of sight is not.
- **Interchangeability** — views and base tables should look and behave the same to their users, which
  is also how views deliver logical independence (Codd rule 9).

## 8. Theory → legacy failure → literature fix

| What you observe | Theoretical failure | Literature fix |
|---|---|---|
| Comma-separated IDs in one string column | 1NF — a hidden set of facts (§3) | Connolly & Begg; Karwin — intersection table |
| Updating one department name requires updating 50,000 rows | Update anomaly — partial/transitive dependency (2NF/3NF) | Decompose along the functional dependencies (§3.1) |
| Query slow because of `WHERE UPPER(email) = '…'` | Non-sargable predicate — the function hides the indexed column (§4.1) | Winand — rewrite the predicate, or an expression index |
| Triggers cascade silently into 5 other tables, causing lock timeouts | Lock-scope inflation under strict 2PL; lock-order deadlocks (§5.1) | Silberschatz; Elmasri & Navathe — short transactions, one lock order |
| One database is a full copy of another | SSOT violation (§6) | Eliminate the copy; single authoritative schema |
| `curso_1`, `curso_2`, `curso_3` columns on one table | Repeating group — a missing entity (1NF) | Barker — intersection entity (er-modeling CAP1 §A1.4, CAP2 §A2.1) |
| `tipo_ref` + `id_ref` pointing at different tables per row | Generic arc — referential integrity cannot be declared; metadata stored as data (§10) | Barker / Karwin — explicit arc, or the missing supertype (er-modeling §A3.2 step 5) |
| `attr_name` + `attr_value` rows instead of columns | EAV — metadata stored as data (§10); not a relation (§3) | Karwin — model the subtypes; `jsonb` for genuinely open attributes |
| `ventas_2022`, `ventas_2023` with identical columns | Data promoted to metadata (§10); keys and FKs undeclarable across the set | Karwin; Faroult — one table + declarative partitioning |
| `PRIMARY KEY (a, b)` but `a` alone is unique | Reducible key — the true key is unenforced (§2.1) | Date & Darwen — keys are irreducible; declare every candidate key |
| Room double-booked after a "BCNF" split | Lost functional dependency (§3.1) | Stay at 3NF, or enforce the lost FD (physical-design §5.3) |
| Old invoices reprinted with today's price | Event-time fact treated as derived (§6) | Store the price charged on the line (er-modeling §A1.4) |
| Nullable `hasta` meaning both "still open" and "not recorded" | Overloaded NULL — the predicate is a disjunction (§3.2) | Darwen — one meaning per NULL; an unbounded range |
| `NOT IN (SELECT col …)` silently returns nothing | Three-valued logic (§3.2) | `NOT EXISTS` |
| `WITH (NOLOCK)` in a stock-check procedure | Dirty read (§5.2) | Kleppmann — remove the hint; read-committed snapshot for non-blocking reads |
| `IF NOT EXISTS (SELECT …) INSERT` guarding uniqueness or a booking | Write skew / phantom (§5.2) | Declare `UNIQUE` / an exclusion constraint; else lock or `SERIALIZABLE` + retry |
| `SELECT @saldo = saldo …; UPDATE … SET saldo = @saldo - @x` | Lost update (§5.2) | One atomic `UPDATE … SET saldo = saldo - @x WHERE … AND saldo >= @x` |
| Department "must have employees" on the model; nothing enforces it | Equality dependency not expressible as an FK (§7.1) | Date — deferred constraint trigger + verification query |
| Insert through a filtered view "succeeds" but the row isn't in the view | Assignment Principle (§7.3) | `WITH CHECK OPTION` |
| `CHECK (posted = 0 OR dbo.fn(id) = 0)` while entries can still change | Integrity independence faked — the check runs only when this row changes (rule 10) | A deferred constraint trigger with a parent lock (physical-design §5.3) |
| Trigger copies every change into another database | Dual write; an undeclared derived copy (§6) | Kleppmann — same-transaction outbox / CDC; name the system of record |

## 9. Entity–relationship modelling (Barker / CASE\*METHOD)

The conceptual layer that sits *above* the relational model. The normal forms in §3 describe
relations; the ER model describes the business they were derived from. A defect visible in a table is
very often a modelling decision that was never made. The terms are defined once here; *how* to model
with them is [`er-modeling.md`](er-modeling.md) (CAP1–CAP4).

| Term | Meaning | Relational counterpart |
|---|---|---|
| **Entity** | A thing of significance with many, uniquely identifiable instances | Table |
| **Attribute** | A single-valued characteristic of an entity or relationship; mandatory (`*`) or optional (`o`) | Column (`NOT NULL` if mandatory) |
| **Relationship** | Barker binary association with lowercase role names at both ends, independent optionality and cardinality, and optional UID/non-transferability marks | Foreign key (M:M → intersection table) |
| **Unique identifier (UID)** | Attributes and/or relationships that identify an instance; must be non-null, unique, **invariant**, short | Primary key; alternates → `UNIQUE` |
| **Intersection (associative) entity** | Resolves an M:M; its relationships out are mandatory | Table with two FKs whose combination is a key (the PK, or `UNIQUE` beside a surrogate PK) |
| **Recursive relationship** | An entity related to itself; optional at both ends | Nullable self-referencing FK |
| **Subtype / supertype** | Mutually exclusive, exhaustive kinds of one entity (*OR*) | Single table + type column, separate tables, or supertype + subtype tables |
| **Role** | One thing playing several parts at once (*AND*) | One table + role relationships, never one table per role |
| **Arc** | Mutually exclusive relationships from one entity, all mandatory or all optional | Explicit FKs + exclusivity `CHECK` (or a generic FK + type column, which loses RI) |
| **Historical entity** | Tracks values over time; a time indicator is part of its UID | History table; in PG18 a range column with `WITHOUT OVERLAPS` |
| **Derived attribute** | Computable *forever* from data still in the model; excluded from the conceptual model | Computed in query; stored only as a deliberate physical choice |

Model-level normalization restates §3 on the diagram: **1NF** — the UID-to-attribute relationship is
1:1 (no repeating values); **2NF** — every attribute depends on the *whole* UID; **3NF** — no non-UID
attribute depends on another non-UID attribute. A normalized ER model maps to a normalized relational
design without further work.

Use Barker / Oracle CASE*METHOD notation consistently for every conceptual ER diagram: soft-cornered
singular uppercase entity boxes; `#` UID, `*` mandatory, and `o` optional attribute marks; binary
relationships with reciprocal lowercase role names; solid mandatory and dashed optional relationship
segments; one/many end markers; UID bars and non-transferability diamonds where applicable. Do not
mix symbols from another ER notation. The relational model is a separate view and uses table/key
notation instead. See [Redgate’s Barker notation guide](https://www.red-gate.com/blog/barkers-erd-notation/)
and the detailed rules in [`er-modeling.md`](er-modeling.md).

## 10. Data/metadata separation

Data values live in rows; the names of tables and columns are metadata and live in the catalog (Codd
rules 1 and 4). Two inverse failures break this:

| Failure | What happens | Anti-patterns |
|---|---|---|
| **Metadata stored as data** | A string value names a column or a table, so the engine can't type, constrain or reference what it names | EAV (`attr_name`), polymorphic association / generic arc (`ref_type` = a table name) |
| **Data promoted to metadata** | A data value becomes part of a table or column name, so new data needs new DDL | Per-period or per-tenant clones (`sales_2023`, `revenue2002`), numbered column families, a fluid value list frozen in `CHECK`/`ENUM` |

Either way the constraint the engine could have enforced moves into application code. Test: *does a new
business value require DDL, or does a string column name a schema object?*

## 11. Security principles

- **Code/data separation** — input is bound as a value, never parsed as SQL text; identifiers (table,
  column, sort direction) come from a fixed whitelist or are quoted by the engine. Violated by
  string-built dynamic SQL (injection), including values read back from the database and spliced into a
  later statement (second-order injection).
- **Store verifiers, not secrets** — a system that can read a credential back exposes it to anyone who
  reads the database, its backups or its logs. Store a per-row-salted, slow, one-way hash (argon2id,
  scrypt, bcrypt, PBKDF2) computed in the application.
- **Least privilege** — every role, login and piece of code runs with the smallest rights it needs; the
  owner of the objects is not the role the application connects as.
- **Identifiers are not authorization** — a sequential or time-ordered key in a URL is guessable;
  authorize every access.

## Reference literature

- **Codd, E. F. (1970).** *A Relational Model of Data for Large Shared Data Banks.* The founding
  paper — relations, attributes, data independence.
- **Codd, E. F. (1985).** *Is Your DBMS Really Relational?* / *Does Your DBMS Run By the Rules?*
  Computerworld. The source of the 0–12 rules in §1.
- **Armstrong, W. W. (1974).** *Dependency Structures of Data Base Relationships.* Proc. IFIP. The
  axioms of §2.
- **Silberschatz, A., Korth, H. F., & Sudarshan, S. (2020).** *Database System Concepts* (7th ed.).
  McGraw-Hill. Algorithmic FD theory (closure, canonical cover, dependency preservation, BCNF
  decomposition, 3NF synthesis), MVD/4NF and temporal FDs; E-R design and EER constraints; isolation
  levels, 2PL, deadlock, snapshot isolation and write skew.
- **Ramakrishnan, R., & Gehrke, J. (2003).** *Database Management Systems* (3rd ed.). McGraw-Hill.
  Schema refinement and normal forms; its solutions manual's ch. 19 is a source of FD/normal-form
  drills (its isolation-level answers are not reliable).
- **Date, C. J., & Darwen, H. (2006).** *Databases, Types, and the Relational Model: The Third
  Manifesto* (3rd ed.). Addison-Wesley. Relation vs relvar, predicates and the Closed World
  Assumption, keys as irreducible superkeys, the Golden Rule, multiple assignment, the proscriptions
  against duplicates, nulls and column order, and view updating.
- **Date, C. J., & Darwen, H. (2014).** *Database Explorations: Essays on The Third Manifesto and
  Related Topics* (rev. 2). Normalization as relvar decomposition (dependency preservation, induced
  inclusion/equality dependencies), the decomposition approach to missing information, view-updating
  principles, and SQL's three-valued-logic pitfalls.
- **Date, C. J., Darwen, H., & Lorentzos, N. (2003).** *Temporal Data and the Relational Model.*
  Morgan Kaufmann. Intervals, PACK/UNPACK and 6NF history — the background to physical-design §5.2.
- **Connolly, T. M., & Begg, C. E.** *Database Systems: A Practical Approach to Design,
  Implementation, and Management.* Pearson. Structured 3-phase design methodology: conceptual
  (ER models) → logical (normalization) → physical (indexing, clustering, storage).
- **Elmasri, R., & Navathe, S. B.** *Fundamentals of Database Systems.* The university standard;
  deep on query optimization, transaction processing (ACID), and relational calculus.
- **Maier, D. (1983).** *The Theory of Relational Databases.* Computer Science Press. The raw
  mathematical foundations — relational schemes, hypergraph acyclicity, data dependencies.
- **Barker, R. (1990).** *CASE\*Method: Entity Relationship Modelling.* Addison-Wesley / Oracle.
  The ER notation and method used in CAP1–CAP4 of `er-modeling.md` — soft boxes, must-be/may-be
  optionality, crow's feet, UID bars, subtypes, arcs — and the six-step mapping from ER model to
  tables.
- **Watt, A., & Eng, N. (2014).** *Database Design* (2nd ed.). BCcampus (CC BY 4.0). An open
  introductory text with a worked requirements→ERD case and business-rule chapters; the source of two
  CAP4 drills and the crow's-foot reading conventions. Not authoritative on FD theory.
- **Sharma, N., Perniu, L., Chong, R. F., et al. (2010).** *Database Fundamentals.* IBM. Domains and
  semantic constraints, lossless/dependency-preserving decomposition, minimal cover and 3NF
  synthesis, and a library case carried through all three phases.
- **Booth, J. D.** *Database Design Succinctly.* Syncfusion. Requirements gathering, external data
  standards (ISO 3166/4217/639, E.164), catalogue-stored column documentation, and a double-entry
  ledger model. Not reliable on normal forms beyond 3NF.
- **Kimball, R.** *The Data Warehouse Toolkit.* Dimensional modeling (star/snowflake schemas) for
  reporting/BI workloads — the correct paradigm when normalization (OLTP) is the wrong tool.
- **Winand, M. (2012).** *SQL Performance Explained.* How a B-tree lookup works and why indexes are
  "slow"; access vs filter predicates; concatenated-index column order; function, partial and NULL
  indexing; bind parameters; join algorithms; clustering factor and index-only scans; pipelined
  `ORDER BY`, top-N and seek pagination; the write cost of indexes. Compares Oracle, SQL Server,
  PostgreSQL and MySQL.
- **Faroult, S., with Robson, P. (2006).** *The Art of SQL.* O'Reilly. Set processing over row-by-row
  work; the cost and limits of indexing; query shapes (`EXISTS`/`IN`/`NOT IN`, `DISTINCT` as a smell,
  views hiding cost); partitioning trade-offs; transaction scope; dynamic search criteria; workload
  monitoring.
- **Karwin, B. (2010).** *SQL Antipatterns.* Pragmatic Bookshelf. 24 logical-design, physical-design,
  query and application antipatterns with recognition cues and remedies — the source of the EAV,
  polymorphic-association, metadata-tribble, value-list, tree-encoding and password entries.
- **Kleppmann, M. (2017).** *Designing Data-Intensive Applications.* O'Reilly. Isolation anomalies and
  vendor naming; ACID consistency as an application property; schema evolution with backward and
  forward compatibility; systems of record vs derived data; CDC vs dual writes; idempotency.
- **Petrov, A. (2019).** *Database Internals.* O'Reilly. Heap vs index-organized tables, B-tree splits
  and right-edge appends, read/write/space amplification, MVCC and isolation, two-phase commit.
- **Obe, R., & Hsu, L. (2014).** *PostgreSQL: Up and Running* (2nd ed.). O'Reilly. Roles, schemas
  and `search_path`, privileges and default privileges, extensions, range/JSONB types, exclusion
  constraints, index methods, function volatility and `SECURITY DEFINER`, trigger semantics. Its
  version facts are 9.4-era.
- **Fontaine, D. (2017).** *Mastering PostgreSQL in Application Development.* PostgreSQL as a
  concurrent data-access service: set-based SQL over application loops, protocol-level parameters
  against injection, constraints as the keeper of business-rule consistency.
- **Shahabi, C. (2010).** *Introduction to object-relational database development.* InfoLab.
