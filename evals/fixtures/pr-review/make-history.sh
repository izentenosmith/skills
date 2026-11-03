#!/usr/bin/env bash
# Build the pr-review fixture's git repository: Ledgerline, a small stdlib-Python
# billing service (invoices, late fees, statements, payments, CSV export). main has
# ten months of history (2026-01 to 2026-10, ~200 commits); feature/late-fee-config
# adds three commits on top and is left checked out. The PR's title and body sit
# next to repo/ in PR.md.
# Idempotent: removes and rebuilds repo/ each time.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

# The history is generated: every commit really changes the files it names, and the
# fee policy (billing/fees.py) and the policy text printed on customer statements
# (billing/statement.py) travel together, as they have all year.
python3 -I - <<'PY'
import datetime, os, pathlib, subprocess, textwrap

ROOT = pathlib.Path.cwd()
AUTHORS = ["Ana Lopez", "Ben Okafor", "Chen Wei", "Dana Fischer"]


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).lstrip("\n"))


def commit(when, author, subject, body=""):
    env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when,
               GIT_AUTHOR_NAME=author, GIT_COMMITTER_NAME=author,
               GIT_AUTHOR_EMAIL=author.lower().replace(" ", ".") + "@example.invalid",
               GIT_COMMITTER_EMAIL=author.lower().replace(" ", ".") + "@example.invalid")
    subprocess.run(["git", "add", "-A"], check=True)
    st = subprocess.run(["git", "diff", "--cached", "--quiet"])
    assert st.returncode == 1, f"empty commit: {subject}"
    args = ["git", "commit", "-q", "-m", subject] + (["-m", body] if body else [])
    subprocess.run(args, check=True, env=env)


# ------------------------------------------------------------------ templates

def fees_py(p):
    helper = p.get("helper", True)
    months = (
        '''
        def months_overdue(invoice, today):
            """Started months past the grace period; 0 while still inside it."""
            days = (today - invoice.due_on).days
            if days <= GRACE_DAYS:
                return 0
            return (days - GRACE_DAYS - 1) // 30 + 1


        ''' if helper else "\n")
    calc = ("    months = months_overdue(invoice, today)\n    if not months:\n        return 0\n" if helper else
            "    days = (today - invoice.due_on).days\n    if days <= GRACE_DAYS:\n        return 0\n"
            "    months = (days - GRACE_DAYS - 1) // 30 + 1\n")
    return (textwrap.dedent(f'''
        """Late fees on overdue invoices.

        {p["doc"]}
        """
        from decimal import ROUND_HALF_UP, Decimal

        POLICY_VERSION = "{p["version"]}"
        LATE_FEE_PERCENT = Decimal("{p["rate"]}")  # of the open balance, per started month overdue
        GRACE_DAYS = {p["grace"]}
        MAX_LATE_FEE_CENTS = {p["cap"]}

        ''').lstrip("\n") + textwrap.dedent(months)
        + textwrap.dedent('''
        def late_fee_cents(invoice, today):
            """The late fee owed on `invoice` as of `today`, in cents."""
            if invoice.status == "paid" or invoice.open_cents <= 0:
                return 0
        ''').lstrip("\n") + calc
        + "    fee = Decimal(invoice.open_cents) * LATE_FEE_PERCENT / 100 * months\n"
        + "    return min(int(fee.quantize(Decimal(\"1\"), rounding=ROUND_HALF_UP)), MAX_LATE_FEE_CENTS)\n")


def statement_py(p, title="Statement for"):
    dollars = f'{p["cap"] // 100:,}.{p["cap"] % 100:02d}'
    return textwrap.dedent(f'''
        """Customer statements: the text block mailed with each month's invoices."""
        from billing.fees import late_fee_cents
        from billing.money import fmt

        FEE_POLICY = (
            "Fee policy {p["version"]}: overdue balances are charged {p["rate"]}% per month "
            "after a {p["grace"]}-day grace period, capped at ${dollars} per invoice."
        )


        def render(customer, invoices, today):
            """The statement text for one customer."""
            lines = [f"{title} {{customer.name}} ({{customer.id}}), {{today:%d %B %Y}}", ""]
            for inv in invoices:
                fee = late_fee_cents(inv, today)
                flag = " (in dispute)" if inv.disputed else ""
                lines.append(f"{{inv.number}}{{flag}}  due {{inv.due_on}}  open {{fmt(inv.open_cents)}}  "
                             f"late fee {{fmt(fee)}}")
            lines += ["", FEE_POLICY]
            return "\\n".join(lines)
        ''').lstrip("\n")


