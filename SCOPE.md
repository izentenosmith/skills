# Scope

What gets into this repo and what gets cut. The skills follow what I actually do (see the
[README](README.md)), so the bar for a change is something that actually happened.

## A change starts from an observed failure

A change to a skill needs a failure seen in a real session. Write down three things:

- **what ran**: the skill, the model, the repo or fixture, and the request;
- **what the skill did**: quoted from the transcript or the files it wrote;
- **what was expected**: and which line of the skill should have produced it.

"It would be better if…", a technique from a book, or another repo's habit doesn't qualify on its
own. It qualifies once a session misses it.

The evals are how a failure is kept, not where one comes from. Turn the failure into a seeded
fixture and an assertion that fails without the fix. Fix the skill until it passes, then re-run the
skill's evals and keep the change only if none of them drops ([evals/README.md](evals/README.md)).
A held-out eval never drives an edit: when one fails, write a train eval for the same gap and fix
against that. A higher benchmark number with no failure behind it is not a reason for a change.

Grader false negatives, broken links and checker fixes are repairs, not changes to what a skill
does, and need no session behind them.

## No new skill when existing ones compose

Before adding a skill, show that no chain of existing skills covers the work: a mode of one skill,
a handoff between two, or a reference file one of them opens. A new skill earns its place with a
failure the existing ones can't fix without becoming something else. It ships with an eval
(`check_repo.py` fails a skill without one).

## Budgets

- **Description: 500 characters.** It is what the agent reads to decide whether to load the
  skill, on every turn. Lead with when to use it, not a list of what it does.
- **SKILL.md body: 375 lines and 3,700 words**, frontmatter excluded, reference files not counted.
  Detail that doesn't fit goes into a reference file the body says when to open.
  [`budget.py`](.github/scripts/budget.py) has the numbers, why they were chosen, and the dated
  allowances for the skills over budget today; `check_repo.py` fails a skill over budget without
  one.

## What was cut

Ideas tried and taken out, or turned down, are in [.out-of-scope/](.out-of-scope/README.md), one
file each with the reason, so the next session doesn't propose them again.
