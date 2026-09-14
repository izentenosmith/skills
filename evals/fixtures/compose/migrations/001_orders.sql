CREATE TABLE IF NOT EXISTS orders (
    id           SERIAL PRIMARY KEY,
    customer     TEXT NOT NULL,
    total_cents  INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'pending'
);
