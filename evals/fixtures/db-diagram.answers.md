Answer key for `db-diagram/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# db-diagram — `dbdiagram` from an approved design (eval 32)

The estate is **PawLedger**, a desktop app for small vet clinics with one SQLite file per clinic. The same design (`design/design.md` rev 3 and `design/model.json`: 6 entities, one three-way association, 6 binary relationships, 7 tables, 9 foreign keys) is used by `db-propose` (eval 33) and `db-build` (eval 34), so the three stages agree with each other.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | VACCINATION is written in the design as a **three-way association** (a VET gives a VACCINE to a PET on a date), with no role names | draws a Chen diamond, or one connector joining three or more entities, instead of an intersection entity VACCINATION with three binary relationships (dbdiagram: "Never draw a ternary relationship connector") |
| 2 | PET – VET is **inferred** from the v1 column `pet.primary_vet_id` (design §2.3, open question Q4) | draws "registered with / primary vet of" as an established fact, with no inferred label on the relationship or in the provenance note |
| 3 | Every relationship but PET – VET is mandatory at one end and optional at the other | draws each relationship as one solid line: Barker shows each end's optionality on its own half (solid = must be, dashed = may be) |
| 4 | Attribute marks are given in the design (`#`, `*`, `o`) | drops the marks, or substitutes SQL `NOT NULL` on the ER page |
| 5 | The entity and its table share a name (VACCINATION → `vaccination`) | lets draw.io generate cell IDs, so nothing traces an entity to its table across the two files |
| 6 | The design is the input | edits `design/` while drawing (it must stay byte-identical) |

A correct run writes `er-model.drawio` (page **Barker ER Model**, a legend naming Barker notation and its glyphs, UPPERCASE singular entities in soft-cornered boxes with `#`/`*`/`o` attributes, two-segment relationships with a lowercase role name at each end) and `relational-model.drawio` (every table with its columns, PK and FK labels, exactly one edge per foreign key), both uncompressed mxfile with semantic cell IDs (`er-pet` ↔ `rel-pet`) and a provenance note naming `design/design.md`.

How it is graded: both files are parsed as XML. Entities are found by label; edges are resolved to the entity (or table) they end on, through nested cells. A non-entity vertex an edge ends on is a connector: a junction joining two half-lines is a Barker relationship, a connector joining three or more entities is a ternary connector, and a diamond or oval joined to an entity is Chen notation. Role names are edge labels (the edge's value or a label cell inside it); optionality is the `dashed` style of each segment.
