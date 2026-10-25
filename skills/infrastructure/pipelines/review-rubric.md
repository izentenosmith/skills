# Review Rubric — Six Domains

> The criteria Review mode grades against. Each domain has 🟢 what good looks like, 🔴 the
> anti-patterns (**What / Why / Detect / Severity**), and the **Checklist** whose criteria are scored
> proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md). Find candidates with [`detection-signals.md`](detection-signals.md),
> then read each job in context — a match is a candidate, not a finding.

---

## 1. flow — the path from commit to artifact to production

In scope: each pipeline definition that builds or ships something.

### 🟢 Well done
- Triggered on every push/PR to trunk; stages chained, each consuming the previous stage's output
  (P5).
- **One build** produces an immutable, environment-agnostic artifact, versioned by commit/build ID,
  stored in a registry; every later stage pulls it by digest (P3).
- Pipeline logic lives in versioned scripts/targets (`make test`, `./ci/deploy.sh`) that developers can
  run too; YAML orchestrates (P2).
- Shared steps come from a **versioned template** (reusable workflow, `include:` with a ref, template
  repo), not copy-paste (P15).
- Dependency caches, parallel jobs/shards, and path filters keep the commit stage within budget (P5).
- Short-lived branches merged to trunk daily; release branches (if any) cut from trunk (P7).

### 🔴 Not well done

#### Rebuild per environment
**What:** Build/compile/`docker build` steps inside deploy or later-stage jobs; a build job per
environment; production built from a release tag/branch rather than promoted.
**Why:** What was tested isn't what ships (P3; CD pp. 113–114, 402–403).
**Detect:** build commands under deploy jobs; `needs:` absent between build and deploy. ✅.
**Severity:** High.

#### Environment-specific artifacts
**What:** `--build-arg ENV=…`, `build:prod`, `-Pprod`, one image tag per environment, config files
copied into the image per environment.
**Why:** The artifact can't be promoted; config is frozen into binaries (P3, P10; CD pp. 41–42).
**Detect:** grep. ✅.
**Severity:** High.

#### Mutable, untraceable artifacts
**What:** Images/packages tagged `latest`, by branch, or overwritten; deploys referencing a tag not a
digest; no revision stamped in the artifact.
**Why:** You can't say what is running or roll back to it (P3, P19; SRE ch. 8 p. 90).
**Detect:** tag patterns in push/deploy steps. ✅.
**Severity:** High when production deploys by mutable tag; Medium otherwise.

#### Schedule-only integration
**What:** Acceptance/integration stages triggered only by cron; CI only on `develop`/feature branches;
long-lived branches as the integration model.
**Why:** Failures surface a day late and can't be tied to a commit; no real integration (P5, P7).
**Detect:** triggers. ✅ for triggers; 🔬 for branch age.
**Severity:** Medium.

#### Manual handoffs in the value stream
**What:** The pipeline stops at "upload artifact"; a person deploys by runbook; manual promotion
copies artifacts between registries by hand.
**Why:** Unrepeatable, unaudited, and the release path that matters most is the least practised
(P1, P4; DOH ch. 12).
**Detect:** no deploy job for an environment that exists; README deploy steps. ✅.
**Severity:** High for production; Medium otherwise.

#### Logic only in the CI tool
**What:** Long inline `run:` / `script:` blocks with no local entry point; behaviour that can't be
reproduced off the CI runner.
**Why:** Developers bypass it; nobody can debug or refactor it (P2; CD ch. 6).
**Detect:** inline script length per job. ⚠️.
**Severity:** Low; Medium when the deploy itself is inline-only.

#### Copy-pasted pipelines
**What:** Near-identical YAML across repos or across jobs in one file (per environment, per service)
instead of a template or matrix.
**Why:** Fixes land in one copy; the copies drift (P15; DOH ch. 20).
**Detect:** diff jobs/files. ✅ once diffed.
**Severity:** Medium.

### Checklist (flow)
1. Triggers on every change to trunk and on PRs.
2. Builds the artifact exactly once, upstream of every deploy.
3. The artifact is environment-agnostic, immutable and traceable to its revision.
4. Later stages consume the artifact by digest/ID from a registry.
5. Uses versioned shared templates or matrices instead of copy-paste.
6. Has a local entry point for each stage's logic.
7. Has no manual handoff between commit and the last automated environment.

