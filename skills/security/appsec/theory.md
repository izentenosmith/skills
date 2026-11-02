# Theory — The Principles Every Appsec Finding Cites (A1–A43)

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** in application code, and **what violating it looks like**. Sources are cited by short
> name:
>
> | Short name | Source |
> |---|---|
> | **SE** | Ross Anderson, *Security Engineering*, 3rd ed. (Wiley, 2020) — PDF page numbers |
> | **ONET** | Troy Hunt, *OWASP Top 10 for .NET developers* (2011) — built on the OWASP Top 10 2010; chapter and page |
> | **LWD** | Linux Professional Institute, *Web Development Essentials* (030) learning materials, v1.0 — topic and PDF page |
> | **LOS** | Linux Professional Institute, *Open Source Essentials* (050) learning materials, v1.0 — topic and PDF page |
> | **LSE** | Linux Professional Institute, *Security Essentials* (020) learning materials, v1.0 — topic and PDF page |
| **TW** | Michal Zalewski, *The Tangled Web* (No Starch, 2011) — chapter and PDF page (PDF = printed + 22) |
| **WSD** | Malcolm McDonald, *Web Security for Developers* (No Starch, 2020) — chapter and PDF page (PDF = printed + 28) |
| **HAPI** | Corey Ball, *Hacking APIs* (No Starch, 2022) — chapter and PDF page (PDF = printed + 28) |
| **TAOSSA** | Dowd, McDonald & Schuh, *The Art of Software Security Assessment* (Addison-Wesley) — chapters 1–4 preview; printed pages |
> | **Practice** | Current practice where the books predate a mechanism: OWASP Top 10 (2021, 2025), OWASP API Security Top 10 (2023), OWASP ASVS and Cheat Sheets, CWE, NIST SP 800-63B, SPDX/CycloneDX, the WHATWG URL/HTML/Fetch standards |
>
> ONET is written for ASP.NET; every principle here is stated stack-neutrally and the .NET mechanism
> is one example of it. Where a book's mechanism is dated, the principle stands and the current
> mechanism is named — see **Where the books are dated** at the end.

---

## Part A — Input: data must stay data

### A1 — All input is untrusted until validated against an allow-list
**Says:** Every value from outside the process is hostile until checked — query string, form, route
parameters, headers, cookies, uploaded files and their metadata, message payloads, data read back from
your own database. Validate type, format, length and range against what is allowed, not against a
list of what is forbidden; client-side validation is a convenience, never the control (ONET ch1,
pp.16, 23–24, 32; ONET ch2, pp.41–42; LWD 035.2, pp.315–316; LWD 032.4, p.139).
**Why:** A blacklist is a race the attacker always wins; type conversion is not validation — a
string-typed value passes straight through (ONET ch1, pp.25, 33). ONET's injection demo ran through
the `Accept-Language` header, not a form field (p.32).
**Violation:** request values used with no schema or validator; validation only in JavaScript or
HTML attributes (`accept=`, `maxlength`); regexes that strip "bad" characters; headers and cookies
trusted because "users can't edit them".

### A2 — Keep data out of the code channel
**Says:** Never build a query, command, filter or expression by concatenating untrusted data into it.
Use parameterised statements, an ORM's bound parameters, argument arrays instead of a shell, and
allow-lists for the parts parameters can't carry (table and column names, sort order) (ONET ch1,
pp.18–27; LWD 035.3, p.347; SE §6.4.1–6.4.2, pp.279–280 — stack smashing and SQL injection are the
same failure: data interpreted as code).
**Why:** Injection is cheap to prevent and catastrophic when missed — ONET's demo went from a
tautology to schema discovery to bulk exfiltration in a few requests (pp.19–22). Stored procedures
that build dynamic SQL inside are concatenation moved one layer down (p.25).
**Violation:** `"SELECT … " + id`, template literals or f-strings in `query()/execute()`;
`exec`/`sp_executesql` over string parameters; `os.system`, `shell=True`, `child_process.exec`,
`Runtime.exec` with request data; Mongo queries built from `req.body` objects (operator injection);
LDAP filters assembled from input; an all-powerful database login that turns any injection into
total loss (ONET ch1, p.28).

### A3 — Encode output for its context, by default
**Says:** Data written into HTML, an attribute, JavaScript, a URL, CSS or a header is encoded for
that exact context at the point of output — including data from your own database, admin screens and
e-mails. Use a template engine that escapes by default and a vetted encoder library; when users may
supply HTML, sanitise it with a library rather than encoding or hand-writing a filter (ONET ch2,
pp.45–50; LWD 035.2, p.334 — `<%=` escapes, `<%-` doesn't).
**Why:** XSS breaks out of a data context into a code context (ONET ch2, p.36). HTML-encoding inside
a `<script>` block is the wrong encoder (pp.48–49); stored XSS fires later, often for an admin (p.48).
**Violation:** unescaped template output (`@Html.Raw`, `<%-`, `{{{ }}}`, `|safe`, `th:utext`,
`v-html`, `dangerouslySetInnerHTML`); `innerHTML`/`document.write` with non-literal data (LWD 034.4,
pp.277–279); handlers that echo request data with `res.send` as `text/html` (LWD 035.2, pp.314–316);
request validation switched off site-wide (ONET ch2, p.44).

### A4 — Parsers and deserialisers are attack surface
**Says:** Treat every parser of untrusted bytes as exposed code: disable external entities and DTDs
in XML parsers, never deserialise untrusted data into native objects, bound sizes and depths, and
prefer data-only formats with schemas (SE §4.8, pp.188–189 — interpret messages from their content,
avoid ambiguous formats; SE §6.4.4, pp.283–284 — prefer memory-safe parsers; Practice: OWASP A08
Software and Data Integrity Failures).
**Why:** A deserialiser that instantiates types named in the input is remote code execution waiting
for a gadget; an XML parser with external entities reads local files and makes outbound requests.
**Also:** Bound the size, depth and expansion of what parsers accept — XML entity expansion, archive bombs (A39).
**Violation:** `BinaryFormatter`, Java `ObjectInputStream`, Python `pickle`/`yaml.load` (unsafe
loader), PHP `unserialize`, Ruby `Marshal.load` on request data; XML parsers with DTD processing on;
unbounded JSON/multipart bodies.

### A5 — Server-side requests, file paths and redirects are capabilities
**Says:** A URL the server fetches, a path it opens, a file it stores and a location it redirects to
are authority the server exercises on the caller's behalf. Resolve them from allow-lists or indirect
identifiers, never from free-form input; store uploads outside the web root with generated names,
checked type and size; redirect only to known destinations (ONET ch10, pp.241–244; LWD 032.4, p.139;
LWD 035.2, p.326 — serve static files from one directory only; SE §6.4.3, p.282 — the confused
deputy; Practice: OWASP A10:2021 SSRF).
**Why:** SSRF reaches cloud metadata endpoints and internal admin APIs; path traversal reads
configuration; an open redirect lends your domain's credibility to a phishing page (ONET ch10,
pp.237–238, 246).
**Also:** Traversal filters fall to double and overlong encodings (`%252e`, `%c0%ae`) — prefer indirect references or the server's own path resolver to string checks (WSD ch11, pp.139–140). A proxy or backend-for-frontend that forwards a client-chosen path to an internal service is SSRF by another name: one real breach traversed through such a proxy into an unauthenticated internal directory API (HAPI ch15, pp.343–345). URL decisions themselves are A28.
**Violation:** `fetch(req.query.url)`, `requests.get(user_url)`; `open(base + filename)` without
canonicalisation; uploads saved under `public/` with the client's file name; `res.redirect(req.query.next)`,
`Response.Redirect(Request.QueryString["Url"])`; `express.static('.')` or a database file reachable by
URL (LWD 035.3, p.345).

