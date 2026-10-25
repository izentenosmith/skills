---
name: pipelines
description: Review, design, or propose changes to CI/CD pipelines — GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, CircleCI, Bitbucket and similar — graded against Continuous Delivery, DevOps Handbook and SRE release-engineering theory. Covers flow (build once, promote, fail fast), feedback (test strategy, stop the line), release safety (same deploy everywhere, smoke checks, rollback, canary/blue-green, migrations), pipeline security and supply chain (secrets, OIDC, pinned actions, untrusted triggers, scanning, signing), environments and config, and infrastructure delivery (Terraform plan/apply). Review mode audits with evidence-backed findings and a repeatable 0–10 score; Design mode lays out a deployment pipeline; Propose mode sequences the migration without taking the path to production down. Use for pipeline review, "why is our CI slow/flaky/unsafe", designing a deployment pipeline, release strategies, or IaC delivery. It never triggers, approves or reconfigures a real CI system.
---

# 🚀 pipelines

A deployment pipeline is **the automated manifestation of the path from commit to production**. Its
job is to make releasing boring: every change gets the same build, the same tests and the same deploy,
fast enough that people keep changes small, and safe enough that a bad one is caught early, contained
when it isn't, and undone in minutes. This skill grades, designs and re-sequences pipelines against
that job.

## Where this fits

Two infrastructure skills, and they meet at the apply path:

- [terraform](../terraform/SKILL.md) — the infrastructure code, its state and what a change does to it
- **pipelines** (this skill) — the path every change takes to production, including the plan/apply
  pipeline for infrastructure code

Infrastructure code delivered by the pipeline is graded here in the **infrastructure** domain (how
plan and apply are run, gated and credentialed). What the Terraform itself contains belongs to
terraform.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding cites (P1–P22): Continuous Delivery, the
  Three Ways, release engineering, progressive delivery, pipeline security
- [review-rubric.md](review-rubric.md) — per domain: 🟢 well done, 🔴 anti-patterns (what, why,
  detect, severity), checklist criteria
- [detection-signals.md](detection-signals.md) — grep/regex per anti-pattern, with the platform
  translation table
- [design-patterns.md](design-patterns.md) — the reference pipeline, stage contracts, release
  strategies, branching, environments, IaC delivery, and the default for each trade-off
- [scoring.md](scoring.md) — severity, confidence, the 0–10 formula, the gate, templates
- [proposal.md](proposal.md) — decisions by band, sequencing that keeps the path to production up

---

## 📐 Pick the mode

| Mode | Input | Output |
|---|---|---|
| **Review** | Existing pipeline definitions (or a PR diff to them) | Findings, per-domain scores, the gate. Changes nothing. |
| **Design** | Requirements, or a review to correct | `pipeline-design.md`: stages and their contracts, promotion path, environments, release strategy, security model |
| **Propose** | A review and/or a design | `proposal.md`: decisions per domain and a sequenced migration |

Review tiers:

| Tier | When | Run |
|---|---|---|
| **PR review** | A diff to pipeline files | R1 for the touched pipelines, R3 on the changed jobs; findings without a score |
| **Domain review** | One concern ("is our CI secure?") | R1–R3 for that domain |
| **System review** | One repo's CI/CD | R1–R4 |
| **Estate review** | Several repos or a shared template library | R1–R4 per repo, then R5 |

Infer the **platform** from the files and say it: `.github/workflows/*.yml` → GitHub Actions;
`.gitlab-ci.yml` → GitLab CI; `azure-pipelines.yml` → Azure Pipelines; `Jenkinsfile` → Jenkins;
`.circleci/config.yml` → CircleCI; `bitbucket-pipelines.yml` → Bitbucket; plus deploy tooling
(Argo CD, Flux, Spinnaker, Helm, Terraform, Atlantis). Signals are written for GitHub Actions and
GitLab CI; [detection-signals.md](detection-signals.md) translates.

---

## 🔎 Review

The review **does not prescribe** — evidence, theory, a model of the value stream and a number.

