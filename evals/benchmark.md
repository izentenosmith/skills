# Benchmark

`delta` = assertions that test what the skill instructs. `cap` = does the skill do its job at all. `n` = with-skill runs; the baseline is one run.

| eval | from | n | delta (mean ± sd) | delta base | gain | cap | cap base |
|---|---|---|---|---|---|---|---|
| 0-architect-charter-and-options | i7 | 1 | 0.91 ± 0.00 | 0.00 | +0.91 | 1.00 | 1.00 |
| 1-brief-ordered-criteria | i1 | 3 | 1.00 ± 0.00 | 0.00 | +1.00 | 1.00 | 0.86 |
| 10-hotfix-script-no-tests | i7 | 1 | 1.00 ± 0.00 | 0.20 | +0.80 | 1.00 | 1.00 |
| 11-hotfix-routes-outage-out | i10 | 3 | 0.83 ± 0.29 | 0.00 | +0.83 | 1.00 | 1.00 |
| 12-incident-webapp-contain-by-flag | i10 | 3 | 0.95 ± 0.08 | 0.43 | +0.52 | 1.00 | 0.50 |
| 13-incident-batch-repair-artifact | i10 | 3 | 0.90 ± 0.17 | 0.60 | +0.30 | 1.00 | 1.00 |
| 14-incident-library-no-deploy | i7 | 1 | 1.00 ± 0.00 | 0.57 | +0.43 | 1.00 | 1.00 |
| 15-harness-loop-closes-teardown | i5 | 1 | 1.00 ± 0.00 | — | — | 1.00 | — |
| 16-netaudit-hub-spoke-recovers-and-scores | i6 | 1 | 1.00 ± 0.00 | 0.23 | +0.77 | 1.00 | 0.60 |
| 17-netdesign-plans-around-what-is-in-use | i6 | 1 | 0.90 ± 0.00 | 0.30 | +0.60 | 1.00 | 0.00 |
| 18-netdiagram-canonical-views-from-model | i6 | 1 | 0.90 ± 0.00 | 0.20 | +0.70 | 1.00 | 0.00 |
| 19-netpropose-contains-before-restructuring | i6 | 1 | 0.90 ± 0.00 | 0.70 | +0.20 | 1.00 | 1.00 |
| 2-tdd-reads-brief-vertical | i1 | 3 | 1.00 ± 0.00 | 0.50 | +0.50 | 0.78 | 0.83 |
| 20-netblueprint-waits-for-acceptance | i6 | 1 | 1.00 ± 0.00 | 1.00 | +0.00 | 1.00 | 1.00 |
| 21-terraform-review-state-and-secrets | i6 | 1 | 1.00 ± 0.00 | 0.57 | +0.43 | 1.00 | 0.83 |
| 22-terraform-design-isolates-state | i6 | 1 | 1.00 ± 0.00 | 0.86 | +0.14 | 1.00 | 1.00 |
| 23-terraform-propose-no-recreate | i6 | 1 | 0.91 ± 0.00 | 0.82 | +0.09 | 1.00 | 1.00 |
| 24-pipelines-review-untrusted-and-rebuild | i6 | 1 | 1.00 ± 0.00 | 0.67 | +0.33 | 1.00 | 0.75 |
| 25-pipelines-design-build-once-progressive | i6 | 1 | 1.00 ± 0.00 | 0.79 | +0.21 | 1.00 | 1.00 |
| 26-pipelines-propose-keeps-prod-up | i6 | 1 | 0.80 ± 0.00 | 0.50 | +0.30 | 1.00 | 1.00 |
| 27-acceptance-tests-red-for-the-right-reason | i12 | 3 | 1.00 ± 0.00 | 0.25 | +0.75 | 1.00 | 0.50 |
| 28-dockerfile-repair-pins-and-drops-root | i6 | 1 | 0.79 ± 0.00 | 0.79 | +0.00 | 1.00 | 1.00 |
| 29-release-notes-translates-drops-and-leads-with-breaking | i6 | 1 | 1.00 ± 0.00 | 0.54 | +0.46 | 1.00 | 0.86 |
| 3-refactor-promotes-noted-smell | i2 | 3 | 1.00 ± 0.00 | 0.14 | +0.86 | 1.00 | 1.00 |
| 30-dbaudit-postgres-dump-scored-not-fixed | i6 | 1 | 0.86 ± 0.00 | 0.36 | +0.50 | 1.00 | 0.83 |
| 31-dbdesign-sqlite-from-requirements-traps | i12 | 3 | 0.95 ± 0.04 | 0.54 | +0.41 | 0.93 | 0.80 |
| 32-dbdiagram-barker-and-relational-from-design | i6 | 1 | 0.83 ± 0.00 | 0.75 | +0.08 | 0.83 | 0.83 |
| 33-dbpropose-orphans-before-constraints | i12 | 3 | 0.92 ± 0.00 | 0.46 | +0.46 | 1.00 | 0.80 |
| 34-dbbuild-executable-ddl-from-accepted-proposal | i6 | 1 | 1.00 ± 0.00 | 0.78 | +0.22 | 1.00 | 1.00 |
| 4-teardown-finds-vacuous-test | i2 | 3 | 0.92 ± 0.14 | 0.25 | +0.67 | 1.00 | 1.00 |
| 5-verdict-cuts-and-slices | i2 | 3 | 1.00 ± 0.00 | 0.40 | +0.60 | 1.00 | 0.83 |
| 6-compose-detects-real-services | i6 | 1 | 0.89 ± 0.00 | 0.67 | +0.22 | 1.00 | 1.00 |
| 7-postmortem-widens-range-and-describes | i6 | 1 | 1.00 ± 0.00 | 0.60 | +0.40 | 1.00 | 1.00 |
| 8-hotfix-node-shared-cause | i7 | 1 | 1.00 ± 0.00 | 0.38 | +0.62 | 1.00 | 1.00 |
| 9-hotfix-jvm-both-callers | i7 | 1 | 1.00 ± 0.00 | 0.71 | +0.29 | 1.00 | 1.00 |

