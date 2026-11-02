# Theory — The Principles Every Threat-Model Finding Cites (S1–S27)

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** for a design specifically, and **what violating it looks like** in an architecture, a
> design doc or a threat model. Sources are cited by short name:
>
> | Short name | Source |
> |---|---|
> | **SE** | Ross Anderson, *Security Engineering*, 3rd ed. (Wiley, 2020) — chapter, §section, PDF page numbers |
> | **LSE** | Linux Professional Institute, *Security Essentials* (020) learning materials, v1.0 — topic, PDF page numbers |
> | **TAOSSA** | Dowd, McDonald & Schuh, *The Art of Software Security Assessment* (Addison-Wesley, 2006) — ch. 1–3 (preview), printed page numbers |
> | **Practice** | Current practice where the book names an idea and a later method operationalises it: STRIDE, attack trees, NIST SP 800-30 risk assessment, the OWASP threat-modelling guidance, MITRE ATT&CK |
>
> Anderson teaches the principles; where a method postdates or extends him (STRIDE is named in SE
> §27.3.5 but its per-element table is current practice), the principle comes from the book and the
> method is named as practice.

---

## Part A — Framing: what the model is for

### S1 — Policy, mechanism, assurance, incentive: all four or none
**Says:** A dependable system needs a **policy** (what must hold), a **mechanism** (what enforces
it), **assurance** (evidence the mechanism works) and an **incentive** (someone motivated to keep it
working). Failures sit in exactly one of them (SE §1.2, pp.52–53). Ask who pays when it fails, and
put the guard with the loser — systems fail when the people guarding them don't bear the cost (SE
§8.1, p.319; §8.6, p.338). Beware guards who gain by not looking (SE §8.6.6, p.348) and markets where
buyers can't tell secure from insecure, so price wins (SE §8.3.3, p.328).
**Why:** Visible controls are not effective controls: screening spend was large while cheap cockpit
doors were decisive, and testers found screeners missing over half of real weapons (SE §1.2, p.53).
A mechanism with no assurance is theatre; one with no incentive decays.
**Violation:** a control with no stated goal; a mechanism nobody tests; a risk owned by a team that
doesn't lose when it materialises; fraud detection owned by a revenue-measured function; a vendor
chosen on a certificate rather than test results.

### S2 — Write the protection goals down, for a system that includes its people
**Says:** State the goals explicitly — who may do what to which asset — before choosing mechanisms;
"secure" means different, conflicting things to different parties (SE §1.7–§1.8, pp.63–64). The
system includes the product, its operators, admins, internal and external users and the recovery
flows; narrower definitions hide failures (SE §1.7, p.60). Distil the goals into a one-page policy
model: threat model → policy → mechanism → target (SE §9.2, pp.360–361).
**Why:** Ignoring the human component is among the largest causes of failure; products certified at
the component level broke in use the certification never imagined (SE §1.7, p.60).
**Violation:** requirements that say "secure" or "protected" without subject, action and object; a
model that lists only services; no help-desk, onboarding or account-recovery flow on the diagram; no
asset register; assets without owners.

### S3 — Eliminate the hazard before mitigating it
**Says:** The first move is design, not control: don't hold data, keys or privilege you don't need;
remove the central store that makes one breach a total breach; minimise what must be trusted (SE
§27.3.2, p.1003 — SWIFT's early design let banks exchange keys directly so SWIFT itself couldn't
forge traffic).
**Why:** A hazard that isn't there needs no mechanism, no monitoring, no test and no owner. Every
mitigation is a component that can fail.
**Violation:** a central database of secrets, biometrics or plaintext personal data with no stated
need; long retention "in case"; one service holding every tenant's keys; a design that adds controls
around a hazard it could have removed.

### S4 — Shrink the trusted computing base; mediate everything
**Says:** *Trusted* means its failure breaks the policy; *trustworthy* means it won't fail. Make the
trusted set small and verifiable (SE §1.7, p.61). Route every access through a small reference
monitor that can't be bypassed (SE §9.3.1, p.364).
**Why:** Every component in the TCB is one whose bug is a policy violation. CI runners, admin
consoles, support tools and identity providers are routinely trusted without being treated as such.
**Violation:** a diagram where most components are inside the innermost boundary; "trusted"
components reachable by untrusted input; authorisation checks that some paths skip; no list of what
the TCB is.

