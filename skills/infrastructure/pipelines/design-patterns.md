# Design Patterns — Stages, Promotion, Release, Security, IaC

> The patterns Design mode chooses between, each with when it fits, what it costs, and **the
> default**. Cite the principle (P-N, [`theory.md`](theory.md)) when you pick one; say why when you
> deviate.

---

## §1 The reference pipeline

```
          ┌──────────── commit stage (≤10 min) ────────────┐
PR/push ─►│ checkout · deps (cached) · lint · unit · SAST   │─► artifact@digest ─► registry
          │ SCA · secret scan · build ONCE · sign · SBOM    │        (immutable, signed)
          └─────────────────────────────────────────────────┘
                          │ (merge to trunk)
                          ▼
  acceptance ─► deploy artifact to test env · smoke · acceptance suite (parallel) · DAST
                          │ gate: all green
                          ▼
  staging ───► same deploy job · migrations · smoke · (capacity, scheduled or on release candidates)
                          │ gate: green + risk-based approval if required
                          ▼
  production ► same deploy job · progressive rollout · health analysis · auto-rollback · deploy marker
```

Every arrow consumes the **same artifact** (P3) through the **same deploy job** (P4). Stage
contracts:

| Stage | Proves | Hands on | Budget | Gate |
|---|---|---|---|---|
| Commit | it compiles, units pass, no known-bad dependency/secret/pattern | signed artifact + SBOM + reports | ≤ 10 min (≤ 5 ideal) | hard |
| Acceptance | it works as specified in a prod-like env | the same artifact, marked "accepted" | ≤ 30–60 min, parallelized | hard |
| Staging | it deploys and migrates like prod, integrates with real dependencies | the same artifact, marked "release candidate" | minutes | hard; approval only if policy requires |
| Production | it serves users within SLO | deploy record + marker | rollout duration by risk | health/SLO analysis, auto-rollback |

Manual exploratory testing pulls any accepted build on demand; it doesn't sit in the line (CD p. 112).

**Smaller is fine.** A library or a small service may be commit → publish/deploy with a smoke check.
Say which stages you dropped and why. **Never drop:** build-once, a test gate before production, a
post-deploy check, a rollback path.

## §2 Branching and triggers

| Model | Use | Cost |
|---|---|---|
| **Trunk-based, short-lived PR branches (≤ 1–2 days)** | **Default** (P7) | Needs feature flags / branch by abstraction for unfinished work |
| Release branches cut from trunk | Versioned products with supported releases | Fixes land on trunk first, cherry-picked; re-run gates on the branch (SRE ch. 8 p. 90) |
| GitFlow / long-lived `develop` | Avoid | Not CI; merge debt; untested combinations (CD ch. 14) |

Triggers: PR → commit stage (+ plan for IaC); merge to trunk → full pipeline; tag → (only if
releases are versioned) **promote**, don't rebuild; schedule → drift, dependency updates, capacity
tests — never as the only trigger for a gate.

## §3 Artifact and promotion model

- One registry per artifact type (OCI registry, package feed). Artifacts are named by immutable
  version (`<semver>+<sha>` or `sha-<sha>`) and referenced by digest downstream.
- Promotion = recording that an artifact passed a stage (metadata, attestation, or a label/tag added
  to the same digest) — never copying a rebuilt artifact (SRE ch. 8 p. 91).
- Configuration is not in the artifact. It comes from the environment at deploy/run time: env vars,
  mounted config, a config service, Helm values per environment (P10).
- Keep released artifacts for rollback; purge failed candidates (CD ch. 7).

## §4 Test placement

| Where | What | Notes |
|---|---|---|
| Pre-commit / IDE | format, lint, fast unit | optional, mirrors the commit stage |
| Commit stage | unit, static analysis, SCA, secret scan, 1–2 smoke tests that the app starts | no network, no DB; ≤ 10 min |
| Acceptance | component, contract, functional acceptance via an app driver, deployment smoke first | prod-like env; state created per test; parallel |
| Integration-point stage | small suite against real third parties' test instances | less often; doesn't block every commit |
| Capacity / performance | scenario tests with thresholds | dedicated env; on release candidates or nightly; guard tests in commit stage |
| Post-deploy | smoke, synthetic probes | every environment, every deploy |

Flaky tests: quarantine out of the gate with an owner and a deadline; track the flake rate (P6).
Every escaped bug gets a test at the lowest level that would catch it (DOH ch. 10).

## §5 Release strategies

