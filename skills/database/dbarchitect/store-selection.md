# Store Selection — Models, Engines, Replication, Partitioning

> The trade-off tables dbarchitect decides from. They state what each choice buys and costs; the
> decision itself comes from the load parameters and access patterns of
> [`SKILL.md`](SKILL.md) steps 1–3. Vendor and version facts change: check the current documentation
> for the version you are choosing before writing a decision down.

## 1. Data model by relationship shape and access pattern

| Model | Fits when | Costs | Default role |
|---|---|---|---|
| **Relational** | Many-to-one and many-to-many relationships matter; invariants must be declared and enforced; ad-hoc queries; multi-row transactions | Schema changes need migrations; joins cost at very large scale | System of record by default |
| **Document** | Self-contained one-to-many trees loaded and saved whole (an order with its lines); heterogeneous or externally dictated structure (schema-on-read) | Many-to-many and cross-document references fall back to the application; weaker cross-document constraints | System of record for aggregate-shaped data only, when no cross-aggregate invariant exists |
| **Graph** | Highly interconnected data queried by traversal of arbitrary depth (networks, recommendations, fraud rings) | Fewer tools; aggregations and bulk scans are weaker | System of record or a derived traversal index |
| **Key-value** | Access only by key; very high rates; simple values (sessions, carts, feature flags) | No queries by value; integrity is the application's | Cache (derived) or session store |
| **Wide-column** | Very high write rates partitioned by a known key; queries designed up front per access pattern | Query flexibility; secondary indexes and joins are limited; each query shape is a table | System of record for append-heavy, key-accessed data |
| **Time-series** | Append-mostly measurements by time and series; downsampling and retention windows | Updates and joins are weak | System of record for telemetry; derived for business metrics |
| **Search engine** | Full text, relevance ranking, faceting, fuzzy matching | Not transactional; refresh lag; it can lose or duplicate on reindex | **Derived** — never the system of record |
| **Columnar / warehouse** | Analytic scans and aggregations over many rows and few columns | Point updates and transactional workloads | **Derived** from the OLTP systems (dimensional model) |
| **Log / stream** (Kafka-style) | Ordered, replayable change history; feeding many consumers; event sourcing | Querying the current state needs a derived view; retention and compaction to plan | Integration backbone; the system of record only under deliberate event sourcing |
| **Object store** | Large immutable blobs (documents, media) | No transactions with the database; lifecycle and orphans to manage | Holds bytes; the database holds the metadata and a content hash |

Before adding a specialist store, check whether the relational system of record already covers the need
well enough — PostgreSQL full text and `pg_trgm`, `jsonb` with GIN, range types, partitioning, read
replicas, materialized views. A second store is worth its operational cost only when a stated requirement
exceeds what the first can do.

## 2. Storage-engine families

| Family | Strength | Weakness |
|---|---|---|
| **B-tree, update in place** (most relational engines) | Predictable read latency; one copy of each key; natural range locks for isolation | Write amplification from page splits and WAL; random-key inserts scatter |
| **LSM tree** (RocksDB-based, Cassandra, many key-value stores) | High write throughput; compression | Read and space amplification; compaction competes with foreground work at the tail |
| **Row-oriented** | Whole-row access; OLTP | Wide analytic scans |
| **Column-oriented** | Scans and aggregates over a few columns; compression | Point writes, row reconstruction |

Read, write and space amplification trade against each other: no engine minimizes all three. Benchmark
the real access pattern on representative data before letting engine-family claims decide.

## 3. Replication topologies

| Topology | Buys | Costs |
|---|---|---|
| **Single leader, synchronous follower(s)** | No lost acknowledged writes on failover | Write latency; a slow follower stalls writes (use one synchronous, the rest asynchronous) |
| **Single leader, asynchronous followers** | Read scaling; low write latency | Replication lag; acknowledged writes lost on failover; a promoted lagging follower can reuse keys others already hold |
| **Multi-leader** (multi-region, offline clients) | Local writes per region; survives a region loss | Write conflicts; last-write-wins silently drops data; constraints across leaders can't be enforced |
| **Leaderless, quorum** (`w + r > n`) | Availability under node loss | Quorums don't give linearizability on their own; conflict resolution and read repair to design |

## 4. Consistency vocabulary

| Term | Means | Where it matters |
|---|---|---|
| **ACID consistency** | Application invariants hold (theory §5) | Every transaction |
| **Linearizability** | Every read sees the latest write, as if there were one copy | Uniqueness, leader election, locks, balances |
| **Eventual consistency** | Replicas converge when writes stop — no bound on when | Derived stores, caches, replicas |
| **Read-your-writes** | A user sees their own updates | Save-then-reload flows served by replicas |
| **Monotonic reads** | A user never sees time go backwards | Paging and refreshing across replicas |
| **Consistent prefix** | Readers see writes in the order they happened | Causally related data (a question before its answer) |

Split every staleness discussion into **timeliness** (how stale a reader may see data — heals by waiting)
and **integrity** (no loss or contradiction — needs repair). Derived data may relax the first, never the
second (theory §6).

## 5. Partitioning schemes

| Scheme | Buys | Costs |
|---|---|---|
| **Key range** | Range scans in key order | Hot spots on monotonic keys (time, sequences): every write lands on the last range |
| **Hash of key** | Even load | No range scans across partitions |
| **Compound** (hash on one part, range on the rest) | Even load across entities, ranges within one entity | Queries must know the hashed part |
| **Local secondary indexes** | Cheap writes | Reads on the indexed column scatter to every partition and gather |
| **Global secondary indexes** | Targeted reads | Index updates are cross-partition and usually asynchronous |

Mitigate a known hot key by splitting it (a random suffix) and recombining on read — at the cost of
every read of that key. Choose a rebalancing method (fixed partition count, dynamic splitting) before the
first rebalance is needed.

## 6. Integration mechanisms

| Mechanism | Buys | Costs |
|---|---|---|
| **In-database derivation** (generated column, materialized view, trigger in the same transaction) | Atomic with the source | Load on the source; same-database only |
| **Outbox table** written in the source transaction, relayed to consumers | Atomic with the business change; replayable | A relay process; consumers must be idempotent |
| **Change data capture** from the source's log | No application changes; full history | Log retention and slot management; schema changes flow through to consumers |
| **Scheduled ETL / batch** | Simple; good for warehouses | Staleness of a whole batch interval; reconciliation |
| **Dual writes from application code** | — | Races and partial failure: permanent divergence. Not an option |

A snapshot used to start a new derived store is taken at a known log position and then replayed from
there, so no change is missed between the copy and the stream.
