# PawLedger v1 clinic database — Audit summary

> Usage: in use (every installed clinic). Objects: 6 tables · 1 index · 0 views · 0 triggers.
> Source: `schema-v1.sql`, dumped from the sample clinic file (Harbourside Vets) on 2026-10-02, plus profiling
> queries against the same file. Rubric v1.1. Audited 2026-10-09. Coverage: every table and index.

## Score

| Object type | p (criteria) | Base | Cap | Score |
|---|---|---:|---:|---:|
| tables | 0.74 | 7.4 | 2.0 (DB-REF-01, Critical) | **2.0** |
| indexes | 0.80 | 8.0 | — | 8.0 |
| **Database** (weighted 0.9 / 0.1) | | 7.5 uncapped | 2.0 | **2.0** |

## Severity tally

Critical 1 · High 2 · Medium 3 · Low 1 · 🔬 3 open

## Findings (worst first)

| ID | Object | Finding | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| DB-REF-01 | `vaccination.pet_id`, `vaccine_id`, `vet_id` | No FOREIGN KEY on any of the three columns. Profiling found **37 rows whose `pet_id` matches no pet** (9 pets deleted since 2023); `vaccine_id` and `vet_id` all resolve today. | ✅ | §7 referential integrity | Critical | schema-v1.sql:33-40; profile q3 |
| DB-NRM-01 | `owner.full_name` | First and last name in one column; owners cannot be searched or sorted by last name (R-1). Not atomic for the way the business uses it. | ✅ | §3 1NF; er-modeling §A1.4 | High | schema-v1.sql:6 |
| DB-DOM-01 | `pet.species` | Free text: 11 spellings of 4 species (`Dog`, `dog`, `canine`, `Cat `, …). No CHECK and no lookup. | ✅ | §7 domain integrity | High | schema-v1.sql:22; profile q5 |
| DB-REF-02 | `pet.primary_vet_id` | No FOREIGN KEY and no documentation. Every value matches a vet id today; the meaning is guessed from the name. | ⚠️ | §7 referential integrity | Medium | schema-v1.sql:20 |
| DB-DOM-02 | `appointment.duration_min` | No CHECK; 3 rows hold 0. | ✅ | §7 domain integrity | Medium | schema-v1.sql:47; profile q6 |
| DB-KEY-01 | `vaccine.code` | Natural key without UNIQUE (no duplicates today). | ✅ | §7 entity integrity; er-modeling §A1.5 | Medium | schema-v1.sql:29 |
| DB-KEY-02 | `vaccination`, `pet` | Foreign-key columns not indexed: `vaccination.pet_id`, `vaccine_id`, `vet_id`; `pet.owner_id`. | ✅ | §7 smart indexing | Low | schema-v1.sql:19, 33-40 |

## Needs-data flags (not scored)

- 🔬 **Microchip duplicates.** 4 chip numbers are each held by two pets. Re-chipping by a shelter, or data-entry
  error? Needs the practice's records; it decides whether `microchip` can be an alternate key.
- 🔬 **Reports add-on 1.x install base.** The add-on queries `SELECT full_name, phone FROM owner` directly
  (vendor-supplied source, `reports-addon/queries/clients.sql:3`). How many clinics still run 1.x is unknown: there
  is no telemetry.
- 🔬 **The 37 orphaned vaccination rows.** Whether the deleted pets can be restored from paper records, or the rows
  must be set aside, is being checked by the practice manager.

## Coupling

| Source | Target | Via | Count |
|---|---|---|---|
| Reports add-on 1.x | `owner.full_name`, `owner.phone` | direct read-only SQL on the clinic file | 1 query |
| PawLedger app | every table | better-sqlite3, `foreign_keys = ON` per connection | — |

## What is working well

- 🟢 Surrogate `INTEGER PRIMARY KEY` on every table; `vet.licence_no` is declared `UNIQUE`.
- 🟢 `appointment` declares both its foreign keys, with a deliberate `ON DELETE CASCADE` on the pet.
- 🟢 The app turns `foreign_keys` on for every connection, so declared constraints are enforced.

## Gate

- Score 2.0 < 9.0 — **not met**
- Open Critical/High — **not met** (1 Critical, 2 High)
- 🔬 ratio 3/7 objects — **not met** (> 10%)
- Usage: in use, not a copy — met

Gate failed: route to dbdesign, dbdiagram and dbpropose.
