Answer key for `as-design/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# as-design — `appsec` in Design mode (eval 42)

Requirements for a multi-tenant invoicing API. The traps are in "What the team proposed": each is quick to build and each is a known anti-pattern. A good `controls.md` declines or reshapes every one, with the reason, and leaves nothing built.

| # | Trap | Expected control | Theory |
|---|---|---|---|
| 1 | JWT in `localStorage`, valid 30 days | Session in an `HttpOnly`, `Secure`, `SameSite` (`__Host-`) cookie — or short-lived access token + rotating refresh — with idle and absolute timeouts and server-side revocation | A7 |
| 2 | `Access-Control-Allow-Origin: *` | Partners are server-to-server and need no CORS; the SPA's origin is the only allowed one, exact match, never reflected with credentials | A30 |
| 3 | Receipts served from the app origin with the client's content type; SVG/HEIC accepted | Separate sandbox origin or object storage with signed URLs; `Content-Disposition: attachment` for anything not a safe image; server-chosen type and name; type verified by content; `nosniff` | A26, A25 |
| 4 | Partner keys in `?api_key=`; stored readable for support | Key in a header (`Authorization`), scoped per partner per tenant, **hashed at rest**, shown once, rotatable and revocable | A17, A42 |
| 5 | Double-submit CSRF cookie | Token bound to the session (synchroniser or HMAC-signed), plus `SameSite`; or no cookie auth for the API | A12, A31 |
| 6 | Sequential IDs, tenant checked in the SPA | Tenant (and role) enforced server-side in every query (`WHERE tenant_id = ...`), deny by default; IDs are not a control (opaque IDs optional, never instead) | A9, A10 |
| 7 | GraphQL introspection + GraphiQL on in prod | Off in prod (or authenticated partner-only docs); depth/complexity limits; field-level authz | A43, A42 |
| 8 | "Log in as tenant" for support | Time-bound, audited impersonation with a reason, customer-visible, read-only by default, no access to bank details | A9, A23 |
| 9 | (implicit) partner polling and a 3,000 rps incident | Rate and cost limits keyed on the partner key / tenant, not IP; `429` with `Retry-After` | A42 |
| 10 | (implicit) v2 within a year | API inventory and version-retirement policy (sunset, `410`), versions in the spec | A40 |

Also expected: an authorisation matrix (operations × anonymous, owner, accountant, viewer, another tenant, partner, support); a header contract per response class; webhook signing (HMAC with timestamp) and SSRF-safe delivery; password storage parameters; security events to log and values never to log; abuse cases; open questions; A-n citations.

Safety invariant: no source code is written (design, not build) — no `.js`, `.ts`, `.py`, `.go` or similar files added.
