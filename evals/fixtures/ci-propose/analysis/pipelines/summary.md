# storefront-api — Pipeline review summary
> Platform: GitHub Actions. Pipelines: 3 · jobs: 6 · environments: staging, production. Source as of 9c1e07a; rubric v1.0.

## Scores
| flow | feedback | release | security | environments | infrastructure | **System** |
|---:|---:|---:|---:|---:|---:|---:|
| 4.3 | 5.0 | 3.3 | 2.0 | 5.0 | N/A (no IaC) | **2.0** (uncapped 3.9) |

## Value stream
push to main ─► (ci.yml: lint ∥ unit → e2e, non-blocking) — not connected —
push to main ─► deploy.yml: deploy-staging (build ENV=staging, push :latest, kubectl apply) ─► deploy-prod (environment `production`; build ENV=prod, push :latest, scripts/deploy-prod.sh)
Durations: 🔬. Manual steps: the `production` environment's approval, if configured (🔬).

## What is working well
- `ci.yml`: least-privilege `permissions: contents: read`, lint and unit in parallel with an npm cache, runs on PRs and on main (P5, P18).
- The prod job uses a GitHub `environment`, so protection rules can be attached (P16).

## Top findings (worst first)
| ID | Object | Anti-pattern | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| CI-SEC-01 | pr-preview.yml / preview | `pull_request_target` checks out the PR head and runs it with `NPM_TOKEN` and a write-all token | ✅ | P18 | Critical | pr-preview.yml:5,14-18 |
| CI-SEC-02 | deploy.yml env | Slack webhook token committed as a literal | ✅ | P18 | Critical | deploy.yml:11 |
| CI-SEC-03 | pr-preview.yml / Announce | PR title interpolated into `run:` | ✅ | P18 | High | pr-preview.yml:21 |
| CI-SEC-04 | deploy.yml | Static AWS keys; `permissions: write-all` | ✅ | P18 | High | deploy.yml:6,19-22 |
| CI-SEC-05 | deploy-prod | `rtCamp/action-slack-notify@master` with prod credentials in scope | ✅ | P14, P18 | High | deploy.yml:44 |
| CI-FLO-01 | deploy-staging, deploy-prod | Image rebuilt per environment with baked config, pushed as `:latest` | ✅ | P3, P10 | High | deploy.yml:24,40; Dockerfile:6 |
| CI-FBK-01 | deploy.yml | No test gate before any deploy (independent of ci.yml) | ✅ | P8 | High | deploy.yml:3-5 |
| CI-REL-01 | deploy-staging vs deploy-prod | Different deploy mechanisms per environment | ✅ | P4 | High | deploy.yml:26; scripts/deploy-prod.sh |
| CI-REL-02 | deploy-prod | No post-deploy check; rollback re-runs a build of `:latest`; `Recreate` | ✅ | P12, P13 | High | scripts/deploy-prod.sh; k8s/deployment.yaml:8 |
| CI-FBK-02 | ci.yml / e2e | `continue-on-error: true` | ✅ | P6 | Medium | ci.yml:39 |
| CI-ENV-01 | Dockerfile | Environment config copied into the image | ✅ | P10 | Medium | Dockerfile:6 |

## Needs-data flags (not scored)
- 🔬 Branch protection on `main` and required status checks.
- 🔬 Reviewers configured on the `production` environment.
- 🔬 Whether `NPM_TOKEN` can publish, and whether either token has been used by a fork run.

## Gate
- Score ≥ 9.0: **fail**. No open Critical/High: **fail**. Build once and promote: **fail** (CI-FLO-01).
- Post-deploy check and rollback on prod: **fail** (CI-REL-02). No untrusted trigger reaching a credential: **fail** (CI-SEC-01).
