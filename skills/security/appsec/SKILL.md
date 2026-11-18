---
name: appsec
description: Review, design, or propose application security for any stack (.NET, Java, Node, Python, PHP, Go, Ruby) — injection and input handling, authentication and sessions, access control, cryptography and secrets, configuration, dependencies and licences, logging, the browser trust boundary (content types, framing, CORS, cookie scope, URLs) and APIs (REST/GraphQL inventory, property exposure, rate limits, docs) — graded against security-engineering theory, the OWASP Top 10 and the OWASP API Top 10. Review is a static code and config review that recovers a reconciled endpoint inventory, with file:line findings and a 0–10 score with a gate; Design writes the controls a service needs (controls.md) including an authorisation matrix; Propose sequences remediation in risk order, fixing each class of bug at its shared cause. Use for repo, PR or API security reviews, OWASP audits, or designing auth. Dynamic tests only against an environment the user owns and names, never production.
---

# 🔐 appsec

Application security is the code's half of a bargain: the platform keeps attackers off the host, and
the code makes sure that **everything that does reach it is treated as data, not instructions**, and
that **every action is checked against who is asking**. Almost every application vulnerability is a
failure of one of those two — untrusted input crossing into an interpreter, or a request acting with
authority it was never given. This skill grades code against that model, designs the controls a
service needs, and sequences the fixes.

## Where this fits

Three security skills, one per layer:

- [threatmodel](../threatmodel/SKILL.md) — *what* to protect and from *whom*: assets, adversaries,
  trust boundaries, the security policy a system must enforce
- **appsec** (this skill) — whether the **code** enforces it: injection, authn/authz, sessions,
  crypto use, dependencies
- [hardening](../hardening/SKILL.md) — whether the **platform** the code runs on is locked down:
  hosts, accounts, networks, storage, backups, monitoring, governance

Neighbours outside the family: `pipelines` grades the
supply chain in CI (pinned actions, untrusted triggers, signing); `dockerfile`
builds the image. Fixes go through `tdd` with a red test first, or
`hotfix` when it's urgent. Where a finding is a design flaw rather
than a coding one — no authorisation model at all, a trust boundary in the wrong place — record it
here and hand the redesign to threatmodel.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding cites (A1–A43)
- [review-rubric.md](review-rubric.md) — per domain: 🟢 well done, 🔴 anti-patterns (what, why,
  detect, severity), checklist criteria
- [detection-signals.md](detection-signals.md) — grep/semgrep-style signals per anti-pattern, per
  stack, with confidence tags
- [design-patterns.md](design-patterns.md) — the control patterns per domain and the default for each
  trade-off: queries, encoders, CSP, cookies, password hashing, reset flow, authorisation, CSRF,
  secrets, dependency and licence policy, headers, logging, the browser header contract, cookie
  scope and origin plan, user files, URL allow-lists, API versions, DTOs, rate limits, spec linting
- [scoring.md](scoring.md) — severity, confidence, the 0–10 formula, the gate, the OWASP mapping,
  templates
- [proposal.md](proposal.md) — decisions by band, fix-the-class sequencing, red test first

---

## 📐 Pick the mode

Say which one up front, and the tier within it.

| Mode | Input | Output |
|---|---|---|
| **Review** | A repo, a service, or a PR diff (plus config and dependency manifests) | Findings, per-domain scores, the gate. Changes nothing. |
| **Design** | Requirements (users, data classes, clients, integrations), a threat model if one exists, or a review to correct | `controls.md`: the authentication, session, authorisation, input, output, crypto, secrets, header, dependency and logging controls the service needs, and where each is enforced |
| **Propose** | A review and/or a `controls.md` | `proposal.md`: decisions per domain and a remediation sequence that fixes each class of bug at its shared cause, each fix with a red test |

Review tiers:

| Tier | When | Run |
|---|---|---|
| **PR review** | A diff, not a codebase | R1 for the touched endpoints and sinks, R3 against the changed lines and everything they reach; findings without a score |
| **Domain review** | One concern ("is our auth right?", "are we injectable?") | R1–R3 for that domain |
| **Service review** | One deployable application or API | R1–R4, all nine domains (browser only where a browser is a client; api only where the service exposes one) |
| **Estate review** | Several services or repos | R1–R4 per service, then R5 |

**Infer the stack and say it** before grading: language and version, framework (ASP.NET, Spring,
Express/Nest, Django/Flask/FastAPI, Laravel/Symfony, Rails, Go net/http/Gin), template engine, ORM or
query layer, auth library or identity provider, how sessions are carried (cookie, bearer token),
package manager and lockfile, deployment shape (server-rendered, SPA + API, mobile backend, worker).
[detection-signals.md](detection-signals.md) gives the signals per stack. Never assume one stack.

---

## 🔎 Review

The review **does not prescribe**. It produces evidence, the principle each defect violates, an
inventory and a number. The fix belongs to Design and Propose.

Scope is **static evidence by default**: source, templates, configuration per environment, dependency
manifests and lockfiles, IaC that configures the app, and scanner output. **Dynamic testing** —
sending requests, fuzzing, replaying with a tampered ID — only against an environment the user owns
and names (localhost, a `test`/`staging` host they give you), and only within what they asked for.
**Never exploit, scan or probe production or anything the user hasn't named.** Anything that needs
runtime evidence you don't have is a 🔬 flag.

### R1 — Inventory

- [ ] **Redact first.** Config files, `.env`, test fixtures and CI files carry credentials. Never copy
  a secret value into an output — record the *kind* and the location
  (`config/prod.yml:12, database password`). A committed secret is a Critical finding on its own.
- [ ] **The endpoint inventory** — the review's spine. One row per route/handler/RPC/message
  consumer: method and path · who may call it (anonymous, user, role, service) · **where
  authentication is checked** · **where authorisation is checked** (none, controller, policy layer,
  query predicate) · untrusted inputs it reads · sinks they reach (query, command, template, file,
  outbound request, redirect) · whether it changes state · whether cookies authenticate it. Include
  AJAX/JSON endpoints, GraphQL resolvers, webhooks, admin routes, static and private file routes.
  Access control, input and the gate all read this table.
- [ ] **Reconcile the inventory** (APIs): code routes ↔ the OpenAPI/GraphQL schema ↔ gateway or
  ingress config ↔ DNS/host names. A route in code but not in the spec is a **shadow** API; a
  version, environment or host in the spec, gateway or DNS that the code still serves but nobody owns
  is a **zombie**; a spec operation with no route is drift. Each operation gets one row per
  **route × method × version**. Anything outside the repo (gateway, DNS) is 🔬 unless the user
  supplies it (A40).
- [ ] **Response classes and cross-origin channels** (browser): route classes by content type
  (HTML pages, JSON APIs, user files, static assets), and every CORS policy, `postMessage` handler,
  frame and third-party script — the browser domain grades these (A25–A39).
- [ ] **Trust boundaries**: browser ↔ server, server ↔ database, server ↔ third-party APIs, service ↔
  service, user ↔ tenant. Name what is trusted on each side, and why.
- [ ] **Credential stores and crypto uses**: where passwords are hashed, what is encrypted or signed
  and with what, where keys come from.
- [ ] **Dependency manifest**: direct dependencies with versions, the lockfile, runtime version,
  licences.
- [ ] **Counts per domain** — they weight the score ([scoring.md](scoring.md)).
- [ ] **Source version**: the commit every finding cites. **Output location**: the repo's convention,
  else `analysis/appsec/`. Never write inside this skill's folder.

### R2 — Run the static tools if they're available

