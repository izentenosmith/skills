# Contributing

- All changes go through a **merge request** into `main`; `main` is protected.
- A release is a tag `vX.Y.Z` on `main`. The tag pipeline deploys to **staging** automatically;
  production is the manual `promote_production` job, after someone has checked staging.
- Tests: `./run-tests.sh` (the same command CI runs).
