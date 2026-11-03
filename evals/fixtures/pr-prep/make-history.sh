#!/usr/bin/env bash
# Build the pr-prep fixture's git repository: orderdesk, a small stdlib-Python orders service
# whose CSV export finance pulls every week. main carries about seven months of history
# (160 commits, 2026-03 to 2026-09, plus two after the branch point); the author's branch
# feature/export-filters (4 commits, 2026-10) adds date-range and status filters to the
# export (#412) and is left checked out. The plants are listed in README.md next to this
# script, and the answer key is ../pr-prep.answers.md.
# Idempotent: removes and rebuilds repo/ each time. Needs only git, awk, sed and python3.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

commit() { # commit <iso-date> <author> <subject> [body] — stages everything first
  git add -A
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  GIT_AUTHOR_NAME="$2" GIT_COMMITTER_NAME="$2" \
  GIT_AUTHOR_EMAIL="$(echo "$2" | tr 'A-Z ' 'a-z.')@example.invalid" \
  GIT_COMMITTER_EMAIL="$(echo "$2" | tr 'A-Z ' 'a-z.')@example.invalid" \
  git commit -q -m "$3" ${4:+-m "$4"}
}

insert_before() { # insert_before <file> <marker> <line>: the line goes above the marker line
  awk -v line="$3" -v mark="$2" 'index($0, mark) { print line } { print }' "$1" > "$1.tmp"
  mv "$1.tmp" "$1"
}

subst() { # subst <file> <sed expression>
  sed -i.bak "$2" "$1" && rm "$1.bak"
}

mkdir -p orderdesk tests docs .github/workflows

# ===================================================================== the initial service
cat > orderdesk/__init__.py <<'EOF'
"""orderdesk: orders, and the CSV export finance pulls every week."""
__version__ = "1.4.0"
EOF

cat > orderdesk/models.py <<'EOF'
"""Order records as the store returns them."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

STATUSES = ("pending", "paid", "shipped", "delivered", "cancelled", "refunded")


@dataclass(frozen=True)
class Order:
    order_id: str
    placed_on: date
    status: str
    customer_id: str
    customer_name: str = ""
    customer_email: str = ""
    country: str = ""
    currency: str = "EUR"
    subtotal_cents: int = 0
    tax_cents: int = 0
    shipping_cents: int = 0
    discount_cents: int = 0
    total_cents: int = 0
    items_count: int = 0
    channel: str = "web"
    coupon_code: str = ""
    payment_method: str = ""
    shipped_on: Optional[date] = None
    carrier: str = ""
    tracking_number: str = ""
    warehouse: str = ""
    sales_rep: str = ""
    notes: str = ""
EOF

cat > orderdesk/store.py <<'EOF'
"""Orders in SQLite. In memory by default; the service passes a file path."""
import dataclasses
import json
import sqlite3
from datetime import date

from orderdesk.models import Order

_DATES = ("placed_on", "shipped_on")


class OrderStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, "
                        "placed_on TEXT NOT NULL, status TEXT NOT NULL, body TEXT NOT NULL)")

    def add(self, order):
        body = {k: (v.isoformat() if isinstance(v, date) else v)
                for k, v in dataclasses.asdict(order).items()}
        with self.db:
            self.db.execute("INSERT INTO orders VALUES (?, ?, ?, ?)",
                            (order.order_id, order.placed_on.isoformat(), order.status, json.dumps(body)))

    def all(self):
        rows = self.db.execute("SELECT body FROM orders ORDER BY placed_on, order_id")
        return [self._load(body) for (body,) in rows]

    @staticmethod
    def _load(body):
        data = json.loads(body)
        for key in _DATES:
            if data.get(key):
                data[key] = date.fromisoformat(data[key])
        return Order(**data)
EOF

cat > orderdesk/prefs.py <<'EOF'
"""Per-user preferences, kept between sessions (SQLite)."""
import sqlite3


class PrefsStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS prefs (user TEXT NOT NULL, key TEXT NOT NULL, "
                        "value TEXT NOT NULL, PRIMARY KEY (user, key))")

    def get(self, user, key, default=None):
        row = self.db.execute("SELECT value FROM prefs WHERE user = ? AND key = ?", (user, key)).fetchone()
        return row[0] if row else default

    def set(self, user, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO prefs VALUES (?, ?, ?)", (user, key, value))
EOF

cat > orderdesk/export.py <<'EOF'
"""CSV export of orders. The column registry below is the export format;
docs/export-formats.md describes it for the people who read the files."""
import csv
from dataclasses import dataclass
from typing import Callable

FLUSH_EVERY = 200   # rows buffered before each write to the output


class UnknownColumn(ValueError):
    pass


def text(value):
    return "" if value is None else str(value)


def iso_date(value):
    return "" if value is None else value.isoformat()


def money(cents):
    """Cents as a decimal string, two places, no thousands separator."""
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def integer(value):
    return "" if value is None else str(int(value))


@dataclass(frozen=True)
class Column:
    name: str
    header: str
    attr: str
    fmt: Callable = text

    def render(self, order):
        return self.fmt(getattr(order, self.attr))


COLUMNS = [
    Column("order_id", "Order", "order_id"),
    Column("placed_on", "Placed", "placed_on", iso_date),
    Column("status", "Status", "status"),
    Column("customer_id", "Cust. ID", "customer_id"),
    Column("total", "Total", "total_cents", money),
    # end of columns
]

BY_NAME = {c.name: c for c in COLUMNS}


def select_columns(names=None):
    """The Column objects for `names`, in that order; every column when names is empty."""
    if not names:
        return list(COLUMNS)
    unknown = [n for n in names if n not in BY_NAME]
    if unknown:
        raise UnknownColumn(f"unknown export column(s): {', '.join(unknown)}")
    return [BY_NAME[n] for n in names]


def export_csv(orders, out, columns=None):
    """Write orders to `out` as CSV, header first. Returns the number of data rows."""
    columns = columns or list(COLUMNS)
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow([c.header for c in columns])
    buffer, count = [], 0
    for order in orders:
        buffer.append([c.render(order) for c in columns])
        count += 1
        if len(buffer) >= FLUSH_EVERY:
            writer.writerows(buffer)
            buffer.clear()
    writer.writerows(buffer)
    return count
EOF

cat > orderdesk/api.py <<'EOF'
"""HTTP entry points. handle_export is what GET /export runs."""
import io
import json
from http import HTTPStatus
from urllib.parse import parse_qs

from orderdesk.export import UnknownColumn, export_csv, select_columns

COLUMNS_PREF = "export.columns"


def _one(params, key):
    values = params.get(key)
    return values[-1] if values else None


def _error(message):
    return HTTPStatus.BAD_REQUEST, {"Content-Type": "application/json"}, json.dumps({"error": message})


def handle_export(store, prefs, user, query):
    """GET /export?columns=a,b,c -> (status, headers, body).

    The column choice is remembered per user: an export without `columns` uses the
    user's last choice, or every column the first time."""
    params = parse_qs(query or "")
    requested = _one(params, "columns")
    remembered = prefs.get(user, COLUMNS_PREF)
    try:
        columns = select_columns((requested or remembered or "").split(",") if (requested or remembered) else None)
    except UnknownColumn as exc:
        return _error(str(exc))
    if requested is not None:
        prefs.set(user, COLUMNS_PREF, requested)
    out = io.StringIO()
    count = export_csv(store.all(), out, columns)
    headers = {"Content-Type": "text/csv; charset=utf-8",
               "Content-Disposition": 'attachment; filename="orders.csv"',
               "X-Row-Count": str(count)}
    return HTTPStatus.OK, headers, out.getvalue()
