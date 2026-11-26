"""Outgoing mail. Production swaps OUTBOX for the SMTP relay at startup."""
OUTBOX = []


def send_reset_link(to, token):
    OUTBOX.append({"to": to, "subject": "Reset your Boxwise password",
                   "body": f"https://boxwise.example/reset?token={token}"})