---

## 2. feedback — tests, gates and stopping the line

In scope: test and verification jobs, plus each pipeline's commit stage.

### 🟢 Well done
- Commit stage (compile, unit tests, lint, static analysis, package) completes in ≤ 10 minutes (P5).
- Tests follow the pyramid: many unit, fewer component/acceptance, few end-to-end (P8).
- Acceptance tests run in a production-like environment against the deployed artifact and **gate**
  every later stage (P8).
- Failing tests fail the build; flaky tests are quarantined out of the gate with an owner and a
  ticket, not retried silently (P6).
- Test reports and artifacts upload even on failure (`if: always()`); failures are visible where the
  team looks (P5).
- An environment/smoke check runs first in each acceptance run and aborts it fast (P5; CD p. 217).

### 🔴 Not well done

#### Silenced failures
**What:** `continue-on-error: true`, `allow_failure: true`, `|| true`, `-DskipTests`, `--passWithNoTests`
on gating test jobs; ignore lists that only grow.
**Why:** The alarm is muted; regressions accumulate (P6; CD p. 70).
**Detect:** grep on test jobs. ✅.
**Severity:** High on the commit or acceptance gate; Medium elsewhere.

#### Retry-until-green
**What:** Blanket `retry:` / rerun wrappers on test jobs; reruns as the documented fix.
**Why:** Flakiness hidden is flakiness kept; people learn to ignore red (P6; DOH ch. 10; SRE ch. 17).
**Detect:** retry config on test jobs. ⚠️ (a retry for runner infrastructure failures only is fine).
**Severity:** Medium.

#### Slow or misordered commit stage
**What:** E2E, UI or container-heavy suites in the first gating job; no cache; serial jobs that could
run in parallel; commit stage > 10 minutes.
**Why:** Slow feedback grows batches and stops people caring (P5; CD p. 185).
**Detect:** job graph ✅; duration 🔬 unless history is supplied.
**Severity:** Medium.

#### No gating acceptance stage
**What:** Deploys to staging/prod don't depend on acceptance; acceptance non-blocking; acceptance only
nightly.
**Why:** Unfit candidates reach users (P8; CD pp. 124, 213).
**Detect:** `needs:`/`dependencies`/`dependsOn` graph. ✅.
**Severity:** High when prod has no automated test gate at all; Medium otherwise.

#### Inverted pyramid
**What:** Most test time in UI/e2e tests; few or no unit tests.
**Why:** Slow, brittle feedback dependent on scarce environments (P8; DOH ch. 10).
**Detect:** test job inventory. ⚠️.
**Severity:** Medium.

### Checklist (feedback)
1. Runs the commit stage within ~10 minutes (🔬 without history; ⚠️ from the job graph).
2. Fails the build on test failure (no silencing).
3. Handles flaky tests by quarantine with ownership, not blanket retry.
4. Gates every later stage on automated acceptance.
5. Runs tests in pyramid proportions.
6. Publishes results on failure and makes them visible.

---

## 3. release — deploying, verifying, rolling back

In scope: deploy jobs × target environment.

### 🟢 Well done
- One deploy mechanism for every environment, parameterized by environment config (P4).
- Every deploy runs a smoke/health check that can fail it, then emits a deploy marker (P13, P20).
- Rollback is the same mechanism with the previous artifact (or a blue/green flip), runnable in one
  step and exercised at least once (P13).
- Production uses a progressive strategy matched to risk — rolling with bounded surge/unavailable,
  blue-green, or canary with automated analysis — and promotion reads user-facing metrics (P12).
- Deploy and release are decoupled with feature flags where the product needs it (P11).
- Database migrations are versioned, run by the deploy, and expand/contract (P21).
- Production protection is risk-based: peer review before merge plus an environment protection rule;
  the author can't self-approve prod if separation of duties is required (P16).
- Emergency fixes use the same pipeline; there is no test-skipping hotfix path (P13).

### 🔴 Not well done

