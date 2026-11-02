# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How an application security review is graded and written down. **Rubric version: `v1.0`.** Every
> output records the rubric version it was graded against and the source version (commit) it read.
> Each finding names the principle it violates from [`theory.md`](theory.md) (A-N). A finding that
> asserts a defect without naming the principle is incomplete — a defect without a principle is
> taste.
>
> The formula is the same one the database, networking, infrastructure and other security skills
> use, so a 7.4 means the same thing everywhere.

## Severity taxonomy

Severity reads **reachability** (anonymous internet, authenticated user, admin only, internal
service) and the **data class** behind the endpoint. Say which you graded against.

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | An outsider or any user can read or change data that isn't theirs, run code, or take over accounts — now | Injection (SQL, OS command, template, deserialisation) reachable from an unauthenticated or ordinary-user endpoint; a missing authorisation or ownership check exposing other users' or tenants' data; authentication bypass (`alg: none` accepted, a trusted client-set cookie); a live credential, key or token committed to VCS or shipped in an artefact; passwords stored in plaintext or reversibly; a known-exploited vulnerability in a dependency on a reachable path |
| **High** | A broad weakness one step from compromise | Stored or reflected XSS on an authenticated page; CSRF on a state-changing action; SSRF to internal ranges or metadata; path traversal; open redirect on a login flow; passwords hashed with a fast or unsalted function; session IDs in URLs or not rotated on login; reset tokens that don't expire or are reusable; account enumeration plus no throttling; TLS verification disabled in a client; debug/trace endpoints in production; ECB or unauthenticated encryption of sensitive data; hard-coded keys; secrets in logs; a dependency with a critical CVE on a reachable path; AGPL/GPL in a product shipped in a way that triggers it, with no decision |
| **Medium** | Controlled risk, or debt that becomes High as the code grows | Authorisation checks duplicated per handler with no central layer; missing security headers (CSP, `nosniff`, framing); cookies without `SameSite`; verbose errors; no lockfile or floating version ranges; EOL runtime or library without a known exploit; no logging of authentication or authorisation failures; CORS wider than needed without credentials; uploads without size/type limits; licence inventory missing |
| **Low** | Hygiene, documentation, cosmetic | `X-Powered-By` and version headers; missing `rel="noopener"` on internal links; inconsistent validation messages; outdated but unaffected dev-only dependencies; missing NOTICE entries for permissive components in internal tools |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current practice.
- 🟡 **Acceptable / watch**: works, but carries security debt.
- 🔴 **Not well done**: violates the criterion. A defect, an anti-pattern, or a theory failure.

## Detection confidence

Not everything can be proven from source. Every anti-pattern carries one of three tags.

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the code and config: a request value traced into a concatenated query; a handler with no authorisation on a path that changes state; `DEBUG=True` in the production settings file; `MD5` over a password; a lockfile entry at a version with a published CVE | Yes. A confirmed defect. |
| ⚠️ **proxy** | A static signal that needs judgement: a sink whose input *may* be user-controlled through layers you couldn't fully trace; a dependency CVE whose vulnerable function may not be reachable; a missing header whose impact depends on the page; per-handler checks that look consistent but aren't centrally enforced | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs runtime evidence or access you don't have: what the reverse proxy adds or strips, whether the WAF blocks a payload, the production values of environment variables, whether a token is actually validated by a gateway in front, real traffic patterns | **No.** Recorded as a flag, never scored. |

A defect demonstrated by a test you wrote and ran locally, or by a request to an environment the
user owns and named, is ✅. Configuration read from the file is weaker than configuration observed
from the running system — say which you read.

## Scoring model

### Evaluation units

One evaluation per **domain** per service, graded with its section of
[`review-rubric.md`](review-rubric.md):

| Domain | In-scope objects (the weight) |
|---|---|
| input | sinks reached by untrusted data: queries, commands, templates/HTML outputs, parsers/deserialisers, outbound requests, file paths, redirects |
| authentication | authentication and session mechanisms, credential stores, recovery flows, token validators |
| access | endpoints and handlers: pages, APIs, RPCs, resolvers, webhooks, static and private file routes |
| crypto | crypto uses (hashing, encryption, signing, random generation, TLS clients) and secrets |
| configuration | deployable configurations, one per environment |
| dependencies | direct dependencies (and transitive ones for the vulnerability criteria), plus the runtime |
| logging | security-relevant events: login success/failure, access denied, privilege change, admin action, credential change, validation failure |
| browser | HTTP response classes (route classes × content type) plus cross-origin channels: CORS policies, `postMessage` handlers, frames, embedded third-party resources |
| api | API operations in the reconciled inventory: route × method × version (REST operations, GraphQL operations, RPCs) |

