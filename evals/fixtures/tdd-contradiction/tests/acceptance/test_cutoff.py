"""Acceptance tests for the cancellation cutoff (.workflow/brief.md), through BookingService.submit only."""
from datetime import datetime, timedelta

import pytest

from reservations.api import BookingService, Rejected
from tests.test_booking import FakeConfig, FakeStore

# Every hour open, so the opening-hours rule decides a cutoff test only where the test closes the venue.
OPEN = {"opens_at": 0, "closes_at": 24}
CLOSED = {"opens_at": 0, "closes_at": 0}


def service(**cfg):
    store = FakeStore()
    return BookingService(store, FakeConfig({**OPEN, **cfg})), store


def in_minutes(m, seconds=0):
    return datetime.now() + timedelta(minutes=m, seconds=seconds)


def test_booking_inside_cutoff_window_is_rejected_with_cutoff_window():
    svc, store = service()
    with pytest.raises(Rejected) as e:
        svc.submit("acct-1", "venue-1", in_minutes(30), 2)
    assert e.value.codes == ["CUTOFF_WINDOW"]
    assert store.saved == []


def test_booking_outside_window_is_accepted_and_persisted():
    svc, store = service()
    with pytest.raises(Rejected):
        svc.submit("acct-1", "venue-1", in_minutes(119), 2)
    booking = svc.submit("acct-1", "venue-1", in_minutes(121), 2)
    assert store.saved == [booking]


def test_window_length_reads_from_account_config():
    longer, _ = service(cutoff_minutes=240)
    with pytest.raises(Rejected) as e:
        longer.submit("acct-1", "venue-1", in_minutes(180), 2)
    assert e.value.codes == ["CUTOFF_WINDOW"]
    shorter, store = service(cutoff_minutes=60)
    booking = shorter.submit("acct-1", "venue-1", in_minutes(90), 2)
    assert store.saved == [booking]


def test_slot_at_window_edge_is_accepted():
    # The call itself takes a moment, so the slot is built one second past the edge.
    svc, store = service()
    with pytest.raises(Rejected):
        svc.submit("acct-1", "venue-1", in_minutes(119), 2)
    booking = svc.submit("acct-1", "venue-1", in_minutes(120, seconds=1), 2)
    assert store.saved == [booking]


def test_cutoff_and_party_size_violations_surface_both_codes():
    svc, store = service()
    with pytest.raises(Rejected) as e:
        svc.submit("acct-1", "venue-1", in_minutes(30), 13)
    assert sorted(e.value.codes) == ["CUTOFF_WINDOW", "PARTY_TOO_LARGE"]
    assert store.saved == []


def test_cutoff_is_reported_alone():
    svc, store = service(**CLOSED)
    with pytest.raises(Rejected) as e:
        svc.submit("acct-1", "venue-1", in_minutes(30), 13)
    assert e.value.codes == ["CUTOFF_WINDOW"]
    assert store.saved == []
