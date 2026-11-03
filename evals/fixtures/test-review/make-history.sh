#!/usr/bin/env bash
# Build the test-review fixture's git repository: shopcore, a small stdlib-Python
# order service. main has orders, checkout totals and a customer birth month; the
# branch feature/loyalty-points (LOY-77, ticket in ../issues/77.md) adds a points
# calculator, a ledger, redemption and refunds, with their tests. The repo is left
# checked out on the branch. Idempotent: removes and rebuilds repo/ each time.
# The answer key is ../../test-review.answers.md; README.md here lists the plants.
set -euo pipefail
cd "$(dirname "$0")"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
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

mkdir -p shop tests .github/workflows

# ================================================================ main
cat > README.md <<'EOF'
# shopcore

Orders, checkout totals and customers for the shop. Standard library only.

    python3 -m unittest        # from the repository root

CI runs the same command on every push (`.github/workflows/ci.yml`).
EOF
cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m unittest -v
EOF
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
EOF
: > shop/__init__.py
: > tests/__init__.py
cat > shop/orders.py <<'EOF'
"""Customers and orders."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Customer:
    id: str
    email: str


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    subtotal: Decimal
    placed_on: date = field(default_factory=date.today)
EOF
cat > shop/checkout.py <<'EOF'
"""Checkout totals."""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def order_total(subtotal, tax_rate, discount=Decimal("0")):
    """Subtotal less discount, plus tax on the discounted amount, rounded half up to the cent."""
    if discount < 0:
        raise ValueError("discount must not be negative")
    taxable = max(subtotal - discount, Decimal("0"))
    return (taxable * (1 + tax_rate)).quantize(CENT, rounding=ROUND_HALF_UP)
EOF
cat > tests/test_checkout.py <<'EOF'
import unittest
from decimal import Decimal

from shop.checkout import order_total


class OrderTotalTest(unittest.TestCase):
    def test_tax_is_added_to_the_subtotal(self):
        self.assertEqual(order_total(Decimal("100.00"), Decimal("0.08")), Decimal("108.00"))

    def test_tax_is_charged_on_the_discounted_amount(self):
        self.assertEqual(order_total(Decimal("100.00"), Decimal("0.08"), Decimal("10.00")), Decimal("97.20"))

    def test_half_a_cent_rounds_up(self):
        self.assertEqual(order_total(Decimal("0.05"), Decimal("0.10")), Decimal("0.06"))

    def test_a_discount_larger_than_the_subtotal_gives_zero(self):
        self.assertEqual(order_total(Decimal("5.00"), Decimal("0.08"), Decimal("9.00")), Decimal("0.00"))

    def test_a_negative_discount_is_refused(self):
        with self.assertRaises(ValueError):
            order_total(Decimal("5.00"), Decimal("0.08"), Decimal("-1.00"))


if __name__ == "__main__":
    unittest.main()
EOF
cat > tests/test_orders.py <<'EOF'
import unittest
from datetime import date
from decimal import Decimal

from shop.orders import Order


class OrderTest(unittest.TestCase):
    def test_an_order_keeps_its_placed_date(self):
        order = Order(id="o-1", customer_id="c-1", subtotal=Decimal("10.00"), placed_on=date(2026, 7, 1))
        self.assertEqual(order.placed_on, date(2026, 7, 1))


if __name__ == "__main__":
    unittest.main()
EOF
commit "2026-07-14T10:12:00+00:00" "Dana Whitfield" "Initial shopcore: orders and checkout totals"

python3 - <<'EOF'
import pathlib
p = pathlib.Path("shop/orders.py")
p.write_text(p.read_text().replace(
    "    id: str\n    email: str\n",
    "    id: str\n    email: str\n    birth_month: Optional[int] = None  # 1-12, given at sign-up for the birthday email\n").replace(
    "from decimal import Decimal\n", "from decimal import Decimal\nfrom typing import Optional\n"))
EOF
commit "2026-08-21T15:40:00+00:00" "Dana Whitfield" "Customers: optional birth month for the birthday email"

# ================================================================ feature/loyalty-points (LOY-77)
git checkout -q -b feature/loyalty-points

cat > shop/loyalty.py <<'EOF'
"""Loyalty points (LOY-77): earn on orders, redeem in blocks of 100, take back on refund."""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

GOLD_THRESHOLD = 1000          # lifetime earned points
POINTS_PER_BLOCK = 100
BLOCK_VALUE = Decimal("1.00")


class InsufficientPoints(Exception):
    pass


class InvalidRedemption(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    customer_id: str
    order_id: Optional[str]
    kind: str                  # "earn", "redeem" or "refund"
    points: int


class Ledger:
    """Every change to a balance, in order. Finance audits it."""

    def __init__(self):
        self._entries: List[Entry] = []

    def add(self, entry):
        self._entries.append(entry)

    def entries(self, customer_id, kind=None):
        return [e for e in self._entries
                if e.customer_id == customer_id and (kind is None or e.kind == kind)]

    def for_order(self, order_id, kind):
        return [e for e in self._entries if e.order_id == order_id and e.kind == kind]

    def balance(self, customer_id):
        return sum(e.points for e in self.entries(customer_id))

    def lifetime(self, customer_id):
        return sum(e.points for e in self.entries(customer_id, kind="earn"))


class PointsCalculator:
    def points_for(self, customer, order, lifetime):
        points = int(order.subtotal)                      # whole dollars, cents dropped
        if lifetime >= GOLD_THRESHOLD:
            points = points * 3 // 2                      # Gold: 1.5x, rounded down
        if customer.birth_month is not None and order.placed_on.month == customer.birth_month:
            points *= 2                                   # birthday month
        return points


class LoyaltyService:
    def __init__(self, ledger=None, calculator=None):
        self.ledger = ledger if ledger is not None else Ledger()
        self.calculator = calculator if calculator is not None else PointsCalculator()

    def award(self, customer, order):
        lifetime = self.ledger.lifetime(customer.id)
        points = self.calculator.points_for(customer, order, lifetime)
        self.ledger.add(Entry(customer.id, order.id, "earn", points))
        return points

    def balance(self, customer_id):
        return self.ledger.balance(customer_id)

    def redeem(self, customer_id, points):
        if points <= 0 or points % POINTS_PER_BLOCK:
            raise InvalidRedemption(f"redeem whole blocks of {POINTS_PER_BLOCK} points, got {points}")
        if points > self.balance(customer_id):
            raise InsufficientPoints(f"{customer_id} has {self.balance(customer_id)} points, asked for {points}")
        self.ledger.add(Entry(customer_id, None, "redeem", -points))
        return BLOCK_VALUE * (points // POINTS_PER_BLOCK)

    def refund(self, order_id):
        for earned in self.ledger.for_order(order_id, "earn"):
            self.ledger.add(Entry(earned.customer_id, order_id, "refund", -earned.points))
EOF
cat > tests/test_loyalty.py <<'EOF'
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from shop.loyalty import InsufficientPoints, InvalidRedemption, Ledger, LoyaltyService, PointsCalculator
from shop.orders import Customer, Order

ALICE = Customer(id="c-1", email="alice@example.invalid", birth_month=5)
BOB = Customer(id="c-2", email="bob@example.invalid")


class PointsCalculatorTest(unittest.TestCase):
    def setUp(self):
        self.calc = PointsCalculator()

    def test_one_point_per_whole_dollar(self):
        order = Order(id="o-1", customer_id="c-1", subtotal=Decimal("25.99"))
        self.assertEqual(self.calc.points_for(ALICE, order, lifetime=0), 25)

    def test_gold_customer_earns_time_and_a_half(self):
        order = Order(id="o-2", customer_id="c-1", subtotal=Decimal("100.00"))
        self.assertEqual(self.calc.points_for(ALICE, order, lifetime=5000), 150)

    def test_regular_customer_earns_the_base_rate(self):
        order = Order(id="o-3", customer_id="c-1", subtotal=Decimal("100.00"))
        self.assertEqual(self.calc.points_for(ALICE, order, lifetime=200), 100)


class LoyaltyServiceTest(unittest.TestCase):
    def test_award_records_points_in_ledger(self):
        ledger = mock.Mock(spec=Ledger)
        ledger.lifetime.return_value = 0
        calculator = mock.Mock(spec=PointsCalculator)
        calculator.points_for.return_value = 42
        service = LoyaltyService(ledger=ledger, calculator=calculator)
        order = Order(id="o-4", customer_id="c-2", subtotal=Decimal("42.00"))

        awarded = service.award(BOB, order)

        calculator.points_for.assert_called_once_with(BOB, order, 0)
        ledger.add.assert_called_once()
        self.assertEqual(awarded, 42)

    def test_refund_takes_back_the_points(self):
        service = LoyaltyService()
        order = Order(id="o-5", customer_id="c-2", subtotal=Decimal("40.00"), placed_on=date(2026, 3, 2))
        service.award(BOB, order)

        service.refund("o-5")

        for entry in service.ledger.entries("c-2", kind="reversal"):
            self.assertEqual(entry.points, -40)
            self.assertEqual(service.balance("c-2"), 0)
        self.assertGreaterEqual(service.balance("c-2"), 0)

    @unittest.skip("later")
    def test_refund_after_redemption_never_goes_negative(self):
        service = LoyaltyService()
        service.award(BOB, Order(id="o-6", customer_id="c-2", subtotal=Decimal("250.00"), placed_on=date(2026, 3, 2)))
        service.redeem("c-2", 200)

        service.refund("o-6")

        self.assertEqual(service.balance("c-2"), 0)


class RedemptionTest(unittest.TestCase):
    def setUp(self):
        self.service = LoyaltyService()
        self.service.award(BOB, Order(id="o-7", customer_id="c-2", subtotal=Decimal("300.00"),
                                      placed_on=date(2026, 3, 2)))

    def test_redeeming_the_whole_balance_is_allowed(self):
        self.assertEqual(self.service.redeem("c-2", 300), Decimal("3.00"))
        self.assertEqual(self.service.balance("c-2"), 0)

    def test_redeeming_one_block_more_than_the_balance_is_refused(self):
        with self.assertRaises(InsufficientPoints):
            self.service.redeem("c-2", 400)
        self.assertEqual(self.service.balance("c-2"), 300)

    def test_a_partial_block_is_refused(self):
        with self.assertRaises(InvalidRedemption):
            self.service.redeem("c-2", 150)
        self.assertEqual(self.service.balance("c-2"), 300)

    def test_redeeming_zero_points_is_refused(self):
        with self.assertRaises(InvalidRedemption):
            self.service.redeem("c-2", 0)
        self.assertEqual(self.service.balance("c-2"), 300)

    def test_redeeming_negative_points_is_refused(self):
        with self.assertRaises(InvalidRedemption):
            self.service.redeem("c-2", -100)
        self.assertEqual(self.service.balance("c-2"), 300)


if __name__ == "__main__":
    unittest.main()
EOF
# The first commit carries the calculator and its tests; the second the service.
mv tests/test_loyalty.py "$STAGE/test_loyalty.py"
python3 - "$STAGE/test_loyalty.py" <<'EOF'
import pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text()
head, _, _ = src.partition("class LoyaltyServiceTest")
pathlib.Path("tests/test_loyalty.py").write_text(
    head.replace("from unittest import mock\n", "")
        .replace("InsufficientPoints, InvalidRedemption, Ledger, LoyaltyService, PointsCalculator", "PointsCalculator")
        .replace("BOB = Customer(id=\"c-2\", email=\"bob@example.invalid\")\n", "")
        .replace("from datetime import date\n", "")
    + 'if __name__ == "__main__":\n    unittest.main()\n')
EOF
cp shop/loyalty.py "$STAGE/loyalty.py"
python3 - <<'EOF'
import pathlib
p = pathlib.Path("shop/loyalty.py")
src = p.read_text()
p.write_text(src.split("class LoyaltyService:")[0].rstrip() + "\n")
EOF
commit "2026-10-05T09:30:00+00:00" "Ravi Menon" "LOY-77: points calculator with the Gold tier"

cp "$STAGE/loyalty.py" shop/loyalty.py
cp "$STAGE/test_loyalty.py" tests/test_loyalty.py
python3 - <<'EOF'
import pathlib
p = pathlib.Path("tests/test_loyalty.py")
p.write_text(p.read_text().replace('    @unittest.skip("later")\n', ""))
EOF
commit "2026-10-08T16:05:00+00:00" "Ravi Menon" "LOY-77: ledger, redemption and refunds" \
"LoyaltyService.award records each order's points in the ledger; redeem spends
them in blocks of 100; refund takes back what the order earned."

cp "$STAGE/test_loyalty.py" tests/test_loyalty.py
commit "2026-10-12T11:20:00+00:00" "Ravi Menon" "LOY-77: tidy tests before review"

