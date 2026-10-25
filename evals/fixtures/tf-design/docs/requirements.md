# Platform infrastructure — requirements

We're moving the checkout platform from hand-built AWS resources to Terraform. This is what the
platform needs; how to lay out the Terraform is open.

## Accounts and regions

- AWS Organizations is already set up. There is one account per environment: `dev`
  (111111111111), `staging` (222222222222), `prod` (333333333333), plus a `shared-services`
  account (444444444444) that hosts CI runners and the container registry.
- Everything runs in `eu-west-1`. `eu-central-1` is planned for prod disaster recovery next year.

## What runs

| Component | Contains | Who changes it | How often |
|---|---|---|---|
| Network | VPC, subnets, NAT, transit gateway attachment, Route 53 private zones | platform team | about monthly |
| Orders service | ECS service, its Aurora Postgres cluster, SQS queues, IAM roles, alarms | orders team | several times a day |
| Payments service | ECS service, its own DynamoDB tables, KMS key, IAM roles | payments team | weekly |
| Observability | CloudWatch dashboards, log groups, alert routing | platform team | ad hoc |

Payments stores card tokens and is in PCI DSS scope; the auditors want its infrastructure changes
and the people who can make them to be separable from the rest of the platform.

## How we work today

- One GitHub organisation; GitHub Actions for CI. Service teams own their application repos;
  the platform team owns a `platform-infra` repo.
- A few people have AdministratorAccess in every account and apply things from their laptops
  when something is urgent.
- The orders database lost three days of data last year when someone deleted and recreated it
  by mistake.

## Asks from leadership

- "Keep it simple: one Terraform workspace per environment, all in one state bucket, so anyone
  can see everything."
- Changes to prod should be reviewed. Nobody should need admin rights in prod for routine work.
- We'd like to add a new service in under a day once this is in place.
