"""Customer accounts: sign-up and lookup."""
from .emails import looks_like_email, normalize_email
from .passwords import hash_password


class InvalidEmail(ValueError):
    pass


class EmailTaken(Exception):
    pass


MIN_PASSWORD = 8


def find_by_email(db, email):
    """The account registered under `email`, or None."""
    return db.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?",
        (normalize_email(email),),
    ).fetchone()


def signup(db, email, password):
    """Create an account and return its id."""
    email = normalize_email(email)
    if not looks_like_email(email):
        raise InvalidEmail(email)
    if len(password) < MIN_PASSWORD:
        raise ValueError("password too short")
    if find_by_email(db, email) is not None:
        raise EmailTaken(email)
    cur = db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, hash_password(password)),
    )
    db.commit()
    return cur.lastrowid


def get_user(db, user_id):
    """The account's public fields, or None."""
    row = db.execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None
