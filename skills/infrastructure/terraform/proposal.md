# Proposal — From Review and Design to a Decision

This reference governs **Propose** mode. It consumes a review (Review mode's findings, scores and
gate) and a design (Design mode's `design.md`) when those exist. **Do not re-run the review or
re-design here.** If an input is missing, say so and scope the proposal to what exists — never imply
a missing review or design was done.

Treat review scores as evidence, not a substitute for judgement. Read the caps and the gate:
an open Critical caps a domain at 2.0, an open High at 6.0; 9.0 is the score threshold, and the gate
also needs remote locked state with prod isolated, and every root applied only through a reviewed
saved plan in a pipeline.

## Decisions per domain

Use each domain's band as the starting posture, then explain any evidence-based override:

| Score band | Starting posture |
|---|---|
| 9.0–10 | **Keep** |
| 7.0–8.9 | **Refactor** — targeted changes inside the current layout (pin a provider, add `moved` blocks, tag defaults, add a scanner) |
| 5.0–6.9 | **Rework** — change the pattern in this domain (split a monolithic state, replace copy-pasted env folders with one root and per-env config, introduce a module registry) |
| 0–4.9 | **Rebuild** — new layout for the domain, with resources migrated in by `import`/`moved`, never recreated |
| Abandoned root (no apply in months, resources gone) | **Retire** — state the evidence and the confirmation needed |

Any open Critical gets a corrective decision **in the first change window**, even when the overall
score is high. Secrets in code come first: **rotate the credential, then remove it** — deleting it
from HEAD does not remove it from history or from state.

## The refactoring rule: no resource is recreated by accident

Most Terraform improvement work is moving code, not changing infrastructure. A refactor is correct
only when the plan for it shows **0 to destroy** and **0 to add** for the moved objects (T8, T12).
The tools, in order of preference:

| Move | Use | Avoid |
|---|---|---|
| Rename a resource or module call, wrap resources into a module, `count` → `for_each` | `moved { from = … to = … }` blocks, committed with the code (Terraform ≥ 1.1) | `terraform state mv` by hand — unreviewed and unrepeatable across environments |
| Bring existing, unmanaged infrastructure under management | `import { to = … id = … }` blocks (≥ 1.5), with `-generate-config-out` for a draft only | ClickOps-then-forget; recreating the resource |
| Stop managing a resource without destroying it | `removed { from = … lifecycle { destroy = false } }` (≥ 1.7) | `terraform state rm` by hand |
| Split one state into several | `removed` (destroy = false) in the old root + `import` in the new root, applied in that order, in one change window, with a state backup taken first | Copying `.tfstate` files around |
| Upgrade a provider across a major version | One root at a time, non-prod first, reading the provider's upgrade guide; plan must be empty | Bumping every root at once |

Where the Terraform version predates the block, say so and fall back to scripted `state mv` run
**by the pipeline**, with the script committed and a state backup step.

## Sequencing

Order the work:

1. **Containment.** Rotate and remove leaked credentials; make a public state bucket private; turn on
   locking; block anything Critical. Small, reversible, first.
2. **Foundations others depend on.** Remote backend with locking and encryption per environment;
   pinned core and providers with a committed `.terraform.lock.hcl`; a pipeline that runs
   `fmt`/`validate`/lint/scan and posts the plan on every change (hand the pipeline design to the
   [pipelines](../pipelines/SKILL.md) skill).
3. **Apply path.** Move apply into the pipeline with a saved plan and an approval on production; remove
   human write credentials to production.
4. **Structural refactors in dependency order.** Split states leaf-first: the components other roots
   read (network, DNS, identity) stay put until their consumers read them through a stable interface
   (outputs + `terraform_remote_state` or, better, data sources / SSM-style parameters). Extract
   modules after the state boundaries settle, not before.
5. **Hardening.** Destructive-change protection on stateful resources, least-privilege pipeline roles,
   policy-as-code, drift detection on a schedule.
6. **Cleanup.** Delete dead variables, retire abandoned roots, remove `moved` blocks only after every
   environment has applied them.

## The register

Each step names:

- the finding IDs it addresses;
- the change in outline (the files and blocks — not a full diff);
- the **expected plan** per environment (`0 to add, 0 to change, 0 to destroy` for a pure refactor;
  the exact resources otherwise);
- the pre-check (state backup taken, lock free, no pending changes in the target root);
- the validation (plan is empty after apply; the drift job is clean; the service checks pass);
- the rollback (revert the commit and re-apply, restore the state version, or the explicit reason a
  step is one-way);
- the blast radius (roots, environments and services touched while it is in flight);
- the owner and window, if known.

All changes are proposals for review. This skill never runs `apply`, `import` or `state` commands
against a real backend.

## Deliverable — `proposal.md`

1. Executive recommendation, scope, source commit, Terraform and provider versions.
2. What is good, what needs attention, and the expected improvement: per-domain score now → target,
   and each gate condition now → target.
3. The decision register per domain, with evidence (finding IDs).
4. The target layout (from the design): the directory tree, the state map, the module graph.
5. The sequenced migration, with the per-step fields above.
6. Open questions — every 🔬 flag that blocks a decision, and the decision it blocks.
7. A closing line: nothing here is applied until the proposal is accepted, and each step's plan is
   reviewed in its own pull request.

Keep it reviewable. Link files instead of pasting large HCL.
