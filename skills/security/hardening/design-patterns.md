# Design Patterns — The Baseline Catalogue, Platform Mapping, Conventions

> What Design mode chooses from. §2 is the control catalogue a baseline starts from; §3–§4 map each
> control onto each distro and each cloud; §5–§7 are how a baseline is verified, named and excepted; §8–§10 are the admin-workstation
> overlay, the threat tier, and the measures this baseline deliberately does not adopt. The
> **service** domain in §2 applies only to hosts that run the role.
> Cite the principle (H-N, [`theory.md`](theory.md)) when you adopt, tighten, relax or drop a
> control; say why when you deviate from the default.
>
> Everything here is written with placeholders — `<org>`, `<product>`, `<client>`, `<env>`,
> `<region>` — so the baseline fits any organisation. A baseline that hard-codes one company's
> names, one distro's paths or one cloud's product names is a baseline nobody else can adopt.

---

## §1 Tiers and data classes

A control's level comes from the **tier** of the environment and the **class** of data it holds.
Pick both per asset before grading or designing.

| Tier | Meaning | Default posture |
|---|---|---|
| **prod** | Serves real users or holds real data | Every **R** control enforced, exceptions time-bound and approved |
| **non-prod** | Shared dev/test/staging; may hold copies of real data | **R** controls enforced unless the column says otherwise; real data in non-prod is promoted to prod's level |
| **sandbox** | Individual, disposable, no real data, no connectivity to prod | Identity, exposure and cost controls only; isolated from prod by network and account |

| Data class | Examples | Raises |
|---|---|---|
| **public** | Marketing site content, published docs | Integrity controls only |
| **internal** | Internal tooling, non-sensitive business data | Default levels |
| **confidential** | Customer data, contracts, source code, credentials | Encryption with managed keys, private endpoints, access reviews |
| **restricted** | Regulated data (payment, health, national ID), key material | All of the above plus customer-managed keys, immutable backups, dedicated accounts, access logging read by a human |

Levels in §2: **R** required · **Rec** recommended · **—** not required. "R (conf+)" means required
when the data class is confidential or restricted.

---

## §2 The control catalogue

Each control: **ID**, the statement, level per tier (prod / non-prod / sandbox), and the principle.
The verification for each is in [`detection-signals.md`](detection-signals.md) under the same ID.

