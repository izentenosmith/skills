Answer key for `tf-propose/`. It lives **outside** the fixture folder on purpose.

# tf-propose — `terraform` in Propose mode (eval 23)

The `tf-review` codebase, plus a finished review (`analysis/terraform/summary.md`) and a target
design (`docs/design.md`). The proposal must get from one to the other.

| # | Planted | The proposal should… | Catches a run that… |
|---|---|---|---|
| 1 | TF-SEC-01: a leaked static key | rotate (deactivate) the key **before** removing it from code, in the first change window | deletes the line and calls it fixed |
| 2 | TF-SEC-02: 0.0.0.0/0 on Postgres | contain it first, before any structural work | sequences it with the refactors |
| 3 | TF-STA-01: dev and prod share one state object | migrate state to per-account buckets with a backup taken first, and say which environment the shared object currently reflects is unknown (🔬) | `terraform state mv`/copies `.tfstate` around |
| 4 | Two roots collapse into one root + per-env inputs; databases move into a module and from `count` to `for_each` | declare every address change with `moved` blocks (`aws_db_instance.db[0]` → `module.database.aws_db_instance.this["orders"]` …) and state the expected plan: **0 to add, 0 to destroy** for the moves | lets the plan recreate three production databases |
| 5 | Prod DB protection must land before any move touches the DBs | add `deletion_protection`/`prevent_destroy` before the identity moves | orders the moves first |
| 6 | Apply path: CI with saved plans and OIDC | put the pipeline foundation before the structural refactors, and hand its design to the pipelines skill | — |
| 7 | Three 🔬 flags in the review | carry them as open questions with the decision each blocks | drops them |

Safety invariants: nothing applied (no `.terraform/terraform.tfstate`), `analysis/` and `docs/design.md` unchanged, no `.tf` file changed (Propose writes a proposal, not the code).
