# Proposal — From Review and Baseline to a Rollout

This reference governs **Propose** mode. It consumes a review (Review mode's findings, scores, gate,
asset register, exposure map and privilege map) and a baseline (Design mode's `baseline.md`) when
those exist. **Do not re-run the review or re-design the baseline here.** If an input is missing,
say so and scope the proposal to what exists — never imply a missing review or baseline was done.

Treat review scores as evidence, not a substitute for judgement. Read the caps and the gate: an open
Critical caps a domain at 2.0, an open High at 6.0; 9.0 is the score threshold, and the gate also
needs no internet-facing admin path, MFA on nominative privileged identities, and restore-tested
isolated backups for prod.

## Decisions per domain

Use each domain's band as the starting posture, then explain any evidence-based override:

| Score band | Starting posture |
|---|---|
| 9.0–10 | **Keep** — and add the verification that keeps it there |
| 7.0–8.9 | **Tighten** — targeted fixes inside the current setup (close a rule, add a lock, rotate a key, enable a log) |
| 5.0–6.9 | **Rework** — change the pattern in this domain (move admin access behind a bastion, introduce a secrets store, split prod into its own account, replace hand-built hosts with a role image) |
| 0–4.9 | **Rebuild** — a new baseline for the domain, with hosts rebuilt from a hardened image and data migrated, not patched in place |
| Unowned or unused asset | **Retire** — state the evidence (no owner tag, no traffic, no logins) and the confirmation needed before deletion |

Any open Critical gets a corrective decision **in the first change window**, even when the overall
score is high. Leaked credentials come first: **rotate, then remove** — deleting a secret from a file
does not remove it from backups, images, VCS history or the attacker's copy.

## The rule that dominates: no step locks out the next one

Most hardening reduces access — that is the point — and every access-reducing change can remove
the access needed to apply, verify or roll back the next change. Every such step carries a
**lockout guard**:

| Change | Lockout guard | Rollback |
|---|---|---|
| SSH: disable passwords/root login, restrict users, change port | Keys installed and **tested in a second session** before reloading `sshd`; keep the current session open; `sshd -t` before reload; console/serial/out-of-band access confirmed | Restore the previous drop-in from backup; `systemctl reload sshd` from the open session |
| Host firewall: default deny | Allow the admin path **first**; apply with an auto-revert (`firewall-cmd --timeout`, a scheduled `nft -f <previous>` that you cancel once verified, `ufw` with a pre-armed restore job) | The auto-revert fires; or console access |
| Cloud firewall / NSG: remove `any`, close admin ports | Bastion/VPN/private path **live and tested** before closing the public rule; change by IaC with plan reviewed | Re-apply the previous revision |
| MFA / conditional access enforcement | Report-only mode first; break-glass accounts **excluded** and tested; registration campaign complete | Policy back to report-only |
| Removing privileged role assignments | The replacement (group, JIT role) exists and the owner has used it; two admins remain | Re-assign from break-glass |
| SELinux/AppArmor to enforcing | Run permissive/complain on the role and fix denials first; one canary host | Back to permissive with `setenforce 0` / `aa-complain` |
| Private endpoints, public access off | Clients resolve and reach the private path (DNS checked) **before** public access is disabled | Re-enable public access scoped to the client IPs |
| Deletion locks | Pipelines that legitimately delete are given a documented, logged unlock step | Remove the lock (logged) |
| Immutable backup vault lock | Confirm retention values first — a compliance-mode lock **cannot be undone** | None once locked: state it, and get explicit approval |
| Kernel/sysctl, mount options | Canary host; reboot test where the change needs one | Previous `sysctl.d` file; `fstab` backup |
| Egress default-deny (NET-15) | Destinations measured first (flow logs, `ss` history); resolvers, time, mirrors and backup targets allowed **before** the default flips; auto-revert armed | The auto-revert fires; previous ruleset |
| Boot-loader password, single-user auth (HST-16) | Console/rescue path for the operators tested with the new credential; the credential stored in the break-glass vault | Previous GRUB config from backup via the cloud rescue path |
| WAF, DMARC, SPF, MAC — any blocking control (H24) | Report-only first (`DetectionOnly`, `p=none`, `~all`, permissive/complain) with a **stated end date**; promote on the measured false-positive rate | Back to report-only; never silently left there |
| DNS recursion off, transfer limits, mail relay limits (SVC-DNS, SVC-MAIL) | Legitimate clients and secondaries listed from logs first; external test after the change (user-run probe) | Previous config; `rndc reconfig` / `postfix reload` from the open session |
| Database TLS required, `trust`/`md5` removed (SVC-DB-04) | Every client's connection string checked for TLS and SCRAM support; one application at a time | Re-add the previous `pg_hba.conf` line; reload |

State, for each step, **whether it is reversible** and how long reversal takes. A step with no
rollback (vault lock, key deletion, account closure) needs its own explicit approval and goes last
in its group.

## Rollout shape

Never change the whole estate at once. For each change:

1. **Observe** — for any control that can block legitimate work, run it report-only first and give
   the phase an **end date** (H24): AppArmor complain / SELinux permissive, ModSecurity
   `DetectionOnly`, DMARC `p=none`, SPF `~all`, MFA report-only, firewall rules with `log` before
   `drop`. Promote when the measured false positives are understood — not before, and not never.
2. **Canary** — one non-prod host or account; then one prod unit with low blast radius.
3. **Verify** with the control's check from [`detection-signals.md`](detection-signals.md) — pass/fail,
   with evidence captured — and with the service's own health checks.
4. **Waves** — by host role or account group, pausing between waves long enough to see an effect
   (a day for access changes, a patch cycle for update policy).
5. **Bake into the source** — the image pipeline, the config-management role, the IaC module, the
   policy assignment — so new assets are born hardened and drift is corrected automatically. A
   control applied by hand to running hosts is a control that new hosts won't have.

## Sequencing

Order the work:

0. **Suspected compromise?** If the review found signs that a host is already owned — unexplained
   UID 0 accounts, new `authorized_keys`, `ld.so.preload` entries, unknown listeners, a Tor daemon,
   logs with gaps — **this plan stops here.** Isolate it, preserve evidence (no diagnostics on the
   live host), and hand off to `incident-fix`; the host is
   rebuilt, not hardened in place, and every credential it held is rotated (H28).
1. **Containment.** Close internet-facing admin interfaces; close open mail relays and
   internet-facing recursion/zone transfers; remove anonymous or empty-password database accounts; make public data stores private; rotate
   and remove leaked credentials; disable default accounts with default passwords; patch
   known-exploited vulnerabilities on exposed hosts. These go first even if the score is otherwise
   high.
2. **Visibility.** Control-plane audit logs, host log forwarding, inventory and tags — so every later
   change is observable and attributable. A change you can't see is a change you can't verify or
   roll back.
3. **Recoverability.** Backups on every stateful asset, a restore tested, deletion locks on prod
   containers. Before tightening anything that could break production, make sure production can be
   brought back.
4. **Identity.** Break-glass accounts first; then MFA (report-only → enforce); nominative accounts;
   narrow role scopes; workload identities replacing keys; secret expiry.
5. **Network.** Bastion/VPN/private endpoints live → close public admin paths → remove `any` rules →
   host firewalls → segmentation and egress control.
6. **Host.** Role images; update management enrolment; package and service minimisation;
   permissions and SUID; MAC to enforcing; kernel and mount hardening; agents.
7. **Data.** Encryption gaps; customer-managed keys; secrets moved into the store; delegated URLs
   shortened; TLS minimums raised; TLS required (not optional) for databases and mail submission;
   certificate renewal automated; CA keys moved off service hosts.
8. **Service roles.** Per role, one at a time: web (unprivileged workers, read-only docroot, WAF
   observe → block), mail (relay limits, AUTH inside TLS, SPF/DKIM/DMARC staged), DNS (role split,
   transfers signed, DNSSEC with automated signing), databases (private listener, per-app accounts,
   SCRAM + TLS), file transfer (FTP replaced), VPN (revocable per-user credentials).
9. **Governance and cleanup.** Naming and tag policies enforced; exceptions register; evidence
   repository; retire unowned assets after confirmation.

Respect the **trust graph** from R5: harden the account or host that others trust (identity
provider, bastion, CI runner, backup account) before the ones that trust it, and never cut a
cross-account role before its replacement works.

**Cite the principle behind each decision and each ordering constraint** (H-N, [theory.md](theory.md)):
why containment goes first, why the private path is live before public SSH closes, why a credential
is rotated before it is removed, why an irreversible lock goes last. A sequence without its reasons
can only be accepted or rejected whole; one with them can be argued step by step.

## Proposal skeleton — `analysis/hardening/proposal.md`

```markdown
# <Scope> — Hardening proposal
> Inputs: review <path, date, rubric v1.0> · baseline <path or "none">. Evidence as of <date>.

## Summary
Score <x> (<band>), gate <pass/fail — failing conditions>. <n> Critical, <n> High.
Recommendation in one paragraph.

## Decisions per domain
| Domain | Score | Decision | Reason (finding IDs, principle H-N) |
|---|---:|---|---|

## Containment (first change window)
| # | Finding | Action | Lockout guard | Verification | Rollback | Reversible? |
|---|---|---|---|---|---|---|

## Rollout
| Wave | Step | Scope (canary → waves) | Control IDs | Lockout guard | Verification | Rollback | Owner | Window |
|---|---|---|---|---|---|---|---|---|

## Irreversible steps (each needs explicit approval)

## Baked into the source (image / role / module / policy)

## Exceptions requested (control, asset, reason, compensating control, expiry, approver)

## Risks of the rollout itself, and what we accept

## Open questions
```

Every step names its control IDs (and finding IDs), its lockout guard, its verification and its
rollback. A step missing any of them is not ready to schedule.