Semgrep (with the stack's rulesets), CodeQL, `bandit`, `gosec`, `brakeman`, SpotBugs + find-sec-bugs,
`eslint-plugin-security`; `npm audit` / `pip-audit` / `osv-scanner` / `trivy fs` / `dotnet list
package --vulnerable` / `bundler-audit`; `gitleaks` / `trufflehog` for secrets; `syft` + `grype` for an
SBOM and its vulnerabilities; ScanCode or `licensee` for licences. **Their output is evidence, not the
review** — a scanner finds sinks and versions; it doesn't see that a handler never checks ownership,
that a reset token never expires, or that a vulnerable function is unreachable. Record which tools
ran and which didn't.

### R3 — Evaluate each domain

One domain, one section of [review-rubric.md](review-rubric.md): **input**, **authentication**,
**access**, **crypto**, **configuration**, **dependencies**, **logging**, **browser**, **api**.

How to read code for security, not just for correctness (TAOSSA):

- **A green suite and a clean scan don't clear an input-gated path.** Black-box testing misses the
  branch that only a specific parameter reaches; source review and testing are complementary
  (TAOSSA pp. 11–12).
- **Trace each untrusted input from source to sink, through storage.** Data validated at one entry
  point is read back from the database, a queue or a report by code that assumes it's clean; code
  that looks safe is often safe only because of an unrelated filter upstream (pp. 18–19).
- **Every assumption is a candidate.** "Only our client calls this", "the field is never longer than
  …", "nobody can reach that interface" — each is a hypothesis to test against the code (pp. 20–21).
- **Docs are evidence, not truth.** When a design doc or threat model exists, read it first for
  orientation — then verify every claim against the code (p. 51).
- **Switch techniques periodically** — inventory sweep, source-to-sink trace, reading one module
  whole, checking one pattern across all modules — rather than grinding one; the least is known at
  the start, so abstract flaws surface late (pp. 97–98).
- **Classify each finding as design, implementation or operational** (pp. 14–17): implementation
  defects are this skill's; a design-layer finding (no authorisation model, a trust boundary in the
  wrong place) also goes to [threatmodel](../threatmodel/SKILL.md); an operational one (TLS settings at
  the proxy, an exposed management port) to [hardening](../hardening/SKILL.md).

- [ ] **Triage if large** ([scoring.md](scoring.md)) and state coverage.
- [ ] **Walk the domain's 🔴 anti-patterns** against every in-scope object, using
  [detection-signals.md](detection-signals.md) to find candidates and **tracing each from source to
  sink** in context. A grep hit is a candidate: a concatenated query over a constant is not
  injection; a parameterised query whose table name comes from the request is.
- [ ] **Every finding carries six things**: ID, object, anti-pattern, **confidence** (✅/⚠️/🔬),
  **the theory it violates** (A-N), **severity**, and **evidence** as `file:line` (the source, the
  sink, and the missing check). A finding missing any of them is incomplete.
- [ ] **Record the 🟢 too.** A central authorisation layer, an autoescaping template engine, a
  parameterised query builder — Propose keeps and extends them.
- [ ] **Count per criterion** how many in-scope objects satisfy it. The score is computed from counts.

### R4 — Score and summarize

Apply the formula: `p` per criterion, base, caps, confidence rule. **Show the arithmetic.** Write
`summary.md` from the template: scores, severity tally, 🔬 tally, the endpoint inventory, the trust
boundaries, the OWASP Top 10 mapping of the findings, what works, top findings, systemic issues (one
missing layer causing many findings), and **each gate condition separately**.

### R5 — Estate synthesis

Across services: capped and uncapped estate score; a severity heatmap (service × domain); **shared
causes** (one internal auth library, one template helper, one vulnerable dependency used everywhere);
the **service-to-service trust graph** (who accepts whose tokens, who calls whom with which
credential) — Propose sequences from it; themes, each tied to its theory.

---

## 📝 Design

