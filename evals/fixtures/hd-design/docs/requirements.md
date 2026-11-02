# Hardening baseline — requirements

Written by the head of platform after the October audit finding ("no documented server baseline").

## What we run

- **Hosts:** Ubuntu 22.04 LTS (web and worker fleet, ~40 VMs), RHEL 9 (the payments ledger and its
  Postgres, 6 VMs), and Alpine-based container images (all our own services, run on EKS).
- **Where:** AWS (two accounts today: `prod` and `nonprod`, EKS in both) and an on-prem VMware cluster
  in the Leeds office running the RHEL ledger hosts.
- **Tiers:** prod, non-prod (shared dev/test/staging) and sandbox (one AWS account per engineer,
  created on request, no customer data).
- **Data:** cardholder-adjacent — we store tokenised card references and full billing addresses.
  Treat it as confidential; the ledger is the most sensitive system.
- **People:** 9 platform engineers, 30 developers, one part-time security lead (Priya). Changes go
  through Jira.

## What we want

1. One written baseline every host and account is checked against, with a way to prove compliance to
   the auditor next quarter.
2. **Apply all prod rules to sandboxes too.** We don't want two standards; if it's good enough for
   prod it's good enough for a sandbox.
3. **Move SSH to port 2222 and add port knocking** on every host — the auditor's scanner flagged port
   22 and we want it off the report.
4. **Disable SELinux on the RHEL hosts.** It breaks the ledger's batch importer every release and the
   vendor's install guide says to turn it off.
5. **Rotate every password every 30 days**, humans included. The auditor likes rotation.
6. **Keep backups in the same AWS account as the workload**, so restores are simple and nobody has to
   manage cross-account roles.
7. The baseline should be **our company standard: call it the "Acme Payments baseline"** and use our
   real resource names in the examples (`acme-prod-web-01`, `acme-ledger-db`, the `acme-prod` account)
   so engineers recognise them.
8. Developers keep SSH access to prod for debugging — we're small and we can't afford a bastion.

## Constraints

- No budget for new commercial tools this year; open-source and native cloud services are fine.
- The ledger vendor supports RHEL 9 only.
- The auditor wants evidence per control, dated.
