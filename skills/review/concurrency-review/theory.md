# Theory — The Principles Every Concurrency Finding Cites (CR1–CR23)

> A concurrency finding cites the principle that makes it a defect and not a hunch. A process rule
> cites the principle that justifies it. Each principle gives **what it says**, **why it holds**, and
> **what ignoring it looks like** in a review. Sources by short name:
>
> | Short name | Source | Pages cited as |
> |---|---|---|
> | **CC** | Robert C. Martin, *Clean Code* (Prentice Hall, 2009), ch. 13 "Concurrency" and Appendix A "Concurrency II" (Brett L. Schuchert) | PDF pages (printed + 31) |
> | **BKS** | Jason Cohen et al., *Best Kept Secrets of Peer Code Review* (SmartBear, 2006) | printed pages |
> | **OCR** | OWASP, *Code Review Guide* v2.0 (2017) | PDF pages (printed + 1) |
>
> The page conventions match [peer-review's theory](../peer-review/theory.md), so a cite here and a
> cite there point at the same page.
>
> **Clean Code's examples are Java threads.** The principles carry over to async runtimes, worker
> processes, databases and message systems, because each of those also has two actors reaching one
> piece of state. Where a principle reaches past what the sources say (databases, delivery
> guarantees, leases, deployment topology), it is marked **(not from the sources)**: it is practical
> guidance, and it carries no page cite.

---

## Part A — Why concurrency needs its own review

### CR1 — Concurrency hides state from the reader
**Says:** Concurrent code separates *what* is done from *when* it is done, so the reader can no
longer tell the state of the system from the code path in front of them. **Why:** In a
single-threaded program the stack trace tells you the state. Decoupling what from when changes that
and usually changes the design (CC p.209–210). Running inside a container or framework does not make
the code safe. You still have to know what the container does about concurrent update and deadlock
(CC p.210). **Ignoring it:** Reading a handler as if it runs alone. "The framework handles
threading."

### CR2 — Concurrency defects don't repeat on demand, so they get written off
**Says:** A failure that appears once and vanishes is a candidate concurrency defect until shown
otherwise. **Why:** Concurrency bugs aren't usually repeatable, so teams dismiss them as one-offs
(CC p.211). The book's advice is to assume one-offs do not exist, because the longer they are
ignored, the more code is built on the faulty approach (CC p.218). Failures that show up only under
load or at random times get written off as one-time events (CC p.222). **Ignoring it:** "Flaky,
re-run it." A `@Retry` on a test that touches shared state.

### CR3 — Reason over interleavings, because tests can't make the race fail reliably
**Says:** For any state two actors reach, write down the schedule that breaks it. A passing test is
weak evidence. **Why:** One `++` shared by two threads has 12,870 possible execution paths at the
byte-code level, and 2,704,156 when the field is a `long`. Most paths are fine and a few lose an
update (CC p.211, p.354). A two-thread test of that bug failed about once in ten runs of a million
iterations, so reliable failure needs well over a hundred million, and the tuning differs per
machine (CC p.372). **Ignoring it:** "It passed the tests," on code no test can make fail reliably.

## Part B — Shared state

### CR4 — Know what is atomic, and assume nothing else is
**Says:** Treat every read-modify-write, check-then-act and multi-word write as divisible unless a
primitive guarantees otherwise. **Why:** Pre- and post-increment are not atomic. It is a common
misconception that they are (CC p.357). On the JVM a write to a 64-bit value can be two 32-bit
writes, and another thread can see half of it (CC p.355). Skipping a lock "because concurrent update
is unlikely" is imprecision, not a decision (CC p.332, G26). **Ignoring it:** `count += 1` on a
shared field, with "it's one line."

### CR5 — Limit the scope of shared data; prefer copies and independent actors
**Says:** The fewer places that mutate shared state, the fewer places a guard can be forgotten.
Copy, partition or confine data where you can. **Why:** Encapsulate shared data and limit access to
it. Each extra mutation site is another chance to forget the guard and another copy of the guarding
logic (CC p.212). Copies merged in one thread often cost less than the locks they avoid (CC
p.212–213). Threads that share nothing, such as per-request data held in locals, need no
synchronisation (CC p.213). **Ignoring it:** A new field on a singleton service written from every
request, guarded in two of the three places that touch it.

### CR6 — Each call being atomic does not make the sequence atomic
**Says:** A client calling two or more methods on a shared object, and assuming nothing changes in
between, has a race even if every method is synchronised. Prefer one atomic operation on the server
side. **Why:** Dependencies between synchronised methods cause subtle bugs; avoid using more than one
method on a shared object (CC p.216). `hasNext()` then `next()` fails only on the last element, so it
ships (CC p.360–361). Client-based locking makes every caller remember the lock. Server-based locking
(one method such as `putIfAbsent` or `getNextOrNull`) puts the policy in one place, narrows the scope
of shared state, and reduces errors (CC p.362–364). **Ignoring it:** `if (!map.containsKey(k))
map.put(k, v)` on a `ConcurrentHashMap`, approved because the map is "thread-safe."

### CR7 — Know your library, including what it does not promise
**Says:** Use the runtime's concurrency primitives (pools, concurrent collections, atomics, latches)
and know which common types are not safe to share. **Why:** The book's advice is to learn the
library: thread-safe collections, executors, non-blocking solutions, and the classes that are not
thread-safe (CC p.213–214). Database connections, plain collections and date formatters are
examples of types that are unsafe to share (CC p.359). Some collections have individually
thread-safe methods, and any operation spanning more than one of them is still unsafe (CC p.359).
**Ignoring it:** A hand-rolled worker pool, or a shared `SimpleDateFormat`, connection or ORM
session.

### CR8 — Optimistic concurrency detects the conflict and retries
**Says:** A compare-and-swap, a version column or a conditional update checks that the value is
still what you read before writing, and retries when it isn't. **Why:** CAS verifies that the
variable still has its last known value before setting it, and the book calls it the analogue of
optimistic locking in databases, with `synchronized` the analogue of pessimistic locking (CC
p.358–359). The detection is usually cheaper than taking a lock (CC p.359). **Ignoring it:** A
read-then-write with no version check and no lock, or a version column that is incremented but never
checked in the `WHERE` clause.

## Part C — Locks and deadlock

### CR9 — Guard every critical section, keep it small, and don't call one from another
**Says:** Lock exactly the code that touches shared state, every time it is touched. Don't lock
what doesn't need it, and don't call a locked section from inside another. **Why:** Locks create
delays and add overhead, so keep synchronised sections as small as possible (CC p.216, p.365).
Learn which regions must be locked and lock them, don't lock regions that need no lock, and avoid
calling one locked section from another (CC p.222). Releasing a lock anywhere but a `finally` block
may cause issues (OCR p.183). **Ignoring it:** A lock held around an HTTP call, a callback, or an
`await`. A lock taken on the happy path and leaked on the exception path.

### CR10 — Deadlock needs four conditions; break one, usually circular wait
**Says:** Deadlock needs mutual exclusion, lock and wait, no preemption, and circular wait, all at
once. Break any one. The usual way is a single global order for acquiring resources. **Why:** All
four conditions must hold for deadlock to be possible (CC p.367–368). Using resources that allow
simultaneous use breaks mutual exclusion. Refusing to wait breaks lock and wait, at the risk of
starvation and livelock. Asking the owner to release is preemption, and is hard to get right (CC
p.368–369). A global acquisition order is "the most common approach," but it fails when the identity
of the second resource comes from the first (CC p.369–370). The book's example is two operations
taking two connection pools in opposite orders. It freezes under load, and the debug statements
added to find it move it elsewhere for months (CC p.366–367). Locks must be acquired and released in
the right order, even in error-handling code (BKS p.113). **Ignoring it:** Two code paths that lock
the same two rows, accounts, pools or mutexes in opposite orders.

## Part D — Structure and lifecycle

### CR11 — Keep concurrency code separate from everything else
**Says:** Thread, task and scheduling management lives in a few places that do nothing else, so
it can be reviewed, tuned and tested on its own. **Why:** Concurrency design is complex enough to be
a reason to change in its own right, so it gets its own classes (CC p.212). The appendix untangles a
server whose thread handling lived inside the message-processing method, and the fix separates the
two (CC p.350–352). Separate thread-aware code from thread-ignorant code and keep the thread-aware
part small (CC p.221). **Ignoring it:** Locks, spawns and retries sprinkled through business logic,
so no single place shows how the work is scheduled.

### CR12 — Recognise the execution model
**Says:** Most concurrency problems are a variant of producer-consumer, readers-writers or dining
philosophers. Name the one in the diff and check its known failure modes. **Why:** The book defines
bound resources, mutual exclusion, starvation, deadlock and livelock, and gives those three models
(CC p.214–215). A bounded queue needs signalling in both directions, "not empty" and "not full."
Readers-writers trades throughput against starvation and stale data. Competing for several resources
risks deadlock and livelock. Learn the standard solutions (CC p.215–216). **Ignoring it:** A queue
that signals only one way, or a reader-preferring lock that starves writers.

### CR13 — Bound what you create
**Says:** Every pool, queue and fan-out has a limit, and the code says what happens at the limit.
**Why:** A thread per request with no limit can hit the JVM's limit, and with many users the system
"might grind to a halt" (CC p.350). The appendix recommends the Executor framework's pools over
hand-made threads (CC p.357). **Ignoring it:** `Promise.all(items.map(call))` over a user-sized list,
a goroutine per message, an executor with an unbounded queue.

### CR14 — Shutdown is hard, so design it early
**Says:** Every worker, consumer and scheduler needs a stop path that finishes or hands back the work
in flight, and nothing waits forever for a signal that won't come. **Why:** Graceful shutdown commonly
fails by deadlock. A parent waits for a deadlocked child. A consumer blocks on a producer that has
already exited and never sees the shutdown signal. Think about shutdown early, because it takes longer
than you expect (CC p.217). **Ignoring it:** A new background loop with no stop, or a consumer that
acknowledges a message before the work it stands for is durable.

### CR15 — Concurrency pays only where there is waiting
**Says:** Check the performance claim behind a "make it faster with threads" change against what the
work actually does. **Why:** Concurrency improves performance only when there is wait time to share
(CC p.210). Adding threads to processor-bound work doesn't make it faster. I/O-bound work gains,
because one part uses the CPU while another waits (CC p.349, p.365–366). **Ignoring it:** Threads or
tasks added to CPU-bound work, which buys contention and new races for no speed-up.

## Part E — Evidence

### CR16 — Make concurrent code testable, then force the schedule
**Says:** A concurrency test that can find a bug runs the non-threaded logic on its own first, then
runs the threaded code with more actors than cores, tunable counts, several platforms and injected
scheduling points. **Why:** Get the non-threaded code working first, and don't chase threading and
non-threading bugs at once (CC p.218). Make threaded code pluggable and tunable (CC p.218–219). Run
with more threads than processors, because frequent task switching exposes missing critical
sections and deadlocks (CC p.219). Different platforms schedule differently, so run on every target
platform (CC p.219). Instrument the code with `yield`, `sleep` or random "jiggle" points to force
rare orderings (CC p.219–221). Instrumentation took one failure rate from about one in ten million
iterations to about one in thirty (CC p.373). **Ignoring it:** One two-thread test, run once, on the
developer's laptop.

### CR17 — The scenario is an interleaving; CONFIRMED needs a reproduction, run more than once
**Says:** A concurrency finding's scenario is a numbered schedule of two or more actors that reaches
the wrong state. CONFIRMED needs a reproduction (a forced schedule, a stress loop or a race-detector
report) that has been re-run. Without one the finding is PLAUSIBLE, and it names the run that would
confirm it. **Why:** Don't ignore a failure because the tests pass on a later run (CC p.217). One
tuned stress test may not fail on another machine (CC p.372). A long run of passes may mean only that
the tests can't expose the problem (CC p.372). **Ignoring it:** Citing one red run as proof, or one
green run as safety.

## Part F — Beyond one process

### CR18 — A race is an integrity defect, and often a security one
**Says:** A race that lets a check and its use come apart is a security finding when the check
guards money, a limit, a one-time token or an identity. **Why:** An unexpected ordering of events
can leave the code's state machine undefined, and then "security cannot be accurately enforced"
(OCR p.182). The guide's own example is a lost update, `X = X + 10`, run by two threads (OCR p.182).
Static fields holding per-request data are shared across threads, and static state must be
thread-safe (OCR p.183). Static globals holding sensitive security information can cause session
issues (OCR p.209). Practical extension **(not from the sources):** an attacker can choose the
interleaving by sending the same request many times in parallel, so a race on a balance check, coupon
redemption, rate limit or one-time token is reachable on purpose, not by bad luck. **Ignoring it:**
Grading a double-spend as a rare-timing `minor`.

### CR19 — The database is a concurrent system, and its isolation level is part of the code
**Says:** Two requests running read-then-write in transactions race exactly as two threads do. The
isolation level, the locks and the constraints decide which interleavings the database allows.
**Why:** The database analogue of CAS is optimistic locking, and of `synchronized` is pessimistic
locking (CC p.358). Practical extension **(not from the sources):** most databases default to an
isolation level that permits lost updates or write skew on read-then-write, a transaction does not
make a read-modify-write atomic by being a transaction, and a unique constraint is often the only
lock that holds across every code path and every instance. **Ignoring it:** "It's in a transaction,
so it's safe."

### CR20 — At-least-once delivery means some messages arrive twice **(not from the sources)**
**Says:** Under retries, redelivery and consumer restarts, a handler sees duplicates and
reorderings. Its effects must be idempotent, keyed on something stable, and recorded atomically with
the effect. **Why:** A consumer that crashes after doing the work and before acknowledging it gets
the message again. A client that times out and retries sends the request again. Exactly-once is a
property of a whole pipeline with deduplication, not of a queue. **Ignoring it:** A payment consumer
that charges on every delivery, or a dedupe check done before the effect in a separate transaction.

### CR21 — A lock that can expire is not mutual exclusion without a fencing token **(not from the sources)**
**Says:** A distributed lock or lease with a timeout can be held by two actors at once when the first
pauses past expiry. The protected resource must reject the stale holder, usually by checking a
monotonically increasing token. **Why:** A GC pause, a slow network call or a stopped container
outlives the lease. The holder wakes up, still believes it holds the lock, and writes. **Ignoring it:**
`SET lock NX PX 30000` around a job that can run longer than thirty seconds, released with a plain
`DEL`.

### CR22 — Topology decides reachability **(not from the sources)**
**Says:** How many instances, worker processes, consumers, partitions and scheduler replicas run
decides which interleavings exist. An in-process lock protects nothing across processes. **Why:** A
module-level cache, a `threading.Lock`, an `AtomicInteger` or a `setInterval` is per process. With
two pods, four workers each, the "single" timer runs eight times and the lock guards an eighth of the
callers. Clean Code's nearest point is that each deployment environment schedules differently, so
test on all of them (CC p.219). **Ignoring it:** Approving an in-memory lock or a cron in app code
without asking how many copies of the app run.

## Part G — Review practice

### CR23 — Use the checklist one item at a time, aimed at omissions
**Says:** Sweep every shared-state site for one check before moving to the next. When a new class of
defect turns up, re-check the sites already done. **Why:** A checklist found the most defects per
hour of the reading techniques compared (BKS p.49). It is strongest against omissions, because if
the author forgot something the reviewer is likely to forget it too (BKS p.111). Keep each list short
(BKS p.112). Its sample checklist has three thread-safety items: globals protected by locks, shared
objects accessed only under a lock, and locks taken and released in the right order, error paths
included (BKS p.113). The PSP practice is one item across the whole work product at a time (BKS
p.133–134). **Ignoring it:** Reading each line once against "is this thread-safe?", which finds what
is there and misses what is not.