Design the **controls** — what each boundary checks and where the check lives — before writing
code. Read [theory.md](theory.md) and [design-patterns.md](design-patterns.md) first. If a
[threatmodel](../threatmodel/SKILL.md) exists, its security requirements are the input: every control
traces to one.

| Tier | Input | Output |
|---|---|---|
| **New service** | Users and roles, data classes, clients (browser, mobile, service), integrations, compliance | `controls.md` |
| **Revision** | A review | `controls.md` where every changed control traces to a finding ID or a stated requirement |
| **Design review** | An existing auth/security design or ADR | Findings against the rubric's checklists; rewrite only when asked |

Method:

1. **Scope, assumptions, open questions.** Users, roles, tenants, data classes, clients, third
   parties. Never silently promote an assumption into a requirement.
2. **Authentication model.** Who authenticates how (framework or identity provider, never hand-rolled
   — A6); password storage parameters; MFA; throttling; the recovery flow; service-to-service auth.
3. **Session model.** Cookie or token; lifetime (idle and absolute); rotation on login and privilege
   change; logout; cookie attributes; token validation rules (A7).
4. **Authorisation model and where it's enforced.** Roles/permissions/relationships; one policy layer
   that every endpoint passes through; object ownership in the data query; tenant scoping; deny by
   default; how new endpoints inherit it (A9–A11).
5. **Input contract per boundary.** For each input: type, format, length, allow-list; the parser; what
   happens on failure (A1, A2).
6. **Output encoding per context.** HTML body, attribute, JavaScript, URL, CSS, SQL, shell, LDAP,
   headers — which encoder, applied where, by default (A3).
7. **Request-forgery and cross-origin.** CSRF defence for every cookie-authenticated state change;
   CORS allow-list; `postMessage` peers; framing policy; cookie scope and the origin plan — which host
   names exist, which serves user content, whether any sibling hosts less-trusted code (A12,
   A29–A32).
7a. **The authorisation matrix.** One row per operation, one column per actor — anonymous, owner,
   another user, another tenant, a lower role, admin — each cell *allow* or the exact refusal. It is
   the spec the acceptance tests encode, and its verification is HAPI's A-B / A-B-A method: user A
   creates, user B tries to read, change and delete through every method and every ID-bearing field,
   user A re-reads to confirm nothing changed (HAPI ch10, pp.253–256).
7b. **Browser contract per response class.** Content type and charset, `nosniff`, `Cache-Control`,
   framing, CSP, `Referrer-Policy`; how user files are served; third-party scripts and their SRI
   (A25–A26, A33–A35).
7c. **API contract.** The reconciled inventory; per-role response shapes and writable properties;
   rate, size and cost limits and their keys; version-retirement policy; what documentation and
   introspection are exposed where (A40–A43).
8. **Crypto and keys.** What is hashed, encrypted, signed; with which library and mode; where keys
   come from and how they rotate (A14–A16).
9. **Secrets plan.** Which secrets exist, where they live, who reads them at runtime, rotation (A17).
10. **Configuration and headers.** Per-environment config, error handling, security headers (A18–A20).
11. **Dependency and licence policy.** Pinning, update cadence, SCA gate, licence allow-list for how
    the product ships (A21–A22).
12. **Security events.** What is logged, what must never be logged, where it goes, what alerts
    (A23–A24).
13. **Abuse cases.** For each feature, how it would be misused (enumeration, scraping, account
    takeover, workflow bypass), and the control that answers it.
14. **Validation checklist**: every endpoint passes the authorisation layer; every state-changing
    cookie-authenticated endpoint has a CSRF defence; every sink has its encoder or parameterisation;
    every operation has a full row in the authorisation matrix; every API version and documentation
    endpoint is in the inventory; no secret in code; every control traced; open questions listed.

