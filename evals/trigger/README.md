# Triggering eval

The evals in `evals/evals.json` tell each run which skill to follow, so they measure what a skill
does once it is loaded. This one measures the step before: whether a skill's frontmatter
`description` makes an agent pick the skill up when it should, and leave it alone when it should
not. The description is the only text that decides this, so a trigger rate is attributable to it
alone.

## The cases

`cases.json` holds six prompts for each of twenty-five skills that have close neighbours: `hotfix` and
`incident-fix`, `dbaudit` and `dbdesign`, `peer-review` and `pr-prep`, `ticket` and `backlog`, and (added
2026-11-20, when their descriptions changed) six development skills: `agent-brief`, `architect-deep-dive`,
`devils-advocate`, `tyr-verdict`, `refactor-review` and `nexus`; and (added 2026-11-21, so every bundle
in `skills/bundles.json` has cases) `dockerfile` and `docker-compose`, `netaudit` and `netdesign`,
`threatmodel` and `appsec`; and (added 2026-11-21) the other five database skills: `dbquery`, `dbpropose`, `dbbuild`,
`dbdiagram` and `dbarchitect`.

- Three **should trigger**: the skill under test is the right first pick.
- Three **should not**: near-misses. Most belong to a neighbour (`expected` names it:
  `incident-fix`, `dbpropose`, `test-review`, …); a few need no skill at all (`expected: null`).

Prompts are written the way a user would write them and never name a skill; a test enforces that.
The set is balanced on purpose: a description tuned only on should-trigger cases gets greedy, and
only the should-not cases show it.

Each case records:

| field | meaning |
|---|---|
| `skill` | the skill whose description the case tests |
| `should_trigger` | whether that skill should be the first one picked |
| `expected` | the skill that should be picked first, or `null` for none of this repo's skills |
| `split` | `train` or `heldout` |

## The split, and the rule

One of every three cases in each (skill, should/should-not) group was drawn at random into
`heldout` (seeds recorded in `cases.json`): 100 train, 50 held-out. The split is stored, not
re-derived, so adding cases never moves an existing one.

**Only train cases may be read while editing a description.** Run `--split train`, read those
prompts and their transcripts, change the description, run train again. The held-out cases are
for one question only, asked after the edit is settled: did the improvement carry over to prompts
the edit never saw? Do not open held-out prompts or their transcripts to work out why one failed;
once a held-out prompt has shaped a description it measures nothing, and has to be moved to train
and replaced with a new one. The summary reports the two splits apart so a gain on train with none
on held-out is visible as what it is: a description fitted to its examples.

## Running it

```bash
python3 evals/trigger/run_trigger.py --dry-run                       # the plan and a cost estimate; touches nothing
python3 evals/trigger/run_trigger.py --model sonnet --split train    # one description-editing round
python3 evals/trigger/run_trigger.py --model sonnet --reps 3         # the full set, three runs per case
```

Also `--skills hotfix,incident-fix`, `--cases hotfix-yes-1`, `--max-turns`, `--max-budget-usd`,
`--concurrency`, `--timeout`, `--out`.

### Per bundle (coexistence)

```bash
python3 evals/trigger/run_trigger.py --bundle on-call --model claude-opus-5-5 --reps 3
```

`--bundle NAME` stages only what a user who installs that bundle has: its skills from
`skills/bundles.json` and the ones offered with every bundle (repo-memory). It runs the cases whose
skill under test is in the bundle, so it asks whether the descriptions still route correctly among
the skills that are installed together. A should-not case whose expected neighbour is not in the
bundle cannot pick that neighbour; its `expected` becomes no skill for the run, and results.jsonl
keeps the original as `expected_outside_bundle`. The false-trigger rate is unaffected; "picked what
was expected" then means the run left the skill under test alone and picked nothing else.

Each run is one headless `claude -p` given the case's prompt and nothing else. All of this repo's
skills are copied to `<tmp>/skills-home/.claude/skills/` and attached with `--add-dir`; the working
directory is an empty folder beside it. `--setting-sources project` keeps your own skills, plugins
and `CLAUDE.md` out, and `--strict-mcp-config` your MCP servers. (`--safe-mode`, which `run.py`
uses, would load no skills at all.) The run gets the Skill tool and read-only file tools, and is
stopped at the first skill it picks: a Skill tool call, or a Read of a staged `SKILL.md`.

Results go to `../skills-workspace/trigger/<stamp>/`, outside git like every other run:
`results.jsonl`, `transcripts/`, `summary.json` and `summary.md`. `summary.json` also records a
hash of each tested description (so a rate can be tied to the wording it measured) and the skills
the runs were offered that are not from this repo.

### Results: every bundle, 2026-11-21