## Part B — Authentication and sessions

### A6 — Use the framework's authentication; never roll your own
**Says:** Identity, credential checks, session issuance and recovery come from the platform's
membership/identity component or an identity provider, configured strictly — not from code written
for this app (ONET ch3, pp.66–68, 75; ONET ch8, p.192; LWD 035.2, p.319).
**Why:** Hand-rolled authentication gets the hard parts wrong — timing, recovery, session fixation,
storage — because each looks easy alone. ONET's examples of failures are almost all home-grown
schemes.
**Violation:** `Session["User"] = name` after a custom password check; a cookie like `known=1` or
`role=admin` trusted by its presence or value (LWD 035.2, p.317); a client-chosen identifier used as
the only identity (LWD 035.3, p.348); custom JWT verification code.

### A7 — Sessions are bearer credentials
**Says:** Whoever holds the session identifier is the user. Issue it server-side and unguessable;
carry it only in a cookie (never the URL); rotate it at login and privilege change; expire it on idle
and absolutely; invalidate it on logout; set `Secure`, `HttpOnly` and `SameSite` (ONET ch3,
pp.63–69; ONET ch9, pp.214–221; LWD 031.3, p.49; SE §4.8 / §4.7.4, pp.187–188 — short-lived,
revocable tokens; OAuth is delegation, not authentication).
**Why:** ONET hijacked a session by pasting a URL that carried its identifier (pp.63–65) and by
sniffing an auth cookie sent over HTTP after an HTTPS login (pp.196–214).
**Also:** A client-side session cookie that is only signed is readable by its holder and can't be revoked server-side — encrypt it if it carries anything sensitive, or keep state on the server (WSD ch10, pp.124–125); session IDs in URLs end up in logs (pp.127–128); a flood of attacker-set cookies can push the real session cookie out (TW ch9, pp.172–173). JWT payloads are readable by anyone: one test API signed the user's password, admin flag and balance into the token (HAPI ch7, p.194), and a themed-wordlist guess recovered a weak HMAC secret in minutes (ch8, pp.227–228). Tokens with little entropy are enumerable (pp.216–220).
**Violation:** `cookieless` sessions or `;jsessionid=` in URLs; no regeneration on login; cookies
without `Secure`/`HttpOnly`/`SameSite`; multi-day sliding sessions; JWTs with `alg: none` accepted,
no `exp`, a weak or shared signing secret, or secrets inside the payload; an OAuth access token
treated as proof of who the user is.

### A8 — Passwords are stored with a slow salted KDF, and recovery is the real login
**Says:** Store passwords with a memory- or time-hard function (Argon2id, scrypt, bcrypt, or PBKDF2
with a high iteration count) and a per-user random salt; screen new passwords against a breached
list; allow long passphrases and paste; throttle guessing rather than hard-locking; add MFA. Recovery
uses a single-use, expiring, unguessable link, answers the same whether or not the account exists,
never e-mails a password and doesn't auto-login (ONET ch7, pp.146–161; ONET ch3, pp.69–72; SE §3.4.4–3.4.6,
pp.145–152; SE §3.4.1, pp.139–140; LSE 025.1, p.273).
**Why:** Unsalted fast hashes fall to precomputed tables in seconds (ONET ch7, pp.146–156); recovery
flows are attacked because they're weaker than login — security questions are often publicly
answerable (SE pp.139–140).
**Also:** Run the password hash even when the account doesn't exist — skipping it is a timing oracle (WSD ch9, p.119); reset links expire within about half an hour and are single-use (p.115). One-time codes of 4–6 digits are 10⁴–10⁶ guesses: without a limit keyed to the account (A42) they are brute-forceable (HAPI ch3, p.85).
**Violation:** `MD5`/`SHA-1`/plain `SHA-256` over a password; no salt column; reversible encryption
or plaintext; `EnablePasswordRetrieval`; security questions as the only recovery factor; reset tokens
that don't expire or can be reused; "no account with that e-mail" messages; lockout that lets anyone
deny service to anyone (SE §3.4.6, p.152).

## Part C — Access control