MODELS = '''
"""The billing records."""
from dataclasses import dataclass
from datetime import date


@dataclass
class Customer:
    id: str
    name: str
    email: str

    @classmethod
    def from_row(cls, row):
        """A customer from one row of the customer import (a csv.DictReader row)."""
        return cls(id=row["id"].strip(), name=row["name"].strip(), email=row["email"].strip().lower())


@dataclass
class Invoice:
    number: str
    customer: Customer
    issued_on: date
    due_on: date
    total_cents: int
    paid_cents: int = 0
    status: str = "open"  # open | paid | void
    disputed: bool = False  # set by support while a dispute is open

    @property
    def open_cents(self):
        return max(self.total_cents - self.paid_cents, 0)


@dataclass
class Payment:
    id: str
    invoice_number: str
    captured_cents: int
    captured_on: date
    refunded_cents: int = 0
    status: str = "captured"  # captured | refunded
'''

MONEY = '''
"""Money is integer cents everywhere; this is the one place it becomes text."""


def fmt(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"
'''


def invoices_py(terms, prefix):
    return f'''
"""Issuing invoices."""
from datetime import timedelta

from billing.models import Invoice

PAYMENT_TERMS_DAYS = {terms}
NUMBER_PREFIX = "{prefix}"


def invoice_number(seq, issued_on):
    return f"{{NUMBER_PREFIX}}{{issued_on:%Y}}-{{seq:05d}}"


def issue(seq, customer, issued_on, total_cents):
    """A new open invoice, due PAYMENT_TERMS_DAYS after issue."""
    if total_cents <= 0:
        raise ValueError("an invoice total must be positive")
    return Invoice(number=invoice_number(seq, issued_on), customer=customer, issued_on=issued_on,
                   due_on=issued_on + timedelta(days=PAYMENT_TERMS_DAYS), total_cents=total_cents)


def apply_payment(invoice, cents):
    """Record a payment against an invoice; marks it paid once nothing is open."""
    if cents <= 0:
        raise ValueError("a payment must be positive")
    invoice.paid_cents += cents
    if invoice.open_cents == 0:
        invoice.status = "paid"
    return invoice
'''


def capture_py(timeout, retries):
    return f'''
"""Capturing card payments through the processor client."""
from billing.models import Payment

CAPTURE_TIMEOUT_SECONDS = {timeout}
MAX_RETRIES = {retries}


class CaptureError(Exception):
    pass


def capture(client, invoice, cents, today):
    """Capture `cents` for `invoice`, retrying transient failures up to MAX_RETRIES times."""
    if cents <= 0 or cents > invoice.open_cents:
        raise CaptureError("capture amount must be positive and no more than the open balance")
    last = None
    for _ in range(MAX_RETRIES + 1):
        try:
            ref = client.capture(invoice.number, cents, timeout=CAPTURE_TIMEOUT_SECONDS)
            return Payment(id=ref, invoice_number=invoice.number, captured_cents=cents, captured_on=today)
        except TimeoutError as e:
            last = e
    raise CaptureError(f"processor timed out {{MAX_RETRIES + 1}} times") from last
'''


def refunds_py(window, reasons):
    return f'''
"""Refunding captured payments."""

REFUND_WINDOW_DAYS = {window}
REASONS = {reasons!r}


class RefundError(Exception):
    pass


def refund(payment, today, reason="requested_by_customer"):
    """Refund a captured payment in full. Returns the cents refunded."""
    if reason not in REASONS:
        raise RefundError(f"unknown refund reason: {{reason}}")
    if payment.status != "captured":
        raise RefundError("only a captured payment can be refunded")
    if payment.refunded_cents:
        raise RefundError("payment already refunded")
    if (today - payment.captured_on).days > REFUND_WINDOW_DAYS:
        raise RefundError("outside the refund window")
    payment.refunded_cents = payment.captured_cents
    payment.status = "refunded"
    return payment.captured_cents
'''