EOF

cat > orderdesk/carriers.py <<'EOF'
"""Carrier tracking links shown next to shipped orders."""

TRACKING_URLS = {
    "postnl": "https://tracking.carriers.example/postnl/{}",
    # end of carriers
}


def tracking_url(carrier, number):
    template = TRACKING_URLS.get((carrier or "").lower())
    return template.format(number) if template and number else ""
EOF

cat > orderdesk/countries.py <<'EOF'
"""Countries we ship to, and the shipping zone each is priced in."""

SHIPPING_ZONES = {
    "NL": "domestic",
    # end of zones
}


class UnsupportedCountry(KeyError):
    pass


def zone_for(code):
    try:
        return SHIPPING_ZONES[code.upper()]
    except KeyError:
        raise UnsupportedCountry(code) from None
EOF

cat > orderdesk/holidays.py <<'EOF'
"""Days the warehouse is closed: no picking, no carrier collection."""
from datetime import date

WAREHOUSE_CLOSED = {
    date(2026, 1, 1),
    # end of closures
}


def is_open(day):
    return day.weekday() < 5 and day not in WAREHOUSE_CLOSED
EOF

cat > docs/export-formats.md <<'EOF'
# Export formats

`GET /export` returns orders as CSV: UTF-8, comma-separated, CRLF line endings, header row first.
Finance imports it into the month-end workbook, so a change to a header or a value format
breaks their import. Say so in the release notes when one changes.

## Parameters

| Parameter | Meaning |
|---|---|
| `columns` | Comma-separated column names, in the order wanted. Omitted: the user's last choice, or every column. An unknown name returns 400. |

## Values

- Dates are ISO 8601 (`2026-03-14`).
- Money is a decimal string in the order's currency, two decimals (`1234.50`), no thousands separator.
- An empty value is an empty field, never `null` or `None`.
- Fields containing commas, quotes or newlines are quoted (RFC 4180).

## Columns

In export order. `columns=` takes the name.

| Name | Header | Value |
|---|---|---|
| `order_id` | Order | The order number |
| `placed_on` | Placed | The day the order was placed |
| `status` | Status | One of pending, paid, shipped, delivered, cancelled, refunded |
| `customer_id` | Cust. ID | The customer account |
| `total` | Total | The amount charged, tax and shipping included |
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_export.py <<'EOF'
import io
import unittest
from datetime import date

from orderdesk import export
from orderdesk.export import COLUMNS, UnknownColumn, export_csv, money, select_columns
from orderdesk.models import Order


def order(n=1, **kw):
    base = dict(order_id=f"A-{1000 + n}", placed_on=date(2026, 3, 14), status="paid",
                customer_id=f"C-{n}", total_cents=123450)
    base.update(kw)
    return Order(**base)


class MoneyTest(unittest.TestCase):
    def test_two_decimals(self):
        self.assertEqual(money(123450), "1234.50")
        self.assertEqual(money(5), "0.05")

    def test_negative(self):
        self.assertEqual(money(-250), "-2.50")

    def test_none_is_empty(self):
        self.assertEqual(money(None), "")


class SelectColumnsTest(unittest.TestCase):
    def test_default_is_every_column(self):
        self.assertEqual(select_columns(), list(COLUMNS))

    def test_keeps_requested_order(self):
        self.assertEqual([c.name for c in select_columns(["status", "order_id"])], ["status", "order_id"])

    def test_unknown_raises(self):
        with self.assertRaises(UnknownColumn):
            select_columns(["order_id", "colour"])


