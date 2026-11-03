#!/usr/bin/env bash
# Build the concurrency fixture's git repository: Tillpoint, a stdlib-Python wallet and
# promotions service (a threaded HTTP API, a threaded queue worker, SQLite locally and
# PostgreSQL in production). main has the API, the broker, the order.paid consumer and the
# Kubernetes manifests (api: 2 replicas, worker: 3). feature/coupon-worker adds wallet
# debit/credit/transfer, coupon redemption, a cashback consumer and a daily reminder job,
# and is left checked out. The plants are listed in README.md next to this script.
# Idempotent: removes and rebuilds repo/ each time.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

commit() { # commit <iso-date> <author> <subject> [body]
  git add -A
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  GIT_AUTHOR_NAME="$2" GIT_COMMITTER_NAME="$2" \
  GIT_AUTHOR_EMAIL="${2// /.}@example.invalid" \
  GIT_COMMITTER_EMAIL="${2// /.}@example.invalid" \
  git commit -q -m "$3" ${4:+-m "$4"}
}

mkdir -p tillpoint/worker tests deploy

# ================================================================ main
cat > README.md <<'EOF'
# Tillpoint

Wallets and promotions for the Tillpoint checkout. Standard-library Python 3.12+.

- `tillpoint/api.py`: the HTTP API (`python -m tillpoint.api`), a thread per request
- `tillpoint/worker/`: the queue worker (`python -m tillpoint.worker`), consumers on threads
- `tillpoint/broker.py`: the at-least-once queue interface (SQS standard queues in production)
- `deploy/`: the Kubernetes manifests

Locally and in tests everything runs on SQLite. Production runs the same SQL on PostgreSQL 16.

    python3 -m unittest discover -s tests -t .
EOF

cat > tillpoint/__init__.py <<'EOF'
EOF

cat > tillpoint/clock.py <<'EOF'
import datetime as dt


def utcnow():
    """Now, as the ISO 8601 UTC text the database stores."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
EOF

cat > tillpoint/db.py <<'EOF'
"""Database connections.