def export_py(max_rows, delim=",", datefmt="%Y-%m-%d"):
    return f'''
"""The monthly invoice export (CSV), imported by finance's ledger tool."""
import csv

from billing.fees import late_fee_cents

DELIMITER = "{delim}"
DATE_FORMAT = "{datefmt}"
MAX_ROWS = {max_rows}
COLUMNS = ["number", "customer_id", "issued_on", "due_on", "total_cents", "open_cents", "late_fee_cents", "status"]


def export_invoices(invoices, out, today):
    """Write one row per invoice to the text stream `out`. Returns the number of rows written."""
    if len(invoices) > MAX_ROWS:
        raise ValueError(f"export is limited to {{MAX_ROWS}} rows; split by month")
    writer = csv.writer(out, delimiter=DELIMITER, lineterminator="\\n")
    writer.writerow(COLUMNS)
    for inv in invoices:
        writer.writerow([inv.number, inv.customer.id, inv.issued_on.strftime(DATE_FORMAT),
                         inv.due_on.strftime(DATE_FORMAT), inv.total_cents, inv.open_cents,
                         late_fee_cents(inv, today), inv.status])
    return len(invoices)
'''


def aging_py(buckets):
    return f'''
"""Accounts-receivable aging: open balances bucketed by days past due."""

BUCKETS = {buckets!r}  # upper bounds in days past due; the last bucket is open-ended


def bucket(days_past_due):
    for upper in BUCKETS:
        if days_past_due <= upper:
            return f"<= {{upper}}"
    return f"> {{BUCKETS[-1]}}"


def aging(invoices, today):
    out = {{}}
    for inv in invoices:
        if inv.status != "open":
            continue
        key = bucket(max((today - inv.due_on).days, 0))
        out[key] = out.get(key, 0) + inv.open_cents
    return out
'''


TESTS_COMMON = '''
from datetime import date

from billing.models import Customer, Invoice

ACME = Customer(id="C-001", name="Acme Ltd", email="ap@acme.example")


def invoice(total=100_000, due=date(2026, 3, 1), **kw):
    return Invoice(number="INV2026-00001", customer=kw.pop("customer", ACME), issued_on=date(2026, 2, 1),
                   due_on=due, total_cents=total, **kw)
'''

TEST_FEES = '''
import unittest
from datetime import date, timedelta

from billing import fees
from tests.helpers import invoice


class LateFeeTest(unittest.TestCase):
    def test_no_fee_inside_grace_period(self):
        inv = invoice()
        self.assertEqual(fees.late_fee_cents(inv, inv.due_on + timedelta(days=fees.GRACE_DAYS)), 0)

    def test_one_month_fee_after_grace(self):
        inv = invoice(total=100_000)
        expected = round(100_000 * fees.LATE_FEE_PERCENT / 100)
        self.assertEqual(fees.late_fee_cents(inv, inv.due_on + timedelta(days=fees.GRACE_DAYS + 1)), expected)

    def test_paid_invoice_has_no_fee(self):
        inv = invoice(status="paid", paid_cents=100_000)
        self.assertEqual(fees.late_fee_cents(inv, date(2026, 12, 1)), 0)

    def test_fee_is_capped(self):
        inv = invoice(total=100_000_000)
        self.assertEqual(fees.late_fee_cents(inv, date(2027, 6, 1)), fees.MAX_LATE_FEE_CENTS)


if __name__ == "__main__":
    unittest.main()
'''

