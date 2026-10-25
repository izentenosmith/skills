# Theory — The Principles Every Pipeline Finding Cites (P1–P22)

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** for a pipeline, and **what violating it looks like** in a pipeline definition. Sources:
>
> | Short name | Source |
> |---|---|
> | **CD** | Humble & Farley, *Continuous Delivery* (2010) |
> | **DOH** | Kim, Humble, Debois & Willis, *The DevOps Handbook* (2016) |
> | **SRE** | Beyer, Jones, Petoff & Murphy (eds.), *Site Reliability Engineering* (2016) |
> | **IaC** | Kief Morris, *Infrastructure as Code* (2016), ch. 1–2 |
> | **AWS-PG** | AWS Prescriptive Guidance, *Best practices for using the Terraform AWS Provider* (2025) |
>
> CD and SRE cite printed pages; DOH cites chapters (the edition used has no stable page numbers).
> The books predate GitHub Actions, OIDC federation and SLSA; where a principle is old and the
> mechanism is new, the principle comes from the book and the mechanism is named as current practice.

---

## Part A — The pipeline as a system

### P1 — A repeatable, reliable, automated process
**Says:** Releasing should be pressing a button, because every step has been rehearsed hundreds of
times; automate almost everything — only exploratory testing, demos and sign-offs need humans
(CD pp. 24–25). Release engineering exists so releases are repeatable, not unique (SRE ch. 8 p. 87).
Manual, repetitive release work is toil: it scales with the service and leaves nothing behind
(SRE ch. 5).
**Violation:** the pipeline stops at "upload artifact" and a runbook takes over; manual promotion
between stages; hand-run deploy scripts; manual version bumps and tagging; approval clicks that
never reject anything.

### P2 — Everything in version control, including the pipeline
**Says:** Code, tests, build and deploy scripts, environment and network config, database scripts and
the toolchain are versioned, tied together by one identifier (CD p. 26; DOH ch. 9). The pipeline's
own definition is code: refactored, reviewed and kept with the application (CD pp. 137, 152; DOH
ch. 10). Build and deploy logic lives in versioned scripts that CI *and* developers run — one entry
point per stage — not only inside the CI tool (CD ch. 6).
**Violation:** pipelines configured in a UI; large inline shell blocks in YAML with no local
equivalent; CI runners hand-built with tools nobody can list.

### P3 — Build once, promote the same artifact
**Says:** Build binaries once, in the commit stage; every later stage deploys that same artifact from
an artifact repository, verified by hash (CD pp. 113–114; DOH ch. 10). Artifacts are not
environment-specific — configuration is injected at deploy or run time, never at build time
(CD pp. 41–42, 114–115). Promote binaries, not source: rebuilding from a release branch ships
something untested (CD pp. 402–403). Every artifact is traceable to its revision and build
(SRE ch. 8 p. 90).
**Violation:** `docker build`/`npm run build` inside deploy jobs; `build:prod` scripts or
`--build-arg ENV=prod`; one image per environment; images tagged `latest` or by branch; production
built from a tag that recompiles.

### P4 — Deploy the same way to every environment
**Says:** One deployment mechanism, parameterized by environment configuration, for every target;
production then becomes the most rehearsed path, not the least (CD pp. 115–117; DOH ch. 12; the CSG
case rehearsed prod ~100 times in lower environments). The deployment system is the only way to
change any environment (CD p. 249).
**Violation:** `deploy-staging.sh` and `deploy-prod.sh` that differ; prod jobs with extra inline
steps; a different tool for production.

### P5 — Fast feedback, fail fast
**Says:** Every change triggers feedback, as soon as possible, and the team acts on it (CD pp. 12–16).
The commit stage takes under ~10 minutes, ideally under 5 (CD pp. 61, 120, 185; DOH ch. 10). Put
the checks most likely to fail first; abort a long suite at once if the environment check fails
(CD p. 217); otherwise run everything and report all failures (CD ch. 6). Trigger on every commit,
not on a schedule (CD p. 118; DOH ch. 10).
**Violation:** e2e/UI/DB-container suites in the first gating job; nightly-only acceptance; serial
jobs that could run in parallel; no dependency cache.