#### Fire-and-forget deploy
**What:** The deploy job ends at `kubectl apply`/`helm upgrade`/`az webapp deploy` with no health,
rollout-status or smoke step.
**Why:** A bad deploy is discovered by users (P13; CD p. 117; DOH ch. 12).
**Detect:** last steps of deploy jobs. ✅.
**Severity:** High for production.

#### No rollback path
**What:** No job or documented one-step way to redeploy the previous artifact; a hand-written
`rollback.sh` unlike the deploy; deploys that copy only changed files.
**Why:** Rarely used paths fail when needed (P13; CD pp. 131–132; SRE ch. 13).
**Detect:** workflow inventory. ✅ for absence; 🔬 for "rehearsed".
**Severity:** High for production.

#### Different deploy per environment
**What:** Separate scripts or steps for prod; prod uses a different tool; prod jobs carry extra inline
steps.
**Why:** Production is the least rehearsed path (P4).
**Detect:** diff deploy jobs. ✅.
**Severity:** High.

#### Big-bang production rollout
**What:** One job deploys every region/cluster at once; `maxUnavailable` 100% / replace-all; no bake
between stages.
**Why:** The whole user base is exposed to every bad change (P12; SRE ch. 1, ch. 22).
**Detect:** deploy targets and strategy config. ✅.
**Severity:** Medium; High for large user-facing services.

#### Canary without a gate
**What:** Progressive steps with fixed sleeps and no metric analysis or automatic rollback.
**Why:** A canary nobody watches is a slow big bang (P12; DOH ch. 12).
**Detect:** rollout config (Argo Rollouts/Flagger analysis, deploy job checks). ✅.
**Severity:** Medium.

#### Risky migrations
**What:** No migration step; destructive DDL (drop/rename/type change) shipped with the code that
stops using it; migrations run manually.
**Why:** No rollback once the schema has moved (P21; CD pp. 329–334).
**Detect:** migrations directory and deploy steps; DDL in the diff. ✅ for structure; ⚠️ for content.
**Severity:** High when destructive DDL ships with the code change; Medium otherwise.

#### Test-skipping hotfix lane
**What:** `skip_tests` inputs, `[skip ci]`, or a separate workflow that deploys straight to prod.
**Why:** The riskiest changes get the least verification (P13; CD pp. 265–266; SRE ch. 17 p. 201).
**Detect:** workflow inputs and paths. ✅.
**Severity:** High.

#### Approval theatre
**What:** Manual approvals on every environment; approvers outside the team; approval as the only
control before prod (no automated tests).
**Why:** Distant approval worsens both stability and speed and rubber-stamps (P16; DOH ch. 18).
**Detect:** environment protection config (🔬 if UI-only); `when: manual` / approval stages ✅.
**Severity:** Medium; High when it replaces automated testing.

### Checklist (release)
1. Uses the same deploy mechanism as every other environment.
2. Runs a post-deploy check that can fail the deploy.
3. Has a one-step rollback using the same mechanism.
4. Uses a rollout strategy matched to the target's risk (bounded, progressive for prod).
5. Promotion past a canary/stage is gated by health signals (or N/A for non-prod).
6. Applies schema changes by versioned, backward-compatible migrations (or N/A).
7. Emits a deploy marker / record of what version is where.
8. Has no path to prod that skips tests.
9. Production gating is peer/automation-based rather than distant manual approval.

---

## 4. security — credentials, untrusted input, supply chain

In scope: jobs that hold a credential or run untrusted input, plus every third-party action, image,
orb, template or plugin reference.

### 🟢 Well done
- No secret in any pipeline file; secrets in the platform's store or a vault, scoped to environments
  (P18).
- Cloud access by OIDC federation, per-environment roles, least privilege; no static cloud keys (P18).
- Token permissions minimal by default (`permissions: contents: read` at top level), elevated per job
  (P18).
- Untrusted triggers (fork PRs, `pull_request_target`, `workflow_run`, issue/comment events) never
  check out and execute PR code with secrets; event fields are passed via `env:`, not interpolated
  into `run:` (P18).