Opus (`claude-opus-5-5`), three runs per case, all cases (train and held-out) whose skill is in the
bundle; 414 runs, no errors, about $26 (the 57 runs that finished reported $3.80; the 357 stopped at
their skill choice report tokens only, priced here from the finished runs' rate). Results are in the
workspace under `trigger/bundles-20261121/<bundle>/`.

| bundle | skills staged | runs | trigger rate | false-trigger rate | picked what was expected |
|---|---|---|---|---|---|
| builder | 12 | 144 | 72/72 | 0/72 | 135/144 |
| reviewer | 8 | 54 | 27/27 | **3/27** | 51/54 |
| on-call | 7 | 72 | 36/36 | 0/36 | 72/72 |
| platform | 9 | 36 | 18/18 | 0/18 | 36/36 |
| data | 8 | 36 | 15/18 | 0/18 | 33/36 |
| network | 6 | 36 | 18/18 | 0/18 | 36/36 |
| security | 5 | 36 | 18/18 | 0/18 | 36/36 |

- **reviewer: `appsec-no-1` falsely triggers appsec, 3 of 3.** Its prompt asks for the security
  design of a system not yet built, which belongs to threatmodel; threatmodel is not in the reviewer
  bundle, so appsec, the nearest installed skill, takes it. Every other bundle keeps its skills apart.
  **Fixed** by adding the rest of the security family (threatmodel, hardening, container-hardening)
  to the reviewer bundle. Re-run the same day, same model and reps (`trigger/bundles-20261121-reviewer2/`,
  11 skills staged, 72 runs, about $5): trigger 36/36, false-trigger 0/36, picked what was expected
  72/72. `appsec-no-1` now picks threatmodel 3 of 3; `appsec-no-2`, which picked nothing while
  hardening was outside the bundle, now picks hardening; every case from the first run picks what it
  picked before or better.
- **builder: the 9 misses are not false triggers.** Three near-misses belong to peer-review, which
  is not in the bundle; all 9 runs picked the CLI's built-in `code-review` instead, never the skill
  under test.
- **data: `dbdesign-yes-3` picks nothing, 3 of 3.** A one-line normal-form question the model answers
  itself; it picked no skill in all ten earlier all-skills runs too, so it is not a bundle effect.
- The runs were also offered 22 skills that are not this repo's (the CLI's built-ins such as
  `code-review`, `debug`, `simplify`); none of the user's own skills leaked in.

### Results: the 500-character rewrite, 2026-11-26

Opus (`claude-opus-5-5`), three runs per case, all skills staged, the 150 cases of the 25 skills that
had cases before 2026-11-24 (train and held-out); 450 runs before (the descriptions as of `36e6515`,
run from a checkout of that commit) and 450 after (the rewritten descriptions, with the words the routing check added on
2026-11-24), no errors. Results
are in the workspace under `trigger/before-20261126/` and `trigger/after-20261126/`.

| | trigger rate (train) | trigger rate (held-out) | false-trigger rate | picked what was expected |
|---|---|---|---|---|
| before | 144/150 | 75/75 | 0/225 | 439/450 |
| after | 148/150 | 75/75 | 0/225 | 445/450 |

No skill lost a hit or gained a false trigger. dbdesign went 6/9 → 9/9 and dbpropose 6/9 → 7/9 on
should-trigger runs; pr-prep's near-misses now find their neighbour 18/18 (16/18 before). The
remaining misses: `dbpropose-yes-1` picks no skill in 2 of 3 runs (3 of 3 before), and
`refactor-review-no-1` picks the CLI's built-in `code-review` instead of the expected neighbour in
all three runs, as before; neither is a false trigger.

## Reading the summary

- **Trigger rate**: of the should-trigger runs, how many picked the skill first.
- **False-trigger rate**: of the should-not runs, how many picked the skill under test.
- **Picked what was expected**: stricter; a should-not run that left the skill alone but did not
  find the neighbour either counts against this and not against the false-trigger rate.
- **Expected → picked**: the confusion table. Rows marked ✗ show which neighbour (or nothing) was
  picked instead.

## Cost

Almost all of a run's cost is the system prompt and the skill listing, about 16k input tokens,
written to the prompt cache once and read by the runs that follow. Measured with claude 2.1.295:
a Haiku run that picked no skill and used all three turns cost $0.004–0.005; on Sonnet the same
kind of run cost $0.06, and a run stopped at its skill call costs less than that (it ends before
its result event, so it reports tokens and no dollar figure). The estimate `--dry-run` prints uses
a rough per-run figure for each model, and `--max-budget-usd` (default 0.25) is a hard cap per run.

## Caveats

- **The model matters.** In the first proof runs Haiku picked no skill for a prompt on which Sonnet
  picked `hotfix` at once. Measure on the model you use the skills with; a rate from another model
  says little.
- **Built-in skills are present.** The CLI's own skills (`code-review`, `debug`, `simplify`, …) are
  offered alongside the staged ones and cannot be switched off without switching off all skills. A
  run that picks one shows up in the confusion table under that name.
- **The working directory is empty.** There is no repo to fix or schema to audit, so a run that
  looks for files before choosing a skill finds none. `--max-turns` (default 3) is how long it gets
  to choose.
- **One run per case is noisy.** With three should-trigger cases per skill a single flip moves a
  skill's rate by a third. Use `--reps 3` or more before reading anything into a per-skill number.
- **First pick only.** A run that picks the neighbour first and the right skill second is a miss.
