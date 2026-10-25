# Theory — The Principles Every Terraform Finding Cites (T1–T22)

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** for Terraform specifically, and **what violating it looks like** in code. Sources are
> cited by short name:
>
> | Short name | Source |
> |---|---|
> | **IaC** | Kief Morris, *Infrastructure as Code: Managing Servers in the Cloud* (O'Reilly, 2016), ch. 1–2 |
> | **TFB** | James Turnbull, *The Terraform Book* (v1.5, 2019), ch. 3 |
> | **AWS-PG** | AWS Prescriptive Guidance, *Best practices for using the Terraform AWS Provider* (rev. 2025) |
> | **CD** | Humble & Farley, *Continuous Delivery* (2010) |
> | **DOH** | Kim, Humble, Debois & Willis, *The DevOps Handbook* (2016) |
> | **SRE** | Beyer, Jones, Petoff & Murphy (eds.), *Site Reliability Engineering* (2016) |
> | **TF docs** | The Terraform/OpenTofu language documentation — used where the books predate a feature (`for_each`, `moved`, `import`, `removed`, `check`, `terraform test`) |
>
> Page numbers are printed pages. The books teach principles; where a Terraform feature postdates
> them, the principle comes from the book and the mechanism from TF docs.

---

## Part A — What infrastructure as code is for

### T1 — Everything is defined in code, in version control
**Says:** Infrastructure is specified in text definition files, kept in VCS, and a commit is what
drives a change. The VCS is the source of truth for desired state (IaC pp. 22–24; CD ch. 2; DOH ch. 9).
**Why:** Only what is written down can be reviewed, reproduced, rolled back, or correlated with an
incident. Anything made by hand in a console ("ClickOps") is invisible to every one of those.
**Violation:** resources referenced only by hard-coded ID or `data` lookup with no defining code
anywhere; networking, DNS or IAM missing from a repo that manages the compute on top of them
(IaC's *hand-crafted infrastructure* antipattern, p. 31); internal tooling (CI, monitoring) with no
code — *snowflake environments* (IaC p. 31).

### T2 — Systems are reproducible
**Says:** Any element can be rebuilt with no significant decisions left to a human; versions, names
and sizes live in code (IaC pp. 18–19). The test of reproducibility is to **build forward** — create a
fresh instance from the code and test it — not to generate code from what exists (IaC p. 54).
**Why:** Reproducibility removes the fear from change and from failure; a team that can't rebuild an
environment can't safely change it.
**Violation:** bulk-imported or generated code that has never been applied to a fresh environment;
an environment that "can't be torn down"; required manual steps in a README between `apply`s.

### T3 — Small pieces, small changes
**Says:** Prefer small, frequent changes over batches; they are easier to test, debug and reverse,
and one fault doesn't block the rest (IaC pp. 24–25; DOH ch. 1–2 on batch size). Design is always
changing, so keep it as simple as current needs require (IaC p. 21).
**Why:** In Terraform the batch is the plan. A plan with 300 changes cannot be reviewed; a plan with
6 can.
**Violation:** routinely huge plans; release-train style infrastructure PRs; speculative modules and
variables nobody sets.

### T4 — Desired state, converged
**Says:** Terraform is declarative: code states the end state; `plan` computes the difference from
current reality; `apply` converges (TFB pp. 69–72). Ordering comes from the dependency graph built
from references, with `depends_on` only for dependencies references can't express (TFB p. 47;
AWS-PG p. 21).
**Why:** Imperative steps hidden inside a declarative tool (`local-exec`, `null_resource`, scripts)
are invisible to `plan`, untracked in state, and not idempotent (AWS-PG p. 23).
**Violation:** provisioners doing configuration; `null_resource` + `triggers` orchestration;
`depends_on` used where a reference would do; references written as quoted strings (an old-syntax
bug, TFB p. 27).

## Part B — State

### T5 — State is the map between code and reality
**Says:** State records which real object each resource address corresponds to, plus its attributes.
Lose it and Terraform loses track of what it owns; leak it and you leak every secret any resource
wrote into it (AWS-PG p. 12; TFB p. 20).
**Why:** State is not a cache. It is part of the system, and most of the scariest Terraform incidents
— duplicate resources, orphaned infrastructure, mass destroys — are state incidents.
**Violation:** `*.tfstate` in VCS or missing from `.gitignore`; state bucket without versioning or
backup; manual edits of state JSON.

### T6 — Remote state, locked, encrypted, audited
**Says:** Shared state lives in a remote backend with locking, encryption at rest, versioning and
backup, and access audited (AWS-PG pp. 15–18). On S3, native locking (`use_lockfile = true`,
Terraform ≥ 1.10) replaces the deprecated DynamoDB lock (AWS-PG p. 16).
**Why:** Two concurrent applies against unlocked state corrupt it. Versioning is the only undo for a
bad state write.
**Violation:** `backend "local"` or no backend for shared infrastructure; S3 backend without
`use_lockfile`/`dynamodb_table`; `encrypt = false`; state bucket without versioning.

### T7 — Blast radius: one state per lifecycle, per environment
**Says:** Draw state boundaries along the **scope of change** — resources that change together, by
the same team, at the same rate, belong together (IaC p. 48). A *monolithic stack* makes every small
change risky and every plan slow (IaC pp. 37–39). Each environment has its own backend, and production
state is writable only by the pipeline and break-glass roles (AWS-PG pp. 18–19). Prefer dedicated over
shared infrastructure: change overhead grows with the number of consumers (IaC pp. 43–45).
**Why:** A bad apply can damage everything in its state and nothing outside it. The state boundary
*is* the blast radius.
**Violation:** prod and non-prod in one state; environments switched by `terraform.workspace` in one
backend; one root with hundreds of resources across unrelated services; a wrapper script that
applies every stack in sequence threading outputs between them (IaC pp. 41–43). The signal from the
people side: teams are afraid to apply, or a coordination meeting exists for applies (IaC p. 39).

### T8 — Resource identity is the address
**Says:** Terraform identifies a resource by its address (`module.x.aws_s3_bucket.logs["eu"]`).
Changing the address — a rename, a move into a module, a `count` index shift — means *destroy the old,
create the new* unless the move is declared (TF docs: `moved`, `import`, `removed`).
**Why:** For stateless resources that's churn; for a database, a bucket, a KMS key or a DNS zone it's
data loss. `count` keyed by list position is the classic trap: remove a middle element and every
later instance is replaced.
**Violation:** `count = length(var.list)` with `var.list[count.index]` for distinct, long-lived
objects; renames in a diff with no `moved` block; `terraform state mv` in a README instead of a
committed `moved` block.

## Part C — Code structure

### T9 — Modules are interfaces
**Says:** A module is an API: variables are inputs, outputs are the response, resources are hidden
(TFB pp. 29, 42–46). A good module raises the level of abstraction to an architectural concept; a
module that wraps one resource adds indirection and nothing else (AWS-PG p. 25). Keep nesting to one
or two levels; let the root compose (AWS-PG pp. 22, 26). Reusable modules declare
`required_providers` but never configure a provider (AWS-PG p. 26). Every variable has a type and a
description; expose a variable only when something really varies; adding one is compatible, removing
one is breaking (AWS-PG p. 21).
**Why:** The interface is what callers depend on. A shallow, leaky interface spreads every internal
change to every caller.
**Violation:** single-resource wrapper modules; `provider` blocks or hard-coded `region` inside
`modules/`; variables without `type`/`description`; outputs that echo an input (`value = var.x`) and
lose the dependency edge (AWS-PG p. 21); a removed variable without a major version bump.

### T10 — Share deliberately; don't copy environments
**Says:** One parameterized definition serves every environment (*re-usable definition files*);
copied per-environment definitions are an antipattern because nothing keeps them consistent and no
pipeline can promote a change through them (IaC pp. 33–35). For code shared across teams, prefer
versioned modules that callers opt into over a mandatory central library (IaC p. 47); customize
community modules through variables, don't fork them (AWS-PG p. 37).
**Why:** Copy-paste environments drift by construction, and the copy you didn't update is the one
that breaks.
**Violation:** `envs/dev/main.tf` and `envs/prod/main.tf` with near-identical resources rather than
thin calls to one module; vendored, locally edited community modules.

### T11 — Pin everything
**Says:** Pin Terraform core (`required_version`), every provider (`required_providers` with a
constraint, plus the committed `.terraform.lock.hcl`) and every module (registry `version`, git
`?ref=<tag>` or commit SHA) (AWS-PG pp. 27, 31–35). Shared modules state minimums (`>=`); roots
constrain to a major (`~>`). Upgrade providers in non-production first (AWS-PG p. 35).
**Why:** An unpinned dependency is a change nobody reviewed. A provider major version can change
defaults and force replacements.
**Violation:** no `required_version`; provider without `version`; `.terraform.lock.hcl` in
`.gitignore`; module `source` with no `version`, or `?ref=main`/a branch (TFB p. 33 shows a branch
pin — it is the pattern to flag).

## Part D — Change safety

### T12 — The plan is the contract
**Says:** Always plan before apply and read the add/change/destroy counts (TFB pp. 69–70). What was
reviewed must be what is applied: save the plan (`plan -out`) and apply that file (TF docs). Changes
go through pull requests with run approvals and policy checks (AWS-PG p. 12).
**Why:** Between a plan and a later fresh apply, the code, the provider or reality can change. An
apply that re-plans applies something nobody saw.
**Violation:** `terraform apply -auto-approve` with no saved plan; apply jobs that re-plan; plans
not posted where reviewers see them.

### T13 — Everything goes through the pipeline
**Says:** Run Terraform from a central, rebuildable agent driven by CI/CD, not from laptops: it is
logged and audited, needs no credentials on personal machines, and its toolchain isn't a snowflake
(IaC pp. 54–55; AWS-PG pp. 12, 18–19). Test and promote the same definition through environments
(IaC p. 35; CD ch. 5, 11).
**Why:** A laptop apply bypasses review, policy and audit, and the laptop's Terraform/provider
versions become production's.
**Violation:** READMEs telling humans to `terraform apply`; humans holding write credentials to prod
state; no CI job that applies; state unlocks from workstations (AWS-PG p. 19).

### T17 — Destructive changes are guarded
**Says:** Resources that hold data or identity are protected against accidental replacement and
deletion — `lifecycle { prevent_destroy = true }`, provider-level `deletion_protection`, backups
whose restore is tested — and policy can block destroying production resources outright (AWS-PG
p. 14; SRE ch. 26 on data integrity; TF docs).
**Why:** Most Terraform data loss is a replace the reviewer didn't notice in a long plan.
**Violation:** stateful resources (databases, buckets with data, KMS keys, DNS zones, volumes) with no
protection; `force_destroy = true` on data buckets; `skip_final_snapshot = true` on production
databases; `create_before_destroy` missing where a replacement would cause downtime.

### T18 — Drift is detected, not tolerated
**Says:** Configuration drift — reality diverging from code through hand changes — feeds the
*automation fear spiral*: people stop running automation because it might "undo" hand fixes, so
drift grows (IaC pp. 15–18). The cure is to run the automation continuously and unattended (IaC
p. 18) — for Terraform, a scheduled plan that alerts on any diff (AWS-PG p. 13 uses runtime scanners
for the same purpose).
**Why:** Drift turns the next routine apply into an unplanned revert of somebody's emergency fix.
**Violation:** no scheduled drift plan; `ignore_changes` used to silence drift instead of fixing its
cause; `ignore_changes = all`.

## Part E — Security

### T14 — Least privilege, for resources and for Terraform itself
**Says:** Grant specific actions on specific resources, build policies up from empty, use Access
Analyzer to remove unused permissions (AWS-PG pp. 5–6). Terraform authenticates with roles and
short-lived credentials — OIDC from CI, instance profiles, assumed roles locally — never static keys
(AWS-PG pp. 6–10).
**Why:** Terraform's own role is usually the most powerful identity in the account; if it leaks, the
blast radius is the account.
**Violation:** `"Action": "*"` / `resources = ["*"]`; `AdministratorAccess` on the CI role;
`aws_iam_access_key` for a pipeline user; `access_key`/`secret_key` in a provider block.

### T15 — Secrets are never in code, and as little as possible in state
**Says:** Credentials never go in `.tf` or `.tfvars` (TFB pp. 3, 23; AWS-PG p. 22: tfvars are for
non-sensitive values). Secrets live in a secret manager; Terraform references them; variables and
outputs that carry secrets are `sensitive = true` — which hides them from output, **not** from state
(TFB p. 44; AWS-PG p. 12). Prefer resources that let the platform generate and hold the secret (e.g.
managed master passwords) and ephemeral values where the Terraform version supports them (TF docs).
**Violation:** literal passwords/keys; `*password*`/`*token*` variables without `sensitive`; secrets
emitted as plain outputs; state readable by people who shouldn't read the secrets inside it.

### T16 — Defaults fail closed
**Says:** Encryption on, public access off, logging on, ingress narrow — by default in modules, so a
caller has to opt *out* explicitly and visibly. Tag everything through provider `default_tags` so
ownership and cost are never missing (AWS-PG pp. 29–30).
**Why:** Most cloud exposures are a default nobody changed.
**Violation:** module variables defaulting to public, unencrypted or `0.0.0.0/0`; S3 buckets without
a public access block; no `default_tags`.

### T20 — Policy as code
**Says:** Organizational rules — required tags, allowed instance types, no destruction of production,
no public buckets — are enforced by policy checks in the pipeline (Sentinel, OPA/Conftest, Checkov
custom policies) rather than by reviewers remembering them (AWS-PG pp. 13–14; DOH ch. 22–23).
**Violation:** rules that exist only in a wiki; scanners present but with failures ignored.

## Part F — Delivery and testing

### T19 — Test infrastructure code continuously, cheapest checks first
**Says:** Test continuously and in small increments; fast feedback is what removes automation fear
(IaC p. 24). Order the checks like a test pyramid (CD ch. 4; DOH ch. 10): `fmt` and `validate`
(TFB p. 68), then lint (`tflint` with the provider ruleset) and security scanning (`checkov`,
`trivy`/`tfsec`) as pre-commit hooks and CI gates (AWS-PG pp. 13, 33–35), then plan-level tests
(`terraform test` with `command = plan`, policy on plan JSON), then apply-level tests in an ephemeral
environment (`terraform test` with `apply`, Terratest), then post-apply smoke checks (TF docs; SRE
ch. 17).
**Violation:** no CI checks; scanners whose failures don't fail the build; reusable modules with no
example or test that has ever been applied.

### T21 — Environments differ only by their inputs
**Says:** Elements doing the same job are identical apart from the configuration that must differ
(IaC p. 20); environments are instances of the same definition with different parameters and their
own state (IaC pp. 33–35). Environment-specific values have no defaults, so forgetting one fails
loudly (AWS-PG p. 21).
**Why:** Then a change tested in staging is the change that reaches production (CD ch. 10).
**Violation:** `count = var.env == "prod" ? 1 : 0` sprinkled through resources to make environments
structurally different; per-env code forks; defaults on `account_id`/`environment`.

### T22 — Simplicity
**Says:** Boring, simple systems are reliable systems; every line of code is a liability, and
unneeded features, flags and abstractions should be removed (SRE ch. 9). Don't over-design up front
(IaC p. 21). Use modules in moderation (AWS-PG p. 25).
**Violation:** layers of wrapper modules; dynamic blocks and `for` expressions that make a plan
unreadable to save a few lines; variables nobody sets; meta-tooling (generators, wrappers) for a
codebase of a dozen resources.

---

## Theory → domain index

| Domain | Principles |
|---|---|
| structure | T3, T9, T10, T21, T22, T4 |
| state | T5, T6, T7 |
| dependencies | T2, T11 |
| security | T14, T15, T16 |
| change-safety | T8, T12, T17, T18 |
| delivery | T13, T19, T20, T1 |
