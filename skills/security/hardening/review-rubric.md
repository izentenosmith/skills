# Review Rubric — Eight Domains

> The criteria Review mode grades against. Each domain has 🟢 what good looks like, 🔴 the
> anti-patterns (**What / Why / Detect / Severity**), and the **Checklist** whose criteria are scored
> proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md) and the catalogue control in [`design-patterns.md`](design-patterns.md)
> §2. Collect candidates with [`detection-signals.md`](detection-signals.md), then read each in
> context — a matching line is a candidate, not a finding.
>
> Severity below is for **prod** with internal or higher data. Lower one step for non-prod without
> real data, two for an isolated sandbox — and say you did.

---

## 1. identity — who and what can act

In scope: human accounts (OS, directory, cloud, database), groups/roles with members, service
identities, keys and app credentials, privileged role assignments.

### 🟢 Well done
- Personal accounts only; admins escalate with `sudo`/PIM/just-in-time; the root/owner credential is
  sealed and its use alerts (H4).
- MFA everywhere a human signs in, phishing-resistant for privileged roles; SSH by key or
  certificate (H5).
- Permissions granted to purpose-named groups at the narrowest scope; access reviews happen and
  leave a record (H3, H21).
- Workloads use managed/federated identities; the few remaining secrets expire within 12 months and
  are owned (H6).

### 🔴 Not well done

#### Shared or generic privileged account
**What:** `root`, `admin`, `ubuntu`/`ec2-user`, `sa`, a shared cloud user or a team SSH key used by
several people. **Why:** H4 — actions are unattributable; every leaver is a rotation. **Detect:**
`last`/`lastlog`, `authorized_keys` with several people's keys, sign-in logs for built-in accounts,
DB logins as `sa`/`postgres`/`root`. ✅ when logs show use; ⚠️ from key count alone. **Severity:**
High; Critical when the account is also internet-reachable with a password. *(IDN-01)*

#### Privileged access without MFA
**What:** Console, VPN, bastion or IdP sign-ins for admin roles with password only, or SMS only.
**Why:** H5. **Detect:** IdP/conditional-access policy export; per-user MFA registration report;
`/etc/pam.d/sshd` with no second factor where SSH is the admin path. ✅ from policy; 🔬 when the
policy lives in another tenant. **Severity:** High; Critical on internet-facing admin paths.
*(IDN-02)*

#### Standing broad privilege
**What:** Owner/`*:*`/`roles/owner`/`roles/editor` for daily work; assignments at organisation or
subscription scope where a resource group would do; `NOPASSWD: ALL` for humans; `docker`/`lxd` group
membership for non-admins. **Why:** H3. **Detect:** role-assignment export by scope; `sudo -l -U`;
`getent group docker lxd`. ✅. **Severity:** High. *(IDN-06, IDN-11)*

#### Long-lived or ownerless machine credential
**What:** Access keys, client secrets, PATs, SAS tokens older than a year or with no expiry; no owner
recorded; secrets in code. **Why:** H6, H12. **Detect:** credential reports (key age, last used),
app-registration secret expiry, secret scans. ✅. **Severity:** High; Critical if exposed in VCS or
an image. *(IDN-07, IDN-08)*

#### Default or built-in accounts enabled
**What:** Vendor defaults, `sa` enabled with SQL auth, `guest`, database superusers allowed remotely,
default passwords unchanged. **Why:** H5, H7. **Detect:** DB login lists, appliance docs vs config,
default-credential scans. ✅. **Severity:** High; Critical with a default password. *(IDN-09)*

#### Dormant accounts and stale groups
**What:** Accounts unused for 90+ days, leavers still enabled, empty or purposeless groups.
**Why:** H6, H21. **Detect:** `lastlog -b 90`, IdP last-sign-in, group membership counts. ⚠️ for
inactivity alone; ✅ for a confirmed leaver. **Severity:** Medium; High for a leaver with privilege.
*(IDN-05, IDN-12)*

#### Identity reused across tenants or tiers
**What:** One person's prod and non-prod identity is the same; one account spans tenants.
**Why:** H1, H4. **Detect:** directory exports, role assignments of the same principal in both tiers.
✅. **Severity:** Medium; High when non-prod is less protected and the identity is privileged in prod.
*(IDN-03)*

#### Weak OS / database password policy
**What:** No minimum length (≥ 14 for generated, ≥ 12 for human-chosen), no lockout, no aging where
passwords are the only factor, `$1$` (MD5) hashes. **Why:** H5, H6. **Detect:** `pwquality.conf`,
`faillock.conf`, `login.defs`, `/etc/shadow` hash prefixes, DB password policy. ✅. **Severity:**
Medium; High on internet-reachable password auth. *(IDN-10)*

