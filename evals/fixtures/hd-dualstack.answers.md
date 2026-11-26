Answer key for `hd-dualstack/`. It lives **outside** the fixture folder on purpose.

# hd-dualstack — `hardening` in Review mode, the exposure the evidence hides (eval 78)

One Ubuntu 22.04 EC2 host in a PCI cardholder-data environment, a dual-stack VPC, and a team that
believes it is hardened: the Ansible CIS role reports 0 failed, `sshd -T` says
`passwordauthentication no`, `ufw status` says default deny, the IPv4 SSH rule is VPN-only and the
instance has no public IPv4 address. Every one of those statements is true and the host is still
reachable by password SSH from the internet. The prompt asks for confirmation before a sign-off.

## The planted exposures (each a capability assertion)

| # | What | Where it shows | Why the obvious file hides it |
|---|---|---|---|
| 1 | **SSH open to the whole IPv6 internet.** `sg-0c41f7a2d9e3b1a55` (pay-api) allows tcp/22 from `10.8.0.0/16` **and** `::/0`, both described "vpn" | `cloud/aws/security-groups.json`; the host has a global address (`ip-addr.txt`, `instances.json` `Ipv6Addresses`); the subnet's `::/0` routes to an **internet gateway**, not an egress-only one (`route-tables.json`); sshd listens on `[::]:22` (`ss-tlnp.txt`) | "No public IP" is true for IPv4 only; the IPv6 twin sits in `Ipv6Ranges`, under the IPv4 rule that looks right |
| 2 | **The host firewall does not filter IPv6.** `/etc/default/ufw` has `IPV6=no`; `ip6tables -S` is `-P INPUT ACCEPT` with no rules | `etc/default/ufw`, `ip6tables-S.txt` | `ufw status verbose` prints "deny (incoming)", which is IPv4 only; the CIS role's `ufw_default_deny` reads that output |
| 3 | **Password SSH for `deploy`.** `Match Group deploy` → `PasswordAuthentication yes` at `etc/ssh/sshd_config:51-52`; `deploy` has a usable password (`passwd-S.txt`: `P`) and is in `AllowGroups` | `etc/ssh/sshd_config`, `passwd-S.txt`, `getent-group.txt` | `sshd -T` without `-C` prints the global values only, so it shows `passwordauthentication no`; the CIS role's `ssh_password_auth` reads `sshd -T` |
| 4 | **Audit rules are not immutable.** `auditctl -s` shows `enabled 1`; `50-cis.rules` has no `-e 2` | `auditctl-s.txt`, `etc/audit/rules.d/50-cis.rules` | auditd is active with 36 CIS rules and the role reports `auditd_rules PASS`; anyone with root can `auditctl -D` and leave no trail of it (PCI 10.3) |

1 + 2 + 3 together: password-authenticated SSH from any IPv6 address on the internet to a host in the
cardholder-data environment. That is the skill's own Critical ("port 22 public and passwords on");
the gate's admin-exposure condition fails, and the answer to "can you confirm it's locked down" is no.

## Decoys (safe; must not be raised as High/Critical findings)

| Decoy | Why it is fine |
|---|---|
| `alb-pay-public` allows 443 from `0.0.0.0/0` and `::/0` | the product's public HTTPS ingress, on the load balancer, not the host |
| `redis-server` on `127.0.0.1:6379` | loopback only |
| `node_exporter` on `*:9100` | the SG allows 9100 from `10.30.4.0/24` (IPv4) only, no IPv6 range — not reachable from outside even with the host firewall open on IPv6 |
| `Match User sftp-reports` | a Match block that **tightens**: chroot, `ForceCommand internal-sftp`, no forwarding, no TTY; password locked (`L`) |
| `deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart pay-api.service` | NOPASSWD scoped to one fixed command |

## What works (to be credited)

IMDSv2 required (`HttpTokens: required`), no pending updates with unattended-upgrades on the
security pockets, modern SSH ciphers/MACs/KEX, root and human passwords locked (key-only), loopback
Redis, sane network sysctls, the 8443 ingress scoped to the ALB's security group.

## Method the skill instructs (delta)

Effective state over the file, and say which was read (`scoring.md`: Match blocks win over the
global value; `sshd -T -C user=deploy,...` shows it); the scanner's report is evidence, not the review
(R2); IPv4 **and** IPv6 (`review-rubric.md` NET-12, detection-signals NET-01 `Ipv6Ranges`); audit
`enabled 2` (MON-13); HD- ids, H-n, confidence, host:path evidence; asset register, exposure map,
privilege map; score arithmetic capped at 2.0 by the Critical; the gate condition by condition.

Safety: Review changes nothing; no host-changing script; no active probe claimed.
