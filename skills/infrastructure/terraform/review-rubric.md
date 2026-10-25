# Review Rubric — Six Domains

> The criteria Review mode grades against. Each domain has 🟢 what good looks like, 🔴 the
> anti-patterns (**What / Why / Detect / Severity**), and the **Checklist** whose criteria are scored
> proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md). Grep for candidates with [`detection-signals.md`](detection-signals.md),
> then read each in context — a match is a candidate, not a finding.

---

## 1. structure — layout, modules, interfaces

In scope: every root module and every child module in the codebase.

### 🟢 Well done
- **A predictable layout.** Roots are obvious (one directory per state unit, or one root plus
  `envs/<env>/` inputs); modules under `modules/`; `main.tf`, `variables.tf`, `outputs.tf`,
  `versions.tf`, `providers.tf` (roots only), `locals.tf`; `README.md` per module with an example
  (AWS-PG pp. 20–25).
- **Environments are one definition with different inputs** — not copied directories (T10, T21).
- **Modules are deep**: each represents a capability (network, data tier, service), not one resource;
  nesting ≤ 2 levels; the root composes (T9).
- **Interfaces are typed and described**; environment-specific variables have no defaults;
  `validation` blocks catch bad input early; outputs reference resource attributes (T9).
- **Declarative throughout**: no provisioners doing configuration, no `null_resource` orchestration
  (T4).

### 🔴 Not well done

#### Copy-pasted environments
**What:** `envs/dev`, `envs/staging`, `envs/prod` (or per-region folders) each holding near-identical
resource blocks instead of calls to one module or one root with per-env inputs.
**Why:** Per-environment definitions drift by construction and can't be promoted through a pipeline
(T10, T21; IaC p. 33).
**Detect:** diff the folders; resource blocks (not just module calls and values) repeated across them.
✅ when the duplication is shown by diff.
**Severity:** Medium; High when the copies have already drifted on a security or stateful resource.

#### Monolithic root
**What:** One root holding unrelated lifecycles — network, IAM, databases and every service — or
several environments.
**Why:** The state boundary is the blast radius; every plan is slow and every apply risky (T7;
IaC pp. 37–39).
**Detect:** resource count per root; number of distinct services/teams in one root. ⚠️ proxy.
**Severity:** Medium; High if it contains prod and non-prod (graded in **state**).

#### Thin wrapper modules / deep nesting
**What:** A module whose only content is one resource with pass-through variables; module chains
deeper than two levels; sibling modules calling each other.
**Why:** Indirection without abstraction; every change ripples through layers (T9, T22; AWS-PG
pp. 25–26).
**Detect:** count `resource` blocks per module; module-call depth. ✅.
**Severity:** Low; Medium when it is the dominant pattern.

#### Providers configured inside reusable modules
**What:** `provider "aws" { region = … }` in `modules/**`.
**Why:** The module can't be used in another region/account and can't be removed cleanly (T9;
AWS-PG p. 26).
**Detect:** `provider "` blocks under `modules/`. ✅.
**Severity:** Medium.

#### Untyped, undocumented, over-exposed interface
**What:** Variables without `type` or `description`; defaults on environment-specific values
(`account_id`, `environment`); variables no caller sets; outputs that echo `var.*`.
**Why:** An unclear contract fails late; a default on an env-specific value applies the wrong
environment silently (T9, T21; AWS-PG p. 21).
**Detect:** per-variable scan. ✅.
**Severity:** Low; Medium for defaulted env-specific values.

#### Imperative work inside Terraform
**What:** `provisioner "local-exec"/"remote-exec"`, `null_resource`/`terraform_data` with scripts,
`external` data sources doing work a resource could do.
**Why:** Invisible to plan, untracked in state, not idempotent (T4; AWS-PG p. 23).
**Detect:** grep. ✅ for presence; ⚠️ for "a resource could do it".
**Severity:** Medium.

#### Structurally different environments
**What:** `count = var.environment == "prod" ? 1 : 0` and similar switches scattered through
resources so prod has a different shape from staging.
**Why:** What was tested isn't what ships (T21; CD ch. 10).
**Detect:** conditionals on environment names. ⚠️ (some differences are legitimate sizing).
**Severity:** Medium.