### A9 — Authorise on the server, on every request, at every kind of endpoint; deny by default
**Says:** Every request is checked against the caller's rights at the server, through one
centralised layer that new endpoints inherit — pages, AJAX/JSON, APIs, GraphQL resolvers, webhooks,
file downloads alike. What isn't explicitly allowed is denied (ONET ch8, pp.177–190; ONET ch4,
pp.84–86; LWD 031.2, pp.27, 32–33; SE §6.1, p.254 — upper layers are weaker, so don't leave the
data layer directly reachable).
**Why:** ONET's admin page was protected only by not linking to it (ch8, p.183); its customer service
endpoint checked nothing (ch4, pp.80–85). Duplicated per-handler checks drift.
**Also:** Write the authorisation model down before coding and test who must be *denied* (WSD ch11, pp.133–135). Authorise per HTTP method and per API version too: an admin function distinguished only by method, or a secured `PUT` beside an unsecured `POST`, is a missing check (HAPI ch3, p.88; ch10, p.258). A gateway or WAF in front is an extra layer, never the service's own check (HAPI ch0, p.35).
**Violation:** authorisation only in the UI (`if isAdmin` around a link); routes without auth
middleware or attributes; `permitAll()` ordering mistakes; services callable without the session; a
role check by named user (`User.Identity.Name == "…"`, ONET ch8, p.181).

### A10 — Check the object, not just the function
**Says:** Knowing the caller may "view invoices" isn't enough; check that they may view *this*
invoice. Take identity from the session, never from a caller-supplied ID; put the ownership or
tenant predicate in the data query and treat zero affected rows as "not found"; use indirect or
non-guessable references as a second layer, never the only one (ONET ch4, pp.84–92; LWD 035.3,
pp.348–350; SE §10.4.4, pp.400–401 — a role that spans contexts leaks across them).
**Why:** Insecure direct object references are the commonest real breach shape: ONET replays one
request with the next integer and gets another customer (ch4, pp.80–83); its real cases exposed
businesses' bank details and millions of e-mail addresses (pp.89–90).
**Also:** Every identifier-bearing input goes through the object check — path, query, body, nested objects, arrays, e-mail addresses, phone numbers, group IDs — and an unguessable ID is not the control: GUIDs fell as soon as a list endpoint leaked them (HAPI ch10, pp.252–253, 260–263). A "private" flag enforced only in the UI, and identity searches that accept wildcards, exposed whole user bases in real breaches (HAPI ch15, pp.336–338). Time-gated content behind guessable paths is the same defect (WSD ch11, p.136). Verify with two test identities: A creates, B reads/edits/deletes, A re-reads (HAPI ch10, pp.253–256).
**Violation:** `findById(req.params.id)` with no owner filter; tenant ID read from the request body;
sequential IDs plus no check; bulk endpoints that return every row; admin "impersonate" features with
no audit.

### A11 — Obscurity and client-side signals are not controls
**Says:** Hidden URLs, hidden form fields, disabled buttons, `User-Agent`, `Referer`, source IP and
`Accept` headers are all chosen by the client. Use them for convenience or telemetry, never for a
security decision (ONET ch4, p.90; ONET ch5, pp.112–113; ONET ch8, pp.184, 193; LWD 031.3, p.48; LWD
035.2, p.316).
**Why:** One real service "protected" itself by checking the user agent (ONET ch4, p.90). Anyone can
edit a hidden field with developer tools.
**Also:** A security-relevant flag read from the request (`mfa=true`, `skip_verification`, `role`) is the consumer deciding for the server (HAPI ch3, p.95). A partner API whose end users could call partner-level operations is the same mistake one level up (p.94).
**Violation:** prices, roles or user IDs in hidden fields; authorisation keyed on `req.ip` or
`X-Forwarded-For`; "unguessable" admin paths; content negotiation used as a gate (LWD notes an
endpoint answering only with `Accept: application/json`).

### A12 — Bind every state change to the user's intent
**Says:** A cookie-authenticated request proves the browser sent it, not that the user meant to.
Require an unpredictable per-session token (or a verified same-site/origin policy with `SameSite`
cookies) on every state-changing request; don't change state on GET; allow cross-origin access only to
named origins; accept only the fields a request may set; and never let a privileged component act for
a caller with its own authority (ONET ch5, pp.94–113; SE §6.4.3, p.282; SE §4.3.3–4.3.4, pp.176–180 —
authenticate the transaction, not just the user).
**Why:** ONET's CSRF demo changed a user's status from an unrelated site because the service checked
only that the caller was authenticated (pp.99–102). Mass assignment and confused deputies are the
same failure from the server side.
**Also:** Login forms need CSRF protection too — a silent account switch keeps same-origin access and turns self-XSS into real XSS (TW ch9, pp.167–168); re-authenticate for sensitive actions (WSD ch8, p.107). A double-submit token compared with a cookie is forgeable by anyone who can set a cookie on a sibling subdomain — bind the token to the session (A31). Cross-origin access rules are A29–A30.
**Violation:** state changes with no anti-forgery token and no `SameSite`; `csrf().disable()`,
`@csrf_exempt`; `cors({origin: true, credentials: true})`; binding the whole request body to a model
with `isAdmin`; a service using its own credentials to fetch whatever the caller names.

### A13 — Check and use atomically; enforce invariants in the server
**Says:** A permission checked and then exercised by name can change in between; business rules
(balances, quotas, one-time use, workflow order) are enforced server-side with transactions and
invariants, not trusted to the sequence a client follows (SE §6.4.2, pp.280–281; SE §12.2.1–12.2.3,
pp.449–451 — well-formed transactions and Clark-Wilson; SE §14.5, p.565 — enforce at the point of
consumption).
**Why:** Races and skipped steps turn correct checks into bypasses: redeem a coupon twice in parallel,
skip the payment step by calling the confirm endpoint.
**Also:** Search, one-time-code and coupon endpoints are sensitive business flows and need an abuse control of their own, not just an authorisation check (HAPI ch10, pp.261–264; ch15, pp.336–337).
**Violation:** check-then-act without a lock or conditional update; "replay protection" comparing only
to the previous value (SE §4.4, p.181); multi-step flows whose later steps don't verify the earlier
ones; quantities and prices accepted from the client.

## Part D — Cryptography and secrets

