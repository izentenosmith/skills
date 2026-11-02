# Review Rubric — Six Domains

> The criteria Review mode grades against. Each domain has 🟢 what good looks like, 🔴 the
> anti-patterns (**What / Why / Detect / Severity**), and the **Checklist** whose criteria are scored
> proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md). Find candidates in the design artefacts with
> [`detection-signals.md`](detection-signals.md), then read each in context — a phrase is a
> candidate, not a finding.
>
> Severity below assumes the asset at stake is confidential or higher, or moves money or identity.
> Lower one step for internal-only data with no money or identity, and say you did.

---

## 1. scope — what the model covers and why

In scope: every asset in the register (data classes, money, identities, keys, availability,
metadata).

### 🟢 Well done
- Protection goals written as *who may do what to which asset*; a one-page policy model exists
  (S2).
- The system definition includes operators, support, customers, partners, onboarding and recovery
  flows (S2).
- Every asset has an owner and a reason an adversary wants it; metadata is listed as an asset (S2,
  S16).
- Hazards were removed by design where possible, and the model says which (S3).
- The trusted computing base is named and small (S4).
- Each control states its policy, mechanism, assurance and owner (S1).

### 🔴 Not well done

#### Goals without subjects
**What:** "The system shall be secure / protect customer data" with no who, what or which. **Why:**
S2 — an unstated goal can't be enforced or tested. **Detect:** requirement and goal sections; search
for "secure", "protected", "safe" without an actor. ✅. **Severity:** High for a system with no other
policy statement; Medium otherwise.

#### Software-only system definition
**What:** The model covers services and stores but not admins, support, customers, partners, the
recovery or onboarding flows. **Why:** S2, S7. **Detect:** DFD external entities; is there a help
desk, an admin console, a reset flow? ✅ when absent from a model that claims completeness.
**Severity:** High when recovery or support can change credentials; Medium otherwise.

#### Missing or ownerless asset register
**What:** No list of assets, or assets with no owner or no class. **Why:** S1, S2. **Detect:** asset
section. ✅. **Severity:** Medium; High for systems holding regulated data.

#### Hazard kept that could be removed
**What:** A central store of secrets, plaintext personal data or keys, or long retention, with no
stated need. **Why:** S3. **Detect:** data stores and retention statements vs the functions that
use them. ⚠️ (need judgement). **Severity:** Medium; High for restricted data or key material.

#### Sprawling trusted base
**What:** Most components inside the innermost boundary; CI, admin consoles, IdP or support tools
trusted but not modelled as such. **Why:** S4. **Detect:** count components inside each boundary;
TCB statement. ⚠️. **Severity:** Medium; High when an untrusted input reaches a TCB component
directly.

#### Controls with a missing axis
**What:** A mechanism with no stated goal, no evidence it works, or no one who loses if it fails.
**Why:** S1. **Detect:** controls table: policy / mechanism / assurance / owner columns. ✅ for blank
cells. **Severity:** Medium.

#### Model built from the docs alone
**What:** A threat model or design review with no reference to the code, IaC or configuration;
mitigations credited in the tree that nobody can point to; only intended use scenarios, none of the
forbidden ones. **Why:** S27. **Detect:** sources cited in the model; tree nodes marked mitigated
without a component or control ID. ✅. **Severity:** Medium; High when a credited mitigation is
absent.

### Checklist
1. Assets with an owner and a data class.
2. Assets with a stated reason an adversary wants them.
3. Protection goals expressed as subject–action–object.
4. People and recovery/onboarding flows in the system definition.
5. Hazards eliminated by design where feasible, with the decision recorded.
6. The TCB named, with each member justified.
7. Controls with policy, mechanism, assurance and owner stated.

---

## 2. adversaries — from whom

In scope: the adversary classes relevant to the system — opponent class × grade, plus insiders and
abusers where they apply.

### 🟢 Well done
- Opponents named by class (spies, crooks, researchers, abusers) and graded, with capabilities,
  motives and budgets (S5).
- What each can obtain legitimately — an account, a support call, a job — is listed (S7).
- Scaling attacks — credential stuffing, bulk signup, scraping, automated fraud — are modelled
  first (S6).
