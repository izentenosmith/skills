# Review checklist

Run through this on every PR, author first, reviewer second.

- [ ] **Money** is integer minor units end to end; no float arithmetic on amounts.
- [ ] **New routes** have an auth dependency and appear in `api/openapi.yaml`.
- [ ] **External calls** have a timeout and a bounded number of retries.
- [ ] **Migrations** can be rolled back, and a backfill is a separate step.
- [ ] **Logs** carry no secrets, API keys or card data.
- [ ] **Tests** cover the failure path, not only the happy path.
- [ ] **No unused imports** and no commented-out code.
- [ ] **Names** are descriptive words; no abbreviations.
