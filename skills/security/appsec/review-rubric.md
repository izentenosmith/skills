# Review Rubric — Nine Domains

> The criteria Review mode grades against. Each domain has 🟢 what good looks like, 🔴 the
> anti-patterns (**What / Why / Detect / Severity**), and the **Checklist** whose criteria are scored
> proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md). Find candidates with [`detection-signals.md`](detection-signals.md), then
> **trace each from source to sink** — a match is a candidate, not a finding.
>
> Severity below assumes the endpoint is reachable by an ordinary user or anonymously and touches
> internal or higher data. Lower one step for admin-only or internal-service reachability, and say
> you did.

---

## 1. input — data must stay data

In scope: sinks reached by untrusted data — queries, commands, templates and HTML outputs, parsers
and deserialisers, outbound requests, file paths, redirects.

### 🟢 Well done
- One query layer (ORM or builder) with bound parameters everywhere; identifiers from allow-lists
  (A2).
- A template engine that escapes by default; raw output rare, reviewed and sanitised (A3).
- Every boundary has a schema: type, length, format, allow-list; failures rejected (A1).
- Parsers configured safely (no DTDs/external entities, no native deserialisation of input) (A4).
- Outbound requests, file paths and redirects resolved from allow-lists or indirect IDs (A5).

### 🔴 Not well done

#### Injection into an interpreter
**What:** Untrusted data concatenated or interpolated into SQL, NoSQL queries, shell commands, LDAP
filters, XPath, template source or `eval`. **Why:** A2. **Detect:** sink grep per stack, then trace
the argument back to a request source. ✅ when traced; ⚠️ when the source is several layers away.
**Severity:** Critical; High when only admins reach it.

#### Unescaped output (XSS)
**What:** Request or stored data written to HTML, attributes, scripts or URLs without the context's
encoder; raw-output helpers; DOM sinks (`innerHTML`, `document.write`) fed by data; request data
echoed as `text/html`. **Why:** A3. **Detect:** raw-output grep per template engine; DOM sink grep;
reflected echo handlers. ✅ when traced. **Severity:** High; Critical when stored and rendered to
admins or when session cookies aren't `HttpOnly`.

#### Wrong encoder for the context
**What:** HTML-encoding used inside `<script>`, inside an `href`/`src`, inside CSS or an event handler.
**Why:** A3. **Detect:** read each raw-ish insertion's surrounding context. ✅. **Severity:** High.

#### Blacklist or client-only validation
**What:** Validation that strips "bad" characters, relies on JavaScript or HTML attributes, or relies
on type conversion for strings. **Why:** A1. **Detect:** sanitiser functions with deny-lists;
handlers with no server-side schema. ✅. **Severity:** Medium alone; it raises the severity of the
sink it fails to protect.

#### Unsafe parser or deserialiser
**What:** XML with DTD/external entities enabled; native deserialisation (`BinaryFormatter`,
`ObjectInputStream`, `pickle`, unsafe YAML, `unserialize`, `Marshal.load`) of request data; unbounded
body sizes. **Why:** A4. **Detect:** parser construction and deserialiser calls. ✅. **Severity:**
Critical for native deserialisation of input; High for XXE.

#### Server-side request forgery
**What:** The server fetches a URL derived from input without an allow-list and without blocking
internal and metadata ranges after DNS resolution. **Why:** A5. **Detect:** HTTP client calls with
request-derived URLs; webhook and "import from URL" features. ✅ when traced. **Severity:** High;
Critical on cloud hosts with reachable metadata credentials.

#### Path traversal and unsafe upload
**What:** File paths built from input without canonicalising and checking the base; uploads stored in
the web root, under client-supplied names, without type/size checks. **Why:** A5. **Detect:** file
API calls with request data; upload handlers; static-serving roots (`express.static('.')`). ✅.
**Severity:** High; Critical when an uploaded file can execute.

#### Open redirect
**What:** Redirect or forward targets taken from a parameter (`next`, `returnUrl`, `url`, `redirect`,
`continue`) without an allow-list or a local-URL check. **Why:** A5. **Detect:** redirect calls with
request data. ✅. **Severity:** Medium; High on login/logout and OAuth flows.

