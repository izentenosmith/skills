# Detection Signals — What to Look For in Design Artefacts

> Phrases, structures and greps that point at each anti-pattern in [`review-rubric.md`](review-rubric.md),
> with a **confidence tag** (✅ decidable / ⚠️ proxy / 🔬 needs-data — see [`scoring.md`](scoring.md)).
> Design evidence is prose and pictures as much as code: architecture docs, ADRs, diagrams
> (Mermaid, PlantUML, draw.io XML), sequence diagrams, OpenAPI/AsyncAPI specs, IaC, runbooks, an
> existing threat model.
>
> A match is a **candidate**. Read it in context: "the internal network is trusted" under
> *Rejected alternatives* is the opposite of a finding. And **silence is a proxy**: a doc that never
> mentions revocation is ⚠️ until the code or the owners confirm.
>
> Greps assume a repo with docs under `docs/`, `adr/`, `architecture/` or similar; adjust the paths.
> Use `-i` throughout — design prose isn't consistent about case.

## Inventory

| What | Command / where |
|---|---|
| Design documents | `find . -iregex '.*\(adr\|architecture\|design\|threat\|security\|rfc\).*\.\(md\|adoc\|rst\|txt\)' -not -path './node_modules/*'` |
| Diagrams | `find . \( -name '*.drawio' -o -name '*.puml' -o -name '*.mmd' -o -name '*.dsl' \) -o -name '*.md' -exec grep -l '```mermaid' {} +` |
| Existing threat-model files | `find . \( -name '*.tm7' -o -name '*threat*.json' -o -name 'tm.py' -o -name 'threagile*.yaml' \)` |
| API specs | `find . \( -name 'openapi*.y*ml' -o -name 'swagger*.json' -o -name 'asyncapi*.y*ml' -o -name '*.proto' \)` |
| Entry points in code (to reconstruct the DFD) | route decorators/registrations: `grep -rnE '@(Get\|Post\|Put\|Delete\|Patch\|Request)Mapping\|app\.(get\|post\|put\|delete\|patch)\(\|router\.\|@app\.route\|path\(\|\[Http(Get\|Post)\]' --include='*.{java,kt,ts,js,py,cs,go}' .` |
| Outbound integrations | `grep -rnoiE 'https?://[a-z0-9.-]+' --include='*.{yaml,yml,json,env.example,properties,tf}' . \| sort -u` |
| Trust zones in IaC | VPCs/VNets, subnets, security groups, network policies, IAM roles — the boundaries the platform actually enforces |
| Document dates vs architecture change | `git log -1 --format=%cs -- <threat-model-file>` vs `git log -1 --format=%cs -- <iac-or-arch-dir>` |

## scope

| Anti-pattern | Signal | Conf. |
|---|---|---|
| Goals without subjects | `grep -rniE '\b(shall\|must\|should) be (secure\|protected\|safe)\b' docs/` | ✅ |
| Software-only system definition | DFD external entities: none of *admin*, *operator*, *support*, *help desk*, *customer*, *partner*; no *reset*, *recovery*, *onboarding* flow — `grep -rniE 'help ?desk\|support (agent\|tool)\|password reset\|account recovery\|onboarding' docs/` returns nothing | ⚠️ |
| No asset register | no section titled *assets*, *data inventory*, *data classification* | ✅ |
| Hazard kept | `grep -rniE 'store (all\|every)\|keep (forever\|indefinitely)\|retain(ed)? for ever\|central (vault\|store) of' docs/`; data stores holding secrets/biometrics/plaintext PII | ⚠️ |
| Sprawling TCB | most components inside one boundary; *trusted* applied to CI, IdP, admin tooling without analysis — `grep -rniE '\btrusted (service\|component\|zone\|network)\b' docs/` | ⚠️ |
| Control with missing axis | controls table without owner/test columns; `grep -rniE 'mitigat(ed\|ion)' docs/` lines with no mechanism or owner nearby | ⚠️ |
| Model built from the docs alone | the model cites no code path, IaC file or config; tree nodes marked *mitigated* with no component or control ID; no *misuse*, *abuse* or *forbidden* scenarios — `grep -rniE 'misuse\|abuse case\|must not be (able\|possible)' docs/` returns nothing | ✅ |

## adversaries

| Anti-pattern | Signal | Conf. |
|---|---|---|
| No adversary model | no section on *adversary*, *attacker*, *threat actor*, *opponent*; or only `grep -rniE '\b(hackers?\|malicious users?)\b'` | ✅ |
| Scaling attacks ignored | auth/signup/reset/payment endpoints in the spec with no *rate limit*, *throttl*, *captcha*, *bot*, *breached password*, *anomaly* anywhere: `grep -rniE 'rate.?limit\|throttl\|captcha\|bot (detection\|protection)\|breached\|pwned\|anomal' docs/ src/` | ⚠️ (✅ when stated absent) |
| Insiders omitted | `grep -rniE '\b(admin\|support\|operator)s? can (see\|view\|access\|edit\|change\|reset)\b' docs/`; no *insider* in the adversary list | ✅ |
| No abuse analysis | features *shared account*, *family*, *delegate*, *location sharing*, *view as* with no *abuse* section | ⚠️ |
| Security by user vigilance | `grep -rniE 'users? (should\|must\|will) (verify\|check\|notice\|confirm)\|educat(e\|ion) users\|awareness training' docs/` as a mitigation | ✅ |
| Recovery by assertion | `grep -rniE '(support\|agent\|help ?desk).{0,40}(reset\|unlock\|change).{0,40}(password\|mfa\|2fa\|email)' docs/ runbooks/` | ✅ |