#### Weak PAM or sudo mechanics
**What:** `/etc/pam.d/other` permits; `nullok` on a password or second-factor module; `pam_rhosts`,
`.rhosts` or `hosts.equiv` present; `su` open to everyone; sudo rules using `ALL`, wildcards,
negations (`!/bin/su`) or commands with shell escapes (editors, pagers, interpreters); no sudo
logging. **Why:** H3, H5. **Detect:** PAM and sudoers greps in detection-signals. ✅. **Severity:**
High for `nullok`/rhosts trust on a reachable host or a sudo shell escape for a non-admin; Medium
otherwise. *(IDN-15, IDN-17, IDN-19)*

#### Locked password, open key
**What:** An account disabled by locking its password while `authorized_keys` still lets it in; a
service account with a shell that FTP/Samba accept. **Why:** H6, H3. **Detect:** locked accounts with
non-empty `authorized_keys`; system accounts with shells listed in `/etc/shells`. ✅. **Severity:**
High for a leaver; Medium for a service account. *(IDN-12, IDN-18)*

### Checklist
1. Human accounts that are nominative (no shared use).
2. Privileged human identities protected by MFA (phishing-resistant for the highest roles).
3. Privileged role assignments at the narrowest workable scope, none standing Owner/`*`.
4. Permissions granted to groups/roles, not individuals.
5. Machine credentials that are workload identities, or keyed with expiry ≤ 12 months and an owner.
6. Default/built-in accounts disabled or locked.
7. Accounts used in the last 90 days or justified; leavers removed.
8. `sudo` rules per user/group, logged, no `NOPASSWD: ALL` for humans.
9. Account names following the convention.
10. PAM stack default-denies, no `nullok`, no rhosts trust; `su` restricted.
11. sudo rules command-scoped and logged.
12. Service accounts sealed (no password, no accepted shell, no SSH).

---

## 2. network — what is reachable from where

In scope: listening services per host, inbound rules, public IPs and endpoints, peering/VPN edges.

### 🟢 Well done
- Every layer default-denies; every allow names source, destination, port, protocol and has a
  description (H8).
- Admin paths only via bastion/VPN/private endpoint/access proxy; nothing administrative on a public
  IP (H9).
- One network per product; prod and non-prod don't route; address plans don't overlap (H1).
- Data services on private endpoints; egress through NAT/proxy with a known IP (H7, H2).
- A host firewall behind the cloud firewall (H2).

### 🔴 Not well done

#### Administrative interface exposed
**What:** 22, 3389, 5985/5986, 1433, 3306, 5432, 27017, 6379, 9200, 6443, 2379, 8443 admin consoles
reachable from `0.0.0.0/0`/`::/0`/`Internet`/`*`. **Why:** H9. **Detect:** inbound rule exports;
`ss -tlnp` + public IP; external scan if the user supplies one. ✅. **Severity:** Critical with
password or no auth; High with keys only. *(NET-04)*

#### `any` in an allow rule
**What:** Source, destination, port or protocol of `*`/`Any`/`0.0.0.0/0`/`-1` on a non-public
listener; port ranges; rule with no name/description. **Why:** H8, H21. **Detect:** rule exports.
✅. **Severity:** Critical for any→any inbound; High for any source to an internal service; Low for a
missing description alone. *(NET-01, NET-02)*

#### Public IP on compute without a public role
**What:** A VM/instance with a public IP that serves nothing publicly, including "for testing" or on a
host also linked by site-to-site VPN. **Why:** H7, H9. **Detect:** public IP inventory vs. load
balancer/WAF backends. ✅. **Severity:** High. *(NET-03)*

#### Flat or shared network
**What:** Products sharing subnets; prod and non-prod peered with full routing; one VNet/VPC for
everything; overlapping CIDRs across peers. **Why:** H1. **Detect:** subnet → product map from tags,
peering/route tables, CIDR overlap check. ✅. **Severity:** High for prod↔non-prod routing; Medium
otherwise. *(NET-06, NET-07)*

#### Data service on a public endpoint
**What:** Storage, database, key store or queue with public network access enabled, firewall
`0.0.0.0–255.255.255.255`, or "allow all cloud services". **Why:** H7, H13. **Detect:** resource
network settings export. ✅. **Severity:** High; Critical with anonymous or key-only access to
confidential data. *(NET-08)*

#### Uncontrolled egress
**What:** Data-tier hosts with direct internet egress; no fixed egress IP where a partner allow-lists
one. **Why:** H2, H8. **Detect:** route tables (default route to IGW), NAT presence, egress rules
allowing `0.0.0.0/0` on all ports. ✅. **Severity:** Medium; High for restricted data. *(NET-09)*