### identity — who and what can act

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| IDN-01 | Every human identity is **nominative** (one person, one account); no shared admin accounts; no daily use of `root`/built-in owner/break-glass accounts | R | R | R | H4 |
| IDN-02 | **MFA** on every human sign-in to the cloud control plane, VPN, bastion and identity provider; phishing-resistant (FIDO2/passkey, platform authenticator) for privileged roles | R | R | R | H5 |
| IDN-03 | **Separate identities per tenant/organisation and per tier** — an operator's prod identity is not their non-prod identity, and accounts are not shared across tenants | R | Rec | — | H1, H4 |
| IDN-04 | Account names follow one convention that encodes tier and affiliation (§6.3); the same rule applies to database users | R | R | Rec | H4, H21 |
| IDN-05 | Every human is in at least one **purpose-named group**; permissions are granted to groups or roles, never to individuals directly; empty or unused groups are removed | R | R | Rec | H3, H21 |
| IDN-06 | **Least privilege**: role assignments at the narrowest scope that works; no Owner/`*:*`/project-owner for daily operations; privileged roles are just-in-time or time-bound where the platform supports it | R | R | Rec | H3 |
| IDN-07 | **Workload identities** (managed identity, instance profile, workload identity federation, service account with no key) for service-to-service and service-to-cloud access; no long-lived keys in code or config | R | R | Rec | H6, H12 |
| IDN-08 | Where a client secret or API key is unavoidable: stored in the secrets store, scoped, **expiry ≤ 12 months**, owner recorded, rotated before expiry | R | R | Rec | H6 |
| IDN-09 | **Default and built-in accounts** disabled, renamed or locked (database `sa`/superuser remote login, vendor default users, guest); default passwords changed before first exposure | R | R | R | H5, H7 |
| IDN-10 | Human database/OS passwords where federation is impossible: **≥ 14 characters, randomly generated**, rotated ≤ 180 days or on role change; lockout after repeated failures | R | R | Rec | H5, H6 |
| IDN-11 | **Privileged access via `sudo` (or the platform's elevation)** with per-user rules, logged; no `NOPASSWD: ALL` for humans; root login disabled locally where policy allows | R | R | Rec | H3, H4, H19 |
| IDN-12 | **Access reviews**: privileged assignments and group memberships reviewed at least quarterly; leavers removed the same day; an account with a locked password but a populated `authorized_keys` still logs in — lock both | R | Rec | — | H3, H21 |
| IDN-13 | **Conditional access**: sign-in restricted by device posture, network location or geography where the identity provider supports it | Rec | Rec | — | H2, H5 |
| IDN-14 | **Breached-credential monitoring**: the organisation's domains are subscribed to breach notification; new passwords are screened against a breached-password list | R | Rec | — | H5, H6 |
| IDN-15 | **Command-scoped sudo**: rules name exact commands and target users — no `ALL`, wildcards, negations (`!/bin/su`) or shell/editor escapes; `logfile`/`log_input`/`use_pty` set; short `timestamp_timeout` | R | R | Rec | H3, H19 |
| IDN-16 | **Central directory for fleet logins** (SSSD over LDAPS, Kerberos, or IdP-issued short-lived SSH certificates) so a leaver is one action; clocks synchronised and directory traffic encrypted | R (fleet) | Rec | — | H4, H6 |
| IDN-17 | **PAM stack reviewed**: catch-all `other` denies; no `nullok`; no `pam_rhosts`, `.rhosts` or `hosts.equiv`; `su` limited by `pam_wheel`; `sufficient` modules ordered deliberately; `pam_access` for origin limits | R | R | Rec | H3, H5 |
| IDN-18 | **Sealed service accounts**: no password, no shell any daemon accepts (a shell listed in `/etc/shells` is accepted by FTP/Samba), no SSH; virtual users for mail and file services | R | R | Rec | H3, H7 |
| IDN-19 | **SSH second factor done right**: `UsePAM yes`, `AuthenticationMethods publickey,keyboard-interactive`, no `nullok` on the factor module | R | R | — | H5 |

### network — what is reachable from where

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| NET-01 | **Default deny inbound** at every layer (cloud firewall/security group, host firewall); every allow rule names source, destination, port and protocol | R | R | R | H8 |
| NET-02 | **No `any`** as source, destination, port or protocol in an allow rule, except an explicit public listener (443 on a load balancer/WAF); every rule has a **name and a description** a stranger can understand | R | R | Rec | H8, H21 |
| NET-03 | **No public IP on compute** that isn't a deliberate public endpoint; public traffic enters through a load balancer, WAF or API gateway | R | R | Rec | H7, H9 |
| NET-04 | **No administrative interface (SSH, RDP, database, cluster API, management console) reachable from the internet.** Admin access goes through a bastion/jump host, VPN, private endpoint or identity-aware proxy | R | R | R | H9 |
| NET-05 | Where a client uses an **allow-list**, rules admit only the listed source addresses — never "temporarily" wider | R | R | — | H8 |
| NET-06 | **Segmentation per product/component**: a product's compute, data and endpoints sit in its own network/subnets; products don't share subnets; prod and non-prod networks don't route to each other | R | R | R | H1 |
| NET-07 | **Address plans don't overlap** across accounts, sites and VPN peers; subnets are sized per component, honouring each provider's minimums for platform subnets | R | R | Rec | H1 |
| NET-08 | Data services (object storage, databases, key stores, queues) reached over **private endpoints / service endpoints / private service access**; public network access disabled | R (conf+) | Rec | — | H7, H13 |
| NET-09 | **Controlled egress**: outbound traffic through a NAT gateway, proxy or egress firewall; a fixed egress IP when a partner allow-lists it; egress to the internet denied by default for data tiers | R | Rec | — | H2, H8 |
| NET-10 | **DDoS protection** on public endpoints and the networks behind them; **WAF** in front of internet-facing HTTP | R | Rec | — | H2 |
| NET-11 | Only **required protocols** exposed: HTTPS (443) for web, SFTP/FTPS (never plain FTP/Telnet) for file transfer | R | R | R | H7, H11 |
| NET-12 | **Host firewall** active (nftables/iptables via firewalld, ufw or direct rules; Windows Firewall) as a second layer behind the cloud firewall | R | Rec | — | H2 |
| NET-13 | **SSH hardened**: key or certificate auth only, `PermitRootLogin no`, `PasswordAuthentication no`, `MaxAuthTries` ≤ 4, idle timeout, allow-listed users/groups, modern ciphers/KEX/MACs only | R | R | R | H5, H9 |
| NET-14 | Site-to-site VPN/interconnect: named per client, dedicated gateway, strong IKE/IPsec suites, the client's routes advertised narrowly | R | R | — | H1, H11 |
| NET-15 | **Per-host egress allow-list**: server tiers drop outbound by default and list destinations (resolvers, time, mirrors, named APIs); no blanket "new outbound" rule | R | Rec | — | H8, H27 |
| NET-16 | **One-way admin trust**: hosts in an exposed tier cannot open SSH, RDP or database sessions into the internal tier | R | R | — | H1, H27 |
| NET-17 | **Refused traffic is logged** with a per-rule prefix and a volume budget; invalid conntrack state dropped; cloud flow logs on | R | Rec | — | H19, H8 |
| NET-18 | **ICMP minimum and anti-spoofing**: only needed ICMP/ICMPv6 types (path-MTU, neighbour discovery) allowed, echo rate-limited; bogon and impossible sources dropped on public interfaces; `rp_filter` on, `log_martians` on | R | Rec | — | H8 |
| NET-19 | **Firewall ordering and reversible change**: rules load before networking and persist across reboot (running = persisted); remote changes are test-then-commit with an automatic rollback | R | Rec | — | H14, H24 |
| NET-20 | **Own-range discovery**: scheduled, authorised scans of your own address space, diffed against the asset register; unknown hosts and ports are findings. An **active probe** — the user runs it; the skill reads the output | R (weekly) | Rec | — | H20, H21 |

### data — what is stored and how it's protected

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| DAT-01 | **Encryption at rest** for every disk, volume, snapshot, bucket and database — AES-256 or the platform equivalent; host-level/temp-disk encryption where the platform offers it | R | R | R | H11 |
| DAT-02 | **Encryption in transit**: TLS 1.2 minimum (1.3 preferred) on every endpoint, internal included; plaintext protocols disabled; HSTS on public web | R | R | Rec | H11 |
| DAT-03 | **Customer-managed keys** in the platform key service (or HSM) for confidential and restricted data; key rotation enabled; key deletion protected | R (conf+) | Rec | — | H12 |
| DAT-04 | **Secrets, connection strings, integration credentials and TLS certificates** live in a secrets store/key vault and are read at runtime by a workload identity; none in code, images, env files or VCS | R | R | R | H12 |
| DAT-05 | **Object storage is private**: public access blocked at the account/organisation level; no anonymous read; no direct grants to external users outside the sharing mechanism | R | R | R | H13 |
| DAT-06 | **Delegated access is time-bound**: presigned / SAS / signed URLs and pre-authenticated requests carry the shortest workable lifetime, scoped to one object or prefix and to read or write — **never more than 12 months**, and user-delegated where the platform allows | R | R | Rec | H6, H13 |
| DAT-07 | **Storage account keys / root access keys** are not used by applications; identity-based access instead. Where tooling needs a key (non-prod only), it's rotated and never shared | R | Rec | — | H6, H12 |
| DAT-08 | **Database access** is nominative, network-restricted (firewall + private endpoint), role-based with least privilege, and audited | R | R | Rec | H3, H4, H19 |
| DAT-09 | Containers, buckets, blobs and tables have **clear, purposeful names** and an owner; no "temp", "test2", "backup-old" holding live data | Rec | Rec | — | H21 |
| DAT-10 | **Data minimisation**: real data never copied into non-prod or sandbox without masking/anonymisation and an approval | R | R | R | H1, H13 |
| DAT-11 | **TLS profile from a maintained source** (Mozilla server-side *intermediate*, *modern* where clients allow): TLS 1.2+, AEAD forward-secret suites; never hand-written cipher strings | R | R | Rec | H11, H14 |
| DAT-12 | **Certificate lifecycle automated**: ACME or equivalent renewal timer, alert at ≤ 21 days, complete chain, private key `0600`/`0640` readable by the service group only | R | R | Rec | H6, H12 |
| DAT-13 | **Downgrade resistance**: HTTP redirects to HTTPS with HSTS ≥ 1 year (`includeSubDomains` once inventoried); TLS **required** for database connections and mail submission; clients verify the peer (`verify-full`, `verify required`) | R | R | Rec | H26 |
| DAT-14 | **PKI operation**: issuing-CA keys offline or in KMS/HSM, never on a service host; RSA ≥ 3072 or ECDSA P-256; revocation or short lifetimes; a private CA trusted only by its closed set of peers | R | R | Rec | H26, H12 |
| DAT-15 | **Media sanitisation**: decommissioned disks and volumes are crypto-erased (key destroyed) or vendor secure-erased; `dd` overwrite is unreliable on SSDs and meaningless in the cloud | R | Rec | — | H11, H13 |
| DAT-16 | **Swap, hibernation images, core and crash dumps** encrypted or disabled; crash-dump directories root-only, because memory holds secrets | R (conf+) | Rec | — | H11, H12 |
| DAT-17 | **OCSP stapling** where the issuing CA still supports it | Rec | — | — | H26 |

### host — the operating system itself

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| HST-01 | **Minimal installation**: a role-specific image; packages, services and kernel modules the role doesn't need are absent or disabled; no compilers/debuggers on prod hosts | R | Rec | — | H7 |
| HST-02 | **Supported OS**: the distro release is inside its vendor's security-support window | R | R | Rec | H18 |
| HST-03 | **Automatic security updates** or an update manager enrolment with a defined cadence (monthly baseline; critical/known-exploited within days); reboots scheduled | R | R | Rec | H18 |
| HST-04 | **Packages only from signed, trusted repositories**; GPG checking on; no `curl \| sh` installs on prod; **fail closed** — `localpkg_gpgcheck`/`repo_gpgcheck` on, no `AllowInsecureRepositories` or `--allow-unauthenticated` | R | R | Rec | H14 |
| HST-05 | **File permissions**: no world-writable files outside `/tmp`-like paths; sticky bit on world-writable dirs; `/etc/shadow` (or equivalent) `0640`/`0600`; home dirs not world-readable; sensible `umask` (027/022) | R | R | Rec | H10 |
| HST-06 | **SUID/SGID inventory**: only the distro's expected set; anything else justified or removed by a human — alert on drift against package ownership, never auto-strip (that breaks `su`, `sudo`, `passwd`) | R | R | Rec | H10 |
| HST-07 | **Mount options**: `nodev,nosuid,noexec` on `/tmp`, `/var/tmp`, `/dev/shm` and removable media where the role allows | R | Rec | — | H10 |
| HST-08 | **Kernel and network sysctls**: ASLR on, `kptr_restrict`, `dmesg_restrict`, no IP forwarding unless routing, no source routing/redirects, SYN cookies, `rp_filter`, `fs.protected_*` links/fifos | R | Rec | — | H14 |
| HST-09 | **Mandatory access control** enforcing where the distro supports it (SELinux on RHEL family/Fedora, AppArmor on Debian/Ubuntu/SUSE); runtime mode matches the configured mode; never disabled to troubleshoot | R | Rec | — | H2, H10 |
| HST-10 | **Time synchronised** (chrony, systemd-timesyncd, ntpd) to at least three trusted sources, authenticated (chrony with NTS) or internal — logs and certificates depend on it | R | R | Rec | H19 |
| HST-11 | **Malware/EDR agent** where the platform or data class requires it; file-integrity monitoring per HST-20 | R (conf+) | Rec | — | H20 |
| HST-12 | **Boot and console**: bootloader password or locked config; secure boot where available; no unattended console access; serial console restricted | Rec | — | — | H10 |
| HST-13 | **Required agents/extensions installed and healthy**: monitoring, logging, backup, patch and security agents report in | R | R | — | H20 |
| HST-14 | **Configuration managed as code** (Ansible, Salt, Puppet, Chef, cloud-init, image pipeline); hand-edited hosts are drift | R | Rec | — | H14, H22 |
| HST-15 | **Containers and nodes**: images non-root, read-only root filesystem where possible, no privileged containers, no host network/PID namespaces unless required; nodes hardened like any host | R | R | Rec | H3, H7 |
| HST-16 | **Boot, console and out-of-band access authenticated**: GRUB2 PBKDF2 superuser, single-user/rescue mode requires authentication, `ctrl-alt-del.target` masked, no boot from removable media, old kernels pruned; cloud serial console, snapshot sharing, volume attach and user-data edit granted to named roles only | R | Rec | — | H25 |
| HST-17 | **Network daemons confined**: unprivileged user, minimal capabilities, restricted filesystem view, no new privileges, private `/tmp` — systemd sandboxing (`User`, `NoNewPrivileges`, `CapabilityBoundingSet`, `ProtectSystem`, `PrivateTmp`) replaces chroot | R | Rec | — | H3, H7, H10 |
| HST-18 | **Per-service resource limits** (memory, CPU, tasks, file descriptors), quotas on multi-user hosts, core dumps off outside development | R (exposed) | Rec | — | H23 |
| HST-19 | **Separate filesystems** for `/tmp`, `/var/tmp`, `/var`, `/var/log`, `/home` where the role allows, so mount options apply and growth can't fill root (tmpfs-based cloud images are an exception) | R (role allows) | Rec | — | H10, H19 |
| HST-20 | **Tamper-evident file-integrity baseline**: AIDE or Wazuh built from a known-good state, database off-host or read-only, new files reported, every report read before the baseline is updated | R (conf+) | Rec | — | H29 |
| HST-21 | **ACLs are documented exceptions**: base mode first; every extended ACL justified and restorable from a `getfacl -R` dump | Rec | Rec | — | H3, H10 |
| HST-22 | **Uncommon filesystems and USB storage** kernel modules blacklisted (`install <mod> /bin/false`) where the role doesn't need them | Rec | — | — | H7 |
| HST-23 | **Login banner** stating authorised use, for console and SSH | Rec | Rec | — | H4 |
| HST-24 | **Static paths immutable or read-only** where the role allows (read-only `/usr`, immutable critical configs) — a tripwire, not a substitute for FIM, since root can undo it | Rec | — | — | H10, H29 |
| HST-25 | **Homogeneous fleet**: few distinct OS releases per role; drift from the role's image is a finding | Rec | Rec | — | H30, H14 |

### continuity — surviving loss

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| CON-01 | **A backup policy is attached at creation** — no stateful asset runs a day without one; daily is the minimum for prod | R | Rec | — | H15 |
| CON-02 | **The first backup is verified** the day after it's due, and job status is monitored afterwards; failures alert | R | Rec | — | H15, H20 |
| CON-03 | **Restore tests** on a schedule (at least quarterly per data class) and after every backup design change; the restore goes into a mirror of production, passes the application's functional checks, and is timed against the RTO | R | — | — | H15 |
| CON-04 | **Restores happen in an isolated restore scope** (a dedicated resource group, project, account or network) — never over the live asset; restored resources live only as long as needed and the scope is emptied afterwards | R | R | — | H1, H15 |
| CON-05 | **Backups are immutable and locked** (vault lock, immutable vault, object lock, WORM) for the retention period, with soft-delete on; backup admins can't also delete the vault | R | — | — | H16 |
| CON-06 | **Backups are isolated** from the source's credentials and blast radius: a separate vault/account/region; ransomware on the source can't reach the copy | R | — | — | H16 |
| CON-07 | **Retention** matches the contracted RPO and legal holds; default **30 days** of daily restore points plus short-lived instant-restore snapshots (e.g. 2 days); longer tiers (monthly/yearly) only where required | R | Rec | — | H15 |
| CON-08 | **Deletion protection** on critical resources: compute and its disks, storage accounts/buckets, databases, backup vaults, networks, gateways, VPN connections, public IPs and the containers that hold them | R | Rec | — | H17 |
| CON-09 | **RPO/RTO stated per asset** (and per client contract) and the backup schedule proven to meet them | R | — | — | H15 |
| CON-10 | **Configuration and secrets are recoverable** too: IaC in VCS, key-store soft-delete/purge protection, DNS zones exported | R | Rec | — | H15, H17 |
| CON-11 | **Backup scope manifest**: every data store, configuration, custom-built software and key listed and checked against the asset register | R | Rec | — | H15, H21 |
| CON-12 | **Standby tier declared per asset** (cold / warm / hot) and failover proven against the RTO | R (tier-1) | — | — | H15 |

### monitoring — seeing and responding

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| MON-01 | **Control-plane audit logs** on in every account (who did what, from where) and retained ≥ 1 year (or per regulation) outside the account's own admins' reach | R | R | Rec | H19 |
| MON-02 | **Host logs** (auth, sudo, sshd, kernel, package changes) forwarded off-host over TCP with TLS (or RELP), never plain UDP, to a central store that accepts only named senders; local retention as a buffer only | R | Rec | — | H19 |
| MON-03 | **OS audit** (`auditd`/`auditd`-equivalent rules) for identity files, sudoers, SSH config, privileged commands and time changes on prod; rules persisted in `rules.d`, keyed with `-k`, reviewed with an `aureport` routine | R | — | — | H19 |
| MON-04 | **Metrics, uptime and default alerts** per asset (CPU, memory, disk, health probe, certificate expiry); every alert routes to an owned channel someone reads | R | Rec | — | H20 |
| MON-05 | **Security posture service** enabled (cloud-native posture/CSPM, or an equivalent scanner) and its recommendations triaged — reviewed in context before applying, not auto-applied blind | R | R | Rec | H18, H20 |
| MON-06 | **SIEM/SOC coverage**: security-relevant logs reach a SIEM with detections, and someone is on call for them | R | — | — | H20 |
| MON-07 | **Vulnerability management**: every host and image scanned at least weekly; findings tracked to closure with SLAs by severity; known-exploited first | R | R | Rec | H18 |
| MON-08 | **Patch compliance reported**: machines outside the update schedule are listed and corrected each cycle | R | R | — | H18 |
| MON-09 | **Connection and access auditing**: sign-ins to the cloud, bastion sessions and database logins are logged and reviewed for anomalies | R | Rec | — | H19 |
| MON-10 | **Incident plan before the incident**: an owner, the prosecute-or-not decision, who may isolate or power off a host, contacts, per-platform runbook | R | Rec | — | H20, H28 |
| MON-11 | **Host evidence runbook and forensic readiness**: isolate the network; snapshot (memory where possible) before anyone logs in; image and hash; analyse the copy from a separate host; logs already off-host; disks set to survive stop | R | Rec | — | H28, H19 |
| MON-12 | **Baseline diff of persistence points**: SUID, UID 0, cron/at/timers, enabled units, `authorized_keys`, `ld.so.preload`, kernel modules, promiscuous interfaces — diffed on a schedule against a stored baseline | R | Rec | — | H29 |
| MON-13 | **Local log protection**: `/var/log` on its own filesystem or quota; append-only where supported; audit rules locked (`-e 2`); journal integrity verifiable | R | — | — | H19 |
| MON-14 | **External exposure review** (quarterly): passive internet-scan indexes for your addresses and domains, public repositories and job ads for stack leakage | R | — | — | H9, H21 |
| MON-15 | **Advisory loop**: a team mailbox subscribed to distro and vendor advisories; each relevant advisory becomes a ticket naming the fixed version, closed with evidence | R | Rec | — | H18 |
| MON-16 | **Log triage by exclusion**: known-good patterns suppressed, the remainder delivered to someone who reads it, tuned over time | Rec | — | — | H20 |

### governance — ownership, change and evidence

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| GOV-01 | **Account structure separates tiers**: prod and non-prod in different accounts/subscriptions/projects; sandboxes separate again | R | R | R | H1 |
| GOV-02 | **One resource container per product or client** (resource group, project, compartment, account+tag), holding everything that product owns | R | R | Rec | H1, H21 |
| GOV-03 | **Naming convention** applied to every resource (§6.1) — lower-case, type prefix, product, client, environment | R | R | Rec | H21 |
| GOV-04 | **Mandatory tags** on every resource: `owner`, `product`, `client` (or cost centre), `environment`, `data-class`, `category`; enforced by policy, not by memory | R | R | R | H21 |
| GOV-05 | **Deletion locks / deny-delete policy** on every resource container holding prod, and on the critical resource types in CON-08 | R | Rec | — | H17 |
| GOV-06 | **Who may create what is defined**: compute, networks and identity are created by a named platform owner (or their pipeline), not ad hoc | R | Rec | — | H3, H22 |
| GOV-07 | **Every change, exception and non-standard parameter goes through a ticket** in the change tracker; access requests need approval from the security owner, and unapproved requests are returned | R | R | — | H22 |
| GOV-08 | **Production readiness review**: a product is promoted to prod only with a ticket and a review against this baseline | R | — | — | H22 |
| GOV-09 | **Evidence is retained**: verification output and screenshots are stored in the designated evidence repository, linked to the account and the control ID | R | Rec | — | H22 |
| GOV-10 | **Configuration names are stable across environments** (environment variables, secret names, parameter keys) so the same deploy works everywhere | R | R | Rec | H14, H22 |
| GOV-11 | **Cost and quota guardrails**: budgets and alerts per account; quotas sized so a compromise can't spin up unbounded resources | Rec | R | R | H2 |
| GOV-12 | **Active testing is scoped and authorised**: scanners, password audits, relay and zone-transfer tests run only against named systems, with written permission, from trusted tooling, in an agreed window | R | R | — | H22 |


### service — roles a host runs (applies only where the role exists)

In scope only on hosts that run the role; graded per service instance. The generic controls above
still apply to the host underneath.

| ID | Control | prod | non-prod | sandbox | H |
|---|---|:-:|:-:|:-:|:-:|
| SVC-WEB-01 | Web workers run unprivileged; the document root is root-owned and readable, not writable, by the worker (`755`/`644`, or group-scoped `750`/`640`) | R | R | R | H3, H10 |
| SVC-WEB-02 | Credential files live outside the document root and use bcrypt (`htpasswd -B`), never MD5/`apr1`; basic auth only over TLS | R | R | R | H5, H12 |
| SVC-WEB-03 | WAF with a maintained rule set, promoted from detect to block (H24), logs shipped off-host — a layer, never the only one | R | Rec | — | H2, H24 |
| SVC-WEB-04 | Admin virtual hosts require client certificates from an internal CA, or are network-restricted to the admin path | Rec | Rec | — | H9 |
| SVC-MAIL-01 | Not an open relay: `mynetworks` minimal, relay only for authenticated clients or own destinations; `VRFY`/`EXPN` off; message-size, rate and connection limits | R | R | R | H27 |
| SVC-MAIL-02 | Submission requires SASL **inside** TLS on 587/465 (`smtpd_tls_auth_only`); port 25 inbound only on MX hosts; server-to-server AUTH never reuses system credentials | R | R | Rec | H5, H26 |
| SVC-MAIL-03 | Domain authentication staged per H24: SPF ending `-all` once senders are inventoried (`v=spf1 -all` on non-sending domains); DKIM ≥ 2048-bit with dated selectors rotated with overlap; DMARC from `p=none` to `quarantine`/`reject` with a monitored `rua` | R | R | — | H11, H24 |
| SVC-MAIL-04 | MTA-STS and TLS-RPT published for receiving domains | Rec | — | — | H26 |
| SVC-DNS-01 | Authoritative and recursive roles on separate servers; `recursion no` on authoritative; recursion only for named internal clients | R | R | — | H1, H27 |
| SVC-DNS-02 | Zone transfers only to named secondaries, signed with TSIG `hmac-sha256`; secondaries trust only the named primary | R | R | — | H27 |
| SVC-DNS-03 | Response-rate limiting on anything internet-facing; query logging retained for forensics; source ports randomised (never a fixed query source port) | R | Rec | — | H2, H19 |
| SVC-DNS-04 | Dynamic updates use per-host TSIG keys with `update-policy` narrowed to subdomain and record type; key files `0600` | R | R | — | H3, H6 |
| SVC-DNS-05 | DNSSEC on public zones (where the registrar supports DS) with automated signing, rollover by TTL and an alert well before signature expiry | Rec | — | — | H6, H11 |
| SVC-DNS-06 | Hosts use a validating resolver; registrar lock and CAA records on public domains | Rec | Rec | — | H11 |
| SVC-DB-01 | Listener on loopback or a private address only; the database tier denies egress except to backup targets | R | R | R | H7, H9 |
| SVC-DB-02 | No anonymous or empty-password accounts; the local administrative login is not reachable by every local user | R | R | R | H3, H5 |
| SVC-DB-03 | One database and one credential per application, host-scoped, least privilege (read-only where possible); broader duplicates (`user@%`) removed when tightening | R | R | Rec | H1, H3 |
| SVC-DB-04 | TLS required for client connections (H26); no `trust` or `md5` authentication — SCRAM or federated | R | R | Rec | H5, H26 |
| SVC-DB-05 | Application-side encryption keys held outside the database, the code and world-readable files (a key service); no key-bearing statements in query logs | R (conf+) | Rec | — | H12 |
| SVC-DB-06 | Admin credential files (`~/.my.cnf`, `~/.pgpass`) `0600`; no passwords on command lines | R | R | R | H12 |
| SVC-FILE-01 | No plain FTP: SFTP, FTPS or object storage with signed URLs; any legacy FTP chrooted, with uploads non-executable and a pinned passive range | R | R | — | H11, H7 |
| SVC-FILE-02 | NFS exports narrow (named clients, no `*`), no `no_root_squash`, read-only where possible; clients mount `nosuid,nodev`; Kerberos for NFSv4 | R | R | — | H3, H10 |
| SVC-VPN-01 | Remote-access VPN authenticates per user or device with individually revocable credentials (certificates with a CRL, or an IdP); CA key offline; a unique address pool | R | R | — | H4, H9 |
| SVC-VPN-02 | SSH forwarding is policy: `AllowTcpForwarding`, `GatewayPorts`, `PermitTunnel` restricted on bastions; no outbound SSH from the data tier (a reverse tunnel bypasses a no-inbound perimeter) | R | R | — | H9, H27 |

---

## §3 Linux platform mapping

The control is the same; the mechanism moves. Use the column for each distro in scope; give the
command and file in [`detection-signals.md`](detection-signals.md).

| Concern | Debian / Ubuntu | RHEL / Rocky / Alma / Fedora / Amazon Linux | SUSE / openSUSE | Alpine | Arch |
|---|---|---|---|---|---|
| Package manager | `apt` / `dpkg` | `dnf` (`yum`) / `rpm` | `zypper` / `rpm` | `apk` | `pacman` |
| Automatic security updates | `unattended-upgrades` | `dnf-automatic` (`upgrade_type = security`) | `zypper patch` via systemd timer / `os-update` | `apk upgrade` from cron | none by design — scheduled `pacman -Syu` with review |
| Repo signature checking | `apt` secure by default; no `[trusted=yes]` | `gpgcheck=1` in `/etc/yum.repos.d/*.repo` | `gpgcheck=1` in `/etc/zypp/repos.d/*.repo` | signed `APKINDEX`, keys in `/etc/apk/keys` | `SigLevel = Required` in `pacman.conf` |
| Firewall front-end | `ufw` or `nftables` | `firewalld` (nftables backend) | `firewalld` | `nftables` / `iptables` / `awall` | `nftables` / `iptables` |
| Mandatory access control | AppArmor | SELinux (`enforcing`) | AppArmor (SELinux on newer SLE Micro/Tumbleweed) | none by default | AppArmor optional |
| Password quality | `libpam-pwquality` | `pam_pwquality` + `/etc/security/pwquality.conf` | `pam_pwquality` / `pam_cracklib` | `shadow` + PAM optional | `pam_pwquality` |
| Lockout on failures | `pam_faillock` | `pam_faillock` (`authselect`) | `pam_faillock` | — | `pam_faillock` |
| Init / services | systemd | systemd | systemd | OpenRC (`rc-update`, `rc-service`) | systemd |
| Logs | journald + rsyslog; `/var/log/auth.log` | journald + rsyslog; `/var/log/secure` | journald; `/var/log/messages` | syslog (busybox) `/var/log/messages` | journald |
| OS audit | `auditd` | `auditd` | `audit` | `audit` package | `audit` |
| Time sync | `systemd-timesyncd` or `chrony` | `chronyd` | `chronyd` | `chronyd` / `openntpd` | `systemd-timesyncd` |
| File integrity | `aide` | `aide` | `aide` | `aide` | `aide` |
| Sudo group | `sudo` | `wheel` | `wheel` | `wheel` (`doas` common) | `wheel` |
| Security scanner content | `lynis`; OpenSCAP + SSG Debian/Ubuntu profiles | OpenSCAP `scap-security-guide` (CIS, STIG profiles) | OpenSCAP SSG SLE profiles | `lynis` | `lynis`, `arch-audit` |
| Web server package / user | `apache2` / `nginx`, user `www-data` | `httpd` / `nginx`, user `apache`/`nginx` | `apache2` / `nginx`, user `wwwrun` | `nginx`, user `nginx` | `apache` / `nginx`, user `http` |
| Mail / DNS / DB packages | `postfix`, `bind9`, `unbound`, `postgresql`, `mariadb-server` | `postfix`, `bind`, `unbound`, `postgresql-server`, `mariadb-server` | `postfix`, `bind`, `unbound`, `postgresql-server`, `mariadb` | `postfix`, `bind`, `unbound`, `postgresql`, `mariadb` | `postfix`, `bind`, `unbound`, `postgresql`, `mariadb` |
| Daemon sandboxing | systemd unit hardening (`systemd-analyze security`) | same | same | OpenRC: `command_user`, `capabilities`, `rc_cgroup_*` | same as systemd |
| Known-vulnerable packages | `debsecan`, `apt list --upgradable` | `dnf updateinfo list --security` | `zypper list-patches --category security` | `apk version -l '<'` + secdb | `arch-audit` |

**Init-system note.** Where a check says `systemctl is-enabled X`, the OpenRC form is
`rc-update show | grep X`; `systemctl list-units --type=service --state=running` becomes
`rc-status --servicelist`. Containers usually have no init — grade the image and the orchestrator
instead.

**Windows hosts** are in scope of the same domains (local admin group, RDP exposure, BitLocker,
Windows Update/WSUS, Defender, Event Log forwarding, LAPS); the commands differ and are noted
where they appear in [`detection-signals.md`](detection-signals.md).

---

## §4 Cloud mapping

Name the generic control first; the vendor feature second. On-prem has an answer for every row.

| Generic control | AWS | Azure | Google Cloud | Oracle Cloud (OCI) | On-prem / private cloud |
|---|---|---|---|---|---|
| Identity provider, MFA, conditional access | IAM Identity Center + external IdP; MFA | Microsoft Entra ID; MFA; Conditional Access | Cloud Identity / Workspace; 2SV; Context-Aware Access | OCI IAM identity domains; MFA; sign-on policies | AD/LDAP + IdP (Keycloak, etc.); MFA at VPN/bastion |
| Workload identity | IAM roles (instance profile, IRSA/EKS Pod Identity), IAM Roles Anywhere | Managed identity; workload identity federation | Attached service accounts; Workload Identity Federation | Instance/resource principals; workload identity | Vault-issued short-lived creds, SPIFFE/SPIRE |
| Narrow-scope RBAC | IAM policies, permission sets, SCPs | Azure RBAC at management group/subscription/resource group; PIM for just-in-time | IAM roles at org/folder/project; PAM for just-in-time | IAM policies on compartments | AD groups, sudoers, RBAC in each tool |
| Account/tier separation | AWS Organizations: OUs + accounts | Management groups + subscriptions | Organization: folders + projects | Tenancy: compartments (+ separate tenancies for prod) | Separate clusters/VLANs/domains |
| Resource container per product | Account per product, or tags + resource groups | Resource group | Project | Compartment | Folder/namespace/VLAN per product |
| Network firewall | Security groups + NACLs; Network Firewall | NSG; Azure Firewall | VPC firewall rules / hierarchical firewall policies | Security lists / NSGs | Perimeter firewall + host firewall |
| No public admin path | Systems Manager Session Manager; EC2 Instance Connect Endpoint | Azure Bastion; JIT VM access | IAP TCP forwarding; OS Login | OCI Bastion | Bastion/jump host, VPN, identity-aware proxy |
| Private access to data services | VPC endpoints / PrivateLink | Private Endpoint; service endpoints | Private Service Connect; Private Google Access | Private endpoints; service gateway | Data services on internal VLANs only |
| Controlled egress / fixed egress IP | NAT gateway; egress via Network Firewall | NAT Gateway | Cloud NAT | NAT gateway | Egress proxy / firewall NAT |
| DDoS / WAF | Shield; AWS WAF | DDoS Protection; Application Gateway WAF / Front Door WAF | Cloud Armor | OCI WAF; built-in DDoS | Upstream scrubbing service; WAF appliance/reverse proxy |
| Site-to-site VPN | Site-to-Site VPN; Transit Gateway | VPN Gateway (virtual network gateway + connection) | Cloud VPN (HA) | Site-to-Site VPN; DRG | IPsec gateway |
| Key management | KMS; CloudHSM | Key Vault (keys); Managed HSM | Cloud KMS; Cloud HSM | Vault (keys); HSM | HSM; HashiCorp Vault transit |
| Secrets store | Secrets Manager; SSM Parameter Store (SecureString) | Key Vault (secrets, certificates) | Secret Manager | Vault (secrets) | HashiCorp Vault, OpenBao, CyberArk |
| Disk / host encryption | EBS encryption by default | Disk encryption (SSE with PMK/CMK); encryption at host | Default encryption; CMEK | Block volume encryption; CMK | LUKS/dm-crypt; SAN encryption |
| Object storage private by default | S3 Block Public Access (account + bucket) | Storage account `allowBlobPublicAccess = false`; public network access disabled | Uniform bucket-level access + public access prevention | Bucket visibility private | MinIO/Ceph policies; no anonymous |
| Time-bound delegated URL | Presigned URL | SAS (user-delegation SAS preferred); stored access policy | Signed URL | Pre-authenticated request (PAR) | Presigned URL (S3-compatible) |
| Backup service | AWS Backup | Recovery Services vault / Backup vault | Backup and DR; Backup vault | OCI Backup (block/boot volume policies) | Bacula, Restic, Veeam, Borg |
| Immutable backups | Backup Vault Lock (compliance mode); S3 Object Lock | Immutable vault (locked); soft delete | Backup vault with enforced retention; bucket lock | Retention rules (locked) on Object Storage | WORM storage; offline/air-gapped copy |
| Deletion protection | Termination protection; `DeletionProtection` on RDS/DynamoDB; SCP deny-delete | Resource locks (`CanNotDelete`); Azure Policy deny | Deletion protection flags; resource liens; org policy | IAM deny policies; delete protection where offered | Change control + snapshots |
| Patch / update management | Systems Manager Patch Manager | Azure Update Manager | VM Manager OS patch management | OS Management Hub | Satellite, Landscape, SUSE Manager/Uyuni, Ansible |
| Posture management | Security Hub; Config; Inspector | Defender for Cloud; Advisor | Security Command Center | Cloud Guard | OpenSCAP, Wazuh, Lynis at scale |
| Control-plane audit log | CloudTrail (org trail) | Activity Log → Log Analytics; Entra sign-in/audit logs | Cloud Audit Logs (admin + data access) | Audit service | Hypervisor/vCenter, IdP and firewall logs |
| SIEM | Security Lake + a SIEM; GuardDuty | Microsoft Sentinel | Google Security Operations | Logging Analytics + a SIEM | Wazuh, Elastic, Splunk, Graylog |
| Monitoring and alerts | CloudWatch | Azure Monitor; VM Insights | Cloud Monitoring | Monitoring | Prometheus + Alertmanager, Zabbix |
| Tag enforcement | Tag policies + SCPs; Config rules | Azure Policy (require/inherit tag) | Org policy + labels/tags | Tag defaults; tag namespaces | CMDB with required fields |
| Managed database: TLS enforced, no public endpoint | RDS `rds.force_ssl` / `require_secure_transport`; private subnets | `require_secure_transport` / `ssl_enforcement`; private endpoint | Cloud SQL `ssl_mode = ENCRYPTED_ONLY`/`TRUSTED_CLIENT_CERTIFICATE_REQUIRED`; private IP | Autonomous DB mTLS; private endpoint | `hostssl` / `require_secure_transport` |
| Managed DNS: DNSSEC, query logging | Route 53 DNSSEC signing; Resolver query logs | Azure DNS DNSSEC; DNS analytics | Cloud DNS DNSSEC; logging policy | OCI DNS (DNSSEC where offered) | BIND/Knot inline signing |
| Managed mail sending: domain auth | SES Easy DKIM, custom MAIL FROM + SPF, DMARC | Communication Services email: SPF/DKIM verification | Third-party relay with SPF/DKIM | Email Delivery: SPF/DKIM | Postfix + OpenDKIM |
| Serial console / snapshot / attach rights (H25) | `ec2-instance-connect:SendSerialConsoleSSHPublicKey`, `ec2:ModifySnapshotAttribute`, `ec2:AttachVolume` | Serial console access, `Microsoft.Compute/snapshots/beginGetAccess`, disk attach | `compute.instances.setMetadata` (serial-port-enable), snapshot IAM, `compute.instances.attachDisk` | Console connections, boot-volume backup and attach policies | BMC/IPMI and hypervisor console access |

Provider minimums for platform subnets (Azure Bastion `/26`, VPN `GatewaySubnet` `/27` recommended,
and their equivalents) belong in the network design; size application subnets per component
(small, e.g. `/29`–`/27`, grown deliberately) and keep every plan non-overlapping (NET-07). For a
full addressing design, use `netdesign`.

---

## §5 Verification — every control is a check

A control becomes real when it has a **read-only check** with a **pass condition** and leaves
**evidence**. Write each as:

| Field | Example (NET-13) |
|---|---|
| Check | `sshd -T 2>/dev/null \| grep -Ei '^(permitrootlogin\|passwordauthentication\|maxauthtries)'` |
| Pass | `permitrootlogin no`, `passwordauthentication no`, `maxauthtries` ≤ 4 |
| Evidence | Command output with host, date and the operator who ran it |
| Cadence | On build (image pipeline), then daily drift scan |
| Owner | The platform team; drift tickets to the host owner |

Prefer checks that read the **effective** state (`sshd -T`, `sysctl -a`, `nft list ruleset`, the
cloud API) over checks that read a config file — later drop-ins, `Match` blocks, policies and
inheritance win. Run checks from the image pipeline (before a host exists), from config management
(on every run) and from a scheduled scanner (drift).

---

## §6 Conventions — naming, tagging, grouping, accounts

Generic patterns, written with placeholders, and enforced by policy. The organisation's values are
bound to the placeholders once, in a short values table (`<org>` → its short code, `<env>` → its
environment codes), never by rewriting the patterns or the examples with them.

**When the requirements ask for the organisation's real names in the baseline** (its account, host or
database names as the examples), decline that part and say why: the baseline is a standard meant to
outlive today's estate and be shared beyond it; examples built from real names become the convention
by copy-paste, and they publish an inventory in a document with a wider audience than the inventory
itself. Do not carry the existing names into the baseline at all — not as examples, not as "legacy
aliases". They are inventory: Review records which ones break the convention, and renaming them is a
Propose step with its own sequence.

