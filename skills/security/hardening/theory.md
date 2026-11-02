# Theory — The Principles Every Hardening Finding Cites (H1–H30)

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** for a platform specifically, and **what violating it looks like** on a host or in an
> account. Sources are cited by short name:
>
> | Short name | Source |
> |---|---|
> | **SE** | Ross Anderson, *Security Engineering*, 3rd ed. (Wiley, 2020) — PDF page numbers |
> | **LSE** | Linux Professional Institute, *Security Essentials* (020) learning materials, v1.0 — PDF page numbers, topic number |
> | **LE** | Linux Professional Institute, *Linux Essentials* (010) learning materials, v2.0 — PDF page numbers, topic number |
> | **CGS** | A production cloud governance and hardening standard, anonymised and generalised for this skill — section number |
> | **RANKIN** | Kyle Rankin, *Linux Hardening in Hostile Networks* (Addison-Wesley, 2017) — PDF pages (printed = PDF − 27) |
> | **TURNBULL** | James Turnbull, *Hardening Linux* (Apress, 2005) — PDF pages (printed = PDF − 29); principles kept, mechanisms mostly obsolete (see the table at the end) |
> | **KALSI** | Tajinder Kalsi, *Practical Linux Security Cookbook*, 2nd ed. (Packt, 2018) — PDF pages (printed = PDF − 16) |
> | **CLINTON** | David Clinton, *Linux Security Fundamentals* (Sybex, 2021) — PDF pages (printed = PDF − 18) |
> | **MLS** | Hasan & Balbahaith, *Mastering Linux Security* (LAP Lambert, 2020) — PDF pages (printed = PDF − 5); cited sparingly |
> | **YALLA** | Barnhart-Magen, *Hardening Linux Made Easy* (conference slides, 2019) — slide numbers |
> | **Practice** | Current practice where the books predate a mechanism: CIS Benchmarks, NIST SP 800-53/800-123, the cloud providers' well-architected security guidance, each distro's own hardening guide |
>
> The books teach principles; where a mechanism postdates them (passkeys are in LE, but posture
> management, immutable backup vaults and workload identity federation are newer), the principle
> comes from the book and the mechanism is named as current practice.

---

## Part A — Structure: how far a compromise reaches

### H1 — Separate by tier, by product and by tenant
**Says:** Compartmentalise so one failure has a bounded blast radius: prod apart from non-prod,
each product in its own network, resource container and identity scope, each tenant with its own
accounts (SE §27.5.6, p.1025; SE §21.4.1.5, pp.755–757 — small segments a person can actually
maintain beat one elaborate central installation; CGS §2, §3, §7).
**Why:** How far an attacker gets after the first foothold depends on how much machines and
accounts trust each other (SE §21.1, pp.734–735); misuse risk grows with the value of what is
centralised and the number of people who can reach it (SE §10.1, pp.384–385). A shared subnet, a shared role or a shared
account turns one compromise into all of them.
**Violation:** prod and dev in one account or one VNet; two products sharing a subnet or resource
group; one operator identity used across tenants; a restore performed over the live asset instead
of in an isolated scope; real customer data copied into a sandbox.

### H2 — Defence in depth: two independent mechanisms per serious hazard
**Says:** Every serious hazard is covered by at least two mechanisms that don't fail together —
and management (inventory, patching), filtering (firewalls) and detection (logs, alerts) are all
needed, because each fails in ways the others catch (SE §27.3.5, p.1006; SE §21.4, pp.750–752; LSE
023.2, pp.158–159).
**Why:** A single layer is a single point of failure. The cloud firewall that's mis-edited at 2 a.m.
is the moment the host firewall earns its keep.
**Violation:** a host with no local firewall relying only on a security group; an internet-facing
web app with no WAF and no rate limit; admin access protected by a password and nothing else; a
hazard-by-mechanism matrix (or a mental one) with a row holding one entry.

### H3 — Least privilege, at the narrowest scope that works
**Says:** Give users, services and pipelines only the rights their task needs, for only as long as
they need them; run daemons as dedicated unprivileged accounts with no login shell; escalate per
command, not per session (LE 015.1, pp.334–338; LSE 021.3, p.41; SE §6.2.3, pp.259–260 — suid-root
shortcuts move access decisions into code that rarely gets them right; SE §6.4.4, p.284).
**Why:** Privilege is what a compromise inherits. A web process running as root, an operator with
Owner on the subscription, or a CI role with `*:*` turns any bug into full control.
**Violation:** `NOPASSWD: ALL` for humans; service accounts with `/bin/bash`; Owner/Contributor or
`roles/editor` granted for daily work; role assignments at subscription or organisation scope where
a resource group would do; membership of `docker`/`lxd` groups treated as harmless (they are
root-equivalent).
**Also:** PAM and sudo are where least privilege is actually enforced on a host, and their mechanics are easy to get wrong: the catch-all `other` service should deny and warn; a misplaced `sufficient` module authenticates without the checks after it; `su` belongs to a named group (`pam_wheel`); legacy trust (`pam_rhosts`, `.rhosts`, `hosts.equiv`) goes (TURNBULL pp.77–80). In `sudoers`, `ALL` gives no granularity and a negated command (`!/bin/su`) is bypassed by copying the binary (TURNBULL pp.68–69); name exact commands and log them. A restriction implemented through a shell is only as strong as the shell — an `authorized_keys` forced command wrapping a script was bypassed through an environment variable in the Shellshock case (KALSI pp.334–338).

