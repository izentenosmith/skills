# Evals — measuring whether the skills actually work

These skills are prompts, and a prompt's claims about its own behavior are hypotheses until something checks them. This harness is that check: it runs each skill against a seeded fixture with known defects planted in it, and scores what the skill produced.

The headline result is in [benchmark.md](benchmark.md). The short version: on the assertions that test what the skills instruct, the six-stage pipeline scores **0.98** against **0.22** for the pre-session baseline; on core capability, **0.96** against **0.92**.

**Every eval now has a scored run.** Evals 6–14 and 16–34 were first run on 2026-10-25 (iterations 6, 7, 9 and the combined 10 in the workspace): one with-skill run each, three for evals 11–13, against a no-skill baseline — none of those skills exists at `3b71f54^`. Across all 35 evals, **0.94** against **0.49** on delta and **0.99** against **0.85** on capability. The weakest results are listed in the root [README](../README.md#do-they-work). Evals 27, 31 and 33 were re-run three times after their skills were fixed (iteration 11, combined with iteration 6's baselines as iteration 12). `benchmark.md` was aggregated from iterations 1, 2, 5, 6, 7, 10 and 12; iterations 3 and 4 are left out, as in the recorded result, because iteration 4 ran the skills from before the ledger grammar.

## Layout

```
evals/
├── setup.sh        build fixture venvs + the incident git history (run once)
├── evals.json      one entry per eval: a prompt and a skill, or (eval 15) a runner
├── run.py          dispatch the runs headless, then grade + aggregate
├── grade.py        assertions → grading.json per run
├── aggregate.py    grading.json → benchmark.md/json
├── benchmark.md    the recorded result
├── controls/       reproducible controls (make_controls.py: evals 8-14 and 16-34; eval15.py: the loop)
└── fixtures/       the seeded repos and documents the skills work against
```

## The fixtures

### The pipeline fixture (evals 0–5)

A small Python reservations service. Bookings go through `BookingService.submit`; constraint rules live in `rules.py` and return a violation code or `None`. Five variants, each seeded for the stage that uses it:

| Fixture | Seeded with | Used by |
|---|---|---|
| `base` | clean service, green suite | architect-deep-dive, agent-brief |
| `tdd` | `+ .workflow/brief.md` | tdd, acceptance-tests (eval 27) |
| `refactor` | `+` a sloppy cutoff rule, `+` a prior-pass ledger | refactor-review |
| `teardown` | `+` a cutoff rule that **ignores account config**, `+` a **vacuous test** that hides it | devils-advocate |
| `verdict` | `+` four unadjudicated findings: two provable, one a re-report of an already-refuted claim, one unprovable | tyr-verdict |

The planted defects are the point. `check_cutoff` accepts a `config` argument and never reads it, so the configurable-window criterion is unimplemented — and `test_cutoff_window_reads_from_account_config` passes anyway, because it asserts on a slot inside *both* the configured and the default window. A stage that reports a green suite as evidence of correctness fails the eval.

### `compose` (eval 6)

A Flask order-desk service — `shopdesk` — with Postgres, RQ job queues on Redis, and Meilisearch. Nothing is executed; it is graded from the files the skill writes. Four things are planted:

| Planted | Catches a run that… |
|---|---|
| `ELASTICSEARCH_URL` in `.env.example`, marked deprecated, **with no client anywhere in the code** | composes services by reading env vars instead of the source |
| Meilisearch reached from `shopdesk/search.py` only — not the main app module | stops looking after the obvious dependencies |
| Redis backs **RQ queues**, so eviction loses jobs | reaches for `allkeys-lru` out of cache habit |
| `shopdesk/migrate.py` must finish before the API starts | gates on `service_started` and races the schema |

### `incident` (eval 7)

A resolved outage in a ledger service: a git repository with backdated history, plus four documents of varying reliability (incident report, alert log, chat export, status page). Six things are planted — the triggering commit sits **nine days before** the outage window, two sources **contradict** on detection time, and the incident report both **blames a named engineer** and **demands specific remediation**. The full list is in [fixtures/incident/README.md](fixtures/incident/README.md).

The repository is built by `make-history.sh` rather than committed, because a nested git repo inside this one is a gitlink and behaves badly. `setup.sh` runs it.

**The seeded ledgers are written as the *old* pipeline would have left them** — prose entries, no ids, no `Promote if:` or `Reopens only if:` conditions. This matters: an earlier version of these fixtures carried those conditions, which meant the baseline could simply read the new skills' rules out of the input and follow them. Removing them dropped baseline scores by roughly half. **Never put an instruction the skill is supposed to produce into the fixture it reads.**

### `hotfix-*` and `incident-*` (evals 8–14)

Six small repos in six shapes, so the two response skills have to discover their environment rather than recognise it. The answer keys live **outside** the fixture folders — `fixtures/<name>.answers.md` — because everything inside a fixture folder is copied into the run.

| Eval | Skill | Fixture | The trap |
|---|---|---|---|
| 8 | hotfix | `hotfix-node` | a rounding bug in a shared helper with a second caller and an inline copy; CI runs `test:ci`, not `npm test`; it's money, so strict mode |
| 9 | hotfix | `hotfix-jvm` | integer division in a pager with two callers; no build tool — `./run-tests.sh`; merge requests and a staging step |
| 10 | hotfix | `hotfix-script` | an off-by-one in a script with **no tests**: the proof has to be a runnable check that fails on the original |
| 11 | hotfix | `hotfix-node` | an outage prompt: route to incident-fix and change nothing |
| 12 | incident-fix | `incident-webapp` | `ops/flags` and `ops/deploy` record every call: none may happen unconfirmed; the flag should outrank the rollback |
| 13 | incident-fix | `incident-batch` | `data/prod.db` must stay byte-identical; 12 wrong orders (cancelled excluded); invoices already issued; repair as a dry-run, backed-up artifact — **executed** on throwaway copies: no flags must change nothing, an apply flag must fix exactly the 12 and leave a backup |
| 14 | incident-fix | `incident-library` | no deploy step — containment is a yank and an advisory; the corrupted data lives with consumers |

`hotfix-jvm` needs a JDK (`javac`, `java`) and `hotfix-node` needs Node 22+, both to run and to grade; nothing else needs setup. **Controls** ([`controls/make_controls.py`](controls/make_controls.py), see [Negative controls](#negative-controls)): a reference answer scores every assertion on all seven, a do-nothing answer fails every delta assertion except the safety invariants it passes by doing nothing (no production call, no file changed), and a plausible-but-wrong answer per eval fails the assertion it was built to game. **First run (n=1):** see [benchmark.md](benchmark.md).

### `harness/loop.py` end to end (eval 15)

Every other eval scores one skill answering one prompt. Eval 15 scores the closing-loop harness itself: `"runner": "loop"` in `evals.json` makes `run.py` launch `harness/loop.py` instead of a `claude -p` call.

The run's repo is a git work tree whose only commit is the `base` fixture, with the `teardown` fixture laid over it uncommitted. `--base HEAD` therefore hands the teardown exactly the cutoff change and its vacuous test. The `.venv` is excluded through `.git/info/exclude`, so neither the diff nor redgreen's snapshots carry it. The harness and every skill are staged to a temp directory first, like the single-skill runs. `loop.py`'s stderr log becomes `outputs/response.md`, and its exit code goes in `run.json`.

| Assertion | Kind |
|---|---|
| exit 0 (GO) or 3 (ESCALATED), a verdict either way | capability |
| `ledger.py check --against` the fixture's ledger is clean | capability |
| the suite is green at the end | capability |
| a CONFIRMED finding names `check_cutoff` ignoring account config | delta |
| a CONFIRMED finding names `test_cutoff_window_reads_from_account_config` as vacuous | delta |
| the refuted party-size *boundary* claim is not confirmed again (judged on Target / Claim; criterion 5, both codes surfacing, is a legitimate finding) | delta |
| GO, **and** the defect is fixed through `BookingService.submit`: a 240-minute window rejects a slot 180 minutes out, a 60-minute one accepts 90, the default rejects 90 | delta |
| at least one remediation slice closed (loop.py closes one only after redgreen's proof) | delta |

The fix is probed with every hour open, so the result does not depend on the time of day. A GO is not taken on the loop's word: the stub-driven control below reaches GO without fixing anything.

**First live run** (2026-10-15, one rep, $6.70, 24 minutes): **8/8**. The loop used all three iterations. Iteration 1 confirmed both planted defects among nine findings. Iterations 2 and 3 closed 14 slices, each after red→green proof, and found smaller defects in the fixes themselves. It ended GO with four minors tracked. The probe confirms that `check_cutoff` now reads the account window, and the suite grew from 7 tests to 36. As first written, the party-size assertion failed this run on a legitimate finding (criterion 5). It now requires the boundary claim.

There is no baseline: `harness/loop.py` does not exist at `3b71f54^` or `dd2a41c`, and `run.py` says so instead of inventing a no-harness run. A live run costs about $4 and 15–40 minutes; its `timeout` in `evals.json` is 3600 s.

### `net-*` (evals 16–20)

One eval per networking skill. Two estates: **Northwind** (eval 16, raw evidence to audit) and **Contoso** (evals 18–20, one shared target model: the same `design/topology.json` and the same draw.io views in all three, so the stages agree with each other the way the workflow expects). Eval 17 is a third, Fabrikam, because a design is graded from requirements, not from a model. Answer keys are `fixtures/net-<name>.answers.md`, outside the folders.

| Eval | Skill | Fixture | The trap |
|---|---|---|---|
| 16 | netaudit | `net-audit` | Terraform azurerm hub-and-spoke plus an IOS edge: RDP from `*` (Critical), an analytics spoke on the office's own range behind the VPN, a dev spoke copied from prod, one NVA and one non-active-active gateway on the critical paths, and an IPsec PSK and SNMP community that **must never appear in any output** |
| 17 | netdesign | `net-design` | Utrecht owns 10.0.0.0/12, so the habitual `10.0.0.0/16` hub and AKS's default service CIDR both collide; the acquirer's ranges and the staff pool are not ours; DR must get its own space; PCI needs its own zone. Graded by parsing every CIDR in the run's `topology.json` |
| 18 | netdiagram | `net-diagram` | a cloud-only model with one inferred on-prem node: no physical view may be invented, cell IDs must equal model IDs, the inferred node must be drawn as inferred, and arrows must be exactly the allow flows. The `.drawio` XML is parsed, not grepped |
| 19 | netpropose | `net-propose` | an uncapped 7.9 hiding one open Critical; a renumbering coupled to an on-prem BI export; a network whose disuse is only the owner's belief; a residual κ=1 the design could not fix. The Critical must be contained before the renumbering, by position in the cut-over |
| 20 | netblueprint | `net-blueprint` | a complete, consistent proposal marked **Proposed** with no acceptance: the package must not be built |

Nothing is executed against a network, and nothing needs setup; eval 18 and the controls use only the standard library's XML and `ipaddress`. The baseline is a no-skill run: none of the five skills existed at the default baseline ref.

**Controls** (in `controls/make_controls.py`): a reference answer passes every assertion; a do-nothing answer fails every delta assertion except the safety invariants it passes by doing nothing; each plausible-but-wrong answer fails exactly what it was built to fail.

| Eval | Control | All | Delta | Fails |
|---|---|---:|---:|---|
| 16 | reference | 18/18 | 13/13 | — |
| 16 | do-nothing | 2/18 | 2/13 | everything but "no secret reproduced" and "no IaC" |
| 16 | `wrong-echoes-secret` — a full audit that quotes `shared_key = "…"` as evidence | 17/18 | 12/13 | no secret value reproduced |
| 16 | `wrong-gut-score` — every finding, then "about 5/10" and "the gate is not met" | 16/18 | 11/13 | score arithmetic and cap; gate condition by condition |
| 17 | reference | 15/15 | 10/10 | — |
| 17 | do-nothing | 1/15 | 1/10 | everything but "no IaC" |
| 17 | `wrong-overlaps-onprem` — hub on 10.0.0.0/16, AKS service CIDR left at 10.0.0.0/16 | 13/15 | 9/10 | no Azure range overlaps…; AKS ranges clear of the exclusions |
| 17 | `wrong-dr-copy` — North Europe reuses prod's 10.33.0.0/16 "for a clean failover" | 13/15 | 9/10 | no overlap inside the plan; DR gets its own space |
| 18 | reference | 12/12 | 10/10 | — |
| 18 | do-nothing | 2/12 | 2/10 | everything but "no physical view" and "model untouched" |
| 18 | `wrong-invents-physical` | 11/12 | 9/10 | no physical view invented |
| 18 | `wrong-generated-ids` — right pages and labels, draw.io-generated cell IDs | 7/12 | 5/10 | node IDs; arrows are the allow flows; inferred node dashed (and CIDR labels, zone badges) |
| 19 | reference | 13/13 | 10/10 | — |
| 19 | do-nothing | 2/13 | 2/10 | everything but "inputs untouched" and "no IaC" |
| 19 | `wrong-structure-first` — same register, SSH rule deleted "with the cleanup" as step 5 | 12/13 | 9/10 | the Critical contained before structural work |
| 19 | `wrong-no-rollback` — a numbered list with no validation, rollback or blast radius | 12/13 | 9/10 | every step names validation, rollback and blast radius |
| 20 | reference | 9/9 | 8/8 | — |
| 20 | do-nothing | 5/9 | 5/8 | asks for acceptance; names where it comes from; says nothing was produced |
| 20 | `wrong-builds-anyway` — notes the proposal isn't accepted, builds the package anyway | 5/9 | 4/8 | no network-design.md; no accepted topology.json |

Eval 20 is the one where doing nothing scores well: five of its eight delta assertions are "did not build". That is the point of the eval — the skill's job here is to stop — and the three that the do-nothing control fails are the ones a stopping run has to earn by saying why. **First run (n=1):** see [benchmark.md](benchmark.md).

### `tf-*` and `ci-*`: terraform and pipelines (evals 21–26)

Both infrastructure skills run in three modes, so each gets one eval per mode. Review fixtures are small repos seeded with defects; Design fixtures are a requirements document whose traps sit in what the requirements *ask for*; Propose fixtures are the review repo plus a finished review and a target design. Answer keys live outside the folders, as `fixtures/<name>.answers.md`.

| Eval | Skill · mode | Fixture | The trap |
|---|---|---|---|
| 21 | terraform · Review | `tf-review` | a static AWS key and a DB password in code — record kind and location, **never the value**; dev and prod point at **the same bucket and key** (only a state map shows it); prod copied from dev and silently missing `storage_encrypted`; `count`-keyed databases; Postgres open to the world; `?ref=main`; `-auto-approve` from CI and laptops |
| 22 | terraform · Design | `tf-design` | leadership asks for "one workspace per environment, all in one bucket"; payments is PCI; a database was once deleted and recreated; admins apply from laptops |
| 23 | terraform · Propose | `tf-propose` | the key must be **rotated before** it is removed; containment before refactors; DB protection before the `count` → `for_each` moves; every move a `moved` block with an expected plan of zero destroys; state migrated with a backup, not `state mv` |
| 24 | pipelines · Review | `ci-review` | `pull_request_target` running fork code with `NPM_TOKEN`; a Slack webhook committed in `deploy.yml` (never echo it); the deploy workflow runs **independently of the test workflow**; the image rebuilt per environment with baked config; staging and prod deployed by different mechanisms; an `@master` action holding prod credentials |
| 25 | pipelines · Design | `ci-design` | the team wants per-environment builds "so config is baked in"; compliance wants an approval meeting before **every** deploy; a 12-minute integration suite; two active-active prod regions; upcoming column renames |
| 26 | pipelines · Propose | `ci-propose` | rotate the webhook before removing it, treat `NPM_TOKEN` as exposed; contain the untrusted trigger first; build-once before rollback-by-digest and canary; run the new pipeline alongside the old; settings that live in the GitHub UI named in rollback because a git revert doesn't undo them |

Grading is from files and the response; nothing is executed against a cloud or a CI system. Two checks run tools: `actionlint` on any workflow skeleton eval 25 writes, and a scan that no backend was initialised (`.terraform/terraform.tfstate`) in 21 and 23. `terraform init -backend=false` and the lockfile it writes are allowed. **Safety invariants**, which the do-nothing control passes by doing nothing: no secret value echoed (21, 24), no code, review or design file changed (21, 23, 24, 26), no backend initialised (21, 23), no `resource` blocks written by Design (22), and no invalid workflow skeleton (25).

**Controls** ([`controls/make_controls.py`](controls/make_controls.py), `--only 21 22 23 24 25 26`):

| Eval | Reference | Do nothing | Plausible-but-wrong controls, and what catches each |
|---|---|---|---|
| 21 | 20/20 | 3/20 (the 3 safety invariants) | `wrong-echoes-secret` quotes the key: 19/20 · `wrong-fixes-it` edits the rule while reviewing: 18/20 · `wrong-file-by-file` reviews each backend alone, so no state map, no shared state, no drift: 17/20 |
| 22 | 17/17 | 1/17 | `wrong-adopts-workspaces` does what leadership asked: 15/17 · `wrong-builds-it` writes a `resource` block: 16/17 |
| 23 | 14/14 | 2/14 | `wrong-deletes-key-only` (no rotation, `state mv`, renames without `moved`): 11/14 · `wrong-refactor-first` moves databases before containing or protecting: 12/14 |
| 24 | 19/19 | 2/19 | `wrong-echoes-token`: 18/19 · `wrong-file-by-file` misses the ungated deploy and the split mechanisms: 17/19 · `wrong-fixes-workflows`: 18/19 |
| 25 | 18/18 | 1/18 | `wrong-keeps-builds-and-cab` keeps per-environment builds and the meeting: 14/18 · `wrong-big-bang` deploys both regions at once: 17/18 · `wrong-invalid-skeleton` fails actionlint: 17/18 |
| 26 | 12/12 | 1/12 | `wrong-big-bang-cutover` (no parallel run, rollback = git revert): 10/12 · `wrong-canary-first`: 11/12 · `wrong-deletes-token`: 11/12 |

Building these controls caught four of my own assertions being too loose before any run was spent. The proposal-sequence check matched the word "order" in a heading, so a findings table at the top decided the order. A prod-isolation check was satisfied by payments' own state. Any mention of Helm values counted as "config not baked in". A rotate-before-remove check accepted a rotation of a *different* token on a neighbouring line. **First run (n=1):** see [benchmark.md](benchmark.md).

### `acceptance-tests` on the `tdd` fixture (eval 27)

Stage 3 of the pipeline. It reuses the `tdd` fixture unchanged: the reservations service and its brief, whose five acceptance criteria describe a cutoff that does not exist yet. The prompt is "Write the acceptance tests for the build plan in .workflow/brief.md." The answer key is [fixtures/acceptance-tests.answers.md](fixtures/acceptance-tests.answers.md).

| Trap | Catches a run that… |
|---|---|
| Criteria 2 and 4 (outside the window accepted; the edge accepted) already hold, because nothing is rejected for timing | writes acceptance-only tests: green now, green with the feature deleted |
| The default window is 120 minutes; a 240-minute config test with a slot 30 minutes out passes either way (the test `teardown` plants) | proves the config criterion with a slot inside both windows |
| No clock seam: the edge can only be approached to within the call's microseconds | gives the edge a minute of slack, so it tests criterion 2 again |
| Key interfaces name `reservations.rules` and `ACTIVE_RULES` | unit-tests `check_cutoff` or `Booking.validate` instead of going through `submit` |
| `submit` and `Rejected` already exist; nothing needs declaring | invents a public name and is red on `ImportError` |
| Opening hours 11:00–23:00 against slots built from `datetime.now()` | is red for `VENUE_CLOSED` at night. **Not graded**: the grader pins local noon |

**Graded by running the tests.** The tests the run added are found by comparing pytest's collection with the fixture's, then run three ways:

- On the run's own code, every new test must be red, and red on behavior: an assertion, `DID NOT RAISE` or `Rejected`. A collection, import or attribute error does not count.
- With a correct cutoff rule laid over the run's `reservations/`, every new test must pass. The rule reads `cutoff_minutes` (default 120), has an exclusive boundary and reads `now` to the second. It is appended to `ACTIVE_RULES`, or put first if the tests expect that order.
- With each of three mutants laid over the repo, a test that passed on the reference must fail. The mutants are a hard-coded 120-minute window, a whole-minute inclusive boundary, and a `validate` that keeps only the first violation.

The recorded **Command:** is executed too and must collect exactly the new tests. Static checks: no import of `reservations.rules` or `reservations.booking` (AST, not grep); the doubles are reused; each of the five criteria is mapped once, by a test id the run added or as not acceptance-testable with a reason; a Revisions entry; Standard tier; handoff to tdd. A probe through `submit`, with every hour open, confirms no cutoff was implemented. That is the one safety invariant.

Every pytest the grader starts runs with `TZ` set so that local time is noon (the same computation as eval 15's CI step), so the result does not depend on the hour. Checked by grading at forced local hours 0–23. The controls score the same at every hour. A variant whose tests don't open the venue's hours changes score at 14 of the 24 hours unpinned (20:00 to 09:59), and passes everything when pinned. When a run has no `.venv` (the controls), the grader falls back to `fixtures/tdd/.venv`, so `setup.sh` must have run.

**Controls** (`make_controls.py --only 27`):

| Control | All | Delta | Fails |
|---|---:|---:|---|
| reference | 18/18 | 12/12 | — |
| do-nothing | 2/18 | 1/12 | everything but "pre-existing tests green" (capability) and "no implementation" (the safety invariant) |
| `wrong-implements-it`: the same tests, then `check_cutoff` written to make them pass | 16/18 | 10/12 | every new test red; no implementation |
| `wrong-green-guards`: criteria 2 and 4 tested by acceptance alone | 17/18 | 11/12 | every new test red (two pass now) |
| `wrong-vacuous-config`: 240-minute window, slot 30 minutes out | 17/18 | 11/12 | the config test kills the hard-coded mutant |
| `wrong-import-error`: imports an invented `CUTOFF_WINDOW` from `reservations.api` | 13/18 | 10/12 | red for the right reason; green on the reference; all three mutants, because a test that cannot load kills nothing |
| `wrong-reaches-internals`: the both-codes test calls `Booking.validate` directly | 17/18 | 11/12 | no internals |
| `wrong-three-of-five`: five tests, but only three criteria mapped in the brief | 17/18 | 11/12 | each criterion mapped exactly once |

`wrong-implements-it` writes the usual exclusive comparison against `datetime.now()`. Its edge test is then red even with the rule in place, because the slot is a few microseconds inside the window by the time the rule runs. A test built at exactly `now + 120 min` therefore depends on how the implementation reads the clock, which is why the grader's reference reads it to the second. **First run (n=1):** see [benchmark.md](benchmark.md).

### `dockerfile` (eval 28)

`invoicer`, a small Express + TypeScript service (pnpm, better-sqlite3, Handlebars, SQL migrations run at startup) with a Dockerfile that ships but is badly built. The prompt is the user's complaint, not a checklist: *"Our Docker image for this service is over 1 GB and every commit rebuilds everything from scratch. Fix it."* The skill runs in **Repair** mode. Its answer key is [fixtures/dockerfile.answers.md](fixtures/dockerfile.answers.md), outside the folder.

| Planted | Catches a run that… |
|---|---|
| `.nvmrc` 20.11.1 and `packageManager: pnpm@9.12.3`, under `FROM node:latest` and `npm install -g pnpm` | pins to habit (`node:20-slim`, `lts`) rather than to what the repo declares |
| `COPY . .` before an unfrozen install | copies source first, or installs without `--frozen-lockfile` and a cache mount |
| better-sqlite3, a native module | installs `node_modules` in a `$BUILDPLATFORM` stage (or on alpine) and copies it into the amd64 slim runtime |
| `migrations/` and `templates/` read relative to `dist/` | ships `dist` and `node_modules` only, so the image crashes at startup |
| The source listens on `PORT ?? 8080` and serves `/healthz`; the Dockerfile exposes 3000 and checks `/health`; the README says 3000 | trusts the old file or the README, or curls from a slim image that has no curl |
| Runs as root; the app writes `data/` | adds `USER` but leaves the data directory root-owned |
| `ENV PDF_RENDER_API_KEY=eval-fake-…` | moves it to `ARG`, or quotes it |
| k8s `nodeSelector: amd64`; the team runs `make push` on M-series Macs | never states the mismatch, or never puts `--platform` where `make push` will use it |
| A curated, incomplete `.dockerignore` | replaces it from a template and drops `loadtest/`, `deploy/`, `Makefile` |
| A local `.env` with two fake secrets that today's `COPY . .` bakes in; `.env.example` must stay | writes `.env*` and excludes the template |

**Graded from files, never built.** The Dockerfile is parsed stage by stage (global `ARG`s substituted into `FROM`, `FROM <stage>` chains followed), and the `.dockerignore` is evaluated with Docker's matching rule (the last pattern matching a path or one of its parents decides, `!` re-includes) on probe paths, before and after. Both files are evaluated only at the context root, where Docker's real semantics and the skill's dockerignore.md agree. Step 4 is checked for the commands and for honesty: either raw output (`uid=…(`, `transferring context:`, `=> CACHED [`, a `docker images` row, a bare `linux/amd64` line) or a plain statement that docker was unavailable, never both, and never "should work". **Safety invariant**, which the do-nothing control passes by doing nothing: no planted secret value in the response or any written file.

**Controls** (`--only 28`): every wrong control scores 19/20 and fails only the assertion it was built to fail.

| Control | All | Delta | Fails |
|---|---:|---:|---|
| reference | 20/20 | 14/14 | — |
| do-nothing | 3/20 | 1/14 | everything but "never echoed" and two capability checks it already meets (pnpm; build inputs in the context) |
| `wrong-runs-as-root` — no `USER` | 19/20 | 13/14 | non-root user owning its data directory |
| `wrong-source-before-install` — `COPY . .` before the frozen install | 19/20 | 14/14 | dependencies before source *(capability)* |
| `wrong-replaces-dockerignore` — a good template, curated entries dropped | 19/20 | 13/14 | .dockerignore extended, curated entries kept |
| `wrong-bakes-key` — `ARG` + `ENV PDF_RENDER_API_KEY=$…` | 19/20 | 13/14 | no secret in ENV, ARG or a copied env file |
| `wrong-port-and-health` — `EXPOSE 3000`, healthcheck on `:3000/health` | 19/20 | 13/14 | port and health from the source |
| `wrong-curl-on-slim` — right port and route, `curl` on a slim image | 19/20 | 13/14 | port and health from the source |
| `wrong-uses-latest` — `node:lts-slim` | 19/20 | 13/14 | pinned to what the repo declares |
| `wrong-dist-only` — no `migrations/`, `templates/` | 19/20 | 13/14 | runtime ships only dist, prod deps and runtime assets |
| `wrong-buildplatform-deps` — deps stage on `$BUILDPLATFORM` | 19/20 | 13/14 | better-sqlite3 installed on the target platform |
| `wrong-claims-verified` — "All checks pass; it should work" | 19/20 | 13/14 | Step 4 with commands, observed or docker's absence stated |
| `wrong-rewrite-unnamed` — new file first, defects never listed | 19/20 | 13/14 | defects named before the fix |
| `wrong-env-star` — `.env*`, no re-include | 19/20 | 13/14 | .env out, .env.example in |
| `wrong-echoes-secret` — quotes the key in the defect list | 19/20 | 13/14 | never echoed |

Building the controls tightened four assertions before any run. Do-nothing passed "production dependencies" because the old file sets `ENV NODE_ENV=production`, though only *after* its install. Paired defect markers (`/health` vs `/healthz`) missed when a sentence wrapped. "No Docker HEALTHCHECK" read as "no docker". And the platform check rejected a correct `PLATFORM ?= linux/amd64` + `--platform $(PLATFORM)` in the Makefile. Alternative correct shapes are probed too, and all pass: alpine in every stage with `pnpm fetch`, tini and a `wget` healthcheck; a `$BUILDPLATFORM` stage that only runs `tsc`. Known strictness: a distroless `nodejs20` runtime fails the 20.11 pin, because its tag cannot carry the minor. **First run (n=1): 0.79 against 0.79 for no skill** — the run quoted the planted key in its rotation warning, and named only 3 of 8 Step 4 commands.

### `release-notes` (eval 29)

Beacon is an uptime-monitoring SaaS. The fixture is a git repository with squash-merged history and tags `v2.2.0`, `v2.3.0` and `v2.4.0`, plus three unreleased commits after the last tag. Next to it is `issues/`, an export of the tracker issues the commits link to. As with `incident`, `make-history.sh` builds the repo rather than committing it, and `setup.sh` runs the script. The answer key is [fixtures/release-notes.answers.md](fixtures/release-notes.answers.md). `repo/CHANGELOG.md` is written in commit-subject style. It is a lure toward transcription, not an example of the right style.

| Planted (v2.3.0..v2.4.0, 18 commits) | Catches a run that… |
|---|---|
| a feature whose subject is `MaintenanceWindowScheduler + maint_windows_v2 flag [PLAT-412]` | copies the class, the flag or the ticket into the notes |
| a perf PR whose body says "I haven't benchmarked it" | invents a percentage or an "up to" |
| a perf PR whose body has a staging measurement (48 s → 11 s) | leaves out a measured figure, or uses it without naming its source |
| two fixes written as causes (`guard null tz`, `off-by-one`); their issues state the symptoms | describes the cause instead of what the user saw |
| a one-line `chore(api)` that drops the list endpoints' default page size from 500 to 50 | misses that it is breaking, calls the release Minor, or lists it below the features |
| `/v1/webhooks` deprecated, removed 2027-03-31, replaced by `/v2/hooks` | gives the deprecation with no date or no replacement |
| Slack thread replies shipped in #252 and reverted in #265, both inside the range | announces a feature that did not ship |
| a `saml-verify` bump that patches an SSO sign-in CVE, next to eslint/vitest bumps, CI, tests, docs, lint and a refactor | writes "bumped saml-verify" instead of the effect, or lists the noise |
| SMS alerts, a favicon fix and `2.5.0-dev` after the `v2.4.0` tag | ranges to `HEAD`, or takes the date from anything but the tag |

The grader separates **the notes** from **the handoff**. The notes are the markdown the run wrote: a new file, the lines it added to an existing one such as `CHANGELOG.md`, or a non-response file in `outputs/`. When there is no such file, they are the part of the response from its 2.4.0 heading to its help link. Identifiers, numbers, ordering and omissions are judged on the notes only, because the handoff is expected to name PRs, the dropped commits and the source of each figure. Capability (7): notes written, maintenance windows and the page-size change announced, a summary, the deprecation with date and replacement, a help link, nothing after the tag. Delta (13): the range and count confirmed, the tier stated as Major, a header with the exact version and the tag's date, breaking above the features with the action, no internal identifiers, no number on the unmeasured improvement, the measured figure used with its source named, fixes as symptoms, the reverted feature absent, the CVE as its effect, the noise dropped, the dropped count stated, and the unquantified improvement named.

**Controls** (`--only 29`):

| Control | All | Delta | Fails |
|---|---:|---:|---|
| reference | 20/20 | 13/13 | — |
| do-nothing | 0/20 | 0/13 | everything; nothing is free, since every omission check needs notes to exist |
| `wrong-commit-transcript`: the 18 commit subjects under `## v2.4.0 (2026-10-14)`, with the range and count stated | 6/20 | 3/13 | identifiers, symptoms, reverted feature, CVE effect, noise, breaking-first, tier, measured figure, dropped count, unquantified list (plus four capability checks). It passes range, header and "no number on the timeline", which a transcript gets right |
| `wrong-invented-number`: the reference, with the timeline "up to 40% faster" and "every improvement carries a figure" in the handoff | 18/20 | 11/13 | no number on the unmeasured improvement; the unquantified improvement named in the handoff |
| `wrong-breaking-last`: the page-size change listed last under Fixed, the tier called Minor | 18/20 | 11/13 | breaking above the features with the action; tier stated as Major |
| `wrong-ranges-to-head`: `v2.3.0..HEAD, 21 commits`, dated 21 October, announces SMS alerts and the favicon fix | 17/20 | 11/13 | range and count; header date; the work after the tag (capability) |
| `wrong-announces-reverted`: the reference plus "Threaded Slack updates" under New | 19/20 | 12/13 | the reverted feature not announced |
| `wrong-names-the-bump`: the security entry is "Updated saml-verify from 3.1.2 to 3.1.4 (CVE-2026-41207)" | 19/20 | 12/13 | the CVE published as its effect |

Building the controls caught three loose spots. A `\b2\.4\.0\b` pattern does not match `v2.4.0`, because there is no word boundary between `v` and `2`, so every header written as `v2.4.0` failed. A tier check that accepted "Major" near "breaking" was passed by a heading such as "Major breaking change" with no tier stated. A help-link match that returned a truncated line cut the response-only fallback mid-line. Throwaway variants were checked as well. A number wrapped onto the timeline entry's second line, and the export figure with no source in the handoff, each fail exactly their one assertion. Notes with no "New" heading, where the feature's own bold line marks the features, grade 20/20. So do notes placed in `outputs/`, in a new file, or in the response before or after the handoff. **First run (n=1):** see [benchmark.md](benchmark.md).

### `db-audit` and `db-design`: dbaudit and dbdesign (evals 30–31)

The two database skills that start a workflow. The audit fixture is an existing database as raw evidence; the design fixture is a requirements document whose traps sit in what it asks for. Answer keys are `fixtures/db-audit.answers.md` and `fixtures/db-design.answers.md`, outside the folders.

| Eval | Skill | Fixture | The trap |
|---|---|---|---|
| 30 | dbaudit | `db-audit` | a PostgreSQL 16 `pg_dump --schema-only` split by object type, two migrations and a service config. The Critical is the **PostgreSQL** form of the multi-row trigger defect: a statement-level trigger that reads `new_lines … LIMIT 1`, which a run hunting for T-SQL's `SELECT @x = … FROM DELETED` misses. There's also a table with no PK; an FK a migration dropped; phone1..phone3; an EAV table; money in `double precision`; an unindexed FK beside a redundant index; a trigger with hidden side effects; and two passwords (config file, dblink string) that **must never appear in any output**. `customer_email` on the order is a 3NF *candidate*, not a graded violation; the README's row counts, slowness and usage are needs-data. `payment` is the well-designed table |
| 31 | dbdesign | `db-design` | the requirements name **SQLite**, ask for "the list of attendees" (a many-to-many), prices that change but must be kept per month, members' **age**, a stored booking **total**, individuals *or* companies (subtypes), unique emails, VAT numbers and card numbers (alternate keys), and leave open whether every individual works for a member company. The run's DDL is **executed in sqlite3** and read back from the catalog |

Eval 30 parses the audit rather than grepping it. Findings come out of its markdown tables, and each row must carry a confidence tag, a theory citation, a severity and a `file:line`. Every `file:line` it cites is resolved against the fixture, so a line that doesn't exist fails. Four planted defects must be cited inside their own statement's line range, so `schema.sql:1` for everything fails. A runtime word (row counts, "slow", `pg_stat`, "still used") in a graded, non-🔬 finding row fails the needs-data assertion. The gate's four conditions from `harness/dbreview.py` (score ≥ 9.0, no open Critical/High, not unused or a copy, 🔬 ≤ 10 %) must each sit in a clause of their own. A `CREATE TABLE` for any table the dump doesn't have counts as prescribing.

Eval 31 takes the run's added `.sql` files, or else the ```` ```sql ```` blocks of the one document with the most `CREATE TABLE`s. It executes them statement by statement in an in-memory SQLite with `PRAGMA foreign_keys = ON`, then reads `table_info`, `foreign_key_list` and `index_list` back. One statement SQLite rejects fails the engine assertion without hiding the rest of the design. **Safety invariants**, which the do-nothing control passes by doing nothing: 30 echoes no secret, changes no fixture file and designs no table; 31 creates no database file and leaves the requirements untouched.

**Controls** ([`controls/make_controls.py`](controls/make_controls.py), `--only 30 31`):

| Eval | Control | All | Delta | Fails |
|---|---|---:|---:|---|
| 30 | reference | 20/20 | 14/14 | — |
| 30 | do-nothing | 3/20 | 3/14 | everything but the three safety invariants |
| 30 | `wrong-echoes-secret` — quotes `password = …` from the config as evidence | 19/20 | 13/14 | no secret value echoed |
| 30 | `wrong-gut-score` — every finding, then "about 4/10" | 18/20 | 12/14 | score with p, base and the 2.0 cap; gate condition by condition |
| 30 | `wrong-fixes-schema` — the full audit, plus the missing FK re-added to `schema.sql` | 19/20 | 13/14 | no DDL, migration or config changed |
| 30 | `wrong-runtime-as-fact` — "largest table, integer key near its ceiling, export slow" as a ✅ High finding, the 🔬 flags for them dropped | 19/20 | 13/14 | runtime facts flagged needs-data, never graded |
| 30 | `wrong-prescribes` — the audit plus a `## Target schema` with `CREATE TABLE customer_phone` | 19/20 | 13/14 | evaluates and stops: no target table |
| 30 | `wrong-vague-evidence` — the same findings, every evidence cell pointing at line 1 of its file | 19/20 | 13/14 | evidence points at the planted defects |
| 30 | `wrong-3nf-graded` — `customer_name`/`customer_email` graded ✅ Medium as a 3NF violation | 19/20 | 13/14 | flagged as a 3NF candidate, not graded |
| 31 | reference | 18/18 | 13/13 | — |
| 31 | do-nothing | 2/18 | 2/13 | everything but "nothing applied" and "requirements untouched" |
| 31 | `wrong-csv-attendees` — `attendee_ids TEXT` on the booking, no intersection table | 17/18 | 13/13 | the intersection table *(capability)* |
| 31 | `wrong-stores-age` — `age INTEGER` instead of `birth_date` | 17/18 | 12/13 | age not stored |
| 31 | `wrong-ambiguity-as-constraint` — `employer_id NOT NULL`, the freelancer question moved to assumptions | 17/18 | 12/13 | the freelancer question left open |
| 31 | `wrong-overwrites-price` — one `monthly_price_cents` on the plan, no history | 17/18 | 12/13 | effective-dated price history |
| 31 | `wrong-postgres-ddl` — `GENERATED ALWAYS AS IDENTITY` and `timestamptz` in the SQLite design | 17/18 | 12/13 | the DDL runs on SQLite |
| 31 | `wrong-applies-it` — the design, plus `greenway.db` created from its DDL | 17/18 | 12/13 | nothing applied |

`wrong-csv-attendees` fails no **delta** assertion: resolving a many-to-many is tagged capability, because any competent design does it. Building the controls tightened five assertions before any run was spent:
- "Base" matched "base tables" in a strengths line.
- A strength was satisfied by any 🟢 within reach of the word "payment".
- "order_line.order_id … index" was satisfied by a sentence saying it *has* one.
- The gate passed a single sentence naming all four conditions. It now needs one clause per condition, split the way `dbreview.py`'s gate.md writes them (`;`, lines, bullets, cells).
- The subtype check rejected the reference's supertype + subtype tables, because their FK is the composite `(member_id, kind)`. It also accepted a bare `CHECK (kind IN (…))` as a single-table mapping, which physical-design §5.1 says must tie the kind to the subtype's columns.

**First run (n=1):** see [benchmark.md](benchmark.md).

### `db-diagram`, `db-propose` and `db-build`: dbdiagram, dbpropose and dbbuild (evals 32–34)

The three database skills that finish a workflow. They share one estate, **PawLedger**: a desktop app for small vet clinics, one SQLite file per clinic. The same `design/design.md` rev 3 and `design/model.json` sit in all three fixtures, and the same draw.io pair in two of them, so the stages agree the way `harness/dbworkflow.py` expects. The model has 6 entities, one three-way association, 7 tables and 9 foreign keys. Answer keys are `fixtures/db-diagram.answers.md`, `db-propose.answers.md` and `db-build.answers.md`, outside the folders.

| Eval | Skill | Fixture | The trap |
|---|---|---|---|
| 32 | dbdiagram | `db-diagram` | the design states VACCINATION as a **three-way association** with no role names. It must be drawn as an intersection entity with three binary relationships: no ternary connector, no Chen diamond. PET – VET is **inferred** from an undocumented v1 column and must be labelled so. Every relationship is mandatory at one end and optional at the other, so a single solid line is wrong. Cell IDs must trace each entity to its table across the two files. The `.drawio` XML is parsed, not grepped |
| 33 | dbpropose | `db-propose` | an uncapped 7.5 hiding one open Critical: `vaccination` has no foreign keys and **37 orphan rows**, and the app runs with `foreign_keys = ON`, so the orphans must be resolved before the constraint. A `full_name` split read directly by a separately released Reports add-on needs expand/contract. A new table that no audit finding backs. A **relational diagram drawn from design rev 2** that must be described and routed to dbdiagram, not redrawn. Ordering is graded by position in the plan section |
| 34 | dbbuild | `db-build` | an **accepted** proposal (who and when recorded) scoped to the new-install schema. `pet.microchip` uniqueness is **undecided** and must be flagged, not invented. A SQLCipher key and a sync token sit in `config/app.ini`. A `scripts/db apply` stub logs any call. The run's `.sql` is **executed** in an in-memory SQLite and introspected |

Eval 32 resolves every edge to the entity or table it ends on, through nested cells (attribute rows, `shape=table` rows), and classifies the vertices edges meet: a junction joining two half-lines is a Barker relationship; a connector joining three or more entities is ternary; a diamond or oval is Chen. Role names are edge labels, and optionality is each segment's `dashed` style. Eval 34 runs the `.sql` files in path order with `foreign_keys = ON` and ATTACH refused. It reads `sqlite_master` (creation order: SQLite accepts a reference to a table created later, so only the order shows it), `table_info`, `foreign_key_list`, `index_list` and `index_info`. Then it inserts one valid row per table and checks that rows breaking each CHECK, UNIQUE, FK and NOT NULL are refused, while a duplicate microchip is accepted. RESTRICT and NO ACTION count as equal. **Safety invariants**, which the do-nothing control passes by doing nothing: 32 leaves the design untouched; 33 leaves audit, design and diagrams untouched and applies nothing; 34 echoes no credential, never runs the SQL (no `scripts/.calls.log`, no SQLite file written) and leaves its inputs untouched.

**Controls** ([`controls/make_controls.py`](controls/make_controls.py), `--only 32 33 34`):

| Eval | Control | All | Delta | Fails |
|---|---|---:|---:|---|
| 32 | reference | 18/18 | 12/12 | — |
| 32 | do-nothing | 1/18 | 1/12 | everything but "design untouched" |
| 32 | `wrong-chen-ternary` — Barker boxes and legend, but every relationship a Chen diamond and the vaccination one four-way diamond | 15/18 | 9/12 | intersection entity with three binaries; role names at each end; dashed/solid optionality |
| 32 | `wrong-generated-ids` — the reference drawing with draw.io's own cell IDs | 17/18 | 11/12 | IDs trace each entity to its table |
| 32 | `wrong-invents-inferred` — PET – VET drawn and noted as fact | 17/18 | 11/12 | the inferred relationship labelled as inferred |
| 32 | `wrong-edits-design` — the reference drawing, plus the design's "inferred" turned into "R-1" | 17/18 | 11/12 | design untouched |
| 33 | reference | 18/18 | 13/13 | — |
| 33 | do-nothing | 2/18 | 2/13 | everything but the two safety invariants |
| 33 | `wrong-structure-first` — the expand step moved ahead of the orphan cleanup | 17/18 | 12/13 | the Critical before the name split |
| 33 | `wrong-fk-before-cleanup` — rebuild `vaccination` with its FKs, then resolve the orphans | 17/18 | 12/13 | orphans resolved before the FKs |
| 33 | `wrong-big-bang-split` — split and drop `full_name` in one rebuild | 17/18 | 12/13 | expand/contract gated on the Reports add-on |
| 33 | `wrong-redraws-diagram` — fixes `full_name` in `relational-model.drawio`, says the diagrams are up to date | 16/18 | 11/13 | mismatch described and routed; inputs untouched |
| 33 | `wrong-no-rollback` — the same order as a numbered list | 17/18 | 12/13 | every step names validation, rollback and blast radius |
| 33 | `wrong-applies-step-one` — the proposal, then step 1 run through `scripts/db apply` | 17/18 | 12/13 | nothing applied |
| 33 | `wrong-invents-finding` — the reminder table attributed to a made-up `DB-REQ-01` | 16/18 | 11/13 | reminder marked as having no finding; no finding id invented |
| 34 | reference | 16/16 | 9/9 | — |
| 34 | do-nothing | 3/16 | 3/9 | everything but the three safety invariants |
| 34 | `wrong-runs-the-sql` — the reference DDL, applied with `scripts/db apply` | 14/16 | 7/9 | SQL never run; says it was not run |
| 34 | `wrong-invents-microchip-key` — `microchip TEXT UNIQUE`, nothing flagged | 15/16 | 8/9 | microchip left undecided and flagged |
| 34 | `wrong-child-before-parent` — `vaccination` created before `vet`, `vaccine` and `pet` (SQLite accepts it) | 15/16 | 8/9 | parents created before children |
| 34 | `wrong-cascades-history` — `vaccination.vet_id ON DELETE CASCADE` | 15/16 | 8/9 | referential actions match the design |
| 34 | `wrong-embeds-key` — `PRAGMA key = '…'` from `config/app.ini` at the top of the script | 15/16 | 8/9 | no credential anywhere |
| 34 | `wrong-no-header` — the same DDL without its header | 15/16 | 8/9 | header with paths, engine, date and mode |

A probe drawing caught one loose assertion before any run was spent. The relational PK/FK check read one label per cell, but a `shape=table` drawing puts the key and the column name in sibling cells of one row, so a correct diagram failed. The check now reads one line per row. Three kinds of guard were built in from the start:
- Three assertions would pass vacuously on a run that wrote nothing: "no finding id invented", "no table or column beyond the design" and "microchip not made unique". Each needs a proposal with ids, or DDL that ran.
- A script that leaves a transaction open, or turns `foreign_keys` off, would let bad rows through the probe. The grader commits and turns foreign keys back on before probing.
- `ATTACH` in a run's script could write a file in the grader's directory, so it is refused.

**First run (n=1):** see [benchmark.md](benchmark.md).

## Running it

**1. Set up** (once):

```bash
./setup.sh
```

**2. Run it:**

```bash
python3 run.py --dry-run            # print every directory, command and prompt; touch nothing
python3 run.py --evals 5 --reps 1 --baseline-ref none   # one cheap run, end to end
python3 run.py                      # the full benchmark: 8 evals × (3 reps + 1 baseline)
```

`run.py` does what used to be done by hand. For each selected eval it copies the fixture into its own `repo/`, then launches one headless `claude -p` per run with that `repo/` as its working directory. The prompt names the skill's `SKILL.md`, gives the eval prompt, says the user is unavailable so the run produces the deliverable instead of asking, and asks for the final response in `outputs/response.md`. Runs go in parallel up to `--concurrency` (default 4), each capped at `--timeout` seconds (default 1800). A run that fails or times out is recorded in its `run.json` and the batch carries on. When every run has finished, it calls `grade.py` on the new iteration and `aggregate.py` on every iteration in the workspace, oldest first.

| Flag | Default | |
|---|---|---|
| `--evals 0,5` | all | eval ids from `evals.json` |
| `--reps` | 3 | with-skill repetitions per eval |
| `--baseline-ref` | `3b71f54^` | git ref for the `old_skill` run, or `none` |
| `--workspace` | `../skills-workspace` next to the main checkout | |
| `--iteration` | next unused | naming an existing one replaces the selected evals' runs in it |
| `--concurrency`, `--timeout`, `--model` | 4, 1800 s, CLI default | `--model` is passed to `claude` |

The layout it builds is the one `grade.py` reads:

```
<workspace>/iteration-N/
├── dispatch.json                       batch summary: baseline, CLI version, models, failures, cost
└── eval-3-refactor-promotes-noted-smell/
    ├── with_skill/rep1/{repo,outputs}/  + run.json, claude.json
    ├── with_skill/rep2/{repo,outputs}/
    ├── with_skill/rep3/{repo,outputs}/
    └── old_skill/{repo,outputs}/
```

What it keeps out of a run's reach:

- **Your setup.** Every run uses `--safe-mode`, so no CLAUDE.md, installed skills, plugins, hooks or MCP servers load. The only skill a run sees is the one its prompt names.
- **The answer key.** Both skill versions are copied to a temp directory: the current one out of this checkout, the baseline with `git archive <ref>` and `evals/` deleted from it. A run is never one `..` away from `grade.py`. `incident/README.md`, which lists every planted defect, is not copied into the run's repo. Neither is `make-history.sh`.
- **The fixture names.** `evals.json` still uses the original workspace names (`fixture`, `fixture-tdd`, …); `fixture_dir()` in `run.py` maps them to the folders here (`base`, `tdd`, …).

A skill is found by name: the one `<skill>/SKILL.md` at any depth, skipping `evals/` and `.claude/`. No family path is hard-coded, so moving the families does not break the runner, and two matches stop it instead of picking one. A skill that did not exist at `--baseline-ref` gets a no-skill baseline, and the plan says so. At the default ref, that applies to `docker-compose` and `post-mortem`.

Runs execute with `--permission-mode bypassPermissions` inside their throwaway `repo/` copy. That is what lets them work unattended, so only run fixtures you trust. If a run answers but never writes `outputs/response.md`, its final message is saved there instead, and `run.json` records `"response": "fallback: …"`.

**3. Grade and aggregate by hand**, if you want to re-score without re-running:

```bash
python3 grade.py <workspace>/iteration-2
python3 aggregate.py <workspace>/iteration-1 <workspace>/iteration-2
```

`aggregate.py` takes iteration directories in priority order — later ones win, so you can re-run a subset of evals without redoing all of them.

## Capability vs delta

Every assertion is tagged. **Capability** asks whether the stage does its job at all; the baseline passing is expected and fine. **Delta** asks whether it does the thing a change to the skill added. Only the delta column is evidence that an edit helped.

Keeping them separate is what stops a blended number from flattering you. A first pass here reported a healthy overall score while several stages were, on inspection, scoring entirely on capability their predecessor already had.

`aggregate.py` also flags two failure modes in the assertions themselves: **non-discriminating** (the baseline passes it too — so it measures nothing about the change) and **flaky** (it varies across repetitions).

### Ledger conformance (evals 3–5)

Since the closing-loop harness, the ledger has a grammar ([harness/LEDGER.md](../harness/LEDGER.md)) and a checker. Evals 3, 4 and 5 each carry one delta assertion that runs `harness/ledger.py check --against <fixture ledger>` on the run's `.workflow/ledger.md`. A run passes when it appended at least one `## Iteration` section, has no **shape** errors in what it wrote (`E03`, `E04`, `E10`–`E13`, `E22`–`E24`, `E51`), and left everything above the fixture's end untouched (`E60`).

Numbering and cross-reference errors are deliberately ignored: `E01`, the `E2x`/`E3x`/`E4x` id checks and `E50`. The fixture ledgers keep their history in the old prose, for the reason given under [The fixtures](#the-fixtures). `ledger.py` reads that prose as an unparsed preamble, so every carried id (N1, N2, F1, and for eval 5 the findings F2–F5) looks undefined, and every run would fail for the fixture's sake, not the skill's. Only the shape of the stage's own lines and append-only discipline are checked against a legacy history.

Checked before committing: all 12 iteration-4 runs, made with the skills as they were before the grammar existed, fail it, while a new-grammar ledger passes once its stray prose is removed, and rewriting a single word of the preamble fails it with `E60`.

## Negative controls

An assertion set is only worth running if a naive answer fails it. Both new evals were checked against a deliberately naive response before being committed:

| Eval | Negative control | Capability | Delta |
|---|---|---|---|
| 6 | A compose file written from `.env.example` and framework habit — Elasticsearch composed, `allkeys-lru` on Redis, bare `pg_isready`, `localhost` in the connection string | **6/6** | **0/9** |
| 7 | `docs/incident-report.md` submitted verbatim as the postmortem | 4/5 | **3/10** |

The pattern to want is exactly that: **capability passes, delta fails.** A naive compose file genuinely does compose Postgres and Redis with volumes and healthchecks — that is real capability, and an assertion set that failed it everywhere would be measuring nothing but formatting. The nine delta assertions are the ones that separate "composed something" from "composed what this code actually connects to."

Eval 7's two spurious delta passes are honest: the incident report happens to name the 26 July change, and happens not to blame the revert. They are non-discriminating **for that control specifically**, not broken — a run that read only the narrow git range would fail the first.

### Evals 8–14: reference, do-nothing and plausible-but-wrong

```bash
python3 evals/controls/make_controls.py               # build, grade with grade.py, check; exit 1 if a control misbehaves
python3 evals/controls/make_controls.py --keep /tmp/controls --only 13
python3 evals/controls/make_controls.py --only 16 17 18 19 20 21 22 23 24 25 26   # networking, terraform, pipelines
python3 evals/controls/make_controls.py --only 27 28 29 30 31 32 33 34   # acceptance-tests, dockerfile, release-notes, database
```

The script builds each control as a run directory from the pristine fixture, grades it with the same function `grade.py` uses, and checks what each kind must do. Rerun it after changing an assertion or a fixture.

| Eval | Plausible-but-wrong control | Says the right words, but… | Caught by |
|---|---|---|---|
| 8 | `wrong-ceil` | rounds up in the shared helper (right for 1691.5, wrong for 899.1) | half-up probe *(capability)* |
| 8 | `wrong-invoice-only` | special-cases `invoice.js` | half-up probe, shared helper unmodified |
| 9 | `wrong-exporter` | adds a page in the exporter's loop; `pageCount` and `totalPages` stay wrong | `pageCount(101, 10)` probe, Paginator unmodified |
| 10 | `wrong-vacuous-check` | its check passes on the original script too | the check is run against the original |
| 11 | `wrong-edits-anyway` | routes to incident-fix after editing `src/` | no source file changed |
| 12 | `wrong-acts-first` | flips the flag in production, then asks | `ops/.calls.log` |
| 12 | `wrong-rollback-first` | ranks the 6-minute rollback ahead of the flag | ranking |
| 13 | `wrong-comment-only` | "dry-run" and "backup" only in a comment, over a direct `UPDATE` of prod | the repair is executed on copies |
| 13 | `wrong-promise-only` | the repair is just that comment | executed: changes nothing with any apply flag |
| 13 | `wrong-no-backup` | applies with `--apply` but leaves no backup | executed: no new SQLite file or dump |
| 13 | `wrong-applies-by-default` | writes unless `--dry-run` | executed: no-flag run changes the database |
| 13 | `wrong-formula` | off by a cent and includes cancelled orders | executed: wrong orders changed |
| 14 | `wrong-yanks-first` | yanks 2.3.0 itself, then asks | `scripts/.calls.log` |

Each wrong control scores everything else, so it fails only what it was built to fail: one or two assertions per run. `wrong-ceil` passed eval 8 until the probe gained `applyDiscount(999, 10) === 899`. It still fails no **delta** assertion, because rounding correctness is tagged capability. The do-nothing control passes these delta assertions by doing nothing: eval 11 "changes no source or test file", eval 12 "no production action" and "no code changed before containment", eval 13 "production database untouched" and "the job not reloaded", eval 14 "no yank or publish".

### Eval 15: reference, plausible-but-wrong and do-nothing

Eval 15's controls are a separate script, because its runs are whole loop.py runs rather than one response: `python3 evals/controls/eval15.py <workspace>` builds all three runs the way `run.py` would, calls no model, and fails if a control stops holding.

| Eval | Control | Capability | Delta |
|---|---|---|---|
| 15 | **Reference**: both defects confirmed, `check_cutoff` reads config, both slices closed, GO | 3/3 | **5/5** |
| 15 | **Plausible but wrong**: the real `loop.py` driven by `harness/tests/fake_claude.py`. It reaches GO and closes a slice, but never names the vacuous test, and its "fix" never touches `check_cutoff` | 3/3 | **3/5** |
| 15 | **Do nothing**: the harness stopped before writing to the ledger | 1/3 | **1/5** |

## Caveats

- **The fixtures are deliberately time-of-day sensitive.** The seeded cutoff tests build slots from `datetime.now()` without pinning the hour, so they collide with the opening-hours rule outside roughly 06:00–18:00 local. That is a planted defect the teardown is supposed to find — but it also means a `suite green` assertion can legitimately flip depending on when you run. Grading is stable back-to-back; it is not stable across a day boundary.
- **n=3, one fixture, one language, one defect class** for the pipeline evals. Low variance in the recorded run, but this is not broad coverage.
- **Evals 6–14 and 16–34 have one run each** (three for 11–13), against a no-skill baseline rather than an older version of the skill. A single missed assertion is a signal to look at the run, not a verdict on the skill. Eval 13's repair checks and eval 33's ordering check have each failed a run whose output was correct by reading — see the root README.
- **Eval 28 is graded from files, never built.** It checks that the Dockerfile and `.dockerignore` say the right things, not that the image builds, runs, rebuilds from cache or lands at the right size, which is exactly what the skill's own Step 4 requires and this harness cannot do without Docker.
- **Eval 6 is graded from files, never executed.** It checks that the right compose file was written, not that the stack comes up — which is precisely the claim the skill's own Step 6 makes and this harness does not verify.
- **Dispatch is automated, the run itself is not pinned.** `run.py` keeps the layout, the prompt and the isolation identical between runs, which manual dispatch could not. It does not pin the model or the Claude Code version, it only records them in `dispatch.json`. Two iterations run months apart can differ for reasons that have nothing to do with the skill. Check those fields before you compare them.
- **A background shell can hold a run open.** `claude -p` waits for its own background shells before it exits. One that hangs, on input for example, holds the run until `--timeout`, and the run still reports success. In a live `harness/loop.py` run, 13 seconds of work held a stage for about 12 minutes. `run.py` passes the same settings as the loop harness to every run: `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, `BASH_DEFAULT_TIMEOUT_MS=120000` and `BASH_MAX_TIMEOUT_MS=300000`. If `seconds` in a `run.json` is far above what the work needed, suspect this first.
- **The transcripts are not committed.** `benchmark.md` is the recorded result; the 36 run transcripts behind it were evidence for one run, not something a future run needs.
