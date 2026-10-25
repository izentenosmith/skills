---
name: terraform
description: Review, design, or propose changes to Terraform/OpenTofu infrastructure code — module and repo structure, state and backends, version pinning, security, change safety (resource identity, destructive changes, drift) and the path from commit to apply — graded against Infrastructure-as-Code theory, a scored rubric and the AWS provider best practices. Review mode audits an existing codebase with evidence-backed findings and a repeatable 0–10 score; Design mode lays out a new codebase or a redesign (layout, state map, module graph, environments); Propose mode turns a review and design into a sequenced, no-recreate migration plan. Use for Terraform code review, IaC audits, state splitting, module design, landing-zone layout, provider upgrades, or "is our Terraform any good". It never runs apply, import or state commands against a real backend.
---

# 🏗️ terraform

Terraform is a tool for keeping a **written description** of infrastructure and the **real thing**
in agreement, through a **state file** that maps one to the other. Almost every Terraform failure is a
failure of one of those three — the code doesn't say what's true, the state doesn't map what's real,
or the path between them lets an unreviewed change through. This skill grades, designs and
re-sequences codebases against that model.

## Where this fits

Two infrastructure skills, and they meet at the apply path:

- **terraform** (this skill) — the code, its state, its modules, and what a change does to real
  infrastructure
- [pipelines](../pipelines/SKILL.md) — the CI/CD that carries a change from commit to production,
  including the plan/apply pipeline for this code

Where a finding is about *how* the plan reaches apply (who runs it, which credentials, which gate),
this skill records it in the **delivery** domain and hands the redesign to pipelines.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding cites (T1–T22): IaC, desired state, the
  state file, blast radius, resource identity, plan as contract, pinning, least privilege, testing
- [review-rubric.md](review-rubric.md) — per domain: 🟢 well done, 🔴 anti-patterns (what, why, detect,
  severity), checklist criteria
- [detection-signals.md](detection-signals.md) — grep/regex per anti-pattern, with its confidence tag
- [design-patterns.md](design-patterns.md) — repo layouts, state partitioning, module design,
  environment patterns, the AWS provider specifics, and the default for each trade-off
- [scoring.md](scoring.md) — severity, confidence, the 0–10 formula, the gate, templates
- [proposal.md](proposal.md) — decisions by band, the no-recreate refactoring rule, sequencing

---

## 📐 Pick the mode

Say which one up front, and the tier within it.

| Mode | Input | Output |
|---|---|---|
| **Review** | An existing codebase (or a PR diff) | Findings, per-domain scores, the gate. Changes nothing. |
| **Design** | Requirements, or a review to correct | `design.md`: layout, state map, module graph, environment and promotion model, guardrails |
| **Propose** | A review and/or a design | `proposal.md`: decisions per domain and a sequenced migration where no resource is recreated by accident |

Review tiers:

| Tier | When | Run |
|---|---|---|
| **PR review** | A diff, not a codebase | Step R1 for the touched roots, then Step R3 against the changed lines only; findings without a score |
| **Domain review** | One concern ("is our state set up right?") | Steps R1–R3 for that domain |
| **Codebase review** | One repo or one directory | Steps R1–R4 |
| **Estate review** | Several repos | R1–R4 per codebase, then R5 |

Infer the **tooling** from the code and say it: Terraform or OpenTofu and the version
(`required_version`, `.terraform-version`, `.tool-versions`), providers, backend type, wrapper
(Terragrunt, Terramate, Atlantis, Spacelift, TFC/TFE), CI platform. The signals are written for
Terraform + AWS; [detection-signals.md](detection-signals.md) notes the azurerm/google equivalents.

---

## 🔎 Review

The review **does not prescribe**. It produces evidence, theory, a model of the codebase and a
number. A review that also prescribes has an incentive to shape findings toward the prescription; the
fix belongs to Design and Propose.

Scope is **static evidence**: `.tf`, `.tfvars`, lockfiles, wrapper configs, CI definitions, and any
plan JSON or state listing the user supplies. **Never run `plan`, `apply`, `import`, `state` or
`refresh` against a real backend** unless the user explicitly asks; `fmt -check`,
`init -backend=false` and `validate` are safe. Anything that needs the cloud account is a 🔬 flag.

