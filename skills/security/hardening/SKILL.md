---
name: hardening
description: Review, design, or propose a security hardening baseline for Linux hosts and cloud estates — identity and privilege, network exposure, data protection, the host itself, backup and restore, monitoring and incident readiness, governance (naming, tagging, locks, change control, evidence), and service roles (web, mail, DNS, database, file transfer, VPN) — distro-agnostic (Debian/Ubuntu, RHEL family, SUSE, Alpine, Arch; systemd or OpenRC) and cloud-agnostic (AWS, Azure, GCP, OCI, on-prem). Review audits collected evidence (configs, command output, IaC, cloud exports) with findings and a repeatable 0–10 score; Design writes the baseline — controls with IDs, per-platform mapping and a read-only check each; Propose sequences the rollout so nobody is locked out and every step has a check and a rollback. Use for "harden this server", CIS-style audits, a landing-zone or subscription baseline, a pre-production readiness check, or "is this host locked down". It never changes a host or cloud account.
---

# 🛡️ hardening

Hardening is **removing what an attacker could use and making what remains fail closed** — fewer
accounts, fewer privileges, fewer listening ports, fewer packages, fewer ways in — and then
**proving** it, with a check that can be re-run tomorrow. A baseline nobody verifies decays into a
document; a check nobody owns decays into noise. This skill grades estates against a baseline,
writes the baseline, and sequences the rollout.

The same seven core domains apply to a single VM, a fleet, a Kubernetes node pool or a whole cloud
tenant; an eighth, **service**, grades the roles a host runs (web, mail, DNS, database, file
transfer, VPN) and applies only where the role exists. What changes is the evidence and the command
that reads it — never the principle.

## Where this fits

Three security skills, one per layer:

- [threatmodel](../threatmodel/SKILL.md) — *what* to protect and from *whom*: assets, adversaries,
  trust boundaries, the security policy a system must enforce
- [appsec](../appsec/SKILL.md) — whether the **code** enforces it: injection, authn/authz, sessions,
  crypto use, dependencies
- **hardening** (this skill) — whether the **platform** the code runs on is locked down: hosts,
  accounts, networks, storage, backups, monitoring, governance

Neighbours outside the family: `terraform` grades the IaC
that builds the platform; `pipelines` grades the path that
deploys to it; `netaudit` grades network topology in depth. Where
a hardening finding lives in Terraform code, record it here against the control and point to the
file; the code review belongs to terraform.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding cites (H1–H30)
- [review-rubric.md](review-rubric.md) — per domain: 🟢 well done, 🔴 anti-patterns (what, why,
  detect, severity), checklist criteria
- [detection-signals.md](detection-signals.md) — the read-only command per control, per distro and
  per cloud, with its confidence tag
- [design-patterns.md](design-patterns.md) — the baseline catalogue (control IDs, defaults per tier,
  the service-role controls), the platform mapping tables, naming and tagging conventions, the
  exception process, the admin-workstation overlay, the threat tier, and what not to adopt
- [scoring.md](scoring.md) — severity, confidence, the 0–10 formula, the gate, templates
- [proposal.md](proposal.md) — decisions by band, the no-lockout rule, rollout sequencing

---

## 📐 Pick the mode

Say which one up front, and the tier within it.

| Mode | Input | Output |
|---|---|---|
| **Review** | Evidence from hosts and/or cloud accounts (or a PR to IaC/config) | Findings, per-domain scores, the gate. Changes nothing. |
| **Design** | Requirements (platforms, tiers, data classes, compliance), or a review to correct | `baseline.md`: the controls, their per-platform implementation, the verification for each, the exception process |
| **Propose** | A review and/or a baseline | `proposal.md`: decisions per domain and a staged rollout where no step can lock out its own operators |

Review tiers:

| Tier | When | Run |
|---|---|---|
| **Spot check** | One host, one account, or one concern ("is SSH locked down?") | R1 for that scope, R3 for the touched domain(s); findings without a score |
| **Host review** | One host or one image/template | R1–R4, domains identity · network · data · host · continuity · monitoring, plus service for each role the host runs |
| **Account review** | One cloud account / subscription / project, or one on-prem segment | R1–R4, all seven core domains, plus service where roles exist |
| **Estate review** | Several accounts, or a fleet | R1–R4 per unit (fleet: per role, with a sample), then R5 |

