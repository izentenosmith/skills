# Design Patterns — Controls per Domain, and the Default for Each Trade-off

> The patterns Design mode chooses between, each with when it fits, what it costs, and **the
> default**. Cite the principle (A-N, [`theory.md`](theory.md)) when you pick one; say why when you
> deviate. Patterns are stated stack-neutrally, with the mechanism per stack where it differs.
>
> The design rule behind every section: **put the control in one place that every path goes
> through, and make the safe behaviour the default** — so the next developer gets it right without
> knowing it exists (SE §3.2.5.3, p.126; SE §27.6 — secure-by-construction APIs).

---

## §1 Queries and commands (A2)

| Need | Pattern | Default |
|---|---|---|
| Values in SQL | Parameterised statements or an ORM's bound parameters | **Always.** No string building with request data, ever |
| Identifiers (table, column, sort, direction) | Map an input token to a constant from an allow-list | `{"name": "u.name", "created": "u.created_at"}[sort] ?? "u.id"` |
| Dynamic filters | Query builder with bound values; never `raw` with interpolation | The ORM's builder |
| Stored procedures | Typed parameters; no dynamic SQL inside built from parameters (ONET ch1, pp.24–25) | Only where they buy a narrower grant |
| Shell commands | Avoid; otherwise argument arrays, no shell, allow-listed arguments | Library call instead of a process |
| Database account | Least privilege per application role; no owner/`sa`/`root` for the app (ONET ch1, pp.28–31) | One read/write account per service, DDL in a separate migration account |

## §2 Output encoding by context (A3)

| Context | Encoder | Default |
|---|---|---|
| HTML body | HTML entity encoding | The template engine's autoescape (Razor `@`, JSP `<c:out>`, EJS `<%=`, Jinja/Django autoescape, Blade `{{ }}`, ERB `<%= %>` with Rails escaping, Go `html/template`) |
| HTML attribute | Attribute encoding, always quoted | Autoescaping engine; never unquoted attributes |
| JavaScript | JS string encoding, or better: data in a JSON `<script type="application/json">` block read with `JSON.parse` | Never interpolate into script |
| URL | Percent-encode the component; allow-list the scheme (`https`, `mailto`) | Reject `javascript:` and `data:` |
| CSS | Avoid user data in CSS | Classes from an allow-list |
| User-supplied rich text | Sanitiser library with an allow-list policy (DOMPurify, OWASP Java HTML Sanitizer, Bleach successor/`nh3`, HtmlSanitizer, Loofah) | Markdown rendered then sanitised |
| DOM updates | `textContent`, `setAttribute`, framework bindings | No `innerHTML` with data (LWD 034.4, pp.277–279) |

## §3 Input contracts (A1, A4, A5)

- **One schema per boundary** (JSON Schema, Pydantic, Bean Validation, FluentValidation, zod/joi):
  types, lengths, formats, enums; unknown fields rejected; size limits on bodies and uploads.
- **Parsers**: XML with DTDs off; JSON/YAML with safe loaders; no native object deserialisation of
  untrusted input — data-only formats with schemas.
- **Outbound requests**: destination allow-list; resolve DNS once and reject private, loopback,
  link-local and metadata ranges; no redirects followed to new hosts; dedicated egress for webhooks.
- **Files**: store outside the web root (object storage), generated names, content type sniffed
  server-side, size-capped, served with `Content-Disposition: attachment` and `nosniff`.
- **Redirects**: relative paths only, or IDs mapped server-side to destinations (ONET ch10,
  pp.242–244).

## §4 Authentication (A6, A8)

| Decision | Default |
|---|---|
| Who authenticates | The framework's identity component or an external IdP (OIDC); never a custom scheme |
| Password hash | **Argon2id** (memory ≥ 19 MiB, iterations ≥ 2, parallelism 1) · or scrypt (N=2^17, r=8, p=1) · or bcrypt (cost ≥ 10, mind the 72-byte limit) · or PBKDF2-HMAC-SHA256 (≥ 600,000 iterations) — per-user random salt; re-hash on login when parameters rise |
| Password policy | Minimum 12 (8 with MFA), maximum ≥ 64, breached-password screening, paste allowed, no composition rules, no periodic expiry — change on compromise (SE §3.4.4, pp.145–147) |
| MFA | TOTP or WebAuthn/passkeys; WebAuthn required for admins; SMS only as a fallback for low-risk accounts |
| Guessing | Per-account and per-IP progressive delay and rate limits; CAPTCHA or step-up after a threshold; no hard lockout an attacker can trigger (SE §3.4.6, p.152) |
| Responses | The same message and timing for "no such user" and "wrong password" (A16) |

