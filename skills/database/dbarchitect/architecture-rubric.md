# Architecture Rubric — A1–A12

**Contents:** A1. Load parameters are stated · A2. One system of record per fact · A3. Derived data is named-source, one-way and rebuildable · A4. Derived stores are fed by the database, CDC or an outbox — never dual writes · A5. Each read path states its freshness and consistency need · A6. Each workflow names the anomalies it can't tolerate · A7. Hard constraints have a coordination point · A8. Retries are safe end to end · A9. No heterogeneous distributed transactions · A10. Replication and failover are designed, not defaulted · A11. Partitioning is justified and keyed from the access pattern · A12. Analytics are separated from transactions · Summary table (Review mode)

> The rules a data architecture is built from (Design mode) and graded against (Review mode). Each item
> gives the rule, why it matters, the evidence a review looks for, and the question to ask when the
> evidence isn't there. Theory references are to [`theory.md`](theory.md); store-specific choices are in
> [`store-selection.md`](store-selection.md). Grade each item 🟢 met / 🟡 partly or unconfirmed / 🔴
> violated, always with its evidence.

### A1. Load parameters are stated
**Rule:** every store decision rests on stated volumes, rates, read/write ratio, fan-out and percentile
latency targets per domain.
**Why:** "it needs to scale" is not a requirement; a choice made without numbers is made on fashion.
**Evidence:** a load table with sources; growth estimates; latency targets as p95/p99.
**Ask:** what is the peak write rate, the data volume in two years, and the latency users notice?
**🔴 when:** a store, sharding scheme or cache was introduced with no figure behind it.

### A2. One system of record per fact
**Rule:** each fact has exactly one authoritative, writable home (theory §6).
**Why:** two writable homes drift, and nobody can say which is right — divergence that is permanent, not
stale.
**Evidence:** the data inventory; integration code writing the same fact to two stores; "sync" jobs
running both ways.
**Ask:** if these two copies disagree, which one wins, and who decided?
**🔴 when:** two stores accept writes for one fact. Critical.

### A3. Derived data is named-source, one-way and rebuildable
**Rule:** caches, search indexes, read models, warehouses and replicas each name their source, are
written only by their derivation, and can be dropped and rebuilt (theory §6).
**Evidence:** the dataflow map; a documented rebuild path (a full re-sync from the source, a replay from
a log position).
**Ask:** how would you rebuild this store from scratch, and how long would it take?
**🔴 when:** users or services write directly to a derived store, or there is no rebuild path.

### A4. Derived stores are fed by the database, CDC or an outbox — never dual writes
**Rule:** the source's change stream (or an outbox table written in the source's own transaction)
drives every derived store.
**Why:** two independent writes from application code race (copies end in different final states with
no error) and fail partially (one write lands, the other doesn't).
**Evidence:** integration code; the order of writes; failure handling between them.
**🔴 when:** application code writes the source and a derived store in two separate operations. High
(Critical when the "derived" store is read as authoritative anywhere).

### A5. Each read path states its freshness and consistency need
**Rule:** for every read served by a replica, cache or derived store, the acceptable staleness
(timeliness) is stated, and integrity — no loss, no contradiction — is never relaxed.
**Evidence:** a consistency map; session guarantees for replica reads (read-your-writes after a user's
own update; monotonic reads across page loads).
**Ask:** may this screen show data that is a few seconds old? What happens if a user saves and reloads?
**🔴 when:** a read-after-write flow is served from an asynchronous replica with no guarantee.

### A6. Each workflow names the anomalies it can't tolerate
**Rule:** per transaction type, the anomalies of theory §5.2 that must be excluded, and the mechanism
(declared constraint, atomic statement, lock, serializable isolation) that excludes them.
**Evidence:** the engine's default isolation level and the level each workflow runs at; constraints
backing each invariant.
**🔴 when:** an invariant on money, stock, bookings or identity relies on a check-then-act under read
committed or snapshot isolation.

### A7. Hard constraints have a coordination point
**Rule:** uniqueness and other constraints that must never be violated have one place that decides — a
single leader for the key, a database constraint, or consensus. Elsewhere, coordination-free designs
with compensation are an explicit business decision.
**Evidence:** where usernames, seat assignments or account balances are decided in a multi-region or
multi-leader setup.
**🔴 when:** a hard constraint is checked independently in several places that accept writes.

### A8. Retries are safe end to end
**Rule:** every command that may be retried (payments, transfers, order submission, message
consumers) carries an idempotency key enforced by a unique constraint at the system of record, and
retries only transient failures.
**Evidence:** request ids in APIs and messages; `UNIQUE (request_id)`; consumer de-duplication.
**🔴 when:** an at-least-once consumer or a client retry can apply a money movement twice.

### A9. No heterogeneous distributed transactions
**Rule:** no XA / two-phase commit across different stores or services.
**Why:** a participant that has voted "prepared" holds its locks until the coordinator decides; a
coordinator failure leaves transactions in doubt and couples the availability of every participant.
**Evidence:** transaction managers spanning databases and brokers; linked-server writes inside
transactions.
**Alternative:** a log or outbox plus idempotent consumers.
**🔴 when:** present on a request path. High.

### A10. Replication and failover are designed, not defaulted
**Rule:** topology, synchronous vs asynchronous replication, RPO/RTO, failover procedure and the
conflicts a multi-leader or leaderless design accepts are stated. Last-write-wins is named as the data
loss it is.
**Evidence:** replication configuration; failover runbooks; conflict-resolution rules.
**Ask:** if the primary fails now, which acknowledged writes can be lost, and could a promoted replica
hand out keys that already exist elsewhere?
**🔴 when:** asynchronous replication with automatic failover on a store whose lost writes would not be
noticed.

### A11. Partitioning is justified and keyed from the access pattern
**Rule:** shard only when a stated number says one node can't hold the data or the writes; choose the
key from the dominant access pattern; know the hot keys, the secondary-index strategy and the
rebalancing method.
**Evidence:** the load table (A1); key choice and its rationale; queries that don't include the key
(scatter/gather).
**🔴 when:** a monotonic key range-partitions every write onto the last shard, or most queries scatter
to every shard.

### A12. Analytics are separated from transactions
**Rule:** heavy analytic scans don't run on the OLTP system of record; a warehouse or columnar store is
derived from it (A3, A4) and modelled for analysis (dimensional modelling), with its staleness stated.
**Evidence:** reports and BI tools pointed at the OLTP database; long-running scans in the workload.
**🔴 when:** reporting load visibly competes with transactions (dbquery evidence) and no derived store
exists.

## Summary table (Review mode)

| # | Item | Grade | Evidence |
|---|---|---|---|
| A1 | Load parameters stated | 🟢/🟡/🔴 | … |
| A2 | One system of record per fact | | |
| A3 | Derived data named, one-way, rebuildable | | |
| A4 | No dual writes | | |
| A5 | Freshness stated per read path | | |
| A6 | Anomalies excluded per workflow | | |
| A7 | Coordination for hard constraints | | |
| A8 | Idempotent retries | | |
| A9 | No heterogeneous 2PC | | |
| A10 | Replication and failover designed | | |
| A11 | Partitioning justified | | |
| A12 | Analytics separated | | |