### Checklist
1. Query and command sinks that use parameters or argument arrays (no concatenation).
2. Identifiers that parameters can't carry (table, column, sort) resolved from an allow-list.
3. Output sinks encoded for their context by default.
4. Raw-HTML outputs sanitised by a vetted library.
5. Boundaries with a server-side schema (type, length, format).
6. Parsers configured safely; no native deserialisation of untrusted data.
7. Outbound requests restricted to allow-listed destinations.
8. File paths canonicalised and confined; uploads stored outside the web root with generated names.
9. Redirect targets allow-listed or local-only.

---

## 2. authentication — who is asking

In scope: authentication and session mechanisms, credential stores, recovery flows, token validators.

### 🟢 Well done
- The framework's identity component or an identity provider; no hand-rolled login (A6).
- Passwords hashed with Argon2id/scrypt/bcrypt/PBKDF2 at current cost; breached-password screening;
  MFA available and required for privileged roles (A8).
- Sessions server-issued, cookie-carried, rotated at login, idle- and absolute-timed, flagged
  `Secure; HttpOnly; SameSite` (A7).
- Recovery by single-use expiring link with uniform responses (A8, A16).
- Tokens validated by a library with pinned algorithms, issuer, audience and expiry (A7).

### 🔴 Not well done

#### Hand-rolled authentication
**What:** Custom password checks writing to the session; trust in a client-set cookie value or
presence; custom token parsing. **Why:** A6. **Detect:** session writes after a manual compare;
`req.cookies.*` used as identity. ✅. **Severity:** Critical when bypassable; High otherwise.

#### Weak password storage
**What:** Plaintext, reversible encryption, MD5/SHA-1/unsalted or single-pass SHA-2; low KDF cost;
retrievable passwords. **Why:** A8. **Detect:** hash calls in the credential path; hasher
configuration. ✅. **Severity:** Critical for plaintext/reversible; High for fast hashes.

#### Session identifier exposed or fixed
**What:** Session IDs in URLs; no regeneration at login; no invalidation at logout; cookie without
`Secure`/`HttpOnly`. **Why:** A7. **Detect:** session configuration; login handler; cookie options.
✅. **Severity:** High.

#### Unbounded sessions
**What:** No idle timeout, multi-day sliding expiry, "remember me" storing credentials, long-lived
refresh tokens without revocation. **Why:** A7. **Detect:** session and token lifetime config. ✅.
**Severity:** Medium; High for privileged apps.

#### Broken token validation
**What:** JWT `alg: none` or algorithm taken from the token; HS/RS confusion; no `exp`/`aud`/`iss`
checks; weak or shared HMAC secret; sensitive data in the payload; access tokens used as identity.
**Why:** A7. **Detect:** JWT library calls and options; verification code. ✅. **Severity:** Critical
for signature bypass; High otherwise.

#### Weak recovery
**What:** Security questions as the only factor; reset tokens that don't expire or can be reused;
passwords e-mailed; auto-login after reset; responses that reveal whether the account exists.
**Why:** A8, A16. **Detect:** reset flow handlers and templates. ✅. **Severity:** High.

#### Guessing unthrottled — or hard lockout
**What:** No rate limit or progressive delay on login, reset and MFA endpoints; or a hard lockout any
caller can trigger for any account. **Why:** A8. **Detect:** middleware on auth routes. ✅/⚠️ (a
gateway may throttle — 🔬 if unknown). **Severity:** Medium; High with account enumeration.

#### No MFA for privileged users
**What:** Admin or high-value accounts authenticate with a password only, or SMS only. **Why:** A8
(SE §4.6 — SMS second factors fall to SIM swap). **Detect:** auth configuration, IdP policy. ✅/🔬.
**Severity:** High for admin; Medium otherwise.

### Checklist
1. Authentication mechanisms provided by the framework or an IdP.
2. Credential stores using a slow salted KDF at current cost.
3. New passwords screened against a breached list; long passphrases allowed.
4. Sessions in cookies only, rotated at login, invalidated at logout.
5. Session cookies `Secure; HttpOnly; SameSite`.
6. Idle and absolute timeouts set.
7. Token validators pinning algorithm, issuer, audience and expiry.
8. Recovery by single-use expiring token with uniform responses.
9. Authentication endpoints throttled without enabling denial of service.
10. MFA required for privileged roles.