### Checklist (structure)
1. Lives in a predictable, conventional layout with a README (modules) or documented entry point (roots).
2. Is shared across environments rather than copied (roots and env folders).
3. Is a deep module (represents a capability) and nests ≤ 2 levels.
4. Configures no provider (child modules) / configures providers only at the root.
5. Every variable has `type` and `description`; env-specific variables have no default.
6. Contains no imperative provisioning where a resource exists.
7. Differs between environments only by input values.

---

## 2. state — backends, isolation, blast radius

In scope: every root × environment (state unit). Build the **state map** first.

### 🟢 Well done
- Remote backend per state unit with **locking**, **encryption**, **versioning** and backup
  (S3 + `use_lockfile`, or a managed backend) (T6).
- **One backend (or bucket/key prefix with separate access) per environment**; production state
  writable only by the pipeline role and break-glass (T7; AWS-PG pp. 18–19).
- **State boundaries follow lifecycle and ownership** — foundations, shared platform, per-service.
- Cross-state reads go through a narrow, stable interface: data sources or a parameter store, or
  `terraform_remote_state` limited to outputs meant for consumers (IaC pp. 41–43).
- `.gitignore` excludes `*.tfstate*`, `.terraform/`, crash logs.

### 🔴 Not well done

#### State in version control
**What:** `*.tfstate` or `*.tfstate.backup` tracked by git.
**Why:** State holds secrets in plaintext and conflicts on merge (T5, T15).
**Detect:** `git ls-files`. ✅.
**Severity:** Critical when it contains secrets (it usually does); High otherwise.

#### Local state for shared infrastructure
**What:** No `backend` block (or `backend "local"`) in a root that more than one person or a pipeline
applies.
**Why:** No locking, no backup, no shared truth; the laptop is production's state store (T6).
**Detect:** roots with no `backend`/`cloud` block. ✅.
**Severity:** High.

#### Remote state without locking
**What:** `backend "s3"` with neither `use_lockfile = true` nor `dynamodb_table`; other backends with
locking disabled.
**Why:** Concurrent applies corrupt state (T6).
**Detect:** backend block scan. ✅.
**Severity:** High. (DynamoDB-only locking is Low: deprecated, works — recommend migrating.)

#### State not encrypted / not versioned
**What:** `encrypt = false` or absent on S3; the state bucket (if managed here) without versioning or
SSE.
**Why:** No undo for a bad write; secrets at rest unprotected (T5, T6).
**Detect:** backend + bucket config. ✅ when the bucket is in this repo; 🔬 when created elsewhere.
**Severity:** High.

#### Prod and non-prod share state or backend access
**What:** One state for several environments; workspaces as the only environment separation, all in
one backend with one access policy; one key for all envs.
**Why:** A dev mistake becomes a prod outage; access can't be scoped (T7; AWS-PG pp. 18–19).
**Detect:** `terraform.workspace` used to pick environments; one backend config for every env. ✅.
**Severity:** High.

#### Brittle cross-state coupling
**What:** Many roots reading each other's state wholesale via `terraform_remote_state`; cycles; a
wrapper script that applies roots in sequence passing outputs as `-var`.
**Why:** Couples lifecycles back together and leaks every output of the producer (T7; IaC pp. 41–43).
**Detect:** count `terraform_remote_state` per root; scripts chaining applies. ⚠️.
**Severity:** Medium.

### Checklist (state)
1. Uses a remote backend.
2. Has locking enabled.
3. Is encrypted at rest and versioned (🔬 if the bucket is managed elsewhere).
4. Is isolated per environment, with prod writable only by the pipeline/break-glass.
5. Holds one lifecycle (no unrelated services mixed in).
6. Reads other states only through a narrow interface.
7. State files and `.terraform/` are excluded from VCS.

---

## 3. dependencies — versions and sources

In scope: Terraform core constraint and each provider per root; every `module` call.

### 🟢 Well done
- `required_version` in every root; `required_providers` with `source` and constraint in every module
  (T11).
- Roots constrain providers to a major (`~> 5.0`); shared modules state minimums (`>= 5.0`);
  `.terraform.lock.hcl` committed for every root.
