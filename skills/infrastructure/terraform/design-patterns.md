# Design Patterns — Layouts, State, Modules, Environments

> The patterns Design mode chooses between, each with when it fits, what it costs, and **the
> default**. Cite the principle (T-N, [`theory.md`](theory.md)) when you pick one. When you deviate
> from a default, say why in `design.md`.

---

## §1 Components and lifecycles — where the state lines go

Group resources by **how often they change, who changes them, and what breaks if they're wrong**
(T7; IaC p. 48). A typical cut, from slowest to fastest:

| Layer | Contains | Changes | Blast radius if wrong |
|---|---|---|---|
| **Organization / accounts** | accounts/subscriptions/projects, org policies, SSO, audit logging | rarely; platform team | everything |
| **Foundations** | network (VPC/VNet, subnets, transit, DNS zones), shared KMS, CI identity (OIDC providers, deploy roles) | monthly; platform team | every workload in the account |
| **Shared platform** | clusters, shared databases (avoid if possible), observability stack, registries | weekly; platform team | every tenant |
| **Service** | one service's compute, its own data store, queues, IAM, DNS records, alarms | daily; the service team | that service |

**Default:** one state per layer per environment, and one per service in the service layer.
Co-locate a service's infrastructure with its application code when changes usually span both
(IaC pp. 45–46). Prefer dedicated over shared data stores — shared ones couple every consumer's
change schedule (IaC pp. 43–45).

**Signals a state is too big:** plans take minutes; people are afraid to apply; a coordination ritual
exists for applies; unrelated teams edit the same root (IaC p. 39). **Too small:** many states that
always change together, long `terraform_remote_state` chains, or a script that applies them in
sequence.

## §2 Repository layouts

### 2a. Single root, per-environment inputs — **default for one service or a small platform**

```
infra/
  main.tf  variables.tf  outputs.tf  versions.tf  providers.tf  locals.tf
  envs/
    dev/      backend.hcl  terraform.tfvars
    staging/  backend.hcl  terraform.tfvars
    prod/     backend.hcl  terraform.tfvars
  modules/            # only if something is reused or deserves a boundary
```
`terraform init -backend-config=envs/<env>/backend.hcl` and `plan -var-file=envs/<env>/terraform.tfvars`.
One definition, per-env state and inputs (T10, T21; AWS-PG pp. 22–23). The pipeline loops
environments in order.

### 2b. Thin per-environment roots calling one module

```
live/
  dev/      main.tf (module "stack" { source = "../../modules/stack" ... })  backend.tf
  staging/  main.tf  backend.tf
  prod/     main.tf  backend.tf
modules/stack/
```
Use when environments need **different providers/accounts/regions** that are awkward as variables,
or when per-env backend blocks must be static. Rule: the env roots contain **only** module calls,
provider config and backend — never resources. If resources appear there, it has degraded into
copy-pasted environments (T10).

### 2c. Layered estate (multiple components × environments)

```
live/
  <account-or-env>/
    <region>/
      network/   service-a/   service-b/
modules/          # or a separate module repo
```
Use for a platform with several layers (§1). Each leaf is one state. A wrapper (Terragrunt,
Terramate) is worth it here and only here: it generates the backend/provider boilerplate and
dependency order. Below ~10 states, plain Terraform with 2a/2b is simpler (T22).

### 2d. Module repositories

A module reused across repos gets its own repo named `terraform-<provider>-<name>`, semver tags,
`README.md`, `examples/`, `tests/`, and `versions.tf` with minimum provider versions
(AWS-PG pp. 24–25, 30–31). Modules used by one repo stay in that repo under `modules/`.

**Anti-default:** one directory per environment containing full copies of the resources (IaC p. 33).

## §3 Environment models

| Model | How environments differ | Use | Cost |
|---|---|---|---|
| **Same definition, per-env inputs + per-env backend** | `.tfvars` and backend config only | **Default** (T21) | none |
| **Workspaces** | `terraform.workspace` selects state in one backend | Ephemeral copies of one environment (per-PR previews) in **one** account | One backend and one access policy for all workspaces; no isolation for prod (AWS-PG p. 19) |
| **Per-env roots (2b)** | provider/account blocks per root; same module | Account-per-environment estates | Discipline needed to keep roots thin |
| **Copied definitions** | everything | Never | Drift by construction (T10) |

**Account/subscription per environment** is the strongest isolation and the default for production
on AWS/Azure/GCP: state, IAM and quotas are separated by the cloud itself. Deploy roles are per
account; the pipeline assumes the role for the environment it is applying.

Promotion: the **same commit** is planned and applied to dev → staging → prod, each from its own saved
plan, with prod gated (T12, T13). Environment-specific values have no defaults (T21).

## §4 Module design

