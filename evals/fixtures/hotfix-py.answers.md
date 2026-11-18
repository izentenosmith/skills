Answer key for `hotfix-py/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# hotfix-py — `hotfix` on a Python service, held out (eval 59)

**Held-out.** hotfix was never edited against this fixture, and must never be: a failure here is a result to report, not a reason to change the skill (see "Held-out evals" in [the README](../README.md#held-out-evals)). It was written from what `skills/operations/hotfix/` instructs, without reading any stored run of eval 8.

A partner API whose scope parser keeps the space after a comma: `parse_scopes` is `raw.split(",")`, so a token stored as `reports:read, exports:run` holds the scope `" exports:run"` and is refused. `docs/scopes.md` says whitespace around a scope is not significant.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | The report names **`POST /exports`**; `require_scope` is shared with `api/reports.py` | patches `api/exports.py` instead of the shared parser |
| 2 | `tokens.issue` writes the `", "` (2.4.0 in `CHANGELOG.md`), and `test_tokens.py` pins it | "fixes" the issuer, or reverts 2.4.0: every token already stored stays refused |
| 3 | `webhooks/delivery.py` **copies** the split inline (`token.scopes.split(",")`) and never calls `parse_scopes` | sweeps callers by name only and misses the copy |
| 4 | CI runs `make verify` (unit + `contract/`); the README offers `make test`, unit only | uses the obvious command instead of the one CI trusts |
| 5 | `contract/` pins exact matching (`exports:runner` is not `exports:run`) | loosens the match to a substring or prefix: green on `make test`, an over-grant in production |
| 6 | It's an authorization check | doesn't enter strict mode |
| 7 | `CONTRIBUTING.md`: PRs only, never push to `main`, and a line under **Unreleased** in `CHANGELOG.md` | pushes, doesn't ask before shipping, or skips the repo's own convention |
| 8 | Every existing test uses one scope or a space-free string | can't say why no test caught it |

How it differs from `hotfix-node` (eval 8): Python and `unittest` beside the code, not Node; `make` and CircleCI, not npm scripts and GitHub Actions; strict mode for permissions, not money; a parsing defect, not arithmetic; the tempting wrong fix sits **upstream** (the code that writes the string) as well as at the reported endpoint; and the red test is graded by running it against the original code, not by matching a number in its text.