---

## 3. access — what the caller may do

In scope: endpoints and handlers — pages, APIs, RPCs, resolvers, webhooks, static and private file
routes.

### 🟢 Well done
- One authorisation layer every endpoint passes through, deny by default; new routes inherit it (A9).
- Ownership and tenant predicates inside the data query; zero rows → not found (A10).
- No decision depends on hidden fields, headers, IP or obscurity (A11).
- Every cookie-authenticated state change carries a CSRF defence; CORS allow-listed; request binding
  restricted to allowed fields (A12).
- Multi-step flows verify earlier steps; invariants enforced server-side, atomically (A13).

### 🔴 Not well done

#### Missing function-level authorisation
**What:** Routes reachable without authentication or without the required role; admin functions
hidden in the UI but open at the server; AJAX/API/file endpoints left out. **Why:** A9. **Detect:**
endpoint inventory vs middleware/attributes/decorators; replay without the session in an environment
the user owns. ✅. **Severity:** Critical for admin or data-changing functions.

#### Insecure direct object reference
**What:** Objects fetched, updated or deleted by a caller-supplied ID without an ownership or tenant
check; tenant ID taken from the request. **Why:** A10. **Detect:** data access by `id` alone in
handlers; repository calls without the user/tenant predicate. ✅. **Severity:** Critical.

#### Decisions on client-controlled signals
**What:** Authorisation by hidden field, `User-Agent`, `Referer`, `X-Forwarded-For`, `Accept`,
"secret" URLs or disabled buttons. **Why:** A11. **Detect:** reads of those values feeding a
branch. ✅. **Severity:** High; Critical when it gates data access.

#### Cross-site request forgery
**What:** Cookie-authenticated state-changing endpoints with no anti-forgery token and no `SameSite`
protection; state changes on GET. **Why:** A12. **Detect:** CSRF middleware disabled or exempted;
forms and fetches without tokens; GET routes that write. ✅. **Severity:** High.

#### Over-broad CORS
**What:** Reflected `Origin` or `*` with credentials; wildcard subdomain matching; `null` origin
allowed. **Why:** A12. **Detect:** CORS configuration. ✅. **Severity:** High with credentials;
Medium without.

#### Mass assignment
**What:** Whole request bodies bound to models, letting callers set `role`, `isAdmin`, `ownerId`,
`price`. **Why:** A12. **Detect:** model binding without allow-listed fields/DTOs. ✅. **Severity:**
High.

#### Confused deputy
**What:** A service uses its own broad credentials to act on a resource the caller names. **Why:**
A12, A5. **Detect:** privileged clients invoked with request-derived targets. ✅/⚠️. **Severity:**
High.

#### Race and workflow bypass
**What:** Check-then-act without atomicity (double redeem, overdraw); later workflow steps callable
directly; client-supplied prices and quantities trusted. **Why:** A13. **Detect:** read-modify-write
without transaction/conditional update; step endpoints that don't verify prior state. ⚠️ usually.
**Severity:** High where money or entitlements are involved.

### Checklist
1. Endpoints behind the central authorisation layer, deny by default.
2. Object accesses scoped by owner/tenant in the query.
3. No authorisation decision on client-controlled signals.
4. Cookie-authenticated state changes with a CSRF/same-site defence; no state change on GET.
5. CORS restricted to named origins; no credentials with wildcards.
6. Request binding restricted to allowed fields.
7. Privileged calls made with the caller's authority, not the service's.
8. State changes atomic; workflow steps verify prior state; prices and quantities server-derived.

---

## 4. crypto — keys, randomness, secrets

In scope: crypto uses (hashing, encryption, signing, random generation, TLS clients) and secrets.

### 🟢 Well done
- High-level, maintained libraries; AEAD; HMAC; current signature schemes (A14).
- CSPRNG for every token, salt, IV and nonce; nonces never reused; keys per purpose (A15).
- Constant-time comparisons; uniform errors (A16).
- Secrets read at runtime from a store; none in code, images or CI files (A17).

