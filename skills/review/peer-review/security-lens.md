# Security Lens — The Pass Every Diff Gets (Lens L)

> A generalist reviewer's job on security is narrower than an audit and never optional. Ask three
> questions of every change. Does it let untrusted data reach an interpreter? Does it act without
> checking who's asking? Does it make the attack surface larger? Then know when to call the
> specialist. Page numbers are PDF pages of the *OWASP Code Review Guide* v2 (the printed page is
> the PDF page − 1). See [theory.md](theory.md).
>
> The deep review, with an endpoint inventory, nine domains, a score and a gate, is
> `appsec`. This lens finds what a diff introduces and escalates
> what it can't settle.

---

## 1. Context first: three facts that set the depth

Before reading a line for security, write down three facts (OCR p.21, p.26–28):

1. **Who can reach the changed code?** Anonymous internet, any authenticated user, an admin, an
   internal service, or only a batch job.
2. **What data does it touch?** Public, internal, personal, credentials, payment, regulated.
3. **Which trust boundary does it cross?** Browser to server, server to database, to a third party,
   service to service, tenant to tenant.

Reachability and data class move a finding's severity, so the anchors in [report.md](report.md)
read them. When you can't tell from the code, say so and grade against the worse case.

---

## 2. The diff checklist

Each item is a question answered from the changed lines and whatever they reach. A grep hit is a
candidate, not a finding: trace it from source to sink first (OCR p.18, p.43).

### Untrusted data reaching a sink
- [ ] **Trace every new or changed input to its sinks.** Inputs are parameters, headers, cookies,
  bodies, files and their metadata, environment, message payloads, service responses, and data
  read back from storage (the second-order path). Sinks are queries, commands, templates/HTML/DOM,
  file paths, redirects, headers, outbound requests, deserialisers and logs. Every path needs the
  validation or encoding that suits its sink (OCR p.18, p.33–35).
- [ ] **Queries.** No SQL, HQL, NoSQL or ORM raw query built by concatenation or interpolation with
  request-derived values. That includes conditionally assembled `WHERE` clauses and `ORDER BY`
  columns, which need an allow-list because they can't be bound (OCR p.45–53).
- [ ] **Commands, templates and evaluation.** No shell string built from input (`exec`, `system`,
  `subprocess(..., shell=True)`). No `eval`, `new Function`, string timers, or template source built
  from input (OCR p.52, p.76).
- [ ] **Output.** Encoding is right for the context: HTML body, attribute, JS string, URL, CSS. No
  `innerHTML`, `document.write`, `.html()`, `dangerouslySetInnerHTML`, `|safe` or `{!! !!}` fed by
  data. Framework protections stay on (OCR p.72–77, p.191).
- [ ] **Paths, redirects, outbound requests.** File paths, redirect targets and fetched URLs come
  from an allow-list or an indirect ID, never raw input. Header values are stripped of CR/LF
  (OCR p.152–153). SSRF is missing from the guide, but treat a server-side fetch of an
  input-derived URL as the same class.
- [ ] **Parsers and deserialisers.** No native deserialisation of input (`pickle`, `ObjectInputStream`,
  `BinaryFormatter`, `unserialize`, unsafe YAML). XML parsers have external entities off. This is
  an **escalation** trigger (OCR p.210–211).

### Who is asking
- [ ] **New endpoint, action, resolver, consumer or webhook.** Does central, default-deny
  authorisation cover it? The check runs before the business logic, on the server, never in the
  view or client JS. Audit every new `[AllowAnonymous]`, `@PermitAll`, `permission_classes = []`,
  or route outside the auth middleware (OCR p.135–139).
- [ ] **Object loaded by an ID from the request.** Is ownership or tenancy checked on the server?
  A parameterised query is not an authorisation check (OCR p.79–81).
- [ ] **Binding the request onto a model** with privileged fields (`role`, `isAdmin`, `price`,
  `tenantId`, limits). Binding must be allow-listed or go through a DTO (OCR p.80–82).
- [ ] **Code stops after a redirect, forward or failed check.** A `return` is present, and the
  forwarded target enforces its own authorisation (OCR p.153, p.197).
