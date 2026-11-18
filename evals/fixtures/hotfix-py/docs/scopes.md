# Scopes

A token carries its scopes as one string, for example `reports:read,exports:run`.

- Scopes are separated by commas. **Whitespace around a scope is not significant**: `reports:read, exports:run`
  and `reports:read,exports:run` grant the same two scopes. Stored tokens carry both forms.
- Empty entries are ignored; an empty string grants nothing.
- Matching is exact and case-sensitive. There are no wildcards and no prefixes: `exports:run` does not grant
  `exports`, and `exports:runner` does not grant `exports:run`.
- An endpoint that needs a scope the token lacks answers `403` with
  `{"error": "missing_scope", "scope": "<the scope>"}`.

| Scope | Grants |
|---|---|
| `reports:read` | `GET /reports/<id>` |
| `exports:run` | `POST /exports` |
| `webhooks:<event>` | delivery of that event to the token's webhook URL |