## boundaries

| Anti-pattern | Signal | Conf. |
|---|---|---|
| "Internal means trusted" | `grep -rniE 'internal (network\|traffic\|services?) (is\|are) trusted\|behind the (firewall\|vpn\|load balancer)\|trusted network\|no auth(entication)? (needed\|required) (internally\|inside)' docs/` | ✅ |
| Crossing with no decision (spec) | OpenAPI operation with `security: []`, or no `security` at root and none per operation: `grep -nE '^\s*security:\s*\[\s*\]' openapi*.y*ml` | ✅ |
| Crossing with no decision (code) | handlers on state-changing routes without an authorisation call or decorator — read each; `grep -rnLE 'authorize\|PreAuthorize\|permission\|policy\|can\(\|has_perm\|requires_auth' <handlers-dir>` as triage | ✅ after reading |
| Authorisation only at the edge | `grep -rniE '(gateway\|api gateway\|ingress\|frontend\|ui) (handles\|does\|enforces) (auth\|authori[sz]ation)' docs/`; batch jobs, admin scripts, direct DB access or presigned-URL flows that skip the service | ✅ |
| Unauthenticated service-to-service | no mTLS, service tokens or network policies in IaC/manifests: `grep -rniE 'mtls\|peerauthentication\|serviceaccount token\|networkpolicy\|spiffe' .` returns nothing | ⚠️ |
| Missing or stale DFD | no diagram; diagram older than IaC/arch changes (inventory date check); components in IaC absent from the diagram | ✅ |
| Shared intermediate / cascade | one IdP, CI system, log pipeline, admin group or signing key referenced by systems of different trust; `grep -rniE 'shared (service )?account\|shared (key\|secret\|credential)\|same (key\|credential) (for\|across)' docs/` | ✅ |
| Write-up from low trust | flows from monitoring/analytics/CI/partner components into prod stores or control systems; CI with prod write credentials | ✅ |
| Confused deputy | features *fetch URL*, *import from link*, *webhook*, *proxy*, *export on behalf of*; downstream calls with a service identity instead of the user's — `grep -rniE 'on behalf of\|impersonat\|service account (calls\|accesses)' docs/` | ⚠️ |
| Over-privileged component | IaC roles with `*`, `Owner`, `roles/owner`, `cluster-admin` bound to app identities | ✅ |
| Component straddling trust domains | one handler/service with `is_admin`, `internal`, `trusted` or `role` flags choosing which checks run — `grep -rnE 'if .*(is_?admin\|internal\|trusted\|skip_?(auth\|check))' <src>`; internal and public routes on one listener | ⚠️ |

## policy

| Anti-pattern | Signal | Conf. |
|---|---|---|
| No stated model | no section *authorisation model*, *access control*, *roles*, *permissions*; per-user grants in seed data or IaC | ✅ |
| Tenancy implicit | multi-tenant product; `grep -rniE 'tenant' docs/` silent on how tenant is checked per request | ⚠️ |
| Integrity without invariants | ledger/balance tables written by several services or by admin SQL; `grep -rniE 'update (balance\|ledger\|wallet)\|manual (adjustment\|correction)' docs/ runbooks/` | ✅ |
| Single principal for grave actions | `grep -rniE '(single\|one) approv(al\|er)\|self.?approv\|auto.?approv' docs/`; runbooks: *run in prod*, *delete*, *drop*, *export key*, *change payee* with one actor | ✅ |
| Checker can change what they check | approval workflow allowing edits after approval; same role creates and approves | ✅ |
| Silent break-glass | `grep -rniE 'break.?glass\|emergency access\|override\|god mode\|superuser\|impersonate user' docs/` with no *alert*, *review*, *log* nearby | ✅ |
| Temporary as permanent | `grep -rniE '\btemporar(y\|ily)\b\|for now\|TODO.{0,20}(auth\|security)\|will (add\|fix) (later\|in v2)' docs/ src/` on a control | ⚠️ |
| Roles spanning contexts | role → field matrix; *support can view full record*; one *staff* role | ✅ |
| Inference ignored | `grep -rniE 'anonymi[sz]ed\|de.?identified\|pseudonym\|hash(ed)? (email\|phone\|ssn\|id)' docs/` claims with no linkage analysis; analytics APIs with exact small counts | ⚠️ |
| Circumventable rule or self-grantable role | delegation, impersonation, *act as*, invite, share or role-assignment features — `grep -rniE 'delegat\|impersonat\|act[ _-]as\|assign[_ ]role\|grant[_ ]permission\|invite' docs/ <src>` — read each for a rule against targeting yourself; limits enforced on one path to an outcome | ⚠️ |

