# Detection Signals — Read-Only Checks per Control

> The command that reads each control, per distro and per cloud, with its **confidence tag**
> (✅ decidable / ⚠️ proxy / 🔬 needs-data — see [`scoring.md`](scoring.md)). IDs match the catalogue
> in [`design-patterns.md`](design-patterns.md) §2.
>
> **Every command here is read-only.** None installs, restarts, reloads or writes. Most host checks
> need root to see everything; run them only with the user's say-so, or ask the user to run them and
> paste the output. Prefer commands that show the **effective** state (`sshd -T`, `sysctl`,
> `nft list ruleset`, the cloud API) over reading a config file that a later drop-in overrides.
>
> Prefer real tools when present — they cover hundreds of checks consistently: `lynis audit system`,
> `oscap xccdf eval --profile <cis|stig> <ssg-content>`, `kube-bench`, `trivy fs|config|k8s`,
> `prowler <aws|azure|gcp>`, `scout <provider>`. Their output is evidence; the commands below are
> the fallback and the way to confirm a scanner finding in context.

## Platform detection (run first)

| What | Command |
|---|---|
| OS family and version | `cat /etc/os-release` |
| Init system | `ps -p 1 -o comm=` (`systemd`, `init` → check `/sbin/openrc`, `runit`) |
| Package manager | `command -v apt dnf yum zypper apk pacman 2>/dev/null` |
| Firewall front-end | `command -v nft iptables firewall-cmd ufw 2>/dev/null` |
| MAC | `command -v getenforce aa-status 2>/dev/null` |
| In a container? | `cat /proc/1/cgroup; ls /.dockerenv /run/.containerenv 2>/dev/null` |
| Cloud | `cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name 2>/dev/null` (Amazon EC2, Microsoft Corporation/Virtual Machine, Google, OracleCloud) — read-only, no metadata calls needed |

## identity

| ID | Check | Pass | Conf. |
|---|---|---|---|
| IDN-01 | `awk -F: '$3==0{print $1}' /etc/passwd` | only `root` | ✅ |
| IDN-01 | `last -n 50; lastlog \| grep -v 'Never'` | no shared logins (`admin`, `ubuntu`, `ec2-user`) used by several people | ⚠️ |
| IDN-01 | `for f in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do echo "$f $(grep -c . "$f" 2>/dev/null)"; done` | one owner's keys per account | ⚠️ |
| IDN-09 | `awk -F: '$2==""{print $1}' /etc/shadow` | empty | ✅ |
| IDN-10 | `awk -F: '$2 ~ /^\$1\$/{print $1}' /etc/shadow` | empty (no MD5 hashes) | ✅ |
| IDN-10 | `grep -Ev '^\s*(#\|$)' /etc/security/pwquality.conf /etc/security/faillock.conf 2>/dev/null; grep -E '^PASS_(MAX\|MIN\|WARN)_' /etc/login.defs` | `minlen` ≥ 14 (generated) / 12 (chosen), lockout configured | ✅ |
| IDN-11 | `visudo -c; grep -rnE 'NOPASSWD\|ALL\s*=\s*\(ALL(:ALL)?\)\s*ALL' /etc/sudoers /etc/sudoers.d/` | parses; no `NOPASSWD: ALL` for humans | ✅ |
| IDN-11 | `stat -c '%a %U %n' /etc/sudoers /etc/sudoers.d/*` | `440 root` | ✅ |
| IDN-11 | `passwd -S root` | `L`/`LK` (locked) or policy-approved | ✅ |
| IDN-06 | `getent group sudo wheel admin docker lxd libvirt` | only named admins; `docker`/`lxd` treated as root-equivalent | ✅ |
| IDN-12 | `lastlog -b 90 \| awk 'NR>1 && $0 !~ /Never/'`; `chage -l <user>` per human | dormant accounts justified | ⚠️ |
| — | Service accounts with a shell: `awk -F: -v m="$(awk '/^UID_MIN/{print $2}' /etc/login.defs)" '$3<(m?m:1000) && $1!="root" && $7!~/(nologin\|false)$/{print $1,$7}' /etc/passwd` | only `sync`/`shutdown`/`halt` | ✅ |

OpenRC/Alpine: `passwd -S` needs the `shadow` package; `doas` replaces `sudo` — read `/etc/doas.conf`.

**More identity checks (H3, H5, H6):**

| ID | Check | Pass | Conf. |
|---|---|---|---|
| IDN-12 | `passwd -S -a 2>/dev/null \| awk '$2~/^L/{print $1}' \| while read u; do h=$(getent passwd "$u" \| cut -d: -f6); [ -s "$h/.ssh/authorized_keys" ] && echo "LOCKED-BUT-HAS-KEYS $u"; done` | none | ✅ |
| IDN-15 | `grep -rnE 'NOPASSWD\|ALL\s*=.*\*\|!\s*/\|!authenticate\|timestamp_timeout\|Defaults.*(logfile\|log_input\|use_pty)' /etc/sudoers /etc/sudoers.d/ 2>/dev/null` | no wildcards or negations; logging defaults present | ✅ |
| IDN-15 | sudo rules granting editors, pagers or interpreters: `grep -rnE '/(vi\|vim\|nano\|less\|more\|man\|python[0-9.]*\|perl\|ruby\|find\|awk\|tar\|env)\b' /etc/sudoers /etc/sudoers.d/` | none for non-admins (shell escapes) | ✅ |
| IDN-17 | `cat /etc/pam.d/other; grep -RInE 'nullok\|pam_rhosts\|pam_permit\.so\|sufficient' /etc/pam.d/; grep -RIn pam_wheel /etc/pam.d/su; find / -xdev \( -name .rhosts -o -name hosts.equiv \) 2>/dev/null`; RHEL: `authselect current` | `other` denies; no `nullok`/rhosts; `su` wheel-restricted; each `sufficient` justified | ✅ |
| IDN-18 | `awk -F: -v m="$(awk '/^UID_MIN/{print $2}' /etc/login.defs)" '$3<(m?m:1000) && $1!="root"{print $1,$7}' /etc/passwd` vs `cat /etc/shells` | no system account has a shell listed in `/etc/shells` | ✅ |
| IDN-19 | `grep -nE 'pam_google_authenticator\|pam_oath\|pam_u2f\|nullok' /etc/pam.d/sshd; sshd -T \| grep -Ei '^(authenticationmethods\|usepam\|kbdinteractiveauthentication)'` | no `nullok`; `publickey,keyboard-interactive`; `usepam yes` | ✅ |
| H5 | `for k in /root/.ssh/id_* /home/*/.ssh/id_*; do case $k in *.pub) ;; *) [ -f "$k" ] && ssh-keygen -y -P '' -f "$k" >/dev/null 2>&1 && echo "UNPROTECTED $k";; esac; done` — reads key files; record **paths only** | none on servers | ✅ |
| H3 | `grep -RIn 'command=' /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null` | forced commands don't point at shell scripts | ⚠️ |
| IDN-14 | breach-notification subscription and password-screening config (IdP setting, `pam_pwquality` dictionary) — process evidence | present | 🔬 |

