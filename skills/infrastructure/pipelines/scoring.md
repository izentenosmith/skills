# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How a pipeline review is graded and written down. **Rubric version: `v1.0`.** Every output records
> the rubric version it was graded against and the source version (commit) it read. Each finding
> names the principle it violates from [`theory.md`](theory.md) (P-N). A review that asserts a defect
> without naming the principle is incomplete — a defect without a principle is taste.
>
> The formula is the same one the database, networking and Terraform skills use, so a 7.4 means the
> same thing everywhere.

## Severity taxonomy

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | Anyone outside the trust boundary can run code with the pipeline's credentials, a secret is readable by anyone with repo access, or a defect can reach production with no gate at all | A long-lived cloud key or token committed in a pipeline file; `pull_request_target` (or equivalent) that checks out and runs the PR head with secrets in scope; a production deploy credential available to jobs triggered by forks; a deploy job that pushes to production on every push to any branch with no test stage before it |
| **High** | A broad integrity, safety or feedback gap | The artifact is rebuilt per environment (what was tested is not what ships); production deploy with no automated test or smoke check; no rollback path; third-party actions/images referenced by a mutable tag (`@v3`, `:latest`) in a job holding deploy credentials; static cloud keys where OIDC is available; default `GITHUB_TOKEN`/job token with write-all permissions; Terraform `apply` without a reviewed saved plan; production reachable from unprotected branches |
| **Medium** | Flow and maintainability debt, controlled risk | Commit stage over ~10 minutes; no dependency cache; serial jobs that could run in parallel; manual steps between stages; environment-specific logic copy-pasted across jobs; flaky tests retried silently; no deployment marker or notification; no SAST/SCA/secret scan |
| **Low** | Naming, documentation, cosmetic | Unnamed steps; inconsistent stage names; no README for the pipeline; dead jobs or commented-out stages |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current engineering practice.
- 🟡 **Acceptable / watch**: works, but carries flow, safety or security debt.
- 🔴 **Not well done**: violates the criterion. A defect, an anti-pattern, or a theory failure.

## Detection confidence

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the pipeline definition and repo: `uses: actions/checkout@v4` (tag, not SHA), `permissions: write-all`, a `docker build` inside each deploy job, `AWS_SECRET_ACCESS_KEY:` literal, no job between `build` and `deploy-prod` | Yes. A confirmed defect. |
| ⚠️ **proxy** | A static signal that approximates a concern: test-job count as a proxy for coverage, a `retry:` on a test job as a proxy for flakiness, a manual approval gate as a proxy for an external CAB | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs the CI system's history or settings: real pipeline duration, failure rate, flaky-test rate, deployment frequency, lead time, change failure rate, MTTR, branch protection and environment protection rules set in the UI, who can approve | **No.** Recorded as a flag, never scored. |

When the user supplies run history, settings exports or DORA numbers, findings from them are ✅.
**Never trigger, re-run, cancel or approve a pipeline**, and never read secret values, unless the user
explicitly asks.

## Scoring model

### Evaluation units

One evaluation per **domain** per pipeline system (one repo's CI, usually), each graded with its
section of [`review-rubric.md`](review-rubric.md):

| Domain | In-scope objects (the weight) |
|---|---|
| flow | pipelines (each workflow / pipeline definition that builds or ships something) |
| feedback | test and verification jobs, plus the commit stage of each pipeline |
| release | deploy jobs × target environment |
| security | jobs that hold a credential or run untrusted input, plus every third-party action/image/template reference |
| environments | environments (dev, test, staging, prod, ephemeral) |
| infrastructure | IaC roots delivered by a pipeline (N/A when the repo has no IaC — say so and drop the domain) |

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps** (lowest wins): any open **Critical** caps at **2.0**; any open **High** caps at
   **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Per-system and estate scores

The **system score** is the mean of its domain scores, weighted by in-scope object count, caps
re-applied. Several repos make an **estate**: mean of system scores weighted by objects, caps
re-applied. Report uncapped beside capped.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A pipeline system is **good enough** — no redesign proposal is owed — only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- every production deploy promotes an artifact built once, upstream, and verified (P3);
- every production deploy has an automated post-deploy check and a stated rollback path (P13);
- no untrusted trigger can reach a job holding a production credential (P18);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately.

## Triage for large estates

Above **~30 pipeline definitions or ~300 jobs**, signal-scan everything with
[`detection-signals.md`](detection-signals.md), deep-read the pipelines that deploy to production
plus the worst 10% by signal density, sample ~5 more, and state coverage. Shared templates
(reusable workflows, GitLab `include:`, Azure templates, Jenkins shared libraries) are always
deep-read: one defect there is a defect in every caller.

## Theory → domain mapping

| Domain | Primary theory to invoke |
|---|---|
| flow | Automate everything, pipeline as code (P1, P2); build once (P3); fail fast (P5); small batches (P7); self-service and shared templates (P15) |
| feedback | Fast feedback and stop the line (P5, P6); test pyramid (P8) |
| release | Same deploy everywhere (P4); deploy ≠ release (P11); progressive delivery (P12); rollback and health (P13); migrations (P21); review over approval (P16) |
| security | Shift-left security (P17); protect the pipeline (P18); supply-chain integrity (P19); hermetic builds (P14) |
| environments | Production-like environments (P9); config separate from artifact (P10) |
| infrastructure | Infrastructure through the pipeline (P22); plan is the contract; drift |

## Templates

### Per-domain evaluation — `<repo>/analysis/pipelines/<domain>.md`

```markdown
# <Repo> — <Domain> evaluation
> Evaluated against pipelines/review-rubric.md §<domain> (rubric v1.0).
> Source: <pipeline files> — as of <git commit>. CI platform: <GitHub Actions | GitLab CI | …>.
> Coverage: <N of M pipelines deep-read; signal-scan covers all M; shared templates read: …>.

## Findings
| ID | Object | Anti-pattern | Conf. | Theory violated | Severity | Evidence |
|----|--------|--------------|-------|-----------------|----------|----------|
| CI-SEC-01 | deploy.yml / deploy-prod | Mutable action tag with deploy credentials | ✅ | Protect the pipeline (P18) | High | .github/workflows/deploy.yml:41 |

## Signal counts
## Needs-data flags (not scored)
## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)
```

### Per-system summary — `<repo>/analysis/pipelines/summary.md`

```markdown
# <Repo> — Pipeline review summary
> Platform: <…>. Pipelines: <n> · jobs: <n> · environments: <list>. Source as of <commit>; rubric v1.0.

## Scores
| flow | feedback | release | security | environments | infrastructure | **System** |
|---:|---:|---:|---:|---:|---:|---:|

## Value stream (commit → production: stages, gates, manual steps, measured or 🔬 durations)
## Severity tally · Needs-data flags
## What is working well
## Top findings (worst first)
## Systemic issues
## Gate (each condition, pass/fail, with the reason)
```

Finding IDs: `CI-<FLO|FBK|REL|SEC|ENV|INF>-NN`.
