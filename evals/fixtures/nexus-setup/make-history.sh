#!/usr/bin/env bash
# Build the nexus-setup fixture's git repository (eval 72): Harbor Bikes, a small stdlib-Python
# counter app (prices, rentals, receipts), main at three commits, and one resolved design in
# .workflow/designs/ (git-ignored, written after the commits). No notes folder exists yet.
# Idempotent and deterministic: removes and rebuilds repo/ each time.
#
# It deletes repo/, so it refuses to run unless evals/setup.sh (or you, on purpose) sets
# EVALS_FIXTURE_BUILD=1: a copy of this folder is what a run works in.
set -euo pipefail
[ "${EVALS_FIXTURE_BUILD:-}" = 1 ] || { echo "make-history.sh: builds an eval fixture; run evals/setup.sh" >&2; exit 1; }
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

python3 -I - <<'PY'
import os
import pathlib
import subprocess
import textwrap

ROOT = pathlib.Path.cwd()


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).lstrip("\n"))


def commit(when, author, subject):
    email = author.lower().replace(" ", ".") + "@example.invalid"
    env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when, GIT_AUTHOR_NAME=author,
               GIT_COMMITTER_NAME=author, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_EMAIL=email)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], check=True, env=env)


PRICING = '''
"""Rental prices, in cents."""

HOUR_RATE = 600
DAY_RATE = 3000
WEEKEND_DAY_RATE = 3600


def rental_price(hours, weekend=False):
    """The price of a rental of `hours` started hours: hourly, capped at the day rate for each day."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    day = DAY_RATE
    full_days, rest = divmod(hours, 24)
    return full_days * day + min(rest * HOUR_RATE, day)
'''