`controls.md` contains: scope and assumptions · authentication · sessions · authorisation and its
enforcement point · the authorisation matrix · input contracts · output encoding ·
CSRF/CORS/framing/cookie scope · browser contract · API contract · crypto and keys ·
secrets · configuration and headers · dependency and licence policy · security events · abuse cases ·
traceability · validation checklist · open questions. Write code only to show a control's shape (a
policy-layer signature, a cookie configuration, a CSP header); the build goes through
`tdd`.

---

## 📦 Propose

Follow [proposal.md](proposal.md). The rule that dominates it: **fix the class, not the instance**
— a hundred patched concatenations leave the hundred-and-first; one query builder, one encoder, one
authorisation layer don't. Every fix starts with a red test that demonstrates the defect, and every
class gets a regression guard (a lint rule, a CI check, a test over all endpoints). Sequence:
containment (leaked secrets, exploitable holes on public endpoints, known-exploited dependencies) →
systemic fixes at the shared cause → guardrails → configuration → cleanup.

---

## 🛑 Stopping rule

**Review** stops when: the endpoint inventory covers every route and consumer; every in-scope domain
has an evaluation with coverage stated; every finding has its six fields and a traced source → sink;
every score shows `p`, base and cap; every 🔬 flag is listed by name; the gate is stated condition
by condition.

**Design** stops when the validation checklist passes and every open question is listed with the
decision it blocks.

**Propose** stops when every Critical/High has a decision, every step has its red test and its class
guard, and the order respects the service trust graph.

Then stop. There is always another header to add and another theoretical gadget chain. **A change
that doesn't close a path an attacker could use, remove a class of bug, or make the next mistake
impossible by an amount someone would notice is churn.**

---

## Subagents — optional

Worth it for an **estate** or a large monolith. In Review, delegate R1–R3 per service (or per module
of a monolith): read-only, each returning its slice of the endpoint inventory, signal counts and
findings in the six-field shape — with "could not determine" per field, so a silent delegate is
distinguishable from a clean read. **Keep scoring, the gate and the synthesis in the main thread.**
In Design and Propose, delegate only evidence gathering; the authorisation model and the remediation
order are one set of decisions and must stay in one head.

**Dispatch contract.** Give each delegate the prior (mode, tier, stack), the target (which paths it
owns, and that the rest are covered), the context it cannot infer (roles, tenants, which endpoints are
public, which environment if any may be tested dynamically), the return shape above, and "report
conclusions, not file excerpts". Delegates stay read-only and never send a request to anything the
user hasn't named.

---

## Rules of Engagement

1. **Read-only by default.** Review reads code and config. Dynamic testing only against an
   environment the user owns and names, within what they asked; never production. When it runs:
   two test identities the user provides or the test environment seeds; destructive calls (DELETE,
   state changes) only on test data you created; rate-limit checks in small bursts on a throwaway
   account to find the limit, never sustained load or anything resembling denial of service
   (HAPI ch0, pp.36–39).
2. **Never exploit.** Demonstrate a defect with a trace or a failing test, not by extracting data or
   running a payload against a real system.
3. **Never echo a secret.** Record the kind and location; recommend rotation, not just deletion.
4. **Every finding cites a principle.** A-N from [theory.md](theory.md), or it's taste.
5. **Trace source to sink.** A grep match is a candidate; a finding names where the untrusted data
   enters, where it lands, and the check that's missing.
6. **Stack-neutral first.** State the control generically, then the framework's mechanism.
7. **Review doesn't prescribe; design doesn't build.** Each mode stops at its own deliverable.

## Handoff

> Reviewed `<service>` at `<commit>` (`<stack>`): score `<x>` (`<band>`), gate `<pass/fail — failing
> conditions>`. `<n>` Critical, `<n>` High across `<OWASP categories>`. Endpoint inventory in
> `analysis/appsec/summary.md`.
> Next: **Design** for `<domains>`, then **Propose** for the order; fixes go through
> **`tdd`**, design flaws to **[threatmodel](../threatmodel/SKILL.md)**,
> platform gaps to **[hardening](../hardening/SKILL.md)**.
