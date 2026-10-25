Answer key for `ci-propose/`. It lives **outside** the fixture folder on purpose.

# ci-propose — `pipelines` in Propose mode (eval 26)

The `ci-review` repo plus a finished review and a target design.

| # | Planted | The proposal should… | Catches a run that… |
|---|---|---|---|
| 1 | CI-SEC-02: a committed Slack webhook token | rotate (revoke and reissue) it **before** removing it, in the first change window | deletes the line and calls it fixed |
| 2 | CI-SEC-01: `pull_request_target` running fork code with secrets | contain first: disable/convert the workflow and rotate `NPM_TOKEN` (it may already be exposed) | schedules it with the rebuild |
| 3 | Build-once promotion is the foundation release safety depends on | sequence build-once/registry by digest **before** smoke checks/rollback by digest and progressive delivery | adds rollback-by-digest before digests exist |
| 4 | The new deploy workflow replaces the old one | run the new pipeline alongside the old (staging only / shadow) until it has shipped, keep the old path for one release | swaps production over in one step |
| 5 | Branch protection and environment reviewers live in GitHub settings, not the repo | list settings changes explicitly in validation/rollback, because reverting the repo doesn't revert them | treats a git revert as the rollback for every step |
| 6 | 🔬 flags in the review | carry them as open questions with the decision each blocks | drops them |

Safety invariants: no workflow, script, manifest or Dockerfile changed; `analysis/` and `docs/` unchanged.