**Reset flow** (ONET ch3, pp.71–72, minus the secret questions):

1. User submits an identifier; respond identically whether or not it exists.
2. Generate a CSPRNG token (≥ 128 bits); store only its hash with a short expiry (≤ 1 hour) and the
   account ID.
3. E-mail a link carrying the token; never a password.
4. On use: verify hash and expiry, require a new password under policy (and MFA if enrolled),
   invalidate the token and all existing sessions, **don't auto-login**.
5. Notify the account out-of-band that the password changed (SE §3.4.12, p.160).

## §5 Sessions and tokens (A7)

**Session cookie baseline:**

```
Set-Cookie: __Host-session=<opaque, ≥128-bit CSPRNG>; Path=/; Secure; HttpOnly; SameSite=Lax
```

- `__Host-` prefix pins it to the origin; `SameSite=Lax` by default, `Strict` for admin apps.
- Regenerate at login, at privilege change and after password reset; destroy at logout server-side.
- Idle timeout 15–30 min for sensitive apps, absolute 8–12 h; "remember me" is a separate,
  revocable, hashed long-lived token, never stored credentials (ONET ch3, pp.68–69, 72–73).

| Choice | When | Default |
|---|---|---|
| Server-side session (opaque cookie) | Browser apps on one site | **Default for browser apps** — revocable, small, no secrets client-side |
| Signed token (JWT) | Service-to-service, or APIs called by many clients | Short-lived (≤ 15 min) access tokens, rotating refresh tokens with reuse detection; validate signature with a pinned algorithm, `exp`, `nbf`, `iss`, `aud`; no secrets in claims |
| OAuth / OIDC | Delegation and federated login | Authorization code + PKCE; access tokens are for APIs, ID tokens for identity — never treat an access token as proof of who the user is (SE §4.7.4, pp.187–188) |

## §6 Authorisation (A9–A13)

| Pattern | What it is | Default |
|---|---|---|
| **Central policy layer** | Every request passes one middleware/filter/guard that authenticates and evaluates a policy; handlers declare the permission they need | **Always.** Deny when a route declares nothing — new endpoints fail closed |
| **Ownership in the query** | The data query itself carries the owner or tenant predicate: `UPDATE … WHERE id = :id AND owner_id = :current_user`; zero rows → 404 (LWD 035.3, pp.348–350) | **Default for object access** — it can't be forgotten in a later code path |
| Repository scoping | Repositories constructed per request with the caller's tenant, exposing no unscoped queries | For multi-tenant systems, in addition to the above |
| Indirect references | Per-session maps from opaque IDs to internal keys (ONET ch4, pp.86–88) | A second layer for sensitive objects; never the only one |
| Non-guessable IDs | UUIDv4/ULID instead of sequences (ONET ch4, pp.88–89) | Good hygiene; not a control |
| RBAC → ABAC/ReBAC | Roles for functions; attributes or relationships for objects (SE §6.2, pp.256–261) | RBAC for coarse permissions plus ownership predicates; a policy engine (OPA, Cedar, Casbin, framework policies) when rules outgrow code |
| Separation of duty | Two principals for irreversible or high-value actions (SE §12.2.4, pp.453–455) | For payouts, role grants, data exports |

**CSRF and cross-origin** (A12):

| Mechanism | When | Default |
|---|---|---|
| Synchroniser token in forms and a header for fetch/XHR (ONET ch5, pp.104–106) | Any cookie-authenticated state change | **Framework anti-forgery, on globally** |
| `SameSite=Lax`/`Strict` cookies | Every session cookie | Always, as a second layer — not a replacement where old browsers or same-site subdomains matter |
| Origin/`Sec-Fetch-Site` check | APIs called from your own front end | Reject cross-site state-changing requests |
| Bearer tokens in a header | Non-browser clients | Not vulnerable to CSRF; still check CORS |
| CORS | Cross-origin browser clients | Explicit origin allow-list; `credentials` only with named origins; never reflect `Origin` |
| Framing | All HTML | `Content-Security-Policy: frame-ancestors 'none'` (or `'self'`) |

