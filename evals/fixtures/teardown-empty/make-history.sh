#!/usr/bin/env bash
# Build this fixture's git repository in repo/: a small stdlib-Python reservations
# service. main holds the service; feature/cutoff adds the cutoff rule, its tests and a
# review ledger, was merged into main, and is left checked out with a clean tree.
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

mkdir -p reservations tests .workflow

# ================================================================ main
cat > README.md <<'EOF'
# Reservations service

Bookings are submitted through `BookingService.submit` (the public seam). Constraint
rules live in `reservations/rules.py`; each returns a violation code or `None`, and
violations surface to callers as `Rejected(codes)`. Config is read per account through
`config_source.for_account`. Standard library only.

    python3 -m unittest        # from the repository root
EOF
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
EOF
: > reservations/__init__.py
: > tests/__init__.py
cat > reservations/booking.py <<'EOF'
"""Bookings: the aggregate and the service that submits them."""
from dataclasses import dataclass
from datetime import datetime

from reservations.rules import ACTIVE_RULES


class Rejected(Exception):
    def __init__(self, codes):
        super().__init__(", ".join(codes))
        self.codes = codes


@dataclass(frozen=True)
class Booking:
    account_id: str
    venue_id: str
    slot: datetime
    party_size: int
    submitted_at: datetime


def validate(booking, config):
    """Run every active rule, returning all violation codes."""
    return [code for rule in ACTIVE_RULES if (code := rule(booking, config)) is not None]


class BookingService:
    def __init__(self, store, config_source, clock=datetime.now):
        self.store = store
        self.config_source = config_source
        self.clock = clock

    def submit(self, account_id, venue_id, slot, party_size):
        booking = Booking(account_id, venue_id, slot, party_size, self.clock())
        codes = validate(booking, self.config_source.for_account(account_id))
        if codes:
            raise Rejected(codes)
        self.store.save(booking)
        return booking
EOF
cat > reservations/rules.py <<'EOF'
"""Constraint rules. Each takes a booking and its account config and returns a
violation code, or None when the booking passes."""

MAX_PARTY_DEFAULT = 12
OPENS_AT_DEFAULT = 9
CLOSES_AT_DEFAULT = 23


def check_party_size(booking, config):
    limit = int(config.get("max_party", MAX_PARTY_DEFAULT))
    if booking.party_size > limit:
        return "PARTY_TOO_LARGE"
    return None


def check_venue_open(booking, config):
    opens = int(config.get("opens_at", OPENS_AT_DEFAULT))
    closes = int(config.get("closes_at", CLOSES_AT_DEFAULT))
    if not opens <= booking.slot.hour < closes:
        return "VENUE_CLOSED"
    return None


ACTIVE_RULES = [check_party_size, check_venue_open]
EOF
cat > tests/support.py <<'EOF'
"""Test doubles and a pinned clock, shared by the test modules."""
from datetime import datetime

from reservations.booking import BookingService

NOW = datetime(2026, 12, 1, 12, 0)
EVENING = datetime(2026, 12, 3, 19, 30)


class FakeStore:
    def __init__(self):
        self.saved = []

    def save(self, booking):
        self.saved.append(booking)


class FakeConfig:
    def __init__(self, **settings):
        self.settings = settings

    def for_account(self, account_id):
        return dict(self.settings)


def service(now=NOW, **settings):
    store = FakeStore()
    return BookingService(store, FakeConfig(**settings), clock=lambda: now), store
EOF
cat > tests/test_booking.py <<'EOF'
import unittest
from datetime import datetime

from reservations.booking import Rejected
from tests.support import EVENING, service


class PartySizeTest(unittest.TestCase):
    def test_party_size_rule(self):
        cases = [
            (1, None),
            (12, None),
            (13, "PARTY_TOO_LARGE"),
            (40, "PARTY_TOO_LARGE"),
        ]
        for size, code in cases:
            with self.subTest(party_size=size):
                svc, store = service()
                if code is None:
                    svc.submit("acct-1", "venue-1", EVENING, size)
                    self.assertEqual(len(store.saved), 1)
                else:
                    with self.assertRaises(Rejected) as e:
                        svc.submit("acct-1", "venue-1", EVENING, size)
                    self.assertEqual(e.exception.codes, [code])
                    self.assertEqual(store.saved, [])

    def test_party_limit_reads_from_account_config(self):
        svc, store = service(max_party=6)
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", EVENING, 7)
        self.assertEqual(e.exception.codes, ["PARTY_TOO_LARGE"])