**Delta — current 0.95 vs baseline 0.49**
**Capability — current 0.99 vs baseline 0.85**

## Delta assertions the baseline also passed (still non-discriminating)

**eval-10-hotfix-script-no-tests**
- says plainly the repo has no tests

**eval-12-incident-webapp-contain-by-flag**
- the flag ranked ahead of a rollback
- asks for confirmation
- impact start from the logs, not the alert

**eval-13-incident-batch-repair-artifact**
- production database untouched
- the job not reloaded without confirmation
- 12 affected orders, cancelled excluded
- pausing the job proposed as containment
- the issued invoices named as a downstream copy
- a separate repair artifact

**eval-14-incident-library-no-deploy**
- containment fits a library: yank and/or advisory, with a pin
- a 2.3.1 patch through the release convention
- repair guidance for consumers' data
- why the tests missed it

**eval-16-netaudit-hub-spoke-recovers-and-scores**
- secrets recorded by kind and location
- evidence given as file:line
- no IaC or device config written or changed

**eval-17-netdesign-plans-around-what-is-in-use**
- exclusions written down in the design
- open questions listed
- no IaC written

**eval-18-netdiagram-canonical-views-from-model**
- no physical view invented for a cloud-only model
- the model left untouched

**eval-19-netpropose-contains-before-restructuring**
- renumbering sequenced against what depends on it
- retirement waits for usage confirmation
- connectivity before and after stated
- the residual on-prem single endpoint carried as open
- audit, design and diagrams left untouched
- no IaC written

**eval-2-tdd-reads-brief-vertical**
- brief revised in place when reality contradicted it

