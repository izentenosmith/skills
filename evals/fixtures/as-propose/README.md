# billdesk-api

Invoicing API for small businesses. Each business is a **tenant**; users belong to one tenant and
see that tenant's invoices and orders. The web app talks to `/api/v2`; the API description is in
`api/openapi.yaml`.

## Run

```bash
npm ci
cp .env .env.local   # adjust for your machine
npm start            # http://localhost:3000, API docs at /docs
```

Postgres connection and the payment-provider key come from `.env`.

## Notes

- `/api/v1` was the first version of the API. The old mobile app used it; it was replaced by v2 in
  2024.
- Sessions are cookie-based (express-session).
