-- brightcart schema, pg_dump --schema-only, 2026-10-28 (trimmed to the tables in scope)

CREATE TABLE public.customer (
    customer_id bigint GENERATED ALWAYS AS IDENTITY,
    email text NOT NULL,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT customer_pkey PRIMARY KEY (customer_id)
);

CREATE TABLE public.product (
    product_id bigint GENERATED ALWAYS AS IDENTITY,
    sku text NOT NULL,
    name text NOT NULL,
    stock integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    CONSTRAINT product_pkey PRIMARY KEY (product_id),
    CONSTRAINT product_sku_key UNIQUE (sku)
);

CREATE TABLE public.sales_order (
    order_id bigint GENERATED ALWAYS AS IDENTITY,
    customer_id bigint NOT NULL REFERENCES public.customer (customer_id),
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    total numeric(12,2) NOT NULL,
    CONSTRAINT sales_order_pkey PRIMARY KEY (order_id)
);

CREATE TABLE public.order_line (
    order_id bigint NOT NULL REFERENCES public.sales_order (order_id),
    line_no integer NOT NULL,
    product_id bigint NOT NULL REFERENCES public.product (product_id),
    qty integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    note text,
    CONSTRAINT order_line_pkey PRIMARY KEY (order_id, line_no)
);

-- Rows imported from the old CRM on 2026-10-20; customers it could not match have no customer_id.
CREATE TABLE public.blocked_customer (
    blocked_id bigint GENERATED ALWAYS AS IDENTITY,
    customer_id bigint REFERENCES public.customer (customer_id),
    reason text NOT NULL,
    blocked_at timestamptz NOT NULL,
    CONSTRAINT blocked_customer_pkey PRIMARY KEY (blocked_id)
);

CREATE INDEX ix_customer_email ON public.customer USING btree (email);
CREATE INDEX ix_order_created ON public.sales_order USING btree (created_at);
CREATE INDEX ix_order_status ON public.sales_order USING btree (status);
CREATE INDEX ix_order_line_product ON public.order_line USING btree (product_id);

-- Set for the bulk import of historical orders on 2026-10-20.
ALTER TABLE public.sales_order SET (autovacuum_enabled = false);
