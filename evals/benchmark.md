# Benchmark

`delta` = assertions that test what the skill instructs. `cap` = does the skill do its job at all. `n` = with-skill runs; the baseline is one run.

| eval | from | n | delta (mean ± sd) | delta base | gain | cap | cap base |
|---|---|---|---|---|---|---|---|
| 0-architect-charter-and-options | i15 | 3 | 1.00 ± 0.00 | 0.00 | +1.00 | 1.00 | 1.00 |
| 1-brief-ordered-criteria | i15 | 3 | 1.00 ± 0.00 | 0.00 | +1.00 | 1.00 | 1.00 |
| 10-hotfix-script-no-tests | i20 | 3 | 1.00 ± 0.00 | 0.20 | +0.80 | 1.00 | 1.00 |
| 11-hotfix-routes-outage-out | i20 | 3 | 1.00 ± 0.00 | 0.00 | +1.00 | 1.00 | 1.00 |
| 12-incident-webapp-contain-by-flag | i17 | 3 | 1.00 ± 0.00 | 0.43 | +0.57 | 1.00 | 0.50 |
| 13-incident-batch-repair-artifact | i17 | 3 | 1.00 ± 0.00 | 0.70 | +0.30 | 1.00 | 1.00 |
| 14-incident-library-no-deploy | i17 | 3 | 1.00 ± 0.00 | 0.57 | +0.43 | 1.00 | 1.00 |
| 15-harness-loop-closes-teardown | i5 | 1 | 1.00 ± 0.00 | — | — | 1.00 | — |
| 16-netaudit-hub-spoke-recovers-and-scores | i21 | 3 | 1.00 ± 0.00 | 0.31 | +0.69 | 1.00 | 0.60 |
| 17-netdesign-plans-around-what-is-in-use | i21 | 3 | 0.90 ± 0.00 | 0.30 | +0.60 | 1.00 | 0.20 |
| 18-netdiagram-canonical-views-from-model | i23 | 3 | 1.00 ± 0.00 | 0.20 | +0.80 | 1.00 | 0.00 |
| 19-netpropose-contains-before-restructuring | i23 | 3 | 1.00 ± 0.00 | 0.70 | +0.30 | 1.00 | 0.67 |
| 2-tdd-reads-brief-vertical | i24 | 3 | 1.00 ± 0.00 | 0.00 | +1.00 | 1.00 | 0.88 |
| 20-netblueprint-waits-for-acceptance | i23 | 3 | 1.00 ± 0.00 | 0.75 | +0.25 | 1.00 | 1.00 |
| 21-terraform-review-state-and-secrets | i26 | 3 | 1.00 ± 0.00 | 0.57 | +0.43 | 1.00 | 0.83 |
| 22-terraform-design-isolates-state | i26 | 3 | 1.00 ± 0.00 | 0.71 | +0.29 | 1.00 | 1.00 |
| 23-terraform-propose-no-recreate | i26 | 3 | 1.00 ± 0.00 | 0.43 | +0.57 | 1.00 | 1.00 |
| 24-pipelines-review-untrusted-and-rebuild | i26 | 3 | 1.00 ± 0.00 | 0.67 | +0.33 | 1.00 | 0.75 |
| 25-pipelines-design-build-once-progressive | i26 | 3 | 1.00 ± 0.00 | 0.65 | +0.35 | 1.00 | 1.00 |
| 26-pipelines-propose-keeps-prod-up | i26 | 3 | 0.93 ± 0.06 | 0.70 | +0.23 | 1.00 | 1.00 |
| 27-acceptance-tests-red-for-the-right-reason | i15 | 3 | 0.94 ± 0.05 | 0.25 | +0.69 | 1.00 | 0.67 |
| 28-dockerfile-repair-pins-and-drops-root | i16 | 3 | 1.00 ± 0.00 | 0.83 | +0.17 | 1.00 | 1.00 |
| 29-release-notes-translates-drops-and-leads-with-breaking | i26 | 3 | 0.90 ± 0.09 | 0.39 | +0.51 | 1.00 | 0.57 |
| 3-refactor-promotes-noted-smell | i24 | 3 | 1.00 ± 0.00 | 0.12 | +0.88 | 1.00 | 0.75 |
| 30-dbaudit-postgres-dump-scored-not-fixed | i23 | 3 | 0.95 ± 0.04 | 0.43 | +0.52 | 1.00 | 1.00 |
| 31-dbdesign-sqlite-from-requirements-traps | i23 | 3 | 0.97 ± 0.04 | 0.46 | +0.51 | 1.00 | 1.00 |
| 32-dbdiagram-barker-and-relational-from-design | i18 | 3 | 1.00 ± 0.00 | 0.88 | +0.12 | 1.00 | 1.00 |
| 33-dbpropose-orphans-before-constraints | i18 | 3 | 0.97 ± 0.04 | 0.54 | +0.44 | 1.00 | 0.80 |
| 34-dbbuild-executable-ddl-from-accepted-proposal | i18 | 3 | 1.00 ± 0.00 | 0.78 | +0.22 | 1.00 | 1.00 |
| 35-container-hardening-review-socket-and-firewall | i16 | 3 | 1.00 ± 0.00 | 0.57 | +0.43 | 1.00 | 1.00 |
| 36-container-debug-oom-localhost-crlf | i16 | 3 | 1.00 ± 0.00 | 0.82 | +0.18 | 1.00 | 1.00 |
| 37-docker-swarm-review-quorum-and-state | i16 | 3 | 1.00 ± 0.00 | 0.75 | +0.25 | 1.00 | 1.00 |
| 38-threatmodel-review-design-abuse-and-fallback | i26 | 3 | 1.00 ± 0.00 | 0.50 | +0.50 | 1.00 | 1.00 |
| 39-threatmodel-design-abusers-and-traps | i26 | 3 | 0.96 ± 0.03 | 0.65 | +0.31 | 1.00 | 1.00 |
| 4-teardown-finds-vacuous-test | i24 | 3 | 1.00 ± 0.00 | 0.20 | +0.80 | 1.00 | 1.00 |
| 40-threatmodel-propose-contain-then-design-out | i14 | 3 | 1.00 ± 0.00 | 0.54 | +0.46 | 1.00 | 1.00 |
| 41-appsec-review-inventory-and-secrets | i26 | 3 | 0.98 ± 0.03 | 0.61 | +0.37 | 1.00 | 1.00 |
| 42-appsec-design-reshapes-the-quick-wins | i26 | 3 | 1.00 ± 0.00 | 0.71 | +0.29 | 1.00 | 1.00 |
| 43-appsec-propose-contain-then-fix-the-class | i26 | 3 | 0.93 ± 0.00 | 0.50 | +0.43 | 1.00 | 1.00 |
| 44-hardening-review-mixed-estate | i26 | 3 | 0.98 ± 0.03 | 0.68 | +0.30 | 1.00 | 1.00 |
| 45-hardening-design-tier-aware-baseline | i26 | 3 | 1.00 ± 0.00 | 0.60 | +0.40 | 1.00 | 1.00 |
| 46-hardening-propose-no-lockout | i26 | 3 | 0.95 ± 0.04 | 0.69 | +0.26 | 1.00 | 1.00 |
| 47-dbquery-workload-ranked-plans-read-indexes-weighed | i18 | 3 | 1.00 ± 0.00 | 0.93 | +0.07 | 1.00 | 0.83 |
| 48-dbarchitect-one-system-of-record-no-dual-writes | i18 | 3 | 1.00 ± 0.00 | 0.67 | +0.33 | 1.00 | 1.00 |
| 49-peer-review-claim-omission-injection | i25 | 3 | 1.00 ± 0.00 | 0.29 | +0.71 | 1.00 | 1.00 |
| 5-verdict-cuts-and-slices | i15 | 3 | 1.00 ± 0.00 | 0.33 | +0.67 | 1.00 | 0.83 |
| 50-pr-prep-splits-and-discloses | i25 | 3 | 0.97 ± 0.04 | 0.31 | +0.67 | 1.00 | 1.00 |
| 51-code-xray-hotspots-not-cold-giants | i25 | 3 | 1.00 ± 0.00 | 0.40 | +0.60 | 1.00 | 0.83 |
| 52-test-review-would-it-fail | i25 | 3 | 1.00 ± 0.00 | 0.20 | +0.80 | 1.00 | 0.83 |
| 53-concurrency-review-interleavings-and-replicas | i25 | 3 | 1.00 ± 0.00 | 0.39 | +0.61 | 1.00 | 0.83 |
| 54-review-retro-areas-not-people | i25 | 3 | 1.00 ± 0.00 | 0.29 | +0.71 | 1.00 | 1.00 |
| 6-compose-detects-real-services | i16 | 3 | 1.00 ± 0.00 | 0.78 | +0.22 | 1.00 | 1.00 |
| 7-postmortem-widens-range-and-describes | i6 | 1 | 1.00 ± 0.00 | 0.60 | +0.40 | 1.00 | 1.00 |
| 8-hotfix-node-shared-cause | i20 | 3 | 1.00 ± 0.00 | 0.38 | +0.62 | 1.00 | 1.00 |
| 9-hotfix-jvm-both-callers | i20 | 3 | 1.00 ± 0.00 | 0.71 | +0.29 | 1.00 | 1.00 |

