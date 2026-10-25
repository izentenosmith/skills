# PawLedger clinic database — Design (redesign of v1)

> Stage: design · status: approved for diagrams and proposal · **rev 3, 2026-10-16**.
> Machine-readable model: `model.json` (same folder). Input audit: PawLedger v1 audit, 2026-10-09 (score 2.0 capped,
> 7.5 uncapped). Target engine: **SQLite 3.45**, bundled with the desktop app through better-sqlite3.

## 1. Scope and requirements

PawLedger is a desktop practice-management app for small veterinary clinics. Each clinic keeps its data in one
SQLite file on the front-desk PC; the app opens every connection with `PRAGMA foreign_keys = ON`. The file is
encrypted at rest with SQLCipher; the key is part of the app configuration (`config/app.ini` in
developer builds).

| # | Requirement (practice manager, interviews 2026-09) |
|---|---|
| R-1 | Every pet belongs to exactly one owner on record; owners are searched and sorted by last name. |
| R-2 | Appointments are booked for one pet with one vet, with a start time and a length in minutes. |
| R-3 | Every vaccination is recorded with the vet who gave it, the vaccine and its lot number, and the date. |
| R-4 | The app sends reminders when a pet's next dose of a vaccine is due, and records when each was sent. |
| R-5 | Nothing about a pet's medical history may disappear because a vet leaves the practice. |

Out of scope: billing and stock (separate modules, separate files).

## 2. Conceptual model (Barker)

### 2.1 Entities

| Entity | Description | Attributes (`#` UID · `*` mandatory · `o` optional) |
|---|---|---|
| OWNER | A person or organisation responsible for one or more pets and their bills. | `# id` (system-generated: owners share names), `* first name`, `* last name`, `* phone`, `o email` |
| PET | An animal registered with the practice. | `# id` (system-generated), `* name`, `* species`, `o date of birth`, `o microchip` |
| VET | A veterinary surgeon licensed to treat and vaccinate. | `# licence number`, `* name` |
| VACCINE | A vaccine product the practice stocks. | `# code`, `* name` |
| APPOINTMENT | A booked consultation slot for one pet with one vet. | `# id` (system-generated), `* starts at`, `* duration minutes`, `* reason`, `o notes` |
| REMINDER | A notice that a pet's next dose of a vaccine is due. | `# due on`, `o sent at`; UID = PET + VACCINE + `due on` |

`species` is one of dog, cat, rabbit, bird, other. Ages, overdue counts and "next due" dates are derived and are not
attributes.

### 2.2 The vaccination association

R-3 is a **three-way association**: *a VET gives a dose of a VACCINE to a PET on a date.* It carries two facts of its
own, `# given on` and `* lot number`, and is identified by the pet, the vaccine and the date given (the same vaccine is
not given to the same pet twice on one day). Every vaccination involves exactly one pet, one vaccine and one vet; a
pet, a vaccine or a vet may be involved in none or many. Logical table: `vaccination`.

### 2.3 Relationships

| Relationship | Reading (both directions) | Evidence |
|---|---|---|
| PET – OWNER | Each PET **must be** *owned by* one and only one OWNER. Each OWNER **may be** the *owner of* one or more PETs. | R-1 |
| PET – VET | Each PET **may be** *registered with* one and only one VET. Each VET **may be** the *primary vet of* one or more PETs. | **inferred** — see below |
| APPOINTMENT – PET | Each APPOINTMENT **must be** *booked for* one and only one PET. Each PET **may be** the *subject of* one or more APPOINTMENTs. | R-2 |
| APPOINTMENT – VET | Each APPOINTMENT **must be** *attended by* one and only one VET. Each VET **may be** the *attending vet for* one or more APPOINTMENTs. | R-2 |
| REMINDER – PET | Each REMINDER **must be** *issued for* one and only one PET. Each PET **may be** *reminded by* one or more REMINDERs. Part of REMINDER's UID. | R-4 |
| REMINDER – VACCINE | Each REMINDER **must be** a *prompt for* one and only one VACCINE. Each VACCINE **may be** *prompted by* one or more REMINDERs. Part of REMINDER's UID. | R-4 |

**PET – VET is inferred, not confirmed.** v1 has a column `pet.primary_vet_id` with no foreign key and no
documentation. Its values all match vet ids, and the name suggests "the pet's primary vet"; nobody at the practice
has confirmed that meaning yet (open question Q4). The relationship is kept because the column exists and the app
fills it, with the meaning marked as inferred.

## 3. Logical and physical design (SQLite)

Surrogate `id INTEGER PRIMARY KEY` on every table; natural keys become `UNIQUE`. Dates are ISO-8601 `TEXT`
(`YYYY-MM-DD`; `starts_at` and `sent_at` are `YYYY-MM-DDTHH:MM`). Table and column names are `snake_case`, singular.

