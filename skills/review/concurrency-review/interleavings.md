# Interleavings — The Scenario Notation, Worked Examples, and Reproductions

> A concurrency finding's failure scenario is an **interleaving**: a numbered schedule of two or more
> actors' steps that reaches a wrong state, with the shared values after every step (CR3, CR17). This
> file defines the notation, works the common shapes, says when an interleaving is impossible, and
> turns an interleaving into a reproduction a verifier can run and tdd can keep as a red test.
>
> OWASP's race-condition chapter explains its example the same way: two threads, `X = X + 10`, six
> numbered steps, and a final value of 15 where 25 was due (OCR p.182). The notation below is that
> method made compact.

---

## 1. The notation

### Full form (reports, comments)

```text
INTERLEAVING  <short name>
actors     A = <what runs>   B = <what runs>          [how they come to overlap]
shared     <name>=<initial>, …                        [where it lives: field, row, key, file, queue]
invariant  <what must hold afterwards>

 #  actor  step                                        shared after
 1  A      read balance → 100        (wallet.py:41)     balance=100
 2  B      read balance → 100        (wallet.py:41)     balance=100
 3  A      write balance = 100-30    (wallet.py:44)     balance=70
 4  B      write balance = 100-50    (wallet.py:44)   ! balance=50

result     balance=50, want 20: A's debit is lost
needs      two debits for one account at once; ≥ 2 threads, workers or instances
confirm    barrier after step 1 in both actors; assert balance=20; run 3× (forced schedule)
```

### Step vocabulary

| Write | Means |
|---|---|
| `read x → v` | The actor reads shared `x` and gets `v` |
| `write x = <expr>` | The actor writes shared `x`. Show the expression when it uses a stale local |
| `r = v` | A local or register value, private to the actor |
| `lock L` · `unlock L` | Acquire or release `L`. Name the actual lock object, row or key |
| `wait L (held by B)` | Blocked on `L` |
| `~ await <call> ~` | A suspension point: the actor yields here (await, yield, blocking I/O on a green thread) |
| `pause <why>` | The actor stops running without yielding anything: GC pause, preemption, container freeze, slow network |
| `BEGIN` · `COMMIT` · `ROLLBACK` | Transaction boundaries, with the isolation level on the `actors` line |
| `send m` · `deliver m` · `ack m` | Message lifecycle. `deliver m (2nd)` marks a redelivery |
| `crash` · `restart` | The process dies or comes back |
| `lease k until t` · `expires k` | A lease or lock with a timeout |
| `!` in the margin | The invariant breaks at this step |
| `cycle:` | For a deadlock, the wait-for cycle stated on one line |

### Compact form (the harness's `scenario` field, one line)

Steps separated by ` ; `, each `<actor> <step>`, the breaking step marked `!`, then `⇒` the result,
then the preconditions and the confirming run:

```text
A read bal=100 ; B read bal=100 ; A write bal=70 ; B write bal=50 ! ⇒ bal=50 want 20 (A's debit lost) | needs: 2 workers, same account | confirm: barrier after read in both, assert 20, 3 runs
```

### Rules for writing one

1. **Name the actors concretely.** "Two `POST /redeem` requests for one coupon, on any instance", not
   "two threads". Say how they overlap: request concurrency, worker count, redelivery, a second
   scheduler replica.
2. **Show the shared values after every step.** The column is the proof. A schedule without values
   is a story.
3. **Anchor each step to a line** of the diff or the code it calls (`file:line`).
4. **Switch actors only at a real preemption point.** Threads can switch between any two
   instructions. A single-threaded event loop (Node, asyncio, a Kotlin coroutine on one dispatcher)
   switches only at a suspension point, so an interleaving that switches between two lines with no
   `await` between them is impossible there. Database sessions switch between statements.
5. **Shortest schedule that breaks it.** Two actors unless the bug needs three. Leave out steps that
   don't change shared state.
6. **State the invariant** the schedule breaks, in domain words ("each coupon is redeemed once").
7. **`needs`** lists every precondition: topology (instances, workers, consumers), configuration
   (isolation level, `acks_late`, prefetch), and timing ("job runs longer than the 30 s lease").
   These are the facts a `topology_question` asks about.
