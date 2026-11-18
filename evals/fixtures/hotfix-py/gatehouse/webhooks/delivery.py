"""Which tokens are sent a webhook when an event fires."""


def wants(token, event):
    """Whether this token's holder subscribed to `event` and can be reached."""
    if not token.webhook_url:
        return False
    subscribed = token.scopes.split(",")
    return f"webhooks:{event}" in subscribed


def recipients(tokens, event):
    return [t.webhook_url for t in tokens if wants(t, event)]