### R1 — Inventory

- [ ] **Redact first.** `.tfvars`, `*.auto.tfvars`, provider blocks and CI files carry credentials.
  Never copy a secret value into an output — record the *kind* and the location
  (`envs/prod/terraform.tfvars:3, AWS secret key`). A committed secret is a Critical finding on its own.
- [ ] **Roots**: every directory where `terraform init` is meant to run (has a `backend` block, a
  wrapper config, or is referenced by CI). **Child modules**: every directory called by a `module`
  block. Local vs registry vs git sources.
- [ ] **The state map**: root × environment → backend type, key/path, locking, encryption, who applies
  (human, CI job). This table is the review's spine; state findings and the gate read it.
- [ ] **The module graph**: caller → module @ version. Depth, fan-in, and unpinned edges.
- [ ] **Counts per domain** — they weight the score ([scoring.md](scoring.md)).
- [ ] **Source version**: the commit every finding cites. **Output location**: the repo's convention,
  else `analysis/terraform/`. Never write inside this skill's folder.

### R2 — Run the static tools if they're available

`terraform fmt -check -recursive`, `terraform init -backend=false && terraform validate` per root,
and whichever of `tflint`, `checkov`, `trivy config`/`tfsec`, `terrascan` are installed. **Their output
is evidence, not the review** — a scanner flags resources, it doesn't see state layout, blast radius,
identity or the apply path. Record which tools ran and which didn't.

### R3 — Evaluate each domain

One domain, one section of [review-rubric.md](review-rubric.md): **structure**, **state**,
**dependencies**, **security**, **change-safety**, **delivery**.

- [ ] **Triage if large** ([scoring.md](scoring.md)) and **state coverage**.
- [ ] **Walk the domain's 🔴 anti-patterns** against every in-scope object, using
  [detection-signals.md](detection-signals.md) to find candidates and reading each in context.
- [ ] **Every finding carries six things**: ID, object, anti-pattern, **confidence** (✅/⚠️/🔬),
  **the theory it violates** (T-N), **severity**, and **evidence** as `file:line`. A finding missing
  any of them is incomplete.
- [ ] **Record the 🟢 too.** "What is working well" is part of the output, not a courtesy — it tells
  Propose what to keep.
- [ ] **Count per criterion** how many in-scope objects satisfy it. The score is computed from counts.

### R4 — Score and summarize

Apply the formula: `p` per criterion, base, caps, confidence rule. **Show the arithmetic** — two
reviewers with the same findings land on the same number. Write `summary.md` from the template:
scores, severity tally, 🔬 tally, the state map, the module graph, what works, top findings, systemic
issues, and **each gate condition separately**.

### R5 — Estate synthesis

Across codebases: capped and uncapped estate score; a severity heatmap (codebase × domain); the
**cross-state dependency list** (which root reads which root's outputs, via `terraform_remote_state`,
data sources or parameters) — Propose sequences from it; shared modules and the versions each
codebase pins; themes, each tied to its theory.

---

## 📝 Design

Design the **shape** — layout, state boundaries, module interfaces, environment model, guardrails —
before writing HCL. Read [theory.md](theory.md) and [design-patterns.md](design-patterns.md) first.

| Tier | Input | Output |
|---|---|---|
| **New codebase** | Requirements: clouds/accounts, environments, teams, components, compliance | `design.md` |
| **Redesign** | A review | `design.md` where every material change traces to a finding ID or a stated requirement |
| **Design review** | An existing design doc or proposed layout | Findings against the rubric's checklists; rewrite only when asked |

Method:

1. **Requirements, assumptions, open questions.** Accounts/subscriptions/projects, regions,
   environments, the teams that own what, change frequency per component, compliance boundaries.
   Never silently promote an assumption into a constraint.
2. **Components and lifecycles.** Group resources by *how often they change together and who changes
   them* (network/identity foundations, shared platform, per-service). Different lifecycles → different
   states (T7).
3. **The state map.** One row per root × environment: backend, key, lock, encryption, the role that
   applies it, the roots it reads from. Size each for blast radius; say what a bad apply in it can
   take down.
4. **Environment model.** How environments differ (only by input values — T21), how a change is
   promoted between them, and why the chosen pattern beats the alternatives
   ([design-patterns.md](design-patterns.md) §3).