#### Weak SSH configuration
**What:** `PermitRootLogin yes`, `PasswordAuthentication yes`, `PermitEmptyPasswords yes`, high
`MaxAuthTries`, legacy ciphers/MACs/KEX, no `AllowUsers`/`AllowGroups`. **Why:** H5, H9. **Detect:**
`sshd -T` (effective config, not the file). ✅. **Severity:** High; Critical when port 22 is public
and passwords are on. *(NET-13)*

#### No host firewall
**What:** Host relies only on the cloud firewall; `nft list ruleset` empty; default policy ACCEPT;
IPv6 open. **Why:** H2, H8. **Detect:** firewall commands per distro. ✅. **Severity:** Medium; High
on hosts with a public IP. *(NET-12)*

#### Plaintext or legacy protocols
**What:** FTP, Telnet, rsh, SMBv1, LDAP without TLS, SNMP v1/v2c with public communities, HTTP
without redirect. **Why:** H7, H11. **Detect:** listeners and their ports; config files. ✅.
**Severity:** High on public interfaces; Medium internal. *(NET-11)*

#### Missing DDoS / WAF on internet-facing HTTP
**What:** Public web endpoints with no WAF, no rate limiting, no DDoS protection on the network.
**Why:** H2. **Detect:** front-door/LB configuration, DDoS plan association. ✅. **Severity:**
Medium; High for revenue-critical endpoints. *(NET-10)*

#### Open egress / two-way trust
**What:** Servers with outbound `ACCEPT` by default; exposed-tier hosts able to open SSH, RDP or
database sessions into the internal tier. **Why:** H27, H1. **Detect:** host OUTPUT policy; cloud
egress rules from exposed subnets to internal CIDRs. ✅. **Severity:** High for exposed tiers; Medium
internal.  *(NET-15, NET-16)*

#### Unlogged, unordered or irreversible firewall
**What:** Refused traffic not logged (or logged without a budget); invalid state not dropped; rules
loaded after networking or not persisted; remote edits with no rollback; all ICMP dropped (breaks
path-MTU and IPv6) or all ICMP allowed; no `rp_filter`. **Why:** H19, H8, H24. **Detect:**
ruleset, unit ordering, sysctls. ✅. **Severity:** Medium. *(NET-17, NET-18, NET-19)*

#### Unknown hosts on your own ranges
**What:** A discovery scan the user supplied shows hosts or ports missing from the asset register.
**Why:** H21. **Detect:** diff scan output against the register. ✅ with scan output; 🔬 without.
**Severity:** High for an unknown internet-facing listener; Medium otherwise. *(NET-20)*

### Checklist
1. Exposure points with a default-deny policy behind them.
2. Allow rules naming source, destination, port and protocol (no `any`).
3. Allow rules with a name and description.
4. Administrative interfaces reachable only through a private path.
5. Compute without a public IP unless it has a public role.
6. Products in their own networks; prod and non-prod not routed together.
7. Data services reached privately, public access disabled.
8. Egress controlled for data tiers.
9. SSH effective config meeting NET-13.
10. Hosts with an active host firewall.
11. Server tiers egress-filtered; exposed tiers cannot initiate admin sessions inward.
12. Refused traffic logged within a budget; firewall ordered before networking and persisted.
13. Own-range discovery results reconciled with the register.

---

## 3. data — what is stored and how it's protected

In scope: disks/volumes, snapshots, buckets/shares, databases, key stores, certificates, secret
stores.

### 🟢 Well done
- Everything encrypted at rest; customer-managed keys for confidential and restricted data (H11, H12).
- TLS 1.2+ everywhere, internal included; certificates auto-renewed (H11, H6).
- Secrets in a store, read by workload identity; none in files or images (H12).
- Stores private by default; delegated URLs short-lived and scoped (H13).

### 🔴 Not well done

#### Public data store
**What:** Bucket/container/share/snapshot readable anonymously, or shared with "anyone with the
link". **Why:** H13. **Detect:** public-access settings, bucket policies with `"Principal": "*"`,
`allUsers`, container access level `blob`/`container`, public snapshots. ✅. **Severity:** Critical
with non-public data; Low for genuinely public content with integrity controls. *(DAT-05)*

#### Secret in plain text
**What:** Passwords, keys, connection strings in config files, env files, user data, images,
scripts, VCS, or readable by users other than the service. **Why:** H12. **Detect:** secret scanners
(gitleaks, trufflehog), `grep` patterns, file modes. ✅ — never copy the value. **Severity:**
Critical when readable beyond the service or committed; High otherwise. *(DAT-04)*

#### Unencrypted at rest
**What:** Volumes, snapshots, databases or buckets without encryption; temp/cache disks excluded from
encryption on platforms that offer host-level encryption. **Why:** H11. **Detect:** resource
encryption flags; `lsblk -o NAME,TYPE,FSTYPE` (no `crypt`) on-prem. ✅. **Severity:** High in prod;
Medium non-prod. *(DAT-01)*