### 🔴 Not well done

#### Weak algorithm or mode
**What:** ECB; CBC without MAC; DES/3DES/RC4; MD5/SHA-1 for signatures, tokens or integrity;
`h(key||msg)` MACs; RSA without OAEP/PSS. **Why:** A14. **Detect:** cipher and hash construction
calls. ✅. **Severity:** High for sensitive data; Medium otherwise.

#### Home-made crypto
**What:** Custom encryption, token or signing schemes; XOR "encryption"; base64 treated as
protection. **Why:** A14. **Detect:** crypto helpers in the codebase not wrapping a library. ✅.
**Severity:** High.

#### Predictable randomness or reused nonces
**What:** Non-cryptographic RNGs for tokens or IDs; static IVs; counters reset on restart. **Why:**
A15. **Detect:** RNG calls in security paths; IV construction. ✅. **Severity:** High.

#### Distinguishable failures
**What:** `==` on secrets/MACs; different errors for padding vs MAC; enumeration via login or reset
responses. **Why:** A16. **Detect:** comparisons and error branches in crypto and auth paths. ✅.
**Severity:** Medium; High for padding oracles.

#### Secret in code or artefact
**What:** Keys, passwords, tokens, connection strings in source, config committed to VCS, Dockerfiles,
CI YAML, mobile/front-end bundles, test fixtures pointing at real systems. **Why:** A17. **Detect:**
secret scanners over the tree and history; grep. ✅ — record kind and location, never the value.
**Severity:** Critical when live; High when revoked but unrotated elsewhere.

#### TLS verification disabled
**What:** HTTP or database clients that skip certificate or hostname verification. **Why:** A20, A14.
**Detect:** client options. ✅. **Severity:** High.

#### Keys without lifecycle
**What:** One key for all environments; no rotation; keys stored beside the data they protect;
decryption available to every admin. **Why:** A17. **Detect:** key loading code, config per env. ✅/⚠️.
**Severity:** Medium; High for signing keys.

### Checklist
1. Crypto uses through vetted libraries with authenticated modes and current algorithms.
2. Tokens, salts, IVs and nonces from a CSPRNG; nonces unique per key.
3. Keys separated by purpose and environment.
4. Secret comparisons constant-time; crypto errors uniform.
5. Secrets read at runtime from a store; none in VCS or artefacts.
6. TLS clients verifying certificates and hostnames.
7. Keys with an owner and a rotation path.

---

## 5. configuration — how it's deployed

In scope: deployable configurations, one per environment.

### 🟢 Well done
- Production config separate and reviewed; debug, tracing and samples off (A18).
- Generic error pages; diagnostics to logs (A19).
- HTTPS-only with HSTS; baseline security headers; no version banners (A20).
- Admin and management endpoints off or behind authentication and network controls (A18).
- Security checks fail closed on error (A18).

### 🔴 Not well done

#### Debug or tracing in production
**What:** Debug flags, trace endpoints, dev tools, interactive debuggers, `NODE_ENV` not production.
**Why:** A18. **Detect:** per-environment config files and start commands. ✅ when the prod config is
in the repo; 🔬 when only environment variables decide. **Severity:** High; Critical for remote
debuggers.

#### Verbose errors
**What:** Stack traces, SQL, paths or versions in responses. **Why:** A19. **Detect:** error-handler
configuration; exception-to-response mappings. ✅. **Severity:** Medium.

#### Exposed management surface
**What:** Actuator `*`, admin consoles, GraphQL introspection and playgrounds, Swagger UI with live
credentials, `phpinfo()`, directory listing in production. **Why:** A18. **Detect:** config and
route grep. ✅. **Severity:** High when unauthenticated.

#### Missing browser protections
**What:** No CSP (or `unsafe-inline` everywhere), no `nosniff`, no framing control, no HSTS, no
`Referrer-Policy`; cookies not `Secure` by default. **Why:** A20. **Detect:** middleware/header
config; 🔬 when a proxy adds headers. **Severity:** Medium; High for HSTS absence on authenticated
apps.