**Delta — current 0.99 vs baseline 0.49**
**Capability — current 1.00 vs baseline 0.90**

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
- the repair corrects exactly the affected orders

**eval-14-incident-library-no-deploy**
- containment fits a library: yank and/or advisory, with a pin
- a 2.3.1 patch through the release convention
- repair guidance for consumers' data
- why the tests missed it

**eval-16-netaudit-hub-spoke-recovers-and-scores**
- no secret value reproduced anywhere
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
- decisions use the band vocabulary
- connectivity before and after stated
- the residual on-prem single endpoint carried as open
- audit, design and diagrams left untouched
- no IaC written

**eval-20-netblueprint-waits-for-acceptance**
- names where acceptance comes from
- asks for the acceptance record: who, when and which version
- the κ=1 on-prem pair named as an exception acceptance must cover
- the missing audit named as a gap for the package
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
- code, review and design untouched
- nothing applied

**eval-24-pipelines-review-untrusted-and-rebuild**
- no secret value echoed (kind and location only)
- rotation for the committed webhook
- PR-title script injection found
- deploys not gated by any test found
- no post-deploy check or real rollback found
- the @master action holding prod credentials found
- the silenced e2e job found
- the gate stated with its conditions
- what is working well is recorded
- no workflow, script, manifest or Dockerfile changed