### H4 — Every action is attributable to one accountable identity
**Says:** One person, one account, per tenant and per tier; administration through personal
identities that escalate, never a shared root or admin password; logs that tie an action to a person
(LSE 021.1, pp.14, 17–18; LSE 025.1, p.267 — authentication, authorisation, accounting; LE 015.1,
pp.337–338; CGS §10, §11).
**Why:** A shared account makes every incident unattributable and every leaver a credential
rotation. Non-repudiation needs a unique identity, a log and a clock.
**Violation:** `admin`, `ubuntu`, `ec2-user` or `sa` used by several people; more than one UID 0;
direct `root` SSH login; a team sharing one SSH key or one cloud access key; database users named
after applications but used by humans.

### H5 — Strong authentication, and phishing-resistant where it matters
**Says:** Long unique passphrases from a manager; MFA (or passkeys) for remote and privileged
access; key- or certificate-based SSH with passphrase-protected private keys; host keys verified;
default credentials changed before first exposure (LSE 025.1, pp.268–273; LE 011.4, p.77; LE 015.1,
pp.338–343; SE §21.3.4, pp.748–749 — no cleartext passwords on the LAN; SE §21.2.5, p.741 — Mirai
recruited every reachable default-password device within hours).
**Why:** Passwords are guessed, reused and phished — credential stuffing was the largest source of
attempted account compromise in 2019 (SE §2.3.1.4, p.93). SMS and recovery flows are weaker than
they look — SIM swap and SS7 abuse defeat them (SE §22.3.5, p.794; SE §3.4.1, pp.139–140); the
recovery path is the real login.
**Violation:** `PasswordAuthentication yes`; console admins without MFA; MFA by SMS for privileged
roles; vendor default users enabled; unprotected private keys on servers (most server-to-server SSH
keys are stored without a passphrase, so one host compromises its peers — SE §21.5.1, p.762).
**Also:** Screen new passwords against breached-password lists and subscribe the organisation's domains to breach notification (CLINTON pp.60–62). Server-to-server SSH private keys without a passphrase let one compromised host walk to its peers (SE §21.5.1, p.762); treat an unprotected key on a server as a finding, and give admin keys an agent lifetime (RANKIN pp.88–89).

### H6 — Credentials expire, rotate and are never long-lived by default
**Says:** Every non-human credential has an owner, a scope and an expiry; certificates are short-lived
and renewed automatically; human passwords age where they exist and are rotated on evidence of
compromise; dormant and departed accounts are locked or removed (LE 015.2, pp.354–355, 359–361; LSE
022.1, p.70; SE §21.6, pp.767–768 — certificate lifetimes of at most 398 days make automation
mandatory and expiry an outage risk; CGS §4, §12).
**Why:** A credential that never expires outlives the reason it was issued — and the person who knew
about it.
**Violation:** client secrets or SAS tokens with multi-year expiry; access keys older than a year;
`chage -l` showing `never`; accounts of people who left; a certificate renewed by hand from a
calendar reminder. (LSE's "rotate every year or so" for human passwords, p.268, is dated: forced periodic
change produces predictable passwords and NIST withdrew it in 2017 — SE §3.4.4, pp.145–147. Prefer
length, a breached-password blocklist, MFA and rotation on compromise.)
**Also:** Validity windows are availability dependencies too: DNSSEC signatures expire (about a month by default) and must be re-signed before they do; DKIM keys rotate with an overlap while mail is in flight; certificates expire into outages (RANKIN pp.175, 178–179, 201–202, 251). Every expiring thing has an alert before it expires.

## Part B — Exposure: what an attacker can touch

### H7 — Reduce the attack surface
**Says:** What isn't installed, running or listening can't be attacked: minimal role images, only
the services the role needs, each bound to the narrowest address; no unneeded features in APIs and
protocols (LE 014.4, pp.322–323; LSE 024.1, p.213; SE §20.5.4, p.716 — every feature added to a
security API brought a new break).
**Why:** Every listener is a parser exposed to the network; every package is a CVE feed you've
subscribed to.
**Violation:** `ss -tulpn` listing services the role doesn't need, or binding `0.0.0.0` when
`127.0.0.1` would do; compilers and debuggers on prod hosts; Telnet/FTP/rsh installed; public IPs on
compute that serves nothing public.

