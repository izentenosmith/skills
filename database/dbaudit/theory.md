# Theory Foundations

> The conceptual backbone of the audit rubric and of the proposals built on it. Every theoretical term
> a finding, a verdict or a design decision cites is defined **here once** and only referenced
> elsewhere. Read this first. §9 adds the entity–relationship vocabulary used by
> [`er-modeling.md`](er-modeling.md) (CAP1–CAP4).

## 1. The relational model (Codd, 1970)

Modern relational databases descend from E. F. Codd's *A Relational Model of Data for Large Shared
Data Banks* (1970). Codd treats data as mathematical **relations** (tables) over **attributes**
(columns), enforcing **data independence** — decoupling *how data is queried* from *how it is
physically stored*. When we grade a schema, we are ultimately asking how faithfully it honours that
model: are facts represented as well-formed relations, or has physical/ad-hoc structure leaked into
the logical design?

## 2. Functional dependencies (FDs)

A **functional dependency** `X → Y` holds in a relation `R` when every value of `X` is associated
with exactly one value of `Y`. FDs are the tool for discovering the *true* keys of the data: if a
non-key column determines another column, you have found organizational redundancy that threatens
integrity.

### Armstrong's axioms

The inference rules that let you derive every FD in a schema:

- **Reflexivity** — if `Y ⊆ X` then `X → Y`.
- **Augmentation** — if `X → Y` then `XZ → YZ`.
- **Transitivity** — if `X → Y` and `Y → Z` then `X → Z`.

Transitivity is the one that exposes 3NF violations: a transitive dependency `key → A → B` means `B`
is stored against the wrong key and will exhibit update anomalies.

## 3. Normalization

Normalization uses FDs to systematically remove **insertion, update, and deletion anomalies**.

| Form | Requirement | Removes |
|---|---|---|
| **1NF** | Attributes are atomic; no repeating groups, no multivalued cells | CSV/piped/JSON-in-a-column |
| **2NF** | 1NF + no partial dependency on part of a composite key | Redundancy from partial keys |
| **3NF** | 2NF + no transitive dependency on the key | Update anomalies (e.g. changing one logical fact in many rows) |
| **BCNF** | For every non-trivial FD `X → Y`, `X` is a superkey | Anomalies from overlapping candidate keys |
| **4NF** | BCNF + no non-trivial multivalued dependency (MVD) `X ↠ Y` | Independent many-to-many relationships crammed into one relation |

Industry practice usually stops at **3NF**, but a rigorous legacy audit needs BCNF (overlapping
candidate keys) and 4NF (MVDs — e.g. one person with multiple skills *and* multiple languages mixed
into a single table).

## 4. Relational algebra vs. relational calculus

**Relational algebra** is the *procedural* query language: selection `σ`, projection `π`, join `⋈`,
union `∪`. **Relational calculus** is the *declarative* counterpart (what you want, not how). SQL is
declarative; the engine compiles it into a physical execution plan expressed in algebra operators and
then optimizes that plan. This is *why* schema and query shape matter: a query written as a chain of
poorly-constrained joins gives the optimizer a bad algebra tree, and CPU/IO suffer regardless of how
"correct" the SQL reads.

## 5. ACID (and why Isolation dominates the trigger/procedure docs)

- **Atomicity** — all-or-nothing transactions.
- **Consistency** — transactions move the DB between valid states.
- **Isolation** — concurrent transactions don't corrupt each other's view.
- **Durability** — committed data survives failure.

**Isolation** is the property most often impaired by legacy code: triggers run *inside* the invoking
statement's transaction, so heavy trigger logic inflates lock duration and causes blocking/deadlocks
under concurrency. The trigger and procedure rubrics lean on this.

## 6. Single Source of Truth (SSOT)

Every fact should live in **exactly one place**. Copy databases, "shadow" / ad-hoc backup tables
(`*_COPIA_20120605`, `*_2`, `*_old`), and duplicated reference data all violate SSOT: they drift out
of sync, and consumers can no longer tell which copy is authoritative. SSOT is the formal anchor for
the **dead/copy-schema** finding (a whole database duplicating another) and for the shadow-table
anti-pattern in the table rubric.

## 7. Main criteria of a good database design

The positive rubric the object-type docs grade against:

### Data integrity
- **Entity integrity** — every table has a primary key, and it is never null; every row is uniquely
  identifiable.
- **Referential integrity** — every foreign key points to an existing primary key (or is null where
  permitted); no orphan rows.
- **Domain integrity** — columns enforce correct data types, lengths, and constraints
  (`CHECK`, `NOT NULL`) so only valid data can be stored.