## Part B — Adversaries

### S5 — Name the opponents, their grade and what they can afford
**Says:** You can't defend against every threat at reasonable cost, so choose: name the opponent
classes — spies, crooks, researchers, abusers — their capabilities and motives, and re-assess over
the system's life (SE ch.2, pp.66–67). Grade them: Anderson's burglar scale runs from the
opportunist (Derek) through the experienced criminal (Charlie) and the professional (Bruno) to the
state team (Abdurrahman); designing for Charlie fails against Bruno (SE §13.2.1, pp.513–514); and
low-grade attackers can now rent high-grade tools (SE §18.4, pp.644–645).
**Why:** "Hackers" isn't a threat model. Controls are sized to an adversary; without one, they are
sized to a mood.
**Violation:** no adversary section; adversaries without capabilities; insiders omitted; one generic
attacker for a system holding both public content and payment data; no re-assessment date.

### S6 — Defend first against the attacks that scale
**Says:** Attackers prefer high-capital, near-zero-marginal-cost attacks; the criminal economy
specialises into botnets, malware, credential stuffing and cash-out, so industrialised attacks come
first (SE §2.2.1.12, p.77; §2.3.1, pp.90–93). Credential stuffing was the largest source of attempted
account compromise in 2019 (SE §2.3.1.4, p.93). The basics matter: the Equifax breach ran through an
unpatched portal and default credentials (SE §2.2.5, p.89).
**Why:** A defence that requires per-account human attention loses to an attack that costs nothing
per account.
**Violation:** login, signup, password reset or payment endpoints with no rate limit, breached-
password screening or anomaly detection; per-account manual review as the only defence against bulk
abuse.

### S7 — Insiders, abusers and the people you must trust
**Says:** Model what an adversary can obtain *legitimately* — an account, a support call, a job
(SE §27.3.5, p.1006). Identify the few dozen people the system must trust; minimise, monitor and
ask "how would I defraud us?" (SE §12.2.4–§12.2.5, pp.455–456). Design for **abusability** as well
as usability: households aren't units, devices aren't personal, the purchaser isn't the only user
(SE §2.5.4, §2.6, p.107). Handle payee changes and executive requests with procedure — call back a
known number (SE §2.3.2, p.96).
**Why:** Most high-value frauds involve an insider or an impersonated one; most abuse of consumer
systems comes from someone close to the victim.
**Violation:** support tools that can view or change any customer; no privileged-user monitoring;
shared-device or shared-account flows with no abuse analysis; payment-detail changes accepted by
email.

### S8 — People err predictably; design, don't blame
**Says:** Design for slips, lapses, rule mistakes and misconceptions; make dangerous actions look
unlike routine ones (SE §3.2.1, pp.113–114). Every phishing rule taught to users was defeated in
turn — "blame and train" fails (SE §3.4.4.5–§3.4.4.6, pp.149–150). Defaults are the control (SE
§3.2.5.3, p.126). Help-desk staff reset passwords for callers who merely asserted an identity (SE
§3.3.2, pp.132–133).
**Why:** A design that depends on users inspecting URLs, certificates or warnings depends on a
behaviour that doesn't happen.
**Violation:** security that relies on users noticing something; confirmations for destructive
actions identical to routine ones; recovery by help-desk assertion; insecure defaults with an opt-in
to safety.

## Part C — Boundaries

### S9 — Compartmentalise and restrict lateral flow
**Says:** The reach of an attacker after the first foothold depends on how much components trust
each other; authenticate users and devices to each service rather than to a network (SE §21.1,
pp.734–735). Misuse risk grows with the value of what is centralised and the number of people who can
reach it (SE §10.1, pp.384–385). Compartmentalise to bound blast radius (SE §27.5.6, p.1025).
**Why:** "Internal means trusted" turns one compromised laptop, container or partner link into the
whole estate.
**Violation:** a single trust zone for everything behind the perimeter; service-to-service calls
with no authentication; partner VPNs landing in the core network; support staff with access to every
record.