### H8 — Default deny, explicit allow, every rule explained
**Says:** Every filtering layer drops by default and allows named flows: source, destination, port,
protocol, and a reason. NAT is not a firewall (LSE 023.2, pp.158–159; LSE 024.2, p.229; LE 014.4,
p.310; CGS §2, §13).
**Why:** An `any` rule is a decision nobody made. Over-blocking and under-blocking can't both be
eliminated (SE §21.4.1.5, pp.755–757), so each rule has to carry its justification where the next
reviewer will see it.
**Violation:** inbound rules with source `*`/`0.0.0.0/0` to anything but a public listener; port
ranges; rules with no name or description; `ACCEPT` default policies; IPv6 left open behind an IPv4
ruleset; "temporary" allow-list widenings still present.

### H9 — No administrative interface faces the internet
**Says:** SSH, RDP, database ports, cluster APIs and management consoles are reachable only through
a bastion, VPN, private endpoint or an authenticating access proxy; users and devices authenticate to
each service rather than inheriting trust from a network location (SE §21.1, pp.734–735 — the
BeyondCorp model; LSE pp.231–234 on VPNs; CGS §2, §13).
**Why:** Internet-wide scanning finds an open admin port within minutes; from then on the only
control left is the password.
**Violation:** port 22/3389/5432/1433/6443 open to the internet; a VM with a public IP "for
testing"; database firewalls allowing `0.0.0.0–255.255.255.255`; an exposed cloud metadata or
management endpoint.
**Also:** The exposure window is minutes, not days — a fresh server saw intrusion attempts within a minute of first contact (CLINTON p.35). Deny rules are in place before a host first touches the network, and access is opened last.

### H10 — File permissions and privilege boundaries on the host
**Says:** The smallest owner/group/other mask; shadow files root-only; the sticky bit on shared
writable directories; SUID/SGID limited to what the distro ships; mandatory access control (SELinux,
AppArmor) confining what a compromised process can reach (LE 015.2, pp.352, 354; LE 015.3,
pp.371, 376–383; LE 015.4, pp.392–393; LSE 023.2, p.159).
**Why:** Discretionary permissions are the last boundary between a compromised service account and
the rest of the host. Directory write — not file write — governs deletion, which surprises people.
**Violation:** world-writable files outside `/tmp`; world-writable directories without `t`;
`/etc/shadow` readable by others; unexpected SUID binaries; SELinux `permissive`/`disabled` or no
AppArmor profiles where the distro supports them; home directories readable by all.
**Also:** Never disable mandatory access control to troubleshoot: permissive or complain mode only logs denials, and "temporarily" disabled SELinux tends to stay disabled (KALSI pp.105–106; CLINTON p.169). Compare the runtime mode with the configured one — `setenforce 0` survives until reboot and hides behind a correct config file.

## Part C — Data

### H11 — Encrypt at rest and in transit, and know which threat that answers
**Says:** Block-level or provider encryption for every disk, snapshot and store; TLS everywhere with
validated certificates, forward-secret key exchange and legacy protocols disabled (LSE 022.1,
pp.57–58; LSE 022.2, pp.78–85; LSE 022.4, pp.121–122; LE 011.4, p.75). But encryption isn't magic:
at-rest encryption defends against stolen media and leaked snapshots, not against a principal who is
allowed to read (SE §20.2, pp.703–705).
**Why:** Auditors ask for bucket encryption when the real failure was a public bucket policy. Grade
encryption and access control separately so one doesn't hide the other.
**Violation:** unencrypted volumes or snapshots in prod; TLS 1.0/1.1 or SSLv3 accepted; plaintext
protocols (FTP, Telnet, LDAP without TLS, HTTP without redirect); expired or mismatched
certificates; internal service traffic in clear on the assumption the network is trusted.

### H12 — Keys and secrets live in a managed store, separated by purpose
**Says:** Secrets, keys, connection strings and certificates are kept in a key or secrets store,
read at runtime by a workload identity, typed and separated by purpose; key custody is designed so
the people involved will actually follow it (LSE 022.4, p.122; SE §18.3, pp.640–641 — custodians
handed both key halves to the engineer; SE §19.4.2, pp.689–690 — one fleet-wide key let a worm
spread; SE §20.5.1, pp.712–713; CGS §13, §14).
**Why:** A secret in a config file is copied into every backup, image and support ticket that touches
it. A key used for two purposes breaks both.
**Violation:** passwords in `.env`, `appsettings`, `wp-config.php` or cloud-init user data; storage
account keys used by applications; one key or one password across environments; TLS private keys on
disk readable by the application user and backed up in clear.
**Also:** Disk encryption does not protect a mounted database or a running service, and a LUKS keyfile kept on the unencrypted root defeats the encryption; application-side keys must not live in the database, the code or a world-readable file, and native SQL crypto functions send the key over the connection and may write it to query logs (RANKIN pp.96–97, 219–221). Live-data encryption is a key-custody problem.

