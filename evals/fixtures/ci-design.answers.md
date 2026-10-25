Answer key for `ci-design/`. It lives **outside** the fixture folder on purpose.

# ci-design — `pipelines` in Design mode (eval 25)

A requirements document for a Go service on EKS in two prod regions, SOC 2, Terraform in `infra/`.

| # | Planted | The design should… | Catches a run that… |
|---|---|---|---|
| 1 | "The image is built separately for staging and prod so each gets the right config baked in" | build once, push by digest, promote the same digest; config from Helm values per environment (P3, P10) | keeps per-environment builds |
| 2 | Compliance wants a change-approval meeting before every deployment, staging included | decline it with a reason: peer review before merge plus an approval of the specific artifact for prod only, author ≠ approver enforced by the environment rule (P16, SOC 2 satisfied) | adopts a CAB for every environment |
| 3 | Integration tests take 12 minutes | keep them out of the commit stage (≤ 10 min) — acceptance stage, parallel (P5) | puts them in the first gating job |
| 4 | Two active-active prod regions; 15-minute outage = contractual incident | progressive rollout region by region with canary analysis and automatic rollback (P12, P13) | deploys both regions at once |
| 5 | Column renames coming | expand/contract migrations decoupled from the code deploy (P21) | runs destructive migrations with the deploy |
| 6 | "Turn features on for a few customers first" | feature flags: deploy ≠ release (P11) | — |
| 7 | Terraform applied by hand | plan on PR, saved plan applied from CI, OIDC per-account roles, serialized (P22) | — |
| 8 | GitHub-hosted runners, two AWS accounts | OIDC federation with per-environment roles; actions pinned by SHA; untrusted triggers kept away from secrets (P18) | static keys |
| 9 | Audit wants who/what/when | deploy records/markers and retained logs (P20, P16) | — |

Allowed: a YAML skeleton. If one is written it must pass `actionlint`.
