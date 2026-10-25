# storefront-api

Public API behind the storefront. Plain Node 22, no build step.

- `npm test` — unit tests; `npm run test:e2e` — end-to-end against `E2E_URL`
- CI: `.github/workflows/ci.yml`. Deploys: `.github/workflows/deploy.yml` (staging, then prod, on every push to `main`).
- Rollback: re-run an older deploy workflow run.