### H13 — Data is private by default, and minimised
**Says:** Stores are created non-public; sharing is explicit, scoped and time-bound; data that need
not exist is not collected or copied; personal data has a documented purpose and legal basis (SE
§27.3.2, p.1003 — eliminate the hazard by design before adding controls; LSE 025.2, p.285 —
classify and handle by class; LSE 025.3, pp.298–299; CGS §4).
**Why:** The breach that can't happen is the one where the data isn't there. The cheapest control on
a public bucket is that it was never public.
**Violation:** public buckets/containers; anonymous read on shares; presigned/SAS URLs valid for
years or for a whole account; production data in non-prod without masking; no data-class tag.

## Part D — Configuration and change

### H14 — Configuration is code, from trusted sources, verified continuously
**Says:** Hosts are built from definitions (images, config management) rather than hand-edited;
software comes only from signed repositories with checks on; and every control has a check that is
actually run — a verification nobody performs is decoration (LE 011.4, p.74; LE 011.2, pp.28, 38;
LSE 023.2, p.156; SE §16.5.2, p.600 — inspectors pretending to inspect; SE §27.4, pp.1010–1011 —
over-tight controls fail too, so tune by tier).
**Why:** Hand-configured hosts drift; a baseline without verification decays into a document. And a
control so strict that operators route around it is worse than a looser one they keep.
**Violation:** `gpgcheck=0`, `[trusted=yes]`, `SigLevel = Never`, `curl | sh` installs; hosts that
differ from their role; no scheduled drift scan; a hardening standard with no verification per
control; a sandbox held to prod rules so everyone ignores the baseline.
**Also:** Verify downloads through a channel the attacker doesn't also control — a checksum published next to the file proves only that the transfer completed (TURNBULL p.86) — and make tooling fail closed: a package manager that installs after a signature failure is worse than none (TURNBULL p.92). Stage updates and images on a separate machine and never expose an unpatched fresh install (TURNBULL pp.32–33, 85).

### H15 — Backups exist only when restores have worked
**Says:** Back up on a schedule from the day the asset is created; keep copies offsite, encrypted and
access-controlled; and **test restores** — an untested backup is a hope (LSE 023.4, pp.182–187; SE
§20.2 — ransomware now targets backups; CGS §9).
**Why:** Most backup failures are discovered during the restore that was needed. RPO and RTO are
claims until a timed restore proves them.
**Violation:** stateful assets with no backup policy; jobs failing silently; no restore test record;
retention shorter than the contracted RPO or legal hold; configuration, keys and DNS not backed up at
all.
**Also:** A restore test means restoring into a mirror of production (same OS, same package versions) and running the application's functional checks, for every backup set (CLINTON p.149). Keep a backup scope manifest — every data store, configuration, custom-built software and key — and check it against the asset register: the usual failures are a schedule never created, a database left out, custom software not captured (CLINTON p.145). Declare a standby tier per asset — cold, warm or hot — and prove failover against the RTO (CLINTON pp.152–153).

### H16 — Backup copies are isolated and immutable
**Says:** At least one copy can't be altered or deleted by the credentials that can alter the source —
immutable/locked vaults, object lock, offline or air-gapped media; and synchronisation is not backup,
because deletions propagate (LSE 023.4, pp.186–187; CGS §9, §13).
**Why:** An attacker with the source account's admin rights deletes the backups first; so does a
mistaken script. Redundancy is not backup — mirrored disks faithfully replicate a malicious delete,
and ransomware now poisons weeks of copies before it reveals itself (SE §7.3.3, pp.300–302); and
every replica is one more copy that needs the primary's access control (SE §7.3.1.2, pp.298–299).
**Violation:** backups in the same account, with the same admin roles, as the source; no vault lock
or soft-delete; a cloud-sync folder as the only copy; backup admins who can also disable retention.

### H17 — Destruction needs a second, deliberate step
**Says:** Critical resources carry deletion locks or deny-delete policies; break-glass paths exist
and are tested; humans are kept out of production changes where automation can do them (SE
§27.5.6.2, p.1025; SE §27.3.6, p.1007 — decide per component what the safe state is; CGS §7, §14).
**Why:** Most catastrophic data loss is an authorised identity doing the wrong thing quickly. A lock
turns a one-step mistake into a two-step decision — the same reasoning that makes the gravest
actions need several independent conditions (SE §15.2.2, p.572).
**Violation:** no lock on prod resource containers, databases, backup vaults, gateways or public IPs;
`force_destroy`/`skip_final_snapshot` on prod data; key stores without purge protection.

