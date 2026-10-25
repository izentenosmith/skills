# Proposal — From Review and Design to a Decision

This reference governs **Propose** mode. It consumes a review (Review mode's findings, scores and
gate) and a design (Design mode's `pipeline-design.md`) when those exist. **Do not re-run the review
or re-design here.** If an input is missing, say so and scope the proposal accordingly.

Read the caps and the gate: an open Critical caps a domain at 2.0, an open High at 6.0; 9.0 is the
score threshold, and the gate also needs build-once promotion, a post-deploy check and rollback on
every production deploy, and no untrusted trigger reaching a production credential.

## Decisions per domain

| Score band | Starting posture |
|---|---|
| 9.0–10 | **Keep** |
| 7.0–8.9 | **Refactor** — targeted changes in the current pipeline (pin actions, add a cache, parallelize, add a smoke test) |
| 5.0–6.9 | **Rework** — change the pattern in this domain (introduce an artifact registry and promotion, replace per-env builds, move to OIDC, add progressive delivery) |
| 0–4.9 | **Rebuild** — a new pipeline for the domain, run in parallel with the old one until it has shipped on its own |
| Dead pipeline (never triggered, targets gone) | **Retire** — state the evidence |

Any open Critical gets a corrective decision **in the first change window**. Leaked credentials are
**rotated first, then removed** — history and logs keep the old value.

## Sequencing

Pipelines are production infrastructure: a broken pipeline blocks every team that ships through it,
including the fix for the pipeline. Order the work so the path to production is never down:

1. **Containment.** Rotate leaked secrets; restrict token permissions; stop untrusted triggers from
   reaching secrets; pin third-party actions used by deploy jobs. Small and reversible.
2. **Fast, trustworthy commit stage.** Caching, parallelism, splitting slow tests out, quarantining
   flaky tests with an owner. Every later stage depends on developers trusting red.
3. **Build once and promote.** Artifact registry, immutable version per commit, every later stage
   pulls by digest. This is the foundation the release stages need.
4. **Release safety.** Same deploy mechanism for every environment, post-deploy smoke checks,
   automated rollback, then progressive delivery (canary / blue-green) and deploy markers.
5. **Supply chain and policy.** OIDC instead of static keys, SAST/SCA/secret/IaC scanning, SBOM and
   signing, protected environments.
6. **Cleanup.** Remove the old pipeline, dead jobs and unused secrets after the new one has carried
   real releases.

For a rebuild, **run the new pipeline alongside the old** (shadow mode: build and test, deploy to
non-prod only) until it has produced N green runs, then switch production, keeping the old path
available for one release as a rollback.

## The register

Each step names:

- the finding IDs it addresses;
- the change in outline (files, jobs, settings — not a full diff);
- the pre-check (what must already be true: registry exists, OIDC trust configured, etc.);
- the validation (a run that shows it working: the duration drop, the smoke job failing on purpose in
  a non-prod environment, the rollback exercised once);
- the rollback (revert the pipeline change; settings changed in the CI UI listed explicitly, because a
  revert of the repo doesn't revert them);
- the blast radius (which teams' pipelines, which environments, while it is in flight);
- the expected effect on the four delivery metrics, stated as a direction, or measured when data
  exists;
- the owner and window, if known.

All changes are proposals for review. This skill never triggers, re-runs, approves or edits settings
in a real CI system.

## Deliverable — `proposal.md`

1. Executive recommendation, scope, source commit, CI platform(s).
2. What is good, what needs attention, and the expected improvement: per-domain score now → target,
   each gate condition now → target, and the value stream now → target (stages, manual steps,
   durations).
3. The decision register per domain, with evidence (finding IDs).
4. The target pipeline (from the design): the stage diagram, the promotion path, the environment
   matrix.
5. The sequenced migration, with the per-step fields above.
6. Open questions — every 🔬 flag that blocks a decision (run history, CI settings, DORA numbers).
7. A closing line: nothing is changed until the proposal is accepted, and each step lands in its own
   reviewed pull request.