- Third-party actions/images pinned by full commit SHA or digest, updated by a bot (P14, P18).
- SAST, dependency (SCA), secret and IaC scans run on PRs and fail on agreed severities (P17).
- Release artifacts are signed with provenance/SBOM attached and verified at deploy (P19).
- Runners are ephemeral and isolated; self-hosted runners are never used for public-repo PRs (P18).

### 🔴 Not well done

#### Secret in a pipeline file
**What:** Literal tokens, keys, passwords or connection strings in YAML or scripts; secrets echoed to
logs.
**Why:** Anyone with read access has them; history keeps them (P18).
**Detect:** grep; `gitleaks`. ✅.
**Severity:** Critical. Rotate, then remove.

#### Untrusted code with secrets
**What:** `pull_request_target`/`workflow_run` that checks out `github.event.pull_request.head.*` and
runs build/test; GitLab pipelines for fork MRs running in the parent project with protected variables;
self-hosted runners on public PRs.
**Why:** Any outsider runs arbitrary code with your credentials (P18).
**Detect:** trigger + checkout ref. ✅.
**Severity:** Critical.

#### Script injection
**What:** `${{ github.event.issue.title }}`, `head_ref`, PR body, commit message and similar
attacker-controlled fields interpolated into `run:`.
**Why:** Shell injection inside a job with a token (P18).
**Detect:** grep. ✅.
**Severity:** High; Critical if the job holds deploy credentials.

#### Static cloud credentials
**What:** `AWS_ACCESS_KEY_ID`/`AZURE_CLIENT_SECRET`/service-account JSON stored as CI secrets where
the platform supports OIDC.
**Why:** Long-lived, non-rotating, exfiltratable (P18; AWS-PG pp. 8–10).
**Detect:** secret names used in jobs; absence of `id-token: write`. ✅.
**Severity:** High.

#### Over-broad token
**What:** `permissions: write-all` or no `permissions` block (defaulting to write in older repos);
deploy roles with admin across environments.
**Why:** Turns any job compromise into repo/account compromise (P18).
**Detect:** grep. ✅ (🔬 for the repo default).
**Severity:** High.

#### Unpinned third-party code
**What:** `uses: owner/action@v3` / `@main`, `image: node:latest`, `include: remote:` without a ref,
Jenkins plugins unpinned — in jobs that hold credentials.
**Why:** The upstream maintainer (or whoever compromises them) controls your pipeline (P14, P18).
**Detect:** grep for non-SHA refs. ✅.
**Severity:** High in credentialed jobs; Medium otherwise. First-party (`actions/*`) by tag is Low.

#### No security scanning
**What:** No SAST, SCA, secret or IaC scan; scanners set to never fail.
**Why:** Findings arrive late or never (P17; DOH ch. 22).
**Detect:** job inventory. ✅.
**Severity:** Medium.

#### Unsigned, unverifiable artifacts
**What:** No signing, provenance or SBOM for released artifacts; deploy doesn't verify.
**Why:** No proof that what runs is what was built (P19).
**Detect:** absence of cosign/attest/sbom steps. ✅.
**Severity:** Low for internal services; Medium for distributed software or regulated contexts.