### H18 — Patch, track vulnerabilities, and retire what can't be patched
**Says:** Patch OS, firmware and applications on a cadence, faster for known-exploited
vulnerabilities; keep an asset inventory so patching reaches everything; track vulnerabilities by CVE
and severity; an emergency patch is the normal process run faster, not an untested one; retire
end-of-life releases (LSE 023.2, p.155; LSE 021.2, pp.26–27; LE 011.1, pp.17–18; SE §21.4,
pp.750–752; SE §27.5.7, pp.1029–1032).
**Why:** Known CVEs are the cheapest attack there is, and the most critical systems are often the
least patched.
**Violation:** pending security updates older than the window; EOL distro releases; hosts missing
from the update manager; no vulnerability scan; "reboot required" for months; posture-tool findings
never triaged.
**Also:** Close the patch loop with proof: a team mailbox subscribed to distro and vendor advisories, each advisory a ticket naming the fixed version, prioritised by exposure and exploitation, closed with evidence (RANKIN pp.38–39). Prioritise by CVSS and known exploitation; scanners disagree, so use more than one, run authenticated scans from a clean dedicated host, and keep the reports (CLINTON pp.132–134, 137).

## Part E — Seeing and governing

### H19 — Audit trails that survive the incident
**Says:** Log authentication, privilege use and control-plane actions; keep logs off the host and out
of reach of the admins they record; synchronise clocks; set retention as a deliberate policy (LE
014.3, pp.294–296; LSE 025.1, p.267; SE §6.2.3, p.259 — root can alter local logs, so ship them to
another machine; SE §26.5, pp.981–985 — tamper-evident logs and chain of custody; SE §21.4.2,
p.760).
**Why:** Logs are the only evidence after an incident, and the first thing a careful attacker
edits.
**Violation:** volatile journald only; no remote forwarding; audit logs disabled in an account;
retention of days; logs writable by the workload's own roles; unsynchronised time.
**Also:** Logs, and the path they travel, are attack targets: attackers read logs for intelligence and edit `wtmp`/`btmp` and accounting files first; UDP syslog is lossy, unauthenticated and can be congested to drop entries; an open receiver invites flooding (TURNBULL pp.71, 262–269; RANKIN p.94). Ship over TCP with TLS (or RELP), restrict senders, and keep `/var/log` from filling the root filesystem. Alerts must not depend on the service under attack — a mail server can't page you about the mail server (TURNBULL p.371). Time is a spoofable dependency: use authenticated (NTS) or internal sources (RANKIN pp.97–98; Practice).

### H20 — Someone is watching, and knows what to do
**Says:** Metrics, alerts and security detections route to an owned channel; signature tools alone
are not enough — attackers test against them and live off the land, so hunt for persistence; plan
incident response before the incident: monitoring, repair, distribution, reassurance (SE §21.3.5,
pp.749–750; SE §21.4.2, pp.757–760 — with a 0.1% false-alarm rate, false alarms outnumber real
attacks about a hundred to one; SE §27.5.7.3, pp.1031–1032; LSE 021.2, pp.28–30).
**Why:** A detection nobody reads is a log. An alert channel with a hundred false positives a day is
a muted channel.
**Violation:** alerts to an unmonitored mailbox; no on-call for security detections; EDR installed but
never reviewed; no hunt for new `authorized_keys`, cron entries or admin tools; no incident plan or
contact list.
**Also:** Triage by exclusion: suppress known-good patterns and deliver the remainder to someone who reads it, tuning over time (KALSI pp.351–354; CLINTON p.154). Build log analysis in stages — inventory sources, decide what matters, correlate, test — rather than switching everything on at once (TURNBULL p.294).

### H21 — Everything is owned, named and classified
**Says:** Every asset is in an inventory with an owner, a tier and a data class; names and tags make
purpose readable; risks are kept in a register with an owner each (SE §27.2, pp.999–1000; SE §21.4,
p.751; LSE 025.2, p.285; CGS §2–§7, §14).
**Why:** Unowned assets are unpatched assets, and a store nobody has inventoried hides risks nobody
can see (SE §11.4.1, p.439). A resource whose purpose can't be read from its name
and tags can't be safely changed or deleted — so it's left alone, with whatever it exposes.
**Violation:** untagged resources; tags naming a person who left; groups whose names don't say what
they grant; `test2`, `tmp-final`, `backup-old` holding live data; no asset register.
**Also:** Know what is actually on your network: scan your own ranges on a schedule and diff the result against the register — an unknown host or port is a finding (CLINTON pp.88–89, 134; KALSI pp.42–46). Review your external exposure as an attacker sees it — internet-scan indexes, public repositories, job ads that reveal your stack (CLINTON pp.36, 129–130). Scans are active probes: they need authorisation and are the user's to run (H22).