A domain with no in-scope objects (no browser client; no exposed API) is **N/A** and contributes
nothing to the weighted mean — say so in the summary rather than scoring it 10.

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   "In-scope" excludes objects the criterion cannot apply to: the CSRF criterion doesn't apply to a
   read-only endpoint or one authenticated only by a bearer header.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps**, applied after the base (lowest wins): any open **Critical** caps at **2.0**; any
   open **High** caps at **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Per-service and estate scores

The **service score** is the mean of its domain scores, weighted by in-scope object count, with the
Critical/High caps re-applied. The **estate score** is the mean of service scores, weighted by total
objects, caps re-applied. Report the uncapped mean beside the capped one.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A service is **secure enough to ship** — no remediation proposal is owed — only when all of these
hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- every state-changing endpoint has a server-side authorisation check, and — where cookies
  authenticate it — a CSRF/same-site defence (A9, A10, A12);
- no unrotated secret is present in VCS (history included) or in shipped artefacts (A17);
- passwords, if stored, use a slow salted KDF (A8);
- no dependency has a known-exploited vulnerability on a reachable path (A21);
- no API version, environment or documentation endpoint is exposed that the reconciled inventory
  doesn't list and control (A40, A43);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately. A 9.5 whose invoice endpoint
returns any invoice by ID is not secure.

## OWASP Top 10 mapping

Report every finding's OWASP category alongside its A-N, so readers who think in OWASP terms can
follow. The 2025 column follows the list as published at writing — verify the numbering against the
current release before quoting it.

| Domain | Typical findings | OWASP 2021 | OWASP 2025 (verify) |
|---|---|---|---|
| input | SQL/NoSQL/OS/LDAP injection, XSS, template injection | A03 Injection | A05 Injection |
| input | XXE, unsafe deserialisation | A05 Security Misconfiguration / A08 Software and Data Integrity Failures | A02 / A08 |
| input | SSRF | A10 Server-Side Request Forgery | A01 Broken Access Control |
| input | path traversal, open redirect | A01 Broken Access Control | A01 |
| authentication | weak password storage, session flaws, missing MFA, reset flaws, JWT flaws | A07 Identification and Authentication Failures | A07 Authentication Failures |
| access | IDOR, missing function-level checks, CSRF, CORS, mass assignment, tenant leaks | A01 Broken Access Control | A01 |
| access | business-logic and workflow bypass | A04 Insecure Design | A06 Insecure Design |
| crypto | weak algorithms and modes, bad randomness, hard-coded keys, TLS verification off | A02 Cryptographic Failures | A04 Cryptographic Failures |
| configuration | debug, verbose errors, default credentials, missing headers, exposed admin | A05 Security Misconfiguration | A02 Security Misconfiguration |
| configuration | fail-open error handling | A04 Insecure Design | A10 Mishandling of Exceptional Conditions |
| dependencies | vulnerable/EOL components, unpinned, unverified integrity | A06 Vulnerable and Outdated Components / A08 | A03 Software Supply Chain Failures |
| dependencies | licence obligations | — (not an OWASP category) | — |
| logging | missing security events, secrets in logs, no alerting | A09 Security Logging and Monitoring Failures | A09 Logging & Alerting Failures |
| browser | content sniffing, header injection, framing, XSSI, HTML filtering | A03 Injection / A05 Security Misconfiguration | A05 / A02 |
| browser | CORS, `postMessage`, cookie scope, URL parsing on redirects | A01 Broken Access Control | A01 |
| browser | third-party scripts without SRI, dangling DNS | A08 Software and Data Integrity Failures | A03 Software Supply Chain Failures |
| browser | cacheable personal responses, Host-header trust, unbounded requests | A05 Security Misconfiguration / A04 Insecure Design | A02 / A06 |
| api | see the API table below | — | — |

### OWASP API Security Top 10

API findings also carry their API Security category. HAPI is organised around the 2019 list; the
2023 list is current practice and is the one to report.

| API finding | API 2019 (HAPI) | API 2023 (current) | Domain |
|---|---|---|---|
| Object ID not checked against the caller (body, nested, array IDs included) | API1 Broken Object Level Authorization | API1 Broken Object Level Authorization | access |
| Token, key, OTP and login weaknesses | API2 Broken User Authentication | API2 Broken Authentication | authentication / api |
| Stored objects serialised whole; sensitive fields returned | API3 Excessive Data Exposure | API3 Broken Object Property Level Authorization | api |
| No rate, size or cost limits | API4 Lack of Resources & Rate Limiting | API4 Unrestricted Resource Consumption | api |
| Function or method not checked against role | API5 Broken Function Level Authorization | API5 Broken Function Level Authorization | access |
| Extra properties accepted on write | API6 Mass Assignment | API3 (merged into BOPLA) | api |
| Search, OTP, coupon, checkout abused at scale | — (business logic, ch3) | API6 Unrestricted Access to Sensitive Business Flows | access / api |
| Server fetches a client-chosen URL or path | — | API7 Server Side Request Forgery | input |
| Debug, verbose errors, open docs, extra methods, headers | API7 Security Misconfiguration | API8 Security Misconfiguration | configuration / api |
| Injection through API inputs | API8 Injection | — (no separate category) | input |
| Shadow, zombie and test versions | API9 Improper Assets Management | API9 Improper Inventory Management | api |
| Missing security events | API10 Insufficient Logging & Monitoring | — (dropped) | logging |
| Trusting data from third-party APIs | — (cross-API scripting, ch12) | API10 Unsafe Consumption of APIs | input |