- Every module call pinned: registry `version = "x.y.z"`, git `?ref=vX.Y.Z` or a commit SHA;
  modules in the same repo by relative path.
- Provider and module upgrades are deliberate PRs, non-prod first (AWS-PG p. 35).

### 🔴 Not well done

#### Unpinned core or provider
**What:** No `required_version`; provider in `required_providers` without `version`; no
`required_providers` at all.
**Why:** The next `init` silently takes a new major with changed defaults and forced replacements
(T11, T2).
**Detect:** block scan. ✅.
**Severity:** High in roots; Medium in child modules.

#### Lockfile not committed
**What:** `.terraform.lock.hcl` missing or gitignored.
**Why:** Provider builds differ between runs and machines; supply-chain checksums aren't verified (T11).
**Detect:** file presence per root. ✅.
**Severity:** Medium.

#### Floating module source
**What:** Registry source without `version`; git source without `ref`; `ref` naming a branch
(`main`, `master`, `develop`, `production`).
**Why:** Someone else's commit changes your infrastructure on the next init (T11; AWS-PG p. 31).
**Detect:** source/version scan. ✅.
**Severity:** High.

#### Untrusted or forked modules
**What:** Modules from unknown publishers; vendored community modules with local edits.
**Why:** Supply-chain and maintenance risk; the fork never gets upstream fixes (T10, T11; AWS-PG
pp. 37–38).
**Detect:** source namespaces; vendored `terraform-*-*` directories with diffs. ⚠️.
**Severity:** Medium.

### Checklist (dependencies)
1. Core version constrained (per root).
2. Provider version constrained (per provider × module).
3. Lockfile committed (per root).
4. Module source pinned to a tag, version or SHA (per call).
5. Module source is trusted (internal, verified, or reviewed) (per call).

---

## 4. security — identity, secrets, exposure, defaults

In scope: IAM resources, network exposure (security groups, NACLs, public IPs, LBs), data stores,
encryption keys, secrets, provider auth blocks.

### 🟢 Well done
- No credential anywhere in code or tfvars; provider auth via role assumption / OIDC / workload
  identity (T14, T15).
- IAM policies name specific actions on specific resources, built with `aws_iam_policy_document`;
  Terraform's own role scoped per environment (T14).
- Secrets come from a secret manager or are generated and held by the platform; secret-carrying
  variables and outputs are `sensitive` (T15).
- Data stores encrypted, private by default, logged; S3 public access block on; ingress narrow
  (T16).
- `default_tags` at the provider with ownership/cost/environment keys (T16; AWS-PG pp. 29–30).
- Standalone rule resources (`aws_security_group_rule` / `aws_vpc_security_group_ingress_rule`) rather
  than inline blocks mixed with them (AWS-PG pp. 28–29).

### 🔴 Not well done

#### Credential in code
**What:** `access_key`/`secret_key` in a provider; an `AKIA…` string; passwords, tokens or private
keys as literals in `.tf`/`.tfvars`; credential-shaped variables with defaults.
**Why:** Anyone with repo access has it, forever — history keeps it (T15).
**Detect:** grep; secret scanners (`gitleaks`, `trufflehog`). ✅.
**Severity:** Critical. Recommend **rotate, then remove**.

#### Secrets in plain outputs or variables
**What:** `*password*`, `*secret*`, `*token*`, `*key*` variables or outputs without `sensitive = true`;
secrets passed via plain tfvars.
**Why:** Printed in plan/apply logs, visible in CI (T15).
**Detect:** name scan. ⚠️ (names are a proxy).
**Severity:** High.

#### Wildcard IAM
**What:** `Action = "*"` or `Resource = "*"` on write actions; `AdministratorAccess`/`Owner` on a
workload or pipeline role; `iam:PassRole` on `*`.
**Why:** Turns any compromise into an account compromise (T14).
**Detect:** policy scan. ✅.
**Severity:** Critical if a principal outside the account can assume it; High otherwise.

#### Static keys for automation
**What:** `aws_iam_user` + `aws_iam_access_key` for a CI pipeline; keys stored as CI variables.
**Why:** Long-lived, non-rotating, leakable (T14; AWS-PG pp. 9–10).
**Detect:** resource scan; CI files. ✅.
**Severity:** High.