**Cloud identity (read-only):**

| ID | AWS | Azure | Google Cloud | OCI |
|---|---|---|---|---|
| IDN-02 | `aws iam generate-credential-report; aws iam get-credential-report` (mfa_active per user); Identity Center MFA settings | `az rest --method get --url "https://graph.microsoft.com/v1.0/policies/identitySecurityDefaultsEnforcementPolicy"`; Conditional Access policy export; `az ad user list` + MFA registration report | Admin console 2SV enforcement report; `gcloud organizations get-iam-policy` for privileged principals | `oci iam user list` (`is-mfa-activated`) |
| IDN-06 | `aws iam list-attached-user-policies`/`list-entities-for-policy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess` | `az role assignment list --all --include-inherited -o table` (Owner/Contributor at subscription scope) | `gcloud projects get-iam-policy <p>` (`roles/owner`, `roles/editor`) | `oci iam policy list --compartment-id <tenancy>` (`manage all-resources`) |
| IDN-07/08 | credential report `access_key_1_last_rotated`; `aws iam list-access-keys` | `az ad app credential list --id <app>` (`endDateTime`) | `gcloud iam service-accounts keys list --iam-account <sa>` (user-managed keys, `validAfterTime`) | `oci iam customer-secret-key list`, `api-key list` |
| IDN-03 | same principal in prod and non-prod account assignments | same object ID with roles in both subscriptions | same member in prod and non-prod project policies | same user in both compartments' policies |

## network

| ID | Check | Pass | Conf. |
|---|---|---|---|
| NET-04, HST-01 | `ss -tulpn` (Alpine/busybox: `netstat -tulpn`) | every listener in the role's baseline; admin ports bound to private/loopback addresses | ✅ |
| NET-13 | `sshd -T 2>/dev/null \| grep -Ei '^(permitrootlogin\|passwordauthentication\|kbdinteractiveauthentication\|permitemptypasswords\|pubkeyauthentication\|maxauthtries\|x11forwarding\|allowusers\|allowgroups\|clientaliveinterval\|ciphers\|macs\|kexalgorithms)'` | root login `no`; password and keyboard-interactive `no`; empty `no`; `maxauthtries` ≤ 4; no CBC ciphers, no `hmac-md5`/`-sha1`, no `diffie-hellman-group1`/`group14-sha1` | ✅ |
| NET-12 | Debian/Ubuntu: `ufw status verbose`; RHEL/SUSE: `firewall-cmd --state && firewall-cmd --list-all-zones`; any: `nft list ruleset`, `iptables -S`, `ip6tables -S`; Alpine: `rc-service nftables status` | default inbound drop/reject for IPv4 **and** IPv6; only baseline ports | ✅ |
| NET-11 | `ss -tlnp \| grep -E ':(21\|23\|69\|111\|139\|445\|513\|514\|161)\b'` | empty (or justified internal-only) | ✅ |
| HST-08 | `sysctl net.ipv4.ip_forward net.ipv4.conf.all.accept_redirects net.ipv4.conf.all.send_redirects net.ipv4.conf.all.accept_source_route net.ipv4.conf.all.rp_filter net.ipv4.tcp_syncookies net.ipv6.conf.all.accept_redirects` | forward 0 (unless router); redirects 0; source route 0; rp_filter 1/2; syncookies 1 | ✅ |

**More network checks (H8, H27):**

| ID | Check | Pass | Conf. |
|---|---|---|---|
| NET-15 | `nft list chain inet filter output 2>/dev/null; iptables -S OUTPUT; ip6tables -S OUTPUT` | default drop with named destinations on servers | ✅ |
| NET-16 | from an exposed-tier host: `ss -tnp state established '( dport = :22 or dport = :3389 or dport = :5432 or dport = :3306 )'`; cloud egress rules from exposed subnets to internal CIDRs | none inward | ✅ |
| NET-17 | `nft list ruleset \| grep -E 'log prefix\|ct state invalid'; sysctl net.ipv4.conf.all.log_martians`; cloud flow-log status | logging before drops; invalid dropped; martians logged; flow logs on | ✅ |
| NET-18 | `nft list ruleset \| grep -iE 'icmp'; sysctl net.ipv4.conf.all.rp_filter net.ipv4.icmp_echo_ignore_broadcasts net.ipv4.icmp_ratelimit` | PMTUD/NDP types allowed, echo rate-limited, `rp_filter` 1/2 | ✅ |
| NET-19 | `systemctl show nftables firewalld -p Before -p WantedBy 2>/dev/null`; `nft -c -f /etc/nftables.conf` (syntax check only), then compare `nft list ruleset` with the persisted file | ordered before `network-pre.target`; running ruleset matches the persisted one | ⚠️ |
| NET-20 | passive inventory: `ip neigh show`, DHCP leases, cloud inventory APIs; active discovery is a probe the user runs (below) | everything seen is in the register | ✅ with output |

