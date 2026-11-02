# ledgerline — target baseline (abridged)
> Derived from the hardening catalogue; levels shown for prod.

| ID | Control | prod |
|---|---|:-:|
| NET-04 | No administrative interface reachable from the internet; admin via Azure Bastion or a VPN | R |
| NET-13 | SSH: keys only, `PermitRootLogin no`, `MaxAuthTries` ≤ 4, `AllowGroups platform` | R |
| NET-12 | Host firewall default deny | R |
| IDN-06 | No standing Owner for humans; PIM just-in-time for privileged roles | R |
| IDN-11 | `sudo` per user, no `NOPASSWD: ALL` for humans | R |
| DAT-04 | Secrets in Key Vault, read by managed identity | R |
| DAT-05 | Storage private; public blob access disabled at the account | R |
| HST-03 | Security updates within 7 days (critical within 48 h); dnf-automatic / unattended-upgrades | R |
| HST-06 | SUID set limited to distro packages | R |
| HST-09 | SELinux/AppArmor enforcing | R |
| CON-03 | Restore test each quarter, into `rg-ledgerline-restore` | R |
| CON-05 | Vault immutability **locked**, soft delete on | R |
| GOV-04 | Mandatory tags incl. `owner` | R |
| GOV-05 | `CanNotDelete` lock on prod resource groups | R |
| MON-01/02/03 | Activity log retained 1 year; host logs forwarded over TLS; auditd rules on prod | R |
| SVC-DB-01/04 | Postgres on the private address only; TLS required (`hostssl`), no `0.0.0.0/0` | R |
