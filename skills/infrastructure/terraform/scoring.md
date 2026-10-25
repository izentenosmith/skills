# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How a Terraform review is graded and written down. **Rubric version: `v1.0`.** Every output
> records the rubric version it was graded against and the source version (commit) it read. Each
> finding names the principle it violates from [`theory.md`](theory.md) (T-N). A review that asserts
> a defect without naming the principle is incomplete — a defect without a principle is taste.
>
> The formula is the same one the database and networking families use, so a 7.4 means the same thing
> in all three.

## Severity taxonomy

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | Exposure an outsider can use now, a secret anyone with repo access can read, or a change path that can silently destroy data | A literal credential or access key in `.tf`/`.tfvars` committed to VCS; state (which holds secrets) in a public or unencrypted, unauthenticated location; an IAM policy granting `*:*` to a principal reachable from outside the account; a publicly readable bucket or database holding data; a stateful resource whose key is a `count` index in a list that is edited regularly, with no `prevent_destroy` |
| **High** | A broad integrity, isolation or availability gap | Local state for shared infrastructure; a remote backend with no locking; one state holding prod and non-prod; unpinned provider or core version; a module sourced from a branch (`?ref=main`) or with no ref; a production apply run from a laptop rather than a pipeline; no saved plan between review and apply; `ignore_changes = all` on a security-relevant resource; secrets passed as plain `variable` without `sensitive = true` and ending up in outputs |
| **Medium** | Maintainability cost, controlled risk, or debt that will become High as the estate grows | A root module with hundreds of resources across unrelated lifecycles; copy-pasted environment directories that have drifted; `count` where `for_each` keys are natural; hard-coded account IDs, regions or ARNs; provisioners used for configuration; missing tags/`default_tags`; no `tflint`/scanner in CI |
| **Low** | Naming, documentation, cosmetic | Inconsistent naming; variables without `description`/`type`; files not split by convention; unused variables or locals; `terraform fmt` drift |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current engineering practice.
- 🟡 **Acceptable / watch**: works, but carries operational, security or growth debt.
- 🔴 **Not well done**: violates the criterion. A defect, an anti-pattern, or a theory failure.

## Detection confidence

Not everything can be proven from `.tf` text. Every anti-pattern carries one of three tags.

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the code alone: no `required_providers` version, `backend "local"`, a literal `AKIA…` key, `?ref=main`, `0.0.0.0/0` on an ingress to port 22 | Yes. A confirmed defect. |
| ⚠️ **proxy** | A static signal that approximates a concern and needs judgement: resource count per root as a proxy for blast radius, missing `description` as a proxy for an undocumented interface, duplicated blocks across env folders as a proxy for drift | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs runtime state or the cloud account: whether state actually has drift, whether the backend bucket is encrypted when it's created outside this repo, who can assume the CI role, real plan output, whether a resource still exists | **No.** Recorded as a flag, never scored. |

A finding reached through `terraform plan` / `terraform show -json` output that the user supplied is ✅,
not 🔬 — the plan is evidence. Never run `plan`, `apply`, `import` or `state` commands against a real
backend unless the user explicitly asks; `init -backend=false`, `validate` and `fmt -check` are safe.

## Scoring model

### Evaluation units

One evaluation per **domain** per root (or per repo, for a small one), each graded with its section of
[`review-rubric.md`](review-rubric.md):

| Domain | In-scope objects (the weight) |
|---|---|
| structure | modules: every root module and every child module defined in the repo |
| state | state units: every root module × every environment it is applied to |
| dependencies | version constraints: core + each provider per root, and every `module` call |
| security | security-relevant resources: IAM, network exposure, storage, encryption, secrets, provider auth blocks |
| change-safety | stateful and replace-sensitive resources: databases, buckets, volumes, DNS zones, keys, anything with data or identity |
| delivery | root modules (each must have a path from commit to apply) |

A **codebase** is the unit the user names: one repo, or one directory of a monorepo. Several
codebases make an estate.

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   "In-scope" excludes objects the criterion cannot apply to: the `prevent_destroy` criterion does not
   apply to a stateless security group rule.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps**, applied after the base (lowest wins): any open **Critical** caps at **2.0**; any
   open **High** caps at **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Per-codebase and estate scores

The **codebase score** is the mean of its domain scores, weighted by in-scope object count, with the
Critical/High caps re-applied. The **estate score** is the mean of the codebase scores, weighted by
total objects, caps re-applied. Report the uncapped mean beside the capped one.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A codebase is **good enough** — no redesign proposal is owed — only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- every production state unit has remote state with locking, and production is isolated from
  non-production state (T6, T7);
- every root reaches apply only through a reviewed, saved plan in a pipeline (T13);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately. A 9.3 whose prod apply runs from a
laptop is not good enough.

## Triage for large codebases

Above **~50 root modules or ~2,000 resources**, don't read everything cold:

1. **Signal-scan** everything with [`detection-signals.md`](detection-signals.md) and record counts per
   anti-pattern.
2. **Rank** roots by signal density. Deep-read the worst 10% or 10 roots, whichever is larger, plus
   every module they call, plus a random sample of ~5.
3. **State coverage**: "deep-read 12 of 140 roots; signals cover all 140."

The inventory (roots, modules, backends, providers) must still cover **everything**: the state and
dependency domains are only meaningful on the whole estate.

## Theory → domain mapping

| Domain | Primary theory to invoke |
|---|---|
| structure | Small, simple pieces (T3); modules as interfaces (T9); DRY vs. coupling (T10) |
| state | State as the map (T5); remote state and locking (T6); blast radius and isolation (T7) |
| dependencies | Reproducibility (T2); pin everything (T11) |
| security | Least privilege (T14); secrets never in code or plain state (T15); defaults that fail closed (T16) |
| change-safety | Plan is a contract (T12); identity of resources (T8); destructive-change protection (T17); drift (T18) |
| delivery | Everything through the pipeline (T13); test pyramid for infrastructure (T19); policy as code (T20) |

## Templates

### Per-domain evaluation — `<codebase>/analysis/terraform/<domain>.md`

```markdown
# <Codebase> — <Domain> evaluation
> Evaluated against terraform/review-rubric.md §<domain> (rubric v1.0).
> Source: <paths> — as of <git commit>. Terraform <version>, providers <list>.
> Coverage: <N of M roots deep-read; signal-scan covers all M>.

## Findings
| ID | Object | Anti-pattern | Conf. | Theory violated | Severity | Evidence |
|----|--------|--------------|-------|-----------------|----------|----------|
| TF-STA-01 | envs/prod | Local state | ✅ | Remote state and locking (T6) | High | envs/prod/backend.tf:1 |

## Signal counts
| Anti-pattern | Count |
|--------------|------:|

## Needs-data flags (not scored)

## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)
```

### Per-codebase summary — `<codebase>/analysis/terraform/summary.md`

```markdown
# <Codebase> — Terraform review summary
> Roots: <n> · child modules: <n> · resources: <n> · environments: <list>. Source as of <commit>; rubric v1.0.

## Scores
| structure | state | dependencies | security | change-safety | delivery | **Codebase** |
|---:|---:|---:|---:|---:|---:|---:|

## Severity tally · Needs-data flags
## State map (root × environment → backend, key, lock, who applies)
## Module graph (who calls what, at which version)
## What is working well
## Top findings (worst first)
## Systemic issues
## Gate (each condition, pass/fail, with the reason)
```

Finding IDs: `TF-<STR|STA|DEP|SEC|CHG|DEL>-NN`.