- Insiders and the few people who must be trusted are named, with monitoring (S7).
- Abuse cases — shared devices, intimate-partner abuse, coerced users — are considered where the
  product is consumer-facing (S7).
- Human error is designed for, not blamed (S8).

### 🔴 Not well done

#### No adversary model
**What:** No adversaries, or "hackers"/"attackers" without class, grade or capability. **Why:** S5.
**Detect:** adversary section. ✅. **Severity:** High.

#### One grade for everything
**What:** The design is sized to one attacker grade across assets of very different value. **Why:**
S5. **Detect:** compare asset value to the adversary each control is sized for. ⚠️. **Severity:**
Medium; High when the crown-jewel asset is defended only against opportunists.

#### Scaling attacks ignored
**What:** Login, signup, reset, payment or search endpoints with no rate limiting, breached-password
screening, bot or anomaly controls in the design. **Why:** S6. **Detect:** endpoint list vs controls.
✅ when stated absent; ⚠️ when silent. **Severity:** High for authentication and payment; Medium
otherwise.

#### Insiders omitted
**What:** No insider adversary; support or ops tools that can read or change any record; no
privileged-user monitoring. **Why:** S7. **Detect:** adversary list; admin/support capabilities.
✅. **Severity:** High for financial or personal data.

#### No abuse analysis
**What:** Shared accounts, shared devices, family plans, location sharing or delegated access with no
abusability analysis. **Why:** S7. **Detect:** features vs abuse cases. ⚠️. **Severity:** Medium;
High for location or communications products.

#### Security by user vigilance
**What:** Mitigations that rely on users noticing URLs, certificates or warnings; destructive
confirmations identical to routine ones; recovery by asserted identity. **Why:** S8. **Detect:**
mitigation text ("users should verify…"); help-desk procedure. ✅. **Severity:** High when it's the
only mitigation for account takeover.

### Checklist
1. Adversary classes named with grade, capability and motive.
2. Legitimate access each adversary can obtain listed.
3. Scaling attacks modelled with a control each.
4. Insiders and must-trust roles named, with monitoring.
5. Abuse cases considered where the product is consumer-facing.
6. No mitigation that depends solely on user vigilance.
7. Adversary model re-assessment date or trigger set.

---

## 3. boundaries — where they can reach

In scope: every trust boundary and every data flow that crosses one.

### 🟢 Well done
- A DFD with IDs on every element; trust boundaries drawn and named; the diagram matches the code
  or IaC (S9).
- Every crossing names its authentication, its authorisation decision and where it's enforced,
  channel protection and input validation (S11).
- Services authenticate to each other; no zone is trusted because of where it is (S9).
- Low-trust systems can't write to high-trust ones; shared intermediates are modelled (S10).
- Deputies re-check the caller's rights; components run with the least privilege (S12).

### 🔴 Not well done

#### Crossing with no decision
**What:** A flow from a less-trusted zone to a more-trusted one where the design names no
authentication or no authorisation decision. **Why:** S11. **Detect:** boundary-crossing table blank
cells; OpenAPI `security: []`; code handler with no check. ✅. **Severity:** Critical to a high-value
asset from an untrusted zone; High otherwise.

#### "Internal means trusted"
**What:** Service-to-service traffic unauthenticated because it's inside the perimeter, VPC or
cluster. **Why:** S9. **Detect:** phrases in docs; no mTLS/token on internal calls; network policy
absent. ✅. **Severity:** High.

#### Authorisation only at the edge
**What:** UI or gateway enforces access; services, databases or buckets accept any caller that
reaches them. **Why:** S11. **Detect:** alternate paths to data (batch jobs, admin tools, direct DB
access, presigned URLs). ✅. **Severity:** High; Critical when an alternate path is reachable from an
untrusted zone.

#### Missing or stale DFD
**What:** No diagram, a diagram that doesn't match the code/IaC, or missing third parties and admin
paths. **Why:** S9, S24. **Detect:** compare diagram to IaC/code. ✅ for mismatches. **Severity:**
Medium; High when the missing element is an untrusted entry point.

