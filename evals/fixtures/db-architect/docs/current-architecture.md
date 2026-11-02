# Current architecture (tech lead, 2026-10-29)

- **PostgreSQL 16**, one primary and one streaming replica in the same region. Replication is
  asynchronous; Patroni promotes the replica automatically if the primary fails.
- Tables `event`, `seat`, `seat_hold`, `customer`, `ticket_order`, `ticket`, `payment`.
  `seat (event_id, seat_no)` is the primary key of `seat`; `seat_hold` has no unique key — the app
  checks Redis before inserting a hold.
- **Redis** holds `seat:{event}:{seat}` = `free | held | sold`. Checkout reads Redis to decide whether a
  seat can be held, writes the hold to Postgres, then sets the Redis key. During last season's biggest
  on-sale Redis and Postgres disagreed on 41 seats; two of them were sold twice.
- **Elasticsearch** holds the event catalogue for search. The app writes each event to Postgres and then
  to Elasticsearch; orders are also indexed there so support can search them.
- **Metabase** (the sales dashboard) connects to the **primary** and runs its queries live; during
  on-sales the dashboard queries were the top consumers of CPU on the primary.
- The "My tickets" page reads from the **replica** to keep load off the primary.
