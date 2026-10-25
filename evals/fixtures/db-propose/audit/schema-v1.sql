-- PawLedger v1 clinic database, schema as dumped by `.schema` from the sample clinic file
-- (Harbourside Vets, 2026-10-02). SQLite 3.45. The app opens connections with foreign_keys = ON.

CREATE TABLE owner (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT
);

CREATE TABLE vet (
    id INTEGER PRIMARY KEY,
    licence_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE pet (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES owner(id),
    primary_vet_id INTEGER,
    name TEXT NOT NULL,
    species TEXT NOT NULL,
    date_of_birth TEXT,
    microchip TEXT
);

CREATE TABLE vaccine (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE vaccination (
    id INTEGER PRIMARY KEY,
    pet_id INTEGER NOT NULL,
    vaccine_id INTEGER NOT NULL,
    vet_id INTEGER NOT NULL,
    given_on TEXT NOT NULL,
    lot_no TEXT NOT NULL
);

CREATE TABLE appointment (
    id INTEGER PRIMARY KEY,
    pet_id INTEGER NOT NULL REFERENCES pet(id) ON DELETE CASCADE,
    vet_id INTEGER NOT NULL REFERENCES vet(id),
    starts_at TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    reason TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX ix_appointment_vet ON appointment (vet_id, starts_at);
