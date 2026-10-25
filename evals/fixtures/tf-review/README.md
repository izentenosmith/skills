# orders-infra

Terraform for the orders service: its VPC security groups, the Postgres databases and the
application module. Two environments, `dev` and `prod`, each in its own folder.

## Deploying

```bash
cd envs/prod
terraform init
terraform apply
```

CI applies `envs/prod` on every push to `main` (see `.github/workflows/terraform.yml`). For an
urgent change, run the commands above from your laptop with the shared deploy credentials.
