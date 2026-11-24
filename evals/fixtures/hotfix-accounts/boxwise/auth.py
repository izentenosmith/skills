"""Signing in and resetting a password."""
import secrets
from datetime import datetime, timedelta, timezone

from .accounts import MIN_PASSWORD, find_by_email
from .passwords import hash_password, verify_password

RESET_TTL = timedelta(hours=1)


def login(db, email, password):
    """The account id when the email and password match an account, else None."""
    user = find_by_email(db, email)
    if user is None or not verify_password(password, user["password_hash"]):
        return None
    return user["id"]


def request_password_reset(db, email, now=None):
    """Issue a reset token for the account registered under `email`; None when there is none."""
    user = find_by_email(db, email)
    if user is None:
        return None
    now = now or datetime.now(timezone.utc)
    token = secrets.token_urlsafe(24)
    db.execute(
        "INSERT INTO reset_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user["id"], (now + RESET_TTL).isoformat()),
    )
    db.commit()
    return token


def reset_password(db, token, new_password, now=None):
    """Set a new password with a reset token. True when the token was valid."""
    now = now or datetime.now(timezone.utc)
    row = db.execute(
        "SELECT user_id, expires_at, used FROM reset_tokens WHERE token = ?", (token,)
    ).fetchone()
    if row is None or row["used"] or datetime.fromisoformat(row["expires_at"]) < now:
        return False
    if len(new_password) < MIN_PASSWORD:
        raise ValueError("password too short")
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
               (hash_password(new_password), row["user_id"]))
    db.execute("UPDATE reset_tokens SET used = 1 WHERE token = ?", (token,))
    db.commit()
    return True