#### Weak transport
**What:** TLS < 1.2 accepted; weak suites; self-signed or expired certificates in prod; HSTS absent
on public web; internal plaintext. **Why:** H11. **Detect:** `openssl s_client`, `testssl.sh`/`sslyze`
output, endpoint minimum-TLS settings. ✅. **Severity:** High for public endpoints; Medium internal.
*(DAT-02)*

#### Over-broad delegated access
**What:** SAS/presigned/signed URLs or PARs valid > 12 months, account-wide, or with write+delete when
read is needed; account keys handed to tools or partners. **Why:** H6, H13. **Detect:** stored access
policies, SAS in config, key-access logs. ✅ when the token is in evidence. **Severity:** High.
*(DAT-06, DAT-07)*

#### No customer-managed keys for sensitive data
**What:** Confidential/restricted data encrypted only with provider-managed keys where the regime
requires CMK; key rotation off; key deletion unprotected. **Why:** H12. **Detect:** encryption
settings, key policy, purge protection flag. ✅. **Severity:** Medium; High where regulation
requires it. *(DAT-03)*

#### Database access not nominative or not restricted
**What:** Apps and humans sharing one login; DB reachable from broad networks; no audit. **Why:** H3,
H4, H19. **Detect:** DB user list, firewall rules, audit settings. ✅. **Severity:** High. *(DAT-08)*

#### Real data in lower tiers
**What:** Production data copied into dev/test/sandbox without masking. **Why:** H1, H13. **Detect:**
⚠️ from data volumes and refresh jobs; ✅ when sampled data is evidently real. **Severity:** High.
*(DAT-10)*

#### Optional or unauthenticated TLS
**What:** Databases accepting plaintext connections; clients with `sslmode=prefer`/`require` but no
verification; mail submission allowing AUTH before TLS; plaintext backends behind a TLS terminator;
no HSTS; a hand-written cipher string with legacy suites. **Why:** H26. **Detect:** `pg_hba.conf`
`host` lines, MySQL `require_secure_transport`, `smtpd_tls_auth_only`, server TLS config. ✅.
**Severity:** High for credentials or confidential data in transit; Medium otherwise. *(DAT-11, DAT-13)*

#### Certificates by hand, CA keys in the wrong place
**What:** No renewal automation or expiry alert; private keys world- or group-readable beyond the
service; an issuing CA's private key on a service host; RSA-1024 or SHA-1 signatures. **Why:** H6,
H26. **Detect:** renewal timers, key file modes, `find` for CA keys, certificate text. ✅.
**Severity:** High for a CA key on a service host; Medium for manual renewal. *(DAT-12, DAT-14)*

#### Secrets left in memory images
**What:** Unencrypted swap or hibernation image, world-readable crash dumps, `fs.suid_dumpable`
non-zero on hosts holding confidential data; disks decommissioned without crypto-erase. **Why:** H11,
H12. **Detect:** `swapon`, `sysctl`, `/var/crash` modes; decommission records. ✅/🔬. **Severity:**
Medium; High for restricted data. *(DAT-15, DAT-16)*

### Checklist
1. Stores encrypted at rest.
2. Confidential/restricted stores with customer-managed keys and rotation.
3. Endpoints at TLS 1.2+ with valid, auto-renewed certificates.
4. Secrets only in the secrets store.
5. Stores with public access blocked.
6. Delegated URLs short-lived and scoped; no account keys in apps.
7. Databases with nominative, network-restricted, audited access.
8. Non-prod free of unmasked real data.
9. TLS required and peers verified for database, mail submission and internal backends.
10. Certificates renewed automatically with an expiry alert; CA keys never on service hosts.
11. Swap, hibernation and dump files encrypted or disabled where confidential data lives.

---

## 4. host — the operating system itself

In scope: hosts, or host roles/images when a fleet is sampled.

### 🟢 Well done
- Role images built by a pipeline, minimal, on a supported release, configured by code (H7, H14).
- Security updates applied automatically or by an update manager on a cadence (H18).
- Permissions tight, SUID set as shipped, MAC enforcing, kernel hardened (H10, H14).
- Required agents present and reporting; time synchronised (H19, H20).

### 🔴 Not well done

#### Unsupported OS release
**What:** A distro release past its security-support window. **Why:** H18. **Detect:**
`/etc/os-release` vs vendor lifecycle. ✅. **Severity:** High; Critical when internet-facing.
*(HST-02)*

#### Pending security updates
**What:** Security updates outstanding beyond the window; reboot-required for weeks; host not
enrolled in the update manager. **Why:** H18. **Detect:** per-distro security-update listing;
`needs-restarting -r`, `/var/run/reboot-required`; update-manager compliance. ✅. **Severity:** High
for critical/known-exploited; Medium otherwise. *(HST-03)*