### A14 — Use vetted crypto in authenticated modes; never design your own
**Says:** Use the platform's maintained crypto library and high-level APIs: authenticated encryption
(AES-GCM, ChaCha20-Poly1305), HMAC for integrity, current signature schemes, TLS for transport. No
ECB, no unauthenticated CBC, no DES/3DES/RC4, no MD5 or SHA-1 for security, no `h(key || message)` as a
MAC (SE §5.1, p.193; SE §5.5, pp.222–227; SE §5.6.1–5.6.2, pp.230–231; ONET ch7, pp.144–145, 161,
168–170; SE §19.4.1, p.687 — blinded, constant-time implementations).
**Why:** Most crypto failures are in the use, not the cipher: ECB leaks patterns, unauthenticated
modes are malleable, home-made constructions break (SE p.249).
**Violation:** `AES/ECB`, `Cipher.getInstance("DES")`, `createCipher` (deprecated, no IV),
`hashlib.md5` for tokens or signatures, hand-written encryption helpers, a hard-coded key and salt in
source (ONET ch7, p.171).

### A15 — Randomness and uniqueness are security properties
**Says:** Tokens, IDs that act as secrets, salts, IVs and nonces come from a CSPRNG; a nonce or IV is
never reused under the same key; keys are diversified per purpose and per device rather than shared
(SE §5.5.3, p.225; SE §5.7.9, p.249; SE §4.5–4.6, pp.182–183 — never reuse keys across applications;
SE §19.4.2, pp.689–690).
**Why:** A reused keystream exposes the XOR of two plaintexts; a token from `Math.random()` is
predictable; one key in many places breaks everywhere at once.
**Violation:** `Math.random()`, `rand()`, `java.util.Random`, Python `random` for tokens; static or
counter-reset IVs; one signing key for sessions, reset links and webhooks.

### A16 — Fail indistinguishably
**Says:** Different failures must look the same to the caller: one error for bad padding and bad MAC,
one message for unknown user and wrong password, constant-time comparison of secrets and MACs, no
secret-dependent timing (SE §5.5.2, pp.224–225; SE §19.4.1, p.687; SE §20.5.3, pp.714–715; ONET ch3,
p.72).
**Why:** Padding oracles broke SSL, IPsec and TLS for years; a distinguishable login error enumerates
accounts.
**Also:** "Exists but not yours" answered differently from "doesn't exist" (403 vs 404, different body length or timing) enumerates objects and accounts; timing headers such as `X-Response-Time` and distinct login errors do the same (HAPI ch3, pp.82, 91; ch10, pp.254–255).
**Violation:** `==` on HMACs or tokens; "invalid padding" vs "invalid signature"; reset or login
responses that differ for existing accounts; error timings that reveal which check failed.

### A17 — Secrets live outside code, outside images and outside logs
**Says:** Keys, passwords, connection strings and tokens are read at runtime from a secrets store or
the platform's protected configuration, scoped per environment, rotated, and kept apart from the
data they protect; decryption rights are not general admin rights (ONET ch7, pp.173–175; ONET ch6,
pp.134–136; SE §5.7.6.1, pp.244–245 — protect signing keys; SE §3.4.9, pp.155–156).
**Why:** A secret in source is in every clone, fork, build log and backup; it can't be rotated
without a deploy and can't be revoked from history.
**Also:** A key shipped to a client is public — in a JavaScript bundle, a mobile app or a query string — and Base64 hides nothing (HAPI ch2, pp.71–72; ch6, p.168; ch15, pp.340–341; GitHub history and pull requests leak keys too, ch6, pp.161–164). Keep publishable and secret keys apart; webhooks are public URLs, so verify their signature or call back to the provider; test and production never share credentials (WSD ch14, pp.166–167).
**Violation:** credentials in `appsettings.json`, `application.properties`, `settings.py`, `.env`
committed, Dockerfiles or CI YAML; one key for every environment; signing keys on build servers;
`<machineKey>` hard-coded.

## Part E — Configuration and errors

### A18 — Production defaults fail closed
**Says:** Production configuration is a separate, reviewed artefact: debug and tracing off, sample
and admin endpoints removed or protected, default credentials changed, framework protections on, and
errors in any security check deny rather than allow (ONET ch6, pp.122–134; SE §12.4.2, pp.476–477 —
debug backdoors and fail-open back ends; SE §3.2.5.3, p.126 — defaults are the control).
**Why:** ONET's tracing endpoint exposed session state and secrets traced by developers (ch6,
pp.126–129); `debug=true` changes behaviour and is remotely detectable (pp.130–132).
**Violation:** `DEBUG=True`, `<compilation debug="true">`, `app.run(debug=True)`, `NODE_ENV` not
`production`; `trace enabled localOnly="false"`; Spring actuator `include=*`; `ALLOWED_HOSTS=['*']`;
`catch { return true; }` in an authorisation path.

### A19 — Errors don't leak
**Says:** Users get a generic error page; diagnostics go to server-side logs. No stack traces,
framework versions, file paths, SQL text or internal hostnames in responses (ONET ch6, pp.121–124;
ONET ch1, p.31; LWD 031.3, pp.45–48).
**Why:** A verbose error maps the schema for an injection attack and fingerprints the framework for
known exploits (ONET ch6, pp.121–125).
**Violation:** `customErrors mode="Off"`; default framework error handlers in production; exception
messages returned in API bodies; `X-Powered-By`, `Server` and version headers (LWD 035.2, p.311 shows
`X-Powered-By: Express` in its own output).

### A20 — Transport and browser protections are on by default
**Says:** Every authenticated page and API is HTTPS-only with HSTS; cookies are `Secure` by default;
HTTP clients verify certificates; responses carry a baseline of browser protections — CSP,
`X-Content-Type-Options: nosniff`, framing control, `Referrer-Policy`; sensitive data never travels in
URLs (ONET ch9, pp.205–234; LWD 031.3, pp.42–43; SE §5.7.4–5.7.5, pp.241–244; LSE 022.2, pp.78–85).
**Why:** TLS only at login leaks the session cookie afterwards (ONET ch9, pp.211–214); the first HTTP
request is the SSL-strip window HSTS closes (pp.223–229).
**Also:** HSTS needs a `max-age` longer than the usual gap between visits and `includeSubDomains` so sibling hosts can't plant cookies (TW ch16, pp.270–271). The browser protections are developed in Part H.
**Violation:** mixed content; `verify=False`, `rejectUnauthorized: false`,
`CURLOPT_SSL_VERIFYPEER=false`, custom trust-all managers; no HSTS; secrets in query strings
(`method="get"` on a login form); `target="_blank"` without `rel="noopener"` on user-supplied links.

