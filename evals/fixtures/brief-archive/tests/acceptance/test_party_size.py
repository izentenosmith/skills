"""Acceptance tests for the per-account party-size limit, driven through the public handler."""
import pytest
from datetime import datetime, timedelta
from reservations.api import BookingService, Rejected


def slot(hour=19, days_out=30):
    return (datetime.now() + timedelta(days=days_out)).replace(hour=hour, minute=0, second=0, microsecond=0)


class FakeStore:
    def __init__(self): self.saved = []
    def save(self, booking): self.saved.append(booking)


class FakeConfig:
    def __init__(self, cfg=None): self._cfg = cfg or {}
    def for_account(self, account_id): return self._cfg


def test_party_over_the_limit_is_rejected_with_party_too_large():
    with pytest.raises(Rejected) as e:
        BookingService(FakeStore(), FakeConfig()).submit("acct-1", "venue-1", slot(), 13)
    assert e.value.codes == ["PARTY_TOO_LARGE"]


def test_party_at_the_limit_is_accepted_and_persisted():
    store = FakeStore()
    BookingService(store, FakeConfig()).submit("acct-1", "venue-1", slot(), 12)
    assert len(store.saved) == 1


def test_limit_reads_from_account_config():
    service = BookingService(FakeStore(), FakeConfig({"max_party_size": 6}))
    with pytest.raises(Rejected) as e:
        service.submit("acct-1", "venue-1", slot(), 7)
    assert e.value.codes == ["PARTY_TOO_LARGE"]


def test_party_size_and_opening_hours_surface_both_codes():
    with pytest.raises(Rejected) as e:
        BookingService(FakeStore(), FakeConfig()).submit("acct-1", "venue-1", slot(hour=3), 13)
    assert e.value.codes == ["PARTY_TOO_LARGE", "VENUE_CLOSED"]