**Cloud exposure (read-only):**

| ID | AWS | Azure | Google Cloud | OCI |
|---|---|---|---|---|
| NET-01/02/04 | `aws ec2 describe-security-groups --query "SecurityGroups[].IpPermissions[?contains(IpRanges[].CidrIp,'0.0.0.0/0')]"` (and `Ipv6Ranges` `::/0`); NACLs | `az network nsg list` → `securityRules[?sourceAddressPrefix=='*' \|\| sourceAddressPrefix=='Internet' \|\| sourceAddressPrefix=='0.0.0.0/0']`; rules with empty `description` | `gcloud compute firewall-rules list --filter="direction=INGRESS AND sourceRanges:0.0.0.0/0"` | `oci network security-list list`, `nsg rules list` (`source 0.0.0.0/0`) |
| NET-03 | `aws ec2 describe-instances --query "Reservations[].Instances[?PublicIpAddress]"` | `az network public-ip list` → attached `ipConfiguration` on a NIC (not an LB/gateway) | `gcloud compute instances list --format="table(name,networkInterfaces[].accessConfigs[].natIP)"` | `oci compute instance list-vnics` (`public-ip`) |
| NET-08 | `aws rds describe-db-instances --query "DBInstances[?PubliclyAccessible]"`; S3/endpoint policies | `az storage account list --query "[].{n:name,p:publicNetworkAccess,d:networkRuleSet.defaultAction}"`; `az sql server list` (`publicNetworkAccess`) + firewall rules | `gcloud sql instances list` (`ipConfiguration.ipv4Enabled`, `authorizedNetworks`) | `oci db autonomous-database list` (`is-access-control-enabled`, whitelisted IPs) |
| NET-06/07 | `aws ec2 describe-vpc-peering-connections`, route tables; CIDR overlap | `az network vnet list` (address spaces), `vnet peering list` | `gcloud compute networks peerings list` | `oci network drg-attachment list` |
| NET-09 | route tables with `0.0.0.0/0 → igw-` on private subnets; NAT GW presence | subnets with no NAT gateway and default outbound; UDRs | Cloud NAT config; instances with external IPs | NAT gateway + route rules |
| NET-10 | Shield subscriptions; WAF web ACL associations | `az network ddos-protection list`; VNet `ddosProtectionPlan`; WAF policies on App Gateway/Front Door | Cloud Armor policies on backend services | WAF policies |

## data

| ID | Check | Pass | Conf. |
|---|---|---|---|
| DAT-01 | `lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINTS; blkid -t TYPE=crypto_LUKS; swapon --show` | data and swap on `crypt` volumes (on-prem); on cloud, read the provider flag below | ✅ |
| DAT-02 | `openssl s_client -connect <host>:443 -servername <host> </dev/null 2>/dev/null \| openssl x509 -noout -subject -issuer -dates -ext subjectAltName`; `openssl s_client -connect <host>:443 -tls1_1 </dev/null` | valid chain, SAN matches, not near expiry; TLS 1.1 handshake **fails** | ✅ |
| DAT-02 | `testssl.sh <host>` / `sslyze <host>` if installed | no SSLv3/TLS1.0/1.1, no weak suites, HSTS on public web | ✅ |
| DAT-04 | `gitleaks detect --no-git -s <path>` / `trufflehog filesystem <path>`; fallback `grep -rIlE '(password\|passwd\|secret\|api[_-]?key\|token\|connectionstring)\s*[:=]' /etc /opt /srv 2>/dev/null` | no plaintext secrets (record **location and kind only**) | ✅ |
| DAT-04 | `stat -c '%a %U:%G %n' <secret-file>` for each candidate | readable only by the service user | ✅ |
| — | Certificate renewal: `systemctl list-timers \| grep -Ei 'certbot\|acme'`; `crontab -l \| grep -Ei 'certbot\|acme'` | automated | ✅ |

**More data checks (H11, H26):**

| ID | Check | Pass | Conf. |
|---|---|---|---|
| DAT-11 | `nginx -T 2>/dev/null \| grep -E 'ssl_(protocols\|ciphers\|prefer)'`; `grep -rEn 'SSLProtocol\|SSLCipherSuite' /etc/apache2 /etc/httpd 2>/dev/null` | TLS 1.2+; no 3DES/RC4/CBC-SHA1; profile from a maintained source | ✅ |
| DAT-12 | `echo \| openssl s_client -connect <h>:443 -servername <h> 2>/dev/null \| openssl x509 -noout -checkend $((21*86400))`; `systemctl list-timers --all \| grep -Ei 'certbot\|acme\|lego'` (OpenRC: `rc-update show; ls /etc/periodic/*`); `stat -L -c '%a %U:%G %n' /etc/letsencrypt/live/*/privkey.pem /etc/ssl/private/* 2>/dev/null` | > 21 days left; renewal timer present; keys `600`/`640` | ✅ |
| DAT-13 | `curl -sI http://<h> \| head -3; curl -sI https://<h> \| grep -i strict-transport`; Postgres `grep -Ev '^\s*(#\|$)' "$(psql -Atc 'show hba_file')" \| grep -E '^host\s'`; MySQL `SHOW VARIABLES LIKE 'require_secure_transport'`; `postconf smtpd_tls_auth_only` | 301 to HTTPS + HSTS; only `hostssl` lines; TLS required; `yes` | ✅ |
| DAT-14 | `find / -xdev \( -name 'cakey*' -o -name 'ca.key' -o -name 'ca-key.pem' \) 2>/dev/null`; `openssl x509 -noout -text -in <cert> \| grep -E 'Public-Key\|Signature Algorithm\|Not After'` | no CA key on service hosts; ≥ RSA-3072/P-256; SHA-256+ | ✅ |
| DAT-16 | `swapon --show; sysctl fs.suid_dumpable kernel.core_pattern; coredumpctl list 2>/dev/null \| head; ls -ld /var/crash 2>/dev/null; systemctl is-active kdump 2>/dev/null` | swap on an encrypted volume; dumps off or root-only | ✅ |
| DAT-17 | `openssl s_client -connect <h>:443 -servername <h> -status </dev/null 2>/dev/null \| grep -A2 'OCSP Response'` | stapled response where the CA supports it | ✅ |
| DAT-15 | decommission records (crypto-erase / key destruction) | evidence per disk | 🔬 |

