"""Booking constraint rules. Each rule returns a violation code or None."""

from datetime import datetime, timedelta

MAX_PARTY_SIZE = 12


def check_party_size(booking, config):
    if booking.party_size > config.get("max_party_size", MAX_PARTY_SIZE):
        return "PARTY_TOO_LARGE"
    return None


def check_venue_open(booking, config):
    if booking.slot.hour < config.get("opens_at", 11):
        return "VENUE_CLOSED"
    if booking.slot.hour >= config.get("closes_at", 23):
        return "VENUE_CLOSED"
    return None


DEFAULT_CUTOFF_MINUTES = 120


def check_cutoff(booking, config):
    window = timedelta(minutes=DEFAULT_CUTOFF_MINUTES)
    if booking.slot - datetime.now() < window:
        return "CUTOFF_WINDOW"
    return None


ACTIVE_RULES = [check_party_size, check_venue_open, check_cutoff]


def validate(booking, config):
    """Run every active rule, returning all violation codes."""
    return [code for rule in ACTIVE_RULES if (code := rule(booking, config)) is not None]