- [ ] **State-changing operations** are non-GET and CSRF-protected when cookies authenticate them
  (OCR p.142–145).

### Secrets, crypto, sessions
- [ ] **No secret in the diff.** Look for keys, tokens, passwords and connection strings in code,
  config, fixtures, tests and CI files. Record the kind and the location, **never the value**, and
  recommend rotation, because removing it from the diff doesn't remove it from history (OCR p.105,
  p.199).
- [ ] **No sensitive data where it leaks.** No secrets or personal data in URLs, query strings,
  client storage, error responses, analytics or logs (OCR p.121, p.133).
- [ ] **Crypto is the platform's, used correctly.** No MD5, SHA-1 or DES for security. No
  non-cryptographic random for tokens, IDs or salts. No hand-rolled hash, cipher or "encryption" by
  base64 or XOR. Passwords use an adaptive hash (argon2, scrypt, bcrypt). The guide's salted-SHA-2
  example is dated and must not be followed (OCR p.123–130, p.210).
- [ ] **Sessions and cookies.** `Secure`, `HttpOnly` and `SameSite` set. The ID rotates on login and
  privilege change. Logout really ends the session. No IDs in URLs (OCR p.66–70).

### Errors and logs
- [ ] **Failures fail closed.** No stack traces, exception messages, internal paths or SQL in
  responses. Errors don't fall through to "allow" (OCR p.164–174).
- [ ] **Logs.** No passwords (failed ones included), tokens, session IDs, keys or sensitive personal
  data. User data in logs is stripped of CR/LF so it can't forge entries (OCR p.60, p.162–163).
  Security-relevant events get logged: authentication failures, denials, privilege changes, admin
  actions.

### Attack surface (OCR p.132–133)
- [ ] Does the change add a port, input, unauthenticated function, or role?
- [ ] Does it move something from HTTPS to HTTP?
- [ ] Does it add an expensive operation an outsider can script (file writes, SMS or email sends,
  heavy queries) with no rate limit?
- [ ] Does it store new personal data? Is it needed?
- [ ] Does it add a security module that duplicates the central one, such as its own hashing, its
  own auth check, or its own sanitiser?
- [ ] Do uploads have authentication, size limits per file and per user, type checks by content,
  and storage outside the web root?
- [ ] **New dependency.** Is it maintained, current, minimal for the need, from the expected
  registry, with a lockfile entry? Did someone check it for known vulnerabilities (OCR p.148–149)?
- [ ] **Browser channels.** `postMessage` handlers check origins exactly (no `*`). CORS doesn't
  reflect arbitrary origins with credentials. WebSockets use `wss://` and authorise at the app
  level (OCR p.155–158).

---

## 3. Grep table: where to look first

Run these on the **added lines** (`git diff -U0 <base>...HEAD | grep '^+'`) to find candidates fast,
then trace each one. The table compiles the guide's code-crawling lists (OCR p.206–218), extended to
the stacks it doesn't cover.

