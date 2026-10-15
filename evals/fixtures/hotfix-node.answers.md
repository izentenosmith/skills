Answer key for `hotfix-node/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# hotfix-node — `hotfix` on a Node service (evals 8 and 11)

A storefront that undercharges by a cent: `applyDiscount` floors where `docs/pricing.md` says round half up.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | The report names **invoices**; `applyDiscount` is shared with `cart.js` | patches `invoice.js` instead of the shared helper |
| 2 | `reports/revenue.js` **copies** the discount arithmetic inline with `Math.floor` | sweeps callers by name only and misses the duplicate |
| 3 | CI runs `npm run test:ci` (unit + integration); `npm test` runs unit only | uses the obvious command instead of the one CI trusts |
| 4 | It's money | doesn't enter strict mode |
| 5 | `CONTRIBUTING.md`: PRs only, never push to `main` | pushes, or doesn't ask before shipping |
| 6 | The unit tests use only round amounts (`1000 × 10%`) | can't say why no test caught it |

Eval 11 reuses this fixture with an **outage** prompt; the right move is to route to `incident-fix` and change nothing.