**Request binding:** DTOs/view models with the fields a caller may set; never bind entities
directly. **Business invariants:** transactions or conditional updates (`UPDATE … WHERE balance >= :amount`),
idempotency keys on payment-like operations, server-derived prices (A13).

## §7 Crypto, randomness and secrets (A14–A17)

| Need | Default |
|---|---|
| Symmetric encryption | AES-256-GCM or ChaCha20-Poly1305 via a high-level library (libsodium/`secretbox`, Tink, `cryptography` Fernet/AESGCM, .NET `AesGcm`, Go `crypto/cipher` GCM); random 96-bit nonce per message, never reused |
| Integrity of a message | HMAC-SHA-256 with a dedicated key; constant-time verification |
| Signatures | Ed25519, or ECDSA P-256 / RSA-PSS ≥ 3072 |
| Random values | The OS CSPRNG (`RandomNumberGenerator`, `SecureRandom`, `crypto.randomBytes`/`randomUUID`, `secrets`, `random_bytes`, `crypto/rand`, `SecureRandom`) |
| Comparison of secrets | Constant-time compare (see the per-stack list in [`detection-signals.md`](detection-signals.md)) |
| Key storage | A key management service or HSM; envelope encryption for data keys; keys per purpose and per environment |
| Secrets | A secrets store (cloud secrets manager, Vault/OpenBao, Kubernetes secrets with external encryption) read at runtime by a workload identity; nothing in VCS, images or CI variables visible to forks |
| TLS clients | Platform defaults with verification on; pin only with a rotation plan |

## §8 Configuration, errors and headers (A18–A20)

- **Per-environment config** in VCS without secrets; production values reviewed; the same keys in
  every environment so the same deploy works everywhere.
- **Errors**: one generic error page/body with a correlation ID; details to logs (ONET ch6,
  pp.122–124).
- **Fail closed**: an exception inside an authorisation, validation or signature check denies.

**Security headers baseline:**

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-<per-request>'; object-src 'none';
                         base-uri 'none'; frame-ancestors 'none'; form-action 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store          (on authenticated responses)