class ExportCsvTest(unittest.TestCase):
    def export(self, orders, columns=None):
        out = io.StringIO()
        count = export_csv(orders, out, columns)
        return count, out.getvalue()

    def test_header_first(self):
        _, body = self.export([order()])
        self.assertEqual(body.split("\r\n")[0].split(","), [c.header for c in COLUMNS])

    def test_row_count_returned(self):
        count, _ = self.export([order(1), order(2), order(3)])
        self.assertEqual(count, 3)

    def test_crlf_line_endings(self):
        _, body = self.export([order()])
        self.assertTrue(body.endswith("\r\n"))

    def test_writes_every_row_past_the_flush_size(self):
        n = export.FLUSH_EVERY * 2 + 3
        count, body = self.export([order(i) for i in range(n)], select_columns(["order_id"]))
        self.assertEqual(count, n)
        self.assertEqual(len(body.strip().split("\r\n")), n + 1)
EOF

cat > tests/test_api.py <<'EOF'
import unittest
from datetime import date

from orderdesk.api import handle_export
from orderdesk.models import STATUSES, Order
from orderdesk.prefs import PrefsStore


class ListStore:
    def __init__(self, orders):
        self.orders = list(orders)

    def all(self):
        return list(self.orders)


def order(n, status="paid", day=14):
    return Order(order_id=f"A-{1000 + n}", placed_on=date(2026, 3, day), status=status,
                 customer_id=f"C-{n}", total_cents=1000 * n)


class HandleExportTest(unittest.TestCase):
    def setUp(self):
        self.prefs = PrefsStore()

    def test_export_returns_csv(self):
        status, headers, body = handle_export(ListStore([order(1), order(2)]), self.prefs, "dana", "")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/csv"))
        self.assertEqual(headers["X-Row-Count"], "2")
        self.assertEqual(len(body.strip().splitlines()), 3)

    def test_unknown_column_is_400(self):
        status, _, body = handle_export(ListStore([]), self.prefs, "dana", "columns=order_id,colour")
        self.assertEqual(status, 400)
        self.assertIn("colour", body)

    def test_columns_remembered_per_user(self):
        store = ListStore([order(1)])
        handle_export(store, self.prefs, "dana", "columns=status,order_id")
        _, _, mine = handle_export(store, self.prefs, "dana", "")
        _, _, theirs = handle_export(store, self.prefs, "sam", "")
        self.assertEqual(mine.splitlines()[0].split(",")[0], "Status")
        self.assertEqual(len(mine.splitlines()[0].split(",")), 2)
        self.assertGreater(len(theirs.splitlines()[0].split(",")), 2)

    def test_export_includes_every_status(self):
        orders = [order(i, status=s) for i, s in enumerate(STATUSES, 1)]
        _, headers, body = handle_export(ListStore(orders), self.prefs, "dana", "")
        self.assertEqual(headers["X-Row-Count"], str(len(STATUSES)))
        for s in STATUSES:
            self.assertIn(f",{s},", body)
EOF

cat > tests/test_prefs.py <<'EOF'
import unittest

from orderdesk.prefs import PrefsStore


class PrefsStoreTest(unittest.TestCase):
    def test_default_when_unset(self):
        self.assertEqual(PrefsStore().get("dana", "export.columns", "all"), "all")

    def test_set_then_get_per_user(self):
        prefs = PrefsStore()
        prefs.set("dana", "export.columns", "status")
        self.assertEqual(prefs.get("dana", "export.columns"), "status")
        self.assertIsNone(prefs.get("sam", "export.columns"))

    def test_set_overwrites(self):
        prefs = PrefsStore()
        prefs.set("dana", "k", "1")
        prefs.set("dana", "k", "2")
        self.assertEqual(prefs.get("dana", "k"), "2")
EOF

cat > tests/test_registries.py <<'EOF'
import unittest
from datetime import date

from orderdesk.carriers import tracking_url
from orderdesk.countries import UnsupportedCountry, zone_for
from orderdesk.holidays import is_open


class RegistriesTest(unittest.TestCase):
    def test_tracking_url(self):
        self.assertTrue(tracking_url("PostNL", "3S123").endswith("/3S123"))
        self.assertEqual(tracking_url("unknown", "1"), "")

    def test_zone_for(self):
        self.assertEqual(zone_for("nl"), "domestic")
        with self.assertRaises(UnsupportedCountry):
            zone_for("XX")

    def test_closed_on_new_year(self):
        self.assertFalse(is_open(date(2026, 1, 1)))
EOF

cat > README.md <<'EOF'
# orderdesk

Orders for the shop, and the CSV export finance pulls every week (`GET /export`).
Python 3.10+, standard library only.

- `orderdesk/export.py` — the export and its column registry; the format is described in
  [docs/export-formats.md](docs/export-formats.md)
- `orderdesk/api.py` — the HTTP entry points
- `orderdesk/store.py`, `orderdesk/prefs.py` — orders and per-user preferences in SQLite
EOF

commit "2026-03-02T09:12:00+00:00" "Marta Kowalski" "Initial import of orderdesk from the monolith" \
  "Orders, the CSV export with per-user column choice, and the shipping registries, moved out of shop-legacy."

# ===================================================================== the history
# Five kinds of commit, interleaved over seven months:
#   e  the export format (24): a column, a header rename, or a flush-size tweak
#   k  a carrier (20)   c  a shipping country (80)   h  a warehouse closure (30)   m  housekeeping (5)
DATES=($(python3 - <<'PY'
import datetime as d
t = d.datetime(2026, 3, 3, 9, 30, tzinfo=d.timezone.utc)
for i in range(159):
    print((t + d.timedelta(hours=31 * i + (i * 7) % 5, minutes=(i * 13) % 60)).isoformat())
PY
))
SCHEDULE=$(python3 - <<'PY'
kinds = [("m", 5), ("e", 24), ("k", 20), ("c", 80), ("h", 30)]
slots = sorted(((j + 0.5) / n + i * 1e-4, k) for i, (k, n) in enumerate(kinds) for j in range(n))
print(" ".join(k for _, k in slots))
PY
)