## Part F — Dependencies and licences

### A21 — Dependencies are your code
**Says:** Every third-party component ships with your product and its vulnerabilities are yours.
Pin versions with a lockfile; scan them continuously and fix known-exploited ones first; keep runtimes
and libraries inside their support window; prefer maintained projects; budget for any fork you keep;
verify integrity (lockfile hashes, SRI for CDN assets) (ONET ch6, pp.115–120; LOS 054.3, pp.189–191 —
SBOM and SCA; LOS 055.2, pp.222, 224 — EOL, LTS, 0.x carries no compatibility promise; LOS 055.3,
p.237 — forks; SE §27.5.4, p.1020 — most applications ship vulnerable open-source libraries).
**Why:** The cheapest attack on an application is a published CVE in a library it forgot it had.
**Violation:** no lockfile; ranges like `^`, `~`, `*`, `latest`; `npm install <pkg>` with no pin
(LWD's examples throughout); dependencies past EOL; 0.x libraries in production paths; abandoned
single-maintainer packages; vendored copies far behind upstream; CDN scripts without `integrity`.

### A22 — Licences are obligations triggered by how you ship
**Says:** Unlicensed code is all-rights-reserved. Keep an inventory of every component's licence
(an SBOM in SPDX or CycloneDX); know what each obligation is triggered by — distribution, and for
AGPL network use; keep notices; offer source where copyleft requires it; check compatibility in both
directions before release (LOS 052.1, pp.65, 67, 69; LOS 052.2, pp.83–87; LOS 052.3, pp.96–100; LOS
054.3, pp.185–191).
**Why:** A copyleft component in a distributed proprietary product, or AGPL in a hosted service, is a
legal finding that no patch fixes; stripped notices breach even permissive licences.
**Violation:** no licence report; GPL/AGPL components in closed-source distributables or SaaS back
ends without a decision; Apache-2.0 combined with GPL-2.0-only; NOTICE files missing from release
artefacts and images; code pasted from forums with no licence.

## Part G — Logging

### A23 — Log the security events, somewhere they survive
**Says:** Authentication successes and failures, access denials, privilege and role changes, admin
actions, password and MFA changes, and input-validation failures are logged with who, what, when and
from where; logs leave the host to a store the application can't rewrite; someone is alerted on the
patterns that matter (SE §6.2.3, p.259 — keep audit logs out of reach of the admin they audit; SE
§12.2.3, p.451 — an append-only audit trail sufficient to reconstruct each action; SE §21.4.2,
pp.757–760; Practice: OWASP A09:2021).
**Why:** Without these events a breach is noticed by its victims, and the investigation can't tell
where it began.
**Violation:** no logging around login, authorisation failures or admin actions; logs only on the
local disk of an ephemeral container; no alert on bursts of failed logins or denials.

### A24 — Never log what an attacker would want, and never let input forge a log line
**Says:** Passwords, tokens, session IDs, keys, full card numbers and unnecessary personal data stay
out of logs and error reports — remembering that users type passwords into username fields; encode
or strip line breaks and control characters from logged input (SE §3.4.9, pp.155–156; ONET ch6,
pp.124, 129 — tracing and e-mailed stack traces that carried secrets; LSE 025.3, pp.298–299).
**Why:** Logs are copied, shipped and retained far more widely than the data they describe; a secret
in a log has the log's access control, not the secret's.
**Violation:** request bodies or headers logged wholesale; `Authorization` headers in access logs;
failed-login logs recording the attempted password; `logger.info("user " + input)` with no newline
handling.

## Part H — The browser trust boundary

The browser is a second interpreter of everything the server sends, with its own rules for what
counts as the same origin, what a response *is*, and what another site may read. Most of these
principles exist because the browser's rules are looser or stranger than developers assume (TW,
throughout; each chapter ends with a security-engineering cheat sheet).

### A25 — Declare the type and charset of every response
**Says:** Every response carries an explicit `Content-Type` with `charset`, set by the server, plus
`X-Content-Type-Options: nosniff`; user-controlled bytes never decide the type or start the body
(TW ch13, pp.220–225, 228–231, 234).
**Why:** Browsers sniff HTML out of a missing, malformed or "unrecognised" type, including
`text/plain`, `octet-stream` and JSON; a path suffix can steer the heuristic; an undeclared or
misspelt charset lets UTF-7 (`+ADw-script+AD4-`) or a multibyte lead byte smuggle markup past the
encoder; a byte-order mark can override the header.
**Violation:** responses without a charset; `Content-Type` taken from the request, an upload's part
header or a database column; user content served as `text/plain`/`octet-stream`; no `nosniff`;
`charset=UTF8` typos.

### A26 — User files are inert downloads from somewhere else
**Says:** Serve user-supplied files with `Content-Disposition: attachment`, a server-chosen file name
and a type that matches the content, from a separate sandbox origin or object store outside the
application's cookie scope; store them without execute permission, renamed, away from code; check
content after upload because the client's declared type is spoofable and polyglots exist (TW ch13,
pp.225–227, 234; TW ch8, p.160; WSD ch6, pp.90–91).
**Why:** A file the browser renders inline on your origin is script on your origin. `attachment` is
ignored when the file is loaded by `<img>` or `<script>`, so the type still has to be right.
**Violation:** uploads under `public/`, `static/`, `wwwroot/`; downloads served `inline` or without
`Content-Disposition`; the client's file name reused; HTML, SVG or PDF served as-is from the app origin.

