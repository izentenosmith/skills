CREATE TABLE invoice_line (
    id            BIGINT PRIMARY KEY,
    invoice_id    BIGINT NOT NULL REFERENCES invoice_header(id),
    description   TEXT NOT NULL,
    amount_cents  BIGINT NOT NULL
);
