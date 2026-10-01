# ER Modelling — Pure Modelling Standard (CAP1–CAP4)

> Engine-agnostic. How to find the entities, relationships, attributes and identifiers; how to model
> recursion, roles, subtypes, exclusive relationships and history; how to map an ER model to
> relations; and the drills that check a model before it is signed off. Notation is the Barker /
> Oracle CASE\*METHOD entity–relationship convention. The vocabulary is defined once in
> [`theory.md`](theory.md) §9; this document is how to *use* it.
>
> Read it **forwards** to design (requirements → model → tables) and **backwards** to audit
> (tables → recovered model → what the legacy got wrong, §A0). Engine-specific choices — types,
> indexes, collation — are not here; they belong to the physical design, made only after the model
> stands.

## A. Model in three phases (Connolly & Begg; CASE\*METHOD)

Never jump straight to `CREATE TABLE`. Move through three deliberate layers:

| Phase | Question it answers | Produces | Covered by |
|---|---|---|---|
| **Conceptual** (CASE\*METHOD *Strategy* + *Analysis*) | What are the real things, how do they relate, what do we need to know about them? | ER diagram; one-sentence entity descriptions; relationship sentences | [CAP1](#cap1--conceptual-data-modelling-basics), [CAP2](#cap2--advanced-data-modelling) |
| **Logical / database design** (CASE\*METHOD *Design*) | Which relations, keys and references realize that model? Still engine-agnostic. | Table Instance Diagrams (TIDs) | [CAP3](#cap3--database-design-mapping-the-er-model-to-relations) |
| **Physical** | How does the target engine store, constrain and index it? | DDL | the physical design (not in this document) |

[CAP4](#cap4--modelling-drills) is the gate between phases: run its drills against the model before
moving on.

A legacy estate that grew table-by-table without the first two phases is exactly what produces shadow
tables, magic values, repeating-group columns and missing keys. The rebuild reintroduces the
discipline — and for a **rework/rebuild** object, the conceptual model is *reverse-engineered* from
the legacy DDL first (see [§A0](#a0-reverse-engineering-a-legacy-schema-into-a-model)), then corrected
with the rules below, then re-mapped.

---

## A0. Reverse-engineering a legacy schema into a model

This document is written forwards (requirements → model → tables). On a legacy estate it is also run
**backwards**, to recover what the tables were trying to say:

1. **Tables → candidate entities.** One table per entity is the hypothesis; shadow/copy tables
   collapse into their authoritative sibling; a table with only two FKs and a few attributes is a
   candidate *intersection* entity (a resolved M:M).
2. **FKs (declared or by convention) → relationships.** Write the relationship sentence for each
   (CAP1 §A1.3). A relationship you cannot phrase is a modelling smell, not a documentation gap.
3. **Columns → attributes.** Run the single-value test (A1.4) and the normalization checks (A2.1).
   Numbered column families (`x_1`, `x_2`, `x_3`) are repeating groups — a missing entity.
4. **PKs → UIDs.** Grade every PK against the UID criteria (A1.5). A business-code PK that can change
   is a UID that fails the *invariant* criterion.
5. **`tipo_*` columns, sparse nullable column blocks, `id_x` + `tipo_x` pairs → hidden subtypes and
   arcs** (A2.4, A2.5) that were mapped badly or not at all.

The recovered model is the input to the target design; the legacy mapping is evidence, not the
standard.

## CAP1 — Conceptual data modelling basics

**Goal:** an entity–relationship model that represents the business's information requirements —
nothing more, nothing physical.

### A1.1 Why the ER model comes first

- It states requirements in a precise, compact syntax that users can read and validate.
- It defines **scope**: what the system knows about, and what it doesn't.
- It is cheap to change *now*. A requirement discovered during build or after go-live costs orders of
  magnitude more than one discovered on the diagram — establish requirements completely here.
- It is **independent of hardware and software**: the same model can map to a relational,
  hierarchical, network or file-based implementation. Nothing engine-specific belongs in it.
- It is the integration contract between applications that share the data.

Three components: **entities** (the things of significance), **relationships** (how they relate),
**attributes** (what we need to know about them).

### A1.2 Entities

An **entity** is a person, place, thing or concept of interest to the users, about which the system
must hold, know and show information.

Tests for a candidate entity:

- It is a **noun**, and it is **in scope**.
- It exists in its own right (not merely a property of something else).
- It has **many instances** — a "thing" with exactly one instance is usually a parameter, not an
  entity.
- Its instances can be **uniquely identified**. If they can't, it may not be an entity.
- It can be tangible (building, employee), intangible (department, account) or semi-tangible (order,
  invoice).

**Notation:** a soft-cornered box of any size; name **singular**, **unique**, in **UPPERCASE**;
an optional synonym in parentheses when two user groups name the same thing differently.

**Extracting entities from interview notes:**

1. Mark every noun — nouns tend to be entities.
2. Discard what is out of scope.
3. Keep only what the business needs information *about*.
4. Write a one-sentence description with examples: *"An EMPLOYEE is a paid worker of the company —
   for example, Juan Pérez and María Muñoz are EMPLOYEEs."*
5. Diagram it.

Don't disqualify a candidate too early; a noun that looks like an attribute often turns out to be an
entity once its own attributes appear.

### A1.3 Relationships

A **relationship** (association) is a named, significant way in which two entities (or an entity and
itself) are related, which the system must hold and show.

**Reading template** — every relationship is read in *both* directions:

> Each **ENTITY-1** { **must be** | **may be** } *relationship name* { **one and only one** | **one or
> more** } **ENTITY-2**.

*"Each CHEQUE **must be** for **one and only one** EMPLOYEE. Each EMPLOYEE **may be** the recipient of
**one or more** CHEQUEs."*

**Notation:** a line between the boxes; relationship names in lowercase at each end; **solid** half =
*must be* (mandatory), **dashed** half = *may be* (optional); **crow's foot** = *one or more*, plain end
= *one and only one*.

| Degree | Frequency | Heuristic |
|---|---|---|
| **1:1** | Rare | Mandatory at both ends is very rare — two entities in a 1:1 are often **the same entity**. Challenge every 1:1. |
| **1:M** | Very common | Mandatory at both ends is rare. |
| **M:M** | Very common in analysis | Usually optional at both ends (sometimes at one). **Not implementable as-is** — see below. |

**Resolving M:M.** Replace the M:M with an **associative (intersection) entity** and two M:1
relationships. The relationships *from* the intersection entity are always **mandatory** (an
enrolment cannot exist without its student and its course). Attributes that belong to the pairing —
quantity, date, grade — live on the intersection entity.

**Naming.** Use a pair of meaningful names (*based on / basis for*, *bought from / supplier of*,
*operated by / operator of*, *responsible for / the responsibility of*). **Never** *related to* or
*associated with* — a name that says nothing means the relationship isn't understood yet.

**Diagram layout.** Straight horizontal or vertical lines; generous whitespace; avoid bundles of
close parallel lines; stretch boxes to help the layout; crow's feet pointing **up or left**; the most
volatile entities toward the **top**, the least volatile toward the **bottom-right**.

### A1.4 Attributes

An **attribute** is a characteristic of an entity *or of a relationship* that the system must hold.
Attributes **identify** (employee number), **qualify** (name), **quantify** (age) or express **state**
(employment status: active, on leave, terminated).

- Names are **singular, lowercase, specific** (*quantity on hand* vs *quantity ordered*, not
  *quantity*), and **do not repeat the entity name** — the entity already qualifies it (`code` on
  COURSE, not `course_code`).
- An attribute belongs to **exactly one** entity.
- **Decompose to the lowest meaningful component** the business actually uses: a person's name into
  first and last name; an item number into type + supplier + sequence if those parts carry meaning.
  Dates, times and national IDs are normally left whole; an address may stay aggregate until design.
- **Single-value test.** Each attribute has **one value per instance**. A multi-valued attribute or
  repeating group is not an attribute — it signals a **missing entity** (a CUSTOMER with many contact
  dates needs a CONTACT entity).

**Derived attributes** — values computable from other data (number of salespeople per region, monthly
totals, an average, a 10 % commission) — are **redundant**. Leave them **out** of the conceptual
model. Whether to *store* one is a **physical** decision driven by volume and access urgency, made in
the physical design (generated column, materialized view) and kept consistent by mechanism, never
by hand.

**Optionality.** Mark each attribute **`*` mandatory** (a value must be known for every instance) or
**`o` optional**. Validate the marks with an **entity instance diagram** — a few rows of real sample
data under the attribute names; a mandatory attribute with blanks in the sample is mis-marked.

### A1.5 Unique identifiers (UID)

A **UID** is any combination of attributes and/or relationships that uniquely identifies each instance.
Every instance must be identifiable. Notation: `#` before each UID attribute; a **bar** across a
relationship line marks that relationship as part of the UID.

**Criteria for a good UID** — the same criteria that justify surrogate keys in physical design:

| Criterion | Failure it prevents |
|---|---|
| Never null | Unidentifiable rows |
| No duplicates | Ambiguous references |
| **Invariant over time — carries no information** | Identity breaking when the business value changes |
| Short | Wide, slow foreign keys |
| Preferably numeric | Collation/padding/comparison surprises |
| Familiar to users (for the natural candidate) | Users unable to find their own records |

**Intelligent (smart) keys** fail the *carries no information* criterion outright. A part number
`47-22-C` that means *row 47, drawer 22, bin C*, or an employee number `A-01-01` that encodes the
branch that hired them, couples identity to a fact that changes — the part moves bins, the employee
transfers. Split the encoded facts out into attributes or relationships (BIN, BRANCH), give the entity
a meaningless identifier, and keep the old code only as an alternate or lookup attribute if users still
search by it.

When several UIDs qualify they are **candidate identifiers**; the one chosen is primary, the rest are
**alternate** (→ `UNIQUE` constraints in design).

| UID type | When | Example |
|---|---|---|
| **Single attribute** | A natural, stable identifier exists | DEPARTMENT `# number` |
| **Attribute combination** | No single one; typical for **historical** entities, combined with a time attribute | THEATRE TICKET `# performance date` + `# seat number` |
| **Relationship combination** | Intersection entities from a resolved M:M | ASSIGNMENT = EMPLOYEE + PROJECT (+ `# assignment date` if repeats are allowed) |
| **Attribute + relationship** (dependent entity) | The entity cannot exist without its parent, belongs to exactly one parent, and can never move to another | DEPARTMENT `# number` within a BUILDING |
| **System-generated** | No natural attribute identifies the instance reliably | CUSTOMER `# customer code` (two customers can share a name) |

A relationship that participates in a UID must be **mandatory** and **one-and-only-one** in the
direction that participates.

## CAP2 — Advanced data modelling

**Goal:** validate where attributes are placed, and model the constructs plain entities and
relationships can't express: recursion, roles, subtypes, exclusive relationships, history.

### A2.1 Normalization, applied to the ER model

Normalization (Codd, 1972, refined since) is a technique to **develop and evaluate** models, not only
tables. A **normalized ER model translates directly into a normalized relational design** — so
normalize on the diagram, before any DDL exists. The formal definitions (functional dependencies,
BCNF, 4NF) are in [`theory.md` §2–§3](theory.md); the model-level checks are:

| Rule | Model-level statement | Validation check | Fix |
|---|---|---|---|
| **1NF** | Between the UID and each attribute the relationship is 1:1 in that direction | Each attribute has one value per instance; no repeating values | Move the multi-valued attribute to a **new entity** with an M:1 back to the original |
| **2NF** | Every attribute depends on the **whole** UID | Each UID value determines exactly one value of each attribute; no attribute depends on only *part* of a composite UID | The misplaced attribute moves to the entity it really depends on (bank address belongs to BANK, not to ACCOUNT whose UID is bank + account number) |
| **3NF** | No non-UID attribute depends on another non-UID attribute | Look for attribute pairs that determine each other | Move **both** the dependent attribute and its determinant to a **new entity**, related back by M:1 |

**3NF is the working target** for eliminating redundancy in design. The audit still looks at BCNF and
4NF (overlapping candidate keys, independent multi-valued facts — see theory §3), because legacy
schemas break those too.

### A2.2 Hierarchies and recursive relationships

- A fixed-level hierarchy can be modelled as a **chain of M:1 relationships** (DIVISION → DEPARTMENT
  → SECTION). It is explicit but rigid: adding a level means changing the model.
- A **recursive relationship** relates an entity to itself (the "pig's ear"): *"Each EMPLOYEE may be
  managed by one and only one EMPLOYEE; each EMPLOYEE may be the manager of one or more EMPLOYEEs."*
  It absorbs new levels and re-parenting without model changes.
  - The single recursive entity must carry **all attributes of every level** — the pattern fits best
    when every level has the same attributes.
  - A recursive relationship must be **optional at both ends.** If every element *had* to be inside
    another, the hierarchy would be infinite.
- **Bill of materials** (parts, sub-assemblies, assemblies, products) collapses into one COMPONENT
  entity with a **recursive M:M** (*each COMPONENT may be part of one or more COMPONENTs / may be
  composed of one or more COMPONENTs*). Resolve it like any M:M: an intersection entity (ASSEMBLY
  RULE) with **two M:1 relationships back to COMPONENT** — one for the parent, one for the child —
  carrying the attribute that belongs to the pairing (**quantity**).

### A2.3 Roles

When one real-world thing plays several roles (an INSTRUCTOR who is also a PARTICIPANT), separate
entities per role duplicate the person and drift apart. Model the **thing once** (PERSON) and the
**roles as relationships or role entities**. Role entities may share overlapping instances — that is
the point: roles are an *AND*, not an *OR*.

### A2.4 Subtypes and supertypes

Use subtypes for **mutually exclusive kinds** of an entity (*OR*) that share common attributes and
relationships. *"A company has contract and fee-based employees. For all, record id, name and
department; for contract employees, base salary; for fee-based, hourly rate, overtime rate and union."*
→ supertype EMPLOYEE with subtypes CONTRACT EMPLOYEE and FEE EMPLOYEE.

- Subtypes **inherit** every attribute and relationship of the supertype and may add their own.
- Every supertype instance belongs to **exactly one** subtype: the set is **complete and
  non-overlapping**.
- A subtype with no attributes or relationships of its own is probably a **synonym**, not a subtype.
- If an instance could be **both** subtypes, the construct is wrong — that is a role (A2.3).
- When unsure the set is complete, add an **OTHER** subtype.
- Reading: *"Each EMPLOYEE must be either a CONTRACT EMPLOYEE or a FEE EMPLOYEE"*; *"…FEE EMPLOYEE,
  which is a type of EMPLOYEE…"*.

### A2.5 Exclusive relationships (arcs)

Two or more relationships from the same entity that are **mutually exclusive** are drawn with an
**arc** across them (a dot on each relationship that belongs to it): *"Each BANK ACCOUNT must be held
by either one and only one INDIVIDUAL or one and only one COMPANY."*

- Relationships in an arc often share a name.
- They must be **all mandatory or all optional**.
- An arc belongs to **one entity** and includes only relationships **originating** from it.
- An entity may have several arcs, but a relationship belongs to **at most one** arc.

### A2.6 Historical data

A model drawn in the present tense answers *"who drives this taxi now?"* and nothing about yesterday.
Before adding the time dimension, **ask the user** — history is expensive to store and to query:

- Is an audit trail required?
- Can attribute values change over time, and does anyone need the old values?
- Must historical data be queried, and must prior versions be kept?

Patterns:

- **Historical attribute** → a new entity whose **UID includes a time indicator** (date, date+time,
  period number or sequence). CONTRACT with a current status becomes CONTRACT + STATUS, UID = the
  CONTRACT + `# effective date`. One history entity can track several attributes of the same parent.
- **Historical relationship** → a new entity holding the relationship over time (APARTMENT —
  current tenant becomes APARTMENT + LEASE HISTORY).
- **M:M over time** → the intersection entity carries the period, with the **start date in its UID**
  so the same pair can recur (EMPLOYMENT between MEMBER and COMPANY, `# from date`, `to date`).
- Decide explicitly whether **gaps** (periods with no value) and **overlaps** are allowed, and whether
  **future-dated** values (a rent already agreed for next year) are recorded. Non-overlap is enforceable
  by a temporal key (PostgreSQL 18: `WITHOUT OVERLAPS`); *no gaps* and *always has a value* need more
  than a key constraint.
- Agree the **retention window** ("the last two years") — history kept forever by default is a cost
  nobody chose.
- If the user says **current state only**, model the present tense and stop; don't add history the
  requirement didn't ask for.

### A2.7 Complex relationships — rings of M:M

Be wary of a **ring of M:M relationships** (PERSON–JOB–COMPANY, EMPLOYEE–PROJECT–TASK). Resolve each
M:M and then ask *which intersection entity the attribute actually belongs to* (do the job dates
belong to person–job, job–company, or the triple?). Often one **ternary intersection entity**
replaces several binaries, and business rules are enforced by making an intersection reference
**other intersections** instead of base entities — e.g. an employee's task assignment references
*(employee, task) ∈ SKILL* and *(project, task) ∈ PROJECT TASK*, so nobody is assigned a task they
can't do or that the project doesn't contain. Then remove intersections the result makes redundant.

## CAP3 — Database design: mapping the ER model to relations

**Goal:** transform the ER model into a relational design, documented with Table Instance Diagrams.
Still engine-agnostic; types and physical options come in the physical design.

### A3.1 The Table Instance Diagram (TID)

Document every table as a TID — the design-phase counterpart of the entity instance diagram:

| Row | Content |
|---|---|
| Table name | Traceable to the entity name |
| Column name | One per column |
| Key type | `PK`; `FK` — suffixed `FK1`, `FK2` when a table has several; columns of one composite FK share a suffix |
| Nulls / Unique | `NN` = NOT NULL; `U` = unique alone; `U1`, `U2` = unique in combination (same suffix) |
| Sample data | 3–5 realistic rows |

Labelling rules: a single-column PK is `NN, U`; a composite PK is `NN, U1` on each of its columns.
Sample data comes from interview notes, entity instance diagrams, current systems, analysis documents
and follow-up conversations with users. A TID with sample rows catches mis-marked optionality and
broken uniqueness that a column list hides.

### A3.2 The six mapping steps

1. **Entities → tables.** Each *simple* entity (not a subtype/supertype) becomes a table. The name
   traces to the entity; pick one pluralization rule and apply it everywhere.
2. **Attributes → columns.** Each attribute becomes a column of its entity's table; mandatory
   attributes become **`NN`**. Column names are short but meaningful, traceable to the model, avoid SQL
   reserved words (`number`, `date`, `user`), and use **one abbreviation per concept** (is it `num`,
   `no` or `nmro`? pick one).
3. **UIDs → primary keys.** UID attributes become PK columns (`PK`, `NN, U` — or `NN, U1` for a
   composite). If the UID includes a **relationship**, the parent's PK columns are added as FK columns
   **that are part of the PK** (`PK, FK1`).
4. **Relationships → foreign keys.**

   | Relationship | Where the FK goes | Constraints |
   |---|---|---|
   | **M:1** | Take the PK at the *one* end, put it in the table at the *many* end | `NN` if the relationship is *must be* |
   | M:1 already in the PK (step 3) | Nothing to add | — |
   | **1:1 mandatory at one end** | In the table at the **mandatory** end | `NN` **and `U`** — the unique constraint is what makes it 1:1 |
   | **1:1 optional at both ends** | Either table | `U` (nullable) |
   | **Recursive 1:M** | Self-referencing FK in the same table, named for the role (`manager_id`) | **Never `NN`** (A2.2) |
   | **Recursive 1:1** | Self-referencing FK | `U`, never `NN` |

5. **Arcs → alternative foreign keys.** Two designs:

   | | **Explicit arc** (one FK column per relationship) | **Generic arc** (one FK column + a type column) |
   |---|---|---|
   | Referential integrity | Every FK declarable | **Cannot be declared** — the column points at different tables row by row |
   | Exclusivity | Must be enforced — CAP3 leaves it to the application; in PG18 a `CHECK (num_nonnulls(a_id, b_id, c_id) = 1)` (or `<= 1` when optional) enforces it in the DB | Implicit (one column) |
   | Key formats | May differ per target | Must share one format |

   **Target standard: explicit arc + `CHECK`.** A generic arc is a polymorphic association — the
   database can no longer guarantee the referenced row exists.
6. **Subtypes → tables.**

   | | **Single table** | **Separate tables** (one per subtype) | **Supertype + subtype tables** (shared PK, 1:1) |
   |---|---|---|---|
   | Shape | One table, a `type` column, supertype + all subtype columns, all FKs | Each subtype table repeats supertype columns + FKs | Supertype table holds common columns; each subtype table's PK is also an FK to it |
   | Supertype access | Direct | `UNION ALL` view — read-only | Direct |
   | Subtype `NN` | CAP3: not enforceable in the DB; **PG18: enforceable** with `CHECK (type <> 'C' OR salary IS NOT NULL)` per subtype | Enforced | Enforced |
   | UID across subtypes | Natural | **Hard** — nothing stops the same id in two subtype tables | Natural (one PK space) |
   | Application | Must branch on `type` | Must be subtype-specific | Joins for the full row |
   | Use when | Few subtype-specific attributes/relationships | Subtypes are queried apart and never as a whole | Many subtype-specific columns **and** the supertype is an FK target |

   Avoid PostgreSQL table `INHERITS` for this: primary keys, unique constraints and foreign keys do not
   propagate across inheritance children.

## CAP4 — Modelling drills

The exercise set behind CAP1–CAP3, reduced to the trap each one sets and what a correct model shows.
Run these as a **self-check before signing a model off**, and as **lenses when reverse-engineering a
legacy schema** (A0) — each legacy symptom in the right-hand column is something the rubric can find
in DDL.

| # | Drill | Trap | A correct model shows | Legacy symptom |
|---|---|---|---|---|
| 1 | Extract entities from a narrative (a shop chain with stores, items, staff) | Treating "stock is out in one store, over in another" as an attribute of ITEM | STORE, ITEM, EMPLOYEE, and an intersection STOCK (item × store) holding quantity on hand | `cantidad_tienda_1`, `_2`… columns on the item table |
| 2 | Place attributes | Putting a per-store quantity on ITEM, or a chain-wide price on STOCK | Quantity on hand on the intersection; uniform price on ITEM | Price repeated per store row |
| 3 | Spot derived attributes ("total items, stores per state, staff per store") | Modelling counts and totals as attributes | None of them in the model; computed by query, stored only by a physical-design decision | `total_*`, `cant_*`, `promedio_*` columns maintained by procedures/triggers |
| 4 | Challenge a 1:1 (numbered manual copies, one per employee, spares in the safe) | Making it mandatory both ways | Optional on the manual side (spares exist), mandatory-or-optional on the employee side as the rule says | 1:1 FK with no `UNIQUE` — silently 1:M |
| 5 | Choose an identifier (agents identified by quadrant–area–zone) | Using location as identity | A system-generated agent id; the zone is a **relationship** that can change ("Smith moved zones") | PK on a business/location code; FK cascades when it changes |
| 6 | 1NF (order date on ORDER; current part name on PART) | Calling single-valued facts violations | Both fine; current part price lives on PART, order total is **derived** | Repeating groups: `curso_numero_1..3` |
| 7 | 2NF (part name on ORDER LINE; customer number on ORDER LINE) | Attributes depending on part of the composite UID | Part name on PART; customer on ORDER; line total (price × qty) is derived | Descriptions copied into detail tables |
| 8 | 3NF (employee with department id **and** department name) | Keeping the transitive dependency | DEPARTMENT entity; EMPLOYEE references it | `nombre_depto` next to `cod_depto`; mass updates to rename one department |
| 9 | Recursion (re-parent a manager and their subtree; merge under a new manager) | Assuming a width/depth limit; updating every descendant | No limit in either direction; moving a subtree updates **one** row | Fixed `jefe_1`, `jefe_2` level columns |
| 10 | Recursive and non-recursive versions of one hierarchy (sales area → city → district; manager → supervisor → seller) | Forcing a recursive model where levels have different attributes and rules | Both models drawn; recursive only where levels are alike | — |
| 11 | Subtypes + arcs together (vehicle rental: vehicle kinds with kind-specific readings; contract holder person **or** company; risky-customer flag) | Modelling the holder as two optional FKs with no exclusivity; subtype attributes on the supertype | Vehicle supertype/subtypes; an arc on the contract holder; risk as customer state | `id_persona` + `id_empresa` both nullable, no `CHECK` |
| 12 | Price history with no gaps, changing at most daily | Overwriting the current price; allowing overlaps | PART PRICE with `# effective date` in the UID; non-overlap enforced; no-gap rule stated and enforced | `precio` overwritten in place, or history table with no uniqueness on (part, date) |
| 13 | Ring of M:M (employee–project–task; skills; tasks per project) | Three binaries that let an employee do any task on any project | A ternary intersection referencing SKILL and PROJECT TASK, redundant intersections removed | Assignment table with FKs to the base tables only |
| 14 | TID checks (mark nulls, circle `NN`/`U` violations, find the FKs, recursive FKs, BOM table) | Missing that a "unique" column has duplicates or a recursive FK is mandatory | Every `NN`/`U` mark consistent with the sample rows | Self-FK declared `NOT NULL` |
| 15 | Map arcs explicitly **and** generically; map subtypes as single **and** separate tables | Picking one without stating the trade-off | Both drawn, choice justified against A3.2 steps 5–6 | `tipo_ref` + `id_ref` with no FK |

### Additional drills — whole models from interview extracts

Larger narratives where several rules interact. Each lists the decisions a correct model must make.

| # | Narrative | Decisions the model must get right | Legacy symptom |
|---|---|---|---|
| 16 | Cemetery: every client has a number; on death, a plot; plots numbered, ~70 % occupied, ~10 % of clients alive | 1:1 **optional at both ends** (living clients have no plot, empty plots have no client); FK on one side, `UNIQUE`, nullable | Plot columns on the client table; `0` as "no plot" |
| 17 | Repair shop: customers bring many devices; devices tagged on arrival; technicians sign devices and tools in and out, one tool at a time; who sits at which bench | CUSTOMER entered **once**, not per device; check-out/check-in as **historical relationships** with time in the UID; "one tool at a time" as a uniqueness rule on open check-outs; time worked on the device–technician intersection | Customer name and phone repeated on every work order |
| 18 | Apartments with varied equipment (beds, dishwashers, fireplaces), one paying tenant per unit, tenants may rent several units, parking spaces with externally assigned numbers | EQUIPMENT TYPE × UNIT intersection with **quantity**, not one column per appliance; tenant–unit 1:M; parking space with its **own** identifier related to the unit; vacancy counts are **derived** | `has_dishwasher`, `waterbeds`, `regular_beds` columns |
| 19 | Taxi dispatch: taxis, drivers in shifts, areas made of streets, a street in several areas; status reports by radio | STREET × AREA is **M:M** (resolve it); intersection lookup is a query, not an attribute; taxi status as state; counts, averages and percentages per area are **derived** | `taxis_in_area` counter maintained by code |
| 20 | Air cargo: packages on routes, one aircraft per route per day | The route–aircraft assignment changes **daily** → a dated assignment entity, not a 1:1 FK; per-route package counts and availability percentages are derived | Aircraft FK overwritten on the route every morning |
| 21 | Research foundation, current state only: employees in plants, employees on projects, inactive projects | EMPLOYEE × PROJECT resolved; inactive project = no assignments (a query, not a flag); **no history** because the user excluded it | `is_active` flag drifting from the assignment table |
| 22 | Hardware inventory: devices installed in offices on a date, shared by many authorized users | Install date on the device (or on a dated installation entity if devices move); DEVICE × USER authorization intersection; "offices with no device" is a query | User ids packed in one column |
| 23 | Spare parts whose number encodes row–drawer–bin; one part per bin, but a part can sit in two bins; clerks often know only the name | **Eliminate the intelligent key**: PART with a meaningless id, BIN as its own entity, PART × BIN placement; part name searchable (alternate key or index) | PK = location code; duplicate part rows for the second bin |
| 24 | Apartment complex: building code + floor + room identifies a unit; tenants identified by name (duplicates exist); rent varies monthly with two years of history and next year's agreed changes; tenant history with gaps allowed; payments; extras per floor | Dependent UID (unit within building); system-generated tenant id (names aren't unique); RENT with effective date, **always one value, no overlaps, future dates allowed**; tenancy history **gaps allowed but no overlaps**; PAYMENT history; EXTRA × FLOOR with quantity | Rent overwritten in place; tenant PK on name |
| 25 | Restaurant chain: districts, branches within districts, employees numbered by hiring branch, full/part-time, branch managers and district managers, daily product sales with two years of history | Branch UID dependent on district; employee id **not** derived from the hiring branch (they transfer); part/full-time as state or subtype; manager roles as relationships (a branch manager temporarily covering a district); daily sales at branch × product × day, monthly figures **derived** | Employee id `A-01-01`; a stored monthly-sales table kept in step by a job |
