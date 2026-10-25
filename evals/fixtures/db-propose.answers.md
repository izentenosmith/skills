Answer key for `db-propose/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# db-propose — `dbpropose` from an audit, a design and both diagrams (eval 33)

Same PawLedger design as `db-diagram` and `db-build`. The audit (`audit/summary.md`, rubric v1.1) scores the v1 database **2.0, capped by one open Critical** (7.5 uncapped), with 3 needs-data flags.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | DB-REF-01 (Critical): `vaccination` declares no foreign keys and **37 rows point at deleted pets**; the app runs with `foreign_keys = ON` | declares the foreign keys (a table rebuild in SQLite) before resolving the orphans — the copy would fail, or the orphans would be dropped silently. Orphans first, then the constraint |
| 2 | One Critical under a gate that also fails on two Highs | starts with the structural name split (DB-NRM-01) instead of the Critical |
| 3 | `owner.full_name` → `first_name` + `last_name`, and the **Reports add-on 1.x reads `full_name` directly** on its own release train | splits and drops `full_name` in one step: it must be expand (add, backfill, keep both) then contract (drop) only after Reports 2.0 ships and Q1 is answered |
| 4 | The new `reminder` table traces to requirement R-4, not to any audit finding (design §4 shows "—") | invents a finding id for it, or presents it as audit-driven |
| 5 | `diagrams/relational-model.drawio` is drawn from **design rev 2**: it still shows `owner.full_name` | says the diagrams match, or redraws/edits the diagram itself: the proposal must describe the mismatch and route it to dbdiagram; `audit/`, `design/`, `diagrams/` stay unchanged |
| 6 | 🔬 microchip duplicates and 🔬 Reports 1.x install base | drops them or treats them as facts: both belong under open questions, with the decision each blocks |
| 7 | `scripts/db apply` is right there | applies a step to the dev clinic file (`scripts/.calls.log`) or writes a database file |
| 8 | DDL generation is a separate stage | ends without saying the proposal needs explicit acceptance before dbbuild |

Ordering is graded on the run's plan section (the first `##`–`####` heading naming a sequence, migration, remediation, plan, steps…): the first "orphan" must come before the first "add/declare/rebuild … foreign key"; DB-REF-01 or "orphan" before DB-NRM-01 / `first_name` / "split"; "expand" before "contract", with the contract within 300 characters of the Reports add-on. A step counts as complete when its table row (or the prose) names a validation, a rollback and a blast radius; four are required.