### A27 — Nothing from the request reaches a header unencoded
**Says:** Strip CR, LF and NUL — a lone CR included — and encode control characters in any value
placed into a response header, cookie, `Location` or mail header; percent-encode or Base64 user data
in cookies (TW ch3, pp.67, 69–73, 89).
**Why:** Header injection splits responses, sets cookies and poisons caches; browsers split duplicate
headers inconsistently, so even a constrained injection works somewhere; quotes, commas and bytes
above 0x7F change a cookie's meaning; semicolons and NULs truncate `Content-Disposition` names.
**Violation:** `setHeader`/`header()`/`response.headers[...]`/`AddHeader` or `redirect()` with request
data; `Set-Cookie` or `Location` built by concatenation.

### A28 — Parse a URL once, with a real parser, and decide on the parsed parts
**Says:** Every URL the code accepts, redirects to, fetches or renders is parsed by the standard
parser, made absolute, and judged on its parsed scheme and host: allow-list schemes, match hosts on the
right-hand side at a dot boundary, convert international names to Punycode; never decide with a
regex or substring check on the raw string (TW ch2, pp.51–53, 56–62).
**Why:** Browsers treat `\` as `/`, `//host` and `http:host` as relative, decode `%65` in host names,
split `@`, `;` and control characters differently, and accept `java\tscript:`; `evilexample.com`
passes an `endsWith("example.com")` check; homograph host names look identical.
**Violation:** `startsWith("/")`, `.includes(host)`, `.endsWith("example.com")`, `indexOf` on URLs;
scheme blacklists for `javascript:`/`data:`; one parser for the check and another for the use;
`href` bound to request data. Redirect and fetch destinations are also A5.

### A29 — Pin every cross-origin message channel
**Says:** `postMessage` names an explicit target origin; a receiver compares `event.origin` for exact
equality with a known origin before reading the data; `document.domain` is never set; `window.name`
and `location.hash` are not message buses (TW ch9, pp.165–167, 184; TW ch11, pp.199–200).
**Why:** `document.domain` ties your page to your weakest sibling host; `indexOf(".example.com")`
matches `www.example.com.evil.net`; any page that can navigate your frames can write their name and
hash.
**Violation:** `postMessage(…, "*")`; message listeners with no origin check, or with
`indexOf`/`includes`/regex checks; message data into `innerHTML` or `eval`.

### A30 — CORS grants reading; it protects nothing
**Says:** Treat a CORS policy as permission for named origins to *read* responses: allow-list exact
origins, never reflect `Origin`, never allow `null`, never combine credentials with a wildcard, and
send `Vary: Origin`. The request itself is sent either way (TW ch16, pp.258–261, 275; TW ch9,
pp.169–170).
**Why:** "Simple" cross-origin requests reach the server regardless of the policy — only the response
read is gated — so CORS is not a CSRF defence; a reflected origin with credentials hands every site
your users' data.
**Violation:** `Access-Control-Allow-Origin` echoing the request; `cors({origin: true, credentials:
true})`; `allowedOriginPatterns("*")`; `CORS_ALLOW_ALL_ORIGINS`; suffix matching on origins.

### A31 — Cookie scope is the registrable domain, and sibling hosts can write to it
**Says:** Session and authentication cookies are host-only (no `Domain` attribute, `__Host-` prefix);
`Path` is convenience, not isolation; `Secure` and `HttpOnly` restrict reading, not writing; anything
on a sibling subdomain can overwrite your cookies, so no sibling hosts less-trusted code, no wildcard
DNS points into your domain, no `localhost.<domain>` record resolves to 127.0.0.1, and CSRF tokens are
bound to the session rather than double-submitted (TW ch9, pp.171–175, 181, 184; TW ch16,
pp.270–271; WSD ch14, p.168).
**Why:** Cookie injection from a vulnerable or abandoned subdomain fixes sessions and forges
double-submit tokens; a dangling DNS record lets someone else host content on your name.
**Violation:** `Domain=.example.com` on a session cookie; no `__Host-` prefix; CSRF checks that only
compare a cookie to a form field; DNS `CNAME`s pointing at deprovisioned services.

### A32 — Deny framing by default; sensitive actions need more than one click
**Says:** Send `Content-Security-Policy: frame-ancestors` (with `X-Frame-Options` only as a fallback);
don't rely on script frame-busters; sandbox untrusted frames without granting `allow-scripts` and
`allow-same-origin` together; open other sites with `noopener`; require a deliberate second step or
re-authentication for settings and payments (TW ch11, pp.196–203, 208; TW ch14, pp.245–246; TW ch16,
pp.267–269; WSD ch16, pp.186–187; WSD ch8, p.107).
**Why:** A framed page can be overlaid and clicked through (clickjacking); frames you own can be
navigated by the page around them; a window you opened can navigate its opener; keystrokes and drags
can be redirected between frames.
**Violation:** no `frame-ancestors`; `top.location` frame-busting scripts as the only defence;
`sandbox="allow-scripts allow-same-origin"`; `window.open`/`target="_blank"` without `noopener` on
untrusted links; one-click destructive actions.

### A33 — User-specific data is never loadable cross-site as script or style
**Says:** Responses carrying a user's data can't be included by another site's `<script>` or
`<link rel=stylesheet>`: require a token or custom header for them, serve them with their real type
and `nosniff`, and don't offer JSONP; if a callback name is unavoidable, allow-list it (TW ch6,
pp.126–128, 137; TW ch11, pp.203–204; TW ch16, p.267).
**Why:** Script and style includes send cookies and ignore the same-origin policy (cross-site script
inclusion, XSSI); a free-form JSONP callback also lets an attacker call any function and defeats CSP
host allow-lists.
**Violation:** `req.query.callback` reflected; cookie-authenticated GET endpoints returning
JavaScript or JSON with no token; user data served as `application/javascript` or `text/html`.

### A34 — Third-party code is inside your trust boundary
**Says:** Every third-party script, stylesheet, font, widget and ad runs with your page's authority:
prefer self-hosting, require HTTPS, pin CDN assets with Subresource Integrity (`integrity` plus
`crossorigin`), sandbox ad frames, inventory tag-manager content, and retire DNS records pointing at
services you no longer own (TW ch5, p.115; TW ch6, p.137; TW ch11, p.205; WSD ch14, pp.162,
168–171).
**Why:** An analytics or tag-manager script reads everything typed into the page; a compromised CDN
or a taken-over subdomain serves code as you.
**Violation:** `<script src="http://…">`; off-origin scripts or stylesheets without `integrity`;
unsandboxed ad iframes; `CNAME`s whose target answers "not found".