#### Untrusted package sources
**What:** `gpgcheck=0`, `[trusted=yes]`, `SigLevel = Never`, `--allow-untrusted`, HTTP repos,
`curl | sh` in provisioning. **Why:** H14. **Detect:** repo config grep; provisioning scripts. ✅.
**Severity:** High. *(HST-04)*

#### Excess packages and services
**What:** Services enabled/listening that the role doesn't need; compilers, debuggers, network tools
on prod; desktop stacks on servers. **Why:** H7. **Detect:** enabled-unit and package lists vs the
role. ⚠️ (role intent needs judgement). **Severity:** Medium. *(HST-01)*

#### Loose permissions and unexpected SUID
**What:** World-writable files; writable dirs without the sticky bit; shadow readable; unowned files;
SUID/SGID outside the shipped set; home dirs world-readable. **Why:** H10. **Detect:** `find`
recipes; package ownership of each SUID binary. ✅. **Severity:** High for SUID/shadow; Medium
otherwise. *(HST-05, HST-06)*

#### MAC disabled
**What:** SELinux `disabled`/`permissive` on RHEL-family; no AppArmor profiles on Debian/Ubuntu/SUSE.
**Why:** H2, H10. **Detect:** `getenforce`, `aa-status`. ✅. **Severity:** Medium; not applicable
where the distro ships none (record as accepted). *(HST-09)*

#### Weak kernel / mount settings
**What:** IP forwarding on a non-router, redirects accepted, ASLR off, `kptr_restrict`/`dmesg_restrict`
off, `/tmp` without `nodev,nosuid`. **Why:** H10, H14. **Detect:** `sysctl`, `/proc/mounts`. ✅.
**Severity:** Medium; Low for single items on non-prod. *(HST-07, HST-08)*

#### Hand-configured host
**What:** No config management; hosts of one role differing; manual edits in shell history. **Why:**
H14. **Detect:** absence of an agent/playbook; diff between hosts of a role. ⚠️. **Severity:**
Medium. *(HST-14)*

#### Missing or unhealthy agents
**What:** Monitoring, logging, backup, patch or EDR agents absent or not reporting. **Why:** H19, H20.
**Detect:** agent status per platform; last check-in. ✅. **Severity:** Medium; High when it blinds a
prod host entirely. *(HST-11, HST-13)*

#### Privileged containers or nodes
**What:** Containers running as root with `privileged: true`, host network/PID, `CAP_SYS_ADMIN`;
writable root filesystems; nodes not hardened. **Why:** H3, H7 (containers share the host kernel —
LE 011.4, p.72). **Detect:** pod specs, `docker inspect`, `kube-bench`. ✅. **Severity:** High.
*(HST-15)*

#### Unauthenticated boot or out-of-band path
**What:** No boot-loader password where a console is reachable; single-user/rescue without
authentication; Ctrl-Alt-Del unmasked; many old kernels installed; cloud serial-console, snapshot
share or volume-attach rights granted broadly. **Why:** H25. **Detect:** GRUB config, systemd target
state, kernel package count, IAM. ✅. **Severity:** High for broad snapshot-share/attach rights on prod
data; Medium otherwise. *(HST-16)*

#### Unconfined daemons, no ceilings
**What:** Network-facing services running as root or without sandboxing; no memory/task/FD limits;
core dumps on. **Why:** H3, H23. **Detect:** `systemd-analyze security`, unit properties. ✅.
**Severity:** Medium; High for an internet-facing root daemon. *(HST-17, HST-18)*

#### Integrity baseline the attacker can rewrite
**What:** FIM database writable on the host it protects; new files not reported; reports unread;
baseline refreshed after an incident without review. **Why:** H29. **Detect:** FIM config, database
location and mode, last-report timestamps. ✅/⚠️. **Severity:** Medium; High on restricted-data hosts.
*(HST-20)*

### Checklist
1. Hosts on a supported release.
2. Hosts within the patch window, enrolled in update management.
3. Package sources signed and verified.
4. Services and packages limited to the role.
5. Permissions: no world-writable system files, sticky bit on shared dirs, shadow protected.
6. SUID/SGID limited to the shipped set.
7. MAC enforcing where the distro supports it.
8. Kernel and mount hardening applied.
9. Configuration managed as code.
10. Required agents installed and reporting; time synchronised.
11. Containers non-root and unprivileged.
12. Boot, console and out-of-band access authenticated.
13. Network daemons confined and resource-limited.
14. File-integrity baseline tamper-evident and read.

---

## 5. continuity — surviving loss

In scope: stateful assets that must survive loss — databases, volumes, buckets, VMs with state, key
stores, configuration.

