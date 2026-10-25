# infrastructure

Two skills for the code that builds infrastructure and the pipelines that carry every change to
production. Each one works in three modes — **Review**, **Design**, **Propose** — so one skill
covers the whole loop for its subject instead of splitting it across five.

```
            Review ───────────► Design ───────────► Propose
         (findings, score,   (target layout /     (decision register,
          the gate)           target pipeline)     sequenced migration)

terraform   code · state · modules · versions · security · change safety · apply path
pipelines   flow · feedback · release · security & supply chain · environments · IaC delivery
                                   ▲
                    they meet at the apply path: terraform grades *whether*
                    a root has a safe path to apply; pipelines designs it
```

| Skill | What it does |
|---|---|
| [terraform](terraform/SKILL.md) | Reviews Terraform/OpenTofu codebases across six domains — structure, state, dependencies, security, change-safety, delivery — recovering a **state map** and **module graph** and producing evidence-backed findings and a repeatable 0–10 score with a gate. Designs layouts, state boundaries, module interfaces and environment models. Proposes migrations where **no resource is recreated by accident** (`moved`/`import`/`removed`, expected plan of zero adds and destroys). Never runs `apply`, `import` or `state` against a real backend. |
| [pipelines](pipelines/SKILL.md) | Reviews CI/CD (GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, CircleCI…) across six domains — flow, feedback, release, security, environments, infrastructure — recovering the **value stream** from commit to production and producing findings, a score and a gate. Designs the deployment pipeline: stage contracts, build-once promotion, test placement, release strategy, security model, IaC delivery. Proposes changes in an order that **never takes the path to production down**. Never triggers, approves or reconfigures a real CI system. |

## Install

Both, from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill terraform pipelines
```

Or one at a time:

| Skill | Install |
|---|---|
| terraform | `npx skills add izentenosmith/skills --skill terraform` |
| pipelines | `npx skills add izentenosmith/skills --skill pipelines` |

Flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx). Or copy the
folder — each is self-contained (`SKILL.md` plus its reference docs, no symlinks).

Invoke by name, or let the description trigger it:

```
/terraform   review this repo's Terraform
/terraform   design the layout for three accounts and two services
/pipelines   review .github/workflows
/pipelines   propose a migration from the review in analysis/pipelines/
```

## The theory underneath

Both skills grade against principles with IDs, and **every finding cites one** — a defect without
its principle is taste.

| Source | What it contributes |
|---|---|
| Humble & Farley, *Continuous Delivery* | The deployment pipeline: build once, deploy the same way everywhere, commit stage ≤ 10 min, stop the line, smoke tests, rollback, expand/contract migrations, trunk-based development |
| Kim, Humble, Debois & Willis, *The DevOps Handbook* | The Three Ways; on-demand environments; the test pyramid and the Andon cord; deploy vs. release, blue-green, canary, cluster immune system; why distant change approval fails; security and the pipeline as an attack path |
| Beyer et al., *Site Reliability Engineering* | ~70% of outages come from change; progressive rollout, fast detection, safe rollback; error budgets as the release gate; hermetic builds; config as a release; "sometimes zero means all"; restores, not backups |
| Kief Morris, *Infrastructure as Code* (ch. 1–2) | Reproducible, disposable, consistent systems; drift and the automation fear spiral; stacks sized by scope of change; re-usable vs. per-environment definitions; applying from a central agent |
| Turnbull, *The Terraform Book* (ch. 3) | Modules as interfaces, variables/outputs, provider inheritance, `count`, plan/apply |
| AWS Prescriptive Guidance, *Terraform AWS Provider best practices* | Remote state with S3 native locking, per-environment backends, least-privilege roles and OIDC, repo layout, pinning, `default_tags`, scanning, policy as code |

[terraform/theory.md](terraform/theory.md) holds T1–T22; [pipelines/theory.md](pipelines/theory.md)
holds P1–P22. Where a Terraform or CI feature postdates the books (`moved` blocks, OIDC federation,
SLSA provenance), the principle comes from the book and the mechanism is named as current practice.

## How the modes stay honest

- **Review doesn't prescribe.** It produces evidence, theory, a model (state map / value stream) and a
  number. A review that also prescribes has an incentive to shape findings toward the prescription.
- **Confidence tags.** ✅ decidable from the files, ⚠️ a proxy that needs judgement, 🔬 needs runtime
  data (CI history, cloud settings, real plans) — 🔬 is listed but never scored.
- **The same formula as the database and networking families**: proportional criteria, Critical caps
  at 2.0, High at 6.0, 9.0 is "good", and a gate with extra conditions (remote locked state and a
  pipeline-only apply path for Terraform; build-once, verified and reversible prod deploys and no
  untrusted path to credentials for pipelines).
- **Propose sequences for safety.** Terraform refactors must plan to zero destroys; pipeline changes
  keep the path to production up, and a rebuilt pipeline runs alongside the old one until it has
  shipped on its own.

## Reference docs

| Doc | terraform | pipelines |
|---|---|---|
| theory | [T1–T22](terraform/theory.md) | [P1–P22](pipelines/theory.md) |
| review-rubric | [six domains](terraform/review-rubric.md) | [six domains](pipelines/review-rubric.md) |
| detection-signals | [grep per anti-pattern, AWS/azurerm/google](terraform/detection-signals.md) | [grep per anti-pattern, GHA/GitLab/Azure/Jenkins/CircleCI](pipelines/detection-signals.md) |
| scoring | [severity, confidence, formula, gate, templates](terraform/scoring.md) | [same, pipeline anchors](pipelines/scoring.md) |
| design-patterns | [layouts, state, modules, environments, AWS specifics](terraform/design-patterns.md) | [reference pipeline, release strategies, security model, IaC delivery](pipelines/design-patterns.md) |
| proposal | [decisions, no-recreate rule, sequencing](terraform/proposal.md) | [decisions, keep-prod-up sequencing](pipelines/proposal.md) |

## Not measured

Neither skill has an eval yet.