### A35 — Caches and Host headers are security inputs
**Says:** Authenticated and personalised responses send `Cache-Control: no-store` (not merely
`no-cache`) and `Vary` on what they differ by; links, e-mails and redirects are built from configured
host names, never from `Host`/`X-Forwarded-Host`; the server accepts only its own host names (TW ch3,
pp.68–70, 80–82; TW ch12, p.211).
**Why:** GET responses with 200 or 301 can be cached implicitly and replayed to the next user of a
shared cache or the back button; a poisoned cache persists; an app that trusts `Host` writes the
attacker's domain into password-reset links.
**Violation:** authenticated pages without `no-store`; CDN rules caching `/account` or `/api`;
`request.get_host()`/`req.headers.host` used to build URLs; `ALLOWED_HOSTS=['*']`; a catch-all
virtual host serving the app.

### A36 — Filter HTML by parsing, allow-listing and re-serialising
**Says:** When user HTML is allowed, parse it with a real parser, keep only allow-listed elements and
attributes, and serialise the result fresh; never strip or regex markup; quote every attribute;
decode entities before deciding anything; reject user-supplied `id` and `name` (they collide with
DOM properties); never place user data in comments or `<!`/`<?` blocks (TW ch4, pp.95–101, 107–108).
**Why:** Browsers repair broken markup in ways a regex can't predict; DOM-based XSS from
`location.hash` never reaches the server, so server-side filters and logs don't see it (WSD ch7,
pp.99–101).
**Violation:** `strip_tags`, regex sanitisers, home-made `sanitize()`; unquoted attribute templates;
user-set `id`/`name`; concatenating after sanitising.

### A37 — Network position is not authentication
**Says:** Internal tools, intranet apps and developer servers authenticate users, use HTTPS with
`Secure` cookies, validate `Host`, and protect state changes against CSRF — because the victim's
browser sits inside the network and will send whatever an outside page asks (TW ch12, pp.211–213,
217; TW ch3, p.66).
**Why:** DNS rebinding and CSRF reach routers and admin consoles through the browser; services that
aren't HTTP can be fed HTTP requests whose replies the browser renders.
**Violation:** "no auth, it's internal"; authentication by source IP or VPN alone; development
servers bound to `0.0.0.0` with no `Host` check.

### A38 — Don't let your domain launder abuse
**Says:** Publish SPF, DKIM and a DMARC policy for every domain that sends mail; allow no open
redirect (A5, A28); allow-list server-side fetch destinations; deny framing (A32) — so your name
can't be borrowed for phishing, spam or attacks on others (WSD ch16, pp.182–188, 199–200; Practice:
DMARC).
**Why:** A domain that forwards, frames or sends on anyone's behalf becomes a tool in someone else's
attack, and its reputation pays.
**Violation:** no `v=spf1` record or `+all`; no DKIM selector; no `_dmarc` record or `p=none`
indefinitely; redirect and fetch sinks without allow-lists.

### A39 — Bound what each request can consume
**Says:** Cap body, header and upload sizes, connection and read times, archive expansion (size and
ratio), XML entity expansion, page sizes and regex complexity; move long work to queues; put static
content behind a CDN (WSD ch17, pp.193–196; WSD ch15).
**Why:** One request that makes the server unzip a bomb, expand entities or backtrack a regex takes a
worker for everyone.
**Violation:** no `client_max_body_size`/body-parser `limit`; default timeouts; `extractall` without
size, ratio and path checks (also path traversal); `limit` taken from the query unbounded; nested
quantifiers over input. Per-identity rate limits are A42.

## Part I — APIs

An API is the same application with the browser removed — which means every rule the UI used to
enforce now has to hold at the endpoint, for every version, method and field. HAPI is written from
the tester's side; the principles below are its defender's reading.

### A40 — Keep a living inventory of every API surface, and give all of it the same controls
**Says:** Every host, version (`/v1`, `/v2`), environment (`/test`, `/uat`, `beta`), method and
operation is either in the inventory — reconciled from code routes, the OpenAPI/GraphQL schema, the
gateway and DNS — with the full control set, or retired with `410 Gone` (HAPI ch3, pp.93–94; ch6,
p.159; ch9, pp.242–243, 247–249).
**Why:** Old and shadow versions keep the bugs the new one fixed: in the book's lab the v3
password-reset code was attempt-limited and v2 was not; host names like `legacy-api` and published
changelogs tell an attacker which version to try.
**Violation:** routers still mounted for old versions; routes in code that aren't in the spec (shadow
APIs); `deprecated: true` operations still served; versions with different `security` blocks;
several `servers` including test hosts.

### A41 — The server decides which properties leave and which can be written, per role
**Says:** Responses are built from per-role response shapes (DTOs, serialiser field lists, schema
`readOnly`) — never by serialising the stored object and trusting the client to hide fields; requests
bind only allow-listed writable properties (`writeOnly`, `additionalProperties: false`), with values
validated server-side (HAPI ch3, pp.86, 89–90; ch7, pp.200–201, 205–206; ch11, pp.265–275; Practice:
OWASP API3:2023 Broken Object Property Level Authorization).
**Why:** A user-facing endpoint returned admins' e-mail addresses and MFA status alongside the data
the app displayed; leaked IDs from one response fed object-level attacks on another; an extra `admin`
property upgraded an account; a product endpoint accepted a negative price.
**Violation:** `res.json(user)`, `return Ok(entity)`, `fields = '__all__'`, an entity as
`@RequestBody`, `Object.assign(model, req.body)`; one schema for read and write; `role`, `isAdmin`,
`balance`, `price` or `org` in create/update schemas.