### S10 — Secure components don't compose
**Says:** Two components each secure in isolation can be insecure together — through feedback,
shared intermediates and cascades (SE §9.6.1–§9.6.2, pp.375–376). Prefer separate systems joined by
narrow, one-way or mediated links over one system holding several trust levels (SE §9.4.2,
pp.370–372).
**Why:** The shared identity provider, CI system, log pipeline or admin network is how a compromise in
the least important system reaches the most important.
**Violation:** zones of different trust joined through a shared management plane; a low-trust system
with write access to a high-trust one (monitoring that can change what it monitors — SE §9.3.5,
pp.369–370); a portfolio where every system trusts one signing key.

### S11 — Enforce at the layer that can't be bypassed
**Says:** Know which layer — application, middleware, OS, hardware, cloud IAM — enforces each rule;
controls get weaker as you move up the stack, and duplicated enforcement drifts (SE §6.1, p.254;
§6.2.10, pp.268–269). Authorise where the data is, not only where the button is.
**Why:** Authorisation in the UI or the API gateway alone is bypassed by anyone who reaches the
service, the database or the storage directly.
**Violation:** authorisation only in the front end; a database or bucket reachable by a path that
skips the application's checks; "the gateway handles auth" with services that accept any caller.

### S12 — Least privilege, and no confused deputies
**Says:** Give each component the rights its task needs and no more; don't make things privileged to
save effort (SE §6.2.3, pp.259–260; §6.4.4, p.284). A privileged component must not act for a
less-privileged caller with its own authority (SE §6.4.3, p.282).
**Why:** Privilege is what a compromise inherits; a deputy that uses its own credentials on a
caller's behalf hands the caller those credentials.
**Violation:** services that call downstream with a broad service identity on behalf of any user;
file, URL or query parameters that a privileged service fetches without re-checking the caller; a
component running as admin "because it was easier".

## Part D — Policy

### S13 — Choose the access-control model deliberately
**Says:** Pick the model that matches what must hold: groups for people and roles for functions; ACLs
(easy to see who can reach an object) vs capabilities (easy to delegate, hard to revoke) (SE §6.2,
pp.255–262); Bell-LaPadula for confidentiality flow, Biba for integrity, type enforcement for
confinement (SE §9.3, pp.364–370); Clark-Wilson for well-formed transactions with certified
procedures and an append-only audit trail (SE §12.2.3, p.451); Chinese Wall for conflicts of interest
(SE §10.4.8, pp.412–413). Role alone isn't enough when one role spans contexts — require a
relationship too (SE §10.4.4, pp.400–401).
**Why:** An implicit model is an inconsistent one; each endpoint invents its own rule.
**Violation:** per-user grants; no stated model; money or ledger data changed by anything other than
certified procedures; one role reading whole records when it needs administrative fields;
multi-tenant data with no tenant check in the model.

### S14 — Separation of duty, dual control and break-glass
**Says:** Irreversible or high-value actions need more than one principal — dual control (two act
together) or, often stronger, functional separation (complementary roles over one process) (SE
§12.2.4, pp.453–456). The gravest actions need several independent conditions — authorisation,
environment, intent (SE §15.2.2, p.572). Emergency access is logged, alerted and reviewed (SE
§10.4.4.1, p.401). Redundant checkers diffuse responsibility unless each check is forced and
independent (SE §15.1, pp.569–570).
**Why:** A single credential that can move money, delete production or export a key is a single
point of compromise.
**Violation:** one approver for wires, key export or production deletion; the checker can edit what
they check; break-glass with no alert; approvals that are rubber stamps because "the next stage
checks it".

### S15 — Safe defaults that people can live with
**Says:** Make the easy path the safe path (SE §3.2.5.3, p.126); fit controls to the staff's
compliance budget, because controls people must bypass to work become rituals (SE §12.2.4,
pp.455–456); over-tight controls fail as surely as loose ones — prioritise by risk against reward
(SE §27.4, pp.1010–1011). Strict policies collapse into blanket exceptions (SE §9.3.3, p.366).
**Why:** A rule that blocks work is circumvented with shared credentials and screen-sharing, and the
circumvention is invisible.
**Violation:** opt-in security; standing exceptions broader than the rule; controls whose purpose
nobody can state; a policy with more exceptions than subjects.

