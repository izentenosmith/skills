# ledgerline prod — Hardening review summary
> Hosts: 2 (web-01 Rocky Linux 9, db-01 Debian 12) · accounts: 1 Azure subscription + 1 AWS backup account ·
> data stores: 3. Evidence as of 2026-10-28; rubric v1.0. Tier: prod; data class: confidential.

## Scores
| identity | network | data | host | continuity | monitoring | governance | service | **Unit** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.0 | 2.0 | 2.0 | 6.0 | 6.0 | 5.0 | 4.4 | 6.0 | **2.0** (uncapped 5.1) |

Arithmetic: network base 4.0 (4 of 20 points), capped 2.0 by HD-NET-01 (Critical). Data base 5.0, capped 2.0
by HD-DAT-01 (Critical). Identity base 5.6, capped 2.0 by HD-IDN-03 (Critical: the readable password).

## Severity tally
Critical 4 · High 9 · Medium 5 · Low 1. Needs-data 🔬: 2.

## Asset register
| Asset | Tier | Data class | Owner | Roles | Evidence |
|---|---|---|---|---|---|
| web-01 | prod | confidential | — (untagged) | web | evidence/web-01 |
| db-01 | prod | confidential | platform team | database | evidence/db-01 |
| stledgerlineprod | prod | confidential | — (untagged) | object storage | cloud/azure |
| rsv-ledgerline-prod | prod | — | — (untagged) | backup | cloud/azure |
| ledgerline-offsite-backups | prod | confidential | platform team | backup | cloud/aws |

## Exposure map
- Internet → web-01 (203.0.113.47): 80, 443 (intended), **22 (allow-ssh-temp, source `*`)**.
- Internet → stledgerlineprod: public network access, container `exports` anonymous read.
- web-01 → db-01: 5432 and 22 (NSG). db-01 listens on 5432 on all addresses.

## Privilege map
- mrojas: Owner on rg-ledgerline-prod; `NOPASSWD: ALL` on web-01. tkhan: Contributor. sp-ledgerline-deploy: Contributor.
- root SSH login allowed on web-01.

## Top findings (worst first)
| ID | Object | Finding | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| HD-NET-01 | web-01 | SSH open to the internet with password auth and root login | ✅ | H9, H5 | Critical | cloud/azure/nsg-list.json `allow-ssh-temp`; evidence/web-01/sshd-T.txt |
| HD-DAT-01 | stledgerlineprod | Container `exports` publicly readable, holds invoice exports | ✅ | H13 | Critical | cloud/azure/storage-container-list.json |
| HD-IDN-03 | db-01 | Export-job DB password in plain text, world-readable (0644) | ✅ | H12 | Critical | evidence/db-01/etc/app/db.conf |
| HD-HST-02 | web-01 | Critical openssh update pending (RLSA-2026:6021) on an internet-facing host | ✅ | H18 | Critical | evidence/web-01/dnf-updateinfo-security.txt |
| HD-IDN-01 | web-01 | Human with `NOPASSWD: ALL` (mrojas) | ✅ | H3 | High | evidence/web-01/etc/sudoers.d/10-platform |
| HD-IDN-02 | rg-ledgerline-prod | Standing Owner for a human; no MFA evidence | ✅/🔬 | H3, H5 | High | cloud/azure/backup-vault.json (role assignments) |
| HD-HST-03 | web-01 | Unowned SUID binary `/usr/local/bin/backup-helper` | ✅ | H10 | High | evidence/web-01/find-suid.txt |
| HD-HST-04 | db-01 | Security updates pending, unattended-upgrades disabled | ✅ | H18 | High | evidence/db-01/apt-upgradable.txt |
| HD-SVC-01 | db-01 | Postgres on all addresses, `host all all 0.0.0.0/0 md5`, `ssl = off` | ✅ | H26, H27 | High | evidence/db-01/etc/postgresql/* |
| HD-CON-01 | rsv-ledgerline-prod | Vault mutable: immutability and soft delete disabled | ✅ | H16 | High | cloud/azure/backup-vault.json |
| HD-CON-02 | both VMs | No restore ever tested | 🔬 | H15 | High (unscored) | backup job list: no Restore jobs |
| HD-GOV-01 | rg-ledgerline-prod | No deletion lock on the prod resource group | ✅ | H17 | High | cloud/azure/lock-list.json |
| HD-MON-01 | web-01 | auditd inactive; logs only on the host | ✅ | H19 | High | evidence/web-01/auditctl-s.txt, rsyslog.conf |
| HD-NET-02 | web-01 | Host firewall policy accept; no default deny | ✅ | H2, H8 | Medium | evidence/web-01/nft-ruleset.txt |
| HD-GOV-02 | 5 resources | Missing `owner` tag | ✅ | H21 | Medium | cloud/azure/resource-tags.json |

## What is working well
SELinux enforcing on web-01; chrony synchronised; encryption at host on both VMs; storage minimum TLS 1.2;
the AWS off-site bucket is private, encrypted and under Object Lock (COMPLIANCE, 35 days); db-01 SSH is key-only on a private address.

## Gate
- Score ≥ 9.0: **fail** (2.0).
- No open Critical/High: **fail** (4 Critical, 9 High).
- No admin interface reachable from the internet: **fail** (HD-NET-01).
- Privileged humans nominative with MFA, no standing owner in daily use: **fail** (HD-IDN-02; MFA 🔬).
- Prod backups isolated and restore-tested: **fail** (HD-CON-01; HD-CON-02 🔬).
- 🔬 ≤ 10%: pass (2 of 31 objects).

## Needs-data flags
- 🔬 HD-CON-02: whether either backup copy restores.
- 🔬 MFA enforcement for the Azure tenant (Conditional Access not exported).
