# ledger-api — delivery requirements

We need a deployment pipeline for `ledger-api`. Nothing exists yet beyond what's in this repo.

## The service

- Go 1.23 HTTP service; `make test` runs unit tests in about 90 seconds, `make integration` needs
  Postgres and takes about 12 minutes.
- Packaged as a container, deployed with the Helm chart in `charts/ledger-api` to EKS.
- Production runs in two regions, `eu-west-1` and `us-east-1`, active-active. Staging runs in
  `eu-west-1` only.
- Schema migrations live in `migrations/` (golang-migrate). Some upcoming changes rename columns.
- Infrastructure (EKS add-ons, RDS, IAM) is Terraform in `infra/`, one root per environment.

## Constraints

- GitHub Actions is the CI platform; GitHub-hosted runners only.
- We are SOC 2 audited. The auditor's requirement: whoever writes a change must not be the only
  person who approves it reaching production, and we must be able to show who deployed what, when.
- AWS accounts: `staging` (222222222222) and `prod` (333333333333).
- The service handles ledger entries. An outage longer than 15 minutes is a contractual incident.

## What people have asked for

- Product wants to ship weekly instead of monthly, and to turn features on for a few customers
  first.
- Compliance has asked for a change-approval meeting before every deployment, staging included.
- Today the image is built separately for staging and prod "so each one gets the right config
  baked in". The team likes that it is simple.