### §6.1 Resource naming

`<type>-<product>-<client>[-<unit>]-<env>[-<region>][-<nn>]`, lower-case, hyphen-separated, no
spaces. Where a resource type forbids hyphens or caps length (storage accounts, some registries),
drop the separators in the same order: `st<product><function><client><env>`.

| Type prefix | Resource |
|---|---|
| `vm` | Virtual machine / instance |
| `vnet` / `vpc` | Virtual network |
| `snet` | Subnet (`snet-<product>-<component>`) |
| `nsg` / `sg` | Network security group / security group |
| `vng` / `vgw` | VPN gateway; `cn-<client>-<cloud>` for the connection |
| `rg` | Resource group / project / compartment (`rg-<product>` or `rg-<client>`) |
| `st` | Storage account / bucket |
| `kv` | Key vault / secrets store |
| `app` / `func` | Web app / function (`<product>-<client>-api`, `<product>-<client>-web`) |
| `rsv` / `bv` | Backup vault |

Custom domains for a product follow `<product>[-<component>].<client-domain>`; the TLS certificate
lives in the secrets store (DAT-04).

### §6.2 Tags

| Tag | Values | Why |
|---|---|---|
| `owner` | A team or group mailbox, never a person who can leave | Who answers for it (H21) |
| `product` | The product name | Cost, blast radius, deletion decisions |
| `client` | The client or cost centre (`internal` if none) | Billing; which contract governs it |
| `environment` | `prod` · `non-prod` · `sandbox` (or `dev`/`test`/`stg`/`prod` mapped onto these) | Which tier's rules apply |
| `data-class` | `public` · `internal` · `confidential` · `restricted` | Which data controls apply |
| `category` | `compute` · `network` · `data` · `security` · `backup` · `platform` | Grouping for reviews |
| `expires` | ISO date (sandboxes, temporary restores) | Cleanup (CON-04) |