### Checklist (security)
1. Contains no secret literal and doesn't echo secrets.
2. Doesn't run untrusted code or untrusted input with secrets in scope.
3. Authenticates to clouds with short-lived federated identity.
4. Runs with least-privilege token permissions.
5. Pins third-party actions/images/templates to an immutable reference.
6. Runs SAST, SCA, secret and IaC scanning that can fail the build.
7. Signs released artifacts and attaches provenance (or N/A with reason).
8. Runs on isolated, ephemeral runners appropriate to the trust of its trigger (🔬 if runner config isn't in the repo).

---

## 5. environments — parity and configuration

In scope: each environment (dev, test, staging, prod, ephemeral/preview).

### 🟢 Well done
- Every environment is created from version-controlled definitions; staging mirrors prod's stack and
  topology at smaller scale (P9).
- Configuration is injected at deploy/run time from per-environment sources; artifact identical across
  environments (P10).
- Config changes go through the same pipeline and the same canary as code (P10).
- Ephemeral preview environments per PR where the stack allows, torn down automatically (P9).
- Production data never copied to lower environments without masking (P21; CD pp. 343–344).

### 🔴 Not well done

#### Snowflake environments
**What:** Environments with no IaC; staging on a different runtime/base image/OS than prod; environments
provisioned by ticket.
**Why:** Environment surprises at release; slow, wrong environments are the usual first constraint
(P9; DOH ch. 2, 9).
**Detect:** IaC presence per environment; runtime versions per environment. ✅/⚠️.
**Severity:** Medium; High for prod with no IaC.

#### Config outside the pipeline
**What:** Runtime config edited in consoles; config repos without CI; "config-only" changes with a
fast lane that skips tests or canary.
**Why:** Config changes are a leading cause of outages and the least tested (P10; SRE ch. 8, 13, 17).
**Detect:** path filters that skip stages for config paths; config files without a pipeline. ✅.
**Severity:** High when a fast lane reaches prod; Medium otherwise.

#### No deploy-time config validation
**What:** No schema check, dependency connectivity check, or plausibility check on config before it
takes effect.
**Why:** Empty or truncated config takes production down (P10; SRE App. B).
**Detect:** deploy steps. ✅.
**Severity:** Medium.

#### Production data in lower environments
**What:** Jobs restoring production snapshots into CI/test/dev without masking.
**Why:** Privacy exposure and brittle, data-shaped tests (P21).
**Detect:** restore/dump commands. ✅.
**Severity:** High when unmasked personal data; Medium otherwise.

### Checklist (environments)
1. Is defined in version control and reproducible.
2. Matches production's stack (runtime, OS/base image, topology) at its scale.
3. Receives configuration at deploy/run time, not at build.
4. Receives config changes through the pipeline with the same safeguards as code.
5. Validates configuration before it takes effect.
6. Holds no unmasked production data (non-prod only).

---

## 6. infrastructure — delivering IaC

In scope: IaC roots delivered by a pipeline. N/A when the repo has none — say so. The IaC content
itself is the [terraform](../terraform/SKILL.md) skill's job.

### 🟢 Well done
- PRs run fmt/validate/lint/scan and post a plan per affected root × environment (P22).
- Apply runs from CI using the **saved plan** that was reviewed; production apply needs an approval of
  that plan (P22).
- Plan jobs use a read-only role; apply jobs a per-environment write role via OIDC (P18, P22).
- Environments are applied in order with the same code; a failure stops promotion (P22, P4).
- A destroy guard fails the run when a plan deletes or replaces more than expected (P22; SRE ch. 7).
- Drift detection runs on a schedule and alerts (P22; SRE ch. 17).
- Concurrency is controlled: one apply per root/environment at a time (`concurrency:` / resource group)
  in addition to state locking.

### 🔴 Not well done

#### Apply without saved plan
**What:** `terraform apply -auto-approve` that re-plans; apply on PR branches; apply before review.
**Why:** What runs isn't what was reviewed (P22).
**Detect:** apply commands. ✅.
**Severity:** High for production.

#### Plan not visible
**What:** No plan on PRs; plan only inside the apply job.
**Why:** Reviewers review code, not infrastructure change (P22).
**Detect:** triggers. ✅.
**Severity:** High for production roots.

#### One god role
**What:** The same credential plans and applies every environment; admin rights; static keys.
**Why:** A PR job can change production; one leak owns everything (P18).
**Detect:** role/secret usage per job. ✅.
**Severity:** High.

#### No serialization
**What:** Concurrent applies possible for the same root/environment.
**Why:** Lock contention at best, interleaved changes at worst.
**Detect:** absence of `concurrency`/resource-group/queue. ✅.
**Severity:** Medium.

#### No drift detection or destroy guard
**What:** No scheduled plan; no threshold on destroys/replacements.
**Why:** Hand changes accumulate; a bad input can delete everything (P22; SRE ch. 7 p. 85).
**Detect:** schedules; plan-JSON checks. ✅.
**Severity:** Medium.

### Checklist (infrastructure)
1. Runs static checks and posts a plan for review on PRs.
2. Applies the reviewed saved plan, from CI.
3. Separates plan (read) and apply (write) identities, per environment, federated.
4. Promotes through environments in order with the same code.
5. Serializes applies per root/environment.
6. Guards against unexpected destroys/replacements.
7. Detects drift on a schedule.
