def ok(body):
    return 200, body


def forbidden(scope):
    return 403, {"error": "missing_scope", "scope": scope}
