# Languages — Per-Runtime Traps and the Tools That Settle a Claim

> What each runtime makes easy to get wrong, keyed to the checks in [checklist.md](checklist.md), and
> the tools a verifier uses to turn a PLAUSIBLE interleaving into a CONFIRMED one.
>
> **Everything in this file is practical knowledge (not from the sources)**, except where a line cites
> Clean Code. The sources teach the principles with Java threads. The runtime specifics here are the
> current behaviour of each platform as commonly documented. Versions matter: when a trap depends on a
> version (Go 1.22 loop variables, JDK 24 virtual-thread pinning, Python's free-threaded build), check
> the version the project pins before you cite it.

---

## Java and Kotlin

| Trap | Check |
|---|---|
| `count++`, `+=` on a shared field; non-volatile `long`/`double` writes may tear (CC p.355–357) | CK-2 |
| `volatile` gives visibility, not atomicity: `volatile int n; n++` still loses updates | CK-2, CK-5 |
| Double-checked locking without `volatile` publishes a half-built object | CK-21, CK-5 |
| `HashMap`, `ArrayList`, `SimpleDateFormat`, `Calendar`, JDBC `Connection`, JPA `EntityManager` shared across threads (CC p.359) | CK-4 |
| `Collections.synchronizedList`/`Map` still needs manual locking to iterate; `Hashtable`/`Vector` compound calls still race (CC p.359–360) | CK-3, CK-6 |
| `ConcurrentHashMap`: `containsKey`+`put` races; `computeIfAbsent` is atomic per key, but its function must be short and must not modify the map | CK-3, CK-21 |
| Spring singleton beans (`@Service`, `@Controller`) with mutable instance fields are shared by every request | CK-1 |
| `synchronized` on a boxed `Integer`, an interned `String`, or a field that gets reassigned; a lock per instance guarding static state | CK-7 |
| `Lock.lock()` without `try/finally unlock()` | CK-8 |
| `Executors.newFixedThreadPool` has an unbounded queue; `newCachedThreadPool` has unbounded threads | CK-18 |
| `parallelStream()` and `CompletableFuture.supplyAsync` without an executor run on the common `ForkJoinPool`; blocking there starves every other user | CK-18, CK-12 |
| `ThreadLocal`/MDC on pooled threads not cleared in `finally` | CK-20 |
| Virtual threads (JDK 21+): blocking inside `synchronized` pins the carrier thread before JDK 24; `ThreadLocal` per virtual thread multiplies memory | CK-12, CK-18 |
| `@Transactional` on a private or self-invoked method doesn't start a transaction (proxy-based AOP), so `FOR UPDATE` inside it locks for one statement | CK-26 |
| `@Async` has the same self-invocation gap; `@Scheduled` runs in every instance | CK-13, CK-33 |
| JPA/Hibernate: updates write every column by default (`@DynamicUpdate` changes that); `@Version` checked only through the entity path, not bulk JPQL updates | CK-23, CK-27 |
| Kotlin coroutines: `GlobalScope.launch` is fire-and-forget; `runBlocking` inside a coroutine; catching `CancellationException` (or `Exception`, which includes it) swallows cancellation; `kotlinx.coroutines.sync.Mutex` is not reentrant; blocking calls on `Dispatchers.Default` | CK-13, CK-17, CK-12 |

## Go

| Trap | Check |
|---|---|
| Maps aren't safe for concurrent use; a concurrent write is a fatal runtime error, not a recoverable panic | CK-4 |
| Any data race on a slice, string, interface or map value is undefined behaviour, including torn multi-word values | CK-2, CK-5 |
| Copying a struct that contains a `sync.Mutex` copies the lock (`go vet` copylocks) | CK-7 |
| `wg.Add(1)` inside the goroutine instead of before `go`; `wg.Wait()` can return early | CK-13 |
| A panic in a goroutine kills the process; `recover` in the parent doesn't catch it | CK-13 |
| Goroutine leaks: a send on an unbuffered channel whose receiver returned on timeout; a loop that never sees `ctx.Done()` | CK-17, CK-19 |
| Closing a channel twice, or sending on a closed one, panics; only the sender should close | CK-11, CK-19 |
| `context.Context` accepted but not passed to the DB or HTTP call | CK-17 |
| `errgroup.Group` without `WithContext` doesn't cancel siblings on the first error | CK-15 |
| A goroutine per item with no bound | CK-16 |
| Loop variable capture in `go func(){ use(v) }()` was shared before Go 1.22 (per-iteration since) | CK-1 |
| `math/rand.Rand` values (not the package functions) aren't safe to share | CK-4 |
| `signal.NotifyContext` or `signal.Notify` needed for SIGTERM; `http.Server.Shutdown` drains, `Close` doesn't | CK-19 |

## Python

| Trap | Check |
|---|---|
| **The GIL myth.** The GIL makes single bytecodes atomic, not statements: `x += 1`, `d[k] = d.get(k, 0) + 1`, `if k not in d: d[k] = …` all race between threads | CK-2, CK-3 |
| The free-threaded build (PEP 703, `python3.13t` and later) removes the GIL; code relying on incidental GIL serialisation breaks further | CK-2, CK-4 |
| The GIL and every `threading.Lock` are per process. Gunicorn/uWSGI workers, Celery workers and replicas each have their own module globals, caches and locks | CK-1, CK-21, CK-33 |
| CPU-bound threads don't run in parallel under the GIL; "faster with threads" holds only for I/O | CK-37 |
| asyncio: `time.sleep`, `requests`, sync DB drivers and CPU work inside `async def` stall the loop; `asyncio.to_thread` / `run_in_executor` move them off | CK-12 |
| `asyncio.create_task()` without keeping a reference: the loop keeps only a weak reference | CK-13 |
| A coroutine called without `await` never runs ("coroutine … was never awaited") | CK-13 |
| `asyncio.gather` without `return_exceptions=True` raises the first error and leaves the others running; `TaskGroup` (3.11+) cancels siblings | CK-15 |
| `CancelledError` is a `BaseException` (3.8+); a bare `except:` or `except BaseException` swallows cancellation | CK-17 |
| `asyncio.Lock` isn't thread-safe; a `threading.Lock` held across `await` blocks the loop | CK-10, CK-7 |
| Django: `obj.save()` writes every field unless `update_fields`; use `F("n") + 1` or `.update()` for atomic increments; `select_for_update()` must run inside `transaction.atomic()` (it raises in autocommit); `get_or_create` needs a unique constraint behind it | CK-23, CK-24, CK-26 |
| SQLAlchemy `Session` isn't thread-safe; one per request or thread | CK-4 |
| Celery: tasks ack early by default (`acks_late=False`, a crash loses the task); with `acks_late=True` they can run twice; Redis/SQS visibility timeout shorter than the task redelivers it; run one beat scheduler only | CK-29, CK-31, CK-33 |
| Signal handlers run only in the main thread; a worker thread never sees SIGTERM | CK-19 |

## JavaScript, TypeScript and Node

| Trap | Check |
|---|---|
| **The single-thread myth.** One event loop prevents data races between lines, not races across `await`: read, `await`, write is check-then-act | CK-14 |
| Floating promises; `array.forEach(async …)` doesn't wait; an `async` Express 4 handler's rejection isn't routed to error middleware (Express 5 does route it) | CK-13 |
| Unhandled rejections terminate the process by default since Node 15 | CK-13 |
| `Promise.all` rejects on the first failure while the rest keep running; `Promise.allSettled` collects all | CK-15 |
| `Promise.race` with a timer abandons the result, not the work; pass an `AbortSignal` to cancel | CK-17 |
| `Promise.all(items.map(call))` over unbounded input; use a limiter such as `p-limit` | CK-16 |
| `fs.*Sync`, `crypto.*Sync`, `zlib.*Sync`, big `JSON.parse`/`stringify`, and CPU loops block every request on the loop | CK-12 |
| Module-level `let`/`Map` in a server is shared by every request (and by warm serverless invocations) | CK-1 |
| `setInterval(async () => …)` overlaps when a run outlasts the interval | CK-33 |
| `cluster`, PM2 and replicas: in-memory caches, locks and timers are per process | CK-22, CK-33 |
| `worker_threads` with `SharedArrayBuffer` need `Atomics` for every shared access | CK-2, CK-5 |
| `process.on('SIGTERM')` needed to drain; a container whose PID 1 is `npm` may not forward the signal | CK-19 |

## C# and .NET

| Trap | Check |
|---|---|
| `async void` (outside event handlers): exceptions can't be awaited and crash the process; `Parallel.ForEach` with an async lambda is `async void` | CK-13 |
| `.Result`, `.Wait()`, `GetAwaiter().GetResult()` deadlock under a synchronisation context (WPF, WinForms, classic ASP.NET) and starve the pool in ASP.NET Core | CK-12 |
| `lock` can't contain `await` (compile error), so code switches to `SemaphoreSlim`; its `Release()` must be in `finally` | CK-8, CK-10 |
| `Dictionary`, `List`, `Random` instances aren't thread-safe (`Random.Shared`, .NET 6+, is) | CK-4 |
| `ConcurrentDictionary.GetOrAdd`/`AddOrUpdate` may run the factory more than once; wrap the value in `Lazy<T>` when it has effects | CK-21, CK-3 |
| `DbContext` isn't thread-safe; two concurrent operations throw; `Task.Run` from a request with the scoped `DbContext` outlives the scope | CK-4, CK-13 |
| EF Core: concurrency tokens (`[ConcurrencyCheck]`, `[Timestamp]`/`IsRowVersion`) raise `DbUpdateConcurrencyException`, which must be handled; `ExecuteUpdate` bypasses change tracking | CK-27 |
| `static` fields in ASP.NET hold data across requests (OCR p.183, p.209) | CK-1, CK-20 |
| `CancellationToken` accepted but not passed to the I/O call; `BackgroundService.ExecuteAsync` ignoring `stoppingToken`; `StopAsync` timeouts shorter than the work | CK-17, CK-19 |
| `System.Threading.Timer` callbacks overlap when one runs long | CK-33 |
| `AsyncLocal` and `IHttpContextAccessor` used from background work after the request ends | CK-20 |

## Rust

| Trap | Check |
|---|---|
| `Send`/`Sync` rule out data races in safe code. They don't rule out deadlocks, check-then-act across two lock acquisitions (`if m.lock().contains(k) { … m.lock().insert(k) }`), or races in the database | CK-3, CK-9 |
| `std::sync::Mutex` isn't reentrant: locking it twice on one thread deadlocks or panics | CK-9 |
| A `std::sync::MutexGuard` held across `.await` (clippy `await_holding_lock`); use a scoped block, or `tokio::sync::Mutex` only when the section must span the await | CK-10 |
| Blocking (`std::thread::sleep`, sync I/O, heavy CPU) inside a Tokio task; use `spawn_blocking` | CK-12 |
| A dropped `JoinHandle` detaches the task; its panic or error is lost unless joined | CK-13 |
| Cancellation safety: a future dropped at an `.await` inside `select!` mid-operation; check each method's "cancel safety" docs | CK-17 |
| `Ordering::Relaxed` used to publish data guarded by a flag; publishing needs `Release`/`Acquire` | CK-5 |
| `unsafe impl Send`/`Sync` asserts what the compiler couldn't check: read it as a claim | CK-4 |
| Mutex poisoning after a panic: `lock().unwrap()` turns one panic into many | CK-8 |

## SQL and databases

| Trap | Check |
|---|---|
| Default isolation: PostgreSQL, SQL Server and Oracle READ COMMITTED; MySQL InnoDB REPEATABLE READ. None of these makes a read-then-write in the application atomic | CK-25, CK-23 |
| PostgreSQL REPEATABLE READ raises a serialization error on a concurrent update of the same row, which the code must retry; MySQL REPEATABLE READ doesn't (a plain `SELECT` reads the snapshot, the `UPDATE` sees the current row), so the lost update goes through | CK-25 |
| Snapshot isolation allows write skew (two transactions each check a condition over rows the other changes); PostgreSQL SERIALIZABLE catches it and raises errors that must be retried | CK-25 |
| SQL Server READ COMMITTED uses locking reads unless `READ_COMMITTED_SNAPSHOT` is on (it is on by default in Azure SQL Database); behaviour differs between the two | CK-25 |
| `SELECT … FOR UPDATE` outside an explicit transaction locks for one statement; it locks only rows that exist | CK-26, CK-24 |
| MySQL locking reads take gap and next-key locks under REPEATABLE READ, so concurrent inserts into a range can deadlock | CK-9, CK-26 |
| Lock rows in a fixed order (`ORDER BY id … FOR UPDATE`); the database aborts one side of a deadlock, and the caller must retry it | CK-9 |
| `SKIP LOCKED` for job-queue polling; `NOWAIT` or `lock_timeout` where waiting is wrong | CK-26 |
| `UPDATE … SET n = n - :x WHERE id = :id AND n >= :x` plus a row-count check is the atomic conditional update | CK-23, CK-35 |
| `INSERT … ON CONFLICT` (PostgreSQL), `INSERT … ON DUPLICATE KEY UPDATE` (MySQL) are native upserts; SQL Server `MERGE` needs `WITH (HOLDLOCK)` (or `SERIALIZABLE`) to be safe against concurrent inserts | CK-24 |
| `MAX(id) + 1` races; sequences and identity columns are safe but not gap-free | CK-24 |
| Advisory locks (`pg_advisory_xact_lock`, MySQL `GET_LOCK`, SQL Server `sp_getapplock`) are per connection or transaction: the work must run on the same one | CK-32 |
| Long transactions hold row locks and, in PostgreSQL, hold back vacuum | CK-28 |

## Messaging, caches and schedulers

| Trap | Check |
|---|---|
| Kafka: at-least-once by default; a rebalance or a crash before the offset commit redelivers; order holds only within a partition; exactly-once is scoped to Kafka transactions, not to your database | CK-29, CK-30, CK-31 |
| SQS standard queues deliver at least once and don't preserve order; FIFO queues deduplicate within a five-minute window only; a visibility timeout shorter than the work redelivers | CK-29, CK-30, CK-31 |
| RabbitMQ: manual ack after work; `prefetch` greater than 1 with parallel processing reorders | CK-30, CK-31 |
| Webhook providers retry on any non-2xx or timeout; deduplicate on the event id | CK-29 |
| Redis lock: `SET key token NX PX ttl` in one command; release with a compare-and-delete script on `token`; Redlock across nodes still needs fencing for correctness | CK-32 |
| Kubernetes CronJob: `concurrencyPolicy` defaults to `Allow`; the controller may occasionally create two jobs or none for one schedule, so the job must be idempotent | CK-33 |
| Kubernetes sends SIGTERM, waits `terminationGracePeriodSeconds` (default 30 s), then SIGKILL; a readiness probe should fail first so traffic drains | CK-19 |

---

## Tools that settle a claim

The verifier picks the cheapest tool that can turn the finding's `confirm` line into evidence, runs
it in a scratch copy, and re-runs it ([interleavings.md](interleavings.md#45-what-the-verdict-needs)).

| Runtime | Forced schedule | Detector or model checker | Stress |
|---|---|---|---|
| Java | `CountDownLatch`/`CyclicBarrier` at the gap; a fake dependency that blocks | **jcstress** (JMM-level outcomes), **Lincheck** (linearizability; model checking mode), ErrorProne `@GuardedBy`, SpotBugs `IS2_INCONSISTENT_SYNC`; thread dumps (`jstack`) show deadlock cycles | `ExecutorService` with more threads than cores, many iterations (CC p.219) |
| Kotlin | Lincheck; `runTest` with a `StandardTestDispatcher` to control coroutine order | Lincheck | as Java |
| Go | channels or a `sync.WaitGroup` at the gap | **`go test -race`** (ThreadSanitizer-based); `go vet` (copylocks); `goleak` for leaked goroutines | `go test -race -count=N -cpu=1,4,16`, `t.Parallel()` |
| C, C++ | barriers | **ThreadSanitizer** (`-fsanitize=thread`), Helgrind/DRD | many threads, many iterations |
| Rust | `std::sync::Barrier`, channels | **loom** (exhaustive interleavings of a small test), **shuttle** (randomised scheduling), **Miri** (data races in unsafe code), TSan on nightly | `cargo test` in a loop, `--test-threads` above core count |
| Python | `threading.Barrier`/`Event` at the gap; for asyncio, futures resolved in the bad order | asyncio debug mode (`PYTHONASYNCIODEBUG=1`: slow callbacks, never-awaited coroutines) | `pytest-repeat` (`--count=N`) for iterations; `pytest-xdist` (`-n`) runs tests in parallel processes, which exposes shared DB, file and fixture interference between tests, not thread races inside one test |
| JS/TS | deferred promises resolved in the bad order; fake timers | `@typescript-eslint/no-floating-promises`, `no-misused-promises`; ESLint `require-atomic-updates` (noisy, a hint not proof) | `Promise.all` of n concurrent calls in a loop; `autocannon` or `k6` against a local server |
| .NET | `SemaphoreSlim`/`Barrier` at the gap; `TaskCompletionSource` for async order | **Coyote** (systematic testing of async code); `Microsoft.VisualStudio.Threading.Analyzers` (`VSTHRD` rules for sync-over-async, `async void`) | `Parallel.For` with more workers than cores |
| SQL | two sessions driven statement by statement (interleavings.md §4.2) | the database's deadlock report (PostgreSQL logs "deadlock detected" with both statements, and `log_lock_waits` logs long waits; MySQL `SHOW ENGINE INNODB STATUS`; SQL Server `system_health` deadlock graphs) | many concurrent clients against a scratch database; `pgbench` with a custom script |
| Messaging | kill the consumer after the side effect, then redeliver | — | replay a batch twice; assert the effect count |

**What a tool's silence means.** A race detector reports only races on paths the run executed. A
model checker is exhaustive only within the test's bounds. A stress run that passes is weak evidence
(CR3). None of them sees check-then-act on correctly locked calls, races in the database, or
duplicates from redelivery. A clean tool run never REFUTES a finding on its own. A guard does
([interleavings.md](interleavings.md#when-an-interleaving-is-impossible-the-verifiers-refuted)).
