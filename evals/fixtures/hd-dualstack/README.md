# tokenvault — pay-api-01 evidence for the PCI sign-off

Evidence collected read-only on 2026-11-18 by tkhan (platform team) for the PCI DSS assessment on
2026-12-01. Nothing in this folder is live configuration: it is command output and copies of files.

| Asset | What it is | Tier | Data class | Owner |
|---|---|---|---|---|
| `pay-api-01` | Ubuntu 22.04 EC2 instance (`i-0b7c4e19a2d3f5608`) in `subnet-app-1a`, runs the card-tokenisation API (`pay-api`, port 8443) | prod | restricted (cardholder data, PCI CDE) | platform team |
| `alb-pay-public` | Internet-facing application load balancer in front of `pay-api` (HTTPS 443) | prod | restricted | platform team |
| `vpc-tokenvault-prod` | Dual-stack VPC (`10.20.0.0/16`, `2600:1f18:4a2:c300::/56`) | prod | — | platform team |

Accounts on the host: `mrojas` and `tkhan` (platform, key-only), `deploy` (CI runner),
`sftp-reports` (nightly settlement report pickup by the finance SFTP client).

## What the team believes

- The host was hardened by our Ansible role `cis-ubuntu2204` (v3.1.0, Level 1 Server); its last run
  reports **0 failed** (`ansible/cis-report.txt`).
- SSH is only reachable from the VPN (`10.8.0.0/16`), and the instance has no public IP.
- Password authentication is off (`sshd -T` shows `passwordauthentication no`).
- ufw is active with a default-deny inbound policy.
- auditd runs the CIS rule set.

## Layout

```
evidence/pay-api-01/          command output (file name = command) and copies of files from the host
evidence/pay-api-01/etc/      copies of /etc files
evidence/pay-api-01/ansible/  the hardening role's own report
cloud/aws/                    aws CLI exports for the prod account (eu-west-1)
```