## protocols

| Anti-pattern | Signal | Conf. |
|---|---|---|
| Static authenticator | `grep -rniE 'api.?key (is\|as) (the )?(only )?auth\|device (id\|serial) (to\|for) authenticat\|account number (to\|for) (verify\|authenticat)' docs/`; specs with only `apiKey` security schemes for high-value operations | ✅ |
| Replayable requests | state-changing operations with no `nonce`, `timestamp`, `Idempotency-Key` or signature headers in the spec | ⚠️ |
| SMS or session-only approval | `grep -rniE '\bsms\b.{0,40}(otp\|code\|2fa\|mfa\|verif)\|one.?time (password\|code)' docs/` for payment, payee change, admin actions; approval text without payee/amount | ✅ |
| No key lifecycle | keys listed without *rotate*, *rotation*, *revoke*, *destroy*, *compromise*: `grep -rniE 'rotat\|revok\|key (destruction\|ceremony)\|compromis' docs/` silent | ⚠️ |
| Fleet-wide or derived key | `grep -rniE '(same\|single\|one\|master\|global) key (for\|across\|on) (all\|every)\|derive[sd]? .{0,20}from (serial\|device id\|email\|user ?id)' docs/` | ✅ |
| Irrevocable tokens | `grep -rniE 'expires?_?in.{0,10}(30d\|90d\|365d\|never)\|non.?expiring\|long.?lived (token\|key)\|refresh token' docs/ src/ config/`; JWT `exp` far in the future; no revocation list or introspection | ✅ |
| `alg: none` / weak JWT | `grep -rniE '"alg"\s*:\s*"none"\|algorithms?\s*[:=]\s*\[?\s*["'"'"']?(none\|HS256)' src/ config/`; shared HMAC secret across services | ✅ |
| Token as identity | `grep -rniE 'access token (proves\|identifies\|as identity)\|login with oauth' docs/` without OIDC ID-token validation | ⚠️ |
| Crypto without mode / misuse | `grep -rniE '\bAES\b(?!.{0,15}(GCM\|CCM\|SIV\|Poly))\|\bECB\b\|\bDES\b\|3DES\|\bMD5\b\|\bSHA-?1\b\|\bRC4\b' docs/ src/` (PCRE: `grep -P`); custom cipher code | ✅ |
| Opaque randomness | `grep -rnE 'Math\.random\|new Random\(\|random\.random\(\|rand\(\)\|mt_rand' src/` near token/key generation | ✅ |
| Legacy TLS for compatibility | `grep -rniE 'tls ?1\.[01]\|sslv3\|for (backward\|legacy) compatibility' docs/ config/` | ✅ |

## resilience

| Anti-pattern | Signal | Conf. |
|---|---|---|
| Single mechanism per hazard | no hazard × mechanism matrix; mitigation lists with one item for an outcome marked *critical* | ✅ |
| Fail-open | `grep -rniE 'fail.?open\|allow on (error\|timeout)\|if (unavailable\|down).{0,30}(allow\|skip\|bypass)' docs/ src/`; circuit-breaker fallbacks that return *permit* | ✅ |
| Weaker fallback | `grep -rniE 'offline mode\|degraded mode\|legacy (path\|endpoint\|mode)\|fallback to' docs/` without the same checks | ⚠️ |
| Backup equals redundancy | `grep -rniE '(replica\|replication\|raid\|multi.?az\|geo.?redundan).{0,40}(backup\|recover)' docs/`; no restore test | ✅ |
| Work before auth | public endpoints that render, query or upload before authentication; unauthenticated report/export endpoints | ⚠️ |
| Monitoring without response | `grep -rniE '(detected\|caught\|covered) by (monitoring\|siem\|alerts?\|logging)' docs/` with no owner/time | ✅ |
| Mutable evidence | audit logs in the same store/account the admins control; `grep -rniE 'audit (log\|trail)' docs/` with no *immutable*, *append-only*, *WORM*, *separate account* | ⚠️ |
| Frozen assurance | threat model older than arch changes (inventory date check); `grep -rniE 'iso ?27001\|soc ?2\|pci' docs/` used as the assurance argument; no `SECURITY.md` / `security.txt` / disclosure policy: `ls SECURITY.md .well-known/security.txt 2>/dev/null` | ✅ |
| No incident plan | no *incident response*, *runbook*, *on-call*, *contact list* doc | ✅ |
| Misaligned incentive | risk owner a team that doesn't bear the loss; customer terms shifting fraud loss to users | ⚠️ |

## Needs-data (always 🔬 unless evidence is supplied)

Whether production matches the design; whether dual-control procedures are followed; who holds key
shares in practice; whether alerts reach a person; whether restores have worked; actual token
lifetimes in the identity provider; whether the help desk follows the verification script. Ask for
the evidence; list each as a flag by name.
