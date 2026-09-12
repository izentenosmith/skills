"""Prior art: table-driven constraint tests, driven through the public handler."""
import pytest
from datetime import datetime, timedelta
from reservations.api import BookingService, Rejected


def slot(hour=19, days_out=30):
    """A slot `days_out` days from now at `hour`, well clear of any cutoff window."""
    return (datetime.now() + timedelta(days=days_out)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


class FakeStore:
    def __init__(self): self.saved = []
    def save(self, booking): self.saved.append(booking)


class FakeConfig:
    def __init__(self, cfg=None): self._cfg = cfg or {}
    def for_account(self, account_id): return self._cfg


@pytest.fixture
def service():
    return BookingService(FakeStore(), FakeConfig())


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
