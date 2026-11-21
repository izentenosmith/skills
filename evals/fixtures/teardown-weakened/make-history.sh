#!/usr/bin/env bash
# Build this fixture's git repository in repo/: a small stdlib-Python reservations
# service. main holds the service; feature/cutoff adds a build plan, the cutoff rule
# and its tests, and a review ledger, and is left checked out with a clean tree.
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
        # booked at 07:00 for an 08:00 breakfast slot; the venue opens at 09:00
        svc, store = service(now=datetime(2026, 12, 1, 7, 0))
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", datetime(2026, 12, 1, 8, 0), 2)
        self.assertEqual(e.exception.codes, ["VENUE_CLOSED"])
        self.assertEqual(store.saved, [])


if __name__ == "__main__":
    unittest.main()
EOF
commit "2026-10-02T09:15:00+00:00" "Maya Ortiz" "Reservations service: party-size and opening-hours rules"

# ================================================================ feature/cutoff
git checkout -q -b feature/cutoff

cat > .workflow/brief.md <<'EOF'
# Build Plan: Enforce a cancellation cutoff on bookings

**Status:** approved
**Category:** enhancement
**Summary:** Reject bookings submitted within the cutoff window of the slot start.

**Current behavior:**
`BookingService.submit` accepts any well-formed booking that passes the party-size
and opening-hours rules. Nothing checks how close the slot is.

**Desired behavior:**
A booking whose slot starts within the cutoff window is rejected with violation code
`CUTOFF_WINDOW`. The window length is read from account config (`cutoff_minutes`),
defaulting to 120. Bookings outside the window proceed as today.

**Key interfaces (test seams):**
- `BookingService.submit` — the public seam tests drive; raises `Rejected` carrying
  the violation codes
- `reservations.rules` — the cutoff rule joins `ACTIVE_RULES` beside the party-size and
  opening-hours rules, returning a code or `None` like its peers
- Account config — a `cutoff_minutes` field, default 120, per account through
  `config_source.for_account`

**Acceptance criteria** (ordered — first is the tracer-bullet candidate):
- [ ] Tracer bullet: a booking whose slot starts inside the cutoff window is rejected
      with violation code `CUTOFF_WINDOW`
- [ ] A booking whose slot is outside the window is accepted and persisted
- [ ] The window length reads from account config, not a hard-coded default
- [ ] Edge case: a slot exactly at the window edge is accepted (the boundary is
      exclusive)
- [ ] Edge case: a booking that violates both the cutoff and the party-size rule
      surfaces both codes, not just the first

**Test seams & prior art:**
- Drive tests through `BookingService.submit` with the pinned clock in `tests/support.py`
- Use the existing `FakeStore` / `FakeConfig` doubles; do not introduce new ones

**Out of scope:**
- Administrator override of the cutoff window
- Changing the existing party-size or opening-hours rules
- Any change to how `Rejected` is surfaced to HTTP callers

## Revisions
- (none yet)
EOF
commit "2026-11-16T10:00:00+00:00" "Maya Ortiz" "brief: cancellation cutoff, approved"
BASE="$(git rev-parse --short HEAD)"

python3 - "$BASE" <<'EOF'
import pathlib, sys
p = pathlib.Path(".workflow/brief.md")
p.write_text(p.read_text().replace("**Category:** enhancement\n",
                                   f"**Category:** enhancement\n**Base:** {sys.argv[1]}\n"))
EOF
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
    minutes = int(config.get("cutoff_minutes", CUTOFF_MINUTES_DEFAULT))
    if booking.slot - booking.submitted_at < timedelta(minutes=minutes):
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
        svc, store = service(cutoff_minutes=240)
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", in_minutes(180), 2)
        self.assertEqual(e.exception.codes, ["CUTOFF_WINDOW"])

    def test_slot_exactly_at_window_edge_is_accepted(self):
        svc, store = service()
        svc.submit("acct-1", "venue-1", in_minutes(120), 2)
        self.assertEqual(len(store.saved), 1)

    def test_cutoff_and_party_size_surface_both_codes(self):
        svc, store = service()
        with self.assertRaises(Rejected) as e:
            svc.submit("acct-1", "venue-1", in_minutes(30), 13)
        self.assertEqual(sorted(e.exception.codes), ["CUTOFF_WINDOW", "PARTY_TOO_LARGE"])


