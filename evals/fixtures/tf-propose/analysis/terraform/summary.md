# orders-infra — Terraform review summary
> Roots: 2 (envs/dev, envs/prod) · child modules: 1 local (modules/app), 1 remote (acme/terraform-modules//app) · resources: 13 · environments: dev, prod. Source as of 5d41c2e; rubric v1.0.

## Scores
| structure | state | dependencies | security | change-safety | delivery | **Codebase** |
|---:|---:|---:|---:|---:|---:|---:|
| 5.7 | 2.9 | 3.0 | 2.0 | 4.3 | 2.1 | **2.0** (uncapped 3.4) |

## Severity tally
Critical 2 · High 7 · Medium 4 · Low 2. Needs-data flags: 3.

## State map
| Root | Env | Backend | Key | Lock | Encrypted | Applied by |
|---|---|---|---|---|---|---|
| envs/dev | dev | s3 `acme-orders-tfstate` | `orders/terraform.tfstate` | none | not set | humans (README) |
| envs/prod | prod | s3 `acme-orders-tfstate` | `orders/terraform.tfstate` | none | not set | CI on push (`-auto-approve`), humans (README) |

## Module graph
envs/dev → acme/terraform-modules//app @ `main` · envs/prod → acme/terraform-modules//app @ `main` · modules/app is not called by either root (the remote copy is).

## What is working well
- `modules/app`: typed, described and validated variables; outputs reference resources; standalone rule resources; `create_before_destroy` on the security group (T9, T16).
- `default_tags` with owner/environment in both providers (T16).
- State files and `.terraform/` are excluded from git (T5).

## Top findings (worst first)
| ID | Object | Anti-pattern | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| TF-SEC-01 | envs/prod provider | Static AWS access key and secret key in code | ✅ | T15 | Critical | envs/prod/main.tf:3-4 |
| TF-SEC-02 | aws_vpc_security_group_ingress_rule.db_vendor | Postgres 5432 open to 0.0.0.0/0 | ✅ | T16 | Critical | envs/prod/main.tf:27-33 |
| TF-SEC-03 | envs/prod/terraform.tfvars | Database master password as a tfvars literal | ✅ | T15 | High | envs/prod/terraform.tfvars:3 |
| TF-STA-01 | envs/dev + envs/prod | Both environments share one state object (same bucket and key) | ✅ | T7 | High | envs/*/backend.tf:3-4 |
| TF-STA-02 | envs/dev + envs/prod | S3 backend without locking | ✅ | T6 | High | envs/*/backend.tf |
| TF-DEP-01 | module "app" | Module pinned to a branch (`?ref=main`) | ✅ | T11 | High | envs/*/main.tf:14 |
| TF-DEP-02 | envs/dev, envs/prod | No `required_version`/`required_providers`; lockfile gitignored | ✅ | T11 | High | .gitignore:5 |
| TF-CHG-01 | aws_db_instance.db | Distinct databases keyed by `count` index | ✅ | T8 | High | envs/*/main.tf:36-37 |
| TF-CHG-02 | aws_db_instance.db (prod) | `skip_final_snapshot = true`, `deletion_protection = false` in prod | ✅ | T17 | High | envs/prod/main.tf:47-48 |
| TF-DEL-01 | .github/workflows/terraform.yml | Prod applied with `-auto-approve`, no saved plan, no plan on PRs | ✅ | T12, T13 | High | terraform.yml:20 |
| TF-STR-01 | envs/dev vs envs/prod | Copy-pasted environments, drifted: prod lacks `storage_encrypted` | ✅ | T10, T21 | Medium | diff envs/dev/main.tf envs/prod/main.tf |
| TF-DEL-02 | README.md | Laptop applies with shared credentials documented | ✅ | T13 | Medium | README.md:9-17 |
| TF-DEL-03 | repo | No fmt/validate/lint/scan in CI | ✅ | T19 | Medium | terraform.yml |
| TF-STR-02 | modules/app | Local module unused; the remote copy is called instead | ⚠️ | T10 | Low | envs/*/main.tf:14 |

## Needs-data flags (not scored)
- 🔬 Whether the shared state object currently holds dev or prod resources (whichever applied last) — needs `terraform state list` against the bucket.
- 🔬 Whether the leaked key is still active and what it can do — needs IAM.
- 🔬 Whether the vendor still uses the 0.0.0.0/0 rule — needs VPC flow logs.

## Gate
- Score ≥ 9.0: **fail** (2.0).
- No open Critical/High: **fail** (2 Critical, 7 High).
- Remote locked state with prod isolated: **fail** (TF-STA-01, TF-STA-02).
- Apply only through a reviewed saved plan in a pipeline: **fail** (TF-DEL-01, TF-DEL-02).
- 🔬 ≤ 10% of objects: pass (3 of 31).