## Triage for large codebases

Above **~200 endpoints or ~200k lines**, don't read everything cold:

1. **Signal-scan** everything with [`detection-signals.md`](detection-signals.md) and the static tools;
   record counts per anti-pattern.
2. **Rank** modules by exposure (anonymous and public endpoints first, then authenticated,
   admin, internal) and by signal density. Deep-read every anonymous endpoint, every endpoint touching
   money, credentials, permissions or tenancy, the worst 10% of the rest, plus a random sample of ~5.
3. **Shared layers first**: the authentication middleware, the authorisation layer, the query
   builder, the template helpers and the HTTP client wrapper are each read once and in full — one
   defect there is a defect everywhere.
4. **State coverage**: "deep-read 64 of 410 endpoints (all 23 anonymous); signals cover all 410."

The endpoint inventory must still cover **everything**: the endpoint nobody listed is the one
without an authorisation check.

## Theory → domain mapping

| Domain | Primary theory to invoke |
|---|---|
| input | Untrusted until validated (A1); data out of the code channel (A2); encode for context (A3); parsers are attack surface (A4); server-side capabilities (A5) |
| authentication | Framework authentication (A6); sessions are bearer credentials (A7); slow salted KDF and recovery (A8) |
| access | Server-side, every request, deny by default (A9); check the object (A10); obscurity isn't control (A11); bind to intent (A12); atomic checks and invariants (A13) |
| crypto | Vetted crypto, authenticated modes (A14); randomness and uniqueness (A15); fail indistinguishably (A16); secrets outside code (A17) |
| configuration | Fail closed (A18); errors don't leak (A19); transport and browser protections (A20) |
| dependencies | Dependencies are your code (A21); licences are obligations (A22) |
| logging | Log security events durably (A23); never log secrets, prevent log forging (A24) |
| browser | Explicit types (A25); inert user files (A26); no header injection (A27); one URL parser (A28); pinned messaging (A29); CORS is read-permission (A30); cookie scope (A31); framing (A32); XSSI (A33); third-party code (A34); caches and Host (A35); HTML filtering (A36); network position (A37); don't launder abuse (A38); bounded requests (A39) |
| api | Living inventory (A40); per-role properties in and out (A41); metered consumption (A42); gated discovery artefacts (A43); plus object and function checks from access (A9, A10) |

## Templates

### Per-domain evaluation — `analysis/appsec/<service>/<domain>.md`

```markdown
# <Service> — <Domain> evaluation
> Evaluated against appsec/review-rubric.md §<domain> (rubric v1.0).
> Source: <paths> — as of <git commit>. Stack: <language/version, framework, template engine, ORM, auth>.
> Coverage: <N of M objects deep-read; signals cover all M>. Dynamic testing: <none / environment named by the user>.

## Findings
| ID | Object | Anti-pattern | Conf. | Theory violated | OWASP | Severity | Evidence (source → sink, missing check) |
|----|--------|--------------|-------|-----------------|-------|----------|------------------------------------------|
| AS-ACC-01 | GET /api/invoices/{id} | Object not checked against caller | ✅ | Check the object (A10) | A01:2021 | Critical | routes/invoices.js:41 `findById(req.params.id)`, no owner predicate |

## Signal counts
| Anti-pattern | Count |
|--------------|------:|

## Needs-data flags (not scored)

## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)
```

### Per-service summary — `analysis/appsec/<service>/summary.md`

```markdown
# <Service> — Application security review summary
> Endpoints: <n> (anonymous <n>) · sinks: <n> · dependencies: <n direct / n total>. Source as of <commit>; rubric v1.0.

## Scores
| input | authentication | access | crypto | configuration | dependencies | logging | browser | api | **Service** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

## Severity tally · OWASP tally · Needs-data flags
## Endpoint inventory (route → method → version → authn → authz → inputs → sinks → state change → cookie-auth)
## Inventory reconciliation (code ↔ spec ↔ gateway ↔ DNS: shadow, zombie, drift)
## Authorisation matrix (operation × actor → allow / refusal), where Design or a test supplied one
## Trust boundaries
## What is working well
## Top findings (worst first)
## Systemic issues (shared causes)
## Gate (each condition, pass/fail, with the reason)
```

Finding IDs: `AS-<INP|AUT|ACC|CRY|CFG|DEP|LOG|BRW|API>-NN`.