**Cloud data (read-only):**

| ID | AWS | Azure | Google Cloud | OCI |
|---|---|---|---|---|
| DAT-01 | `aws ec2 get-ebs-encryption-by-default`; `describe-volumes --query "Volumes[?!Encrypted]"`; `rds describe-db-instances` (`StorageEncrypted`) | `az vm list --query "[].{n:name,h:securityProfile.encryptionAtHost}"`; `az disk list` (`encryption.type`) | default (always on); CMEK via `gcloud compute disks describe` (`diskEncryptionKey`) | `oci bv volume get` (`kms-key-id`) |
| DAT-03 | `aws kms list-keys` + `get-key-rotation-status` | `az keyvault list` (`enablePurgeProtection`, `enableSoftDelete`); key `rotationPolicy` | `gcloud kms keys list --keyring … --location …` (`rotationPeriod`) | `oci kms management key list` |
| DAT-05 | `aws s3control get-public-access-block --account-id <id>`; `aws s3api get-bucket-policy-status` | `az storage account list --query "[].{n:name,b:allowBlobPublicAccess}"`; container `publicAccess` | `gcloud storage buckets describe gs://<b> --format="value(iam_configuration.public_access_prevention)"`; IAM `allUsers` | `oci os bucket get` (`public-access-type`) |
| DAT-06/07 | presigned URL lifetimes in code/config (max 7 days for SigV4); IAM user keys used by apps | `az storage account show` (`allowSharedKeyAccess`); SAS expiry in config; stored access policies | `gcloud storage sign-url` usage, HMAC keys `gcloud storage hmac list` | `oci os preauth-request list` (`time-expires`) |
| DAT-08 | RDS IAM auth, security groups, `pgaudit`/audit settings | SQL Entra-only auth, firewall rules, auditing settings | Cloud SQL IAM auth, authorized networks, audit flags | DB users and network ACLs |

## host

| ID | Check | Pass | Conf. |
|---|---|---|---|
| HST-02 | `. /etc/os-release; echo "$ID $VERSION_ID"` vs vendor lifecycle | inside security support | ✅ |
| HST-03 | Debian/Ubuntu: `apt list --upgradable 2>/dev/null \| grep -i security`; RHEL: `dnf updateinfo list --security`; SUSE: `zypper list-patches --category security`; Alpine: `apk list -u`; Arch: `checkupdates; arch-audit` | none past the window | ✅ |
| HST-03 | Auto-updates: Debian/Ubuntu `apt-config dump APT::Periodic::Unattended-Upgrade; systemctl is-enabled apt-daily-upgrade.timer`; RHEL `systemctl is-enabled dnf-automatic.timer`; SUSE `systemctl list-timers \| grep -Ei 'patch\|transactional'`; Alpine/Arch `crontab -l` / timers | enabled, or an update manager enrolment | ✅ |
| HST-03 | Reboot needed: Debian/Ubuntu `test -f /var/run/reboot-required && cat /var/run/reboot-required.pkgs`; RHEL `needs-restarting -r`; SUSE `zypper needs-rebooting` | not pending for weeks | ✅ |
| HST-04 | `grep -rn 'trusted=yes\|allow-insecure' /etc/apt/ 2>/dev/null; grep -rn 'gpgcheck\s*=\s*0' /etc/yum.repos.d /etc/dnf /etc/zypp/repos.d 2>/dev/null; grep -n '^SigLevel' /etc/pacman.conf 2>/dev/null; cat /etc/apk/repositories 2>/dev/null` | no disabled signature checks; https repos | ✅ |
| HST-01 | systemd: `systemctl list-unit-files --type=service --state=enabled`, `systemctl list-units --type=socket`; OpenRC: `rc-update show -v`, `rc-status --all` | only the role's services | ⚠️ |
| HST-01 | Packages: `dpkg-query -W -f='${Package}\n'` / `rpm -qa` / `apk info` / `pacman -Q` — look for `gcc`, `gdb`, `tcpdump`, `nmap`, `telnet`, X11 on servers | absent on prod | ⚠️ |
| HST-05 | `find / -xdev -type f -perm -0002 2>/dev/null`; `find / -xdev -type d -perm -0002 ! -perm -1000 2>/dev/null`; `stat -c '%a %n' /etc/passwd /etc/shadow /etc/group /etc/gshadow`; `find / -xdev \( -nouser -o -nogroup \) 2>/dev/null`; `stat -c '%a %n' /home/*` | none; none; `644/≤640/644/≤640`; none; `700`/`750` | ✅ |
| HST-05 | `umask; grep -E '^UMASK' /etc/login.defs` | `027` or `022` | ✅ |
| HST-06 | `find / -xdev -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null` then owner per binary: `dpkg -S` / `rpm -qf` / `pacman -Qo` / `apk info -W` | every binary owned by a distro package and expected; diff against the previous scan | ✅ |
| HST-07 | `findmnt -no TARGET,OPTIONS /tmp /var/tmp /dev/shm` | `nodev,nosuid` (+`noexec` where the role allows) | ✅ |
| HST-08 | `sysctl kernel.randomize_va_space kernel.kptr_restrict kernel.dmesg_restrict kernel.yama.ptrace_scope fs.protected_symlinks fs.protected_hardlinks fs.protected_fifos fs.suid_dumpable` | `2`, ≥`1`, `1`, ≥`1`, `1`, `1`, ≥`1`, `0` | ✅ |
| HST-09 | RHEL family: `getenforce; sestatus`; Debian/Ubuntu/SUSE: `aa-status` | `Enforcing` / profiles loaded and enforcing | ✅ |
| HST-10 | `timedatectl show -p NTPSynchronized --value` (OpenRC: `chronyc tracking`) | `yes` / synchronised | ✅ |
| HST-11 | `systemctl is-active <edr-agent>`; `aide --check` scheduled (`systemctl list-timers \| grep aide`, cron) | running / scheduled | ✅ |
| HST-12 | `mokutil --sb-state`; `grep -rE 'set superusers\|password_pbkdf2' /boot/grub*/grub.cfg /etc/grub.d/ 2>/dev/null` | enabled where available / locked | ✅ |
| HST-14 | presence of a config-management agent or a pull job (`systemctl is-active puppet salt-minion chef-client`, ansible-pull timer); package verify: `dpkg --verify` / `rpm -Va` / `pacman -Qkk` / `apk audit --system` | managed; no unexpected changed files | ⚠️ |
| HST-15 | `docker ps -q \| xargs -r docker inspect --format '{{.Name}} priv={{.HostConfig.Privileged}} user={{.Config.User}} net={{.HostConfig.NetworkMode}} ro={{.HostConfig.ReadonlyRootfs}}'`; Kubernetes: `kubectl get pods -A -o json \| jq '.items[] \| select(.spec.containers[].securityContext.privileged==true) \| .metadata.name'`; `kube-bench` | not privileged, non-root, no host net/PID, read-only root where possible | ✅ |

