# Checklist — The Concurrency Checks (CK-1–CK-38)

> The checks this skill runs, grouped in nine families. Each check is a **true/false statement**
> about the change. Take one check at a time and sweep every shared-state site in scope for it
> before moving to the next. When a new class of defect turns up, re-check the sites already done
> (CR23). A family runs when the trigger table in [SKILL.md](SKILL.md#the-trigger-table) hits it,
> so each review reads a short list, not all 38.
>
> Every check gives: what makes it **false** in a diff, the **interleaving** shape to write
> ([interleavings.md](interleavings.md)), when it is **not a finding**, the **fix direction**, the
> **principle**, and a **default severity** for a realistic, reachable case. Severity then moves by
> reachability, blast radius and reversibility, as peer-review grades it. Per-language traps for each
> check are in [languages.md](languages.md).
>
> This list goes deeper than [peer-review's concurrency checklist](../peer-review/heuristics.md#3-concurrency-checklist-lens-g)
> and agrees with it item for item: shared mutable state (CK-1), non-atomic operations (CK-2),
> compound actions (CK-3), lock scope (CK-7, CK-10), lock order (CK-9), non-thread-safe types
> (CK-4), unbounded concurrency (CK-16, CK-18), shutdown (CK-19), the claim (CK-37), and tests
> (CK-36).

## Which families run

| Trigger family hit (SKILL.md) | Checklist families |
|---|---|
| `threads` | S, L, P |
| `locks` | S, L |
| `async` | A, and S for state that lives across a suspension point |
| `shared` | S, C |
| `dbtx`, `dbwrite` | D (`dbwrite` alone: CK-23, CK-24, CK-25) |
| `messaging`, `retries` | M (CK-29–CK-31), and CK-28 for writes paired with a publish |
| `leases` | CK-32 |
| `schedule` | CK-33, CK-19 |
| `lifecycle` | CK-19 |
| `files` | CK-34 |
| `invariants` with any other hit | CK-35, and the tier goes to Deep |
| `tests` (in test files) | CK-36 |
| any hit | CK-37 when the claim mentions speed; CK-38 when the change adds concurrency code |

---

## S — Shared state

### CK-1 — Every shared mutable site has a named guard or is confined
**False when:** a new or changed field, static, module global, singleton, cache, controller or
service-bean instance field, or closure-captured variable is reachable from two actors, and you can't
name the lock, atomic, actor or confinement that protects it at **every** mutation site. Count the
mutation sites (CR5).
**Interleaving:** lost update or check-then-act on that site.
**Not a finding when:** the object is per-request, per-task or a local. It is immutable after a safe
publication. All writers run on one confined thread or event loop and no reader on another.
**Fix:** confine it (a local, a per-request object), copy it, or put it behind one owner with one
atomic API (CR5, CR6).
**Principle:** CR5, CR18 (per-request data in statics, OCR p.183). **Default:** major. Blocker when
the state is money, identity or authorisation.

### CK-2 — No read-modify-write on shared state without an atomic primitive
**False when:** `x++`, `x += n`, `x = x + 1`, `list.append` used as a counter, `map[k] = map[k] + 1`,
`total = total + item` on shared state, or a non-volatile 64-bit write read by another thread (JVM).
**Interleaving:** [2.1 lost update](interleavings.md#21-lost-update-in-memory-read-modify-write).
**Not a finding when:** the whole sequence runs under one lock every writer uses, or uses an atomic
(`AtomicLong.incrementAndGet`, `Interlocked.Increment`, `atomic.AddInt64`, `fetch_add`), or the state
is confined.
**Fix:** an atomic primitive, or a lock around the whole read-compute-write.
**Principle:** CR4. **Default:** major. Blocker when the count is money, stock or a limit.

### CK-3 — No compound action assumes nothing changed between two calls
**False when:** check-then-act or get-then-put across two calls on a shared object: `containsKey`
then `put`, `get` then `put`, `hasNext` then `next`, `size() > 0` then `remove`, `exists` then
`create`, `if cache.get(k) is None: cache.set(k, …)`. Each call being thread-safe doesn't count
(CR6).
**Interleaving:** check-then-act, two actors pass the check.
**Not a finding when:** one lock spans both calls in every caller, or the duplicate act is harmless
and idempotent (state why).
**Fix:** one server-side atomic operation: `putIfAbsent`, `computeIfAbsent`, `GetOrAdd`,
`LoadOrStore`, `setdefault`, `SET NX`, a conditional update, an upsert. Client-side locking only when
the server can't change, through an adapter (CC p.216, p.362–364).
**Principle:** CR6. **Default:** major.

### CK-4 — No type that isn't safe to share is shared
**False when:** a type whose docs don't promise thread safety is held in shared scope and used by
several actors: `SimpleDateFormat`, `HashMap`, `ArrayList`, `Dictionary<,>`, Go maps, `rand.Rand`,
`java.util.Random` used for security, an ORM session or `DbContext`, a DB connection or cursor, a
non-thread-safe HTTP or SDK client, a parser or buffer object (CC p.359).
**Interleaving:** two actors inside the type's methods at once; name the internal state that tears.
**Not a finding when:** the docs promise thread safety (quote them), or each actor gets its own
instance (per request, per thread, from a pool).
**Fix:** a thread-safe replacement (`DateTimeFormatter`, a concurrent collection), one per actor, or
a pool.
**Principle:** CR7. **Default:** major. Go map concurrent write is a process crash: blocker.

### CK-5 — Writes are visible to the readers that need them, and objects are published whole
**False when:** a flag or reference written by one thread is read by another with no
happens-before edge: a plain `boolean running` polled in a loop, a field published before the
constructor finishes, `this` leaked from a constructor to another thread, a lazily built object read
without synchronisation, `Ordering::Relaxed` used to publish data, a busy-wait on a plain variable
(BKS p.113 lists "no busy-waits in place of proper synchronisation").
**Interleaving:** A writes data then flag; B sees flag and stale data (or never sees the flag).
**Not a finding when:** the field is `volatile`/atomic, written and read under the same lock,
`final` and safely published, or the runtime's memory model makes it safe (state which).
**Fix:** `volatile`/atomics with acquire-release, a lock, a latch or a channel instead of a polled
flag.
**Principle:** CR4, CR7. **Default:** major.

### CK-6 — No shared collection is iterated while another actor mutates it
**False when:** a loop over a shared list, map or set while another thread or task adds or removes:
`ConcurrentModificationException`, Go's fatal concurrent map iteration and write, Python's
"dictionary changed size during iteration", or a stale or skipped element with a concurrent
collection's weakly consistent iterator.
**Interleaving:** A iterating, B removes element k, A's next step.
**Not a finding when:** iteration is over a snapshot copy, or under the lock every writer uses, or
the collection's iterator semantics are acceptable here (say why).
**Fix:** iterate a copy, hold the lock, or use a structure built for it.
**Principle:** CR5, CR7. **Default:** major.

---

## L — Locks and deadlock

### CK-7 — Every access to guarded state uses the same lock, on the right object
**False when:** the state is written under lock L in one place and read or written without L (or
under lock M) in another. The lock is created per call (`with threading.Lock():`,
`new Object()` inside the method), per instance when the state is static, or on a value that isn't
stable (a boxed integer, an interned string, a field that is reassigned). Or the critical section is
wider than the shared state needs (CR9).
**Interleaving:** A inside the guarded block, B in the unguarded path on the same field.
**Not a finding when:** all paths are shown to use one lock object (quote them).
**Fix:** one private, final lock per guarded state, documented next to the state (`@GuardedBy`, a
comment), every path through it. Narrow the section to the shared state.
**Principle:** CR9, BKS p.113. **Default:** major.

### CK-8 — Every lock, permit and resource is released on every path
**False when:** an acquire without `finally`/`defer`/`with`/`using`/RAII; an early `return` or
`throw` between acquire and release; `Semaphore.acquire()` paired with a release on the success path
only; a lock released in a callback that may not run.
**Interleaving:** A acquires, throws at step k, never releases; B waits forever.
**Not a finding when:** the language construct releases it (scoped guard, `with`, `using`,
`synchronized`).
**Fix:** the scoped construct, or `try { … } finally { unlock }` (OCR p.183).
**Principle:** CR9, CR14. **Default:** major. Blocker when the path is reachable by a normal error.

### CK-9 — Locks and pooled resources are taken in one global order
**False when:** two code paths take the same two (or more) locks, rows, pool connections or mutexes
in different orders; a lock is taken while holding another, and the order isn't documented; the
second resource's identity comes from the first, so no order can be imposed (CC p.369–370); two pools
(DB and broker, two DB connections) acquired in opposite orders (CC p.366–367).
**Interleaving:** [2.6 deadlock cycle](interleavings.md#26-deadlock-cycle-lock-order), with its
`cycle:` line.
**Not a finding when:** every path is shown to acquire in one order, or only one lock is ever held
at a time.
**Fix:** one global order (by id, by name), lock all needed resources up front in that order, or
redesign so one lock suffices. Each other way of breaking a deadlock condition has a cost: name it
(CR10).
**Principle:** CR10, BKS p.113. **Default:** blocker when both paths run under normal load; major
otherwise.

### CK-10 — No lock is held across I/O, an `await`, a callback, or code you don't own
**False when:** a lock (or a DB row lock, or a transaction) is held during a network call, file I/O,
`sleep`, an `await`, a user-supplied callback or listener, a log call to a remote sink, or a call
into another component that may take its own locks. A `threading.Lock` held across `await`. A
`std::sync::Mutex` guard held across `.await`.
**Interleaving:** A holds L and waits on I/O; B…N queue on L; or the callback takes lock M that a
thread holding M needs L for (cycle).
**Not a finding when:** the call is local, bounded and lock-free, and that's stated.
**Fix:** copy what you need under the lock, release, then do the slow call. Use an async-aware lock
only when the critical section truly must span the await.
**Principle:** CR9, CR10. **Default:** major.

### CK-11 — Waiting and signalling follow the execution model's rules
**False when:** `wait()` not in a loop re-checking its condition (spurious wakeups, stolen
conditions); `notify` where several waiter kinds share a monitor; a signal sent before the waiter
waits (lost wakeup); a bounded queue that signals only "not empty" and not "not full"; a
readers-writers lock that starves writers under steady reads; a hand-rolled queue or pool where the
library has one (CR7, CR12).
**Interleaving:** B signals at step 1, A starts waiting at step 2 and never wakes.
**Not a finding when:** it uses a library primitive with these semantics built in (a `BlockingQueue`,
a channel, `asyncio.Queue`, `Condition.wait_for(predicate)`).
**Fix:** the library primitive; otherwise `while (!cond) wait()` and `notifyAll`.
**Principle:** CR12, CR7. **Default:** major.

---

## A — Async

### CK-12 — Nothing blocks the event loop or the async runtime's threads
**False when:** inside `async` code: `time.sleep`, `requests`, a synchronous DB driver, sync file
I/O, `fs.readFileSync` on a request path, `crypto.pbkdf2Sync`, a large `JSON.parse` or CPU loop;
`.Result`/`.Wait()`/`GetAwaiter().GetResult()` in .NET; `runBlocking` inside a coroutine;
`std::thread::sleep` or blocking I/O in a Tokio task; `Thread.sleep` in a reactive pipeline.
**Interleaving:** A blocks the loop for t; every other request on that loop stalls for t; or (.NET
with a synchronisation context) A blocks waiting for a continuation that needs the thread A holds.
**Not a finding when:** the call is moved off the loop (`run_in_executor`/`to_thread`,
`spawn_blocking`, `Dispatchers.IO`, a worker thread) or is provably short.
**Fix:** the async API, or offload the blocking call explicitly.
**Principle:** CR9 (holding the shared loop), CR13. **Default:** major. Blocker for a sync-over-async
deadlock on a request path.

### CK-13 — Every task is awaited, owned, or has its errors routed somewhere
**False when:** a missing `await`; a floating promise; `asyncio.create_task(...)` whose result isn't
kept (the loop keeps only a weak reference, so the task can be garbage-collected mid-run); `async
void`; `go func()` with no error path and no `recover` (a panic kills the process); `forEach(async
…)`; `Task.Run` fire-and-forget in a request handler that then uses request-scoped objects; an
`.then()` chain with no `.catch`.
**Interleaving:** A starts task T and returns; T fails at step k; nobody sees it, or T runs after the
request scope (DB session, transaction) is disposed.
**Not a finding when:** the task is held by a supervisor (task group, `errgroup`, a hosted background
queue) that logs or propagates its errors, and fire-and-forget is the intent, stated.
**Fix:** await it; or hand it to an owned scope (`TaskGroup`, structured concurrency, a background
service) that reports failure.
**Principle:** CR11, CR14. **Default:** major.

### CK-14 — No check-then-act or read-modify-write spans a suspension point
**False when:** state is read, then `await`, then written based on the earlier read: in-memory maps,
an object loaded from a store, a "lock" flag set after an await. Single-threaded runtimes race here
too.
**Interleaving:** [2.5 across await](interleavings.md#25-check-then-act-across-an-await-single-threaded-still-a-race).
**Not a finding when:** nothing between the read and the write yields, or an async lock spans it and
every path takes that lock, or the store does the check atomically.
**Fix:** move the check into the store (conditional write), or recheck after the await, or serialise
per key (an async lock map, a single-writer queue).
**Principle:** CR6, CR4. **Default:** major. Blocker on money or limits (CK-35).

### CK-15 — Fan-out handles partial failure: siblings, side effects, and what's left half-done
**False when:** `Promise.all` rejects on the first failure while the other promises keep running
and keep their side effects; `asyncio.gather` without `return_exceptions` propagates the first error
and leaves the rest running; `Task.WhenAll` surfaces one exception and hides the rest; `errgroup`
without context leaves siblings running; nothing compensates for the children that succeeded.
**Interleaving:** child 1 fails at step 2; children 2–3 complete writes at steps 3–4; the caller
reports failure and retries all three.
**Not a finding when:** the children are read-only, or idempotent under the caller's retry, or a
structured scope cancels siblings and the side effects are compensated.
**Fix:** `allSettled`/`return_exceptions`/`TaskGroup`/`errgroup.WithContext`, and a decision per
child: cancel, compensate or keep.
**Principle:** CR14, CR20. **Default:** major.

### CK-16 — Fan-out is bounded
**False when:** one task, goroutine, thread or request per input element with no limit:
`Promise.all(items.map(fetch))` over a user-sized list, `go handle(x)` per message, `new Thread` per
request, `asyncio.gather(*[... for x in rows])`. The downstream pool (DB connections, provider rate
limit, file descriptors) is the real bound and the code ignores it.
**Interleaving:** not a schedule; state the load: n inputs → n concurrent calls against a pool of p.
**Not a finding when:** the input size is bounded and small by construction (quote the bound).
**Fix:** a semaphore or limiter (`p-limit`, `asyncio.Semaphore`, a worker pool, `buffer_unordered(k)`),
sized against the downstream bound.
**Principle:** CR13. **Default:** major.

### CK-17 — Cancellation and timeouts stop the work and leave state consistent
**False when:** a timeout that abandons the result but not the work (`Promise.race` with a timer;
`wait_for` around a shielded call); cancellation caught and swallowed (`except BaseException`,
`catch (OperationCanceledException)` that continues, catching `CancellationException` in Kotlin);
`context.Context`/`CancellationToken`/`AbortSignal` accepted but not passed down; cleanup that
`await`s after cancellation without shielding; a Rust future dropped at an `.await` in `select!`
mid-way through a non-cancel-safe operation.
**Interleaving:** A times out at step 2 and the caller retries (B); A's original work completes at
step 4; both writes land.
**Not a finding when:** the cancellation reaches the leaf call and the operation is atomic or
idempotent.
**Fix:** propagate the token to the leaf, make cleanup cancel-safe (`finally`, shielded cleanup), and
make the retried work idempotent.
**Principle:** CR14, CR20. **Default:** major.

---

## P — Pools, executors and lifecycle

### CK-18 — Pools and queues are sized, bounded and not starved by their own tasks
**False when:** an executor with an unbounded queue (`Executors.newFixedThreadPool` has one) under
unbounded input; an unbounded thread pool (`newCachedThreadPool`); a task that submits to and waits
on the same bounded pool (thread-starvation deadlock); blocking work on a shared pool meant for CPU
work (the common `ForkJoinPool`, `parallelStream`, `CompletableFuture.supplyAsync` without an
executor); no rejection policy; a DB pool smaller than the worker count that holds connections.
**Interleaving:** pool of p; p tasks each submit a child and wait; the children queue behind them
forever.
**Not a finding when:** the queue bound, the rejection policy and the pool's use are stated and fit.
**Fix:** a dedicated, bounded pool per kind of work, with a rejection policy; no waiting on your own
pool.
**Principle:** CR13, CR7. **Default:** major.

### CK-19 — Every worker, consumer and scheduler stops cleanly, and work in flight survives
**False when:** a new loop, consumer, thread or timer with no stop path; SIGTERM not handled (or
handled only in one thread); the process exits while work is in flight; a consumer acknowledges
before the work is durable; a parent waits forever on a child that can block; a producer-consumer
pair where one side can stop and leave the other blocked; daemon threads killed mid-write; the grace
period shorter than the longest unit of work (CC p.217).
**Interleaving:** SIGTERM at step k during a write; the half-written state, the unacked or lost
message.
**Not a finding when:** the framework owns the lifecycle and the code registers with it (a hosted
service's `StopAsync`, a shutdown hook that drains), and in-flight work is idempotent on restart.
**Fix:** a stop signal checked by every loop, drain then close, ack after commit, a grace period
longer than the work, idempotent restart.
**Principle:** CR14. **Default:** major.

### CK-20 — No thread-local or async context leaks between units of work
**False when:** `ThreadLocal`, MDC, `AsyncLocal`, `contextvars`, or a request-scoped holder set on a
pooled thread and not cleared, so the next request on that thread sees the previous user's tenant,
identity, locale or transaction; context lost across an executor hop, so code falls back to a
default identity.
**Interleaving:** request A sets tenant=1 on thread t; A ends without clearing; request B runs on t,
reads tenant=1.
**Not a finding when:** set and cleared in `try/finally` (or the framework scopes it), and propagated
explicitly across hops.
**Fix:** scope it (`try/finally`, a scoped value, framework-managed context), propagate explicitly.
**Principle:** CR5, CR18 (OCR p.209, security information in shared globals). **Default:** major.
Blocker and type `security` when identity or tenant leaks.

---

## C — Lazy initialisation and caches

### CK-21 — Lazy initialisation runs once and publishes a complete object
**False when:** `if instance is None: instance = build()` reachable from two actors; double-checked
locking without `volatile` (Java) or with a non-atomic flag; `ConcurrentDictionary.GetOrAdd` or
`computeIfAbsent` whose factory has side effects (the .NET factory can run more than once);
`computeIfAbsent` whose function touches the same map; module-level init assumed to run once across
worker processes.
**Interleaving:** A and B both see `null`; both build; one instance is lost, or the side effect
happens twice; or B sees A's reference before A's constructor finished (CK-5).
**Not a finding when:** the runtime's once-primitive is used (`sync.Once`, `OnceLock`, `Lazy<T>`
with thread-safe mode, Kotlin `by lazy` default, a holder-class idiom, `functools.cache` on an
idempotent builder) and building twice would be harmless anyway.
**Fix:** the once-primitive; side-effect-free factories.
**Principle:** CR4, CR7. **Default:** minor when building twice is harmless; major when it has
effects.

### CK-22 — A cache can't stampede, and can't be left holding a stale value
**False when:** on expiry or a miss, every concurrent request recomputes (stampede against the DB);
the write path updates the DB and the cache in an order that lets a slower reader put back the old
value (read old from DB → writer updates DB → writer deletes cache → reader sets old into cache);
the cache is per process and the change assumes it's shared.
**Interleaving:** the four-step stale-set above, with the cache and DB values per step.
**Not a finding when:** staleness up to the TTL is acceptable here (say so); single-flight or a lock
per key guards recomputation.
**Fix:** single-flight per key, early or probabilistic refresh, delete-after-commit with a short TTL,
versioned cache entries.
**Principle:** CR6, CR22. **Default:** minor for staleness within a stated TTL; major for a stampede
on a hot key or a permanent stale value.

---

## D — Database

### CK-23 — No read-modify-write through the ORM or SQL loses an update
**False when:** load an entity, change a field from its loaded value, save, with no lock, version or
conditional `WHERE`: `obj.count += 1; obj.save()`, `entity.setBalance(entity.getBalance() - x)`,
`UPDATE t SET n = :computed` where `:computed` was read earlier. A full-row save that also overwrites
columns this code didn't change (the default in several ORMs) is a second lost update.
**Interleaving:** [2.2 ORM lost update](interleavings.md#22-lost-update-through-an-orm-get-modify-save).
**Not a finding when:** the update is relative and atomic in SQL (`SET n = n + 1`, an `F()`
expression), or it's under `SELECT … FOR UPDATE` in the same transaction, or a version column is
checked (CK-27), or the isolation level in force rejects the second write and the error is handled.
**Fix:** an atomic relative update or a conditional update with a row-count check (CR6); else a row
lock; else optimistic locking (CR8). Save only the changed columns.
**Principle:** CR19, CR4. **Default:** blocker for money, stock and counters others rely on; major
otherwise.

### CK-24 — No check-then-insert relies on a check; a constraint is the lock
**False when:** `exists()` or `SELECT` then `INSERT`; `get_or_create`/`findOrCreate`/`firstOrCreate`
without a unique constraint behind it; `SELECT MAX(id) + 1`; "at most N rows" enforced by `COUNT`
then insert; an application-level upsert (`find` then `insert` or `update`); `MERGE` assumed atomic
against concurrent inserts.
**Interleaving:** [2.3 insert race](interleavings.md#23-check-then-act-on-a-database-row-insert-race).
**Not a finding when:** a unique (or exclusion, or check) constraint enforces the invariant and the
violation is caught and mapped, or a native atomic upsert (`INSERT … ON CONFLICT`, `ON DUPLICATE KEY`)
does it.
**Fix:** the constraint first, then the native upsert or insert-and-catch. For "at most N", lock the
parent row or use a counter row with a conditional update.
**Principle:** CR19, CR6. **Default:** major. Blocker when the duplicate is money, an account, or a
security-relevant identity (CK-35).

### CK-25 — The code's correctness doesn't depend on an isolation level it doesn't have
**False when:** the code reads, decides and writes in one transaction and assumes no one else wrote
in between, under the default level (READ COMMITTED for PostgreSQL, SQL Server and Oracle; REPEATABLE
READ for MySQL InnoDB); write skew under snapshot isolation (two transactions each check "someone
else is on call", each removes themselves); a phantom (a range check, then an insert into the range);
SERIALIZABLE set but serialization failures not retried.
**Interleaving:** two transactions, BEGIN to COMMIT, with the isolation level on the actors line.
**Not a finding when:** the level actually in force (connection config, quoted) prevents this anomaly,
and the failure it raises is retried.
**Fix:** a conditional write or a lock on the decided-on rows (or a parent row); SERIALIZABLE with a
retry loop; a constraint that encodes the invariant.
**Principle:** CR19. **Default:** major. `topology_question` when the configured level isn't in the
repo.

### CK-26 — Row locks lock what they mean to, inside a transaction, in a fixed order
**False when:** `SELECT … FOR UPDATE` (or `select_for_update`, `with_for_update`, `PESSIMISTIC_WRITE`)
outside a transaction or in autocommit, so the lock ends with the statement; a framework transaction
that doesn't start (Spring `@Transactional` on a self-invoked or private method); locking rows that
don't exist yet (no row, no lock); rows locked in request order rather than id order (CK-9); a job
queue that polls without `SKIP LOCKED`, so workers collide; no `lock_timeout`/`NOWAIT` where waiting
is wrong.
**Interleaving:** the lost update the lock was meant to prevent, showing the lock released at
statement end; or the deadlock cycle.
**Not a finding when:** the transaction boundary is shown to enclose the lock and the write.
**Fix:** put the lock and the write in one transaction; order by id; `SKIP LOCKED` for queues; lock a
parent row for inserts.
**Principle:** CR19, CR10. **Default:** major.

### CK-27 — Optimistic locking is checked, not just stored
**False when:** a version or timestamp column exists but the update doesn't include it in `WHERE`, or
the affected row count isn't checked; the version isn't incremented; bulk updates or raw SQL bypass
it; the conflict exception is caught and ignored, or retried by re-applying stale input; the version
isn't round-tripped to the client for user edits.
**Interleaving:** A and B read v=3; A writes, v=4; B writes with no `AND version=3`; B's write wins.
**Not a finding when:** the framework adds the check (`@Version`, `[ConcurrencyCheck]`,
`IsRowVersion`) on this path, and the conflict is surfaced or retried from a fresh read.
**Fix:** `WHERE id = ? AND version = ?`, check rows affected = 1, retry from a fresh read or return a
conflict.
**Principle:** CR8, CR19. **Default:** major.

### CK-28 — Transactions are short and contain no side effects they can't roll back
**False when:** an HTTP call, an email, a file write, or a message publish inside a transaction that
can still roll back (the effect happens, the data doesn't); a DB write and a broker publish as two
separate steps (dual write: a crash between them loses one); a transaction held open across user
think-time, a remote call or an `await` on something slow (locks held, pool exhausted); the
transaction bound to a thread or context that an async hop leaves.
**Interleaving:** A commits the order, crashes before publish; no event is ever sent. Or A publishes,
then the transaction rolls back; consumers act on an order that doesn't exist.
**Not a finding when:** an outbox table written in the same transaction and relayed afterwards, or
publish after commit with an idempotent consumer and a reconciliation.
**Fix:** transactional outbox; side effects after commit; short transactions.
**Principle:** CR19, CR20, CR9. **Default:** major.

---

## M — Messages, retries and distributed coordination

### CK-29 — Every handler that can see a message, request or job twice is idempotent
**False when:** a consumer, webhook handler, retried HTTP call, or job whose effect is applied again
on a duplicate: a charge, an email, an increment, an append. A dedupe check done in a separate step
from the effect. A client retry on a non-idempotent POST without an idempotency key. Any retry
policy (`retry`, `tenacity`, Polly, resilience4j) wrapped around a non-idempotent call.
**Interleaving:** [2.7 double delivery](interleavings.md#27-double-delivered-message-at-least-once).
**Not a finding when:** the effect is naturally idempotent (a set to an absolute value, an upsert
keyed by the message id), or a dedupe key is recorded atomically with the effect (same transaction,
unique constraint), or the downstream honours an idempotency key.
**Fix:** an idempotency key per logical operation, stored with the effect under a unique constraint;
pass keys to providers that support them.
**Principle:** CR20. **Default:** blocker for money and external effects; major otherwise.

### CK-30 — No consumer depends on an order the transport doesn't guarantee
**False when:** the code assumes events for one entity arrive in order across partitions, queues,
parallel consumers, retries or a dead-letter replay; a "latest wins" write with no version or
timestamp comparison; a create and an update for one entity on different topics.
**Interleaving:** `send v1 ; send v2 ; deliver v2 (B) ; deliver v1 (A, after retry) ! state=v1`.
**Not a finding when:** one partition key per entity with a single consumer per partition and no
reordering retries, or the write compares versions (`WHERE version < :incoming`).
**Fix:** version-compare on write; partition by entity key; make handlers commutative.
**Principle:** CR20. **Default:** major.

### CK-31 — Acknowledge or commit the offset after the effect is durable, not before
**False when:** ack or auto-commit before processing (a crash loses the message); ack after
processing with no idempotency (duplicates, CK-29); offsets committed for a batch processed
asynchronously, so a crash skips the unfinished part; a visibility timeout or `max.poll.interval`
shorter than the processing time, so the broker redelivers to a second consumer while the first is
still working.
**Interleaving:** A receives m, processing outlives the visibility timeout, B receives m, both
finish.
**Not a finding when:** ack-after-commit plus idempotent handling, and the timeout is longer than the
work (or extended while it runs).
**Fix:** ack after commit; idempotent handler; extend visibility or heartbeat during long work.
**Principle:** CR20, CR14. **Default:** major.

### CK-32 — A distributed lock or lease has an expiry, a fencing token, and owner-checked release
**False when:** `SETNX` then `EXPIRE` as two commands (a crash between them leaves a lock that never
expires); no expiry at all; an expiry shorter than the work with no renewal; release with a plain
`DEL` that can free someone else's lock; no fencing token checked by the protected resource; the
lock guards an in-process resource that a second replica doesn't share; a database advisory lock
taken on one connection and the work done on another.
**Interleaving:** [2.8 lease expiry](interleavings.md#28-lease-expiry-without-a-fencing-token).
**Not a finding when:** a single atomic acquire with expiry (`SET k v NX PX t`), renewal while working,
compare-and-delete release, and either a fencing check at the resource or work that is idempotent
when run twice.
**Fix:** atomic acquire, renewal, owner-checked release, a fencing token; or replace the lock with a
database constraint or a conditional write.
**Principle:** CR21. **Default:** major. Blocker when two holders corrupt money or data.

### CK-33 — A scheduled job runs once per period, and runs don't overlap unless that's safe
**False when:** a cron, `@Scheduled`, `setInterval`, `Ticker`, APScheduler or Celery beat job in app
code that runs on every replica or worker process; a run that can outlast its interval and overlaps
the next (`scheduleAtFixedRate`, `setInterval` with an async body, a Kubernetes CronJob with the
default `concurrencyPolicy: Allow`); a missed run caught up twice after a restart.
**Interleaving:** `pod a run t0 ; pod b run t0 ; both send invoice for period P !`.
**Not a finding when:** a scheduler lock (ShedLock, Quartz clustered, a leader election, a DB row
claim with `SKIP LOCKED`) or a single-instance runner enforced in config, and the job is idempotent
for its period.
**Fix:** run it in one place (a CronJob with `concurrencyPolicy: Forbid`, a leader), claim the
period atomically, make the job idempotent per period.
**Principle:** CR22, CR20. **Default:** major. `topology_question`: replicas and processes per
replica.

---

## F — Files and security-relevant races

### CK-34 — No file operation checks, then acts on, a path another actor can change
**False when:** `exists`/`access`/`stat` then `open`/`create`/`delete`; writing a file in place that
readers may read mid-write; predictable temp file names (`mktemp`, `tempnam`); permission or
ownership checked on a path, then the path used; a lock file created without `O_EXCL`.
**Interleaving:** [2.4 file TOCTOU](interleavings.md#24-check-then-act-on-a-file-toctou).
**Not a finding when:** the operation is atomic (`O_CREAT|O_EXCL`, `open(…, "x")`, write-temp then
rename on one filesystem, `mkstemp`), or the directory is private to one actor.
**Fix:** make check and act one atomic call; write-then-rename; operate on file descriptors, not
re-resolved paths.
**Principle:** CR6, CR18. **Default:** major. Type `security` when the path or directory is
attacker-influenced.

### CK-35 — No limit, balance, one-time token or uniqueness check can be raced on purpose
**False when:** any check-then-act from CK-3, CK-14, CK-23 or CK-24 guards money (balance, refund,
withdrawal, transfer), a quota or rate limit, stock or seats, a coupon, voucher, invite or gift
card, a one-time token (password reset, OTP, email verification), or an identity's uniqueness. An
attacker sends the same request many times at once and picks the interleaving (CR18).
**Interleaving:** n parallel requests, all pass the check before any write; the result is n effects
for one allowance.
**Not a finding when:** the check and the effect are one atomic operation in the store (a conditional
update with a row-count check, a unique constraint on the redemption, a token consumed with
`UPDATE … WHERE used = false`).
**Fix:** as CK-23/CK-24, at the store; never in application memory across instances.
**Principle:** CR18, CR6, CR19. **Default:** blocker, type `security`; escalate to appsec.

---

## T — Tests, claims and structure

### CK-36 — Tests near concurrent code can fail, and flakiness is treated as a finding
**False when:** a test of concurrent behaviour runs one actor; `sleep` used to order actors; a
flaky, retried or quarantined test near the changed concurrent code (CR2); the new concurrent path
has no test at all; a concurrency test's only evidence is one green run (CR3); the test can't vary
actor count or iterations (CC p.218–219).
**Interleaving:** for a missing test, the interleaving the test should force; for a sleep-ordered
test, the schedule where the sleep isn't long enough.
**Not a finding when:** a forced-schedule test or a stress test with more actors than cores exists
and asserts the invariant.
**Fix:** a forced-schedule test at the gap ([interleavings.md](interleavings.md#41-forced-schedule-deterministic-first-choice)),
then a tunable stress test; latches instead of sleeps; un-quarantine and investigate the flaky test.
**Principle:** CR2, CR3, CR16. **Default:** major for no test on a new concurrent invariant; minor for
sleep-ordering in an otherwise sound test. Type `test`.

### CK-37 — A performance claim for added concurrency matches what the work waits on
**False when:** the change claims speed from threads, tasks or processes, and the work is CPU-bound
(in CPython with the GIL, CPU-bound threads don't run in parallel); or the "parallel" calls contend
on one lock, connection or rate limit.
**Interleaving:** not a schedule; state the work profile (I/O wait vs CPU) and the shared bottleneck.
**Not a finding when:** the work waits on I/O, and the bottleneck isn't shared.
**Fix:** measure; use processes or a native pool for CPU work; remove the shared bottleneck, or drop
the concurrency.
**Principle:** CR15. **Default:** minor; major when the added concurrency also adds a race. Type
`evolvability` or `bug`.

### CK-38 — Concurrency code lives in a few places and can be tuned and tested on its own
**False when:** thread or task creation, locking, retry and scheduling logic is spread through
business logic, so no single place shows how the work is scheduled; thread counts and pool sizes are
hard-coded where they need tuning; the threaded logic can't run with one thread or with a test
double (CC p.212, p.218–219).
**Interleaving:** not a schedule; state the concrete cost: which change has to touch how many places,
or which test can't be written.
**Not a finding when:** the concurrency is a single, local, obvious construct.
**Fix:** extract the scheduling into one component (an executor wrapper, a worker class), inject it,
make counts configurable. Hand the restructuring to refactor-review.
**Principle:** CR11, CR16. **Default:** minor. Type `evolvability`.