#### Default credentials and sample apps
**What:** Framework or admin defaults left in place; sample/test accounts seeded in production.
**Why:** A18. **Detect:** seed scripts, config. ✅. **Severity:** Critical.

#### Fail-open handling
**What:** Exceptions in authorisation, validation or verification paths that return success or skip
the check. **Why:** A18. **Detect:** `catch` blocks in security paths. ✅. **Severity:** High.

#### Environment drift
**What:** Security settings differ across environments by hand; prod config not in VCS; secrets
per environment managed inconsistently. **Why:** A18, A17. **Detect:** config diff. ⚠️.
**Severity:** Medium.

### Checklist
1. Production configurations with debug/trace/dev tooling off.
2. Generic error responses; diagnostics only in logs.
3. Management endpoints disabled or authenticated and network-restricted.
4. HTTPS enforced with HSTS on authenticated apps.
5. Baseline headers (CSP, `nosniff`, framing, `Referrer-Policy`) set.
6. No default or sample credentials.
7. Security checks failing closed.
8. Configuration per environment versioned and reviewed.

---

## 6. dependencies — what you ship that you didn't write

In scope: direct dependencies (transitive for vulnerability criteria) and the runtime.

### 🟢 Well done
- Lockfile committed; versions pinned; updates by automated PRs with tests (A21).
- SCA in CI that blocks known-exploited and critical-reachable vulnerabilities (A21).
- Runtime and frameworks inside support; no 0.x on critical paths (A21).
- SBOM per release; licence inventory checked against how the product ships (A22).

### 🔴 Not well done

#### Known-vulnerable component
**What:** A dependency version with a published vulnerability, especially one on a known-exploited
list, on a reachable path. **Why:** A21. **Detect:** SCA output; lockfile vs advisories. ✅ for
presence; ⚠️ for reachability unless traced. **Severity:** Critical when known-exploited and
reachable; High for critical CVEs; Medium when unreachable.

#### Unpinned or unlocked
**What:** No lockfile; floating ranges; installs without versions; `latest` tags. **Why:** A21.
**Detect:** manifests and lockfiles. ✅. **Severity:** Medium.

#### End-of-life runtime or library
**What:** Language runtime, framework or library past its support window. **Why:** A21. **Detect:**
versions vs vendor lifecycle. ✅. **Severity:** High for runtimes and frameworks; Medium for libraries.

#### Unvetted or abandoned dependency
**What:** Single-maintainer packages unchanged for years on critical paths; typo-similar names to
popular packages; install scripts; packages from unofficial registries. **Why:** A21. **Detect:**
registry metadata, manifest review. ⚠️. **Severity:** Medium; High for install-script packages from
unknown publishers.

#### Integrity unverified
**What:** CDN scripts without `integrity`; downloads in build scripts without checksum; lockfiles
without hashes where the ecosystem supports them. **Why:** A21. **Detect:** `<script src=` without
`integrity`; `curl | sh`. ✅. **Severity:** Medium.

#### Stale fork or vendored copy
**What:** Vendored or forked libraries far behind upstream security fixes. **Why:** A21. **Detect:**
vendored directories vs upstream versions. ✅. **Severity:** Medium; High when behind a security fix.

#### Licence obligation unmanaged
**What:** No licence inventory; copyleft (GPL, AGPL) in a distributed or hosted product without a
decision; incompatible combinations; notices missing from releases; unlicensed pasted code. **Why:**
A22. **Detect:** ScanCode/licensee/SBOM; manifest licence fields; NOTICE presence. ✅. **Severity:**
High for triggered strong copyleft without a decision; Medium otherwise.

### Checklist
1. Dependencies locked and pinned.
2. Dependencies free of known-exploited or critical reachable vulnerabilities.
3. SCA running in CI with a blocking threshold.
4. Runtime and frameworks inside support.
5. Dependencies maintained and from trusted registries.
6. External assets integrity-checked.
7. SBOM produced per release.
8. Licences inventoried, compatible with the shipping model, notices included.

---

## 7. logging — what happened, and who knows