### §6.3 Accounts and identities

| Who | Pattern | Notes |
|---|---|---|
| Operator from the organisation running the platform, prod | `<env>_<org>_<given>_<family>` (e.g. `prd_<org>_ana_rojas`) | `<env>` = `prd` / `dev` / `qa`; the affiliation segment distinguishes a third-party operator from the asset owner's staff |
| Asset owner's staff, prod | `<env>_<given>_<family>` | Same rule for OS and database users |
| Directory (UPN / e-mail) | `<given>.<family>@<tenant-domain>` | Aliases and alternates follow the same format; one account per person per tenant |
| Service identity | `<env>-<product>-<purpose>` | Workload identity preferred over a keyed service account |
| App registration / OAuth client | `<env>-<source>-<target>` | Secret expiry ≤ 12 months if a secret is used (IDN-08) |
| Group | `<scope>-<purpose>-<access>` (e.g. `prod-billing-db-readers`) | The name states the goal; empty groups are deleted |
| Break-glass | Two accounts, long random credentials in a sealed store, MFA by hardware key, sign-in alerts | Used only in an outage; every use reviewed |

---

## §7 Exceptions

A baseline that has no exception process gets bypassed silently. Make the bypass visible instead.

| Field | Rule |
|---|---|
| Request | A ticket naming the control ID, the asset, the reason, and the compensating control |
| Approver | The security owner — never the requester or their manager alone; an access request without that approval is returned |
| Duration | Time-bound: ≤ 90 days for prod, renewable with a fresh reason; permanent exceptions become baseline revisions |
| Record | The exceptions register, linked from the asset (tag `exception=<ticket>`) and from the review |
| Review | Expiring exceptions are listed each cycle; an expired exception is an open finding |