**Infer the platform and say it** before grading: OS family and version (`/etc/os-release`), init
system (systemd, OpenRC, runit), package manager (apt, dnf/yum, zypper, apk, pacman), firewall
front-end (nftables, iptables, firewalld, ufw), MAC system (SELinux, AppArmor, none); cloud provider
and account structure; IaC tool if any. [detection-signals.md](detection-signals.md) gives the
command per platform. Never assume Ubuntu or any one cloud.

**Tier the environment** too — `prod`, `non-prod`, `sandbox` — and the data class it holds. A
control's required level comes from the tier ([design-patterns.md](design-patterns.md) §1); a
sandbox doesn't need immutable backups, a production database does.

---

## 🔎 Review

The review **does not prescribe**. It produces evidence, the principle each gap violates, an
inventory and a number. The fix belongs to Design and Propose.

Scope is **evidence that already exists or is collected read-only**: config files, IaC, command
output the user pastes or lets you collect, cloud CLI/API exports, scanner reports (Lynis, OpenSCAP,
CIS-CAT, Prowler, ScoutSuite, Trivy, kube-bench, cloud-native posture tools). **Never change a host
or an account in Review** — no package installs, no service restarts, no `sysctl -w`, no firewall
edits, no cloud writes. If collection needs root or a cloud role, ask; list what you could not read
as 🔬.

### R1 — Inventory

- [ ] **Redact first.** Shadow files, private keys, `.env`, cloud credentials, connection strings and
  tokens show up in evidence. Never copy a secret into an output — record the *kind* and the location
  (`/etc/app/db.conf:4, database password in plain text`). A readable secret is a finding on its own.
- [ ] **The asset register**: every host (or host role, for a fleet), every account/subscription/
  project, every data store, every network edge — with its environment tier, **threat tier**
  ([design-patterns.md](design-patterns.md) §9), data class, owner, the **service roles** each host
  runs, and how it was evidenced. Untagged or ownerless assets are themselves a governance finding.
- [ ] **The exposure map**: what is reachable from where — every listening service per host, every
  inbound rule per security group/NSG/firewall, every public IP, public endpoint and public bucket.
  This table is the review's spine; network, data and the gate read it.
- [ ] **The privilege map**: who and what can administer each asset — human accounts, groups/roles,
  service identities, keys, `sudoers` entries, cloud role assignments at each scope, break-glass
  accounts.
- [ ] **Counts per domain** — they weight the score ([scoring.md](scoring.md)).
- [ ] **Evidence date and version**: when each piece was collected, from which host/account, at
  which commit for IaC. **Output location**: the repo's convention, else `analysis/hardening/`. Never
  write inside this skill's folder.

### R2 — Run the scanners if they're available

