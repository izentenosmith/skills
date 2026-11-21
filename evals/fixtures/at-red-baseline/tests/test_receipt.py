"""Confirmation text for accepted bookings."""
from datetime import datetime

from reservations.booking import Booking
from reservations.receipt import confirmation_text

FRIDAY_7PM = datetime(2026, 6, 5, 19, 0)


def test_confirmation_names_the_party_and_slot():
    booking = Booking("acct-1", "venue-1", FRIDAY_7PM, 4)
    assert confirmation_text(booking) == "Table for 4 guests on Friday 05 June at 19:00."


def test_confirmation_names_a_single_guest():
    booking = Booking("acct-1", "venue-1", FRIDAY_7PM, 1)
    assert confirmation_text(booking) == "Table for 1 guest on Friday 05 June at 19:00."
