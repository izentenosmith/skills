# Triggering eval

The evals in `evals/evals.json` tell each run which skill to follow, so they measure what a skill
does once it is loaded. This one measures the step before: whether a skill's frontmatter
`description` makes an agent pick the skill up when it should, and leave it alone when it should
not. The description is the only text that decides this, so a trigger rate is attributable to it
alone.

## The cases

`cases.json` holds six prompts for each of eight skills that have close neighbours: `hotfix` and
`incident-fix`, `dbaudit` and `dbdesign`, `peer-review` and `pr-prep`, `ticket` and `backlog`.

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
`heldout` (seed recorded in `cases.json`): 32 train, 16 held-out. The split is stored, not
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