### H22 — Change is controlled, reviewed by someone else, and evidenced
**Says:** Changes and exceptions go through a ticket; access is approved by a security owner rather
than the requester; production promotion needs a review against the baseline; evidence is kept
against the control it proves; and review is hostile rather than friendly — the team that built it
doesn't sign it off (SE §28.3.2, p.1070; SE §28.2.9, p.1066 and §12.2.7, p.463 — most large
breached firms held a process certificate, so measure outcomes; SE §15.1, pp.569–570 — five layers
of checking each assumed another had checked; CGS §12, §14).
**Why:** An unrecorded exception becomes permanent; a self-approved one was never a control.
**Violation:** firewall or IAM changes with no ticket; exceptions with no expiry or approver; prod
launched without a readiness review; evidence screenshots scattered in chat; a posture tool's
recommendations auto-applied without review, or never reviewed at all.

---

## Part F — Operating under attack

### H23 — Bound what any one process can consume
**Says:** Availability is a security outcome: limit the CPU, memory, tasks, file descriptors and disk
each service and user can take, and disable core dumps outside development, so a runaway process, a
cryptominer or a flood can't take the whole host (CLINTON pp.43–44, 169; TURNBULL — resource
ceilings and core dumps for non-developers).
**Why:** Without ceilings, the first compromised or misbehaving process decides the availability of
everything else on the box; core dumps of a process that held secrets are a copy of those secrets.
**Violation:** services with no `MemoryMax`/`TasksMax`/`LimitNOFILE`; no quotas on multi-user hosts;
`fs.suid_dumpable` non-zero; sustained unexplained CPU nobody alerts on.

### H24 — Observe before you enforce, then promote on evidence
**Says:** Every control that can block legitimate work is switched on in a report-only mode first,
its log reviewed for a fixed window, and then promoted to enforcing on measured evidence: AppArmor in
complain mode, ModSecurity in `DetectionOnly`, DMARC from `p=none` through `quarantine` to `reject`,
SPF from `~all` to `-all`, RBL rejections watched before they bite (RANKIN pp.92, 150, 164, 169,
180); mail TLS from *may* to *must* once the logs show peers cope (TURNBULL p.415); SELinux
permissive to enforcing (KALSI pp.105–106). Every hardening change carries a tested back-out and a
record of old and new settings (TURNBULL p.27).
**Why:** Enforcing blind breaks production and gets rolled back for good; observing forever is
decoration. The observe phase needs an end date, or it becomes the steady state.
**Violation:** `p=none` a year after publishing DMARC; `SecRuleEngine DetectionOnly` in prod with no
promotion date; profiles left in complain mode; a blocking control switched straight to enforce with
no observation and no rollback.

### H25 — Boot, console, disk and out-of-band access bypass every logical control
**Says:** Whoever can change how a host boots, reach its console or read its disk owns it: lock the
boot loader, require authentication for single-user and rescue modes, mask Ctrl-Alt-Del, disable
booting from removable media, prune old vulnerable kernels (TURNBULL pp.34–43; MLS pp.116–119 — an
edited boot line gave a root shell). In the cloud the same access is a permission: serial console,
snapshot sharing, volume attach, user-data edit — each is physical access by another name.
**Why:** Every control in this baseline runs inside the operating system; the attacker at the boot
prompt or holding a copy of the disk is outside all of them.
**Violation:** no boot-loader password where consoles are reachable; single-user mode with no
password; many old kernels installed; serial-console or snapshot-share rights granted broadly in
IAM. (A locked root password also locks rescue mode — decide it knowingly.)

### H26 — Optional encryption is downgradable: require it, verify the peer, run PKI as an operation
**Says:** TLS that a client may skip, or that doesn't authenticate the server, stops a passive
eavesdropper and nothing else: require it (`hostssl` in `pg_hba.conf`, `REQUIRE SSL` for MySQL
users, HSTS on the web, TLS-only mail submission) and verify the peer (`sslmode=verify-full`,
backend `verify required`) (RANKIN pp.106, 126–127, 145, 168, 217–218). Operate the PKI behind it:
issuing-CA keys on an isolated machine or in a KMS/HSM, never on a service host; key size and expiry
reviewed together; revocation or short lifetimes; a private CA only for a closed set of known peers,
a public CA for the public; service keys protected like system passwords (TURNBULL pp.172–178,
403–405, 559).
**Why:** Opportunistic TLS falls to a downgrade; encryption without authentication is a tunnel to
whoever answers; a CA key on a web server is every certificate it ever signs.
**Violation:** databases accepting plaintext `host` connections; clients with `sslmode=prefer`;
`smtpd_tls_auth_only = no`; a plaintext backend behind a TLS terminator; `ca.key` on a service host;
RSA-1024 or SHA-1-signed certificates.

