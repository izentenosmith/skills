# PawLedger clinic database — proposal workspace

- `audit/` — the v1 audit (`summary.md`) and the schema it was run against (`schema-v1.sql`)
- `design/` — the approved redesign (`design.md`, machine-readable `model.json`)
- `diagrams/` — the draw.io models: `er-model.drawio` (Barker) and `relational-model.drawio`
- `scripts/db` — developer tool: `scripts/db apply FILE.sql` applies a script to the dev clinic file

PawLedger is a desktop app for small veterinary clinics; each clinic's data is one SQLite file on the
front-desk PC. Schema changes ship inside an app release, and clinics install releases themselves, usually
within four weeks.

The **Reports add-on** is sold separately and ships on its own release train. Version 1.x opens the clinic
file read-only and queries it directly; 2.0 is planned for January 2027.
