# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How a hardening review is graded and written down. **Rubric version: `v1.0`.** Every output
> records the rubric version it was graded against and the date and source of the evidence it read.
> Each finding names the principle it violates from [`theory.md`](theory.md) (H-N). A finding that
> asserts a gap without naming the principle is incomplete — a gap without a principle is taste.
>
> The formula is the same one the database, networking and infrastructure families use, so a 7.4
> means the same thing everywhere.

## Severity taxonomy

Severity reads the asset's **tier** and **data class**. The same open port is High on a production
database host and Low on a disposable sandbox; say which tier you graded against.

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | A way in an outsider can use now, a secret anyone with access can read, or a state where data can be lost with no way back | SSH/RDP/database/cluster-API/admin console reachable from the internet with password auth, default credentials or no auth; an inbound *any → any* rule on a production network; a publicly readable bucket, share or snapshot holding non-public data; a private key, cloud key or production password readable by any user or committed to VCS; an owner/admin role granted to an external or anonymous principal; production data with no backup at all; an internet-facing service with a known-exploited vulnerability left unpatched; a database account with no password or an anonymous user reachable from any network; a mail server relaying abuse now |
| **High** | A broad gap in isolation, accountability or recoverability | Privileged human accounts without MFA; shared or generic admin accounts (`admin`, `root` logins in use, one key for a team); direct root SSH login; password authentication on SSH; admin access from a public IP instead of a bastion/VPN/private path; production and non-production in the same account, network or role assignments; backups that are mutable, unlocked, never restore-tested, or stored with the same credentials as the source; no deletion lock on production data stores; audit logging disabled; critical patches older than the baseline's window on production; disks or data stores unencrypted in production; TLS below 1.2 on a production endpoint; unexpected SUID/SGID binaries or world-writable system paths; secrets with no expiry; an open mail relay; an authoritative DNS server answering recursion or zone transfers to the internet; plain FTP with credentials on a public interface; an issuing CA's private key on a service host; optional TLS on database or mail submission; broad snapshot-share or volume-attach rights over prod data; no incident runbook for prod |
| **Medium** | Controlled risk, or debt that becomes High as the estate grows | Services installed or listening that the role doesn't need; no host firewall behind a cloud firewall (single layer); logs kept only on the host; no time synchronisation; overly broad but internal rules (`/16` where a `/29` would do, port ranges); missing owner/environment/data-class tags; secrets in environment variables or config files rather than a secrets store; no MAC (SELinux/AppArmor) in enforcing mode where the distro supports it; restore runbook missing; patch compliance unreported; DMARC stuck at `p=none`; a blocking control left in observe mode past its end date; unconfined network daemons; no resource ceilings; UDP log transport; FIM database writable on the host it protects |
| **Low** | Naming, documentation, cosmetic | Inconsistent naming; missing descriptions on rules; login banner absent; stale but empty groups; unused tags |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current practice.
- 🟡 **Acceptable / watch**: works, but carries security or operational debt.
- 🔴 **Not well done**: violates the criterion. A gap, an anti-pattern, or a theory failure.

## Detection confidence

Not everything can be proven from a config file. Every anti-pattern carries one of three tags.

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the evidence in hand: `PasswordAuthentication yes` in the effective `sshd -T` output, an NSG rule with source `*` to port 22, `find / -perm -4000` listing an unexpected binary, a bucket policy with `"Principal": "*"`, a role assignment of Owner to a guest | Yes. A confirmed gap. |
| ⚠️ **proxy** | A signal that approximates a concern and needs judgement: package count as a proxy for attack surface, last-patch date as a proxy for patch compliance, presence of a backup policy as a proxy for recoverability, a group with no recent sign-ins as a proxy for a stale account | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs runtime or account access you don't have: whether a backup actually restores, whether alerts reach a human, who can assume a role from outside, whether MFA is enforced by a policy defined in another tenant, effective permissions through inherited scopes | **No.** Recorded as a flag, never scored. |

Output from a command the user ran (or let you run read-only) is evidence: a finding read from
`sshd -T` or `az network nsg rule list` is ✅, not 🔬. A file that *configures* a setting is weaker
than a command that shows the *effective* setting — later drop-ins, `Match` blocks, policies and
overrides win. Say which one you read.

## Scoring model

### Evaluation units

One evaluation per **domain** per unit (host, host role, or account), graded with its section of
[`review-rubric.md`](review-rubric.md):

| Domain | In-scope objects (the weight) |
|---|---|
| identity | principals: human accounts, groups/roles with members, service identities, keys and app credentials, privileged role assignments |
| network | exposure points: listening services per host, inbound rules, public IPs and endpoints, peering/VPN edges |
| data | data stores and secrets: disks/volumes, buckets/shares, databases, key stores, certificates, secret stores |
| host | hosts, or host roles/images when a fleet is sampled |
| continuity | stateful assets that must survive loss: databases, volumes, buckets, VMs with state, key stores, configuration |
| monitoring | log and patch sources: every host and every account |
| governance | containers and resources: accounts/subscriptions/projects, resource groups, and the resources tag and lock criteria apply to |
| service | service instances by role — each web, mail, DNS, database, file-transfer/NFS and VPN/bastion instance; empty when a host runs none of them |

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   "In-scope" excludes objects the criterion cannot apply to: the deletion-lock criterion doesn't
   apply to a stateless load-balancer rule; MFA doesn't apply to a workload identity.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps**, applied after the base (lowest wins): any open **Critical** caps at **2.0**; any
   open **High** caps at **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Per-unit and estate scores