### H27 — Default deny applies to directions and functions, not only ports
**Says:** Deny outbound by default on servers and list the destinations they need (resolvers, time,
mirrors); an exposed host may receive admin sessions but must not start them into the internal tier
(TURNBULL pp.111–112, 124–130). Inside an open port, each helper function is a decision: open relay,
`VRFY`/`EXPN`, recursion, zone transfers and FTP write commands are denied unless the role needs them
(TURNBULL pp.365–367, 483, 516–517). Repeat the network ACL inside the service — MySQL `user@host`,
`pg_hba.conf`, Postfix `mynetworks`, BIND `allow-query` — so one bad firewall edit doesn't expose it
(RANKIN pp.162, 186, 213–215).
**Why:** Egress rules cap what a compromised process can do and where it can send what it stole
(CLINTON p.37 — exfiltration is a step every attacker must take). A firewall that allows port 25 has
not decided whether the server relays for the world.
**Violation:** `OUTPUT ACCEPT` on servers; "allow all new outbound"; DMZ hosts able to SSH inward; an
MTA relaying for anyone; an authoritative DNS server answering recursive queries or transfers to
anyone; a database listener whose only ACL is the firewall.

### H28 — Assume the attacker already has a shell; preserve and rebuild a suspect host
**Says:** Harden for the attacker who already has a user-level shell — what can they read, escalate,
reach (YALLA slides 3–4). When compromise is suspected, stop hardening: tightening a host that's owned
locks the attacker in with you (YALLA slide 7). Preserve state first — commands on the live host
change timestamps and evidence, and a rootkit makes the host's own tools lie — then image, hash the
original and the copy, analyse the copy from a separate host, and **rebuild** from known-good media
rather than clean (RANKIN pp.224–241; TURNBULL pp.344–346; CLINTON pp.154, 166). Decide beforehand who
may isolate or power off a host and whether you intend to prosecute (RANKIN pp.224–225).
**Why:** Cleaning a compromised host is "a lost cause", and backups may carry the implant (TURNBULL
pp.344–345). The books' "pull the plug" advice loses memory; current practice is to isolate the
network and capture memory and disk snapshots if tooling is pre-staged (Practice, NIST SP 800-86) —
a trade-off to decide in the runbook, not in the moment.
**Violation:** no incident runbook; hardening scripts run on a host under investigation; diagnostics
run on the live suspect; cleaning instead of rebuilding; credentials the host held not rotated; cloud
disks set to delete on stop where forensics matter.

### H29 — Detect by baseline diff, against a baseline the attacker can't rewrite
**Says:** Keep a known-good baseline of the persistence points — SUID files, UID 0, cron/at/timers,
enabled units, `authorized_keys`, `ld.so.preload`, kernel modules, promiscuous interfaces, hidden
files in system paths — and diff against it on a schedule (TURNBULL pp.343–344). Protect the
baseline itself: signed policy and database, stored off-host or read-only, every violation reviewed
before the database is updated (TURNBULL pp.254, 257; KALSI pp.246–251); report new files, not only
changed ones (KALSI p.264).
**Why:** Scanners find what their authors anticipated, and rootkit checkers trust binaries the
attacker may have replaced (TURNBULL pp.310–315; KALSI p.435); a local privilege escalation such as
Dirty COW leaves nothing abnormal in the logs (KALSI p.350). A detector running on a compromised host
can be lied to — read the disk from outside when it matters (CLINTON p.154).
**Violation:** FIM database writable on the host it protects; `rkhunter --propupd` run after an
incident; no report of new files; no external read of a suspect disk.

### H30 — Simplicity and homogeneity are controls; obscurity is not
**Says:** Standard paths, default configurations, few distros and releases per role: a homogeneous
fleet is easier to patch, audit and reason about (RANKIN pp.30, 81). Hiding version banners, moving
SSH to another port or renaming services reduces log noise at best and must never substitute for
patching or a real boundary (RANKIN pp.38, 86, 185–186; TURNBULL pp.362–364, 515–516; KALSI p.152).
**Why:** Every bespoke host is a baseline of one; every obscurity measure is a control that scores
points without stopping anyone who scans.
**Violation:** many distinct OS releases for one role; hand-tuned snowflake configs; "security"
claimed for a non-standard SSH port, a hidden banner or port knocking.

---

## Where the books are dated

The principles above hold; many of the mechanisms the books show do not. Use the modern form.

