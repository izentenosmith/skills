"""Public entry point: the booking handler. Tests drive the service through here."""

from .booking import Booking


class Rejected(Exception):
    def __init__(self, codes):
        self.codes = codes
        super().__init__(",".join(codes))


class BookingService:
    def __init__(self, store, config_source):
        self._store = store
        self._config_source = config_source

    def submit(self, account_id, venue_id, slot, party_size):
        """Validate and persist a booking, or raise Rejected with the violation codes."""
        booking = Booking(account_id, venue_id, slot, party_size)
        config = self._config_source.for_account(account_id)
        violations = booking.validate(config)
        if violations:
            raise Rejected(violations)
        self._store.save(booking)
        return booking
