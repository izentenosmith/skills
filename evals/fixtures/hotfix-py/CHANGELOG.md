# Changelog

## Unreleased

## 2.4.0 — 2026-10-06
- Admin console: a new token's scopes are stored separated by `", "`, so the token list reads cleanly.
- Webhooks: `export.finished` event.

## 2.3.1 — 2026-09-11
- Reports: `rows` is always a list, also when the report is empty.

## 2.3.0 — 2026-08-27
- Exports endpoint (`POST /exports`), behind the `exports:run` scope.