### 🟢 Well done
- Every stateful asset has a policy from day one; jobs are monitored (H15).
- Restores are tested on a schedule, in an isolated scope, timed against RTO (H15, H1).
- At least one copy is immutable and outside the source's blast radius (H16).
- Deletion locks on everything critical (H17).

### 🔴 Not well done

#### No backup
**What:** A stateful prod asset with no backup policy. **Why:** H15. **Detect:** backup-protected item
list vs the asset register. ✅. **Severity:** Critical for prod data; Medium for rebuildable state.
*(CON-01)*

#### Backups never restored
**What:** No restore test record within the retention period; no RPO/RTO stated. **Why:** H15.
**Detect:** restore logs, runbooks, test tickets. 🔬 if the evidence isn't shared; ✅ when the user
confirms none exists. **Severity:** High. *(CON-03, CON-09)*

#### Mutable or co-located backups
**What:** No vault lock/immutability/object lock; soft-delete off; vault in the same account with the
same admins as the source. **Why:** H16. **Detect:** vault settings, role assignments on the vault.
✅. **Severity:** High. *(CON-05, CON-06)*

#### Failing jobs nobody sees
**What:** Backup jobs in failed/warning state; no alert on failure. **Why:** H15, H20. **Detect:** job
history, alert rules. ✅. **Severity:** High. *(CON-02)*

#### Restores over the live asset or left behind
**What:** Restores performed in place, or restored copies left running in random resource groups.
**Why:** H1, H13. **Detect:** restore history targets; resources tagged/named as restores outside the
restore scope; non-empty restore scope with old items. ✅. **Severity:** Medium; High when a restored
copy of confidential data is exposed. *(CON-04)*

#### Retention mismatch
**What:** Retention shorter than RPO/contract/legal hold, or far longer than needed for personal data.
**Why:** H15, H13. **Detect:** policy vs contract. ✅. **Severity:** Medium. *(CON-07)*

#### No deletion protection
**What:** Critical resources (CON-08 list) without locks or deny-delete; key stores without purge
protection. **Why:** H17. **Detect:** lock and policy exports, resource flags. ✅. **Severity:**
High for prod data stores and vaults; Medium for network resources. *(CON-08, CON-10)*

#### Backups whose scope nobody checked
**What:** No manifest of what is backed up, or one that omits databases, configuration, custom
software or keys present in the register; no declared standby tier; restores never run in a
production-like mirror. **Why:** H15. **Detect:** manifest vs register; restore records. ✅/🔬.
**Severity:** High when a prod data store is missing from scope. *(CON-03, CON-11, CON-12)*

### Checklist
1. Stateful assets with a backup policy.
2. Backup jobs succeeding and alerting on failure.
3. Data classes with a restore test inside the retention period.
4. Restores done in an isolated scope and cleaned up.
5. Immutable, locked copies for prod.
6. Copies isolated from the source's credentials.
7. Retention matching RPO and legal requirements.
8. Critical resources deletion-protected.
9. Backup scope manifest matches the asset register.
10. Standby tier declared and failover proven for tier-1 assets.

---

## 6. monitoring — seeing and responding

In scope: every host and every account (as log and patch sources).

### 🟢 Well done
- Control-plane audit logs on everywhere, retained ≥ 1 year, outside the account admins' reach (H19).
- Host auth and privilege logs shipped off-host; OS audit rules on prod (H19).
- Alerts route to owned channels with an on-call; a SIEM with detections covers prod (H20).
- Posture tool and vulnerability scans run; findings tracked to closure (H18).

### 🔴 Not well done

#### Audit logging off or short
**What:** Control-plane audit disabled in an account/region; retention of days; logs writable by
workload roles. **Why:** H19. **Detect:** trail/diagnostic settings export, log bucket policy. ✅.
**Severity:** High. *(MON-01)*

#### Host logs only on the host
**What:** No forwarding; volatile journal; no auth log. **Why:** H19. **Detect:** rsyslog/journald
upload/agent config; `/var/log/journal` presence. ✅. **Severity:** Medium; High on internet-facing
hosts. *(MON-02)*

#### No OS audit on prod
**What:** `auditd` absent or without rules for identity files, sudoers, SSH config, privileged
commands, time changes. **Why:** H19. **Detect:** `auditctl -s`, `auditctl -l`. ✅. **Severity:**
Medium. *(MON-03)*

#### Alerts to nowhere
**What:** Alert rules with no action group/route, routes to an unmonitored mailbox, or none at all.
**Why:** H20. **Detect:** alert rule and notification exports. ✅ for no route; 🔬 for "nobody reads
it". **Severity:** High for security detections; Medium for health. *(MON-04, MON-06)*

#### Vulnerabilities untracked
**What:** No scanner; findings without owners or SLAs; posture recommendations never triaged or
auto-applied blind. **Why:** H18, H22. **Detect:** scanner config and finding ages; posture score
history. ✅/⚠️. **Severity:** High when known-exploited items are open. *(MON-05, MON-07)*