#### Public exposure
**What:** `0.0.0.0/0` / `::/0` ingress to admin or data ports; public buckets (`acl = "public-read"`,
no public access block); `publicly_accessible = true` databases; public IPs on data-tier instances.
**Why:** The most common real-world cloud breach is a default nobody closed (T16).
**Detect:** grep, then read direction/ports. ✅ once confirmed.
**Severity:** Critical for data or admin ports; High otherwise.

#### Encryption or logging off
**What:** Storage, databases, queues, volumes without encryption at rest; no access logs on public
endpoints; KMS keys without rotation.
**Why:** Fail-open defaults (T16).
**Detect:** per-resource attributes; scanners. ✅.
**Severity:** High for data stores; Medium otherwise.

#### Module defaults that fail open
**What:** Reusable-module variables defaulting to public, unencrypted, `0.0.0.0/0`, or logging off.
**Why:** Every caller that doesn't think about it inherits the exposure (T16).
**Detect:** variable defaults in `modules/`. ✅.
**Severity:** High.

#### No tags
**What:** No `default_tags`; taggable resources without ownership/environment tags.
**Why:** Unowned resources are never cleaned up and can't be attributed in an incident (T16).
**Detect:** provider scan. ✅.
**Severity:** Low; Medium where policy requires tags.

### Checklist (security)
1. Contains no credential or secret literal.
2. Secret-carrying variables/outputs are `sensitive` and sourced from a secret store.
3. IAM grants specific actions on specific resources.
4. Automation authenticates with short-lived credentials (role/OIDC), not static keys.
5. Is not publicly exposed unless it is meant to be, and then only on the intended ports.
6. Is encrypted at rest and logged where the resource supports it.
7. Module defaults fail closed.
8. Is tagged with owner and environment (via `default_tags` or explicit tags).

---

## 5. change-safety — identity, destructive changes, drift

In scope: stateful and replace-sensitive resources (databases, buckets with data, volumes, file
systems, KMS keys, DNS zones, certificates, identity providers, anything whose replacement loses data
or breaks callers).

### 🟢 Well done
- Collections of distinct long-lived objects use `for_each` with stable keys, not `count` indexes (T8).
- Renames and moves ship with `moved` blocks; adoptions with `import` blocks; un-management with
  `removed` (T8).
- Stateful resources carry `prevent_destroy` and/or the provider's deletion protection, final
  snapshots, versioning/soft delete; `create_before_destroy` where replacement would cause downtime
  (T17).
- `ignore_changes` only on attributes another system legitimately owns, each with a comment (T18).
- A scheduled drift plan exists and alerts on non-empty diffs (T18) — graded in **delivery** if it
  lives in CI.
- Plans are reviewed with destroy/replace counts called out; a guard fails the pipeline when destroys
  exceed a threshold (T12; SRE ch. 7 — "sometimes zero means all").

### 🔴 Not well done

#### Index-keyed stateful collections
**What:** `count = length(var.x)` with `var.x[count.index]` creating distinct databases, buckets,
users, DNS records, subnets.
**Why:** Removing one element shifts every later index and replaces those objects (T8).
**Detect:** `count.index` used to index a variable list. ✅.
**Severity:** Critical for data-holding resources edited regularly; High otherwise.

#### Renames without `moved`
**What:** (PR review) a resource or module address changes with no `moved` block; README instructions
for `terraform state mv`.
**Why:** Destroy-and-recreate of the renamed objects (T8).
**Detect:** diff address changes. ✅ in a diff; ⚠️ from history.
**Severity:** High for stateful resources; Medium otherwise.

#### Unprotected stateful resources
**What:** Databases, data buckets, KMS keys, DNS zones with no `prevent_destroy` and no deletion
protection; `force_destroy = true` on data buckets; `skip_final_snapshot = true` /
`deletion_protection = false` in production.
**Why:** A replace the reviewer missed is data loss (T17; SRE ch. 26).
**Detect:** attribute scan per stateful type. ✅.
**Severity:** High in production; Medium elsewhere.

