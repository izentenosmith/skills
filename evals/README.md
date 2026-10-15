# Evals — measuring whether the skills actually work

These skills are prompts, and a prompt's claims about its own behavior are hypotheses until something checks them. This harness is that check: it runs each skill against a seeded fixture with known defects planted in it, and scores what the skill produced.

The headline result is in [benchmark.md](benchmark.md). The short version: on the assertions that test what the skills instruct, the six-stage pipeline scores **0.98** against **0.22** for the pre-session baseline; on core capability, **0.96** against **0.92**.

**Evals 6 and 7 have fixtures and assertions but no scored run yet.** Their assertions are verified to *discriminate* — see [Negative controls](#negative-controls) — but nobody has dispatched the with-skill runs, so there is no number for `docker-compose` or `post-mortem` and `benchmark.md` does not report one.

## Layout

```
evals/
├── setup.sh        build fixture venvs + the incident git history (run once)
├── evals.json      one entry per eval: a prompt and a skill, or (eval 15) a runner
├── run.py          dispatch the runs headless, then grade + aggregate
├── grade.py        assertions → grading.json per run
├── aggregate.py    grading.json → benchmark.md/json
├── benchmark.md    the recorded result
├── controls/       reproducible controls (eval15.py: reference, plausible-wrong, do-nothing)
└── fixtures/       the seeded repos and documents the skills work against
```

## The fixtures

### The pipeline fixture (evals 0–5)

A small Python reservations service. Bookings go through `BookingService.submit`; constraint rules live in `rules.py` and return a violation code or `None`. Five variants, each seeded for the stage that uses it:

| Fixture | Seeded with | Used by |
|---|---|---|
| `base` | clean service, green suite | architect-deep-dive, agent-brief |
| `tdd` | `+ .workflow/brief.md` | tdd |
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

`hotfix-jvm` needs a JDK (`javac`, `java`) and `hotfix-node` needs Node 22+, both to run and to grade; nothing else needs setup. **Controls:** a reference answer scores every assertion on all seven and a do-nothing answer fails every delta assertion except the safety invariants it passes by doing nothing (no production call, no file changed). **No with-skill run has been scored.**

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
| the refuted party-size claim is not confirmed again (judged on Target / Claim, not evidence) | delta |
| GO, **and** the defect is fixed through `BookingService.submit`: a 240-minute window rejects a slot 180 minutes out, a 60-minute one accepts 90, the default rejects 90 | delta |
| at least one remediation slice closed (loop.py closes one only after redgreen's proof) | delta |

The fix is probed with every hour open, so the result does not depend on the time of day. A GO is not taken on the loop's word: the stub-driven control below reaches GO without fixing anything.

There is no baseline: `harness/loop.py` does not exist at `3b71f54^` or `dd2a41c`, and `run.py` says so instead of inventing a no-harness run. A live run costs about $4 and 15–40 minutes; its `timeout` in `evals.json` is 3600 s.

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

Eval 15's controls are a script, so they can be re-run: `python3 evals/controls/eval15.py <workspace>` builds all three runs the way `run.py` would, calls no model, and fails if a control stops holding.

| Eval | Control | Capability | Delta |
|---|---|---|---|
| 15 | **Reference**: both defects confirmed, `check_cutoff` reads config, both slices closed, GO | 3/3 | **5/5** |
| 15 | **Plausible but wrong**: the real `loop.py` driven by `harness/tests/fake_claude.py`. It reaches GO and closes a slice, but never names the vacuous test, and its "fix" never touches `check_cutoff` | 3/3 | **3/5** |
| 15 | **Do nothing**: the harness stopped before writing to the ledger | 1/3 | **1/5** |

## Caveats

- **The fixtures are deliberately time-of-day sensitive.** The seeded cutoff tests build slots from `datetime.now()` without pinning the hour, so they collide with the opening-hours rule outside roughly 06:00–18:00 local. That is a planted defect the teardown is supposed to find — but it also means a `suite green` assertion can legitimately flip depending on when you run. Grading is stable back-to-back; it is not stable across a day boundary.
- **n=3, one fixture, one language, one defect class** for the pipeline evals. Low variance in the recorded run, but this is not broad coverage.
- **Evals 6 and 7 are unrun.** Fixtures and assertions exist and discriminate against a negative control; no with-skill run has been scored, so nothing in `benchmark.md` covers `docker-compose` or `post-mortem`.
- **Eval 6 is graded from files, never executed.** It checks that the right compose file was written, not that the stack comes up — which is precisely the claim the skill's own Step 6 makes and this harness does not verify.
- **Dispatch is automated, the run itself is not pinned.** `run.py` keeps the layout, the prompt and the isolation identical between runs, which manual dispatch could not. It does not pin the model or the Claude Code version, it only records them in `dispatch.json`. Two iterations run months apart can differ for reasons that have nothing to do with the skill. Check those fields before you compare them.
- **A background shell can hold a run open.** `claude -p` waits for its own background shells before it exits. One that hangs, on input for example, holds the run until `--timeout`, and the run still reports success. In a live `harness/loop.py` run, 13 seconds of work held a stage for about 12 minutes. `run.py` passes the same settings as the loop harness to every run: `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, `BASH_DEFAULT_TIMEOUT_MS=120000` and `BASH_MAX_TIMEOUT_MS=300000`. If `seconds` in a `run.json` is far above what the work needed, suspect this first.
- **The transcripts are not committed.** `benchmark.md` is the recorded result; the 36 run transcripts behind it were evidence for one run, not something a future run needs.
