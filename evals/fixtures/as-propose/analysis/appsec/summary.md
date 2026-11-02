# billdesk-api — Application security review summary
> Endpoints: 13 (11 in code under /auth, /api/v2, /api/v1 and /docs; 7 operations in the spec) · stack Node 20 / Express 4.19 / Postgres · rubric v1.0 · source as of `a41c9e2`.
> Tools: `npm audit` (1 high), `gitleaks` (1 finding). Semgrep not available.

## Scores
| input | authentication | access | crypto | configuration | dependencies | logging | browser | api | **Service** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.0 | 2.0 | 2.0 | 2.0 | 6.0 | 6.0 | 6.0 | 6.0 | 2.0 | **2.0** (uncapped 4.6) |

Arithmetic: e.g. access — 7 criteria, 4 pts of 14 → base 2.9; open Critical AS-ACC-01 → cap 2.0. Service mean weighted by objects = 4.6 uncapped; Critical cap → 2.0.

## Severity tally
Critical 6 · High 5 · Medium 2 · Low 0. Needs-data 🔬 2.

## Endpoint inventory (excerpt)
| Route | AuthN | AuthZ | Sinks | State change | Cookie-auth |
|---|---|---|---|---|---|
| GET /api/v2/invoices/search | session | tenant in SQL text | SQL (concatenated) | no | yes |
| GET /api/v2/invoices/:id | session | **none** | SQL | no | yes |
| PATCH /api/v2/users/me | session | self only, all fields | SQL update incl. `role` | yes | yes, no CSRF |
| GET /api/v1/invoices, /api/v1/invoices/:id | **none** | **none** | SQL | no | — |
| POST /auth/login | — | — | redirect (`next`), log | yes | sets cookie |
| GET /docs | none | none | — | no | — |

Reconciliation: `/api/v1/*` and `/docs` are in code, not in `openapi.yaml` (shadow/zombie).

## Top findings (worst first)
| ID | Object | Anti-pattern | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| AS-CRY-01 | `.env` | Committed payment-provider secret key (value not reproduced) | ✅ | A17 | Critical | `.env:4` |
| AS-INP-01 | invoice search | SQL built by string interpolation | ✅ | A1 | Critical | `src/routes/invoices.js:11` |
| AS-ACC-01 | GET /api/v2/invoices/:id | No tenant/ownership predicate (IDOR) | ✅ | A10 | Critical | `src/routes/invoices.js:23` |
| AS-API-01 | /api/v1 router | Zombie API: unauthenticated, not in the spec | ✅ | A40, A9 | Critical | `src/app.js:33` |
| AS-ACC-02 | PATCH /api/v2/users/me | Mass assignment of `role` | ✅ | A12, A41 | Critical | `src/routes/users.js:24` |
| AS-AUT-01 | password storage | Unsalted MD5 | ✅ | A8 | Critical | `src/auth.js:5` |
| AS-AUT-02 | session cookie | Hard-coded secret; not Secure/HttpOnly/SameSite; no CSRF defence | ✅ | A7, A12, A31 | High | `src/app.js:21` |
| AS-BRW-01 | CORS | Reflected origin with credentials | ✅ | A30 | High | `src/app.js:18` |
| AS-DEP-01 | lodash 4.17.15 | Known prototype-pollution vulnerability | ✅ | A21 | High | `package.json` |
| AS-LOG-01 | login | Password written to logs | ✅ | A23, A24 | High | `src/routes/auth.js:9` |
| AS-INP-02 | login redirect | Open redirect via `next` | ✅ | A5, A28 | Medium | `src/routes/auth.js:13` |
| AS-API-02 | /docs | API docs exposed unconditionally | ✅ | A43 | Medium | `src/app.js:27` |

## Needs-data flags (not scored)
- 🔬 Whether the leaked key was ever live, and who has read the repo.
- 🔬 Whether any client still calls `/api/v1` (gateway logs not supplied).

## What is working well
Orders queries are parameterised and tenant-scoped; `helmet()` is on; the error handler is generic; the lockfile is committed.

## Systemic issues
No query layer (raw strings reach `db.query`); authorisation lives in each handler, so new routes start open; no inventory or sunset for API versions; entities are serialised and bound directly.

## Gate
- Score ≥ 9.0 — **fail** (2.0).
- No open Critical/High — **fail** (6 Critical, 5 High).
- Server-side authz and CSRF on every state-changing endpoint — **fail** (PATCH /users/me, v1).
- No unrotated secret in VCS — **fail** (AS-CRY-01).
- Slow salted KDF — **fail** (AS-AUT-01).
- No known-exploited reachable dependency — **fail** (AS-DEP-01).
- Inventory lists every version and docs endpoint — **fail** (AS-API-01, AS-API-02).
- 🔬 ≤ 10% — pass (2 of 13).
