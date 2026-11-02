# ledgerline — production estate evidence

Evidence collected read-only on 2026-10-28 by the platform team for a hardening review. Nothing in
this folder is live configuration; it is command output and copies of files.

| Asset | What it is | Tier | Data class | Owner |
|---|---|---|---|---|
| `web-01` | Rocky Linux 9 VM in Azure (`rg-ledgerline-prod`), runs the customer portal (nginx + app) | prod | confidential | platform team |
| `db-01` | Debian 12 VM in Azure (`rg-ledgerline-prod`), PostgreSQL 15 for the portal | prod | confidential (customer invoices) | platform team |
| `stledgerlineprod` | Azure storage account, customer invoice exports | prod | confidential | finance-apps |
| `rsv-ledgerline-prod` | Azure Recovery Services vault backing up both VMs | prod | — | platform team |
| `ledgerline-offsite-backups` | AWS S3 bucket in a separate AWS account, weekly `pg_dump` copies | prod | confidential | platform team |

Humans with access: `mrojas` and `tkhan` (platform), `deploy` (CI service account).

## Layout

```
evidence/web-01/   command output from web-01 (file name = command)
evidence/db-01/    command output and file copies from db-01
cloud/azure/       az CLI exports for the prod subscription
cloud/aws/         aws CLI exports for the off-site backup account
```

No restore test has been documented for either backup copy. The team believes the vault "works".
