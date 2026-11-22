"""Table-driven constraint tests, driven through the public handler on a fixed clock."""
import pytest
from datetime import datetime, timedelta
from reservations.api import BookingService, Rejected

NOW = datetime(2026, 11, 16, 12, 0)


def slot(hour=19, days_out=30):
    """A slot `days_out` days after NOW at `hour`, well clear of any cutoff window."""
    return (NOW + timedelta(days=days_out)).replace(hour=hour, minute=0)


def in_minutes(m):
    return NOW + timedelta(minutes=m)


class FakeStore:
    def __init__(self): self.saved = []
    def save(self, booking): self.saved.append(booking)


class FakeConfig:
    def __init__(self, cfg=None): self._cfg = cfg or {}
    def for_account(self, account_id): return self._cfg


def make_service(cfg=None, store=None):
    return BookingService(store or FakeStore(), FakeConfig(cfg), clock=lambda: NOW)


@pytest.fixture
def service():
    return make_service()


@pytest.mark.parametrize("party_size,expected", [(4, []), (12, []), (13, ["PARTY_TOO_LARGE"])])
def test_party_size_rule(service, party_size, expected):
    if expected:
        with pytest.raises(Rejected) as e:
            service.submit("acct-1", "venue-1", slot(), party_size)
        assert e.value.codes == expected
    else:
        assert service.submit("acct-1", "venue-1", slot(), party_size).party_size == party_size


def test_booking_outside_opening_hours_is_rejected(service):
    with pytest.raises(Rejected) as e:
        service.submit("acct-1", "venue-1", slot(hour=3), 2)
    assert "VENUE_CLOSED" in e.value.codes


# --- cutoff window ---

def test_booking_inside_cutoff_window_is_rejected(service):
    with pytest.raises(Rejected) as e:
        service.submit("acct-1", "venue-1", in_minutes(30), 2)
    assert e.value.codes == ["CUTOFF_WINDOW"]


def test_booking_outside_cutoff_window_is_accepted_and_persisted():
    store = FakeStore()
    booking = make_service(store=store).submit("acct-1", "venue-1", in_minutes(300), 2)
    assert store.saved == [booking]


def test_slot_exactly_at_window_edge_is_accepted(service):
    """Criterion 4: the boundary is exclusive (architect-deep-dive)."""
    booking = service.submit("acct-1", "venue-1", in_minutes(120), 2)
    assert booking.party_size == 2


def test_cutoff_and_party_size_violations_surface_both_codes(service):
    with pytest.raises(Rejected) as e:
        service.submit("acct-1", "venue-1", in_minutes(30), 13)
    assert sorted(e.value.codes) == ["CUTOFF_WINDOW", "PARTY_TOO_LARGE"]


# --- remediation, iteration 2: F1 and F2 ---

@pytest.mark.parametrize("cutoff,minutes_out,rejected", [
    (240, 180, True),   # inside the configured window, outside the default: F1's breaking case
    (240, 300, False),  # outside both
    (240, 240, False),  # exactly at the configured edge: exclusive
    (60, 90, False),    # a shorter configured window accepts what the default would reject
])
def test_window_length_reads_from_account_config(cutoff, minutes_out, rejected):
    service = make_service({"cutoff_minutes": cutoff})
    if rejected:
        with pytest.raises(Rejected) as e:
            service.submit("acct-1", "venue-1", in_minutes(minutes_out), 2)
        assert e.value.codes == ["CUTOFF_WINDOW"]
    else:
        assert service.submit("acct-1", "venue-1", in_minutes(minutes_out), 2).party_size == 2