5. **Module graph and interfaces.** Which modules exist, what each takes and returns, where they live
   and how they're versioned. Prefer few deep modules over many thin wrappers (T9, T10).
6. **Cross-state interfaces.** How one root consumes another's outputs, and what may not change
   without a coordinated release.
7. **Guardrails.** Pinning policy, tagging, IAM for the pipeline per environment, policy-as-code,
   destructive-change protection, drift detection.
8. **The apply path** in outline (plan on PR, saved plan, approval, apply from CI) — and hand its
   detailed design to [pipelines](../pipelines/SKILL.md).
9. **Validation checklist**: no shared state across prod/non-prod; every root has a lock; every
   stateful resource protected; every version pinned; no secret in code or plain outputs; every
   material change traced; open questions listed.

`design.md` contains: scope and assumptions · components and lifecycles · directory tree · state map ·
environment and promotion model · module graph with interfaces · cross-state interfaces · guardrails ·
apply path outline · traceability (redesign) · validation checklist · open questions. Write example
HCL only for the interfaces (a module's `variables.tf`/`outputs.tf` skeleton, a backend block) — the
build is a separate task.

---

## 📦 Propose

Follow [proposal.md](proposal.md). The rule that dominates it: **a refactor is correct only when its
plan shows nothing destroyed and nothing re-created** — use `moved`, `import` and `removed` blocks,
committed and reviewed, never ad-hoc `state` surgery. Sequence: containment → foundations (state,
pinning, CI) → apply path → structural refactors in dependency order → hardening → cleanup.

---

## 🛑 Stopping rule

**Review** stops when: the state map and module graph cover every root and module; every in-scope
domain has an evaluation with coverage stated; every finding has its six fields; every score shows
`p`, base and cap; every 🔬 flag is listed by name; the gate is stated condition by condition.

**Design** stops when the validation checklist passes and every open question is listed with the
decision it blocks.

**Propose** stops when every Critical/High has a decision, every step has its expected plan and
rollback, and the order respects the cross-state dependency list.

Then stop. There is always another module to extract and another variable to describe. **A change
that doesn't shrink blast radius, remove a failure mode, or make the next change cheaper by an amount
someone would notice is a diff for its own sake.**

---

## Subagents — optional

Worth it for an **estate** or a large monorepo. In Review, delegate R1–R3 per codebase (or per group
of roots): read-only, each returning its slice of the state map, module graph, signal counts and
findings in the six-field shape — with "could not determine" per field, so a silent delegate is
distinguishable from a clean read. **Keep scoring, the gate and the synthesis in the main thread.** In
Design and Propose, delegate only inventory and evidence gathering; the state boundaries and the
sequence are one set of decisions and must stay in one head.

**Dispatch contract.** Give each delegate the prior (mode, tier), the target (which directories it
owns, and that the rest are covered), the context it cannot infer (environments, accounts, which
roots are production), the return shape above, and "report conclusions, not file excerpts". Delegates
stay read-only and never touch a backend.

---

## Rules of Engagement

1. **State is part of the system.** Review the state layout as carefully as the code; most outages
   from Terraform come from where state is, what's in one, and who can write it.
2. **Never touch a real backend.** No `plan`/`apply`/`import`/`state`/`refresh` against real state
   unless the user explicitly asks. Plans the user supplies are evidence.
3. **Never echo a secret.** Record the kind and location; recommend rotation, not just deletion.
4. **Every finding cites a principle.** T-N from [theory.md](theory.md), or it's taste.
5. **Refactors don't recreate.** Any proposed move ships with `moved`/`import`/`removed` and an
   expected plan of zero adds and zero destroys.
6. **Review doesn't prescribe; design doesn't apply.** Each mode stops at its own deliverable.

## Handoff

> Reviewed `<codebase>` at `<commit>`: score `<x>` (`<band>`), gate `<pass/fail — failing conditions>`.
> `<n>` Critical, `<n>` High. State map and module graph in `analysis/terraform/summary.md`.
> Next: **Design** to correct `<domains>`, then **Propose** for the sequence; the apply path goes to
> **[pipelines](../pipelines/SKILL.md)**.