| Book mechanism | Status | Use instead |
|---|---|---|
| LILO / GRUB legacy password; BIOS password (TURNBULL pp.34–37) | Dead / dated | GRUB2 PBKDF2 superuser, UEFI setup password, Secure Boot; cloud serial-console IAM |
| `chkconfig`, `update-rc.d`, `inittab`, `shutdown.allowed`, `securetty`, `pam_console` (TURNBULL pp.38–46; YALLA) | Dead or removed | systemd `disable`/`mask` (mask `ctrl-alt-del.target`), `PermitRootLogin no`, `pam_access`, logind/polkit |
| MD5/DES hashes, `pam_cracklib`, 30–60-day password aging (TURNBULL pp.60–64; MLS p.80) | Dead / withdrawn | yescrypt or SHA-512 hashes, `pam_pwquality`, `pam_faillock`, length + breached-password list + MFA |
| `pam_stack`, process accounting `acct` (TURNBULL pp.73–78) | Removed / superseded | `@include`/`substack`; `auditd` execve rules |
| Hand-built kernels, Openwall, grsecurity/LIDS/RSBAC (TURNBULL pp.95–104; KALSI pp.59–67) | Dead or niche | Distro kernels, kernel lockdown, Yama, `fs.protected_*`, SELinux or AppArmor |
| ipchains/iptables-only, Lokkit, TCP Wrappers, PortSentry (TURNBULL pp.110–161, 371; KALSI pp.195–231) | Dead / unmaintained | nftables (or firewalld/ufw on nftables) with a default policy and IPv6; fail2ban/CrowdSec only as noise reduction |
| UDP syslog, Stunnel, SEC (TURNBULL pp.263–305) | Dated | rsyslog over TLS or RELP, `systemd-journal-remote`, a SIEM |
| Tripwire OSS, `lcap`, sXid, chkrootkit/rkhunter (TURNBULL pp.216–258, 311–315; KALSI pp.223–252, 435) | Superseded / weak | AIDE or Wazuh with an off-host database, capability bounding, IMA/EVM, EDR |
| `dm_crypt` loop files, eCryptfs (TURNBULL pp.237–244; CLINTON p.106) | Superseded | LUKS2 full-disk encryption, encrypted swap |
| RSA-1024, `CA.pl`, CRL-only revocation (TURNBULL pp.171–178) | Dead / dated | RSA-3072 or ECDSA/Ed25519; ACME, step-ca or Vault PKI; short-lived certificates |
| TLS cipher lists with 3DES and TLS 1.0 (RANKIN pp.123–124, 141); `tlsdate` (RANKIN p.97) | Dated / abandoned | A maintained profile (Mozilla intermediate/modern), TLS 1.2+ (1.3 preferred); chrony with NTS |
| OpenVPN with easy-rsa and no revocation (RANKIN pp.114–120) | Incomplete | Per-user certificates with CRL/`crl-verify` and `tls-crypt`, or WireGuard/IdP-backed VPN |
| Manual `dnssec-signzone` from cron, DLV, RSASHA512 (RANKIN pp.199–202); TSIG HMAC-MD5 (TURNBULL pp.530–533) | Dated | Inline/automated signing with ECDSA P-256 (alg 13); TSIG `hmac-sha256` |
| Fixed DNS query source port 53 (TURNBULL pp.519–520) | **Harmful** | Randomised source ports (the post-2008 cache-poisoning defence) |
| ModSecurity 2 with CRS 2.x (RANKIN pp.148–150) | Obsolete | A current engine with OWASP CRS 4 |
| Sendmail, `saslauthd`, SMTP AUTH on port 25, UW-IMAP, fetchmail (TURNBULL pp.350–471) | Dated | Postfix/Exim, Dovecot SASL, submission on 587/465, SPF + DKIM + DMARC + MTA-STS |
| FTP / vsftpd (TURNBULL pp.472–491); NFS v2/v3 (TURNBULL pp.258–259) | Replace | SFTP, FTPS or object storage with signed URLs; NFSv4 with Kerberos |
| Bastille, Nessus 2, John the Ripper audits (TURNBULL pp.316–331) | Dead / dated | OpenSCAP/SSG, CIS-CAT, Lynis; Greenbone/OpenVAS; breached-password screening at set time |
| MD5 checksums for downloads (KALSI pp.31–32; CLINTON p.122) | Dated | Signature verification, or a SHA-256 hash fetched through an independent channel |
| "Pull the plug" on compromise (TURNBULL p.312; RANKIN pp.225, 240) | Contested | Isolate the network, snapshot memory and disks if pre-staged, then rebuild (H28) |
| `UsePAM no` alongside a PAM TOTP module; `nullok` on the second factor (YALLA slides 14–15) | **Defects** | `UsePAM yes`, `AuthenticationMethods publickey,keyboard-interactive`, no `nullok` |
| Auto-stripping SUID from anything off an allow-list; `chmod 000` on compilers; loop-file `/tmp` (YALLA slides 17–18, 23, 25) | Breaks things / ineffective | Alert on SUID drift against package ownership; don't install compilers on prod; `tmp.mount` or fstab options |
| SMS as the second factor (CLINTON p.60) | Weak for privileged access | Phishing-resistant factors (FIDO2/passkeys), TOTP at minimum |
| Plaintext LDAP, default `admin/admin` consoles, click-through self-signed certificates (KALSI pp.113–116, 146, 177–179, 402; CLINTON p.115) | **Unsafe recipes** | LDAPS/StartTLS with verification; changed credentials before first exposure; a trusted CA |

