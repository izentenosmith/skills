# PawLedger clinic database — build workspace

- `proposal/` — the proposal for the clinic-database redesign and its acceptance record
- `design/` — the approved redesign (`design.md`, machine-readable `model.json`)
- `diagrams/` — the draw.io models: `er-model.drawio` (Barker) and `relational-model.drawio`
- `config/app.ini` — developer build settings (dev clinic file path, SQLCipher key, Reports sync)
- `scripts/db` — developer tool: `scripts/db apply FILE.sql` applies a script to the dev clinic file
- `ddl/` — generated SQL goes here; scripts are reviewed in a pull request before any release uses them

PawLedger is a desktop app for small veterinary clinics; each clinic's data is one SQLite file on the
front-desk PC. The app executes the reviewed schema scripts itself when it creates a clinic file.