The **unit score** is the mean of its domain scores, weighted by in-scope object count, with the
Critical/High caps re-applied. The **estate score** is the mean of unit scores, weighted by total
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

A unit is **hardened enough** — no remediation proposal is owed — only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- no administrative interface is reachable from the internet — the exposure map shows every admin
  path through a bastion, VPN, private endpoint or identity-aware proxy (H8, H9);
- every privileged human identity is nominative and protected by MFA, and no standing owner/root
  credential is in daily use (H3, H4);
- every production stateful asset has a backup that is isolated from the source's credentials and has
  been **restored** in a test within the retention period — evidenced, not assumed (H15, H16);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately. A 9.4 whose database port answers
on the internet is not hardened.

## Triage for large estates

Above **~50 hosts or ~20 accounts**, don't read everything cold:

1. **Group hosts by role and image.** Hosts built from one image with one config-management role are
   one sample; read two of each plus every host that drifts from its role.
2. **Signal-scan** everything that can be scanned (posture tool, Lynis/OpenSCAP across the fleet,
   cloud exports) and record counts per anti-pattern.
3. **Rank** units by signal density and exposure. Deep-read the worst 10% or 10 units, whichever is
   larger, every internet-facing unit, plus a random sample of ~5.
4. **State coverage**: "deep-read 14 of 220 hosts (9 roles); signals cover all 220."

The inventory (asset register, exposure map, privilege map) must still cover **everything**: an
unlisted internet-facing host is the finding that matters most.

## Theory → domain mapping

| Domain | Primary theory to invoke |
|---|---|
| identity | Least privilege (H3); accountable, nominative identities (H4); strong authentication (H5); credentials expire (H6); PAM/sudo mechanics (H3) |
| network | Attack-surface reduction (H7); default deny, explicit allow (H8); no direct administrative exposure (H9); defence in depth (H2); directions and functions (H27) |
| data | Encrypt at rest and in transit (H11); keys and secrets in a managed store (H12); data is private by default (H13); required, verified TLS and PKI operation (H26) |
| host | Minimal installation (H7); file permissions and privilege boundaries (H10); secure, verified configuration (H14); patching (H18); resource ceilings (H23); boot and out-of-band access (H25); homogeneity (H30) |
| continuity | Backups that restore (H15); isolated and immutable copies (H16); deletion protection (H17) |
| monitoring | Audit trails (H19); monitored, alerting operations (H20); vulnerability management (H18); observe before enforce (H24); preserve and rebuild a suspect host (H28); baseline diff against a tamper-evident baseline (H29) |
| governance | Everything owned and classified (H21); controlled change with evidence (H22); segregation by environment (H1) |
| service | Functions denied by default, ACL repeated in the service (H27); TLS required and verified (H26); staged enforcement (H24); validity windows (H6); least privilege (H3) |

## Templates

### Per-domain evaluation — `analysis/hardening/<unit>/<domain>.md`

```markdown
# <Unit> — <Domain> evaluation
> Evaluated against hardening/review-rubric.md §<domain> (rubric v1.0).
> Evidence: <commands / files / exports> — collected <date> from <host/account>. Platform: <distro version, init, firewall; cloud>.
> Tier: <prod / non-prod / sandbox>; data class: <…>. Coverage: <N of M deep-read; signals cover all M>.

## Findings
| ID | Object | Anti-pattern | Conf. | Theory violated | Severity | Evidence |
|----|--------|--------------|-------|-----------------|----------|----------|
| HD-NET-01 | web-01 | Admin port open to the internet | ✅ | No direct administrative exposure (H9) | Critical | nsg-web: rule `ssh-in` src `0.0.0.0/0` dst 22 |

## Signal counts
| Anti-pattern | Count |
|--------------|------:|

## Needs-data flags (not scored)

## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)
```

### Per-unit summary — `analysis/hardening/<unit>/summary.md`

```markdown
# <Unit> — Hardening review summary
> Hosts: <n> · accounts: <n> · data stores: <n> · tiers: <list>. Evidence as of <date>; rubric v1.0.

## Scores
| identity | network | data | host | continuity | monitoring | governance | service | **Unit** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|

## Severity tally · Needs-data flags
## Asset register (asset → tier, threat tier, data class, owner, service roles, evidence)
## Exposure map (what is reachable from where)
## Privilege map (who and what can administer each asset)
## What is working well
## Top findings (worst first)
## Systemic issues
## Gate (each condition, pass/fail, with the reason)
```

Finding IDs: `HD-<IDN|NET|DAT|HST|CON|MON|GOV|SVC>-NN`. The service column is `n/a` for a unit with no service roles.