**eval-25-pipelines-design-build-once-progressive**
- build once, promote the same digest
- per-environment builds with baked config replaced
- rollout region by region with automated rollback
- migrations expand/contract, decoupled from the deploy
- deploy decoupled from release with flags
- the every-deploy approval meeting declined with a reason
- separation of duties enforced by the pipeline
- OIDC with per-environment roles
- third-party actions pinned by SHA
- Terraform planned on PR, saved plan applied from CI
- open questions listed

**eval-26-pipelines-propose-keeps-prod-up**
- the webhook rotated before it is removed
- NPM_TOKEN treated as possibly exposed
- untrusted-trigger containment comes first
- needs-data flags carried as open questions
- every step has validation and rollback
- no workflow, script, review or design file changed

**eval-27-acceptance-tests-red-for-the-right-reason**
- the config test kills a hard-coded-window mutant (not vacuous)
- no internals: tests import only the public entry point
- no implementation of the cutoff rule

**eval-28-dockerfile-repair-pins-and-drops-root**
- stack inference stated (Node 20.11.1, pnpm lockfile, dist, PORT 8080, better-sqlite3, assets, amd64, start)
- the existing Dockerfile's defects named before the fix
- pinned to what the repo declares: node 20.11 in every stage, pnpm 9.12.3, digest or its absence recorded
- frozen install against pnpm-lock.yaml under a cache mount
- runtime ships only dist, production deps, migrations/ and templates/: no source, no toolchain
- better-sqlite3 installed on the target platform and libc, not the build host's
- port and health from the source: EXPOSE 8080, /healthz with a tool the runtime has (or left to the k8s probes)
- runs as a non-root user that owns its data directory, USER before CMD
- USER is a numeric uid, which the pod's runAsNonRoot can verify
- application code stays root-owned: only the data directory is the runtime user's
- the cache check changes a source file's content, not its mtime
- no secret in ENV, ARG or a copied env file
- built for linux/amd64 from Apple Silicon: stated, and --platform pinned in what the team runs
- .dockerignore extended, every curated entry kept
- .dockerignore: .env and .env.* out, .env.example in, node_modules and dist out

