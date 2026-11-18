"""API tokens as the admin console issues and stores them."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    name: str
    scopes: str  # the stored scope string; grammar in docs/scopes.md
    webhook_url: str = ""


def issue(name, scopes, webhook_url=""):
    """A new token for `name` carrying the given list of scopes."""
    return Token(name=name, scopes=", ".join(scopes), webhook_url=webhook_url)
