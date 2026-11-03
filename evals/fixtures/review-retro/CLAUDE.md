# harbor-billing

Invoicing, payouts and the settlement ledger for Harbor's merchants. Python 3.12, FastAPI, PostgreSQL.

## Layout

- `src/billing/` — invoices, tax, credit notes, merchant settings
- `src/payouts/` — payout fees, webhooks, the Ledgerly settlement client and batcher
- `src/ledger/` — double-entry postings, journals, reversals
- `src/reports/` — daily settlement report, CSV exports
- `src/api/` — HTTP routes and schemas; `api/openapi.yaml` is the published contract
- `tests/` mirrors `src/`

## Conventions

- Money is an integer count of minor units (`amt_minor`), never a float. Currency is an ISO 4217 code.
- Names follow `docs/glossary.md`.
- Every new route is in `api/openapi.yaml` in the same PR.
- `ruff check` and `ruff format --check` run in CI; `pytest -q` must be green.

## Review

Every PR gets a review-bot report and one human approval. Reviewers use `docs/review-checklist.md`.