**eval-29-release-notes-translates-drops-and-leads-with-breaking**
- header has the exact version and the tag's date
- the breaking change sits above the features, with the action
- the unmeasured timeline improvement carries no number
- fixes state the user's symptom, not the cause
- the unquantified improvement named in the handoff

**eval-3-refactor-promotes-noted-smell**
- prior venue_id smell explicitly left, not silently dropped

**eval-30-dbaudit-postgres-dump-scored-not-fixed**
- cross-file index criteria: the unindexed order_line.order_id FK and the redundant ix_product_sku
- no secret value echoed (kind and location only)
- both credentials recorded by kind and location
- every cited line exists and the evidence points at the planted defects
- no DDL, migration or config file changed
- evaluates and stops: no target table designed

**eval-31-dbdesign-sqlite-from-requirements-traps**
- plan prices kept as effective-dated history, unique per plan and date (executed)
- age not stored: a birth date instead (executed)
- natural keys are UNIQUE alternates, not primary keys (email, VAT, member number)
- the freelancer question left open: the company link optional and listed as an open question
- nothing applied: no database file created
- the requirements left untouched

**eval-32-dbdiagram-barker-and-relational-from-design**
- files named for er-model and relational-model
- the ER page titled Barker ER Model
- a legend naming Barker notation and explaining its glyphs
- entities named singular UPPERCASE in soft-cornered boxes
- every attribute carries its # / * / o mark
- the three-way association drawn as an intersection entity with three binary relationships
- every relationship carries a lowercase role name at each end
- each end's optionality drawn: dashed may-be, solid must-be
- cell IDs are semantic and trace each entity to its table
- a UID bar on each relationship in a UID, and on no other
- every alternate key on the relational page, composite ones included
- microchip not drawn as a key while Q3 is open
- each FK path labelled with its column
- a provenance note naming the design on both pages
- the design left untouched

**eval-33-dbpropose-orphans-before-constraints**
- the full_name split is expand/contract, contract gated on the Reports add-on
- the reminder table marked as having no audit finding
- no finding id invented
- the design and both diagrams cited by path
- needs-data flags carried as open questions
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

**eval-35-container-hardening-review-socket-and-firewall**
- rotation for the committed key
- the read-only socket mount rated Critical, :ro called no protection
- Postgres on all interfaces bypasses ufw
- the privileged worker's replacement named (/dev/dri)
- mutable :latest references found
- the hardened proxy recorded as what works
- image findings handed to dockerfile
- no compose file, manifest, Dockerfile or script changed

**eval-36-container-debug-oom-localhost-crlf**
- no secret value echoed (kind and location only)
- OOMKilled read from the runtime, not inferred from 137
- the limit raised from the measured working set, not removed
- why localhost fails inside a container explained
- the Redis URL fixed to the service name
- the worker's identical Redis URL noticed
- CRLF line endings named as the migrate cause
- recurrence prevented with .gitattributes
- nothing claimed verified on the VM

**eval-37-docker-swarm-review-quorum-and-state**
- no secret value echoed (kind and location only)
- rotation to a new secret, not deletion
- two managers called no better than one (quorum)
- Postgres replicas on node-local volumes found
- depends_on ignored by stack deploy
- .env not read by stack deploy
- the default update config named (pause / stop-first) and rollback prescribed
- the routing mesh breaks the per-client rate limit
- registry auth missing from the deploy
- the gate stated failing with its conditions
- the worker recorded as what works
- no stack file, script, config or secret changed

**eval-38-threatmodel-review-design-abuse-and-fallback**
- no secret value echoed (kind and location only)
- the self-grantable delegation found (S25)
- the fail-open fraud-score fallback found (S22)
- the stale model checked against the partner API (S24/S27)
- what is working well is recorded
- no fixture document changed

**eval-39-threatmodel-design-abusers-and-traps**
- the system definition includes support and recovery
- requirements traced threat → requirement → test
- hashing the national ID declined as privacy (S16)
- caregiver delegation guarded against abuse and self-propagation
- impersonation treated as break-glass
- 'anonymised' export treated as a claim to test
- SMS-only recovery declined
- the lab webhook gets authenticity and freshness
- open questions listed
- requirements untouched and nothing built