**More host checks (H23, H25, H29, H30):**

| ID | Check | Pass | Conf. |
|---|---|---|---|
| HST-04 | `grep -rE 'AllowInsecure\|allow-unauthenticated\|AllowDowngradeToInsecure' /etc/apt 2>/dev/null; grep -RE 'localpkg_gpgcheck\|repo_gpgcheck' /etc/dnf /etc/yum.conf 2>/dev/null` | no insecure overrides; signature checks on | ✅ |
| HST-09 | `getenforce; sed -n 's/^SELINUX=//p' /etc/selinux/config; aa-status 2>/dev/null \| grep -E 'complain\|enforce'` | runtime = configured = enforcing; no stray complain profiles | ✅ |
| HST-10 | `chronyc -n sources; chronyc -n authdata 2>/dev/null` (timesyncd: `timedatectl timesync-status`) | ≥ 3 sources, NTS or internal | ✅ |
| HST-16 | `grep -rE 'set superusers\|password_pbkdf2' /boot/grub*/grub.cfg /etc/grub.d/ 2>/dev/null; systemctl is-enabled ctrl-alt-del.target; systemctl cat rescue.service emergency.service 2>/dev/null \| grep -E 'sulogin'`; kernel count: `dpkg -l 'linux-image-*' \| grep -c ^ii` / `rpm -q kernel \| wc -l`; cloud: who holds serial-console, snapshot-share and volume-attach rights (§4) | locked loader where consoles are reachable; `masked`; `sulogin` on rescue; ≤ 2–3 kernels; rights held by named roles | ✅ |
| HST-17 | `systemd-analyze security --no-pager`; `systemctl show <unit> -p User -p NoNewPrivileges -p CapabilityBoundingSet -p ProtectSystem -p PrivateTmp` (OpenRC: `command_user`, `capabilities` in `/etc/init.d/<svc>`) | network daemons non-root and sandboxed (exposure score low) | ✅ |
| HST-18 | `systemctl show <unit> -p MemoryMax -p TasksMax -p LimitNOFILE -p LimitCORE; grep -rE 'hard\s+core' /etc/security/limits* 2>/dev/null; repquota -a 2>/dev/null` | limits set on exposed services; cores off | ✅ |
| HST-19 | `for m in /tmp /var/tmp /var /var/log /home; do mountpoint -q $m && echo "sep $m" \|\| echo "NOT-SEP $m"; done` | separate where the role allows | ✅ |
| HST-20 | `grep -E '^(database\|database_in\|database_out)' /etc/aide/aide.conf /etc/aide.conf 2>/dev/null; stat -c '%U %a %n' <aide-db>; systemctl list-timers \| grep -i aide; systemctl is-active wazuh-agent 2>/dev/null` (`aide --check` is read-only but heavy on I/O) | database off-host or read-only; scheduled; reports read | ✅/⚠️ |
| HST-21 | `getfacl -R -s -p /etc /home /srv 2>/dev/null \| grep '^# file'` | each extended ACL documented | ⚠️ |
| HST-22 | `modprobe -c 2>/dev/null \| grep -E '^(blacklist\|install) +(cramfs\|freevxfs\|hfs\|hfsplus\|jffs2\|udf\|usb[-_]storage)'; lsmod \| grep -E 'cramfs\|hfs\|udf\|usb_storage'` | blacklisted and not loaded | ✅ |
| HST-23 | `sshd -T \| grep -i '^banner'; cat /etc/issue.net` | banner set | ✅ |
| HST-24 | `lsattr /etc/passwd /etc/shadow /etc/ssh/sshd_config 2>/dev/null; findmnt -o TARGET,OPTIONS /usr /boot` | optional; a tripwire only | ✅ |
| HST-25 | across the fleet: `. /etc/os-release; echo "$ID $VERSION_ID"` per host, counted per role | few distinct releases per role | ✅ |
| HST-08 | `grep -r . /sys/devices/system/cpu/vulnerabilities/ 2>/dev/null` | mitigated / not affected | ✅ |

**Admin workstation overlay (WKS, §8 of design-patterns):**