| Concern | Patterns (any stack) |
|---|---|
| Request sources | `getParameter`, `getHeader`, `Request.Query`/`Form`/`Headers`/`Cookies`, `$_GET`/`$_POST`/`$_REQUEST`, `req.query`/`req.body`/`req.params`, `request.args`/`request.form`/`request.json`, `location.hash`/`search`, `document.referrer`, `localStorage` |
| Query building | `createStatement`, `execute(`, `executeQuery`, `createQuery(`, `CreateSQLQuery`, `ExecuteQuery`, `raw(`, `.query(` + string concatenation or interpolation (`+ "`, `f"`, `${`, `%s`, `.format(`) near `select`/`insert`/`update`/`delete`/`where`/`order by` |
| Commands | `Runtime.exec`, `ProcessBuilder`, `system(`, `popen`, `exec(`, `spawn(`, `shell=True`, `os.system`, backticks |
| Dynamic code | `eval(`, `new Function`, `setTimeout("`, `setInterval("`, `exec(` (Python), `Template(` from input |
| DOM and HTML output | `innerHTML`, `outerHTML`, `document.write`, `.html(`, `dangerouslySetInnerHTML`, `v-html`, `|safe`, `{!!`, `Html.Raw`, `<%=`, `mark_safe` |
| Redirects and headers | `sendRedirect`, `Response.Redirect`, `redirect(`, `header("Location`, `res.redirect`, `window.location =`, `setHeader`, `addHeader` |
| Files | `File(`, `FileInputStream`, `open(`, `readFile`, `sendFile`, `include`, `require(` with a variable, `getRealPath`, `path.join` with input |
| Outbound requests | `fetch(`, `axios`, `requests.get`, `HttpClient`, `urlopen`, `curl_exec` with an input-derived URL |
| Deserialisation | `ObjectInputStream`, `BinaryFormatter`, `pickle.load`, `yaml.load(` (without SafeLoader), `unserialize(`, `Marshal.load`, `XmlReader` with DTD processing |
| Crypto and random | `MD5`, `SHA1`, `DES`, `RC4`, `ECB`, `Random(`, `Math.random`, `random.random`, `rand(` used for tokens, `base64` presented as encryption |
| Auth bypass markers | `AllowAnonymous`, `PermitAll`, `permitAll()`, `@csrf_exempt`, `skip_before_action`, `verify=False`, `rejectUnauthorized: false`, `InsecureSkipVerify` |
| Secrets | `password`, `passwd`, `pwd`, `secret`, `token`, `api_key`, `apikey`, `private_key`, `BEGIN .* PRIVATE KEY`, `AKIA`, `connectionString`, `jdbc:` |
| Errors and logs | `printStackTrace`, `e.message`/`err.stack` in responses, `catch {}`/`except: pass`, `On Error Resume Next`, logger calls with `password`/`token`/`session` |
| Native and unsafe | `unsafe`, `native`, JNI, `strcpy`, `strcat`, `sprintf`, `gets`, `scanf`, `printf(var)` |
| Browser channels | `postMessage(`, `addEventListener('message'`, `Access-Control-Allow-Origin`, `ws://`, `credentials: 'include'` |

Bespoke business logic isn't greppable (OCR p.43). The table finds the places to read, and reading
the code is the review.

---

## 4. Escalate to appsec

Recommend `appsec` in **PR-review tier** before merge, in the report
and the handoff, when the change touches any of these (OCR p.12, p.26–27, p.62, p.84–117,
p.119–124, p.137, p.176–184, p.210–211):

- Authentication, password storage or reset, MFA, SSO or OAuth flows
- Session or token issuance, signing or validation
- The authorisation model itself: roles, policies, tenancy rules, role administration
- Cryptographic design or key management
- Payment or regulated data (PCI, health, personal data under a regulation)
- A new internet-facing entry point to a high-value module
- Framework or server security configuration: CSP, CORS policy, request filtering, TLS, trust
  levels, auth middleware order
- Native-code boundaries, and deserialisation of untrusted data
- Detection, alerting or active-defence logic

**A class, not an instance.** When a finding is a vulnerability class that probably repeats
elsewhere, such as a missing encoder in one template among many or one more concatenated query in
a codebase full of them, report the instance in the diff and recommend a codebase-wide sweep with
appsec. Enumerating every instance is an audit, not a change review (OCR p.16, p.18).

Escalation doesn't replace the finding. The instance in the diff still gets its own finding, with
severity, evidence and a fix.

---

## 5. Don't

- **Don't manufacture security findings.** A clean security pass is a valid result. Write it in
  coverage as "security lens: no untrusted-input paths, no new endpoints, no secrets", not as
  silence (OCR p.193).
- **Don't report a weakness blocked today by another control as "not a finding".** It's real. That
  control may change. Lower the severity and name the control (OCR p.15–16).
- **Don't copy the guide's dated advice:** "HtmlEncode all input" as an injection defence,
  `X-XSS-Protection`, salted SHA-2 for passwords, forced periodic password changes, or referer
  checks as CSRF protection.
- **Don't probe anything live.** This lens is static. Dynamic testing belongs to appsec, and only
  against an environment the user owns and names.
