"""The cutoff window, driven through the public handler with the rules' clock held still."""
from datetime import datetime, timedelta

import pytest

from reservations import rules
from reservations.api import BookingService, Rejected
from test_booking import FakeConfig, FakeStore

NOW = datetime(2026, 11, 18, 12, 0)
OPEN = {"opens_at": 0, "closes_at": 24}


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(rules, "clock", lambda: NOW)


def service(store=None, **cfg):
    return BookingService(store or FakeStore(), FakeConfig({**OPEN, **cfg}))


def in_minutes(m):
    return NOW + timedelta(minutes=m)


def test_booking_inside_cutoff_window_is_rejected():
    with pytest.raises(Rejected) as e:
        service().submit("acct-1", "venue-1", in_minutes(30), 2)
    assert e.value.codes == ["CUTOFF_WINDOW"]


def test_booking_outside_cutoff_window_is_accepted_and_persisted():
    store = FakeStore()
    booking = service(store).submit("acct-1", "venue-1", in_minutes(180), 2)
    assert store.saved == [booking]


@pytest.mark.parametrize("cutoff,minutes,codes", [(30, 45, []), (30, 20, ["CUTOFF_WINDOW"]), (None, 45, ["CUTOFF_WINDOW"])])
def test_cutoff_window_reads_from_account_config(cutoff, minutes, codes):
    svc = service() if cutoff is None else service(cutoff_minutes=cutoff)
    if codes:
        with pytest.raises(Rejected) as e:
            svc.submit("acct-1", "venue-1", in_minutes(minutes), 2)
        assert e.value.codes == codes
    else:
        assert svc.submit("acct-1", "venue-1", in_minutes(minutes), 2).party_size == 2


def test_slot_exactly_at_window_edge_is_accepted():
    assert service().submit("acct-1", "venue-1", in_minutes(120), 2).party_size == 2


def test_cutoff_and_party_size_surface_both_codes():
    with pytest.raises(Rejected) as e:
        service().submit("acct-1", "venue-1", in_minutes(30), 13)
    assert e.value.codes == ["PARTY_TOO_LARGE", "CUTOFF_WINDOW"]
