#!/usr/bin/env bash
# Build repo/: parcels, a small stdlib-Python shipping-quote library (python3 -m unittest).
# main has standard quotes and shipping labels; feature/express-quotes (checked out) adds
# express quotes in two commits. Fixed dates and authors, so the SHAs are stable.
# Idempotent: removes and rebuilds repo/ each time.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

commit() { # commit <iso-date> <author> <subject>
  git add -A
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  GIT_AUTHOR_NAME="$2" GIT_COMMITTER_NAME="$2" \
  GIT_AUTHOR_EMAIL="${2// /.}@example.invalid" \
  GIT_COMMITTER_EMAIL="${2// /.}@example.invalid" \
  git commit -q -m "$3"
}

mkdir -p parcels tests

# ================================================================ main
cat > README.md <<'EOF'
# parcels

Shipping quotes and labels for the warehouse. Standard library only.

    python3 -m unittest discover -s tests -t .     # from the repository root

Prices are `Decimal`, rounded half up to the cent once, at the end of a quote.
EOF
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
EOF
: > parcels/__init__.py
: > tests/__init__.py
cat > parcels/rates.py <<'EOF'
"""Shipping quotes."""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")

ZONE_RATES = {
    "domestic": Decimal("4.50"),
    "regional": Decimal("7.25"),
    "international": Decimal("15.00"),
}
PER_KG = {
    "domestic": Decimal("0.80"),
    "regional": Decimal("1.40"),
    "international": Decimal("3.10"),
}


class UnknownZone(ValueError):
    pass


def standard_quote(weight_kg, zone):
    """Base rate for the zone plus a per-kilo rate, rounded half up to the cent."""
    if zone not in ZONE_RATES:
        raise UnknownZone(zone)
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    price = ZONE_RATES[zone] + PER_KG[zone] * Decimal(str(weight_kg))
    return price.quantize(CENT, rounding=ROUND_HALF_UP)
EOF
cat > parcels/labels.py <<'EOF'
"""Shipping labels."""


def format_label(name, street, city, postcode, country, weight_kg, service):
    # build the name line
    name_line = name.strip().upper()
    if len(name_line) > 32:
        name_line = name_line[:32]
    # build the street line
    street_line = street.strip()
    if len(street_line) > 32:
        street_line = street_line[:32]
    # build the city line
    city_line = (postcode.strip() + " " + city.strip()).strip()
    if len(city_line) > 32:
        city_line = city_line[:32]
    # build the country line
    country_line = country.strip().upper()
    if len(country_line) > 32:
        country_line = country_line[:32]
    # the weight line, one decimal
    weight_line = "%.1f kg  %s" % (weight_kg, service.upper())
    return "\n".join([name_line, street_line, city_line, country_line, weight_line])
EOF
cat > tests/test_rates.py <<'EOF'
import unittest
from decimal import Decimal

from parcels.rates import UnknownZone, standard_quote


class StandardQuoteTest(unittest.TestCase):
    def test_domestic_one_kilo(self):
        self.assertEqual(standard_quote(1, "domestic"), Decimal("5.30"))

    def test_regional_adds_the_per_kilo_rate(self):
        self.assertEqual(standard_quote(2, "regional"), Decimal("10.05"))

    def test_international(self):
        self.assertEqual(standard_quote(3, "international"), Decimal("24.30"))

    def test_an_unknown_zone_is_refused(self):
        with self.assertRaises(UnknownZone):
            standard_quote(1, "mars")

    def test_weight_must_be_positive(self):
        with self.assertRaises(ValueError):
            standard_quote(0, "domestic")


if __name__ == "__main__":
    unittest.main()
EOF
cat > tests/test_labels.py <<'EOF'
import unittest

from parcels.labels import format_label


class LabelTest(unittest.TestCase):
    def test_a_label_has_five_lines(self):
        label = format_label("Ana Ruiz", "Calle Mayor 4", "Madrid", "28013", "Spain", 2.25, "standard")
        self.assertEqual(label.splitlines(), ["ANA RUIZ", "Calle Mayor 4", "28013 Madrid", "SPAIN", "2.2 kg  STANDARD"])

    def test_long_lines_are_cut_at_32_characters(self):
        label = format_label("x" * 40, "y" * 40, "z", "1", "w" * 40, 1, "standard")
        self.assertTrue(all(len(line) <= 32 for line in label.splitlines()))


if __name__ == "__main__":
    unittest.main()
EOF
commit "2026-09-08T09:15:00+00:00" "Lena Okafor" "Standard quotes and shipping labels"

# ================================================================ feature/express-quotes
git checkout -q -b feature/express-quotes

cat >> parcels/rates.py <<'EOF'


def express_quote(weight_kg, zone, saturday=False):
    # check the zone is one we ship to
    if zone not in ZONE_RATES:
        raise UnknownZone(zone)
    # check the weight makes sense
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    # work out the standard price first
    price = ZONE_RATES[zone] + PER_KG[zone] * Decimal(str(weight_kg))
    # express is 60% on top of standard
    price = price * Decimal("1.6")
    # saturday delivery costs a flat 5.00 more
    if saturday:
        price = price + Decimal("5.00")
    return price.quantize(CENT, rounding=ROUND_HALF_UP)
EOF
python3 - <<'EOF'
import pathlib
p = pathlib.Path("tests/test_rates.py")
src = p.read_text()
src = src.replace("from parcels.rates import UnknownZone, standard_quote",
                  "from parcels.rates import UnknownZone, express_quote, standard_quote")
src = src.replace('\n\nif __name__ == "__main__":', '''

class ExpressQuoteTest(unittest.TestCase):
    def test_express_is_sixty_percent_over_standard(self):
        self.assertEqual(express_quote(1, "domestic"), Decimal("8.48"))

    def test_express_regional(self):
        self.assertEqual(express_quote(2, "regional"), Decimal("16.08"))

    def test_saturday_adds_a_flat_five(self):
        self.assertEqual(express_quote(1, "domestic", saturday=True), Decimal("13.48"))

    def test_an_unknown_zone_is_refused(self):
        with self.assertRaises(UnknownZone):
            express_quote(1, "mars")

    def test_weight_must_be_positive(self):
        with self.assertRaises(ValueError):
            express_quote(-1, "regional")


if __name__ == "__main__":''')
p.write_text(src)
EOF
commit "2026-11-02T14:40:00+00:00" "Tomas Brandt" "Express quotes: 60% over standard, Saturday surcharge"

python3 - <<'EOF'
import pathlib
p = pathlib.Path("parcels/rates.py")
p.write_text(p.read_text().replace(
    """    # saturday delivery costs a flat 5.00 more
    if saturday:
        price = price + Decimal("5.00")
""", """    # saturday delivery costs a flat 5.00 more, but not abroad
    if saturday:
        if zone != "international":
            price = price + Decimal("5.00")
"""))
p = pathlib.Path("tests/test_rates.py")
p.write_text(p.read_text().replace('''    def test_an_unknown_zone_is_refused(self):
        with self.assertRaises(UnknownZone):
            express_quote(1, "mars")''', '''    def test_no_saturday_surcharge_abroad(self):
        self.assertEqual(express_quote(3, "international", saturday=True), Decimal("38.88"))

    def test_an_unknown_zone_is_refused(self):
        with self.assertRaises(UnknownZone):
            express_quote(1, "mars")'''))
EOF
commit "2026-11-03T10:05:00+00:00" "Tomas Brandt" "Express: no Saturday surcharge on international parcels"