write(".gitignore", """
.workflow/
__pycache__/
""")
write("README.md", """
# Harbor Bikes — counter software

Rentals, prices and receipts for the harbour bike shop's counter. Python 3.11+, standard library only.

## Running it

    python3 -m fleet.cli quote --hours 3

## Tests

    python3 -m unittest
""")
write("fleet/__init__.py", "")
write("fleet/pricing.py", PRICING.replace("WEEKEND_DAY_RATE = 3600\n", ""))
write("fleet/rentals.py", '''
"""A rental: which bike, who has it, and when it is due back."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Rental:
    bike_id: str
    customer: str
    start: datetime
    due: datetime
    returned: Optional[datetime] = None

    def is_open(self):
        return self.returned is None

    def hours_booked(self):
        seconds = int((self.due - self.start).total_seconds())
        return max(1, -(-seconds // 3600))
''')
write("fleet/receipt.py", '''
"""The counter receipt, one line per charge."""
from .pricing import rental_price


def euros(cents):
    return f"EUR {cents // 100}.{cents % 100:02d}"


def receipt_lines(rental, weekend=False):
    lines = [
        f"Bike {rental.bike_id} - {rental.customer}",
        f"Out: {rental.start:%Y-%m-%d %H:%M}",
        f"Due: {rental.due:%Y-%m-%d %H:%M}",
    ]
    hours = rental.hours_booked()
    lines.append(f"Rental ({hours} h): {euros(rental_price(hours, weekend))}")
    return lines
''')
write("fleet/cli.py", '''
"""Counter commands: python3 -m fleet.cli quote --hours N [--weekend]"""
import argparse

from .pricing import rental_price
from .receipt import euros


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fleet")
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("quote", help="price a rental")
    q.add_argument("--hours", type=int, required=True)
    q.add_argument("--weekend", action="store_true")
    a = ap.parse_args(argv)
    print(euros(rental_price(a.hours, a.weekend)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')
write("tests/test_pricing.py", '''
import unittest

from fleet.pricing import DAY_RATE, HOUR_RATE, rental_price


class PricingTest(unittest.TestCase):
    def test_one_hour(self):
        self.assertEqual(rental_price(1), HOUR_RATE)

    def test_hours_capped_at_day_rate(self):
        self.assertEqual(rental_price(10), DAY_RATE)

    def test_two_days(self):
        self.assertEqual(rental_price(48), 2 * DAY_RATE)

    def test_rejects_zero_hours(self):
        with self.assertRaises(ValueError):
            rental_price(0)
''')
write("tests/test_rentals.py", '''
import unittest
from datetime import datetime

from fleet.rentals import Rental

T0 = datetime(2026, 11, 2, 9, 0)


class RentalTest(unittest.TestCase):
    def test_open_until_returned(self):
        r = Rental("B7", "Ines", T0, T0.replace(hour=12))
        self.assertTrue(r.is_open())
        r.returned = T0.replace(hour=11)
        self.assertFalse(r.is_open())

    def test_hours_booked_rounds_up(self):
        self.assertEqual(Rental("B7", "Ines", T0, T0.replace(hour=11, minute=10)).hours_booked(), 3)

    def test_hours_booked_at_least_one(self):
        self.assertEqual(Rental("B7", "Ines", T0, T0).hours_booked(), 1)
''')
write("tests/test_receipt.py", '''
import unittest
from datetime import datetime

from fleet.receipt import euros, receipt_lines
from fleet.rentals import Rental

T0 = datetime(2026, 11, 2, 9, 0)


class ReceiptTest(unittest.TestCase):
    def test_euros_pads_cents(self):
        self.assertEqual(euros(1205), "EUR 12.05")

    def test_lines_name_bike_and_due(self):
        lines = receipt_lines(Rental("B7", "Ines", T0, T0.replace(hour=12)))
        self.assertEqual(lines[0], "Bike B7 - Ines")
        self.assertEqual(lines[2], "Due: 2026-11-02 12:00")

    def test_rental_line_priced(self):
        lines = receipt_lines(Rental("B7", "Ines", T0, T0.replace(hour=12)))
        self.assertEqual(lines[-1], "Rental (3 h): EUR 18.00")

    @unittest.skip("needs the counter printer")
    def test_prints_on_counter_printer(self):
        pass
''')
commit("2026-10-05T10:00:00+02:00", "Lena Brandt", "Harbor Bikes counter: prices, rentals, receipts")

write(".github/workflows/ci.yml", """
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
      - name: lint
        run: python3 -m compileall -q fleet tests
      - name: unit tests
        run: python3 -m unittest discover -s tests -v
      - name: smoke
        run: python3 -m fleet.cli quote --hours 3
""")
commit("2026-10-20T15:30:00+02:00", "Tomas Ek", "ci: lint, unit tests and a smoke quote")

# The weekend rate arrives with its test, and rental_price never reads it: main is red from here on.
write("fleet/pricing.py", PRICING)
p = ROOT / "tests/test_pricing.py"
p.write_text(p.read_text().replace("from fleet.pricing import DAY_RATE, HOUR_RATE, rental_price",
                                   "from fleet.pricing import DAY_RATE, HOUR_RATE, WEEKEND_DAY_RATE, rental_price")
             + textwrap.indent(textwrap.dedent('''
    def test_weekend_day_rate(self):
        self.assertEqual(rental_price(24, weekend=True), WEEKEND_DAY_RATE)
'''), "    "))
commit("2026-11-12T11:45:00+01:00", "Lena Brandt", "pricing: weekend day rate")

write(".workflow/designs/20261118-1000-late-returns.md", """
# Design: late returns

**Status:** resolved
**Date:** 2026-11-18
**Questions:** 6 of ~6 resolved · 0 deferred
**Charter:** a bike brought back after its due time costs the customer a late fee, which the counter shows, staff can waive with a reason, and which must be settled before the same customer rents again.

## Requirements
- **R1** — a rental returned after its due time is charged a late fee for each started hour late, at the hourly rate.
- **R2** — the late fee for one rental is capped at one day rate.
- **R3** — the counter receipt shows the late fee as a line of its own, with the hours late.
- **R4** — a customer who owes a late fee cannot start a new rental until it is paid or waived.
- **R5** — staff can waive a late fee; the waiver needs a reason and is written to the audit log with who waived it.
- **J1** (journey) — a customer returns two hours late, sees the late fee on the receipt, staff waive it with a reason, and the reprinted receipt shows the fee waived.

## Decisions
1. The fee is computed from `Rental.due` and the return time, in started hours — counter staff count that way today.
2. The cap is the weekday day rate, weekend or not — the owner's rule.
3. The receipt takes the fee as a number; it does not compute it — the fee has one home.
4. Waivers go to an append-only audit log (`audit/waivers.log`), one line each.
5. A waived fee stays on the receipt, struck through — the customer sees what was waived.
6. No change to how rentals are priced.

## Decomposition
One pull request per slice. They merge in this order, because each builds on the one before:

| # | Slice | Delivers | Touches |
|---|---|---|---|
| 1 | `late-fee` — the fee, its cap | R1, R2 | `fleet/late_fee.py`, tests |
| 2 | `receipt` — the late-fee line | R3 | `fleet/receipt.py`, tests |
| 3 | `waiver` — staff waiver and its audit line | R5 | `fleet/waiver.py`, `audit/`, tests |

## Out of scope
- Card payments for late fees (the till handles payment).
- Changing the hourly or day rates.
""")
PY

echo "nexus-setup: $(git rev-list --count main) commits, main at $(git rev-parse --short main)"