**eval-4-teardown-finds-vacuous-test**
- does not re-report the refuted party-size finding

**eval-40-threatmodel-propose-contain-then-design-out**
- the live fail-open and SMS admin contained before redesign
- the self-grant eliminated by design, not monitored
- two independent mechanisms for large payouts
- the staging key rotated before it is removed
- the gate after the plan stated
- no secret value echoed (kind and location only)
- documents, spec and review untouched

**eval-41-appsec-review-inventory-and-secrets**
- rotation, not just removal, for the leaked key
- an endpoint inventory was built
- /api/v1 found absent from the spec (inventory reconciled)
- /api/v1 found unauthenticated
- mass assignment of role found
- CORS reflecting any origin with credentials found
- the /docs endpoint exposure found
- findings carry file:line evidence
- findings carry confidence tags
- what is working well is recorded
- no source, spec, manifest or env file changed

**eval-42-appsec-design-reshapes-the-quick-wins**
- JWT in localStorage declined for an HttpOnly cookie or short-lived token
- session lifetimes: idle and absolute timeouts
- CORS * declined for an exact allow-list
- receipts served from a sandbox origin or object storage, as attachments
- SVG uploads handled as active content
- partner keys in a header, never the query string
- partner keys hashed at rest, not readable by support
- double-submit CSRF replaced by a session-bound token or SameSite
- tenant enforced server-side in the query, not the frontend
- GraphQL introspection and playground off in production
- support impersonation audited and time-bound
- rate limits keyed on the partner or tenant, not IP
- a header contract
- security events and never-logged values defined
- abuse cases listed
- open questions listed
- no code written (design, not build)

**eval-43-appsec-propose-contain-then-fix-the-class**
- no secret value echoed
- the committed key rotated before it is removed
- exploitable holes contained before systemic rework
- /api/v1 retired or gated, and kept gone
- the class fix for injection: one query layer
- passwords migrated to a slow KDF by rehash on login
- code, spec, review and env untouched

**eval-44-hardening-review-mixed-estate**
- evidence cited by host path or resource
- each host's distro identified
- each host's own package tooling named
- Postgres graded as a service role, TLS included
- the unowned SUID binary flagged
- backup immutability gap found, restores flagged needs-data
- governance graded: deletion lock and owner tags
- what is working well is recorded
- the correct off-site AWS bucket credited, not flagged
- rotation recommended for the exposed password
- no secret value echoed (kind and location only)
- no evidence changed and no host-changing script written
- no active probe claimed

**eval-45-hardening-design-tier-aware-baseline**
- levels per tier, sandbox not held to prod rules
- per-platform mapping for AWS and on-prem
- exception process: approver not the requester, with expiry
- port knocking / port 2222 declined as controls
- SELinux kept enforcing; permissive only with an end date
- forced 30-day rotation declined
- backups isolated in another account and immutable
- developer SSH replaced by a private, just-in-time admin path
- nothing written but documents (no host-changing scripts or IaC)

**eval-46-hardening-propose-no-lockout**
- containment before structural and governance work
- the private admin path is live before public SSH is closed
- access-reducing steps carry a lockout guard
- the exposed DB password rotated before it is removed
- the public container closed in containment
- the vault immutability lock flagged as irreversible
- the trust graph respected (bastion and identity first)
- every step has verification and rollback
- evidence, review and baseline untouched

**eval-47-dbquery-workload-ranked-plans-read-indexes-weighed**
- workload ranked by total time: the N+1 lookup ahead of the slow monthly report
- coverage stated as a share of total time
- the report's misestimate traced to stale statistics (autovacuum disabled), fixed by ANALYZE
- open-orders list: (status, created_at) and seek paging
- the laptop plan not taken as production evidence
- the redundant proposed index on order_line(order_id) rejected
- the note index rejected on write cost
- product search needs a trigram (or full-text) index, not a B-tree on name
- prescriptions name how to verify them
- the dbaudit flags settled by id
- no secret value echoed
- never connected: no psql-staging call
- read-only: nothing but markdown written, no fixture file changed

