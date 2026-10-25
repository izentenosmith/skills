Answer key for `db-design/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# db-design — `dbdesign` from requirements (eval 31)

A requirements document for Greenway Coworking's front-desk database (`docs/requirements.md`). The traps sit in what the requirements *ask for*.

| # | Planted | Where | Rubric / theory | Catches a run that… |
|---|---|---|---|---|
| 1 | "the design and its DDL must target **SQLite**" — no server | Platform | dbdesign step 2 (state the engine); physical-design is PostgreSQL 18, "for another target engine, keep the model and translate these choices" | writes PostgreSQL DDL (`GENERATED … AS IDENTITY`, `timestamptz`, `daterange`, `WITHOUT OVERLAPS`, `num_nonnulls`) because that is what the reference describes |
| 2 | "Each booking keeps **the list of attendees**" | Rooms and bookings | M:M → intersection entity (er-modeling §A1.3), 1NF | stores `attendee_ids` as a CSV / JSON / array column on the booking |
| 3 | Plan prices change; past months need the price that applied; future prices entered in advance | Plans | historical entity with a time indicator in its UID (§A2.6, drill 12) | keeps one `monthly_price` on the plan and overwrites it, or keeps a history table with no uniqueness on (plan, date) |
| 4 | "record … **their age**" | Members | derived attribute (§A1.4, drill 3) | stores `age` instead of a birth date |
| 5 | "Store each booking's **total cost** on the booking" | Rooms and bookings | derived attribute; physical-design §4 — denormalize only deliberately | stores it silently; a correct run declines it (a view computes it) or justifies it as deliberate denormalization with a consistency mechanism |
| 6 | A member is **either** an individual **or** a company, each with its own attributes, and bookings point at members | Members | subtypes (§A2.4) and their mapping (§A3.2 step 6; physical-design §5.1) | puts every column on one table with no CHECK tying the kind to its columns, or makes separate tables with no common key for bookings to reference |
| 7 | Member number on the card, VAT number "no two companies share", email "no two individuals" | Members | candidate keys → `UNIQUE` alternates; surrogate PK (physical-design §2) | makes the email or the member number the primary key, or forgets the uniqueness |
| 8 | Operations: every individual works for a member company; sales: freelancers book for themselves; "we haven't settled which is right" | Members | dbdesign step 2: "Do not silently turn an assumption into a constraint" | declares `company_id NOT NULL` (or drops the link) and records the operations view as fact; a correct run keeps the relationship optional and lists it as an open question |

Graded executably. The run's DDL (its added `.sql` files, else the ```` ```sql ```` blocks of the document holding the most `CREATE TABLE`s) is executed statement by statement in an in-memory SQLite with `PRAGMA foreign_keys = ON`, and the design is read back from `PRAGMA table_info`, `foreign_key_list` and `index_list`: every table has a PK; an intersection table has FKs to the booking and to a member/individual table and a unique key on exactly that pair; a child of the plan table carries a price and a date column that, with the plan FK, form a unique key; no `age` column and a birth-date column; email, VAT and member number each `UNIQUE` on their own and not the PK; the FK from the individual (or member) to the company is nullable; the subtypes are either supertype + subtype tables sharing the member's key or one table whose CHECK ties the kind to the subtype's columns.

From the document: Barker relationship sentences with UPPERCASE entity names ("Each BOOKING must be for one and only one ROOM"), at least three functional dependencies with a 3NF/BCNF rationale, at least three of Codd's rules reviewed, an *Assumptions* section apart from an *Open questions* section that carries the freelancer question, and the stored total discussed as derived.

Safety invariants: no SQLite database file created in the repo (dbdesign proposes; it does not apply), and `docs/requirements.md` untouched.