| ID | Check | Pass | Conf. |
|---|---|---|---|
| WKS-01 | `lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINTS \| grep -E 'crypt'`; `grep -Ev '^#' /etc/crypttab \| awk '$3!="none" && $3!="-"'` | root and home on LUKS; no keyfile on an unencrypted partition | ✅ |
| WKS-02 | GNOME `gsettings get org.gnome.desktop.screensaver lock-enabled; gsettings get org.gnome.desktop.session idle-delay`; KDE `kreadconfig5 --file kscreenlockerrc --group Daemon --key Autolock` | lock on; ≤ 600 s | ✅ |
| WKS-05 | the unprotected-key loop from the identity table on `~/.ssh`; `ssh-add -l` | no unprotected keys; agent lifetime set | ✅ |
| WKS-03/04/06 | travel, firmware and separation practice | stated by the owner | 🔬 |

**Windows hosts** (same controls, different commands): local admins `Get-LocalGroupMember Administrators`;
RDP exposure `Get-NetTCPConnection -LocalPort 3389 -State Listen`; firewall `Get-NetFirewallProfile`;
BitLocker `Get-BitLockerVolume`; updates `Get-HotFix \| Sort InstalledOn`; Defender `Get-MpComputerStatus`;
audit policy `auditpol /get /category:*`; LAPS presence.

## service (only where the role exists)

| ID | Check | Pass | Conf. |
|---|---|---|---|
| SVC-WEB-01 | `ps -eo user:20,comm \| grep -E 'nginx\|apache2\|httpd\|caddy' \| sort -u; find /var/www /srv/www -xdev \( -user www-data -o -user apache -o -user nginx -o -perm -o+w \) 2>/dev/null \| head` | workers non-root; docroot not owned or writable by the worker | ✅ |
| SVC-WEB-02 | `awk -F: '{print $1, substr($2,1,4)}' /etc/nginx/*htpasswd* /etc/apache2/*htpasswd* /etc/httpd/*htpasswd* 2>/dev/null` (username and hash prefix only) | `$2y$`/`$2a$`; no `$apr1`/`{SHA}`; files outside the docroot | ✅ |
| SVC-WEB-03 | `grep -rEn '^\s*SecRuleEngine' /etc/modsecurity* /etc/apache2 /etc/httpd /etc/nginx 2>/dev/null` | `On` (not `DetectionOnly` past its end date) | ✅ |
| SVC-MAIL-01/02 | `postconf -n \| grep -E '^(mynetworks\|smtpd_relay_restrictions\|smtpd_recipient_restrictions\|smtpd_tls_auth_only\|smtpd_sasl_auth_enable\|smtpd_tls_security_level\|disable_vrfy_command\|message_size_limit)'`; Exim: `exim -bP relay_from_hosts` | narrow `mynetworks`; `reject_unauth_destination`; AUTH only in TLS; `disable_vrfy_command = yes`; a size limit | ✅ |
| SVC-MAIL-03 | `dig +short TXT <d> \| grep -i spf1; dig +short TXT _dmarc.<d>; dig +short TXT <sel>._domainkey.<d>`; DKIM size: `dig +short TXT <sel>._domainkey.<d> \| tr -d '" ' \| sed 's/.*p=//' \| base64 -d 2>/dev/null \| openssl pkey -pubin -inform DER -noout -text \| head -1` | SPF `-all` (or `~all` during rollout); DMARC with `rua` and a policy beyond `none`; DKIM ≥ 2048 | ✅ |
| SVC-MAIL-04 | `dig +short TXT _mta-sts.<d>; dig +short TXT _smtp._tls.<d>; curl -s https://mta-sts.<d>/.well-known/mta-sts.txt` | `mode: enforce`; TLS-RPT published | ✅ |
| SVC-DNS-01..04 | `named-checkconf -p \| grep -E 'recursion\|allow-(query\|recursion\|transfer)\|rate-limit\|query-source\|update-policy\|algorithm'` (**redact TSIG secrets**); Unbound `grep -E 'access-control\|interface\|ratelimit' /etc/unbound/unbound.conf*` | recursion off on authoritative; transfers to named hosts; RRL on; no fixed `query-source port`; `hmac-sha256` | ✅ |
| SVC-DNS-04 | `stat -c '%a %U %n' /etc/bind/*.key /etc/named/*.key 2>/dev/null` | `600` | ✅ |
| SVC-DNS-05 | `dig +dnssec +multi <d> SOA \| grep -A1 RRSIG; dig +short DS <d>; delv <d> SOA` | expiry well ahead; DS present; "fully validated" | ✅ |
| SVC-DNS-06 | `resolvectl status 2>/dev/null \| grep -E 'DNSSEC'; dig +short CAA <d>` | validation on; CAA present | ✅ |
| SVC-DB-01 | `ss -tlnp \| grep -E ':(3306\|5432\|1433\|1521\|27017\|6379\|9200)\b'` | loopback or private addresses only | ✅ |
| SVC-DB-02..04 (PostgreSQL) | `psql -Atc "show listen_addresses; show ssl; show password_encryption"; grep -Ev '^\s*(#\|$)' "$(psql -Atc 'show hba_file')"` | `hostssl` only; no `trust`; no `md5`; no `0.0.0.0/0` | ✅ |
| SVC-DB-02..04 (MySQL/MariaDB) | `mysql -NBe "SELECT user,host,plugin FROM mysql.user WHERE user='' OR host='%' OR authentication_string=''"; mysql -NBe "SHOW VARIABLES WHERE Variable_name IN ('bind_address','require_secure_transport','tls_version','local_infile')"` | no anonymous, empty or `%` accounts; TLS required | ✅ |
| SVC-DB-05/06 | `stat -c '%a %U %n' /root/.my.cnf /root/.pgpass /home/*/.my.cnf /home/*/.pgpass 2>/dev/null`; `grep -lEi 'pgp_sym_encrypt\|aes_encrypt' /var/log/postgresql/* /var/log/mysql/* 2>/dev/null` (filenames only) | `600`; no key-bearing statements in logs | ✅ |
| SVC-FILE-01 | `ss -tlnp \| grep -E ':(20\|21)\b'; sshd -T \| grep -Ei '^(subsystem\|chrootdirectory)'` | no FTP listener (or chrooted legacy only); SFTP configured | ✅ |
| SVC-FILE-02 | `exportfs -v 2>/dev/null; grep -Ev '^\s*(#\|$)' /etc/exports /etc/exports.d/* 2>/dev/null; findmnt -t nfs,nfs4 -o TARGET,OPTIONS` | no `*`, no `no_root_squash`; clients `nosuid,nodev` | ✅ |
| SVC-VPN-01 | OpenVPN: `grep -Ev '^\s*(#\|;\|$)' /etc/openvpn/server*.conf /etc/openvpn/server/*.conf 2>/dev/null` (look for `crl-verify`, `tls-crypt`, narrow `push route`); `find / -xdev \( -name 'ca.key' -o -name 'ca-key.pem' \) 2>/dev/null`; WireGuard: `wg show` (**not** `wg showconf`, which prints the private key) | revocation present; CA key absent from the server; peers individually listed | ✅ |
| SVC-VPN-02 | `sshd -T \| grep -Ei '^(allowtcpforwarding\|gatewayports\|permittunnel\|permitopen\|allowagentforwarding)'` on bastions; data-tier egress to port 22 | restricted; none outbound | ✅ |
| H27 signal | `ss -tlnp \| grep -E ':(9050\|9001)\b'; pgrep -a tor` | no Tor daemon or relay on prod unless a ticketed exception | ✅ |

