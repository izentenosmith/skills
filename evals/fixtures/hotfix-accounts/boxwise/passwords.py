"""Password hashing (PBKDF2-SHA256)."""
import hashlib
import hmac
import os

ITERATIONS = 20_000


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    _, iterations, salt, digest = stored.split("$")
    again = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(again.hex(), digest)