In scope: security-relevant events — login success and failure, access denied, privilege and role
change, admin action, credential and MFA change, validation failure.

### 🟢 Well done
- Every security event logged with actor, action, target, time, source and outcome (A23).
- Logs shipped off-host to a store the app can't rewrite; retention set (A23).
- Alerts on bursts of failures, denials and admin actions route to an owned channel (A23).
- No secrets, tokens, passwords or unnecessary personal data in logs; input sanitised for newlines
  (A24).

### 🔴 Not well done

#### Security events not logged
**What:** No log on login failure, authorisation denial, role change or admin action. **Why:** A23.
**Detect:** handlers for those events without a log call. ✅. **Severity:** Medium; High for admin
actions in regulated systems.

#### Secrets or credentials in logs
**What:** Request bodies, headers (`Authorization`, `Cookie`), tokens, passwords — including the
username field of a failed login — written to logs or error trackers. **Why:** A24. **Detect:** log
calls over request objects; logger configuration; error-tracker scrubbing. ✅. **Severity:** High.

#### Log injection
**What:** User input logged without encoding newlines and control characters. **Why:** A24.
**Detect:** string-concatenated log calls with request data and a plain-text format. ✅.
**Severity:** Low; Medium where logs drive automated decisions.

#### Logs that don't survive
**What:** Logs only on local disk of ephemeral instances; writable by the app's own credentials; no
retention. **Why:** A23. **Detect:** logging configuration and destination. ✅/🔬. **Severity:**
Medium.

#### No alerting
**What:** Events logged but nobody alerted. **Why:** A23. **Detect:** alert rules; 🔬 if they live
outside the repo. **Severity:** Medium.

### Checklist
1. Security events logged with actor, action, target, time, source and outcome.
2. No secrets, tokens, passwords or unnecessary personal data in logs.
3. Logged input encoded against forging.
4. Logs shipped off-host, tamper-resistant, with retention.
5. Alerts on security event patterns routed to an owned channel.

---

## 8. browser — what the browser does with what you send

In scope: HTTP response classes (route classes × content type — HTML pages, JSON APIs, user files,
static assets) plus cross-origin channels (CORS policies, `postMessage` handlers, frames, embedded
third-party resources). Applies where a browser is a client; mark it N/A for a service-to-service API
with no browser.

### 🟢 Well done
- Every response class has an explicit type and charset, `nosniff`, a framing policy and the right
  `Cache-Control`; authenticated responses are `no-store` (A25, A32, A35).
- User files are served as attachments from a sandbox origin or object store (A26).
- One URL parser decides every redirect, fetch and link; schemes and hosts are allow-listed (A28).
- Cross-origin access is explicit: exact-origin CORS, pinned `postMessage`, no `document.domain`
  (A29, A30).
- Session cookies are host-only with `__Host-`; no sibling subdomain hosts less-trusted code (A31).
- Third-party code is inventoried, self-hosted or SRI-pinned, ads sandboxed (A34).

### 🔴 Not well done

#### Type left to the browser
**What:** Responses without `charset`, without `nosniff`, or with a type the request controls; user
content served as `text/plain`/`octet-stream`. **Why:** A25. **Detect:** response-header contract
per route class; handlers setting types from input. ✅. **Severity:** High where user bytes are
served on the app origin; Medium otherwise.

#### User files rendered on the app origin
**What:** Uploads served inline from the application origin, under the web root, with client-chosen
names; SVG/HTML/PDF served as-is. **Why:** A26. **Detect:** storage path, download handler headers,
cookie domain vs file host. ✅. **Severity:** High.

#### Header or response splitting
**What:** Request data placed into headers, cookies or `Location` without stripping CR/LF/NUL.
**Why:** A27. **Detect:** header-setting calls with request-derived values. ✅. **Severity:** High.

#### Ad-hoc URL checks
**What:** Redirect, fetch or link decisions by regex, prefix or substring; scheme blacklists; separate
parsers for check and use. **Why:** A28 (and A5). **Detect:** string methods over URLs feeding
redirects, fetches or `href`. ✅. **Severity:** High on login and redirect flows; Medium elsewhere.