## continuity

| ID | AWS | Azure | Google Cloud | OCI | On-prem / host |
|---|---|---|---|---|---|
| CON-01 | `aws backup list-protected-resources` vs the asset register | `az backup item list --vault-name <v> -g <rg>`; VMs not in any vault | `gcloud backup-dr` protected resources; snapshot schedules | `oci bv volume-backup-policy-assignment` | `systemctl list-timers --all \| grep -Ei 'backup\|restic\|borg'`; cron |
| CON-02 | `aws backup list-backup-jobs --by-state FAILED` | `az backup job list --status Failed` | backup job history | backup job status | `restic snapshots --latest 3` / `borg list` dates |
| CON-03 | restore job history `aws backup list-restore-jobs` | `az backup job list --operation Restore` | restore history | restore history | restore test records — 🔬 if not supplied |
| CON-04 | restore targets outside the restore account/OU | `az backup job list --operation Restore` targets ≠ the restore resource group; non-empty restore RG | restores outside the restore project | restores outside the restore compartment | restore paths |
| CON-05 | `aws backup describe-backup-vault` (`Locked`, `MinRetentionDays`); S3 Object Lock | `az backup vault show` (`immutabilitySettings.state = Locked`, soft delete) | backup vault enforced retention | Object Storage retention rules (locked) | WORM target / offline copy evidence |
| CON-06 | vault in a separate backup account; vault access policy | vault in a separate subscription; RBAC on vault vs source | backup vault project ≠ source project | separate compartment/tenancy | separate credentials for the backup target |
| CON-07 | backup plan rules (retention, lifecycle) | `az backup policy show` (daily retention, instant-restore days) | backup plan retention | policy schedules | job retention flags |
| CON-08 | `DeletionProtection`/termination protection flags; SCP deny `Delete*` | `az lock list` per RG and resource | `gcloud alpha resource-manager liens list`; `deletionProtection` flags | IAM deny policies | — |
| CON-10 | KMS key deletion window; Route 53 export | `az keyvault show` (`enablePurgeProtection`) | `gcloud kms` destroy-scheduled duration | vault deletion protection | DNS zone export, IaC in VCS |

CON-11 and CON-12 are document checks: the backup scope manifest diffed against the asset register (every data store, config, custom-built software and key), and a declared standby tier with a failover test record per tier-1 asset. Without them they are 🔬.

## monitoring

| ID | Check | Pass | Conf. |
|---|---|---|---|
| MON-02 | `[ -d /var/log/journal ] && echo persistent; grep -E '^Storage=' /etc/systemd/journald.conf; grep -rEn '^[^#]*@@?[A-Za-z0-9]' /etc/rsyslog.conf /etc/rsyslog.d/ 2>/dev/null`; log-agent status | persistent and forwarded off-host | ✅ |
| MON-02 | auth log location: Debian/Ubuntu `/var/log/auth.log`; RHEL `/var/log/secure`; SUSE/Arch `journalctl -u sshd`; Alpine `/var/log/messages` | present and shipped | ✅ |
| MON-03 | `auditctl -s; auditctl -l` | enabled with rules on `/etc/passwd`, `/etc/shadow`, `/etc/sudoers*`, `/etc/ssh/sshd_config`, privileged commands, time changes | ✅ |
| MON-07 | scanner last-run timestamps; `trivy` reports age | ≤ 7 days | ✅ |

| ID | AWS | Azure | Google Cloud | OCI |
|---|---|---|---|---|
| MON-01 | `aws cloudtrail describe-trails` (`IsMultiRegionTrail`, `IsOrganizationTrail`), `get-trail-status`; log bucket policy and retention | `az monitor diagnostic-settings subscription list`; Log Analytics retention; Entra sign-in/audit export | `gcloud logging sinks list`; Data Access audit config in IAM policy | `oci audit configuration get` (retention) |
| MON-04 | `aws cloudwatch describe-alarms` (`AlarmActions` non-empty) | `az monitor metrics alert list`; `az monitor action-group list` | `gcloud alpha monitoring policies list` (notification channels) | `oci monitoring alarm list` (destinations) |
| MON-05 | Security Hub enabled standards; Config recorder | `az security pricing list`; secure score; Advisor recommendations | `gcloud scc` findings | Cloud Guard targets |
| MON-06 | GuardDuty enabled; SIEM ingestion | Sentinel workspace + analytics rules | Security Operations ingestion | Logging Analytics + SIEM |
| MON-08 | `aws ssm describe-instance-patch-states` | Azure Update Manager compliance (`az graph query -q "patchassessmentresources"`) | `gcloud compute os-config patch-jobs list`; VM Manager compliance | OS Management Hub reports |