COLS=(
  'customer_name|Customer|customer_name|text|Billing name'
  'customer_email|Email|customer_email|text|Billing email address'
  'country|Country|country|text|Shipping country, ISO 3166-1 alpha-2'
  'currency|Currency|currency|text|ISO 4217 code of the amounts in the row'
  'subtotal|Subtotal|subtotal_cents|money|Line items before tax, shipping and discount'
  'tax|Tax|tax_cents|money|Tax charged'
  'shipping|Shipping|shipping_cents|money|Shipping charged'
  'discount|Discount|discount_cents|money|Discount applied, as a positive amount'
  'items|Items|items_count|integer|Number of items in the order'
  'channel|Channel|channel|text|web, pos or marketplace'
  'coupon|Coupon|coupon_code|text|Coupon code used, if any'
  'payment_method|Payment method|payment_method|text|card, transfer, invoice or wallet'
  'shipped_on|Shipped on|shipped_on|iso_date|The day the carrier collected it; empty until shipped'
  'carrier|Carrier|carrier|text|Carrier code'
  'tracking|Tracking number|tracking_number|text|The carrier tracking number'
  'warehouse|Warehouse|warehouse|text|Warehouse that picked the order'
  'sales_rep|Sales rep|sales_rep|text|Account manager, for B2B orders'
  'notes|Notes|notes|text|Free text from the customer; may contain commas and newlines (quoted)'
)
EXPORT_STEPS="c c r1 c c f500 c c c c r2 c c f1000 c c c r3 c c f2000 c c c"

add_column() { # add_column <spec>
  IFS='|' read -r name header attr fmt doc <<< "$1"
  if [ "$fmt" = text ]; then
    insert_before orderdesk/export.py "# end of columns" "    Column(\"$name\", \"$header\", \"$attr\"),"
  else
    insert_before orderdesk/export.py "# end of columns" "    Column(\"$name\", \"$header\", \"$attr\", $fmt),"
  fi
  printf '| `%s` | %s | %s |\n' "$name" "$header" "$doc" >> docs/export-formats.md
  echo "Add $header column to the orders export"
}

CARRIERS="dhl ups dpd gls fedex bpost colissimo royalmail hermes correos poste_italiane inpost \
  postnord bring posti ctt an_post austrian_post swiss_post sendle"
COUNTRIES="BE:eu-1 DE:eu-1 LU:eu-1 FR:eu-2 AT:eu-2 DK:eu-2 IE:eu-2 IT:eu-2 ES:eu-2 PT:eu-2 SE:eu-2 FI:eu-3 \
  PL:eu-2 CZ:eu-2 SK:eu-3 HU:eu-3 SI:eu-3 HR:eu-3 RO:eu-3 BG:eu-3 GR:eu-3 CY:eu-3 MT:eu-3 EE:eu-3 \
  LV:eu-3 LT:eu-3 GB:europe NO:europe CH:europe IS:europe LI:europe MC:eu-2 AD:europe SM:europe \
  RS:europe ME:europe MK:europe AL:europe BA:europe MD:europe UA:europe TR:europe GE:world-1 \
  AM:world-1 US:world-1 CA:world-1 MX:world-2 BR:world-2 AR:world-2 CL:world-2 CO:world-2 PE:world-2 \
  UY:world-2 JP:world-1 KR:world-1 SG:world-1 HK:world-1 TW:world-1 AU:world-2 NZ:world-2 IL:world-1 \
  AE:world-1 SA:world-2 QA:world-2 IN:world-2 TH:world-2 MY:world-2 ID:world-2 PH:world-2 VN:world-2 \
  ZA:world-2 MA:world-2 TN:world-2 EG:world-2 KE:world-2 NG:world-2 GH:world-2 CR:world-2 PA:world-2 \
  DO:world-2 EC:world-2"
CLOSURES="2026-04-03 2026-04-06 2026-04-27 2026-05-05 2026-05-14 2026-05-25 2026-06-19 2026-07-03 \
  2026-07-31 2026-08-14 2026-08-28 2026-09-11 2026-10-02 2026-10-30 2026-11-27 2026-12-24 2026-12-25 \
  2026-12-26 2026-12-31 2027-01-01 2027-03-26 2027-03-29 2027-04-27 2027-05-05 2027-05-06 2027-05-17 \
  2027-07-30 2027-08-27 2027-12-24 2027-12-31"
set -- $CARRIERS; CARRIER_LIST=("$@")
set -- $COUNTRIES; COUNTRY_LIST=("$@")
set -- $CLOSURES; CLOSURE_LIST=("$@")
set -- $EXPORT_STEPS; EXPORT_LIST=("$@")

misc_step() { # misc_step <n>: prints the subject
  case $1 in
    1) printf 'test:\n\tpython3 -m unittest discover -s tests -t . -v\n' > Makefile
       cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: make test
EOF
       echo "Add Makefile and CI running the unit tests" ;;
    2) cat > CONTRIBUTING.md <<'EOF'
# Contributing

