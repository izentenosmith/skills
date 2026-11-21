"""Booking constraint rules. Each rule returns a violation code or None."""

from datetime import datetime, timedelta

MAX_PARTY_SIZE = 12
DEFAULT_CUTOFF_MINUTES = 120

clock = datetime.now


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


def _parse_window(value):
    text = value.strip().lower()
    if text.isdigit():
        return int(text)
    if text.endswith("min") and text[:-3].isdigit():
        return int(text[:-3])
    if text.endswith("m") and text[:-1].isdigit():
        return int(text[:-1])
    if text.endswith("h") and text[:-1].isdigit():
        return int(text[:-1]) * 60
    if "h" in text and text.endswith("min"):
        hours = text.split("h")[0]
        minutes = text.split("h")[1][:-3]
        if hours.isdigit() and minutes.isdigit():
            return int(hours) * 60 + int(minutes)
    if "h" in text and text.endswith("m"):
        hours = text.split("h")[0]
        minutes = text.split("h")[1][:-1]
        if hours.isdigit() and minutes.isdigit():
            return int(hours) * 60 + int(minutes)
    return DEFAULT_CUTOFF_MINUTES


def check_cutoff(booking, config):
    # get the window length for this account
    window = config.get("cutoff_minutes")
    # no window configured means the default
    if window is None:
        window = DEFAULT_CUTOFF_MINUTES
    # older accounts store it as text
    if isinstance(window, str):
        window = _parse_window(window)
    # how long until the slot starts
    now = clock()
    until_slot = booking.slot - now
    # the boundary is exclusive: a slot exactly at the edge is accepted
    if until_slot < timedelta(minutes=window):
        return "CUTOFF_WINDOW"
    return None


ACTIVE_RULES = [check_party_size, check_venue_open, check_cutoff]


def validate(booking, config):
    """Run every active rule, returning all violation codes."""
    return [code for rule in ACTIVE_RULES if (code := rule(booking, config)) is not None]