Lynis, OpenSCAP (`oscap xccdf eval` with the distro's SCAP content), CIS-CAT, `kube-bench`, Prowler,
ScoutSuite, Trivy (`fs`/`config`/`k8s`), the cloud's own posture service. **Their output is evidence,
not the review** — a scanner checks settings one at a time; it doesn't see the exposure map, the
privilege map, whether a backup was ever restored, or whether anyone reads the alerts. Record which
tools ran, against what, and which didn't.

### R3 — Evaluate each domain

One domain, one section of [review-rubric.md](review-rubric.md): **identity**, **network**, **data**,
**host**, **continuity**, **monitoring**, **governance**, and **service** for each role a host runs.
Endpoints that hold production credentials are graded under host with the admin-workstation overlay
([design-patterns.md](design-patterns.md) §8).

- [ ] **Triage if large** ([scoring.md](scoring.md)) and state coverage.
- [ ] **Walk the domain's 🔴 anti-patterns** against every in-scope object, using
  [detection-signals.md](detection-signals.md) for the platform's command and reading each result in
  context. A matching line is a candidate, not a finding: `PermitRootLogin yes` inside a `Match`
  block for a console-only address means something else.
- [ ] **Every finding carries six things**: ID, object, anti-pattern, **confidence** (✅/⚠️/🔬),
  **the theory it violates** (H-N), **severity**, and **evidence** (`host:path:line`, command +
  output excerpt, or resource ID). A finding missing any of them is incomplete.
- [ ] **Record the 🟢 too.** What is already hardened tells Propose what to keep and tells the reader
  the review looked.
- [ ] **Count per criterion** how many in-scope objects satisfy it. The score is computed from counts.

### R4 — Score and summarize

Apply the formula: `p` per criterion, base, caps, confidence rule. **Show the arithmetic.** Write
`summary.md` from the template: scores, severity tally, 🔬 tally, the asset register, the exposure
map, the privilege map, what works, top findings, systemic issues, and **each gate condition
separately**.

### R5 — Estate synthesis

Across units: capped and uncapped estate score; a severity heatmap (unit × domain); **shared
failure modes** (one golden image with the defect, one IAM role assumed everywhere, one backup vault
for every account); the **trust graph** between accounts (cross-account roles, peered networks,
shared keys) — Propose sequences from it; themes, each tied to its theory.

---

## 📝 Design

Design the **baseline** — the controls, their level per tier, how each is implemented on each
platform, and how each is verified — before anyone edits a host. Read [theory.md](theory.md) and
[design-patterns.md](design-patterns.md) first.

| Tier | Input | Output |
|---|---|---|
| **New baseline** | Platforms in use, environment tiers, data classes, compliance regime, team/ownership model | `baseline.md` |
| **Revision** | A review | `baseline.md` where every changed control traces to a finding ID or a stated requirement |
| **Baseline review** | An existing standard or policy document | Findings against the rubric's checklists (missing domains, controls with no verification, tier-blind rules, vendor lock-in); rewrite only when asked |

Method:

1. **Scope, assumptions, open questions.** Platforms (distros and versions, clouds, on-prem,
   containers), tiers, data classes, regulatory drivers, who operates what. Never silently promote an
   assumption into a requirement.
2. **Start from the catalogue** in [design-patterns.md](design-patterns.md) §2 — the controls by
   domain with IDs — and adopt, tighten, relax or drop each one **with a reason**. A control dropped
   without a reason is a gap a reviewer will find later.
3. **Level per tier.** For each control: required in prod? in non-prod? in sandbox? A baseline that
   applies prod rules to sandboxes gets ignored; one that applies sandbox rules to prod gets breached.
4. **Platform mapping.** For each control, how it is implemented on each platform in scope — the
   distro's file or package, the cloud's native feature — using the mapping tables (§3–§4). Name the
   feature generically first ("deletion lock"), the vendor term second.
5. **Verification.** Every control gets a **read-only check** that returns pass/fail, and the
   evidence it leaves (§5). A control without a check is an aspiration.
6. **Conventions.** Naming, tagging, resource grouping and account structure (§6) — generic patterns
   with placeholders (`<org>`, `<product>`, `<client>`, `<env>`), never one organisation's literals —
   even when the requirements ask for them; decline with the reason and keep the existing names out
   of the baseline entirely (§6).
7. **Exceptions.** How a deviation is requested, who approves it (a security owner, not the
   requester), how long it lasts, and where it is recorded (§7).
8. **Evidence and cadence.** Where verification output is kept, how often each check runs, who reads
   the drift report.
9. **Validation checklist**: every domain covered; every control has a level per tier, a platform
   mapping for each platform in scope, and a verification; no organisation- or vendor-specific
   literal where a placeholder belongs; exceptions are time-bound with an approver; open questions
   listed.

`baseline.md` contains: scope and assumptions · tiers and data classes · the control table (ID,
domain, statement, level per tier, theory) · platform mapping · verification per control ·
conventions · exception process · evidence and cadence · traceability (revision) · validation
checklist · open questions. Write configuration snippets only to show a control's shape (an
`sshd_config` drop-in, a sysctl file, a policy JSON); generating the full automation is a separate
task.

---

## 📦 Propose

