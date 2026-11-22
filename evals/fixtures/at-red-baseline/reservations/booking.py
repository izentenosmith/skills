"""The Booking aggregate."""

from dataclasses import dataclass
from datetime import datetime

from . import rules


@dataclass
class Booking:
    account_id: str
    venue_id: str
    slot: datetime
    party_size: int

    def validate(self, config):
        """Return the list of constraint violations for this booking."""
        return rules.validate(self, config)