TEST_REFUNDS = '''
import unittest
from datetime import date, timedelta

from billing.models import Payment
from payments import refunds


def payment(cents=10_000, on=date(2026, 5, 1)):
    return Payment(id="pay_1", invoice_number="INV2026-00001", captured_cents=cents, captured_on=on)


class RefundTest(unittest.TestCase):
    def test_full_refund(self):
        p = payment()
        self.assertEqual(refunds.refund(p, date(2026, 5, 10)), 10_000)
        self.assertEqual(p.status, "refunded")

    def test_second_refund_rejected(self):
        p = payment()
        refunds.refund(p, date(2026, 5, 10))
        with self.assertRaises(refunds.RefundError):
            refunds.refund(p, date(2026, 5, 11))

    def test_outside_window(self):
        p = payment()
        with self.assertRaises(refunds.RefundError):
            refunds.refund(p, p.captured_on + timedelta(days=refunds.REFUND_WINDOW_DAYS + 1))


if __name__ == "__main__":
    unittest.main()
'''

TEST_EXPORT = '''
import csv
import io
import unittest
from datetime import date

from reports import export
from tests.helpers import invoice


class ExportTest(unittest.TestCase):
    def test_header_and_row(self):
        out = io.StringIO()
        export.export_invoices([invoice()], out, date(2026, 3, 5))
        rows = list(csv.reader(io.StringIO(out.getvalue()), delimiter=export.DELIMITER))
        self.assertEqual(rows[0], export.COLUMNS)
        self.assertEqual(rows[1][0], "INV2026-00001")
        self.assertEqual(rows[1][2], date(2026, 2, 1).strftime(export.DATE_FORMAT))

    def test_row_limit(self):
        with self.assertRaises(ValueError):
            export.export_invoices([invoice()] * (export.MAX_ROWS + 1), io.StringIO(), date(2026, 3, 5))


if __name__ == "__main__":
    unittest.main()
'''

TEST_INVOICES = '''
import unittest
from datetime import date

from billing import invoices
from tests.helpers import ACME


class InvoiceTest(unittest.TestCase):
    def test_due_date_follows_terms(self):
        inv = invoices.issue(7, ACME, date(2026, 4, 1), 5_000)
        self.assertEqual((inv.due_on - inv.issued_on).days, invoices.PAYMENT_TERMS_DAYS)

    def test_paid_when_nothing_open(self):
        inv = invoices.issue(8, ACME, date(2026, 4, 1), 5_000)
        invoices.apply_payment(inv, 5_000)
        self.assertEqual(inv.status, "paid")


if __name__ == "__main__":
    unittest.main()
'''

README = '''
# Ledgerline billing

Invoices, late fees, customer statements, card payments and the monthly CSV export for
finance. Standard library only.

    python3 -m unittest discover -s tests -t .

| Path | What |
|---|---|
| `billing/` | records, invoices, late fees, statements |
| `payments/` | capture and refunds |
| `reports/` | the monthly CSV export and the aging report |

Money is integer cents everywhere (`billing/money.py` formats it).
{extra}'''

# ------------------------------------------------------------------ the fee policy's year
# Each entry: (subject, policy changes). Every one of these commits changes fees.py AND
# the policy text in statement.py, except where marked.
POLICY = dict(version="2026.01", rate="1.5", grace=10, cap=50_000, helper=True,
              doc="Policy figures come from finance; see POLICY_VERSION.")