### S16 — Protect metadata, and treat "anonymised" as a claim to test
**Says:** Who talked to whom, when and how often can reveal the sensitive fact even when content is
encrypted (SE §1.7, p.62; §10.1, p.386 — billing reveals diagnoses). Stripping names is not
anonymisation for rich or linkable data (SE §11.1, pp.417–418; §11.4.1, pp.437–439); many exact
aggregate answers reconstruct the database (SE §11.3, pp.434–435); hashing low-entropy identifiers
is not privacy (SE §20.3, p.708). Document each use of personal data and its legal basis (SE §26.6,
pp.986–990; LSE 025.3, pp.298–299).
**Why:** Privacy breaches increasingly come from data that was released because it "had no names".
**Violation:** logs, analytics or exports that reveal sensitive relationships; pseudonymised data
shared as non-personal; analytics APIs answering arbitrary small-cell queries exactly; hashed phone
numbers or e-mails as "anonymous IDs"; no data inventory or retention limit.

## Part E — Protocols and keys

### S17 — Freshness: no static secrets over observable channels
**Says:** Never use a fixed code, serial number or identifier as an authenticator; use fresh
challenge-response; make replay and reordering impossible, tracking more than the last token used
(SE §4.2–§4.4, pp.167–181). Names are not secrets: identifiers end up used as passwords (SE §7.4.1,
pp.305–308).
**Why:** Protocol flaws give simpler attacks than cryptanalysis — car remotes were replayed by
"grabbers"; a meter that remembered only its last ticket accepted the same two forever.
**Violation:** API keys or device IDs as the only authenticator; requests without nonce or
timestamp where replay matters; idempotency keys compared only with the previous one; account
numbers or national IDs used to authenticate.

### S18 — Authenticate the transaction, not just the session
**Says:** Defend against relay and man-in-the-middle by binding what is approved — payee, amount,
action — into what is authenticated, and bind names and direction into messages (SE §4.3.3–§4.3.4,
pp.176–180). Malware in the browser changes what the user sees, so high-value approval needs an
independent channel that is actually independent (SE §12.7.3–§12.7.6, pp.500–503). Interpret
messages from content, not context (SE §4.8, pp.188–189).
**Why:** A one-time code that approves "a transaction" approves the attacker's.
**Violation:** OTP or push approval that doesn't display and sign the transaction details; SMS as the
"independent" channel for high-value actions; message meaning that depends on position or channel.

### S19 — Plan key management before choosing keys
**Says:** Decide up front how many keys, how generated, how long they live, how destroyed, how
recovered after compromise; diversify per device or per tenant — never derive keys from public
identifiers or share one fleet-wide (SE §4.3.1, pp.172–173; §4.7.5, p.188; §19.4.2, pp.689–690).
Separate keys by purpose and enforce key typing (SE §4.6, pp.182–183; §20.5.1, pp.712–713). Make
shared control usable, or custodians will hand both halves to one person (SE §18.3, pp.640–641); use
threshold schemes for crown-jewel keys (SE §15.3, pp.574–575). Protect the provisioning process —
keys were stolen from a vendor's personalisation files (SE §18.5.4, p.659).
**Why:** Key management is usually an afterthought, and it is where most crypto actually fails.
**Violation:** one key per fleet or per environment; keys derived from serials or e-mails; the same
key for signing and encryption; no rotation or compromise-recovery procedure; one person holding a
master key whole.

### S20 — Revocation and time are part of the protocol
**Says:** Build revocation in — callbacks, publish-and-notify, short-lived credentials — and know
the cost of propagating it (SE §7.2.1–§7.2.2, pp.290–292). Choose timestamps or nonces knowingly:
each trades one risk for another (SE §4.7.3–§4.7.4, pp.185–187). Treat OAuth as delegation, not
authentication; keep tokens short-lived and revocable (SE §4.7.4, pp.187–188). Don't trust a single
time source (SE §7.2.6, pp.295–296).
**Why:** A credential that can't be revoked is valid for as long as the attacker likes; centralising
revocation concentrates risk — when one CA was removed, the services that depended on it were
offline for days (SE §7.2.2, p.292).
**Violation:** long-lived bearer tokens with no revocation path; access tokens treated as proof of
identity; permission caches with no freshness bound; authentication depending on unauthenticated
time.