#### Cascade through a shared intermediate
**What:** Zones of different trust joined through a shared IdP, CI system, log pipeline, management
network or admin group with no analysis. **Why:** S10. **Detect:** components appearing in several
zones; shared credentials. ✅. **Severity:** High.

#### Write-up from low trust
**What:** Monitoring, analytics, CI or partner systems with write paths into production or control
systems. **Why:** S10 (Biba). **Detect:** flows from low-integrity to high-integrity stores. ✅.
**Severity:** High.

#### Confused deputy
**What:** A privileged service fetches URLs, files or records named by the caller using its own
authority; downstream calls with a broad service identity on behalf of any user. **Why:** S12.
**Detect:** design of fetch/proxy/export features; token propagation. ✅/⚠️. **Severity:** High.

#### Over-privileged component
**What:** Components running with admin or wildcard rights the function doesn't need. **Why:** S12.
**Detect:** identity/role per component in the design or IaC. ✅. **Severity:** High for components
facing untrusted input; Medium otherwise.

#### Component straddling trust domains
**What:** One service, process or class serving callers of different trust, with a flag or role
check choosing which validation applies; internal endpoints on a public listener; shared queues or
caches across a boundary. **Why:** S26. **Detect:** DFD elements with flows from two trust zones;
shared handlers. ✅/⚠️. **Severity:** High when one of the domains is untrusted.

### Checklist
1. Trust boundaries drawn and named; DFD matches code/IaC.
2. Crossings naming their authentication.
3. Crossings naming their authorisation decision and where it's enforced.
4. Crossings naming channel protection and input validation.
5. Internal service-to-service calls authenticated.
6. Data reachable only through paths that apply the same authorisation.
7. Shared intermediates analysed for cascades.
8. No write path from lower-integrity to higher-integrity components.
9. Components with least privilege; deputies re-check callers.

---

## 4. policy — what must hold

In scope: protected operations and objects — each action on each asset class the policy must govern.

### 🟢 Well done
- A stated access-control model, chosen for what must hold — RBAC/ABAC, capabilities, BLP/Biba,
  type enforcement, Clark-Wilson, Chinese Wall — with tenancy explicit (S13).
- Irreversible or high-value operations need dual control or functional separation; the gravest need
  several independent conditions (S14).
- Break-glass is logged, alerted and reviewed (S14).
- Defaults are safe; controls fit the people who live with them; exceptions are few and time-bound
  (S15).
- Personal data has a purpose, legal basis and retention; metadata and aggregate releases are
  analysed (S16).

### 🔴 Not well done

#### No stated model
**What:** Access rules decided per endpoint; per-user grants; no tenancy rule. **Why:** S13.
**Detect:** policy section; authorisation logic scattered in the design. ✅. **Severity:** High for
multi-tenant systems; Medium otherwise.

#### Integrity without well-formed transactions
**What:** Money, balances, entitlements or ledgers changed by direct writes, admin SQL or any service;
no balancing invariant; mutable audit trail. **Why:** S13 (Clark-Wilson). **Detect:** write paths to
ledger stores. ✅. **Severity:** Critical for money; High for entitlements.

#### Single principal for the gravest actions
**What:** One approver or one credential can move money, delete production, export keys, change
payees or grant admin. **Why:** S14. **Detect:** approval flows; runbooks. ✅. **Severity:**
Critical for irreversible high-value actions; High otherwise.

#### Checker can change what they check
**What:** The approver can edit the payee, amount or change after approval; approvals that assume a
later stage checks. **Why:** S14. **Detect:** approval workflow states. ✅. **Severity:** High.

#### Silent break-glass
**What:** Emergency or "support override" access with no alert or review. **Why:** S14. **Detect:**
override paths. ✅. **Severity:** High.

#### Roles spanning contexts
**What:** One role reads whole records across purposes (reception staff reading clinical notes;
support reading payment details). **Why:** S13. **Detect:** role → fields matrix. ✅. **Severity:**
High for confidential data.

#### Unsafe defaults or unusable controls
**What:** Opt-in security; sharing on by default; controls so strict that the design itself
documents a workaround; exceptions broader than the rule. **Why:** S15. **Detect:** default values;
exception lists. ✅. **Severity:** Medium; High when the default exposes confidential data.

