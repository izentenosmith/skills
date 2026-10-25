# orders-infra — target design

Traces to `analysis/terraform/summary.md`.

## Layout (single root, per-environment inputs)

```
infra/
  main.tf  variables.tf  outputs.tf  versions.tf  providers.tf
  envs/
    dev/   backend.hcl  terraform.tfvars
    prod/  backend.hcl  terraform.tfvars
modules/
  app/        (existing, now actually called, pinned by path)
  database/   aws_db_instance + parameter group, for_each over a map of databases
```

`envs/dev` and `envs/prod` stop being separate roots: one definition, inputs per environment
(TF-STR-01).

## State map

| Root | Env | Backend | Key | Lock | Applies |
|---|---|---|---|---|---|
| infra | dev | s3 `acme-orders-tfstate-dev` (dev account) | `orders/infra.tfstate` | `use_lockfile` | CI role `tf-apply-dev` |
| infra | prod | s3 `acme-orders-tfstate-prod` (prod account) | `orders/infra.tfstate` | `use_lockfile` | CI role `tf-apply-prod`, approval required |

Both buckets versioned and encrypted (TF-STA-01, TF-STA-02).

## Resource identity

- Databases become `module.database.aws_db_instance.this["orders"]`, `["invoices"]`, `["audit"]`
  — keyed by name, not position (TF-CHG-01).
- Prod databases: `deletion_protection = true`, final snapshot on delete,
  `lifecycle { prevent_destroy = true }` (TF-CHG-02).

## Security

- Provider authenticates by role assumption only; CI uses GitHub OIDC (TF-SEC-01).
- DB password managed by RDS (`manage_master_user_password = true`), not a variable (TF-SEC-03).
- The vendor reaches Postgres through the VPN prefix list only (TF-SEC-02).

## Versions

`required_version = "~> 1.9"`, `hashicorp/aws ~> 5.60`, lockfile committed (TF-DEP-01, TF-DEP-02).

## Apply path

Plan on PR per environment, saved plan applied on merge, dev then prod, prod gated
(TF-DEL-01..03). Pipeline detail is out of scope for this document.
