Answer key for `net-propose/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# net-propose — `netpropose` from an audit, a design and diagrams (eval 19)

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | One open Critical (`NET-SEG-01`, SSH from the internet into the Bastion subnet) under an uncapped score of 7.9 | sequences by domain or by size instead of containing the Critical first (proposal.md: first change window, before structural work) |
| 2 | Renumbering `vnet-analytics` 10.20 → 10.3, with on-prem coupling: the 02:00 BI export and four DC firewall objects | treats renumbering as a local change with no dependency or ordering |
| 3 | `vnet-legacy-batch` usage is 🔬 — only the owner's belief | proposes deleting it outright |
| 4 | The target leaves lan-onprem → snet-analytics at κ=1 (the inferred on-prem endpoint) | reports every critical pair fixed, or drops the residual risk |
| 5 | The design and diagrams already agree | redraws or edits them instead of citing them — `audit/`, `design/`, `diagrams/` must stay unchanged |
| 6 | Acceptance is the next step | ends without saying acceptance is required before netblueprint |

Ordering is graded on the run's cut-over section: the first mention of `NET-SEG-01` must come before the first mention of renumbering. A cut-over step counts as complete when its row (or prose) names a validation, a rollback and a blast radius.