```

Remove `X-Powered-By` and version banners. Start CSP in report-only mode on an existing app, then
enforce.

## §9 Dependency policy (A21)

| Rule | Default |
|---|---|
| Lock and pin | Lockfile committed; exact versions in lockfiles; hashes where supported |
| Update | Automated update PRs weekly; security updates as they appear; tests gate the merge |
| Scan | SCA in CI on every PR and nightly; **block** on known-exploited or critical-reachable; ticket everything else with an SLA by severity |
| Adopt | Maintained (recent releases, more than one maintainer), widely used, licence on the allow-list, no install scripts from unknown publishers (LOS 054.3, p.191) |
| Runtime | Inside vendor support; 0.x libraries only behind an abstraction you can replace |
| Integrity | SRI on CDN assets; checksums on downloads; registry scoped to the official source |
| SBOM | SPDX or CycloneDX produced per release and stored with the artefact (LOS 054.3, pp.189–190) |

## §10 Licence policy (A22)

Decide by **how the product ships** — internal only, distributed binary/image/device, or hosted
service — because that is what triggers obligations (LOS 052.1, p.67; LOS 054.3, p.185).

| Licence family | Internal use | Distributed | Hosted (SaaS) |
|---|---|---|---|
| Permissive (MIT, BSD-2/3, Apache-2.0, ISC) | Allowed | Allowed — keep copyright notices and licence texts; Apache-2.0: NOTICE file, mark modified files | Allowed |
| Weak copyleft (LGPL, MPL) | Allowed | Allowed with conditions — LGPL: keep the library replaceable (dynamic linking); MPL: modified MPL files stay open | Allowed |
| Strong copyleft (GPL) | Allowed | **Decision required** — derivative work must be GPL with source offered | Allowed (no network clause) |
| Network copyleft (AGPL) | Allowed | **Decision required** | **Decision required** — network use triggers the source obligation |
| Source-available (SSPL, BUSL, Elastic) | Read the terms | Read the terms | Usually restricted — **decision required** |
| No licence | **Not allowed** — all rights reserved (LOS 052.1, p.65) | Not allowed | Not allowed |

**Compatibility as LOS presents it** (052.3, pp.97–100; 052.1, p.69 — compatibility is directional:
permissive code can flow into copyleft projects, not always the reverse):

| Inbound | Compatible with | Not compatible |
|---|---|---|
| MIT, BSD-2-Clause, BSD-3-Clause | GPL-2.0 and 3.0, LGPL-2.x and 3.0, MPL | — |
| Apache-2.0 | GPL-3.0, LGPL-3.0, MPL-2.0 | GPL-2.0(-only), LGPL-2.x, MPL-1.1 (patent terms) |
| GPL-3.0 / AGPL-3.0 | each other | combining other copyleft licences needs case-by-case review |

Record the elected licence for dual-licensed components; never strip notices; re-check on every
upgrade, since projects relicense (LOS 054.3, p.187).

## §11 Security event catalogue (A23, A24)

| Event | Fields | Alert when |
|---|---|---|
| Login success / failure | actor (or attempted identifier, never the password), source IP, user agent, MFA used, outcome | Failure bursts per account or per source; success after many failures |
| Logout, session revoked | actor, session ID hash | — |
| Password / MFA change, reset requested and completed | actor, channel | Reset completed from a new device/location |
| Access denied (authz) | actor, resource, permission | Bursts per actor (enumeration) |
| Role or permission change | actor, target, before → after | Every privilege grant |
| Admin action, data export, impersonation | actor, target, scope | Always (to an owned channel) |
| Validation failure on security-relevant input | endpoint, rule, source | Bursts per source |
| Secret or key use (decrypt, sign) on sensitive paths | actor/service, key ID | Unusual volume |

**Never log:** passwords (including the username field of failed logins when it looks like a
password), session IDs, tokens, keys, full card numbers, unnecessary personal data. Encode newlines
and control characters; prefer structured (JSON) logs. Ship off-host to a store the app can append
to but not rewrite (SE §6.2.3, p.259).

## §12 The browser trust boundary (A25–A39)

### Header contract per route class

Write one table per service and test it (a table-driven test over one route of each class):

| Header | HTML page | JSON API | User file download | Static asset |
|---|---|---|---|---|
| `Content-Type` | `text/html; charset=utf-8` | `application/json; charset=utf-8` | the real type, server-chosen | the real type |
| `X-Content-Type-Options` | `nosniff` | `nosniff` | `nosniff` | `nosniff` |
| `Content-Disposition` | — | — | `attachment; filename="<server-chosen>"` | — |
| `Cache-Control` | `no-store` when authenticated | `no-store` when authenticated | `no-store` when private | long `max-age`, immutable, fingerprinted names |
| `Content-Security-Policy` | nonce baseline (§8) incl. `frame-ancestors 'none'` (or named parents) | `default-src 'none'; frame-ancestors 'none'` | `default-src 'none'; sandbox` | — |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (preload once every subdomain is HTTPS) | same | same | same |
| `Referrer-Policy` | `strict-origin-when-cross-origin` (or `no-referrer` on pages with tokens in URLs) | same | same | same |

Default: **nonce-based CSP with `'strict-dynamic'`**, rolled out report-only first; host allow-lists
are bypassable (TW ch16, p.267). `X-Frame-Options: DENY` only as a fallback for old clients; don't
send `X-XSS-Protection` except as `0`.

### Cookie baseline

```
Set-Cookie: __Host-session=<opaque>; Path=/; Secure; HttpOnly; SameSite=Lax
```

`__Host-` forces host-only, `Secure`, `Path=/` — so a sibling subdomain can't overwrite it (A31). Use
`SameSite=Strict` for admin consoles. No `Domain` attribute on anything authenticating. CSRF tokens
are bound to the session (synchroniser token or an HMAC of the session ID), not double-submitted.

### The origin plan

Decide at design time: which host names exist; which one serves user content (a separate registrable
domain — `usercontent.example-cdn.net`, not `files.example.com` — so cookies don't reach it); which
subdomains run third-party or less-trusted code; who owns each DNS record and how it's retired when the
service behind it goes away (A26, A31, A34).

### Serving user files

Store in an object store or a non-executable directory outside the web root, under a generated key;
record the declared type but re-detect it from content (and re-encode images); serve with
`Content-Disposition: attachment`, the real type, `nosniff`, a server-chosen name, and a short-lived
signed URL on the sandbox origin (A5, A26).

### URL allow-list

1. Parse with the platform's standard URL parser (WHATWG URL in browsers and Node, `urllib.parse`
   plus normalisation, `java.net.URI`, `System.Uri`, `net/url`) and resolve relative URLs against a
   configured base.
2. Allow-list the scheme (`https`, and `http` only where required).
3. Convert the host to Punycode and compare it exactly, or at a dot boundary from the right
   (`host == "example.com" || host.endsWith(".example.com")`).
4. Use the parsed, re-serialised URL — never the original string — for the redirect or fetch.
5. For server-side fetches, also resolve the host and refuse private, loopback, link-local and
   metadata ranges at connect time (A5).

Default for redirects: **indirect references** (a key mapped to a destination) or same-origin
relative paths only.

### Cross-origin channels

- **CORS**: a static allow-list of exact origins; echo the origin only if it's in the list; add
  `Vary: Origin`; credentials only for listed origins; short preflight `Max-Age` (A30).
- **`postMessage`**: send with the exact target origin; receive with `event.origin === <constant>`
  and a schema check on `event.data` before use (A29).
- **Frames**: `frame-ancestors` per page; untrusted embeds in `sandbox` with the fewest tokens
  needed, never `allow-scripts` with `allow-same-origin` (A32).
- **Third-party scripts**: self-host where possible; otherwise `integrity` + `crossorigin`, an
  inventory with an owner per script, and ads in sandboxed frames (A34).

### Bounds

Body size, header size, upload size, request and read timeouts at the edge and in the app; archive
extraction with total-size, ratio and path checks; XML parsers with DTDs off; page sizes capped (A39).

## §13 APIs (A40–A43)

### Inventory and versions

- **Generate, then diff.** The spec (OpenAPI, GraphQL SDL) is generated from code or validated
  against it in CI; a route missing from the spec fails the build (shadow API gate).
- **Version-retirement policy.** Each version has an owner and a sunset date; at sunset its routes
  answer `410 Gone`; a CI check (a request per retired version against the test environment, or a
  route-table assertion) keeps them gone. A deprecated version keeps every current control until it's
  retired (A40).
- **Environments.** Test, beta and UAT surfaces are never on production hosts or in the production
  spec.

### Properties in and out

- **Response DTOs per role** (or serialiser field lists, GraphQL field-level authorisation); never
  serialise the stored object. In the schema, mark server-owned fields `readOnly` (A41).
- **Request DTOs** with an explicit list of writable fields, `additionalProperties: false`, and
  server-side validation of every value (ranges, ownership of referenced IDs).
- Default: **separate read and write schemas** for any resource with privileged or server-owned
  fields.

### Consumption limits

| Limit | Keyed on | Applies to |
|---|---|---|
| Rate (per minute/hour) | authenticated principal, and target account for login/OTP/reset | the normalised route template, across versions and aliases |
| Size | request | body, arrays, strings, uploads |
| Cost | principal | GraphQL depth and complexity, batch counts, expensive searches and exports |
| Quota | tenant or plan | billable operations |

Never key on `X-Forwarded-For` or other client-settable headers unless a trusted proxy sets them and
the app reads only that proxy's value. Return `429` with `Retry-After` (A42).

### Discovery artefacts

Documentation and interactive consoles are built for development and internal use; production serves
them only behind authentication, or not at all; GraphQL introspection off in production (A43).

### Spec linting in CI

Lint the spec on every change (Spectral, `vacuum` or equivalent) with the rules in
[detection-signals.md](detection-signals.md) — every operation has `security`, bodies are closed,
lengths and maxima set, `401/403/429` defined, no `http://` servers. The pipeline mechanics belong
to `pipelines`.

### Authorisation matrix as tests

The matrix from `controls.md` becomes one parametrised acceptance test per protected operation:
anonymous, owner, another user, another tenant, lower role, admin — each asserting the exact
outcome, with the A-B-A check for object-level operations (HAPI ch10, pp.253–256). A row missing
from the test is an untested permission.