#### Unpinned cross-origin messaging
**What:** `postMessage(…, "*")`; listeners without exact `event.origin` checks; `document.domain`
set; `window.name`/`location.hash` as a channel. **Why:** A29. **Detect:** listener and sender code.
✅. **Severity:** High when message data reaches a DOM sink or an action.

#### CORS as protection, or CORS wide open
**What:** Reflected `Origin` or `null` allowed; credentials with wildcards; suffix matching; no
`Vary: Origin`; CORS relied on to stop CSRF. **Why:** A30. **Detect:** CORS configuration and
middleware. ✅. **Severity:** Critical with credentials on user data; High otherwise.

#### Cookies scoped to the whole domain
**What:** Session cookies with `Domain=`; no `__Host-` prefix; double-submit CSRF tokens; wildcard or
dangling DNS under the domain. **Why:** A31. **Detect:** `Set-Cookie` attributes; CSRF implementation;
DNS records if supplied (🔬 otherwise). ✅/🔬. **Severity:** High.

#### Frameable sensitive pages
**What:** No `frame-ancestors`; frame-busting scripts as the only defence; `sandbox` granting scripts
and same-origin together; `target="_blank"` without `noopener` on untrusted links; one-click
destructive actions. **Why:** A32. **Detect:** response headers, templates. ✅. **Severity:** Medium;
High for settings, payment or permission pages.

#### Cross-site script inclusion
**What:** Cookie-authenticated GET endpoints returning user data as script or JSON without a token;
JSONP with a free-form callback. **Why:** A33. **Detect:** callback parameters; response types of
user-data endpoints. ✅. **Severity:** High.

#### Unpinned third-party code
**What:** Off-origin scripts and styles without `integrity`; HTTP script sources; unsandboxed ad
frames; dangling `CNAME`s. **Why:** A34. **Detect:** templates and HTML; DNS if supplied. ✅/🔬.
**Severity:** Medium; High for payment and login pages.

#### Cacheable personal responses; trusted Host
**What:** Authenticated responses without `no-store`; CDN rules caching personal paths; URLs built
from `Host`/`X-Forwarded-Host`; any-host acceptance. **Why:** A35. **Detect:** cache headers and CDN
config; host-header reads feeding links and e-mails. ✅. **Severity:** High for reset-link poisoning;
Medium otherwise.

#### HTML filtered by regex
**What:** Home-made sanitisers, `strip_tags`, unquoted attributes, user-set `id`/`name`. **Why:** A36.
**Detect:** sanitiser code and templates. ✅. **Severity:** High where the output renders to other
users.

#### Internal means trusted
**What:** Internal tools or dev servers without authentication, CSRF protection or `Host` validation.
**Why:** A37. **Detect:** auth configuration of internal apps; bind addresses. ✅/⚠️. **Severity:**
High.

#### Unbounded requests
**What:** No body, header, upload, archive-expansion or timeout limits; unbounded pagination; regexes
with nested quantifiers on input. **Why:** A39. **Detect:** server and parser configuration;
extraction code. ✅. **Severity:** Medium; High for archive and XML expansion.

### Checklist
1. Response classes with explicit type and charset plus `nosniff`.
2. User files served as attachments from outside the app origin.
3. Header and cookie values free of unencoded request data.
4. URL decisions made on parsed, allow-listed scheme and host.
5. Cross-origin messaging pinned to exact origins; no `document.domain`.
6. CORS allow-listed exactly, no credentials with wildcards, `Vary: Origin`.
7. Session cookies host-only (`__Host-`), CSRF tokens bound to the session.
8. Sensitive pages deny framing; destructive actions need a second step.
9. No cross-site-includable user data; no free-form JSONP.
10. Third-party code SRI-pinned or self-hosted; ads sandboxed.
11. Authenticated responses `no-store`; links built from configured hosts.
12. Request size, time and expansion bounded.

---

## 9. api — every operation, every version, every field

In scope: API operations in the reconciled inventory — one object per route × method × version
(REST operations, GraphQL queries/mutations/subscriptions, RPCs). Applies where the service exposes
an API; mark it N/A otherwise. Object- and function-level authorisation stay graded in **access**;
this domain grades what's specific to APIs.