### P6 — Stop the line
**Says:** A broken build or pipeline is the team's top priority; no new work lands on red; fix within
~10 minutes or revert (CD pp. 66–70, 119–120; DOH ch. 10, the Andon cord; SRE ch. 17 p. 191).
Failing tests are fixed or deleted, never silenced; flaky tests are rewritten or removed because they
teach people to ignore red (CD p. 70; DOH ch. 10; SRE ch. 17 pp. 197–198).
**Violation:** `continue-on-error: true` / `allow_failure: true` / `|| true` on test jobs; blanket
retries; growing skip lists; merges allowed while main is red.

### P7 — Small batches on trunk
**Says:** Small changes are easier to test, attribute and reverse (DOH ch. 2; SRE ch. 9 pp. 100–101;
IaC pp. 24–25). CI means merging *to* mainline at least daily; long-lived feature branches are not CI
(CD pp. 59, 390–391, 410–412; DOH ch. 11). Keep trunk releasable with feature hiding and branch by
abstraction (CD ch. 13). Release branches, if any, are cut from trunk, take fixes only, and merge
back (CD pp. 408–409; SRE ch. 8 p. 90).
**Violation:** CI configured mainly for `develop`/`feature/*`; persistent per-branch environments;
release trains; code freezes.

### P8 — The pipeline's stages and the test pyramid
**Says:** Commit stage (compile, unit tests, static analysis, package) → automated acceptance in a
production-like environment → manual/exploratory on demand → capacity/non-functional → release
(CD pp. 110–112). Most defects are caught by fast unit tests; an inverted pyramid is an anti-pattern;
every escaped bug earns a test at the lowest level that would have caught it (DOH ch. 10). Acceptance
is a binary gate — later stages may only consume candidates that passed it (CD pp. 124, 213).
**Violation:** prod deploy with no `needs:` on the test stages; most test time in UI tests; no
regression test added after incidents.

### P15 — Self-service, owned by the people who ship
**Says:** Teams own and run their own releases on shared tooling; releases run automatically and
humans step in only on failure (SRE ch. 8 p. 88). The pipeline is a pull system: anyone authorized
can deploy any passing build to an environment they need, without a ticket (CD pp. 17, 106;
DOH ch. 12). Automation maintained by people who don't use it rots (SRE ch. 7 pp. 79–80). Shared
standards ship as reusable templates, owned and versioned, not as documents (DOH ch. 20).
**Violation:** deploys only one person can run; a central team hand-editing every repo's pipeline;
copy-pasted pipeline YAML across repos instead of a versioned template; standards that exist only in
a wiki.

## Part B — Environments and configuration

### P9 — Production-like, reproducible environments
**Says:** Deploy into copies of production — same OS, stack, topology, scaled down (CD pp. 117–118,
254). Environments are created on demand from version control; creating one is cheaper than repairing
one (CD p. 50; DOH ch. 9). Use the same deployment, monitoring and logging tools before and after
production (DOH ch. 9). CI runners are environments too, and are provisioned the same way (CD p. 76;
DOH ch. 22).
**Violation:** staging on a different runtime or base image than prod; hand-provisioned test
environments; environments requested by ticket.

### P10 — Configuration is separate from the artifact, and tested
**Says:** Keep option names with the code and values elsewhere, keyed by application × version ×
environment; apply configuration only by automation; validate it at deploy time — connect to every
dependency and fail if any is missing (CD pp. 43–48). Configuration is as risky as code and usually
less tested; config that changes often must be treated as a release and canaried like one
(CD p. 40; SRE ch. 17 p. 200; SRE ch. 13 — a config change skipped canary and crash-looped the
fleet). Implausible config (empty, truncated, N% smaller) must not take effect (SRE App. B).
**Violation:** config baked into images; config pushed outside the pipeline; a fast lane that lets
"config-only" changes skip the canary.