**eval-20-netblueprint-waits-for-acceptance**
- asks for explicit acceptance before producing the package
- names where acceptance comes from
- says plainly that nothing was produced or changed
- no network-design.md written
- no accepted topology.json written
- no diagram marked accepted
- proposal, design and diagrams left untouched
- no IaC written

**eval-21-terraform-review-state-and-secrets**
- no secret value echoed (kind and location only)
- rotation, not just removal, for the leaked credentials
- dev and prod found sharing one state object
- count-keyed databases flagged as a replacement risk
- prod drifted from dev on storage_encrypted
- what is working well is recorded
- no Terraform, tfvars or workflow file changed
- no real backend initialised

**eval-22-terraform-design-isolates-state**
- state split by lifecycle / ownership
- payments isolated for PCI
- leadership's one-bucket workspaces ask declined with a reason
- prod state isolated from non-prod
- version pinning policy with a committed lockfile
- CI applies with per-environment OIDC roles
- apply consumes a saved, reviewed plan
- humans read-only in prod, with break-glass
- destructive-change protection on stateful resources
- a narrow cross-state interface
- open questions listed
- no resources built (design, not build)

**eval-23-terraform-propose-no-recreate**
- the leaked key rotated before it is removed
- Critical exposure contained before structural work
- address changes declared with moved blocks
- the expected plan for the moves is zero destroys
- database protection lands before the identity moves
- state migrated with a backup, not hand state surgery
- needs-data flags carried as open questions
- code, review and design untouched
- nothing applied

**eval-24-pipelines-review-untrusted-and-rebuild**
- no secret value echoed (kind and location only)
- rotation for the committed webhook
- PR-title script injection found
- deploys not gated by any test found
- different deploy mechanisms per environment found
- no post-deploy check or real rollback found
- the @master action holding prod credentials found
- the silenced e2e job found
- what is working well is recorded
- no workflow, script, manifest or Dockerfile changed

**eval-25-pipelines-design-build-once-progressive**
- build once, promote the same digest
- per-environment builds with baked config replaced
- the 12-minute integration suite kept out of the commit stage
- rollout region by region with automated rollback
- migrations expand/contract, decoupled from the deploy
- deploy decoupled from release with flags
- the every-deploy approval meeting declined with a reason
- separation of duties enforced by the pipeline
- OIDC with per-environment roles
- Terraform planned on PR, saved plan applied from CI
- open questions listed

**eval-26-pipelines-propose-keeps-prod-up**
- NPM_TOKEN treated as possibly exposed
- needs-data flags carried as open questions
- every step has validation and rollback
- no workflow, script, review or design file changed

**eval-27-acceptance-tests-red-for-the-right-reason**
- red for the right reason: every failure is on behavior, none fails to load
- the mapping logged under Revisions
- no implementation of the cutoff rule

**eval-28-dockerfile-repair-pins-and-drops-root**
- stack inference stated (Node 20.11.1, pnpm lockfile, dist, PORT 8080, better-sqlite3, assets, amd64, start)
- the existing Dockerfile's defects named before the fix
- pinned to what the repo declares: node 20.11 in every stage, pnpm 9.12.3, digest or its absence recorded
- frozen install against pnpm-lock.yaml under a cache mount
- better-sqlite3 installed on the target platform and libc, not the build host's
- runs as a non-root user that owns its data directory, USER before CMD
- no secret in ENV, ARG or a copied env file
- built for linux/amd64 from Apple Silicon: stated, and --platform pinned in what the team runs
- .dockerignore extended, every curated entry kept
- .dockerignore: .env and .env.* out, .env.example in, node_modules and dist out

**eval-29-release-notes-translates-drops-and-leads-with-breaking**
- no internal identifiers in the notes
- the unmeasured timeline improvement carries no number
- fixes state the user's symptom, not the cause
- the reverted Slack threading is not announced
- the CVE published as its effect, not as a bump
- plain bumps, CI, tests, docs, lint and refactors dropped
- the unquantified improvement named in the handoff