- Branch from `main` as `feature/<topic>` or `fix/<topic>`.
- Reference the issue in the commit message, e.g. `(#123)`.
- `make test` runs what CI runs. Keep it green.
- One reviewer approves before merge; squash or rebase, no merge commits on `main`.
EOF
       echo "Add CONTRIBUTING" ;;
    3) printf '\n## Running the tests\n\n    make test\n' >> README.md
       echo "README: how to run the tests" ;;
    4) printf '__pycache__/\n*.pyc\n*.sqlite3\n.venv/\n' > .gitignore
       echo "Ignore bytecode, local databases and venvs" ;;
    5) cat > tests/test_store.py <<'EOF'
import unittest
from datetime import date

from orderdesk.models import Order
from orderdesk.store import OrderStore


class OrderStoreTest(unittest.TestCase):
    def test_round_trip_keeps_dates(self):
        store = OrderStore()
        store.add(Order("A-1", date(2026, 3, 1), "shipped", "C-1", shipped_on=date(2026, 3, 2)))
        (got,) = store.all()
        self.assertEqual(got.shipped_on, date(2026, 3, 2))

    def test_all_sorted_by_day_then_id(self):
        store = OrderStore()
        for oid, day in (("A-3", 2), ("A-2", 1), ("A-1", 2)):
            store.add(Order(oid, date(2026, 3, day), "paid", "C-1"))
        self.assertEqual([o.order_id for o in store.all()], ["A-2", "A-1", "A-3"])
EOF
       echo "Add OrderStore tests" ;;
  esac
}

export_step() { # export_step <n>: prints the subject
  case ${EXPORT_LIST[$(($1 - 1))]} in
    c)     add_column "${COLS[$ci]}"; ci=$((ci + 1)) ;;
    r1)    subst orderdesk/export.py 's/Column("order_id", "Order", /Column("order_id", "Order ID", /'
           subst docs/export-formats.md 's/| Order |/| Order ID |/'
           echo 'Rename the "Order" header to "Order ID"' ;;
    r2)    subst orderdesk/export.py 's/Column("placed_on", "Placed", /Column("placed_on", "Placed on", /'
           subst docs/export-formats.md 's/| Placed |/| Placed on |/'
           echo 'Rename the "Placed" header to "Placed on"' ;;
    r3)    subst orderdesk/export.py 's/Column("customer_id", "Cust\. ID", /Column("customer_id", "Customer ID", /'
           subst docs/export-formats.md 's/| Cust\. ID |/| Customer ID |/'
           echo 'Rename the "Cust. ID" header to "Customer ID"' ;;
    f*)    n=${EXPORT_LIST[$(($1 - 1))]#f}
           subst orderdesk/export.py "s/^FLUSH_EVERY = [0-9]*/FLUSH_EVERY = $n/"
           echo "Buffer $n rows per export write" ;;
  esac
}