Recommendations from a posture tool are **inputs to this process**, not orders: review each in
context (does it break a dependency? is it already compensated?), then adopt it into the baseline or
record why not.

---

## §8 Admin workstation overlay

Endpoints that hold production credentials — keys, tokens, an admin browser session — are tier-0:
whoever owns the workstation owns every server it reaches (RANKIN p.52). Graded under **host** for
those endpoints only.

| ID | Control | Level | H |
|---|---|:-:|:-:|
| WKS-01 | Full-disk encryption (not only `/home`) with a strong passphrase; no keyfile on an unencrypted partition | R | H11 |
| WKS-02 | Screen lock on idle (≤ 10 min) and on suspend; locking is a habit when leaving the desk; Bluetooth proximity lock is not a control | R | H5 |
| WKS-03 | Hibernate or power off when travelling — suspend leaves disk keys in RAM (cold boot) | Rec | H11, H25 |
| WKS-04 | Firmware/boot password — slows, doesn't stop, a determined attacker with the device | Rec | H25 |
| WKS-05 | SSH keys passphrase-protected, agent lifetime limited (`ssh-add -t`), separate keys per environment | R | H5, H6 |
| WKS-06 | Production work in a separate VM, profile or device from browsing and mail | Rec | H1 |

## §9 Threat tier — orthogonal to the environment tier