#### Inference and metadata ignored
**What:** Exports, analytics or logs that reveal sensitive facts by relationship, timing or count;
"anonymised" data that is pseudonymised; hashed identifiers as privacy. **Why:** S16. **Detect:**
data-sharing flows; anonymisation claims. ✅/⚠️. **Severity:** High for regulated data; Medium
otherwise.

#### Circumventable rule or self-grantable role
**What:** A rule enforced on one path to an outcome but not the others; a delegation, impersonation,
invite or role-assignment feature with no rule against assigning it to yourself. **Why:** S25.
**Detect:** for each rule in the policy, list the features that reach its outcome; for each
privilege-granting feature, who may target whom. ✅ when the second path is in the design.
**Severity:** High; Critical when it moves money or grants admin.

### Checklist
1. Protected operations governed by a stated model (including tenancy).
2. Integrity-critical state changed only through certified procedures with invariants and an
   append-only trail.
3. Irreversible or high-value operations requiring independent principals or conditions.
4. Break-glass paths logged, alerted and reviewed.
5. Roles scoped to context and fields, not whole records.
6. Defaults safe; exceptions time-bound and fewer than the rule.
7. Personal data with purpose, legal basis, retention; releases analysed for inference.

---

## 5. protocols — how parties prove who they are and what they mean

In scope: every authentication, authorisation, key-management and other protocol exchange.

### 🟢 Well done
- Fresh challenge-response or signed, timestamped requests; replay and reordering prevented (S17).
- High-value approvals bind and display the transaction content on an independent channel (S18).
- A key-management plan: generation, storage, diversification, purpose separation, rotation,
  destruction, compromise recovery, provisioning (S19).
- Short-lived, revocable credentials; OAuth used for delegation; time sources trustworthy (S20).
- Standard crypto named with its mode; uniform errors; maintained libraries; TLS 1.2+ with
  certificate lifecycle automated (S21).

### 🔴 Not well done

#### Static authenticator
**What:** API keys, device IDs, serial numbers or account numbers as the only proof of identity;
fixed codes over observable channels. **Why:** S17. **Detect:** auth scheme per exchange. ✅.
**Severity:** Critical for high-value assets; High otherwise.

#### Replayable requests
**What:** State-changing requests without nonce, timestamp or idempotency tracking where replay
matters. **Why:** S17. **Detect:** protocol/sequence diagrams; API spec. ✅/⚠️. **Severity:** High for
payments and commands; Medium otherwise.

#### Session approves "a transaction"
**What:** OTP/push/2FA that authenticates the user but not the payee, amount or action; SMS as the
independent channel for high-value actions. **Why:** S18. **Detect:** approval flow text. ✅.
**Severity:** High; Critical for irreversible money movement.

#### No key lifecycle
**What:** Keys named without generation, rotation, destruction or compromise recovery; one key per
fleet or environment; keys derived from identifiers; one key for several purposes; a master key held
whole by one person. **Why:** S19. **Detect:** key inventory. ✅. **Severity:** Critical for a
fleet-wide or derived key protecting high-value assets; High otherwise.

#### Irrevocable credentials
**What:** Long-lived bearer tokens, refresh tokens without revocation, permission caches without
freshness bounds; access tokens treated as identity. **Why:** S20. **Detect:** token lifetimes and
revocation design. ✅. **Severity:** High.

#### Trust in unauthenticated time
**What:** Authentication or licensing depends on a clock that the adversary can influence. **Why:**
S20. **Detect:** timestamp checks; NTP design. ⚠️. **Severity:** Medium.

#### Crypto named without a mode or misused
**What:** "AES" without mode; ECB; nonce or IV reuse; distinguishable padding/MAC errors; custom
primitives; legacy suites enabled for compatibility; encryption offered as the answer to an access
problem. **Why:** S21. **Detect:** crypto sections, library choices, config. ✅. **Severity:** High.

#### Opaque randomness
**What:** Key or token generation from non-cryptographic or single-source RNGs; keys generated at
first boot on constrained devices. **Why:** S21. **Detect:** generation design; code. ✅.
**Severity:** High.