### 🟢 Well done
- The inventory reconciles code, spec, gateway and DNS; retired versions answer `410` (A40).
- Responses are built from per-role shapes; requests bind allow-listed writable fields; the schema
  says which is which (A41).
- Rate, size and cost limits keyed on the principal and normalised route, across versions (A42).
- Documentation and introspection are off in production or behind authentication (A43).

### 🔴 Not well done

#### Shadow and zombie APIs
**What:** Routes in code missing from the spec; old versions, test environments or hosts still
served; deprecated operations still routed; versions with weaker controls than the current one.
**Why:** A40. **Detect:** route-vs-spec diff; version routers; `servers` entries; replay one request
across version paths in an owned environment. ✅ in repo; 🔬 for gateway and DNS not supplied.
**Severity:** High when the older surface lacks a control the current one has; Medium otherwise.

#### Excessive data exposure
**What:** Stored objects serialised whole; response schemas wider than any consumer uses; sensitive
fields (hashes, MFA state, e-mail, internal IDs) returned to roles that shouldn't see them. **Why:**
A41. **Detect:** serialisation of entities; serialiser field lists; per-role response diff in an
owned environment. ✅. **Severity:** High; Critical for credentials or other users' personal data.

#### Writable properties not controlled
**What:** Create/update operations accepting properties the caller may not set (`role`, `isAdmin`,
`balance`, `price`, `ownerId`), or unvalidated values for them. **Why:** A41 (with A12). **Detect:**
request binding and schemas; send one extra privileged property as a test user and re-read. ✅.
**Severity:** Critical when it grants privilege; High otherwise.

#### Unmetered consumption
**What:** No limits on login, OTP, reset, search or expensive operations; limiters keyed on
spoofable headers or raw paths; unbounded page sizes, batch counts, GraphQL depth or complexity.
**Why:** A42. **Detect:** limiter middleware and keys; schema maxima; small-burst check on a
throwaway account in an owned environment. ✅/⚠️. **Severity:** High for credential and OTP
endpoints; Medium otherwise.

#### Discovery artefacts exposed
**What:** Swagger UI, `openapi.json`, GraphQL introspection or playgrounds reachable in production
without authentication; gates keyed on client-settable cookies; docs stating rules the code doesn't
enforce. **Why:** A43. **Detect:** doc and introspection configuration per environment. ✅.
**Severity:** Medium; High when the docs describe admin or internal operations.

#### Existence oracles
**What:** Different status, body or timing for "exists but not yours" vs "doesn't exist"; timing
headers on by default. **Why:** A16, A10. **Detect:** handler branches; compare responses for
another user's ID and a missing ID in an owned environment. ✅. **Severity:** Medium; High where it
enumerates accounts.

#### Gateway as the only check
**What:** Services that rely on a gateway, WAF or backend-for-frontend for authorisation or
validation; proxies forwarding client-chosen paths. **Why:** A9, A5. **Detect:** comments and config
assuming upstream validation; path-rewrite rules built from request data; internal services with no
authorisation of their own. ✅/⚠️. **Severity:** High.

#### Tokens and keys in the open
**What:** JWT payloads carrying secrets or whole user records; weak or literal signing secrets;
verification without an algorithm pin; API keys in front-end bundles, mobile apps or URLs. **Why:**
A7, A17. **Detect:** signing and verify calls; bundles and configs; secret scanners. ✅.
**Severity:** Critical for a forgeable token or a live secret key; High otherwise.

### Checklist
1. Operations present in the reconciled inventory, with no shadow or zombie surface.
2. Retired versions answering `410` and covered by a CI check.
3. Responses built from per-role shapes; no stored object serialised whole.
4. Writable properties allow-listed and validated server-side.
5. Consumption limits keyed on the principal and normalised route, across versions.
6. Page size, batch, depth and complexity bounded.
7. Documentation and introspection off in production or authenticated.
8. Refusals indistinguishable for "not yours" and "doesn't exist".
9. Every service enforces its own authorisation behind any gateway.
10. Tokens carry no secrets, verify with a pinned algorithm and a strong key; no keys shipped to clients.