- **Depth over breadth.** A module encapsulates a capability with a small interface (a "service with
  its database and alarms", "a VPC with its endpoints and flow logs"). If you can't name it
  differently from the one resource inside, don't make it (AWS-PG p. 25; T9).
- **Nesting ≤ 2.** The root composes modules; modules don't chain through each other (AWS-PG p. 26).
- **Inputs:** typed, described, with `validation` blocks for invariants; objects with `optional()`
  attributes over dozens of flat variables; no defaults for environment-specific values; booleans
  named positively (`enable_x`), units in names (`size_gb`) (AWS-PG pp. 21, 28).
- **Outputs:** every important resource is reachable through an output that references the resource
  (not `var.*`), so callers get correct ordering (AWS-PG pp. 21, 26). Mark secret outputs `sensitive`.
- **Providers:** child modules declare `required_providers` with minimum versions and **never**
  configure a provider; multi-region/account modules take `configuration_aliases` and the caller passes
  `providers = {}` (AWS-PG p. 26; TFB pp. 39–40).
- **Secure defaults:** encryption on, public off, logs on — callers opt out explicitly (T16).
- **Collections:** `for_each` over a map/set with stable keys; `count` only for 0/1 toggles (T8).
- **Compatibility:** adding an optional input is minor; removing/renaming an input or changing an
  address is major — ship `moved` blocks in the module so callers upgrade without replacements
  (AWS-PG p. 21; SRE ch. 27 — don't ship breaking platform changes without automating the
  migration).
- **Community modules:** use maintained, verified ones through their variables; fork only to
  upstream a fix (AWS-PG pp. 37–38).

## §5 Cross-state interfaces

| Mechanism | Use | Cost |
|---|---|---|
| **Data source lookup by tag/name** (`aws_vpc`, `aws_subnets` with filters) | **Default** for foundations → services | Lookup must be precise; an empty result must fail, not fan out to nothing (SRE ch. 7) |
| **Parameter store / registry** (SSM Parameter Store, Consul, App Configuration) | Many consumers; producer publishes a small, versioned contract | One more moving part (IaC pp. 41–43) |
| **`terraform_remote_state`** | Small estates, same team | Consumer needs read access to the producer's whole state (all its secrets); tight coupling |
| Wrapper script passing outputs as `-var` | Never at scale | Brittle; loses independent applies (IaC p. 41) |

The producer's published outputs are an API: change them with a deprecation window, not in one PR.

## §6 Guardrails

| Guardrail | Default |
|---|---|
| Versions | `required_version = "~> 1.X"` in roots; providers `~> N.0` in roots, `>= N.M` in modules; lockfile committed with `terraform providers lock` for every platform CI and devs use (T11) |
| Backend | S3 + `use_lockfile = true` + `encrypt = true` + versioned bucket + per-env bucket or key prefix with per-env IAM (AWS-PG pp. 15–19); azurerm/gcs equivalents |
| Identity | CI assumes a per-environment role via OIDC; plan role read-only, apply role scoped to what the root manages; humans read-only in prod with break-glass (T14) |
| Tags | provider `default_tags` with owner, environment, cost centre, repo (AWS-PG pp. 29–30) |
| Destroy protection | `prevent_destroy` + provider deletion protection on every data-holding resource in prod; a plan guard failing when destroys exceed a threshold (T17) |
| Policy as code | OPA/Conftest, Sentinel or Checkov custom policies on plan JSON: required tags, no public data, no prod destroys without a label (T20) |
| Drift | scheduled `plan -detailed-exitcode` per prod root; exit 2 opens an issue/alert (T18) |
| Secrets | from a secret manager via data source or ephemeral resources; platform-managed passwords where offered; never in tfvars (T15) |

## §7 The apply path (outline — the detail belongs to the pipelines skill)

```
PR opened ─► fmt · validate · tflint · scan · terraform test (plan-mode)
          ─► plan per affected root × env ─► posted to PR + policy check
merge     ─► plan dev -out ─► apply dev ─► smoke/drift check
          ─► plan staging -out ─► apply staging ─► checks
          ─► plan prod -out ─► human approval of *that plan* ─► apply prod ─► checks
schedule  ─► drift plan per prod root
```
Apply always consumes the saved plan it was approved with (T12). Never apply from a PR branch to
prod. Detect affected roots from the diff (changed files → roots that include them, plus callers of
changed modules).

## §8 Testing ladder

| Level | Tool | Runs | Catches |
|---|---|---|---|
| Format/syntax | `terraform fmt -check`, `validate` | pre-commit, every PR | typos, invalid references |
| Lint | `tflint` + provider ruleset | every PR | invalid instance types, deprecated args, unpinned providers |
| Security/compliance | `checkov`, `trivy config`, policy on plan JSON | every PR | public exposure, missing encryption, org rules |
| Plan-mode unit tests | `terraform test` with `command = plan`, mocked providers | every PR | module logic, conditionals, validation |
| Apply-mode integration | `terraform test` (apply) or Terratest in an ephemeral account | module PRs, nightly | real API behaviour, IAM gaps |
| Post-apply | smoke checks, drift plan | after each apply, scheduled | runtime breakage, drift |

Cheapest first; every escaped bug earns a test at the lowest level that would have caught it (T19;
DOH ch. 10).

## §9 AWS provider specifics (AWS-PG)

- Multi-account/region: aliased providers with `assume_role`; resources/modules choose explicitly
  (pp. 2–3).
- Authentication by runner: OIDC for GitHub/GitLab, project role for CodeBuild, instance profile on
  EC2 (IMDSv2), dynamic credentials on HCP Terraform; IAM users only for legacy tools, one per
  pipeline (pp. 6–10).
- State bucket: S3 Standard, SSE, versioning, AWS Backup, CloudTrail data events, alerts on
  workstation unlocks (pp. 12–19).
- Prefer standalone rule/attachment resources (`aws_vpc_security_group_ingress_rule`,
  `aws_iam_role_policy_attachment`) over inline blocks, and never mix the two for one parent
  (pp. 28–29).
- `default_tags` in the provider block (pp. 29–30).
- Look up AMIs with `aws_ami`/SSM parameters next to the instance; don't hard-code `ami-` IDs
  (p. 22).
- Upgrade provider majors root by root, non-prod first, reading the upgrade guide (p. 35).
