"""Email addresses as customers type them."""


def normalize_email(raw):
    """The form an address is stored and looked up in: surrounding whitespace dropped."""
    return raw.strip()


def looks_like_email(addr):
    local, sep, domain = addr.partition("@")
    return bool(sep and local and "." in domain.strip(".") and " " not in addr)
