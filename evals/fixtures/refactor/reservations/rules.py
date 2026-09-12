"""Booking constraint rules. Each rule returns a violation code or None."""

from datetime import datetime, timedelta

MAX_PARTY_SIZE = 12
DEFAULT_CUTOFF_MINUTES = 120


def check_party_size(booking, config):
    limit = config.get("max_party_size")
    if limit is None:
        limit = MAX_PARTY_SIZE
    if not isinstance(limit, int):
        limit = int(limit)
    if booking.party_size > limit:
        return "PARTY_TOO_LARGE"
    return None


def check_venue_open(booking, config):
    opens = config.get("opens_at")
    if opens is None:
        opens = 11
    if not isinstance(opens, int):
        opens = int(opens)
    closes = config.get("closes_at")
    if closes is None:
        closes = 23
    if not isinstance(closes, int):
        closes = int(closes)
    if booking.slot.hour < opens:
        return "VENUE_CLOSED"
    if booking.slot.hour >= closes:
        return "VENUE_CLOSED"
    return None


def check_cutoff(booking, config):
    # read the cutoff window from config, falling back to the default
    cutoff = config.get("cutoff_minutes")
    if cutoff is None:
        cutoff = DEFAULT_CUTOFF_MINUTES
    if not isinstance(cutoff, int):
        cutoff = int(cutoff)
    # work out how far away the slot is from right now
    now = datetime.now()
    delta = booking.slot - now
    # the window is exclusive at the edge, so a slot exactly on the boundary is fine
    window = timedelta(minutes=cutoff)
    if delta < window:
        # too close to the slot start -- reject
        return "CUTOFF_WINDOW"
    return None


ACTIVE_RULES = [check_party_size, check_venue_open, check_cutoff]


def validate(booking, config):
    """Run every active rule, returning all violation codes."""
    return [code for rule in ACTIVE_RULES if (code := rule(booking, config)) is not None]