class OpeningHoursTest(unittest.TestCase):
    def test_open_venue_accepted(self):
        svc, store = service()
        svc.submit("acct-1", "venue-1", EVENING, 4)
        self.assertEqual(len(store.saved), 1)

    def test_closed_venue_rejected(self):
        # an 08:00 breakfast slot; the venue opens at 09:00
        svc, store = service()
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", datetime(2026, 12, 3, 8, 0), 2)
        self.assertEqual(e.exception.codes, ["VENUE_CLOSED"])
        self.assertEqual(store.saved, [])


if __name__ == "__main__":
    unittest.main()
EOF
commit "2026-10-02T09:15:00+00:00" "Maya Ortiz" "Reservations service: party-size and opening-hours rules"

# ================================================================ feature/cutoff
git checkout -q -b feature/cutoff

cat > reservations/rules.py <<'EOF'
"""Constraint rules. Each takes a booking and its account config and returns a
violation code, or None when the booking passes."""
from datetime import timedelta

MAX_PARTY_DEFAULT = 12
OPENS_AT_DEFAULT = 9
CLOSES_AT_DEFAULT = 23
CUTOFF_MINUTES_DEFAULT = 120


def check_party_size(booking, config):
    limit = int(config.get("max_party", MAX_PARTY_DEFAULT))
    if booking.party_size > limit:
        return "PARTY_TOO_LARGE"
    return None


def check_venue_open(booking, config):
    opens = int(config.get("opens_at", OPENS_AT_DEFAULT))
    closes = int(config.get("closes_at", CLOSES_AT_DEFAULT))
    if not opens <= booking.slot.hour < closes:
        return "VENUE_CLOSED"
    return None


def check_cutoff(booking, config):
    window = timedelta(minutes=CUTOFF_MINUTES_DEFAULT)
    if booking.slot - booking.submitted_at < window:
        return "CUTOFF_WINDOW"
    return None


ACTIVE_RULES = [check_party_size, check_venue_open, check_cutoff]
EOF
cat > tests/test_cutoff.py <<'EOF'
import unittest
from datetime import timedelta

from reservations.booking import Rejected
from tests.support import NOW, service


def in_minutes(m):
    return NOW + timedelta(minutes=m)


class CutoffTest(unittest.TestCase):
    def test_booking_inside_cutoff_window_is_rejected(self):
        svc, store = service()
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", in_minutes(30), 2)
        self.assertEqual(e.exception.codes, ["CUTOFF_WINDOW"])
        self.assertEqual(store.saved, [])

    def test_booking_outside_cutoff_window_is_accepted(self):
        svc, store = service()
        svc.submit("acct-1", "venue-1", in_minutes(180), 2)
        self.assertEqual(len(store.saved), 1)

    def test_cutoff_window_reads_from_account_config(self):
        svc, store = service(cutoff_minutes=60)
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", in_minutes(30), 2)
        self.assertEqual(e.exception.codes, ["CUTOFF_WINDOW"])


if __name__ == "__main__":
    unittest.main()
EOF
commit "2026-11-10T09:40:00+00:00" "Maya Ortiz" "cutoff: reject bookings inside the cutoff window"

cat > .workflow/ledger.md <<'EOF'
# Ledger — cancellation cutoff

## Iteration 1

### Smells
- **N1** Change Preventers / Shotgun Surgery at the four default constants in `reservations/rules.py` — noted: one module, four adjacent lines; a settings object costs more than it saves
  - **Promote if:** a rule outside `reservations/rules.py` needs one of these defaults
EOF
commit "2026-11-10T15:20:00+00:00" "Maya Ortiz" "refactor-review: smells for the cutoff change"

git checkout -q main
GIT_AUTHOR_DATE="2026-11-12T10:05:00+00:00" GIT_COMMITTER_DATE="2026-11-12T10:05:00+00:00" \
GIT_AUTHOR_NAME="Sam Achebe" GIT_COMMITTER_NAME="Sam Achebe" \
GIT_AUTHOR_EMAIL="Sam.Achebe@example.invalid" GIT_COMMITTER_EMAIL="Sam.Achebe@example.invalid" \
git merge -q --no-ff feature/cutoff -m "Merge branch 'feature/cutoff'"
git checkout -q feature/cutoff
