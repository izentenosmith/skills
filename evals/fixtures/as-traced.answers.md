Answer key for `as-traced/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# as-traced — `appsec` in Review mode, outcome-graded (eval 77)

`tasklane-api`, a multi-tenant Node/Express/Postgres project tracker. Unlike `as-review` (eval 41), where a no-skill
baseline already scores 1.00 on capability, the files a reviewer opens first are **clean**: bcrypt at cost 12, a
rate-limited login with session regeneration, Secure/HttpOnly/SameSite cookies from a Postgres store, every query
parameterised, `loadProject` scoping every project route by tenant, an HMAC compared with `timingSafeEqual`, CSV
formula neutralisation. The defects are each visible only by reading one route's actual middleware chain or by
following one value through storage — what the skill's reconciled endpoint inventory and source-to-sink tracing
do, and what a sample-the-obvious-files review skips. Nothing is executed; the review is graded from what it
writes.

## Planted defects (capability: found at file:line ±3, with what is wrong said there)

| # | Defect | Where | Rubric / theory | Why a skim misses it |
|---|---|---|---|---|
| 1 | `GET /api/admin/tenants` (every tenant: name, plan, seats, billing email) and `GET /api/admin/tenants/:tenantId/users` (every user of any tenant) are declared **above** `router.use(requireRole('admin'))`. Express applies router-level middleware only to routes registered after it, so they run behind `requireAuth` alone: any signed-in tenant user reads every tenant. The comment says "support staff use these" — no role is checked at all. | `src/admin/router.js:8`, `:19`; guard at `:32` | access/api · A9, A11 · Critical | the file has a role guard, and the README says admin routes are "limited to staff roles"; the inventory's "where is authorisation checked" column, filled per route, shows none |
| 2 | The billing webhook verifies the signature only **if** `X-Billing-Signature` is present: `if (signature && !verifySignature(...))`. Omit the header and the body is trusted, so anyone sets any tenant's `plan` and `seats` (free upgrade to business, or downgrade a rival). The verifier itself is correct (HMAC-SHA256, timing-safe), and the tests cover good, tampered and short signatures — never a missing one. | `src/webhooks/billing.js:20` | authentication/api · A9, A18 · Critical | reads `verifySignature` and the green tests and moves on; the route is mounted before the session and absent from the spec |
| 3 | Second-order SQL injection. `PUT /api/me/preferences` stores `reportSort` as any string ≤ 120 chars — parameterised, safe at that point. `exportTasksCsv` reads it back from `users.preferences` and interpolates it into `ORDER BY ${sort}`. A boolean subquery in `ORDER BY` reads any table, across tenants (e.g. other users' `password_hash`). The spec gives `reportSort` an enum (`due_date, status, title`) the code never enforces. | sink `src/reports/export.js:9-13` (interpolation at `:13`); source `src/routes/me.js:21-31` (check at `:26`) | input · A1, A2 · Critical | the value comes from the database, "our own data"; the spec's enum reads like validation |
| 4 | `GET /api/projects/:projectId/files/:fileId` runs `loadProject` (tenant-checked) and then loads the file `WHERE id = $1` alone — the file is never bound to the project. File ids are `bigserial`, so a user enumerates every tenant's files through a project of their own. `DELETE` beside it binds `project_id`; the list route does too. | `src/routes/files.js:42` (route at `:39`) | access · A10 · Critical | the parent check is there; the route "looks scoped" |

## Decoys (capability: not raised as a defect)

| Decoy | Where | Why it is safe |
|---|---|---|
| `ORDER BY ${order} ${dir}` in the project list | `src/routes/projects.js:16-20` | `order` comes only from `SORTABLE.get(...)`, a `Map` of three fixed columns, with a constant fallback; `dir` is one of two constants. A template literal over an allow-list is not injection (the skill: "a concatenated query over a constant is not injection"). |
| `crypto.createHash('md5')` | `src/lib/etag.js:5` | builds a weak `ETag` for `If-None-Match`; no secret, no password, no integrity claim. Flagging it as weak crypto is a false positive. |

## Delta (what the skill instructs)

The endpoint inventory has rows for `/hooks/billing` and the `/api/admin` routes and reconciles code against
`api/openapi.yaml`, which lists neither (shadow routes, A40); the injection is traced from `me.js` to
`export.js`, and the spec's `reportSort` enum is named as unenforced; findings carry AS- ids, A-n theory,
confidence and file:line; scores show base and the 2.0 Critical cap; the gate fails condition by condition;
OWASP mapping; what works is recorded (bcrypt, `loadProject`, the sort allow-list, `timingSafeEqual`, CSV
neutralisation, rate-limited login); nothing in the fixture changes.

Not graded, but true and fine to report: no CSRF token on cookie-authenticated JSON state changes (SameSite=Lax
and JSON bodies blunt it); `POST /api/admin/users/:userId/disable` can disable another admin; uploads accept any
type (served as an attachment with `nosniff`); no audit log for the webhook's plan changes.