Local runs and the tests use SQLite from the standard library. Production runs the same SQL
on PostgreSQL 16 (DATABASE_URL in deploy/*.yaml, default isolation READ COMMITTED); the driver
ships in the production image only. Both are opened in autocommit mode: every statement is its
own transaction unless the caller opens one.
"""
import os
import pathlib
import sqlite3

SCHEMA = pathlib.Path(__file__).with_name("schema.sql")


def connect(url=None):
    url = url or os.environ.get("DATABASE_URL", "sqlite:///tillpoint.db")
    if url.startswith("sqlite:///"):
        return sqlite3.connect(url[len("sqlite:///"):], isolation_level=None,
                               check_same_thread=False, timeout=5)
    return _postgres(url)


def _postgres(url):
    import psycopg  # production image only

    return _Qmark(psycopg.connect(url, autocommit=True))


class _Qmark:
    """Lets the same `?` placeholders run on psycopg."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(sql.replace("?", "%s"), params)

    def close(self):
        self._conn.close()


def init(conn):
    """Create the tables (SQLite; production applies schema.sql as a migration)."""
    conn.executescript(SCHEMA.read_text())
EOF

cat > tillpoint/schema.sql <<'EOF'
CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY,
    user_id      TEXT NOT NULL,
    total_cents  INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    paid_at      TEXT
);

CREATE TABLE IF NOT EXISTS wallets (
    user_id        TEXT PRIMARY KEY,
    balance_cents  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY,
    queue       TEXT NOT NULL,
    body        TEXT NOT NULL,
    visible_at  REAL NOT NULL,
    receipt     TEXT,
    attempts    INTEGER NOT NULL DEFAULT 0
);
EOF

cat > tillpoint/broker.py <<'EOF'
"""A small at-least-once queue on the database, with the contract of the SQS standard queues
production uses (deploy/worker.yaml).

receive() hides a message for `visibility_timeout` seconds and returns it with a receipt.
ack() deletes it. A message that is not acked before its visibility timeout runs out is
delivered again, to whichever consumer asks next. Order is not guaranteed.
"""
import json
import time
import uuid
from dataclasses import dataclass


@dataclass
class Message:
    id: int
    body: dict
    receipt: str
    attempts: int


class Broker:
    def __init__(self, conn, clock=time.time):
        self.conn, self.clock = conn, clock

    def publish(self, queue, body):
        self.conn.execute("INSERT INTO messages (queue, body, visible_at) VALUES (?, ?, ?)",
                          (queue, json.dumps(body), self.clock()))

    def receive(self, queue, visibility_timeout=30):
        now, receipt = self.clock(), uuid.uuid4().hex
        row = self.conn.execute(
            "UPDATE messages SET visible_at = ?, receipt = ?, attempts = attempts + 1 "
            "WHERE id = (SELECT id FROM messages WHERE queue = ? AND visible_at <= ? ORDER BY id LIMIT 1) "
            "RETURNING id, body, attempts",
            (now + visibility_timeout, receipt, queue, now)).fetchone()
        if row is None:
            return None
        return Message(row[0], json.loads(row[1]), receipt, row[2])

    def ack(self, msg):
        self.conn.execute("DELETE FROM messages WHERE id = ? AND receipt = ?", (msg.id, msg.receipt))
EOF

cat > tillpoint/orders.py <<'EOF'
"""order.paid consumer: marks the order paid. Setting an absolute status is safe to repeat."""

QUEUE = "orders.order-paid"


def handle(conn, body):
    conn.execute("UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ?",
                 (body["paid_at"], body["order_id"]))


def consume(broker, conn, stop):
    while not stop.is_set():
        msg = broker.receive(QUEUE)
        if msg is None:
            stop.wait(1.0)
            continue
        handle(conn, msg.body)
        broker.ack(msg)
EOF

cat > tillpoint/api.py <<'EOF'
"""HTTP API: one ThreadingHTTPServer per pod, a thread and a database connection per request."""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import db

ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile(pattern + r"$"), fn))
        return fn
    return deco


@route("GET", r"/wallet/(?P<user_id>[\w-]+)")
def get_wallet(conn, body, user_id):
    row = conn.execute("SELECT balance_cents FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return 404, {"error": "no wallet"}
    return 200, {"user_id": user_id, "balance_cents": row[0]}


class Handler(BaseHTTPRequestHandler):
    def _dispatch(self, method):
        for m, pattern, fn in ROUTES:
            match = pattern.match(self.path)
            if m == method and match:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                conn = db.connect()
                try:
                    status, payload = fn(conn, body, **match.groupdict())
                except Exception as e:
                    if not hasattr(e, "status"):
                        raise
                    status, payload = e.status, {"error": type(e).__name__}
                finally:
                    conn.close()
                return self._send(status, payload)
        self._send(404, {"error": "not found"})

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main(port=8080):
    ThreadingHTTPServer(("", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
EOF

cat > tillpoint/worker/__init__.py <<'EOF'
EOF

cat > tillpoint/worker/__main__.py <<'EOF'
"""The worker process: queue consumers on threads. deploy/worker.yaml runs it."""
import logging
import signal
import threading

from .. import db, orders
from ..broker import Broker


def main():
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    threads = [threading.Thread(target=orders.consume, args=(Broker(db.connect()), db.connect(), stop),
                                name="orders")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
EOF

cat > deploy/api.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tillpoint-api
  labels:
    app: tillpoint
    component: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tillpoint
      component: api
  template:
    metadata:
      labels:
        app: tillpoint
        component: api
    spec:
      containers:
        - name: api
          image: registry.example.invalid/tillpoint:latest
          command: ["python", "-m", "tillpoint.api"]
          ports:
            - containerPort: 8080
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: tillpoint-db
                  key: url
---
apiVersion: v1
kind: Service
metadata:
  name: tillpoint-api
spec:
  selector:
    app: tillpoint
    component: api
  ports:
    - port: 80
      targetPort: 8080
EOF

cat > deploy/worker.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tillpoint-worker
  labels:
    app: tillpoint
    component: worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tillpoint
      component: worker
  template:
    metadata:
      labels:
        app: tillpoint
        component: worker
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: worker
          image: registry.example.invalid/tillpoint:latest
          command: ["python", "-m", "tillpoint.worker"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: tillpoint-db
                  key: url
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/helpers.py <<'EOF'
import os
import tempfile
import unittest

from tillpoint import db


class DbTest(unittest.TestCase):
    """A fresh SQLite file per test, outside the repository."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.url = "sqlite:///" + self.path
        self.conn = db.connect(self.url)
        db.init(self.conn)

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)
EOF

cat > tests/test_broker.py <<'EOF'
from tests.helpers import DbTest
from tillpoint.broker import Broker


class BrokerTest(DbTest):
    def test_receive_hides_until_timeout(self):
        t = [1000.0]
        b = Broker(self.conn, clock=lambda: t[0])
        b.publish("q", {"n": 1})
        m = b.receive("q", visibility_timeout=30)
        self.assertEqual(m.body, {"n": 1})
        self.assertIsNone(b.receive("q"))
        t[0] += 31
        again = b.receive("q")
        self.assertEqual((again.id, again.attempts), (m.id, 2))

    def test_ack_deletes(self):
        b = Broker(self.conn)
        b.publish("q", {"n": 1})
        b.ack(b.receive("q"))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 0)
EOF

cat > tests/test_orders.py <<'EOF'
from tests.helpers import DbTest
from tillpoint import orders


class OrdersTest(DbTest):
    def test_marks_paid(self):
        self.conn.execute("INSERT INTO orders (id, user_id, total_cents) VALUES (1, 'u1', 2500)")
        orders.handle(self.conn, {"order_id": 1, "paid_at": "2026-08-01T10:00:00Z"})
        orders.handle(self.conn, {"order_id": 1, "paid_at": "2026-08-01T10:00:00Z"})
        self.assertEqual(self.conn.execute("SELECT status FROM orders WHERE id = 1").fetchone()[0], "paid")
EOF

commit "2026-08-04T10:12:00+00:00" "Dana Whitlock" "Tillpoint: wallets API, broker and the order.paid consumer"

sed -i.bak 's/replicas: 1/replicas: 3/' deploy/worker.yaml && rm deploy/worker.yaml.bak
commit "2026-09-02T16:40:00+00:00" "Ravi Menon" "deploy: run the worker with 3 replicas" \
"The order.paid backlog reached 40 minutes during the September sale. Three worker pods drain it in
under two minutes."

# ================================================================ feature/coupon-worker
git checkout -q -b feature/coupon-worker

cat > tillpoint/wallet.py <<'EOF'
"""Wallet balances in cents. Credits come from coupons and cashback; debits pay for orders."""
import threading


class InsufficientFunds(Exception):
    status = 402


class NoWallet(Exception):
    status = 404


def balance(conn, user_id):
    row = conn.execute("SELECT balance_cents FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        raise NoWallet(user_id)
    return row[0]


def credit(conn, user_id, amount):
    current = balance(conn, user_id)
    conn.execute("UPDATE wallets SET balance_cents = ? WHERE user_id = ?", (current + amount, user_id))


def debit(conn, user_id, amount):
    current = balance(conn, user_id)
    if current < amount:
        raise InsufficientFunds(user_id)
    conn.execute("UPDATE wallets SET balance_cents = ? WHERE user_id = ?", (current - amount, user_id))


# One lock per wallet, so two transfers touching the same wallet don't interleave.
_locks = {}
_locks_guard = threading.Lock()


def _lock_for(user_id):
    with _locks_guard:
        return _locks.setdefault(user_id, threading.Lock())


def transfer(conn, from_user, to_user, amount):
    """Gift wallet credit to another user."""
    if from_user == to_user:
        raise ValueError("transfer to self")
    with _lock_for(from_user):
        with _lock_for(to_user):
            debit(conn, from_user, amount)
            credit(conn, to_user, amount)
EOF

python3 - <<'EOF'
import pathlib
p = pathlib.Path("tillpoint/api.py")
s = p.read_text()
s = s.replace("from . import db\n", "from . import db, wallet\n")
s = s.replace('''class Handler(BaseHTTPRequestHandler):''', '''@route("POST", r"/wallet/debit")
def post_debit(conn, body):
    """Called by checkout when an order is paid from the wallet."""
    if body["amount_cents"] <= 0:
        return 400, {"error": "amount must be positive"}
    wallet.debit(conn, body["user_id"], body["amount_cents"])
    return 200, {"user_id": body["user_id"], "balance_cents": wallet.balance(conn, body["user_id"])}


@route("POST", r"/wallet/transfer")
def post_transfer(conn, body):
    if body["amount_cents"] <= 0:
        return 400, {"error": "amount must be positive"}
    wallet.transfer(conn, body["from_user"], body["to_user"], body["amount_cents"])
    return 200, {"ok": True}


class Handler(BaseHTTPRequestHandler):''')
p.write_text(s)
EOF

cat > tests/test_wallet.py <<'EOF'
from tests.helpers import DbTest
from tillpoint import wallet


class WalletTest(DbTest):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO wallets VALUES ('alice', 5000), ('bob', 1000)")

    def test_credit_and_debit(self):
        wallet.credit(self.conn, "alice", 250)
        wallet.debit(self.conn, "alice", 1000)
        self.assertEqual(wallet.balance(self.conn, "alice"), 4250)

    def test_debit_rejects_overdraft(self):
        with self.assertRaises(wallet.InsufficientFunds):
            wallet.debit(self.conn, "bob", 1001)
        self.assertEqual(wallet.balance(self.conn, "bob"), 1000)

    def test_transfer_moves_credit(self):
        wallet.transfer(self.conn, "alice", "bob", 2000)
        wallet.transfer(self.conn, "bob", "alice", 500)
        self.assertEqual((wallet.balance(self.conn, "alice"), wallet.balance(self.conn, "bob")), (3500, 2500))
EOF

commit "2026-10-19T09:30:00+00:00" "Ines Calder" "Wallet: debit, credit and transfer" \
"POST /wallet/debit for checkout's pay-with-wallet, POST /wallet/transfer for gifting credit.
Transfers lock both wallets so they can't interleave."

cat >> tillpoint/schema.sql <<'EOF'

CREATE TABLE IF NOT EXISTS coupons (
    code          TEXT PRIMARY KEY,
    amount_cents  INTEGER NOT NULL CHECK (amount_cents > 0),
    assigned_to   TEXT,             -- NULL: anyone may redeem it
    expires_at    TEXT NOT NULL,    -- ISO 8601 UTC
    used          INTEGER NOT NULL DEFAULT 0,
    used_by       TEXT,
    used_at       TEXT
);
EOF

cat > tillpoint/coupons.py <<'EOF'
"""Coupon redemption: a coupon credits its amount to the redeemer's wallet, once."""
from . import wallet


class CouponError(Exception):
    status = 400


class CouponNotFound(CouponError):
    status = 404


class CouponAlreadyUsed(CouponError):
    status = 409


class CouponExpired(CouponError):
    status = 410


class CouponNotYours(CouponError):
    status = 403


def redeem(conn, code, user_id, now):
    """Mark the coupon used by user_id and credit its amount. Returns the amount credited."""
    row = conn.execute("SELECT amount_cents, assigned_to, expires_at, used FROM coupons WHERE code = ?",
                       (code,)).fetchone()
    if row is None:
        raise CouponNotFound(code)
    amount, assigned_to, expires_at, used = row
    if used:
        raise CouponAlreadyUsed(code)
    if expires_at <= now:
        raise CouponExpired(code)
    if assigned_to is not None and assigned_to != user_id:
        raise CouponNotYours(code)
    conn.execute("UPDATE coupons SET used = 1, used_by = ?, used_at = ? WHERE code = ?", (user_id, now, code))
    wallet.credit(conn, user_id, amount)
    return amount
EOF

python3 - <<'EOF'
import pathlib
p = pathlib.Path("tillpoint/api.py")
s = p.read_text()
s = s.replace("from . import db, wallet\n", "from . import coupons, db, wallet\nfrom .clock import utcnow\n")
s = s.replace('''class Handler(BaseHTTPRequestHandler):''', '''@route("POST", r"/coupons/redeem")
def post_redeem(conn, body):
    amount = coupons.redeem(conn, body["code"], body["user_id"], utcnow())
    return 200, {"credited_cents": amount}


class Handler(BaseHTTPRequestHandler):''')
p.write_text(s)
EOF

cat > tests/test_coupons.py <<'EOF'
import threading

from tests.helpers import DbTest
from tillpoint import coupons, db, wallet

NOW = "2026-10-20T12:00:00Z"


class RedeemTest(DbTest):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO wallets VALUES ('u1', 0), ('u2', 0)")
        self.conn.execute("INSERT INTO coupons (code, amount_cents, expires_at) "
                          "VALUES ('WELCOME10', 1000, '2026-12-31T00:00:00Z')")
        self.conn.execute("INSERT INTO coupons (code, amount_cents, expires_at, assigned_to) "
                          "VALUES ('OLD5', 500, '2026-10-01T00:00:00Z', 'u1')")

    def test_redeem_credits_wallet(self):
        self.assertEqual(coupons.redeem(self.conn, "WELCOME10", "u1", NOW), 1000)
        self.assertEqual(wallet.balance(self.conn, "u1"), 1000)

    def test_second_redeem_rejected(self):
        coupons.redeem(self.conn, "WELCOME10", "u1", NOW)
        with self.assertRaises(coupons.CouponAlreadyUsed):
            coupons.redeem(self.conn, "WELCOME10", "u2", NOW)

    def test_expired_rejected(self):
        with self.assertRaises(coupons.CouponExpired):
            coupons.redeem(self.conn, "OLD5", "u1", NOW)

    def test_concurrent_redemptions_only_one_succeeds(self):
        results = []

        def attempt():
            conn = db.connect(self.url)
            try:
                coupons.redeem(conn, "WELCOME10", "u1", NOW)
                results.append("ok")
            except coupons.CouponAlreadyUsed:
                results.append("used")
            finally:
                conn.close()

        for _ in range(20):
            t = threading.Thread(target=attempt)
            t.start()
            t.join()
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(wallet.balance(self.conn, "u1"), 1000)
EOF

commit "2026-10-21T14:05:00+00:00" "Ines Calder" "Coupons: redemption endpoint" \
"POST /coupons/redeem credits the coupon to the wallet. Includes a concurrency test:
20 threads redeem the same coupon and exactly one wins."

cat >> tillpoint/schema.sql <<'EOF'

CREATE TABLE IF NOT EXISTS wallet_entries (
    id            INTEGER PRIMARY KEY,
    user_id       TEXT NOT NULL,
    amount_cents  INTEGER NOT NULL,
    kind          TEXT NOT NULL,
    ref           TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
EOF

cat > tillpoint/worker/stats.py <<'EOF'
"""Per-process counters for the worker's heartbeat log line.

Every consumer thread in this process reports here, and the heartbeat thread reads a snapshot.
Each replica logs its own numbers; nothing aggregates them across replicas or persists them.
"""
import threading


class Stats:
    def __init__(self):
        self._lock = threading.Lock()
        self._handled = 0
        self._failed = 0

    def handled(self):
        with self._lock:
            self._handled += 1

    def failed(self):
        with self._lock:
            self._failed += 1

    def snapshot(self):
        with self._lock:
            return {"handled": self._handled, "failed": self._failed}
EOF

cat > tillpoint/worker/cashback.py <<'EOF'
"""Cashback: 5 % of every paid order goes back to the customer's wallet.

Consumes order.paid from its own queue, promotions.order-paid, on CONSUMER_THREADS threads per
worker process.
"""
import logging

from .. import wallet
from ..clock import utcnow

QUEUE = "promotions.order-paid"
CASHBACK_PERCENT = 5
CONSUMER_THREADS = 4

log = logging.getLogger(__name__)


def handle(conn, body, now):
    amount = body["total_cents"] * CASHBACK_PERCENT // 100
    if amount <= 0:
        return
    wallet.credit(conn, body["user_id"], amount)
    conn.execute("INSERT INTO wallet_entries (user_id, amount_cents, kind, ref, created_at) "
                 "VALUES (?, ?, 'cashback', ?, ?)",
                 (body["user_id"], amount, f"order:{body['order_id']}", now))


def consume(broker, conn, stats, stop):
    while not stop.is_set():
        msg = broker.receive(QUEUE, visibility_timeout=30)
        if msg is None:
            stop.wait(1.0)
            continue
        try:
            handle(conn, msg.body, utcnow())
        except Exception:
            stats.failed()
            log.exception("cashback failed for message %s; it will be redelivered", msg.id)
            continue
        broker.ack(msg)
        stats.handled()
EOF

cat > tillpoint/worker/__main__.py <<'EOF'
"""The worker process: queue consumers on threads. deploy/worker.yaml runs it."""
import logging
import signal
import threading

from .. import db, orders
from ..broker import Broker
from . import cashback
from .stats import Stats

log = logging.getLogger("tillpoint.worker")


def heartbeat(stats, stop):
    while not stop.wait(60):
        log.info("worker alive %s", stats.snapshot())


def main():
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    stats = Stats()
    threads = [threading.Thread(target=orders.consume, args=(Broker(db.connect()), db.connect(), stop),
                                name="orders")]
    threads += [threading.Thread(target=cashback.consume,
                                 args=(Broker(db.connect()), db.connect(), stats, stop),
                                 name=f"cashback-{i}")
                for i in range(cashback.CONSUMER_THREADS)]
    threads.append(threading.Thread(target=heartbeat, args=(stats, stop), name="heartbeat"))
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
EOF

cat > tests/test_cashback.py <<'EOF'
from tests.helpers import DbTest
from tillpoint import wallet
from tillpoint.worker import cashback
from tillpoint.worker.stats import Stats


class CashbackTest(DbTest):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO wallets VALUES ('u1', 0)")

    def test_five_percent_back(self):
        cashback.handle(self.conn, {"order_id": 7, "user_id": "u1", "total_cents": 4000}, "2026-10-23T10:00:00Z")
        self.assertEqual(wallet.balance(self.conn, "u1"), 200)
        ref = self.conn.execute("SELECT ref FROM wallet_entries").fetchone()[0]
        self.assertEqual(ref, "order:7")

    def test_stats(self):
        s = Stats()
        s.handled()
        s.handled()
        s.failed()
        self.assertEqual(s.snapshot(), {"handled": 2, "failed": 1})
EOF

commit "2026-10-23T11:20:00+00:00" "Ravi Menon" "Worker: cashback on order.paid" \
"5 % of each paid order back to the wallet, from the promotions.order-paid queue, four consumer
threads per worker. Heartbeat log line with handled/failed counts."

python3 - <<'EOF'
import pathlib
p = pathlib.Path("tillpoint/schema.sql")
s = p.read_text()
s = s.replace("    used_at       TEXT\n);", "    used_at       TEXT,\n    reminder_sent INTEGER NOT NULL DEFAULT 0\n);")
p.write_text(s)
EOF

cat > tillpoint/mailer.py <<'EOF'
"""Outbound email through the provider's HTTP API (logged only outside production)."""
import logging

log = logging.getLogger(__name__)


class Mailer:
    def send(self, to, subject, text):
        log.info("mail to=%s subject=%r", to, subject)
EOF

cat > tillpoint/jobs.py <<'EOF'
"""Daily jobs the worker runs."""
import datetime as dt

REMINDER_SUBJECT = "Your Tillpoint coupon expires tomorrow"


def send_expiry_reminders(conn, mailer, now, horizon_hours=24):
    """Email each holder whose coupon expires within the next day, once per coupon."""
    until = (dt.datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
             + dt.timedelta(hours=horizon_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = conn.execute(
        "SELECT code, assigned_to, amount_cents, expires_at FROM coupons "
        "WHERE used = 0 AND reminder_sent = 0 AND assigned_to IS NOT NULL "
        "AND expires_at > ? AND expires_at <= ?", (now, until)).fetchall()
    for code, user_id, amount, expires_at in rows:
        mailer.send(user_id, REMINDER_SUBJECT,
                    f"Your {amount / 100:.2f} coupon {code} expires at {expires_at}.")
        conn.execute("UPDATE coupons SET reminder_sent = 1 WHERE code = ?", (code,))
    return len(rows)
EOF

cat > tillpoint/worker/scheduler.py <<'EOF'
"""Runs a function once a day at a fixed UTC time, on a daemon thread in the worker."""
import datetime as dt
import logging
import threading

log = logging.getLogger(__name__)


class DailyJob(threading.Thread):
    def __init__(self, name, at, fn, stop):
        super().__init__(name=name, daemon=True)
        self.at, self.fn, self.stop = at, fn, stop

    def next_run(self, now):
        run = now.replace(hour=self.at.hour, minute=self.at.minute, second=0, microsecond=0)
        return run if run > now else run + dt.timedelta(days=1)

    def run(self):
        while not self.stop.is_set():
            now = dt.datetime.now(dt.timezone.utc)
            if self.stop.wait((self.next_run(now) - now).total_seconds()):
                return
            try:
                self.fn()
            except Exception:
                log.exception("daily job %s failed", self.name)
EOF

python3 - <<'EOF'
import pathlib
p = pathlib.Path("tillpoint/worker/__main__.py")
s = p.read_text()
s = s.replace('''import logging
import signal
import threading

from .. import db, orders
from ..broker import Broker
from . import cashback
from .stats import Stats
''', '''import datetime as dt
import logging
import signal
import threading

from .. import db, jobs, orders
from ..broker import Broker
from ..clock import utcnow
from ..mailer import Mailer
from . import cashback
from .scheduler import DailyJob
from .stats import Stats
''')
s = s.replace('''def main():''', '''def expiry_reminders():
    conn = db.connect()
    try:
        sent = jobs.send_expiry_reminders(conn, Mailer(), utcnow())
        log.info("expiry reminders sent: %d", sent)
    finally:
        conn.close()


def main():''')
s = s.replace('''    for t in threads:
        t.start()
''', '''    for t in threads:
        t.start()
    DailyJob("expiry-reminders", dt.time(2, 0), expiry_reminders, stop).start()
''')
p.write_text(s)
EOF

cat > tests/test_jobs.py <<'EOF'
from tests.helpers import DbTest
from tillpoint import jobs
from tillpoint.worker.scheduler import DailyJob
import datetime as dt
import threading


class FakeMailer:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, text):
        self.sent.append(to)


class RemindersTest(DbTest):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO coupons (code, amount_cents, expires_at, assigned_to) VALUES "
                          "('A', 500, '2026-10-26T20:00:00Z', 'u1'), ('B', 500, '2026-11-30T00:00:00Z', 'u2')")

    def test_reminds_once(self):
        m = FakeMailer()
        self.assertEqual(jobs.send_expiry_reminders(self.conn, m, "2026-10-26T02:00:00Z"), 1)
        self.assertEqual(jobs.send_expiry_reminders(self.conn, m, "2026-10-26T02:00:00Z"), 0)
        self.assertEqual(m.sent, ["u1"])

    def test_next_run(self):
        job = DailyJob("t", dt.time(2, 0), lambda: None, threading.Event())
        now = dt.datetime(2026, 10, 26, 3, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(job.next_run(now), dt.datetime(2026, 10, 27, 2, 0, tzinfo=dt.timezone.utc))
EOF

commit "2026-10-26T15:45:00+00:00" "Dana Whitlock" "Worker: daily coupon expiry reminders" \
"Every day at 02:00 UTC the worker emails holders whose coupon expires within 24 hours, once
per coupon (reminder_sent). Runs inside the worker, so no separate CronJob to deploy."