**More monitoring checks (H19, H28, H29):**

| ID | Check | Pass | Conf. |
|---|---|---|---|
| MON-02 | `grep -rEn '^[^#]*@@\|protocol="tcp"\|StreamDriver\|omrelp' /etc/rsyslog.conf /etc/rsyslog.d/ 2>/dev/null`; syslog-ng `grep -rn 'transport' /etc/syslog-ng`; `systemctl is-active systemd-journal-upload 2>/dev/null` | TCP with TLS or RELP — not a single `@` (UDP) | ✅ |
| MON-03 | `ls /etc/audit/rules.d; auditctl -l \| grep -c -- '-k '; aureport --summary 2>/dev/null \| head` | rules persisted, keyed, reviewed | ✅ |
| MON-11 | AWS `aws ec2 describe-instances --query 'Reservations[].Instances[].BlockDeviceMappings[].Ebs.DeleteOnTermination'`; Azure `az vm show -g <rg> -n <vm> --query storageProfile.osDisk.deleteOption`; GCP `gcloud compute instances describe <i> --format='value(disks[].autoDelete)'`; plus the runbook | disks survive stop where forensics matter; runbook exists | ✅ / 🔬 |
| MON-12 | `cat /etc/ld.so.preload 2>/dev/null; ip -d link \| grep -i promisc; lsmod; systemctl list-unit-files --state=enabled; systemctl list-timers --all; ls -la /var/spool/cron* /etc/cron.* 2>/dev/null; find / -xdev -name authorized_keys 2>/dev/null` — diff each against the stored baseline | no unexplained additions | ✅ with a baseline |
| MON-12 | `find /etc /usr /bin /sbin -xdev -newerct '<ISO date>' -printf '%C+ %u %p\n' 2>/dev/null \| sort \| tail` (ctime can't be reset with `touch`; GNU find only) | changes match tickets | ⚠️ |
| MON-13 | `findmnt /var/log; lsattr /var/log/* 2>/dev/null \| grep -- '-a-'; auditctl -s \| grep enabled; journalctl --verify 2>&1 \| tail -3` | own filesystem; audit `enabled 2`; journal verifies | ✅ |
| MON-10, MON-14, MON-15 | IR plan and contacts; external-exposure review notes; advisory subscription and the ticket trail | present and current | 🔬 |
| H28 | `lsof -nP +L1` (deleted-but-open files), `ss -tnp state established` — **on a suspected host, don't run these: preserve and image first** | — | — |

## governance

| ID | AWS | Azure | Google Cloud | OCI |
|---|---|---|---|---|
| GOV-01 | `aws organizations list-accounts` + `environment` tag per account | `az account list`; `environment` tag distribution per subscription | `gcloud projects list --format="table(projectId,labels.environment)"` | `oci iam compartment list` |
| GOV-03 | name regex over `aws resourcegroupstaggingapi get-resources` | `az resource list --query "[].name"` vs regex | `gcloud asset search-all-resources --format="value(name)"` | `oci search resource structured-search --query-text "query all resources"` |
| GOV-04 | `aws resourcegroupstaggingapi get-resources` (missing keys); tag policies | `az resource list --query "[?tags.owner==null]"`; `az policy assignment list` (require-tag) | `gcloud asset search-all-resources --query="NOT labels:owner"` | tag defaults per compartment |
| GOV-05 | SCP deny-delete on prod OUs | `az lock list --resource-group <rg>` for every prod RG | liens on prod projects | deny policies |
| GOV-07 | CloudTrail change events vs ticket IDs in change descriptions/tags | Activity Log vs ticket references | Admin Activity logs vs tickets | Audit events vs tickets | 

GOV-06, GOV-08, GOV-09 and the exceptions register are **process evidence**: ask for the ticket
export, the readiness checklist and the evidence repository index. Without them they are 🔬.

GOV-12 needs the scope record: the named systems, the permission, the tool and the window for every
active test. Without it, it is 🔬.

## Active probes — the user runs these, with authorisation

These send traffic to targets or write files. The skill does **not** run them; it asks the user (or
their scanner) to, against named systems with written permission (GOV-12), and reads the output as
evidence.

| Probe | What it settles |
|---|---|
| `nmap -sn <range>`, `nmap -sS -sV <host>` | NET-20 discovery; listeners as seen from outside |
| `testssl.sh <host>`, `sslyze <host>` | DAT-02, DAT-11, DAT-13 |
| SMTP relay test: `EHLO` / `MAIL FROM` / `RCPT TO:<external>` against port 25 | SVC-MAIL-01 |
| `dig @<ns> <zone> AXFR` and a recursive query to an unrelated domain, **from outside** | SVC-DNS-01, SVC-DNS-02 |
| Greenbone/OpenVAS, Nikto, ZAP baseline, Trivy against a running service | MON-07 |
| `lynis audit system` (writes `/var/log/lynis.log` and a report file), `oscap xccdf eval` | Broad host baseline |
| Password audits (hashcat against exported hashes) | IDN-10 — only with explicit approval, never on production without a window |

## Book commands that change state — never use them as checks

Several recipes in the source books **change** the system. They may appear in a remediation plan
(Propose), never in collection (Review):

`cryptsetup luksFormat` · `dd of=/dev/…` · `setenforce` · `passwd -l/-u`, `usermod -L/-U` ·
`chmod -R`, `chown -R`, `setfacl` · `tune2fs -o acl` · `iptables -A … -j DROP` (lockout risk),
`iptables-persistent` · `postconf -e` · `a2enmod` · `systemctl stop/start/enable` · `sysctl -p` /
`sysctl -w` · `wg-quick up` · `certbot --apache` (rewrites config) · `rkhunter --propupd` (rewrites
its baseline) · `tripwire --check --interactive` (saving updates the database) · `make install` ·
`unattended-upgrades` / `apt upgrade` / `dnf upgrade` (apply updates now) · `aide --update`.