Scope is **static evidence**: pipeline definitions, shared templates, build and deploy scripts they
call, Dockerfiles, IaC, `CODEOWNERS`, and any run history, settings export or delivery metrics the
user supplies. **Never trigger, re-run, cancel or approve a pipeline, and never read secret values**,
unless the user explicitly asks. Branch protection, environment protection, required reviewers and
runner configuration usually live in the CI system's settings, not the repo: those are 🔬 unless
supplied.

### R1 — Inventory and the value stream

- [ ] **Redact first.** Pipeline files and scripts carry tokens. Record the kind and location only;
  a committed credential is Critical on its own.
- [ ] **Pipelines**: every workflow/pipeline definition, its triggers (push, PR, tag, schedule,
  manual, `workflow_run`, fork PRs), and every shared template it includes.
- [ ] **The value stream**: draw commit → production as a chain of stages, with each stage's trigger,
  what it builds or runs, its gate, its manual steps, and its duration (measured if history is
  supplied, else 🔬). This is the review's spine — flow and release findings read it.
- [ ] **Artifacts**: where each deployable is built, where it is stored, how later stages reference it
  (by digest/version, or rebuilt).
- [ ] **Environments**: each target, how it's deployed, which credential, which gate.
- [ ] **Credentials**: every secret/variable/identity each job can reach, and which triggers can
  reach that job.