### S21 — Use standard cryptography, and use it correctly
**Says:** Authenticated encryption (GCM or equivalent), never ECB; never reuse a nonce or IV under
one key (SE §5.5, pp.222–227). Make failures indistinguishable — no padding or timing oracles (SE
§5.5.2, pp.224–225; §19.4.1, p.687). Standard, reviewed primitives and maintained libraries with
blinding and constant-time code; don't design your own (SE §5.7.9, p.249; §19.4.1, p.687).
Randomness is infrastructure — combine sources, distrust opaque generators (SE §5.7.9, p.249;
§18.5.4, pp.658–659). PKI has many equally trusted CAs and weak revocation: short lifetimes, TLS 1.2+,
HSTS, certificate transparency (SE §5.7.4–§5.7.5, pp.241–244; §21.6, pp.765–768). Encryption isn't
magic — say which threat it answers (SE §20.2, pp.703–705). Disable legacy modes (SE §20.5.2,
pp.713–714).
**Why:** Most real cryptographic failures are implementation, key length or mode — not broken
mathematics.
**Violation:** a design naming "AES" without a mode; custom crypto; distinct error codes for padding
and MAC failures; "encrypted at rest" offered as the answer to an access-control threat; TLS below
1.2 accepted for compatibility.

## Part F — Resilience and assurance

### S22 — Two independent mechanisms per serious hazard; fail to a safe state
**Says:** Every serious hazard is covered by at least two independent mechanisms, checked with a
hazard × mechanism matrix (SE §27.3.5, p.1006). Design for the adversary who forces the one-in-a-
billion failure — random-failure statistics don't apply (SE §27.3.6, p.1009). Decide per component
whether it fails open or closed, and keep faults visible even when redundancy masks them (SE §27.3.6,
p.1007; §27.5.6.2, p.1025). State the failure model — benign or malicious — and use fail-stop for
integrity (SE §7.3, pp.296–298). Backup, redundancy and fallback are different things: mirrors
replicate a malicious delete and ransomware poisons weeks of backups (SE §7.3.3, pp.300–302). Degraded
and fallback modes are attack targets — attackers force the weaker path (SE §7.3.4, pp.302–303).
Public endpoints mustn't let callers force the server to do work or hold state before
authentication (SE §21.2.3, pp.740–741).
**Why:** A single mechanism is a single point of failure, and a fallback weaker than the primary is
the primary the attacker uses.
**Violation:** a hazard row with one mechanism; fail-open on an authorisation-service timeout; a
"legacy" or "offline" mode without the primary's checks; backups reachable from production
credentials; expensive work before authentication on a public endpoint.

### S23 — Detection has base rates; evidence must survive hostile review
**Says:** Design the chain deter → detect → alarm → delay → respond as a whole; delay must exceed
response time (SE §13.2, p.512). Intrusion detection is dominated by false alarms — at a 0.1% false-
alarm rate they outnumber real attacks about a hundred to one (SE §21.4.2, pp.757–760); false alarms
are a denial of service on responders, so test with seeded events (SE §13.3.5, pp.527, 533). Supervise
the monitoring path itself with heartbeats (SE §13.3.4, pp.529–533). Keep evidence that survives a
hostile expert — prosecutions collapsed when banks refused experts access (SE §12.4.3, pp.478–479;
§26.5, pp.981–985); keep audit logs out of reach of the administrator they audit (SE §6.2.3, p.259).
**Why:** A detection nobody acts on is a log; a log the attacker can edit is a story.
**Violation:** threats "mitigated by monitoring" with no alert, owner or response time; alerting only
on events, never on missing heartbeats; audit logs writable by admins; disputes resolved by "the
system is secure".