The environment tier (§1) says what the asset is; the **threat tier** says who you expect to come
for it. Rankin organises every chapter into three levels of attacker (RANKIN pp.18–19); record the
tier per asset and add controls cumulatively.

| Threat tier | Expected attacker | Adds (beyond the §2 baseline) |
|---|---|---|
| **T1** — opportunistic | Automated scanning, commodity malware, credential stuffing | The baseline itself, applied to every internet-exposed asset — sandboxes included |
| **T2** — knowledgeable | A targeted attacker with time and skill | Server FDE, mandatory MAC profiles per service, remote logging with integrity, client-certificate admin paths, imaging-ready forensics (MON-11) |
| **T3** — advanced | Well-resourced, persistent, possibly state-level | Authenticated time (NTS), SSH second factor everywhere, DNSSEC, application-side encryption with a key service, dedicated admin workstations (WKS-06), hostile external review |

Several of Rankin's 2017 "advanced" items are **baseline now**: HSTS, forward secrecy, SPF/DKIM/DMARC
and TLS to the database belong in T1.

## §10 Not recommended

Measures the books (or common folklore) offer that this baseline does not adopt — say why when one
turns up in an estate, and what to do instead.

| Measure | Why not | Instead |
|---|---|---|
| Port knocking | Obscurity with a replayable secret; adds a fragile pre-auth parser | Bastion, VPN or identity-aware proxy (NET-04) |
| SSH on a non-standard port "for security" | Reduces log noise only; scanners find it (H30) | Keys only, no root, private path (NET-04, NET-13) |
| PortSentry / auto-blocking scanners | Spoofed sources turn it into self-inflicted denial of service; unmaintained | Default deny; fail2ban or CrowdSec only as noise reduction |
| fail2ban as the primary SSH control | Attackers rotate source addresses (RANKIN p.86) | Remove password authentication; keep fail2ban for services that can't |
| `chmod 000` on compilers | Trivially bypassed; breaks package updates | Don't install compilers on prod images (HST-01) |
| `securetty` single-TTY root | Mostly removed from modern distros | `PermitRootLogin no`, locked root, `pam_access` |
| Loop-file `/tmp` | Obsolete and fragile | `tmp.mount` or fstab options (HST-07, HST-19) |
| Geo-blocking as a boundary | Trims noise; any VPN defeats it | A real boundary (NET-04) plus conditional access (IDN-13) |
| `user.*` extended attributes as "protection" | They protect nothing; any owner changes them | Permissions, MAC, `chattr +i` as a tripwire (HST-24) |
| Hiding version banners as a control | Obscurity; doesn't stop a scanner or exploit (H30) | Patch (HST-03); log version queries as reconnaissance |