ci=0; ei=0; ki=0; cc=0; hi=0; mi=0; i=0
for kind in $SCHEDULE; do
  when=${DATES[$i]}; i=$((i + 1))
  case $kind in
    m) mi=$((mi + 1)); subject=$(misc_step $mi); who="Marta Kowalski" ;;
    e) ei=$((ei + 1)); who=$([ $((ei % 2)) = 0 ] && echo "Tom Achebe" || echo "Marta Kowalski")
       # export_step runs in this shell: add_column advances $ci
       export_step $ei > .subject; subject=$(cat .subject); rm .subject ;;
    k) c=${CARRIER_LIST[$ki]}; ki=$((ki + 1)); who="Tom Achebe"
       insert_before orderdesk/carriers.py "# end of carriers" "    \"$c\": \"https://tracking.carriers.example/$c/{}\","
       subject="Add $c tracking links" ;;
    c) pair=${COUNTRY_LIST[$cc]}; cc=$((cc + 1)); who="Lena Fischer"
       insert_before orderdesk/countries.py "# end of zones" "    \"${pair%%:*}\": \"${pair#*:}\","
       subject="Ship to ${pair%%:*} (zone ${pair#*:})" ;;
    h) d=${CLOSURE_LIST[$hi]}; hi=$((hi + 1)); who=$([ $((hi % 3)) = 0 ] && echo "Marta Kowalski" || echo "Lena Fischer")
       y=${d%%-*}; md=${d#*-}; mo=${md%%-*}; dd=${md#*-}
       insert_before orderdesk/holidays.py "# end of closures" "    date($y, $((10#$mo)), $((10#$dd))),"
       subject="Warehouse closed on $d" ;;
  esac
  commit "$when" "$who" "$subject"
done
# misc_step ran in a subshell; make sure its files landed anyway
[ -f Makefile ] && [ -f tests/test_store.py ] || { echo "misc steps missing" >&2; exit 1; }

BASE=$(git rev-parse HEAD)

# ===================================================================== the author's branch
git switch -q -c feature/export-filters

# --- 1. the refactor: the column registry moves to orderdesk/columns.py, select_columns -> resolve_columns
{
  cat <<'EOF'
"""The export's column registry and value formatters, moved out of export.py so the
filters and any later exporter can share them."""
from dataclasses import dataclass
from typing import Callable


EOF
  awk '/^class UnknownColumn/ { on = 1 } /^def export_csv/ { on = 0 } on' orderdesk/export.py \
    | sed 's/select_columns/resolve_columns/'
} > orderdesk/columns.py
python3 - <<'PY'
import re, pathlib
p = pathlib.Path("orderdesk/columns.py")
p.write_text(p.read_text().rstrip("\n") + "\n")
PY
flush=$(grep '^FLUSH_EVERY' orderdesk/export.py)
cat > orderdesk/export.py <<EOF
"""CSV export of orders. The columns live in orderdesk/columns.py;
docs/export-formats.md describes the format for the people who read the files."""
import csv

from orderdesk.columns import COLUMNS, UnknownColumn, resolve_columns  # noqa: F401 (re-exported)

$flush


class CsvExporter:
    """Writes orders as CSV rows for a fixed list of columns, buffering
    \`flush_every\` rows between writes to the output."""

    def __init__(self, columns=None, flush_every=None):
        self.columns = list(columns or COLUMNS)
        self.flush_every = flush_every or FLUSH_EVERY

    def header(self):
        return [c.header for c in self.columns]

    def row(self, order):
        return [c.render(order) for c in self.columns]

    def write(self, orders, out):
        """Header first, then one row per order. Returns the number of data rows."""
        writer = csv.writer(out, lineterminator="\r\n")
        writer.writerow(self.header())
        buffer, count = [], 0
        for order in orders:
            buffer.append(self.row(order))
            count += 1
            if len(buffer) >= self.flush_every:
                writer.writerows(buffer)
                buffer.clear()
        writer.writerows(buffer)
        return count


def export_csv(orders, out, columns=None):
    """Write orders to \`out\` as CSV, header first. Returns the number of data rows."""
    return CsvExporter(columns).write(orders, out)
EOF
subst orderdesk/api.py 's/^from orderdesk.export import UnknownColumn, export_csv, select_columns$/from orderdesk.columns import UnknownColumn, resolve_columns\
from orderdesk.export import export_csv/'
subst orderdesk/api.py 's/columns = select_columns(/columns = resolve_columns(/'

cat > tests/test_columns.py <<'EOF'
import unittest

from orderdesk.columns import COLUMNS, BY_NAME, UnknownColumn, iso_date, money, resolve_columns


class MoneyTest(unittest.TestCase):
    def test_two_decimals(self):
        self.assertEqual(money(123450), "1234.50")
        self.assertEqual(money(5), "0.05")

    def test_negative(self):
        self.assertEqual(money(-250), "-2.50")

    def test_none_is_empty(self):
        self.assertEqual(money(None), "")


class IsoDateTest(unittest.TestCase):
    def test_none_is_empty(self):
        self.assertEqual(iso_date(None), "")


class ResolveColumnsTest(unittest.TestCase):
    def test_default_is_every_column(self):
        self.assertEqual(resolve_columns(), list(COLUMNS))

    def test_keeps_requested_order(self):
        self.assertEqual([c.name for c in resolve_columns(["status", "order_id"])], ["status", "order_id"])

    def test_unknown_raises(self):
        with self.assertRaises(UnknownColumn):
            resolve_columns(["order_id", "colour"])

    def test_names_are_unique(self):
        self.assertEqual(len(BY_NAME), len(COLUMNS))
EOF

cat > tests/test_export.py <<'EOF'
import io
import unittest
from datetime import date

from orderdesk import export
from orderdesk.columns import COLUMNS, resolve_columns
from orderdesk.export import CsvExporter, export_csv
from orderdesk.models import Order


def order(n=1, **kw):
    base = dict(order_id=f"A-{1000 + n}", placed_on=date(2026, 3, 14), status="paid",
                customer_id=f"C-{n}", total_cents=123450)
    base.update(kw)
    return Order(**base)


class ExportCsvTest(unittest.TestCase):
    def export(self, orders, columns=None):
        out = io.StringIO()
        count = export_csv(orders, out, columns)
        return count, out.getvalue()

    def test_header_first(self):
        _, body = self.export([order()])
        self.assertEqual(body.split("\r\n")[0].split(","), [c.header for c in COLUMNS])

    def test_row_count_returned(self):
        count, _ = self.export([order(1), order(2), order(3)])
        self.assertEqual(count, 3)

    def test_crlf_line_endings(self):
        _, body = self.export([order()])
        self.assertTrue(body.endswith("\r\n"))

    def test_writes_every_row_past_the_flush_size(self):
        n = export.FLUSH_EVERY * 2 + 3
        count, body = self.export([order(i) for i in range(n)], resolve_columns(["order_id"]))
        self.assertEqual(count, n)
        self.assertEqual(len(body.strip().split("\r\n")), n + 1)


class CsvExporterTest(unittest.TestCase):
    def test_default_columns_are_every_column(self):
        self.assertEqual(CsvExporter().columns, list(COLUMNS))

    def test_row_follows_the_column_order(self):
        exporter = CsvExporter(resolve_columns(["status", "order_id"]))
        self.assertEqual(exporter.row(order(7)), ["paid", "A-1007"])

    def test_small_flush_size_still_writes_every_row(self):
        out = io.StringIO()
        count = CsvExporter(resolve_columns(["order_id"]), flush_every=2).write([order(i) for i in range(5)], out)
        self.assertEqual(count, 5)
        self.assertEqual(len(out.getvalue().strip().split("\r\n")), 6)
EOF
commit "2026-10-05T10:41:00+00:00" "Dana Ortiz" "Extract export columns into orderdesk/columns.py" \
  "Moves Column, the formatters and the registry out of export.py so the filters can use them, and turns the write loop into CsvExporter. select_columns is renamed resolve_columns."

# --- 2. the date-range filter
cat > orderdesk/filters.py <<'EOF'
"""Filters for the orders export (#412): a placed-on date range."""
from dataclasses import dataclass
from datetime import date
from typing import Optional


class InvalidFilter(ValueError):
    pass


@dataclass(frozen=True)
class ExportFilters:
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    def matches(self, order):
        if self.date_from and order.placed_on < self.date_from:
            return False
        if self.date_to and order.placed_on > self.date_to:
            return False
        return True

    def describe(self):
        """A label for the export's file name: "2026-09-01_to_2026-09-30", "from_2026-09-01",
        "until_2026-09-30", or "" when there is no date bound."""
        if self.date_from and self.date_to:
            return f"{self.date_from}_to_{self.date_to}"
        if self.date_from:
            return f"from_{self.date_from}"
        if self.date_to:
            return f"until_{self.date_to}"
        return ""


def _parse_date(raw, name):
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise InvalidFilter(f"{name} must be a date as YYYY-MM-DD, got {raw!r}") from None


def parse_filters(params):
    """ExportFilters from the query parameters `from` and `to` (both optional, both inclusive)."""
    raw_from, raw_to = params.get("from"), params.get("to")
    date_from = _parse_date(raw_from, "from") if raw_from else None
    date_to = _parse_date(raw_to, "to") if raw_to else None
    if date_from and date_to and date_from > date_to:
        raise InvalidFilter("from must not be after to")
    return ExportFilters(date_from, date_to)


def apply_filters(orders, filters):
    for order in orders:
        if filters.matches(order):
            yield order
EOF

cat > orderdesk/api.py <<'EOF'
"""HTTP entry points. handle_export is what GET /export runs."""
import io
import json
from http import HTTPStatus
from urllib.parse import parse_qs

from orderdesk.columns import UnknownColumn, resolve_columns
from orderdesk.export import export_csv
from orderdesk.filters import InvalidFilter, apply_filters, parse_filters

COLUMNS_PREF = "export.columns"
FILTER_PARAMS = ("from", "to")


def _one(params, key):
    values = params.get(key)
    return values[-1] if values else None


def _error(message):
    return HTTPStatus.BAD_REQUEST, {"Content-Type": "application/json"}, json.dumps({"error": message})


def handle_export(store, prefs, user, query):
    """GET /export?columns=a,b,c&from=YYYY-MM-DD&to=YYYY-MM-DD -> (status, headers, body).

    The column choice is remembered per user: an export without `columns` uses the
    user's last choice, or every column the first time."""
    params = parse_qs(query or "")
    requested = _one(params, "columns")
    remembered = prefs.get(user, COLUMNS_PREF)
    try:
        columns = resolve_columns((requested or remembered or "").split(",") if (requested or remembered) else None)
        filters = parse_filters({key: _one(params, key) for key in FILTER_PARAMS})
    except (UnknownColumn, InvalidFilter) as exc:
        return _error(str(exc))
    if requested is not None:
        prefs.set(user, COLUMNS_PREF, requested)
    out = io.StringIO()
    count = export_csv(apply_filters(store.all(), filters), out, columns)
    label = filters.describe()
    filename = f"orders_{label}.csv" if label else "orders.csv"
    headers = {"Content-Type": "text/csv; charset=utf-8",
               "Content-Disposition": f'attachment; filename="{filename}"',
               "X-Row-Count": str(count)}
    return HTTPStatus.OK, headers, out.getvalue()
EOF

cat > tests/test_filters.py <<'EOF'
import unittest
from datetime import date

from orderdesk.api import handle_export
from orderdesk.filters import ExportFilters, InvalidFilter, apply_filters, parse_filters
from orderdesk.models import Order
from orderdesk.prefs import PrefsStore


def order(day, n=1, status="paid"):
    return Order(order_id=f"A-{day:02d}{n}", placed_on=date(2026, 9, day), status=status, customer_id="C-1")


class ListStore:
    def __init__(self, orders):
        self.orders = list(orders)

    def all(self):
        return list(self.orders)


class ParseDateRangeTest(unittest.TestCase):
    def test_no_params_means_no_date_bounds(self):
        filters = parse_filters({})
        self.assertIsNone(filters.date_from)
        self.assertIsNone(filters.date_to)

    def test_from_and_to_parsed(self):
        filters = parse_filters({"from": "2026-09-01", "to": "2026-09-30"})
        self.assertEqual((filters.date_from, filters.date_to), (date(2026, 9, 1), date(2026, 9, 30)))

    def test_bad_date_rejected(self):
        with self.assertRaises(InvalidFilter):
            parse_filters({"from": "01/09/2026"})

    def test_from_after_to_rejected(self):
        with self.assertRaises(InvalidFilter):
            parse_filters({"from": "2026-09-30", "to": "2026-09-01"})


class DateRangeMatchTest(unittest.TestCase):
    def kept(self, filters, days):
        return [o.placed_on.day for o in apply_filters([order(d) for d in days], filters)]

    def test_both_ends_inclusive(self):
        f = ExportFilters(date(2026, 9, 10), date(2026, 9, 20))
        self.assertEqual(self.kept(f, [9, 10, 15, 20, 21]), [10, 15, 20])

    def test_open_ended_from(self):
        f = ExportFilters(date_from=date(2026, 9, 10))
        self.assertEqual(self.kept(f, [9, 10, 30]), [10, 30])

    def test_open_ended_to(self):
        f = ExportFilters(date_to=date(2026, 9, 10))
        self.assertEqual(self.kept(f, [1, 10, 11]), [1, 10])


class ExportDateRangeTest(unittest.TestCase):
    def test_export_counts_only_the_range(self):
        store = ListStore([order(d) for d in (1, 5, 10, 15, 20, 25)])
        status, headers, _ = handle_export(store, PrefsStore(), "dana", "from=2026-09-05&to=2026-09-15")
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Row-Count"], "3")

    def test_bad_date_is_400(self):
        status, _, body = handle_export(ListStore([]), PrefsStore(), "dana", "to=last-week")
        self.assertEqual(status, 400)
        self.assertIn("to must be a date", body)

    def test_file_name_names_the_range(self):
        _, headers, _ = handle_export(ListStore([]), PrefsStore(), "dana", "from=2026-09-01&to=2026-09-30")
        self.assertIn('filename="orders_2026-09-01_to_2026-09-30.csv"', headers["Content-Disposition"])

    def test_file_name_unchanged_without_a_range(self):
        _, headers, _ = handle_export(ListStore([]), PrefsStore(), "dana", "")
        self.assertIn('filename="orders.csv"', headers["Content-Disposition"])


class DescribeTest(unittest.TestCase):
    def test_closed_range(self):
        self.assertEqual(ExportFilters(date(2026, 9, 1), date(2026, 9, 30)).describe(), "2026-09-01_to_2026-09-30")

    def test_open_ends(self):
        self.assertEqual(ExportFilters(date_from=date(2026, 9, 1)).describe(), "from_2026-09-01")
        self.assertEqual(ExportFilters(date_to=date(2026, 9, 30)).describe(), "until_2026-09-30")

    def test_no_bounds_is_empty(self):
        self.assertEqual(ExportFilters().describe(), "")
EOF
commit "2026-10-06T15:03:00+00:00" "Dana Ortiz" "Add date range filter to orders export (#412)"

# --- 3. wip: the status filter, with the author's debugging still in it
cat > orderdesk/filters.py <<'EOF'
"""Filters for the orders export (#412): a placed-on date range and a set of statuses."""
from dataclasses import dataclass
from datetime import date
from typing import FrozenSet, Optional

from orderdesk.models import STATUSES

# Cancelled and refunded orders are noise in most exports.
ACTIVE_STATUSES = frozenset(s for s in STATUSES if s not in ("cancelled", "refunded"))


class InvalidFilter(ValueError):
    pass


@dataclass(frozen=True)
class ExportFilters:
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    statuses: FrozenSet[str] = ACTIVE_STATUSES

    def matches(self, order):
        # TODO: timezones - placed_on is a naive date in the warehouse's local time
        if self.date_from and order.placed_on < self.date_from:
            return False
        if self.date_to and order.placed_on > self.date_to:
            return False
        return order.status in self.statuses

    def describe(self):
        """A label for the export's file name: "2026-09-01_to_2026-09-30", "from_2026-09-01",
        "until_2026-09-30", or "" when there is no date bound."""
        if self.date_from and self.date_to:
            return f"{self.date_from}_to_{self.date_to}"
        if self.date_from:
            return f"from_{self.date_from}"
        if self.date_to:
            return f"until_{self.date_to}"
        return ""


def _parse_date(raw, name):
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise InvalidFilter(f"{name} must be a date as YYYY-MM-DD, got {raw!r}") from None


def _parse_statuses(raw):
    wanted = {s.strip().lower() for s in raw.split(",") if s.strip()}
    unknown = sorted(wanted - set(STATUSES))
    if unknown:
        raise InvalidFilter(f"unknown status(es): {', '.join(unknown)}")
    if not wanted:
        raise InvalidFilter("status must name at least one status")
    return frozenset(wanted)


def parse_filters(params):
    """ExportFilters from the query parameters `from`, `to` (inclusive) and `status`
    (comma-separated). All optional."""
    raw_from, raw_to, raw_status = params.get("from"), params.get("to"), params.get("status")
    date_from = _parse_date(raw_from, "from") if raw_from else None
    date_to = _parse_date(raw_to, "to") if raw_to else None
    if date_from and date_to and date_from > date_to:
        raise InvalidFilter("from must not be afer to")
    statuses = _parse_statuses(raw_status) if raw_status is not None else ACTIVE_STATUSES
    return ExportFilters(date_from, date_to, statuses)


def apply_filters(orders, filters):
    print(f"DEBUG export filters: {filters}")
    for order in orders:
        if filters.matches(order):
            yield order
EOF
subst orderdesk/api.py 's/^FILTER_PARAMS = ("from", "to")$/FILTER_PARAMS = ("from", "to", "status")/'
subst orderdesk/api.py 's|^    """GET /export?columns=a,b,c&from=YYYY-MM-DD&to=YYYY-MM-DD -> (status, headers, body).|    """GET /export?columns=a,b,c\&from=YYYY-MM-DD\&to=YYYY-MM-DD\&status=a,b -> (status, headers, body).|'
awk '/^    out = io.StringIO\(\)$/ {
       print "    # rows = [o for o in store.all() if o.status != \"cancelled\"]"
       print "    # if _one(params, \"from\"):"
       print "    #     rows = [o for o in rows if o.placed_on >= date.fromisoformat(_one(params, \"from\"))]"
     } { print }' orderdesk/api.py > orderdesk/api.py.tmp && mv orderdesk/api.py.tmp orderdesk/api.py
commit "2026-10-07T18:27:00+00:00" "Dana Ortiz" "wip"

# --- 4. fix typo
subst orderdesk/filters.py 's/must not be afer to/must not be after to/'
commit "2026-10-08T09:14:00+00:00" "Dana Ortiz" "fix typo"

# ===================================================================== main moves on
git switch -q main
insert_before orderdesk/countries.py "# end of zones" '    "JE": "europe",'
commit "2026-10-02T11:20:00+00:00" "Lena Fischer" "Ship to JE (zone europe)"
insert_before orderdesk/countries.py "# end of zones" '    "GG": "europe",'
commit "2026-10-07T13:05:00+00:00" "Lena Fischer" "Ship to GG (zone europe)"

git switch -q feature/export-filters
git gc -q --prune=now 2>/dev/null || true
echo "built: main $(git rev-list --count main) commits, feature/export-filters +$(git rev-list --count main..feature/export-filters) over $(git rev-parse --short "$BASE")"
