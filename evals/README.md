# Evals — measuring whether the skills actually work

These skills are prompts, and a prompt's claims about its own behavior are hypotheses until something checks them. This harness is that check: it runs each skill against a seeded fixture with known defects planted in it, and scores what the skill produced.

The headline result is in [benchmark.md](benchmark.md). The short version: on the assertions that test what the skills instruct, the six-stage pipeline scores **0.98** against **0.22** for the pre-session baseline; on core capability, **0.96** against **0.92**.

**Evals 6 and 7 have fixtures and assertions but no scored run yet.** Their assertions are verified to *discriminate* — see [Negative controls](#negative-controls) — but nobody has dispatched the with-skill runs, so there is no number for `docker-compose` or `post-mortem` and `benchmark.md` does not report one.

## Layout

```
evals/
├── setup.sh        build fixture venvs + the incident git history (run once)
├── evals.json      eight prompts, one per skill under test
├── grade.py        assertions → grading.json per run
├── aggregate.py    grading.json → benchmark.md/json
├── benchmark.md    the recorded result
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

## Running it

**1. Set up** (once):

```bash
./setup.sh
```

**2. Dispatch the runs.** This step is **not automated** — you launch the subagents yourself, one per run. For each eval in `evals.json`, give a subagent: a copy of the fixture in its own run directory, the path to the skill's `SKILL.md`, the eval prompt, and an instruction to save its final response to `outputs/response.md`. Tell it the user is unavailable, so it produces the deliverable rather than waiting on a question.

Repeat each run 3× for variance, and run one baseline against an older snapshot of the skill (`git archive <ref> | tar -x -C <snapshot-dir>`). Expected layout:

```
<workspace>/iteration-N/
└── eval-3-refactor-promotes-noted-smell/
    ├── with_skill/rep1/{repo,outputs}/
    ├── with_skill/rep2/{repo,outputs}/
    ├── with_skill/rep3/{repo,outputs}/
    └── old_skill/{repo,outputs}/
```

**3. Grade and aggregate:**

```bash
python3 grade.py <workspace>/iteration-2
python3 aggregate.py <workspace>/iteration-1 <workspace>/iteration-2
```

`aggregate.py` takes iteration directories in priority order — later ones win, so you can re-run a subset of evals without redoing all of them.

## Capability vs delta

Every assertion is tagged. **Capability** asks whether the stage does its job at all; the baseline passing is expected and fine. **Delta** asks whether it does the thing a change to the skill added. Only the delta column is evidence that an edit helped.

Keeping them separate is what stops a blended number from flattering you. A first pass here reported a healthy overall score while several stages were, on inspection, scoring entirely on capability their predecessor already had.

`aggregate.py` also flags two failure modes in the assertions themselves: **non-discriminating** (the baseline passes it too — so it measures nothing about the change) and **flaky** (it varies across repetitions).

## Negative controls

An assertion set is only worth running if a naive answer fails it. Both new evals were checked against a deliberately naive response before being committed:

| Eval | Negative control | Capability | Delta |
|---|---|---|---|
| 6 | A compose file written from `.env.example` and framework habit — Elasticsearch composed, `allkeys-lru` on Redis, bare `pg_isready`, `localhost` in the connection string | **6/6** | **0/9** |
| 7 | `docs/incident-report.md` submitted verbatim as the postmortem | 4/5 | **3/10** |

The pattern to want is exactly that: **capability passes, delta fails.** A naive compose file genuinely does compose Postgres and Redis with volumes and healthchecks — that is real capability, and an assertion set that failed it everywhere would be measuring nothing but formatting. The nine delta assertions are the ones that separate "composed something" from "composed what this code actually connects to."

Eval 7's two spurious delta passes are honest: the incident report happens to name the 26 July change, and happens not to blame the revert. They are non-discriminating **for that control specifically**, not broken — a run that read only the narrow git range would fail the first.

## Caveats

- **The fixtures are deliberately time-of-day sensitive.** The seeded cutoff tests build slots from `datetime.now()` without pinning the hour, so they collide with the opening-hours rule outside roughly 06:00–18:00 local. That is a planted defect the teardown is supposed to find — but it also means a `suite green` assertion can legitimately flip depending on when you run. Grading is stable back-to-back; it is not stable across a day boundary.
- **n=3, one fixture, one language, one defect class** for the pipeline evals. Low variance in the recorded run, but this is not broad coverage.
- **Evals 6 and 7 are unrun.** Fixtures and assertions exist and discriminate against a negative control; no with-skill run has been scored, so nothing in `benchmark.md` covers `docker-compose` or `post-mortem`.
- **Eval 6 is graded from files, never executed.** It checks that the right compose file was written, not that the stack comes up — which is precisely the claim the skill's own Step 6 makes and this harness does not verify.
- **Manual dispatch** is the weakest link — it is the step most likely to drift between runs.
- **The transcripts are not committed.** `benchmark.md` is the recorded result; the 36 run transcripts behind it were evidence for one run, not something a future run needs.