| Table | Columns (`NN` = NOT NULL) | Keys and constraints |
|---|---|---|
| `owner` | `id` INTEGER, `first_name` TEXT NN, `last_name` TEXT NN, `phone` TEXT NN, `email` TEXT | PK `id` |
| `vet` | `id` INTEGER, `licence_no` TEXT NN, `name` TEXT NN | PK `id`; UNIQUE `licence_no` |
| `vaccine` | `id` INTEGER, `code` TEXT NN, `name` TEXT NN | PK `id`; UNIQUE `code` |
| `pet` | `id` INTEGER, `owner_id` INTEGER NN, `primary_vet_id` INTEGER, `name` TEXT NN, `species` TEXT NN, `date_of_birth` TEXT, `microchip` TEXT | PK `id`; FK `owner_id` → `owner`; FK `primary_vet_id` → `vet`; CHECK `species IN ('dog','cat','rabbit','bird','other')`; `microchip` uniqueness **undecided** (Q3) |
| `vaccination` | `id` INTEGER, `pet_id` INTEGER NN, `vaccine_id` INTEGER NN, `vet_id` INTEGER NN, `given_on` TEXT NN, `lot_no` TEXT NN | PK `id`; FKs → `pet`, `vaccine`, `vet`; UNIQUE (`pet_id`, `vaccine_id`, `given_on`) |
| `appointment` | `id` INTEGER, `pet_id` INTEGER NN, `vet_id` INTEGER NN, `starts_at` TEXT NN, `duration_min` INTEGER NN, `reason` TEXT NN, `notes` TEXT | PK `id`; FKs → `pet`, `vet`; CHECK `duration_min > 0` |
| `reminder` | `id` INTEGER, `pet_id` INTEGER NN, `vaccine_id` INTEGER NN, `due_on` TEXT NN, `sent_at` TEXT | PK `id`; FKs → `pet`, `vaccine`; UNIQUE (`pet_id`, `vaccine_id`, `due_on`) |

Attribute → column names that differ: `licence number` → `licence_no`, `lot number` → `lot_no`, `duration minutes`
→ `duration_min`, `date of birth` → `date_of_birth`.

**Referential actions** (R-5: medical history never disappears with a vet):

| Foreign key | On delete |
|---|---|
| `pet.owner_id` → `owner.id` | RESTRICT |
| `pet.primary_vet_id` → `vet.id` | SET NULL |
| `vaccination.pet_id` → `pet.id` | RESTRICT |
| `vaccination.vaccine_id` → `vaccine.id` | RESTRICT |
| `vaccination.vet_id` → `vet.id` | RESTRICT |
| `appointment.pet_id` → `pet.id` | CASCADE |
| `appointment.vet_id` → `vet.id` | RESTRICT |
| `reminder.pet_id` → `pet.id` | CASCADE |
| `reminder.vaccine_id` → `vaccine.id` | RESTRICT |

**Indexes** (every FK column is indexed, or leads a unique index): `pet(owner_id)`, `pet(primary_vet_id)`,
`vaccination(vaccine_id)`, `vaccination(vet_id)`, `appointment(pet_id)`, `appointment(vet_id, starts_at)`,
`reminder(vaccine_id)`. `vaccination(pet_id, …)` and `reminder(pet_id, …)` are led by their unique constraints.

## 4. Audit traceability

| Change from v1 | Audit finding |
|---|---|
| Declare the three `vaccination` foreign keys (v1 has none) | DB-REF-01 |
| Split `owner.full_name` into `first_name` and `last_name` | DB-NRM-01 |
| Constrain `pet.species` to five values (v1 is free text: `Dog`, `dog`, `canine`, …) | DB-DOM-01 |
| Declare `pet.primary_vet_id` → `vet` | DB-REF-02 |
| `CHECK (duration_min > 0)` on `appointment` | DB-DOM-02 |
| `UNIQUE (code)` on `vaccine` | DB-KEY-01 |
| Index the foreign-key columns | DB-KEY-02 |
| New `reminder` table | — |

## 5. Open questions

1. **Q1** — How many clinics still run Reports add-on 1.x, which reads `owner.full_name` straight from the file?
   There is no telemetry; support estimates "most".
2. **Q2** — The 37 `vaccination` rows that point at deleted pets (audit DB-REF-01): restore the pets as archived
   records, or move the rows to a quarantine table? The practice manager is checking paper records.
3. **Q3** — Is `pet.microchip` an alternate key? v1 has 4 chip numbers shared by two pets each; nobody knows yet
   whether that is re-chipping or a data-entry error. Until this is decided, the design states no uniqueness rule.
4. **Q4** — Does `pet.primary_vet_id` mean the pet's primary vet? Inferred from the column name only.