### S24 — Assurance is continuous, hostile and planned for the whole life
**Says:** Assurance now includes the commitment to patch for the system's life (SE §28.1,
pp.1046–1048). Hostile review beats friendly review — the team that built it, or an assessor it
chose, doesn't sign it off (SE §28.3.2, p.1070). Read what a certificate covers; process
certificates are decorative — most large breached firms held one (SE §28.2.7.2, pp.1060–1062;
§28.2.9, p.1066). Run vulnerability intake and coordinated disclosure, and never sue researchers (SE
§27.5.7, pp.1027–1031; §8.6.2, pp.340–342); fix the class of bug, not the instance (SE §27.5.4,
p.1019). Have an incident plan — monitoring, repair, distribution, reassurance — before the incident
(SE §27.5.7.3, pp.1031–1032; LSE 021.2, pp.28–30). The threat model is a living document, re-run
when the architecture or the assumptions change (SE §27.3.3–§27.3.5, pp.1003–1006; §6.4.5,
pp.284–285 — environmental creep).
**Why:** Threats, platforms and dependencies change after the model is written; a model frozen at
design time describes a system that no longer exists.
**Violation:** a threat model older than the last boundary change; sign-off by the builders; "ISO
certified" as the assurance argument; no security contact or disclosure policy; no support horizon
or update path; no incident plan or contact list.

---

## Part G — Reviewing a design in practice

### S25 — Every rule asks which feature defeats it; every role asks who can grant it
**Says:** Business-rule abuse is a design flaw, not an implementation bug: the system does exactly
what each feature specifies, and two features together let someone do what the policy forbids
(TAOSSA pp. 4–5, 26–27). For every rule, ask which *other* feature reaches the same outcome without
passing it; for every role, delegation or sharing feature, ask whether a user can grant it to
themselves (TAOSSA p. 39).
**Why:** A withdrawal limit on one account is defeated by draining a linked account below zero to
force automatic transfers; a "delegate approvals" feature lets an employee appoint themselves and
approve their own expenses. Neither shows up as a bug, and no unit test fails.
**Violation:** rules stated per feature with no cross-feature check; delegation, impersonation,
"act as", invitation or role-assignment features with no rule against self-assignment; limits
enforced on one path to an outcome and not on the others.

### S26 — Trust boundaries are module boundaries; a component serving two trust domains is a finding
**Says:** The trust model is part of the security policy, and in a sound design trust boundaries
fall on module boundaries. A component that serves callers of different trust — public and admin,
tenant and operator, user and internal batch — is a cohesion failure with a security cost: the check
one caller needs is the one the shared code path skips for the other; and strong coupling across a
boundary is where validation goes missing (TAOSSA pp. 28, 32–35).
**Why:** A desktop message queue shared between privileged and unprivileged processes let any window
send commands to a privileged one (the Shatter attack); daemons sharing one account inherited each
other's compromise (TAOSSA pp. 34–35).
**Violation:** one service, process or class that both untrusted users and privileged operators call
with a flag deciding which checks apply; shared mutable state, queues or caches across a boundary;
"internal" endpoints on the same listener as public ones.

### S27 — The design document is evidence to verify, and findings are routed by layer
**Says:** Design documents drift from the system; treat them as claims, and validate the model
against the implementation before relying on it (TAOSSA p. 51). Collect use scenarios that include
the *unauthorised* ones — what must not be possible — alongside the intended ones (TAOSSA pp. 49–53).
Do not take credit for a mitigation in a threat tree before confirming it exists (TAOSSA p. 61).
Classify each finding as **design** (the system does the wrong thing correctly), **implementation**
(it does the right thing wrongly) or **operational** (deployment and configuration), because each
goes to a different owner; then roll component risk up into the order code review should follow
(TAOSSA pp. 14–17, 65–66).
**Why:** A model built only from the docs grades the system the architect intended, not the one that
was built; a model that never ranks components leaves the code review to start wherever is easiest.
**Violation:** a threat model with no reference to code, IaC or config; mitigations marked in the
tree that nobody can point to; only happy-path use scenarios; findings with no layer and no owner; no
ranked list handed to the code review.