### Checklist
1. Exchanges authenticated by fresh challenge or signed, timestamped messages.
2. Replay and reordering prevented where they matter.
3. High-value approvals bound to transaction content on an independent channel.
4. Keys with a full lifecycle, diversified and separated by purpose.
5. Credentials short-lived and revocable; OAuth used as delegation.
6. Crypto standard, mode named, errors uniform, libraries maintained.
7. Randomness from a vetted CSPRNG.
8. Certificate issuance and renewal automated; TLS 1.2+.

---

## 6. resilience — what happens when something fails

In scope: every serious hazard — each undesired outcome the owners can't tolerate.

### 🟢 Well done
- A hazard × mechanism matrix with two independent mechanisms per serious hazard (S22).
- Fail-open or fail-closed decided per component; faults stay visible (S22).
- Backup, redundancy and fallback distinguished; fallbacks are no weaker than the primary (S22).
- Every "detected by monitoring" names the signal, the owner and the response time; detections are
  tested with seeded events (S23).
- Evidence survives hostile review; audit logs sit outside the admins' reach (S23).
- A vulnerability-intake and disclosure route, a patch commitment, an incident plan, and re-run
  triggers for the model (S24).
- The people guarding each control bear its failure (S1).

### 🔴 Not well done

#### Single mechanism for a serious hazard
**What:** A hazard × mechanism row with one entry, or no matrix at all. **Why:** S22. **Detect:**
matrix; mitigation lists. ✅. **Severity:** High; Critical when the one mechanism is a password.

#### Fail-open on a security dependency
**What:** Authorisation, fraud or rate-limit services whose timeout lets the request through. **Why:**
S22. **Detect:** failure-mode statements; circuit-breaker defaults. ✅. **Severity:** High.

#### Weaker fallback
**What:** Legacy, offline, "degraded" or recovery modes without the primary's checks. **Why:** S22.
**Detect:** fallback paths in the design. ✅. **Severity:** High.

#### Backup equals redundancy
**What:** Replication or RAID offered as backup; backups reachable from production credentials; no
restore rehearsal. **Why:** S22. **Detect:** continuity section. ✅. **Severity:** High for data the
business can't lose.

#### Work before authentication
**What:** Public endpoints that allocate state or do expensive work before authenticating;
amplifying responses. **Why:** S22. **Detect:** public endpoint design. ✅. **Severity:** Medium;
High for availability-critical systems.

#### Monitoring as a mitigation with no response
**What:** "Detected by monitoring/SIEM" with no signal, owner or response time; alerting only on
events, never on silence; no seeded tests. **Why:** S23. **Detect:** mitigation text. ✅.
**Severity:** Medium; High when it's the only mitigation.

#### Evidence that won't survive a dispute
**What:** Audit logs writable by the admins they record; no chain of custody; disputes settled by
assertion. **Why:** S23. **Detect:** logging and dispute design. ✅. **Severity:** High for money
and regulated data.

#### Frozen or friendly assurance
**What:** A model older than the last boundary change; sign-off by the builders; certification
offered as assurance; no disclosure route, patch commitment or incident plan. **Why:** S24.
**Detect:** dates, sign-off, process docs. ✅. **Severity:** Medium; High for high-assurance tier.

#### Misaligned incentives
**What:** The owner of a control doesn't bear its failure; customers carry losses the operator
could prevent. **Why:** S1. **Detect:** risk owner vs who pays. ⚠️. **Severity:** Medium.

### Checklist
1. Serious hazards with two independent mechanisms.
2. Components with a stated fail-open/fail-closed decision.
3. Fallback and degraded modes no weaker than the primary.
4. Backup distinct from redundancy, isolated from production credentials, rehearsed.
5. Detections with signal, owner, response time and a seeded test.
6. Audit evidence outside the audited admins' reach.
7. Disclosure route, patch commitment and incident plan in place.
8. Model re-run triggers defined; model newer than the last boundary change.
9. Risk owners who bear the loss.
8. Model validated against code/IaC; forbidden use scenarios listed; findings carry a layer (S27).
10. No component serves more than one trust domain without a boundary inside it (S26).
8. Every rule checked against the other features that reach its outcome; no privilege self-grantable (S25).