8. **`confirm`** names the run that turns PLAUSIBLE into CONFIRMED (section 4).

### When an interleaving is impossible (the verifier's REFUTED)

| The schedule is impossible because | Prove it with |
|---|---|
| Both actors hold **the same** lock across the steps that matter | The lock object and its scope, quoted. A new lock per call, or a different lock per instance, is not the same lock |
| The runtime is single-threaded and there is no suspension point in the gap | The code between the steps, showing no `await`/`yield`/blocking call. Then check the topology: one event loop per process, and how many processes? |
| A constraint rejects the breaking step | The unique index, check constraint or conditional `WHERE` that makes step *k* fail, **and** the code that handles that failure. An unhandled violation turns a lost update into a 500, which is still a finding, a smaller one |
| The isolation level or lock prevents the read | The isolation level actually in force (session or connection config, not the docs' default), or the `FOR UPDATE` inside the same transaction |
| Only one actor can exist | The topology fact, quoted: a single replica pinned in config, a single partition with one consumer, a scheduler with a lock. "We only run one pod today" is a `topology_question`, not a refutation, unless the config enforces it |
| The value is confined | It is a local, a per-request object, or a copy (CR5) |

---

## 2. Worked examples

### 2.1 Lost update in memory (read-modify-write)

```python
# metrics.py
class Counter:                       # one instance, shared by the worker's thread pool
    def __init__(self): self.hits = 0
    def hit(self): self.hits += 1    # line 4
```

```text
INTERLEAVING  lost increment
actors     A, B = two request threads in one gunicorn worker (--threads 8)
shared     counter.hits=42
invariant  hits increases by one per call

 #  actor  step                                  shared after
 1  A      r_a = read hits → 42   (metrics.py:4)  hits=42
 2  B      r_b = read hits → 42   (metrics.py:4)  hits=42
 3  B      write hits = r_b+1     (metrics.py:4)  hits=43
 4  A      write hits = r_a+1     (metrics.py:4) ! hits=43

result     hits=43 after two calls, want 44
needs      ≥ 2 threads calling hit() on the shared instance
confirm    stress: 16 threads × 100k calls, assert hits = 1.6M; run 5×, record the shortfall
```

`+=` is a load, an add and a store (CR4). The GIL makes each bytecode atomic, not the three together.
Clean Code's `getNextId` is the same bug in Java (CC p.211, p.356–357).

### 2.2 Lost update through an ORM (get, modify, save)

```python
# wallet/views.py
def debit(request, account_id, amount):
    acct = Account.objects.get(id=account_id)        # line 12
    if acct.balance < amount: raise Insufficient()   # line 13
    acct.balance -= amount                           # line 14
    acct.save()                                      # line 15: UPDATE … SET balance=…, name=…, …
```

```text
INTERLEAVING  ORM lost update and overdraft
actors     A = debit 30, B = debit 80, same account; 2 pods × 4 workers; Postgres READ COMMITTED, autocommit
shared     account#7.balance=100
invariant  balance = 100 − sum of accepted debits, and never < 0

 #  actor  step                                         shared after
 1  A      read balance → 100        (views.py:12)       balance=100
 2  B      read balance → 100        (views.py:12)       balance=100
 3  A      check 100 ≥ 30 ✓          (views.py:13)       balance=100
 4  B      check 100 ≥ 80 ✓          (views.py:13)       balance=100
 5  A      write balance = 70        (views.py:15)       balance=70
 6  B      write balance = 20        (views.py:15)     ! balance=20

result     both debits accepted (110 taken), balance=20, want one rejected
needs      two debits on one account within the request time; any worker count > 1
confirm    two DB sessions driven step by step (section 4.2); then 50 parallel requests, sum check
```

A transaction around lines 12–15 does not fix it under READ COMMITTED (CR19). Fixes, in order of
preference: a conditional update (`UPDATE … SET balance = balance - 30 WHERE id = 7 AND balance >= 30`,
then check the row count), which is server-side atomicity (CR6). Or `select_for_update()` inside
`transaction.atomic()`. Or a version column checked on save (CR8). The full-row `save()` also
overwrites any column another request changed in between, a second lost update on fields this code
never meant to touch.

### 2.3 Check-then-act on a database row (insert race)

```python
# accounts/signup.py
if not User.objects.filter(email=email).exists():   # line 20
    User.objects.create(email=email, …)              # line 21
```

```text
INTERLEAVING  duplicate signup
actors     A, B = two POST /signup with one email (double-click, client retry)
shared     users rows with email=e: 0; no unique index on email
invariant  at most one user per email

 #  actor  step                                     shared after
 1  A      exists(e) → false     (signup.py:20)      rows(e)=0
 2  B      exists(e) → false     (signup.py:20)      rows(e)=0
 3  A      INSERT user(e)        (signup.py:21)      rows(e)=1
 4  B      INSERT user(e)        (signup.py:21)    ! rows(e)=2

result     two accounts for one email
needs      two requests inside the gap between lines 20 and 21
confirm    two sessions: run line 20 in both, then line 21 in both; assert one row (deterministic)
```

`SELECT … FOR UPDATE` can't help here: there is no row yet to lock. The lock that holds across every
code path and instance is a **unique constraint**, with the violation caught and mapped to "already
exists" (CR19). `get_or_create` is safe only with that constraint behind it.

### 2.4 Check-then-act on a file (TOCTOU)

```python
# export/writer.py
path = f"/srv/exports/{report_id}.csv"
if not os.path.exists(path):           # line 8
    with open(path, "w") as f:         # line 9
        write_report(f, report_id)     # line 10
```

```text
INTERLEAVING  two writers, one file
actors     A, B = two export jobs for one report; 3 Celery workers sharing /srv/exports (NFS)
shared     file exports/91.csv: absent
invariant  the file, once present, holds one complete report

 #  actor  step                                    shared after
 1  A      exists(91.csv) → false  (writer.py:8)    absent
 2  B      exists(91.csv) → false  (writer.py:8)    absent
 3  A      open w, truncate        (writer.py:9)    empty
 4  A      write rows 1–500        (writer.py:10)   500 rows
 5  B      open w, truncate        (writer.py:9)  ! empty
 6  A      write rows 501–900      (writer.py:10)   A's rows 501–900 mixed with B's rows 1–…

result     a corrupt file served as complete
needs      two jobs for one report inside the window; shared filesystem
confirm    forced schedule: block A after line 9 on a test hook, run B to completion, release A
```

Fix: write to a unique temp file and `os.replace` it into place (atomic within one filesystem), or
`open(path, "x")` / `O_CREAT|O_EXCL` to make the existence check and the create one step. When the
path or its directory is attacker-influenced, the same gap is a security TOCTOU (a symlink swapped in
between check and use): type `security`, escalate to appsec (CR18).

### 2.5 Check-then-act across an `await` (single-threaded, still a race)

```ts
// credits.ts
async function spend(userId: string, cost: number) {
  const user = await repo.get(userId);            // line 3
  if (user.credits < cost) throw new Error("no"); // line 4
  await provider.reserve(userId, cost);           // line 5
  user.credits -= cost;                           // line 6
  await repo.put(user);                           // line 7
}
```

```text
INTERLEAVING  double spend across await
actors     A, B = two spend(u, 10) calls on one Node process (one event loop)
shared     user u.credits=10 (in the store)
invariant  credits never go below 0; each reservation is paid for

 #  actor  step                                   shared after
 1  A      ~ await repo.get ~ → credits 10          credits=10
 2  B      ~ await repo.get ~ → credits 10          credits=10
 3  A      check 10 ≥ 10 ✓; ~ await reserve ~       credits=10, reserved=1
 4  B      check 10 ≥ 10 ✓; ~ await reserve ~       credits=10, reserved=2
 5  A      write credits = 0; ~ await put ~         credits=0
 6  B      write credits = 0; ~ await put ~       ! credits=0, reserved=2

result     two reservations paid for once
needs      two calls for one user overlapping; any single process is enough
confirm    deferred promises: resolve both repo.get before either reserve; assert one rejection
```

Every switch happens at an `await`, so the schedule is legal on one event loop (rule 4). "Node is
single-threaded" refutes nothing here.

### 2.6 Deadlock cycle (lock order)

```sql
-- transfer(from, to, amt), called as transfer(1, 2, …) and transfer(2, 1, …)
BEGIN;
SELECT * FROM accounts WHERE id = :from FOR UPDATE;   -- line 2
SELECT * FROM accounts WHERE id = :to   FOR UPDATE;   -- line 3
UPDATE … ; COMMIT;
```

```text
INTERLEAVING  transfer deadlock
actors     A = transfer(1→2), B = transfer(2→1); Postgres; two workers
shared     row locks on accounts#1, accounts#2: free
invariant  every transfer completes or fails cleanly

 #  actor  step                                     shared after
 1  A      BEGIN; lock acct#1  (line 2)              #1 held by A
 2  B      BEGIN; lock acct#2  (line 2)              #1 A, #2 B
 3  A      wait acct#2 (held by B)  (line 3)         #1 A, #2 B
 4  B      wait acct#1 (held by A)  (line 3)       ! #1 A, #2 B

cycle      A holds #1, waits #2 → B holds #2, waits #1 → A
result     the database aborts one transaction with a deadlock error; with in-process mutexes, both hang forever
needs      opposite-direction transfers between the same pair at once
confirm    two sessions, steps 1–4 by hand; expect "deadlock detected" (deterministic)
```

All four conditions hold (CR10): row locks are exclusive, each holds one while waiting, nobody
preempts, and the waits form a cycle. Break circular wait: lock both rows in id order
(`WHERE id IN (:a,:b) ORDER BY id FOR UPDATE`). The database's deadlock detector turns the hang into
an error, so the second question is whether the caller retries the aborted transaction or returns a
500. Clean Code's version is two connection pools taken in opposite orders (CC p.366–367).

### 2.7 Double-delivered message (at-least-once)

```python
# billing/consumer.py
@app.task(acks_late=True)
def charge(order_id):
    order = Order.objects.get(id=order_id)
    psp.charge(order.card_token, order.total)      # line 6: external side effect
    order.status = "paid"; order.save()            # line 7
```

```text
INTERLEAVING  duplicate charge on redelivery
actors     A = worker 1 handling delivery 1, B = worker 2 handling delivery 2 of the same message
shared     order#5.status=new, psp charges for order#5: 0
invariant  each order is charged once

 #  actor  step                                     shared after
 1  A      deliver m(order#5)                        status=new, charges=0
 2  A      psp.charge          (consumer.py:6)       charges=1
 3  A      crash: pod evicted before line 7          status=new, charges=1, m unacked
 4  B      deliver m(order#5) (2nd)                  status=new, charges=1
 5  B      psp.charge          (consumer.py:6)     ! charges=2
 6  B      status = paid; ack m                      status=paid, charges=2

result     customer charged twice
needs      at-least-once delivery (acks_late), and between line 6 and the ack either the worker's broker
           connection drops (pod or node lost) or the broker's visibility timeout runs out
confirm    run the task, kill the worker after line 6 (test hook raising SystemExit), redeliver; assert one charge
```

Checking `status == "paid"` at the top doesn't close it: the crash happens before the status is
written (CR20). The fix is an idempotency key the provider honours (`order#5`), or recording the
attempt in the same transaction as a unique "charge intent" row before calling out, and reconciling.

### 2.8 Lease expiry without a fencing token

```text
INTERLEAVING  two holders of one lock
actors     A, B = nightly settlement job on pod a and pod b; Redis lock SET settle NX PX 30000
shared     lock settle: free; ledger batch#9: open
invariant  one job writes batch#9

 #  actor  step                                     shared after
 1  A      lease settle until t+30s                  lock=A
 2  A      pause (GC / slow query, 45 s)             lock=A
 3  -      expires settle at t+30s                   lock=free
 4  B      lease settle until t+60s                  lock=B
 5  B      write batch#9 totals                      batch#9 by B
 6  A      resumes; write batch#9 totals           ! batch#9 by A over B
 7  A      DEL settle                                lock=free while B still running

result     batch written twice; A's DEL frees B's lock
needs      a run longer than the lease (any pause counts); ≥ 2 replicas
confirm    test with a 1 s lease and a hook that sleeps 2 s in A after acquiring
```

Fix (CR21): the store rejects stale writers (a fencing token from the lock, checked on write), the
lease is renewed while the work runs, and release is compare-and-delete on the holder's value.

---

## 3. Choosing the shape

| The code does | Write the interleaving as | Example |
|---|---|---|
| Read, compute, write back | Lost update | 2.1, 2.2 |
| Check a condition, then act on it | Check-then-act | 2.3, 2.4, 2.5 |
| Take two resources | Deadlock cycle, with a `cycle:` line | 2.6 |
| Consume, act, acknowledge | Crash between act and ack, then redelivery | 2.7 |
| Lock with a timeout | Pause past expiry | 2.8 |
| Lazy-create a shared thing | Check-then-act on `instance == null`, or a reader seeing a half-built object (visibility) | CK-21 |
| Fan out and gather | One child fails at step *k*; show what the others did after it | CK-15 |

---

## 4. From interleaving to reproduction

A finder writes the `confirm` line. A verifier, working in a scratch copy, runs it. tdd keeps it as
the red test.

### 4.1 Forced schedule (deterministic, first choice)

Make the gap in the interleaving a place the test controls, then drive the actors through it in
the bad order:

- **A seam at the gap.** A fake dependency that blocks until released: a repository whose `get`
  returns only when the test opens a latch, a provider stub that waits on a barrier, a clock the test
  advances. Clean Code's jiggle points are the random version of this seam (CC p.219–221). Here the
  point is placed and the order is chosen.
- **Threads:** `CountDownLatch`/`CyclicBarrier` (Java), `threading.Barrier` (Python),
  `sync.WaitGroup` plus channels (Go), `Barrier`/`SemaphoreSlim` (.NET).
- **Async:** deferred promises or futures the test resolves in the bad order.
- **Database:** two connections driven statement by statement from a script (4.2).
- **Crashes:** a hook that raises or exits after the side effect, then a redelivery.

A forced schedule fails every time, if the bug is real. Run it three times. Red three times is
CONFIRMED. A forced schedule that sometimes passes means the seam isn't where the gap is: move it.

### 4.2 Two database sessions

```text
session 1: BEGIN;                                  session 2: BEGIN;
session 1: SELECT balance FROM accounts WHERE id=7;      -- 100
                                                   session 2: SELECT balance FROM accounts WHERE id=7;  -- 100
session 1: UPDATE accounts SET balance=70 WHERE id=7; COMMIT;
                                                   session 2: UPDATE accounts SET balance=20 WHERE id=7; COMMIT;
check:     SELECT balance …   -- 20: the lost update reproduced
```

Set the isolation level the application actually uses, not the database default, and say which.

### 4.3 Stress loop (second choice, and the regression guard)

More actors than cores (CC p.219), many iterations, the invariant asserted at the end, the counts
tunable (CC p.218–219). Record the failure rate (`3 failures in 5 runs of 100k`), not just pass or
fail. A stress run is CONFIRMED when it fails in at least two separate runs. A run that never fails is
weak evidence of safety (CR3), and it is never a REFUTED on its own.

### 4.4 Race detectors and model checkers

`go test -race`, ThreadSanitizer, Miri, jcstress, Lincheck, loom and the others in
[languages.md](languages.md#tools-that-settle-a-claim). A race-detector report names two unordered
accesses with their stacks. It is CONFIRMED evidence that a data race happened in that run, on those
lines. Re-run to show it reproduces on the line the finding names. A clean detector run proves only
that the executed paths had no data race. It says nothing about check-then-act on properly locked
calls (CR6) or about races in the database.

### 4.5 What the verdict needs

| Evidence | Verdict |
|---|---|
| Forced schedule red 3 of 3 runs | CONFIRMED |
| Stress loop red in ≥ 2 separate runs, rate recorded | CONFIRMED |
| Race-detector report on the named lines, reproduced on a re-run | CONFIRMED (data race) |
| One red run that didn't recur in ≥ 10 re-runs | PLAUSIBLE: record it, never dismiss it (CR2) |
| A legal interleaving written out, no run yet | PLAUSIBLE, with its `confirm` line |
| Every run green | Not a verdict. Weak evidence (CR3). Refute only with a guard from section 1 |
