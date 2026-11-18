CREATE TABLE invoice_header (
    id            BIGINT PRIMARY KEY,
    legacy_id     INTEGER NOT NULL UNIQUE,
    customer_id   BIGINT NOT NULL,
    issued_at     TIMESTAMP NOT NULL,
    total_cents   BIGINT NOT NULL
);