| Strategy | Use when | Rollback | Requires |
|---|---|---|---|
| **Rolling, bounded** (`maxSurge`/`maxUnavailable` small, readiness-gated) | **Default** for stateless services on orchestrators | `rollout undo` / redeploy previous digest | good readiness probes separate from liveness (SRE ch. 22) |
| **Blue-green** | Need instant cut-over/rollback; VM or PaaS slots | flip back | double capacity during switch; schema compatible both ways |
| **Canary with analysis** | Large user-facing services; risky changes | stop routing | metrics for canary vs. baseline (errors incl. implicit, p99 latency, saturation); automated judgement (Argo Rollouts, Flagger, deployment groups) |
| **Feature flags / dark launch** | Decouple release from deploy; risky features | flag off | flag service, flag hygiene, tests with flags on (P11) |
| Recreate / all-at-once | Dev environments, batch jobs, singletons that can't run two versions | redeploy | accepted downtime |

Canary progression default: 1–5% → 25% → 100%, bake long enough to see the error budget move, region
by region for multi-region services (SRE ch. 17 p. 189). Promotion reads SLO burn / golden signals;
when the error budget is exhausted, only fixes promote (SRE ch. 3).

**Rollback:** the deploy job with the previous artifact's digest, or the strategy's native undo.
One button, rehearsed in non-prod on a schedule. Database: expand/contract so rollback never needs a
down-migration (P21).

## §6 Infrastructure delivery

```
PR      ─► fmt · validate · lint · scan · terraform test ─► plan (read-only role) per affected root×env
           ─► plan posted to PR · policy check on plan JSON · destroy guard
merge   ─► for env in dev, staging, prod (serialized per root/env):
              plan -out=tfplan (write role for env) ─► [prod: approve this plan] ─► apply tfplan
              ─► post-apply checks (drift plan empty, smoke)
schedule ─► plan -detailed-exitcode per prod root ─► exit 2 → alert/issue
```

- **Saved plan, always:** the apply consumes the plan artifact that was reviewed; if the plan is
  stale (state changed), re-plan and re-approve (P22).
- **Identities:** plan role read-only; apply role per environment, scoped to what the root manages;
  both via OIDC (P18).
- **Serialization:** `concurrency` group per root×env (GHA), `resource_group` (GitLab),
  exclusive lock checks (Azure), in addition to backend locking.
- **Affected roots:** from changed paths and module call graph; changes to a shared module plan every
  caller.
- **App coupling:** an infrastructure change that affects a service re-runs that service's smoke
  checks (CD p. 285).
- Tools: plain CI with `tfcmt`-style PR comments; Atlantis; HCP Terraform/Spacelift/env0 — choose by
  the policy and audit needs, not by fashion (T22).

## §7 Security model

| Control | Default |
|---|---|
| Token permissions | top-level `permissions: contents: read`; elevate per job |
| Cloud credentials | OIDC federation; trust policy pinned to repo + branch/environment (`sub` claim); per-environment roles |
| Secrets | platform secret store or vault, scoped to environments; never echoed; masked |
| Untrusted triggers | `pull_request` (no secrets) for fork code; `pull_request_target` only for metadata (labels, comments) and **never** with PR checkout; `workflow_run` treats artifacts from PRs as untrusted |
| Injection | pass event fields via `env:` and quote them; never `${{ … }}` inside `run:` for attacker-controlled fields |
| Third-party code | actions pinned by SHA, images by digest, includes by ref; Dependabot/Renovate to update them |
| Runners | ephemeral (fresh VM/container per job); self-hosted only for trusted triggers; no long-lived credentials on runners |
| Scanning | SAST, SCA, secret, IaC, container scan on PR; DAST on acceptance env; fail on agreed severity |
| Integrity | sign artifacts (cosign/Sigstore), attach provenance and SBOM, verify at deploy (admission policy) |
| Protected branches/environments | required reviews, required status checks, prod environment restricted to trunk; pipeline files covered by CODEOWNERS |
| Audit | the pipeline records who/what/when/which artifact for every deploy; logs retained centrally (DOH ch. 23) |

## §8 Change approval

Default: **peer review before merge + automated gates**, with production deploys as standard changes
recorded automatically (DOH ch. 18, 23). Add a manual production approval only where regulation or a
risk class demands it, and then approve **the specific artifact/plan**, by someone in the team, with
the pipeline enforcing that the author isn't the approver if separation of duties is required.
Measure gates: an approval that never rejects is toil (SRE ch. 5) — remove it or automate what it
checks.

## §9 Templates and ownership

- Shared pipeline logic is a **versioned template** (reusable workflows, GitLab CI components,
  Azure templates repo, Jenkins shared library) consumed by ref; owners publish a changelog and
  migrate callers on breaking changes (P15; SRE ch. 27).
- Each service owns its pipeline definition; the platform owns the templates and the runners.
- Template defects are estate-wide defects: review and test templates with a sample repo pipeline
  before tagging.

## §10 Measuring the pipeline

Instrument: stage start/end, artifact digest per environment, deploy events (to dashboards, not
pagers), and the four delivery metrics — deployment frequency, lead time for changes, change failure
rate, time to restore (DOH; CD ch. 5). Alert on build-time regression (×2) and on main being red for
longer than the agreed fix-or-revert window. Read throughput and stability together.
