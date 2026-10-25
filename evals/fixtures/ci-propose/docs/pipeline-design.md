# storefront-api — target pipeline

Traces to `analysis/pipelines/summary.md`.

## Stage chain

```
PR ─► ci (lint ∥ unit, cache) ─► build image once, tag sha-<sha>, push, sign
main ─► ci ─► build once ─► deploy staging (digest) ─► smoke ─► e2e (blocking)
          ─► deploy prod (same reusable deploy workflow, digest, environment approval)
          ─► rolling update (maxUnavailable 1) with rollout status ─► smoke ─► deploy marker
```

- One reusable workflow `deploy-env.yml` used for staging and prod (CI-REL-01).
- The image is environment-agnostic; config comes from a ConfigMap per environment (CI-FLO-01, CI-ENV-01).
- Rollback = run `deploy-env.yml` with the previous digest (CI-REL-02).
- AWS access through OIDC roles per environment; `permissions: contents: read` by default; third-party
  actions pinned by SHA (CI-SEC-04, CI-SEC-05).
- PR previews run on `pull_request` for same-repo branches only; no secrets on fork code (CI-SEC-01, CI-SEC-03).
- e2e is blocking; flaky tests are quarantined with an owner (CI-FBK-02).
- Slack notification reads its webhook from the environment's secrets (CI-SEC-02).