**eval-3-refactor-promotes-noted-smell**
- prior venue_id smell explicitly left, not silently dropped

**eval-30-dbaudit-postgres-dump-scored-not-fixed**
- cross-file index criteria: the unindexed order_line.order_id FK and the redundant ix_product_sku
- no secret value echoed (kind and location only)
- both credentials recorded by kind and location
- no DDL, migration or config file changed
- evaluates and stops: no target table designed

**eval-31-dbdesign-sqlite-from-requirements-traps**
- the DDL runs on SQLite, the engine the requirements name
- plan prices kept as effective-dated history, unique per plan and date (executed)
- age not stored: a birth date instead (executed)
- natural keys are UNIQUE alternates, not primary keys (email, VAT, member number)
- the freelancer question left open: the company link optional and listed as an open question
- nothing applied: no database file created
- the requirements left untouched

**eval-32-dbdiagram-barker-and-relational-from-design**
- entities named singular UPPERCASE in soft-cornered boxes
- every attribute carries its # / * / o mark
- each end's optionality drawn: dashed may-be, solid must-be
- cell IDs are semantic and trace each entity to its table
- the inferred PET – VET relationship labelled as inferred
- a provenance note naming the design on both pages
- the design left untouched

**eval-33-dbpropose-orphans-before-constraints**
- the Critical handled before the name split
- no finding id invented
- the design and both diagrams cited by path
- audit, design and diagrams untouched, nothing redrawn
- nothing applied to a database

**eval-34-dbbuild-executable-ddl-from-accepted-proposal**
- parent tables created before the tables that reference them
- referential actions match the design
- no table or column beyond the approved design
- microchip uniqueness left undecided and flagged, not invented
- no credential from config/app.ini anywhere
- the SQL never run: no database tool call, no database file
- proposal, design, diagrams and config untouched

**eval-4-teardown-finds-vacuous-test**
- does not re-report the refuted party-size finding

**eval-5-verdict-cuts-and-slices**
- F4 struck as an already-refuted repeat, citing the prior verdict
- verdicts written back to the ledger

**eval-6-compose-detects-real-services**
- meilisearch detected from the source
- elasticsearch NOT composed (stale env var, no client)
- pg_isready probe names user and database
- dependencies gated on health, not just start
- migrations gated as a one-shot dependency
- verification from a cold start stated

**eval-7-postmortem-widens-range-and-describes**
- the 2026-07-26 trigger is found, nine days before the outage
- the 14:07 vs 14:22 contradiction is recorded, not silently resolved
- the unwatched alert channel is named as a detection factor
- evidence limits recorded (missing chat / expired retention)
- the latent condition is distinguished from the trigger
- the report's demands are not adopted as output

**eval-8-hotfix-node-shared-cause**
- fixed in the shared helper, not special-cased in invoice.js
- the inline duplicate in revenue.js found
- CI's command used, not npm test

**eval-9-hotfix-jvm-both-callers**
- fixed in Paginator, not patched in the exporter
- the API's totalPages named as a second caller
- run-tests.sh recorded as the suite
- merge-request convention followed
- staging verification before production

## Delta assertions that varied across repetitions

**eval-11-hotfix-routes-outage-out**
- changes no source or test file (2/3)

**eval-12-incident-webapp-contain-by-flag**
- no code changed before containment (2/3)

**eval-13-incident-batch-repair-artifact**
- a reproducible COUNT query (2/3)
- the repair defaults to a dry run and backs up first (2/3)
- the repair corrects exactly the affected orders (2/3)

**eval-31-dbdesign-sqlite-from-requirements-traps**
- the member subtypes mapped deliberately, with the choice stated (1/3)

**eval-33-dbpropose-orphans-before-constraints**
- orphan rows resolved before the foreign keys are declared (2/3)
- the relational diagram's mismatch described and routed to dbdiagram (1/3)

**eval-4-teardown-finds-vacuous-test**
- unproven findings name what would settle them (2/3)