FEE_STEPS = [
    ("fees: grace period 10 -> 14 days", dict(grace=14)),
    ("fees: cap late fees at $400 per invoice", dict(cap=40_000)),
    ("fees: rate 1.5% -> 1.25% for Q1", dict(rate="1.25")),
    ("fees: grace period back to 10 days", dict(grace=10)),
    ("fees: raise cap to $450", dict(cap=45_000)),
    ("fees: rate 1.25% -> 1.5%", dict(rate="1.5")),
    ("fees: inline months computation", dict(helper=False), "fees-only"),
    ("fees: 12-day grace period (finance memo 2026-03)", dict(grace=12)),
    ("fees: cap at $500", dict(cap=50_000)),
    ("fees: rate 1.75% from April", dict(rate="1.75")),
    ("fees: grace 15 days for April billing run", dict(grace=15)),
    ("fees: restore months_overdue helper", dict(helper=True), "fees-only"),
    ("fees: rate back to 1.5%", dict(rate="1.5")),
    ("fees: grace period 10 days", dict(grace=10)),
    ("fees: cap at $550 for enterprise volumes", dict(cap=55_000)),
    ("fees: cap back to $500", dict(cap=50_000)),
    ("fees: rate 1.6%", dict(rate="1.6")),
    ("fees: rate 1.5% (finance reverted)", dict(rate="1.5")),
    ("fees: grace period 7 days", dict(grace=7)),
    ("fees: grace period 10 days after complaints", dict(grace=10)),
    ("fees: cap at $480", dict(cap=48_000)),
    ("fees: cap at $500", dict(cap=50_000)),
    ("fees: grace period 11 days", dict(grace=11)),
    ("fees: grace period 10 days", dict(grace=10)),
    ("fees: document the policy source", dict(doc="Policy figures come from finance (fee policy memo); see POLICY_VERSION."), "fees-only"),
]
STATEMENT_ONLY = [
    ("statement: wording of the header", "Statement of account for"),
    ("statement: shorter header", "Statement for"),
]

# Noise: config tweaks elsewhere in the service, each a real change to one module
# (sometimes with its test). None of these files is coupled to fees.py.
TERMS = [30, 45, 30, 21, 30, 14]
PREFIX = ["INV", "INV-"]
TIMEOUT = [20, 25, 30, 15, 20, 25]
RETRIES = [2, 3, 1]
WINDOW = [90, 60, 90, 120]
REASONS = [("requested_by_customer", "duplicate", "fraudulent"),
           ("requested_by_customer", "duplicate", "fraudulent", "service_not_rendered"),
           ("requested_by_customer", "duplicate", "fraudulent", "service_not_rendered", "billing_error")]
MAX_ROWS = [50_000, 100_000, 75_000, 100_000, 200_000]
BUCKETS = [(30, 60, 90), (30, 60, 90, 120), (15, 30, 60, 90)]
READMES = ["", "\nThe export feeds finance's ledger tool, which expects ISO dates and commas.\n",
           "\nThe export feeds finance's ledger tool, which expects ISO dates and commas.\n"
           "Statements go out on the 1st with the fee policy printed at the foot.\n"]

state = dict(terms=0, prefix=0, timeout=0, retries=0, window=0, reasons=0, max_rows=0, buckets=0, readme=0,
             stitle="Statement for")


def write_all():
    write("billing/__init__.py", "")
    write("payments/__init__.py", "")
    write("reports/__init__.py", "")
    write("tests/__init__.py", "")
    write("billing/models.py", MODELS)
    write("billing/money.py", MONEY)
    write("billing/fees.py", fees_py(POLICY))
    write("billing/statement.py", statement_py(POLICY, state["stitle"]))
    write("billing/invoices.py", invoices_py(TERMS[state["terms"]], PREFIX[state["prefix"]]))
    write("payments/capture.py", capture_py(TIMEOUT[state["timeout"]], RETRIES[state["retries"]]))
    write("payments/refunds.py", refunds_py(WINDOW[state["window"]], REASONS[state["reasons"]]))
    write("reports/export.py", export_py(MAX_ROWS[state["max_rows"]]))
    write("reports/aging.py", aging_py(BUCKETS[state["buckets"]]))
    write("tests/helpers.py", TESTS_COMMON)
    write("tests/test_fees.py", TEST_FEES)
    write("tests/test_refunds.py", TEST_REFUNDS)
    write("tests/test_export.py", TEST_EXPORT)
    write("tests/test_invoices.py", TEST_INVOICES)
    write("README.md", README.format(extra=READMES[state["readme"]]))


def bump(key, seq, label, unit=""):
    old = seq[state[key]]
    state[key] = (state[key] + 1) % len(seq)
    new = seq[state[key]]
    fmt = lambda v: f"{len(v)} reasons" if isinstance(v, tuple) and isinstance(v[0], str) else (
        "/".join(map(str, v)) if isinstance(v, tuple) else f"{v}{unit}")
    return f"{label} {fmt(old)} -> {fmt(new)}"