#### Drift silenced
**What:** `ignore_changes = all`; `ignore_changes` on security-relevant attributes (policies, ingress,
encryption); no comment saying who else owns the attribute.
**Why:** Hides hand changes instead of fixing their cause — the automation fear spiral (T18;
IaC pp. 15–18).
**Detect:** grep. ✅.
**Severity:** High on security-relevant attributes; Medium otherwise.

#### Fragile data-source fan-out
**What:** `for_each`/`count` over a data source result (a lookup that may return empty or everything)
driving creates or destroys.
**Why:** An empty or wrong lookup reshapes infrastructure silently (T8, T17; SRE ch. 7 Diskerase).
**Detect:** `for_each = data.` / `count = length(data.`. ⚠️.
**Severity:** Medium; High for destructive scope.

#### Plan bypassed
**What:** `-target` in scripts or CI as routine; apply without a saved plan; `-auto-approve` against
production outside a gated pipeline.
**Why:** What was reviewed isn't what's applied (T12).
**Detect:** scripts and CI files. ✅.
**Severity:** High.

### Checklist (change-safety)
1. Collections of distinct objects are keyed by stable `for_each` keys.
2. Address changes are declared with `moved`/`import`/`removed` (PR review; else N/A).
3. Has destroy protection appropriate to its environment.
4. Has backup/snapshot/versioning where it holds data.
5. Uses `ignore_changes` only on attributes owned elsewhere, with a reason.
6. Is not created or destroyed by an unguarded data-source fan-out.
7. Reaches apply only through a saved, reviewed plan (graded per root).

---

## 6. delivery — the path from commit to apply

In scope: root modules. Grade *whether* each root has a safe path; the pipeline's internal design is
the [pipelines](../pipelines/SKILL.md) skill's job.

### 🟢 Well done
- Pre-commit and CI run `fmt -check`, `validate`, `tflint`, and a security scanner, and **fail** on
  findings (T19; AWS-PG pp. 13, 33–35).
- Every PR gets a plan per affected root/environment posted for review (T12).
- Apply runs in CI from the saved plan, with an approval on production, using a per-environment
  short-lived role; humans don't hold prod write credentials (T13, T14).
- Changes are promoted through environments: same code, non-prod first (T13, T21).
- Policy as code on the plan (required tags, no public data, no prod destroys) (T20).
- Reusable modules have examples and tests (`terraform test`, Terratest) that apply in an
  ephemeral account (T19).
- A scheduled drift detection job (T18).

### 🔴 Not well done

#### Applied from laptops
**What:** No CI apply job; README instructs `terraform apply`; humans hold prod-write credentials.
**Why:** Unreviewed, unaudited, and the laptop's toolchain becomes production's (T13; IaC pp. 54–55).
**Detect:** CI files; README. ✅ for absence of a CI apply; 🔬 for who holds credentials.
**Severity:** High for production roots.

#### No static checks
**What:** No `fmt`/`validate`/lint/scan in CI or pre-commit; scanners configured with
`soft_fail: true` or failures ignored.
**Why:** The cheapest feedback is missing (T19).
**Detect:** CI and `.pre-commit-config.yaml`. ✅.
**Severity:** Medium.

#### Plan not visible before merge
**What:** Plans run only at apply time, or aren't posted to the PR.
**Why:** Review is of the code, not of the change to infrastructure (T12).
**Detect:** CI triggers. ✅.
**Severity:** High for production roots.

#### No promotion path
**What:** Prod and non-prod applied by different code paths, or prod first; no environment order.
**Why:** Nothing tested the change before production (T13, T21).
**Detect:** CI. ✅.
**Severity:** High.

#### Untested reusable modules
**What:** Shared modules with no example that is ever applied, no `terraform test`.
**Why:** Every caller finds the bug for you (T19).
**Detect:** presence of `examples/`, `tests/`, `*.tftest.hcl`. ✅.
**Severity:** Medium.

### Checklist (delivery)
1. Static checks (fmt, validate, lint, scan) run and fail the build.
2. A plan is produced and visible for review before merge.
3. Apply runs from CI using the saved plan.
4. Production apply is gated and uses a scoped, short-lived identity.
5. Changes promote through non-prod before prod with the same code.
6. Policy checks run on the plan (or N/A with the reason).
7. Drift is detected on a schedule.