### A42 — Meter consumption against an identity the client can't choose
**Says:** Rate, size and cost limits are keyed on the authenticated principal and the target
account, applied to the normalised route template across every version and alias, with documented
`429`/`Retry-After`; page sizes and batch counts have maxima; limits protect money and cost as well as
availability (HAPI ch0, pp.36–37; ch3, pp.85, 87; ch13, pp.306–307).
**Why:** Limits fall to path variants, case changes, extra parameters and spoofed `X-Forwarded-For`;
an unlimited one-time-code endpoint is a brute-force tool; an unbounded `pageSize` is a scraper's
dream.
**Violation:** limiter keyed on a forwarding header or the raw path; `trust proxy` with no proxy;
`limit`/`first`/`pageSize` without a maximum; no limit on login, OTP, reset or search; GraphQL with no
depth, complexity or batching limits (Practice).

### A43 — Discovery artefacts are gated like the API they describe
**Says:** Documentation, `openapi.json`, Swagger UI, GraphQL introspection and playgrounds are off in
production or behind the same authentication as the API; nothing is gated by a client-settable cookie
or header; prose that says "admin only" or "do not use" is a rule the code must enforce, not the
enforcement (HAPI ch3, p.95; ch14, pp.317–321, 324; ch15, pp.341–343).
**Why:** Public admin documentation plus one exposed token gave a full takeover in a real case; a
playground toggled by a Base64 cookie is toggled by anyone; introspection hands over the whole
schema.
**Violation:** `/docs`, `/swagger`, `/openapi.json` mounted unconditionally; `introspection: true` or
GraphiQL in production; documentation describing restrictions the handlers don't check.

---

## Where the books are dated

The principle stands; the mechanism has moved on. Correct these when reusing an example:

| Book says | Use now |
|---|---|
| ONET: salted SHA as the minimum for passwords (ch7, p.160) | Argon2id, scrypt, bcrypt or high-iteration PBKDF2 (A8) — ONET itself adds that SHA-1 hashing is insufficient (p.168) |
| ONET: secret questions in the reset flow (ch3, pp.71–72) | A second factor; the tokenised, single-use, expiring link and "no auto-login" rules still hold |
| ONET: AES example without an authenticated mode (ch7, pp.170–171) | AEAD (GCM) with keys from a key service (A14) |
| ONET: request validation and browser XSS filters as defences (ch2, pp.43–44, 56–57) | Context-aware autoescaping templates plus CSP (A3, A20) |
| ONET: CSRF tokens only; predates `SameSite` (ch5) | Framework anti-forgery tokens plus `SameSite` cookies (A12) |
| ONET: Referer check for redirects (ch10, pp.244–246) | Supplementary at best; allow-list or indirect IDs (A5) |
| ONET: HSTS as a draft with a short `max-age` (ch9, p.228) | HSTS with a long `max-age`, `includeSubDomains`, preload where possible; TLS 1.2/1.3 only |
| ONET: `autocomplete="off"` on login forms (ch3, p.74) | Allow password managers; modern browsers ignore it on login fields |
| LWD: a hidden field is something the visitor can't manipulate (032.4, p.138) | Anyone can edit it; never trust it (A11) |
| LWD: GET suits small forms (032.4, pp.140–141) | Never for credentials, tokens or state changes (A12, A20) |
| LWD: `npm install <pkg>` with no version (throughout) | Lockfile and pinned versions (A21) |
| LOS: Apache-2.0 licensees must release unmodified parts under Apache-2.0 (052.3, pp.99–100) | Overstated — verify against the licence text before turning it into a rule |
| TW: `X-Frame-Options` as the framing control (ch11) | CSP `frame-ancestors`; keep XFO only as a fallback (A32) |
| TW: `X-XSS-Protection: 1; mode=block` (ch16, p.275) | Retired — browsers removed the auditor; send `0` or nothing and rely on escaping and CSP (A3) |
| TW: CSP as `X-Content-Security-Policy` with host allow-lists (ch16) | `Content-Security-Policy` with nonces or hashes and `'strict-dynamic'`; host allow-lists are bypassable through JSONP and open CDNs (A20, A33) |
| TW: plug-in security — Flash, Java applets, Silverlight, `crossdomain.xml` (ch8, ch9) | Gone; the principle (every embedded runtime is in your trust boundary) survives in A34 |
| TW: IE-specific sniffing, URL and origin quirks | Browsers now follow the WHATWG URL, HTML, MIME-sniffing and Fetch standards; declare types and parse URLs once anyway (A25, A28) |
| TW: cookies before `SameSite`, `__Host-` and the Public Suffix List (ch9) | Use them — but a sibling subdomain can still write cookies, so A31 stands |
| TW: cheat sheet header `X-Content-Options` (ch13, p.234) | Typo — the header is `X-Content-Type-Options` (correct on p.225) |
| WSD: double-submit cookie CSRF tokens (ch8, pp.105–106) | Bind the token to the session; a sibling host can forge a double-submit pair (A31) |
| WSD: `SameSite=Lax` as "GET only" (ch8, p.107; ch10, p.127) | Lax sends cookies on top-level navigations; treat it as a layer, not the CSRF defence |
| WSD: 301 temporary, 302 permanent (ch16, p.185) | Reversed — 301 is permanent, 302 temporary |
| WSD: CSP host allow-lists (ch7) | Nonces/hashes with `'strict-dynamic'` |
| WSD: hiding versions and banners as defence (ch12, pp.142–144) | Hygiene, not a control — patch the library (A11, A19) |
| WSD: `imghdr` for upload type checks (ch6, p.91) | Removed in Python 3.13; use a maintained content-detection library and re-encode images (A26) |
| WSD: TLS terminated at the edge, plaintext inside (ch13, p.154) | Internal TLS where the threat model or regulation asks for it (A20) |
| TAOSSA: DREAD scoring for threats (ch2) | Weight exposure against damage, but use the severity taxonomy in scoring.md |
| TAOSSA: CBC as the only appropriate block mode; salts must be secret (ch2, pp.45–48) | AEAD (GCM, ChaCha20-Poly1305); salts are unique, not secret (A8, A14) |
| TAOSSA: DES, MD5 and SHA-1 in examples (ch2) | AES, SHA-256/SHA-3, HMAC; no MD5/SHA-1 for security (A14) |