NOISE = [  # (kind, subject builder)
    ("terms", lambda: bump("terms", TERMS, "invoices: payment terms", " days")),
    ("timeout", lambda: bump("timeout", TIMEOUT, "capture: processor timeout", "s")),
    ("max_rows", lambda: bump("max_rows", MAX_ROWS, "export: row limit")),
    ("window", lambda: bump("window", WINDOW, "refunds: refund window", " days")),
    ("buckets", lambda: bump("buckets", BUCKETS, "aging: buckets")),
    ("retries", lambda: bump("retries", RETRIES, "capture: retries")),
    ("reasons", lambda: bump("reasons", REASONS, "refunds: reason codes")),
    ("prefix", lambda: bump("prefix", PREFIX, "invoices: number prefix")),
    ("readme", lambda: bump("readme", READMES, "docs: README") and "docs: README notes"),
]

# ------------------------------------------------------------------ build main
start = datetime.datetime(2026, 1, 6, 9, 30)
end = datetime.datetime(2026, 10, 20, 17, 0)
N_NOISE = 175
total = 1 + len(FEE_STEPS) + len(STATEMENT_ONLY) + N_NOISE
step = (end - start) / (total - 1)

# Interleave: the fee commits spread evenly through the noise.
plan = []
fee_every = N_NOISE // len(FEE_STEPS)
fi, si, ni = 0, 0, 0
while fi < len(FEE_STEPS) or si < len(STATEMENT_ONLY) or ni < N_NOISE:
    for _ in range(fee_every):
        if ni < N_NOISE:
            plan.append(("noise", ni)); ni += 1
    if fi < len(FEE_STEPS):
        plan.append(("fee", fi)); fi += 1
    if si < len(STATEMENT_ONLY) and fi in (9, 19):
        plan.append(("statement", si)); si += 1
    if fi >= len(FEE_STEPS) and ni >= N_NOISE and si < len(STATEMENT_ONLY):
        plan.append(("statement", si)); si += 1