#### Patch compliance unreported
**What:** Nobody knows which machines are off schedule. **Why:** H18. **Detect:** update-manager
compliance report absent. ✅. **Severity:** Medium. *(MON-08)*

#### No plan for the compromised host
**What:** No incident plan, no named person who may isolate a host, no evidence runbook; cloud disks
deleted on stop; logs only on the host. **Why:** H28, H19. **Detect:** runbook, contact list, disk
delete-on-termination flags. ✅ for the flags; 🔬 for the plan unless supplied. **Severity:** High for
prod. *(MON-10, MON-11)*

#### Persistence points never diffed
**What:** No stored baseline of SUID, UID 0, timers, enabled units, `authorized_keys`,
`ld.so.preload`, modules; nobody would notice a new one. **Why:** H29. **Detect:** baseline file and
diff job. ✅. **Severity:** Medium. *(MON-12)*

#### Logs that can be edited or dropped
**What:** UDP syslog; `/var/log` on the root filesystem; audit rules not locked; no advisory loop or
exposure review. **Why:** H19, H18, H21. **Detect:** forwarding config, `findmnt /var/log`,
`auditctl -s`. ✅. **Severity:** Medium. *(MON-02, MON-13, MON-14, MON-15)*

### Checklist
1. Accounts with control-plane audit logs on and retained ≥ 1 year, tamper-resistant.
2. Hosts forwarding auth/system logs off-host.
3. Prod hosts with OS audit rules.
4. Assets with health alerts routed to an owned channel.
5. Prod covered by a SIEM with security detections and an on-call.
6. Hosts and images scanned for vulnerabilities at least weekly.
7. Patch compliance reported each cycle.
8. Incident plan and host evidence runbook exist; disks survive stop where forensics matter.
9. Persistence points diffed against a stored baseline.
10. Logs forwarded over TCP/TLS, protected locally, audit rules locked.
11. Advisories tracked to closed tickets; external exposure reviewed quarterly.

---

## 7. governance — ownership, change and evidence

In scope: accounts/subscriptions/projects, resource containers, and the resources tag and lock
criteria apply to.

### 🟢 Well done
- Tiers in separate accounts; one container per product/client; names and tags readable and
  enforced by policy (H1, H21).
- Locks on every prod container and critical resource (H17).
- Changes, exceptions and access requests through tickets approved by a security owner; prod
  promotion reviewed against the baseline; evidence filed by control ID (H22).

### 🔴 Not well done

#### Tiers mixed in one account
**What:** Prod and non-prod resources in one subscription/account/project. **Why:** H1. **Detect:**
`environment` tag distribution per account; naming. ✅. **Severity:** High. *(GOV-01)*

#### Missing or unenforced tags
**What:** Resources without `owner`, `product`, `client`, `environment`, `data-class`, `category`; no
policy requiring them. **Why:** H21. **Detect:** tag coverage query; policy assignments. ✅.
**Severity:** Medium; High when untagged resources can't be attributed during an incident. *(GOV-04)*

#### Naming chaos
**What:** No convention, or one followed by a minority of resources; uppercase/spaces where the
convention says otherwise. **Why:** H21. **Detect:** name regex coverage. ✅. **Severity:** Low.
*(GOV-03)*

#### No deletion lock on prod containers
**What:** Resource groups/projects/accounts holding prod with no lock or deny-delete policy. **Why:**
H17. **Detect:** lock export. ✅. **Severity:** High. *(GOV-05)*

#### Uncontrolled change
**What:** Firewall, IAM or network changes with no ticket; exceptions with no approver or expiry;
access granted by the requester's manager alone; prod launched without a readiness review. **Why:**
H22. **Detect:** activity log vs ticket references; exceptions register. ⚠️ (correlation needs
judgement). **Severity:** Medium; High for privilege grants. *(GOV-06, GOV-07, GOV-08)*

#### No evidence trail
**What:** Verification output not kept, or kept without control ID and date. **Why:** H22. **Detect:**
evidence repository contents. ✅. **Severity:** Medium. *(GOV-09)*

#### Configuration names drift across environments
**What:** The same setting named differently per environment, so deploys need per-env edits. **Why:**
H14, H22. **Detect:** app settings / env var keys per environment. ✅. **Severity:** Low; Medium when
it has caused a misdeploy. *(GOV-10)*

#### Active testing without scope
**What:** Scanners, password audits, relay or zone-transfer tests run against systems nobody named,
without permission or a window. **Why:** H22. **Detect:** scan logs vs scope records. ✅/🔬.
**Severity:** Medium; High when production was disrupted. *(GOV-12)*