### P21 — Database changes are versioned, additive and decoupled
**Says:** Migrations are versioned scripts applied by the deploy, the same scripts in every
environment (CD p. 326). Prefer additive changes; ship an app version compatible with old and new
schemas, then migrate, then contract later — expand/contract (CD pp. 329–334; DOH ch. 12).
Rehearse upgrade and rollback on every deploy (CD p. 419). Back up before destructive changes, and
prove the restore works (SRE ch. 26).
**Violation:** no migration step in the deploy; drops/renames shipped in the same release as the
code that stops using them; SQL handed to a DBA; production dumps as test data (CD pp. 343–344).

## Part C — Release safety

### P11 — Deploy is not release
**Says:** Deployment installs a version; release exposes features to users. Decouple them — feature
toggles, dark launches — so deploys happen in business hours and release is a product decision
(DOH ch. 12; CD pp. 347–349). Acceptance tests run with toggles on; the toggle mechanism is tested;
dead flags are deleted (DOH ch. 12; SRE ch. 9 — permanently-off flags are time bombs).
**Violation:** deploys scheduled at night for launch dates; no flag mechanism; flags at 0% or 100%
for months.

### P12 — Progressive delivery, gated by health and budget
**Says:** About 70% of outages come from changes; roll out progressively, detect problems fast, and
roll back safely — all automated (SRE ch. 1 p. 10). Canary: a small slice first, bake, then grow —
e.g. 0.1% → 1% → 10% → 100%, changing region as you go (SRE ch. 17 p. 189; ch. 27). Promotion is
gated by user-facing metrics, with automatic rollback when they leave range — the *cluster immune
system* (DOH ch. 12). Releases spend the error budget; when it's exhausted, only fixes ship
(SRE ch. 3 pp. 34–35). No change class skips the canary because it "looks low-risk" (SRE ch. 13).
Budget push capacity: never restart everything at once (SRE ch. 22).
**Violation:** one deploy job to all regions; canary steps with no metric check; `maxUnavailable:
100%`; no budget/SLO input to promotion.

### P13 — Every deploy is verified and reversible
**Says:** Smoke-test every deployment — the app is up and its dependencies are reachable — and fail
the deploy otherwise (CD p. 117; DOH ch. 12). Watch the deploy in production; deployments emit
markers on dashboards (DOH ch. 14, 16; SRE ch. 12). Roll back first, diagnose afterwards
(SRE App. B). Rollback is the same mechanism as deploy — redeploy the previous artifact, or flip
blue/green — not a separate script, and it is rehearsed (CD pp. 131–132, 259–260; SRE ch. 13 p. 153).
Recovery order: toggle off → roll back or fix forward through the normal pipeline (DOH ch. 16).
Emergency fixes go through the same pipeline (CD pp. 265–266).
**Violation:** deploy job ends at `kubectl apply`/`helm upgrade` with no check; no rollback job; a
hand-written `rollback.sh`; a `hotfix` workflow with `skip_tests`.

### P16 — Peer review and automated controls over distant approval
**Says:** External change approval (CABs, distant approvers) correlates with *worse* stability and
throughput; peer review before trunk, small changes and automated tests are the effective controls
(DOH ch. 18). Changes that go through a pipeline with a good track record can be standard changes,
pre-approved and recorded automatically (DOH ch. 23). Where separation of duties is mandated, the
pipeline enforces it: the author can't approve their own production deploy, and the pipeline keeps
the audit trail (CD pp. 436–441; DOH ch. 23). A gate that never rejects is toil (SRE ch. 5).
**Violation:** a manual approval on every environment; approvers outside the team; production deploy
needing a meeting; no review requirement on the pipeline files themselves.

## Part D — Security and supply chain

### P14 — Hermetic, reproducible builds
**Says:** The same revision built anywhere gives the same output; builds don't depend on what's on the
host and don't reach the network for unpinned inputs; toolchains are versioned with the code (SRE
ch. 8 p. 89; CD p. 38). Dependencies come from a pinned lockfile through an organizational mirror
(CD ch. 13).
**Violation:** `:latest` base images; no lockfile; `curl | sh` installers; tools fetched as latest at
build time; actions/templates referenced by branch.

