# Indexes to add before Black Friday

From the backend team, to be applied next week:

1. `CREATE INDEX ix_order_line_order ON order_line (order_id);` — order lines are loaded by order all the time.
2. `CREATE INDEX ix_customer_email_lower ON customer (lower(email));` — support's email lookup.
3. `CREATE INDEX ix_order_line_note ON order_line (note);` — just in case we search notes later.
4. `CREATE INDEX ix_sales_order_status_created ON sales_order (status, created_at);` — the open-orders list.
5. `CREATE INDEX ix_product_name ON product (name);` — product search.