**eval-48-dbarchitect-one-system-of-record-no-dual-writes**
- seat state has one system of record with a uniqueness constraint
- MongoDB not adopted on a proposal with no numbers
- derived stores fed by an outbox or CDC
- My tickets gets read-your-writes
- payment webhooks made idempotent
- zero lost paid orders met by synchronous replication
- dashboard staleness of 15 minutes stated
- unknown search load carried as an open question
- no secret value echoed
- nothing provisioned: only markdown written, no fixture file changed

**eval-49-peer-review-claim-omission-injection**
- the over-refund in payments/refunds.py found
- exactly one recommendation, and it is Request changes
- no working-tree file changed
- no commit, checkout or branch change

**eval-5-verdict-cuts-and-slices**
- F4 struck as an already-refuted repeat, citing the prior verdict
- verdicts written back to the ledger

**eval-50-pr-prep-splits-and-discloses**
- the status filter flagged as untested
- the wip and fix-typo commits to be folded
- no code changed: only markdown written
- no commit, branch or history rewrite

**eval-51-code-xray-hotspots-not-cold-giants**
- the generated schema_pb2.py excluded, never ranked
- the discount clone twins named, with their co-change
- the cold report builder left alone, on its change frequency, not made a target
- no per-person ranking or tally
- read-only: nothing in the repo changed
- the git repository untouched: no commit, branch, stash or staged change

**eval-52-test-review-would-it-fail**
- the May time bomb found: the default placed_on is today and ALICE's birth month is 5
- read-only: no fixture file changed, nothing but markdown added
- the nested repo's refs, HEAD and index untouched

**eval-53-concurrency-review-interleavings-and-replicas**
- the consumer fix is an idempotency key under a unique constraint or in the same transaction
- the daily job's fix is a single runner: lease, leader, CronJob or an atomic claim of the run
- the lock-guarded stats counter cleared, not reported as a defect
- read-only: nothing in the work tree or the PR description changed
- no commit, branch, stash or staged change in the fixture repo

**eval-54-review-retro-areas-not-people**
- the per-person ranking declined, with the area and change-type view offered
- no line pairs a person with a count, a duration or a rank
- unused imports proposed as a lint rule (ruff F401), not a checklist item
- the Ledgerly rate limit explained twice in threads proposed for the code or CLAUDE.md

**eval-6-compose-detects-real-services**
- meilisearch detected from the source
- elasticsearch NOT composed (stale env var, no client)
- pg_isready probe names user and database
- dependencies gated on health, not just start
- migrations gated as a one-shot dependency
- connection strings use service names, not localhost
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

**eval-26-pipelines-propose-keeps-prod-up**
- build-once lands before rollback-by-digest and progressive delivery (1/3)

**eval-27-acceptance-tests-red-for-the-right-reason**
- every new test is red on the unimplemented code (none passes) (2/3)
- tier stated (Standard) (2/3)

**eval-29-release-notes-translates-drops-and-leads-with-breaking**
- the range confirmed: v2.3.0..v2.4.0, 18 commits (1/3)
- the dropped count stated in the handoff (1/3)

**eval-30-dbaudit-postgres-dump-scored-not-fixed**
- runtime facts flagged needs-data, never graded (2/3)
- strengths recorded: the payment table (2/3)

**eval-31-dbdesign-sqlite-from-requirements-traps**
- the member subtypes mapped deliberately, with the choice stated (2/3)

**eval-33-dbpropose-orphans-before-constraints**
- the Critical handled before the name split (2/3)

**eval-39-threatmodel-design-abusers-and-traps**
- trust boundaries named (1/3)

**eval-41-appsec-review-inventory-and-secrets**
- findings mapped to the OWASP lists (2/3)

**eval-43-appsec-propose-contain-then-fix-the-class**
- the class fix for access: one authorisation / tenant-scoping layer (2/3)
- class guards in CI, handed to the pipelines skill (1/3)

**eval-44-hardening-review-mixed-estate**
- score arithmetic shown, capped by the Critical (2/3)

**eval-46-hardening-propose-no-lockout**
- decisions cite the theory (H-n) (1/3)

**eval-50-pr-prep-splits-and-discloses**
- size counted and compared with the ~400-line limit (2/3)
