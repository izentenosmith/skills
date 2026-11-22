"""The confirmation text a guest sees once a booking is accepted."""


def confirmation_text(booking):
    when = booking.slot.strftime("%A %d %B at %H:%M")
    return f"Table for {booking.party_size} guests on {when}."
