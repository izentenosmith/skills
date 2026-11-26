# tasklane-api

Project and task tracking for agencies. Each agency is a **tenant**; its users see that tenant's
projects, tasks and files. The web app (a separate repo) calls `/api`; the public API description is
in `api/openapi.yaml`.

## Run

```bash
npm ci
cp .env.example .env   # fill in DATABASE_URL, SESSION_SECRET, BILLING_WEBHOOK_SECRET
npm run migrate
npm start              # http://localhost:3000
npm test
```

## How requests are protected

- `/auth/*` signs users in and out; sessions are cookies backed by Postgres (`connect-pg-simple`).
- Everything under `/api` requires a session (`src/app.js`).
- Admin and support tooling lives under `/api/admin` and is limited to staff roles
  (`src/admin/router.js`).
- The billing provider calls `/hooks/billing` when a subscription changes; requests are signed with
  `BILLING_WEBHOOK_SECRET`.
- Every query is parameterised and scoped to the caller's tenant.

## Layout

| Path | What |
|---|---|
| `src/app.js` | the Express app: middleware and mounts |
| `src/routes/` | the `/api` routers, collected in `routes/index.js` |
| `src/admin/` | staff tooling |
| `src/webhooks/` | inbound webhooks |
| `src/reports/` | CSV exports |
| `migrations/` | schema |