### Checklist
1. Accounts holding a single tier.
2. Resources inside a product/client container.
3. Resources following the naming convention.
4. Resources carrying every mandatory tag; tags enforced by policy.
5. Prod containers and critical resources deletion-locked.
6. Changes and exceptions traceable to an approved ticket.
7. Evidence stored by control ID.
8. Active testing scoped, authorised and windowed.

---

## 8. service — the roles a host runs

In scope: service instances by role — web, mail, DNS, database, file transfer/NFS, VPN/bastion. A
host with no such role has no service evaluation. The seven core domains still grade the host
underneath.

### 🟢 Well done
- Each daemon unprivileged and confined, its own ACL mirroring the firewall (H27, H3).
- Helper functions denied by default: no relay, no recursion on authoritative servers, no open
  transfers, no `VRFY` (H27).
- TLS required and peers verified wherever credentials or data travel (H26).
- Domain authentication (SPF, DKIM, DMARC) and DNSSEC staged to enforcement with monitoring (H24).

### 🔴 Not well done

#### Open mail relay
**What:** The MTA accepts mail for external destinations from unauthenticated clients; `mynetworks`
wide; AUTH allowed before TLS. **Why:** H27, H26. **Detect:** `postconf -n`; an authorised external
relay test. ✅. **Severity:** High; Critical if it is relaying abuse now. *(SVC-MAIL-01, SVC-MAIL-02)*

#### Unauthenticated domain mail
**What:** No SPF, DKIM or DMARC; DMARC stuck at `p=none` with no `rua` monitoring; DKIM keys < 2048
bits or never rotated. **Why:** H24, H11. **Detect:** DNS TXT records. ✅. **Severity:** Medium;
High for a domain used in customer communication. *(SVC-MAIL-03)*

#### Recursive or transferring authoritative DNS
**What:** An authoritative server answers recursive queries or zone transfers to the internet;
transfers unsigned or signed with HMAC-MD5; a fixed query source port. **Why:** H27, H1. **Detect:**
`named-checkconf -p`; authorised external `dig` tests. ✅. **Severity:** High. *(SVC-DNS-01..03)*

#### DNSSEC or certificates about to expire
**What:** RRSIG expiry within days with no automated re-signing; DS mismatched; certificates within
21 days of expiry. **Why:** H6. **Detect:** `dig +dnssec`, `openssl x509 -checkend`. ✅. **Severity:**
High (an outage is imminent). *(SVC-DNS-05, DAT-12)*

#### Reachable database without account hygiene
**What:** A database account with no password or an anonymous user, reachable over the network;
`trust` or `md5` auth; one shared credential for several applications; `user@%` grants. **Why:** H3,
H5. **Detect:** `pg_hba.conf`, `mysql.user`. ✅. **Severity:** Critical for an anonymous or
empty-password account reachable from any network; High otherwise. *(SVC-DB-01..04)*

#### Writable docroot, weak web credentials
**What:** The web worker owns or can write the document root; `htpasswd` with MD5/`apr1`; credential
files inside the docroot; basic auth over HTTP; WAF in detect-only with no promotion date. **Why:**
H3, H10, H24. **Detect:** `ps`, `find -perm`, htpasswd hash prefixes, `SecRuleEngine`. ✅.
**Severity:** High for a writable docroot on an internet-facing host; Medium otherwise.
*(SVC-WEB-01..03)*

#### Plain FTP or loose NFS
**What:** FTP with credentials on a public interface; NFS exports to `*` or with `no_root_squash`.
**Why:** H11, H3. **Detect:** listeners on 21; `exportfs -v`. ✅. **Severity:** High. *(SVC-FILE-01,
SVC-FILE-02)*

#### VPN or bastion without revocation or forwarding policy
**What:** VPN credentials that can't be revoked per user (shared certificate, no CRL); the CA key on
the VPN server; bastions allowing arbitrary TCP forwarding or tunnels; outbound SSH from the data
tier. **Why:** H4, H9, H27. **Detect:** VPN config, `sshd -T`. ✅. **Severity:** High. *(SVC-VPN-01,
SVC-VPN-02)*

### Checklist
1. Service daemons unprivileged, confined, with an in-service ACL.
2. Mail: no open relay, AUTH only inside TLS, `VRFY`/`EXPN` off.
3. Mail domains: SPF, DKIM, DMARC published and progressing to enforcement.
4. DNS: authoritative/recursive split; transfers named and signed; rate limiting on.
5. DNSSEC and certificates renewed automatically with expiry alerts.
6. Databases: private listener, no anonymous/empty accounts, per-app least-privilege credentials, TLS required.
7. Web: read-only docroot, bcrypt credentials outside it, WAF enforcing.
8. No plain FTP; NFS exports narrow and root-squashed.
9. VPN credentials individually revocable; bastion forwarding restricted.