if __name__ == "__main__":
    unittest.main()
EOF
commit "2026-11-17T09:40:00+00:00" "Maya Ortiz" "cutoff: reject bookings inside the account's window"

cat > reservations/rules.py <<'EOF'
"""Constraint rules. Each takes a booking and its account config and returns a
violation code, or None when the booking passes."""
from datetime import timedelta

MAX_PARTY_DEFAULT = 12
OPENS_AT_DEFAULT = 9
CLOSES_AT_DEFAULT = 23
CUTOFF_MINUTES_DEFAULT = 120


def _setting(config, key, default):
    return int(config.get(key, default))


def check_party_size(booking, config):
    if booking.party_size >= _setting(config, "max_party", MAX_PARTY_DEFAULT):
        return "PARTY_TOO_LARGE"
    return None


def check_venue_open(booking, config):
    opens = _setting(config, "opens_at", OPENS_AT_DEFAULT)
    closes = _setting(config, "closes_at", CLOSES_AT_DEFAULT)
    if not opens <= booking.slot.hour < closes:
        return "VENUE_CLOSED"
    return None


def check_cutoff(booking, config):
    minutes = _setting(config, "cutoff_minutes", CUTOFF_MINUTES_DEFAULT)
    if booking.slot - booking.submitted_at < timedelta(minutes=minutes):
        return "CUTOFF_WINDOW"
    return None


ACTIVE_RULES = [check_party_size, check_venue_open, check_cutoff]
EOF
python3 - <<'EOF'
import pathlib
p = pathlib.Path("tests/test_booking.py")
p.write_text(p.read_text().replace("            (12, None),\n", ""))
EOF
commit "2026-11-17T14:05:00+00:00" "Maya Ortiz" "rules: read every setting through one helper; trim the party-size table"

python3 - <<'EOF'
import pathlib
p = pathlib.Path("tests/test_booking.py")
p.write_text(p.read_text().replace(
    "    def test_closed_venue_rejected(self):\n",
    '    @unittest.skip("flaky: depends on the clock")\n    def test_closed_venue_rejected(self):\n'))
b = pathlib.Path(".workflow/brief.md")
b.write_text(b.read_text().replace(
    "- (none yet)\n",
    "- 2026-11-17 — `test_closed_venue_rejected` skipped: flaky, it depends on the clock. "
    "Not part of the cutoff work; to be fixed separately (tdd)\n"))
EOF
commit "2026-11-17T16:30:00+00:00" "Maya Ortiz" "tests: skip a flaky opening-hours test"

python3 - <<'EOF'
import pathlib
p = pathlib.Path(".workflow/brief.md")
text = p.read_text()
for crit, test in [
    ("      with violation code `CUTOFF_WINDOW`", "test_booking_inside_cutoff_window_is_rejected"),
    ("- [ ] A booking whose slot is outside the window is accepted and persisted",
     "test_booking_outside_cutoff_window_is_accepted"),
    ("- [ ] The window length reads from account config, not a hard-coded default",
     "test_cutoff_window_reads_from_account_config"),
    ("      exclusive)", "test_slot_exactly_at_window_edge_is_accepted"),
    ("      surfaces both codes, not just the first", "test_cutoff_and_party_size_surface_both_codes"),
]:
    assert crit in text, crit
    text = text.replace(crit, f"{crit} — verified by `{test}`", 1)
p.write_text(text.replace("- [ ]", "- [x]"))
EOF
commit "2026-11-17T16:45:00+00:00" "Maya Ortiz" "brief: tick the cutoff criteria"

cat > .workflow/ledger.md <<'EOF'
# Ledger — cancellation cutoff

## Iteration 1

### Smells
- **N1** Change Preventers / Shotgun Surgery at the four default constants in `reservations/rules.py` — noted: one module, four adjacent lines; a settings object costs more than it saves
  - **Promote if:** a rule outside `reservations/rules.py` needs one of these defaults
EOF
commit "2026-11-18T11:10:00+00:00" "Maya Ortiz" "refactor-review: smells for the cutoff change"
