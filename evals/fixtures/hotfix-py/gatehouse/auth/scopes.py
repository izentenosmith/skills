"""Scope checks for the API endpoints."""


class Forbidden(Exception):
    def __init__(self, scope):
        super().__init__(f"missing scope {scope}")
        self.scope = scope


def parse_scopes(raw):
    """The set of scopes in a token's scope string."""
    return frozenset(s for s in raw.split(",") if s)


def has_scope(raw, needed):
    return needed in parse_scopes(raw)


def require_scope(token, needed):
    if not has_scope(token.scopes, needed):
        raise Forbidden(needed)
