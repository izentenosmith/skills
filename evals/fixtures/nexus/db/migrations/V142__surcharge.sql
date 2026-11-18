CREATE TABLE surcharge (
    id            BIGINT PRIMARY KEY,
    invoice_id    BIGINT NOT NULL REFERENCES invoice_header(id),
    kind          TEXT NOT NULL,
    rate          NUMERIC(9,4) NOT NULL
);