### Controlled redundancy
- Each fact stored once (≈3NF). Changing a customer's address should touch **one** row, not many.

### Performance & scalability
- **Smart indexing** of the columns on critical `WHERE` / `JOIN` / `ORDER BY` paths.
- **Right-sized data types** — the smallest type that fits, to minimize I/O and memory footprint.

### Flexibility & maintainability
- The schema absorbs business-logic change without massive refactoring.
- **Consistent naming** for tables, columns, and constraints.

## 8. Theory → legacy failure → literature fix

| What you observe | Theoretical failure | Literature fix |
|---|---|---|
| Comma-separated IDs in one string column | 1NF violation — attributes must be atomic | Connolly & Begg — logical-design phase: normalize out repeating groups |
| Updating one department name requires updating 50,000 rows | Update anomaly — partial/transitive dependency (2NF/3NF) | Decompose into distinct relations along its functional dependencies |
| Query slow because of `WHERE UPPER(email) = '…'` | Index suppression — the function invalidates B-tree order | Winand — use a functional/expression (computed-column) index |
| Triggers cascade silently into 5 other tables, causing lock timeouts | Isolation (ACID) impairment under concurrency | Elmasri & Navathe — concurrency control & transaction scheduling |
| One database is a full copy of another | SSOT violation | Eliminate the copy; single authoritative schema |
| `curso_1`, `curso_2`, `curso_3` columns on one table | Repeating group — a missing entity (1NF) | Barker — resolve into an intersection entity (er-modeling CAP1 §A1.4, CAP2 §A2.1) |
| `tipo_ref` + `id_ref` pointing at different tables per row | Generic arc — referential integrity cannot be declared | Barker — explicit arc; in PG18 explicit FKs + `CHECK (num_nonnulls(…) = 1)` (er-modeling CAP3 §A3.2 step 5) |

## 9. Entity–relationship modelling (Barker / CASE\*METHOD)

The conceptual layer that sits *above* the relational model. The normal forms in §3 describe
relations; the ER model describes the business they were derived from. A defect visible in a table is
very often a modelling decision that was never made. The terms are defined once here; *how* to model
with them is [`er-modeling.md`](er-modeling.md) (CAP1–CAP4).

| Term | Meaning | Relational counterpart |
|---|---|---|
| **Entity** | A thing of significance with many, uniquely identifiable instances | Table |
| **Attribute** | A single-valued characteristic of an entity or relationship; mandatory (`*`) or optional (`o`) | Column (`NOT NULL` if mandatory) |
| **Relationship** | A named, two-way association with an **optionality** (*must be* / *may be*) and a **degree** (1:1, 1:M, M:M) at each end | Foreign key (M:M → intersection table) |
| **Unique identifier (UID)** | Attributes and/or relationships that identify an instance; must be non-null, unique, **invariant**, short | Primary key; alternates → `UNIQUE` |
| **Intersection (associative) entity** | Resolves an M:M; its relationships out are mandatory | Table whose PK contains two FKs |
| **Recursive relationship** | An entity related to itself; optional at both ends | Nullable self-referencing FK |
| **Subtype / supertype** | Mutually exclusive, exhaustive kinds of one entity (*OR*) | Single table + type column, separate tables, or supertype + subtype tables |
| **Role** | One thing playing several parts at once (*AND*) | One table + role relationships, never one table per role |
| **Arc** | Mutually exclusive relationships from one entity, all mandatory or all optional | Explicit FKs + exclusivity `CHECK` (or a generic FK + type column, which loses RI) |
| **Historical entity** | Tracks values over time; a time indicator is part of its UID | History table; in PG18 a range column with `WITHOUT OVERLAPS` |
| **Derived attribute** | Computable from other data; excluded from the conceptual model | Computed in query; stored only as a deliberate physical choice |

Model-level normalization restates §3 on the diagram: **1NF** — the UID-to-attribute relationship is
1:1 (no repeating values); **2NF** — every attribute depends on the *whole* UID; **3NF** — no non-UID
attribute depends on another non-UID attribute. A normalized ER model maps to a normalized relational
design without further work.

## Reference literature

- **Codd, E. F. (1970).** *A Relational Model of Data for Large Shared Data Banks.* The founding
  paper — relations, attributes, data independence.
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
- **Kimball, R.** *The Data Warehouse Toolkit.* Dimensional modeling (star/snowflake schemas) for
  reporting/BI workloads — the correct paradigm when normalization (OLTP) is the wrong tool.
- **Winand, M.** *SQL Performance Explained.* The practical mechanics of B-tree indexes, page sizes,
  and why specific query patterns bypass index structures.
- **Shahabi, C. (2010).** *Introduction to object-relational database development.* InfoLab.