Follow [proposal.md](proposal.md). The rule that dominates it: **no step may lock out the people
who have to apply the next one** — every access-reducing change (SSH, firewall, MFA, role removal,
network isolation) is applied to a canary first, with a second session or break-glass path open and a
tested rollback; and every blocking control is **observed before it is enforced** — report-only,
an end date, promotion on measured evidence (H24). Sequence: containment (exposed admin, leaked credentials, public data) → visibility
(logging, inventory) → recoverability (backups that restore) → identity → network → host → data →
service roles → governance and cleanup. If anything suggests the host is already compromised, the
plan stops at containment and evidence (H28).

---

## 🛑 Stopping rule

**Review** stops when: the asset register, exposure map and privilege map cover every in-scope unit;
every in-scope domain has an evaluation with coverage stated; every finding has its six fields; every
score shows `p`, base and cap; every 🔬 flag is listed by name; the gate is stated condition by
condition.

**Design** stops when the validation checklist passes and every open question is listed with the
decision it blocks.

**Propose** stops when every Critical/High has a decision, every step has its check, its rollback
and its lockout guard, and the order respects the trust graph.

Then stop. There is always another sysctl to tune and another benchmark item to chase. **A control
that doesn't remove a way in, shrink what a compromise reaches, or make recovery possible by an
amount someone would notice is a checkbox for its own sake** — and every checkbox costs the
operators who live with it.

---

## Subagents — optional

Worth it for an **estate** or a large fleet. In Review, delegate R1–R3 per unit (account, or host
role): read-only, each returning its slice of the asset register, exposure map, privilege map, counts
and findings in the six-field shape — with "could not determine" per field, so a silent delegate is
distinguishable from a clean read. **Keep scoring, the gate and the synthesis in the main thread.** In
Design and Propose, delegate only evidence gathering; the baseline and the rollout order are one set
of decisions and must stay in one head.

**Dispatch contract.** Give each delegate the prior (mode, tier), the target (which hosts/accounts it
owns, and that the rest are covered), the context it cannot infer (tiers, data classes, which units
are production, which commands it may run), the return shape above, and "report conclusions, not
file excerpts". Delegates stay read-only and never write to a host or an account.

---

## Rules of Engagement

1. **Read-only, always.** Review collects; it never changes. Propose writes the plan; a human (or
   their automation) applies it. Ask before running anything that needs root or a cloud role.
2. **Never echo a secret.** Record the kind and the location; recommend rotation, not just deletion.
3. **Every finding cites a principle.** H-N from [theory.md](theory.md), or it's taste.
4. **Platform-neutral first.** State the control generically, then the per-distro or per-cloud
   mechanism. No baseline assumes one distro, one cloud, or one organisation's names.
5. **No lockouts.** Every access-reducing step has a canary, a second path in, and a rollback.
6. **Tier-aware.** A finding's severity reads the asset's tier and data class; say which.
7. **Active probes are the user's.** Discovery scans, `testssl.sh`, relay and zone-transfer tests,
   vulnerability scanners, password audits — anything that sends traffic to a target or writes to
   it — run only by the user (or their tooling) against named systems with written authorisation
   (GOV-12). The skill reads their output.
8. **Suspected compromise stops hardening.** Hardening a host that is already owned locks the
   attacker in and destroys evidence. Stop, preserve (don't run diagnostics on the live host), and
   hand off to `incident-fix` (H28).
9. **Observe before enforce.** Every blocking control gets a report-only phase with an end date and
   a promotion step on evidence (H24). A control stuck in observe mode is reported as a gap.
10. **Review doesn't prescribe; design doesn't apply.** Each mode stops at its own deliverable.

## Handoff

> Reviewed `<scope>` (evidence as of `<date>`): score `<x>` (`<band>`), gate `<pass/fail — failing
> conditions>`. `<n>` Critical, `<n>` High. Asset register, exposure map and privilege map in
> `analysis/hardening/summary.md`.
> Next: **Design** to set the baseline for `<domains>`, then **Propose** for the rollout; IaC defects
> go to **`terraform`**, code-level defects to
> **[appsec](../appsec/SKILL.md)**, a suspected compromise to
> **`incident-fix`**.