- [ ] **Counts per domain**, the source commit, and the output location (the repo's convention, else
  `analysis/pipelines/`; never this skill's folder).

### R2 — Run the static tools if available

`actionlint`, `zizmor` (GitHub Actions security), `gitlab-ci-lint`/`glab ci lint`, `checkov`
(CI frameworks), `shellcheck` on inline scripts. Their output is evidence, not the review — they see
syntax and some security patterns, not build-once, test strategy, or the release path. Record which
ran.

### R3 — Evaluate each domain

Domains, each a section of [review-rubric.md](review-rubric.md): **flow**, **feedback**,
**release**, **security**, **environments**, **infrastructure** (N/A without IaC — say so).

- [ ] **Triage if large** and **state coverage**. Shared templates are always deep-read.
- [ ] **Walk the 🔴 anti-patterns** against every in-scope object.
- [ ] **Every finding carries six things**: ID, object (`file / job`), anti-pattern, confidence
  (✅/⚠️/🔬), **theory violated** (P-N), severity, evidence (`file:line`).
- [ ] **Record the 🟢 too** — Propose needs to know what to keep.
- [ ] **Count per criterion.** The score is computed from counts.

### R4 — Score and summarize

Apply the formula, **show the arithmetic**, write `summary.md`: scores, the value stream, severity
and 🔬 tallies, what works, top findings, systemic issues, and **each gate condition separately**.
If delivery metrics were supplied (deployment frequency, lead time for changes, change failure rate,
time to restore), report them beside the score — they measure outcomes; the score measures the
mechanism.

### R5 — Estate synthesis

Across repos: estate score; severity heatmap (repo × domain); **shared templates and every repo that
inherits each one** — a defect in a template is a defect everywhere it's included, so Propose fixes
templates first; cross-repo triggers and artifact dependencies; themes, each tied to its theory.

---

## 📝 Design

Design the **path to production** — stages, contracts, promotion, environments, release strategy,
security model — before writing YAML. Read [theory.md](theory.md) and
[design-patterns.md](design-patterns.md) first.

| Tier | Input | Output |
|---|---|---|
| **New pipeline** | Requirements: what ships, where, how often, who approves, compliance | `pipeline-design.md` |
| **Redesign** | A review | `pipeline-design.md` with each material change traced to a finding ID or a requirement |
| **Design review** | A proposed pipeline design or YAML | Findings against the rubric's checklists |

Method:

1. **Requirements, assumptions, open questions.** Deployables, targets, branching model, release
   cadence wanted, availability objectives (SLOs, error budget if any), compliance (separation of
   duties, audit evidence), the CI platform and runners available.
2. **The stage chain.** Start from the reference pipeline in [design-patterns.md](design-patterns.md)
   §1 and justify every deviation. For each stage: its trigger, its **contract** (what it proves and
   what it hands on), its time budget, its gate. The commit stage fits in ~10 minutes.
3. **Build once, promote.** Where the artifact is built, how it's versioned and stored, and how every
   later stage pulls the same one by digest. Config comes from the environment, never the build.
4. **Test placement.** Which tests run where (the pyramid), how flaky tests are handled, what blocks
   and what informs.
5. **Environments.** The matrix: environment × deploy mechanism × config source × credential × gate ×
   data. Production-like where it matters; ephemeral where it's cheap.
6. **Release strategy.** Deploy vs release; rolling / blue-green / canary / feature flags — chosen per
   service with the reason; the post-deploy checks and the automated rollback trigger; migrations with
   expand/contract.
7. **Security model.** Trigger trust levels; which jobs hold which credentials; OIDC federation;
   least-privilege tokens; pinning of third-party actions/images; scanning; provenance and signing;
   protected environments and who may approve.
8. **Infrastructure delivery** (when IaC exists): plan on PR, saved plan, apply on merge, per-env
   promotion, drift detection — pattern in [design-patterns.md](design-patterns.md) §6, the code
   itself handed to [terraform](../terraform/SKILL.md).
9. **Observability of the pipeline**: deploy markers, notifications, and how the four delivery
   metrics will be measured.
10. **Validation checklist**: built once; same deploy everywhere; every prod deploy has a smoke check
    and a rollback; no untrusted trigger reaches a credential; every third-party reference pinned;
    commit stage in budget; every material change traced; open questions listed.

`pipeline-design.md` contains: scope and assumptions · the stage diagram (Mermaid is fine) · stage
contracts · artifact and promotion model · test placement · environment matrix · release strategy and
rollback · security model · infrastructure delivery · pipeline observability · traceability ·
validation checklist · open questions. Write YAML only as a skeleton for the stage chain on the named
platform — the build is a separate task.

---

## 📦 Propose

Follow [proposal.md](proposal.md). The rule that dominates it: **the path to production never goes
down** — containment first, then the commit stage, then build-once, then release safety, then supply
chain, then cleanup; rebuilds run alongside the old pipeline until they've shipped on their own.

---

## 🛑 Stopping rule

**Review** stops when: the value stream covers every pipeline that ships something; every in-scope
domain has an evaluation with coverage stated; every finding has its six fields; every score shows
`p`, base and cap; every 🔬 flag is listed; the gate is stated condition by condition.

**Design** stops when the validation checklist passes and every open question names the decision it
blocks.

**Propose** stops when every Critical/High has a decision and every step has a validation and a
rollback.

Then stop. There is always another minute to shave and another scanner to add. **A change that
doesn't shorten feedback, reduce the chance or cost of a bad release, or close a path to a credential
by an amount someone would notice is a diff for its own sake.**

---

## Subagents — optional

Worth it for an **estate** or a large template library: delegate R1–R3 per repo (read-only),
each returning its value stream, credential map, signal counts and six-field findings, with "could
not determine" per field. **Keep scoring, the gate and the synthesis in the main thread.** In Design
and Propose, delegate only evidence gathering — the stage chain and the sequence are one design.

**Dispatch contract.** Give each delegate the prior (mode, tier), the target (which repos or files it
owns, and that the rest are covered), the context it cannot infer (which environments are production,
which settings were supplied), the return shape, and "report conclusions, not file excerpts".
Delegates never trigger runs or read secret values.

---

## Rules of Engagement

1. **The pipeline is production infrastructure.** It holds the keys to production; review it with the
   same rigour as the service.
2. **Never act on a real CI system.** No triggering, re-running, approving or settings changes unless
   explicitly asked.
3. **Never echo a secret.** Record the kind and location; recommend rotation, not just deletion.
4. **Every finding cites a principle.** P-N from [theory.md](theory.md), or it's taste.
5. **Measure what you can, flag what you can't.** Durations and failure rates come from history, not
   from reading YAML.
6. **Review doesn't prescribe; design doesn't apply.** Each mode stops at its own deliverable.

## Handoff

> Reviewed `<repo>` CI (`<platform>`) at `<commit>`: score `<x>` (`<band>`), gate `<pass/fail —
> failing conditions>`. `<n>` Critical, `<n>` High. Value stream in
> `analysis/pipelines/summary.md`. Next: **Design** to correct `<domains>`, then **Propose** for the
> sequence; Terraform code findings go to **[terraform](../terraform/SKILL.md)**.