write_all()
commit(start.isoformat(), AUTHORS[0], "Initial import of the billing service")
for i, (kind, k) in enumerate(plan, start=1):
    when = (start + step * i).replace(second=0, microsecond=0).isoformat()
    author = AUTHORS[(i * 3 + i // 5) % len(AUTHORS)]
    if kind == "fee":
        subject, change, *mode = FEE_STEPS[k]
        if not mode and k and k % 3 == 0:  # finance publishes a new policy version now and then
            y, m = POLICY["version"].split(".")
            POLICY["version"] = f"{y}.{int(m) + 1:02d}"
        POLICY.update(change)
        write("billing/fees.py", fees_py(POLICY))
        if not mode:
            write("billing/statement.py", statement_py(POLICY, state["stitle"]))
        body = "" if mode else f"Statement policy text updated to match (policy {POLICY['version']})."
        commit(when, author, subject, body)
    elif kind == "statement":
        subject, title = STATEMENT_ONLY[k]
        state["stitle"] = title
        write("billing/statement.py", statement_py(POLICY, state["stitle"]))
        commit(when, author, subject)
    else:
        key, build = NOISE[k % len(NOISE)]
        subject = build()
        write_all()
        commit(when, author, subject)

# ------------------------------------------------------------------ the feature branch
subprocess.run(["git", "checkout", "-q", "-b", "feature/late-fee-config"], check=True)
BR = "Eli Moreno"

models = (ROOT / "billing/models.py").read_text()
models = models.replace("from datetime import date\n", "from datetime import date\nfrom decimal import Decimal, InvalidOperation\nfrom typing import Optional\n")
models = models.replace('''    email: str

    @classmethod
    def from_row(cls, row):
        """A customer from one row of the customer import (a csv.DictReader row)."""
        return cls(id=row["id"].strip(), name=row["name"].strip(), email=row["email"].strip().lower())
''', '''    email: str
    late_fee_percent: Optional[Decimal] = None  # None: the default rate in billing/fees.py

    @classmethod
    def from_row(cls, row):
        """A customer from one row of the customer import (a csv.DictReader row)."""
        return cls(id=row["id"].strip(), name=row["name"].strip(), email=row["email"].strip().lower(),
                   late_fee_percent=parse_percent(row.get("late_fee_percent")))


def parse_percent(value):
    """The late_fee_percent column: blank means "use the default"; otherwise 0-10."""
    if value is None or not value.strip():
        return None
    try:
        percent = Decimal(value.strip().rstrip("%"))
    except InvalidOperation:
        raise ValueError(f"late_fee_percent is not a number: {value!r}") from None
    if not Decimal("0") <= percent <= Decimal("10"):
        raise ValueError(f"late_fee_percent must be between 0 and 10, got {percent}")
    return percent
''')
(ROOT / "billing/models.py").write_text(models)

fees = (ROOT / "billing/fees.py").read_text()
fees = fees.replace("# of the open balance, per started month overdue",
                    "# the default; Customer.late_fee_percent overrides it", 1)
fees = fees.replace('''def late_fee_cents(invoice, today):
    """The late fee owed on `invoice` as of `today`, in cents."""
''', '''def fee_percent(customer):
    """The late-fee percent for `customer`: their own rate, or the default."""
    return customer.late_fee_percent or LATE_FEE_PERCENT


def late_fee_cents(invoice, today):
    """The late fee owed on `invoice` as of `today`, in cents, at the customer's rate."""
''')
fees = fees.replace("    fee = Decimal(invoice.open_cents) * LATE_FEE_PERCENT / 100 * months\n",
                    "    percent = fee_percent(invoice.customer)\n"
                    "    fee = Decimal(invoice.open_cents) * percent / 100 * months\n")
(ROOT / "billing/fees.py").write_text(fees)

tf = (ROOT / "tests/test_fees.py").read_text()
tf = tf.replace("from datetime import date, timedelta\n", "from datetime import date, timedelta\nfrom decimal import Decimal\n")
tf = tf.replace("from tests.helpers import invoice\n", "from billing.models import Customer, parse_percent\nfrom tests.helpers import invoice\n")
tf = tf.replace('''

if __name__ == "__main__":''', '''

class CustomerRateTest(unittest.TestCase):
    def test_customer_rate_overrides_default(self):
        c = Customer(id="C-002", name="Brightside", email="ap@brightside.example", late_fee_percent=Decimal("2.5"))
        inv = invoice(total=100_000, customer=c)
        self.assertEqual(fees.late_fee_cents(inv, inv.due_on + timedelta(days=fees.GRACE_DAYS + 1)), 2_500)

    def test_customer_without_rate_uses_default(self):
        c = Customer(id="C-003", name="Corvid", email="ap@corvid.example")
        self.assertEqual(fees.fee_percent(c), fees.LATE_FEE_PERCENT)

    def test_parse_percent(self):
        self.assertIsNone(parse_percent(""))
        self.assertEqual(parse_percent("2.5%"), Decimal("2.5"))
        with self.assertRaises(ValueError):
            parse_percent("12")
        with self.assertRaises(ValueError):
            parse_percent("abc")


if __name__ == "__main__":''')
(ROOT / "tests/test_fees.py").write_text(tf)
commit("2026-10-22T10:14:00", BR, "fees: per-customer late fee percent",
       "Customer.late_fee_percent overrides the default rate; parsed from the\nlate_fee_percent column of the customer import.")

ref = (ROOT / "payments/refunds.py").read_text()
ref = ref.replace('''def refund(payment, today, reason="requested_by_customer"):
    """Refund a captured payment in full. Returns the cents refunded."""
    if reason not in REASONS:
        raise RefundError(f"unknown refund reason: {reason}")
    if payment.status != "captured":
        raise RefundError("only a captured payment can be refunded")
    if payment.refunded_cents:
        raise RefundError("payment already refunded")
    if (today - payment.captured_on).days > REFUND_WINDOW_DAYS:
        raise RefundError("outside the refund window")
    payment.refunded_cents = payment.captured_cents
    payment.status = "refunded"
    return payment.captured_cents
''', '''def refund(payment, today, reason="requested_by_customer", amount_cents=None):
    """Refund a captured payment, in full or in part. Returns the cents refunded.

    With no `amount_cents`, refunds whatever has not been refunded yet.
    """
    if reason not in REASONS:
        raise RefundError(f"unknown refund reason: {reason}")
    if payment.status not in ("captured", "partially_refunded"):
        raise RefundError("only a captured payment can be refunded")
    if (today - payment.captured_on).days > REFUND_WINDOW_DAYS:
        raise RefundError("outside the refund window")
    if amount_cents is None:
        amount_cents = payment.captured_cents - payment.refunded_cents
    if amount_cents <= 0:
        raise RefundError("refund amount must be positive")
    if amount_cents > payment.captured_cents:
        raise RefundError("refund exceeds the captured amount")
    payment.refunded_cents += amount_cents
    payment.status = "refunded" if payment.refunded_cents >= payment.captured_cents else "partially_refunded"
    return amount_cents
''')
(ROOT / "payments/refunds.py").write_text(ref)
mdl = (ROOT / "billing/models.py").read_text()
mdl = mdl.replace('status: str = "captured"  # captured | refunded', 'status: str = "captured"  # captured | partially_refunded | refunded')
(ROOT / "billing/models.py").write_text(mdl)
tr = (ROOT / "tests/test_refunds.py").read_text()
tr = tr.replace('''

if __name__ == "__main__":''', '''
    def test_partial_refund(self):
        p = payment(cents=10_000)
        self.assertEqual(refunds.refund(p, date(2026, 5, 10), amount_cents=4_000), 4_000)
        self.assertEqual(p.status, "partially_refunded")
        self.assertEqual(p.refunded_cents, 4_000)

    def test_rest_refunded_by_default(self):
        p = payment(cents=10_000)
        refunds.refund(p, date(2026, 5, 10), amount_cents=4_000)
        self.assertEqual(refunds.refund(p, date(2026, 5, 11)), 6_000)
        self.assertEqual(p.status, "refunded")

    def test_refund_more_than_captured_rejected(self):
        with self.assertRaises(refunds.RefundError):
            refunds.refund(payment(cents=10_000), date(2026, 5, 10), amount_cents=10_001)


if __name__ == "__main__":''')
(ROOT / "tests/test_refunds.py").write_text(tr)
commit("2026-10-23T15:40:00", BR, "refunds: partial refunds", "refund() takes an optional amount_cents (#212).")

ex = (ROOT / "reports/export.py").read_text()
ex = ex.replace('DELIMITER = ","', 'DELIMITER = ";"').replace('DATE_FORMAT = "%Y-%m-%d"', 'DATE_FORMAT = "%d/%m/%Y"')
ex = ex.replace('''    writer = csv.writer(out, delimiter=DELIMITER, lineterminator="\\n")
    writer.writerow(COLUMNS)
    for inv in invoices:
        writer.writerow([inv.number, inv.customer.id, inv.issued_on.strftime(DATE_FORMAT),
                         inv.due_on.strftime(DATE_FORMAT), inv.total_cents, inv.open_cents,
                         late_fee_cents(inv, today), inv.status])
    return len(invoices)
''', '''    writer = csv.writer(out, delimiter=DELIMITER, lineterminator="\\n")
    writer.writerow(COLUMNS)
    writer.writerows(_row(inv, today) for inv in invoices)
    return len(invoices)


def _row(inv, today):
    day = lambda d: d.strftime(DATE_FORMAT)
    return [inv.number, inv.customer.id, day(inv.issued_on), day(inv.due_on), inv.total_cents,
            inv.open_cents, late_fee_cents(inv, today), inv.status]
''')
(ROOT / "reports/export.py").write_text(ex)
commit("2026-10-24T11:05:00", BR, "reports: tidy export writer")
PY

echo "$(git rev-list --count main) commits on main, $(git rev-list --count main..HEAD) on $(git branch --show-current)"