### P17 — Security in every commit (shift left)
**Says:** Static analysis, dependency scanning and secret scanning run on every commit, findings go to
the team's own tracker, and the build gives the author exact fix information (DOH ch. 22). Dynamic
scans run against deployed test environments. IaC is linted and policy-checked like code (DOH ch. 10,
22; AWS-PG p. 13). Prefer pre-approved, shared components (auth, crypto, base images, pipeline
templates) so teams inherit controls (DOH ch. 20, 22).
**Violation:** no SAST/SCA/secret scan; scanners that never fail the build; security review as a
pre-release phase.

### P18 — Protect the pipeline itself
**Says:** The pipeline holds the keys to production, so it is an attack path: harden and rebuild
runners from code, isolate each job, give CI read-only VCS credentials, review test code (a favored
hiding place for malicious code) and protect pipeline configuration like production
(DOH ch. 22). Credentials are least-privilege, short-lived and scoped per environment — OIDC
federation rather than static keys (AWS-PG pp. 8–10; SRE ch. 7 p. 80). Untrusted input (fork PRs,
issue titles, branch names) never runs with secrets in scope; third-party actions and images are
pinned to an immutable digest/SHA.
**Violation:** `pull_request_target` that checks out the PR head; `${{ github.event.* }}` interpolated
into `run:`; `permissions: write-all`; static cloud keys in CI variables; shared persistent runners for
public repos; `uses: org/action@v3` in a job holding deploy credentials.

### P19 — Integrity and provenance
**Says:** Sign commits and artifacts, log hashes centrally, and verify them at each stage (DOH ch. 22;
CD p. 438). Packages carry a name, a hash and a signature, and promotion moves a label, not bytes
(SRE ch. 8 p. 91). Current practice: build provenance attestations and SBOMs (SLSA), verified at
deploy time.
**Violation:** unsigned images; deploys by mutable tag instead of digest; no SBOM or provenance for
released artifacts.

## Part E — Measurement and infrastructure

### P20 — Instrument the pipeline and the deploy
**Says:** Record the start and end of every stage; cycle time — commit to production — is the primary
metric (CD pp. 137–139). Track deployment frequency, lead time for changes, change failure rate and
time to restore, and read throughput and stability together: high performers are faster *and* more
stable (DOH Intro, ch. 18). Emit deploy events to monitoring; alert when build time doubles
(DOH ch. 14). Page only on symptoms; deploy noise goes to dashboards, not pagers (SRE ch. 6).
**Violation:** no deploy markers; no record of which version is where; durations only visible by
clicking through runs.

### P22 — Infrastructure goes through a pipeline too
**Says:** Infrastructure changes are tested and promoted like code: same definition through each
environment, from a central agent, never laptops (IaC pp. 35, 54–55; CD ch. 11; DOH ch. 9). For
Terraform: plan on PR, the reviewed **saved** plan is what gets applied, per-environment roles, prod
gated, drift detected on a schedule (AWS-PG pp. 12, 18–19; SRE ch. 17 p. 188 — configuration tests
compare running state to the checked-in state). Infrastructure changes trigger the tests of the
applications that run on them (CD p. 285). Guard against "zero means all": fail when a plan destroys
more than expected (SRE ch. 7 p. 85).
**Violation:** `terraform apply -auto-approve` without a saved plan; one CI role with admin on every
account; no plan visible on the PR; no drift job.

---

## Theory → domain index

| Domain | Principles |
|---|---|
| flow | P1, P2, P3, P5, P7, P15, P14 (build side) |
| feedback | P5, P6, P8 |
| release | P4, P11, P12, P13, P16, P21 |
| security | P14, P17, P18, P19 |
| environments | P9, P10 |
| infrastructure | P22, P12, P13 |
| (all) | P20 — measured where history is available |
