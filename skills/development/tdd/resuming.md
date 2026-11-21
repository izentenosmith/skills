# Resuming a build

> Companion to the [tdd](SKILL.md) skill. Read it in step 0 when you are resuming — after a usage
> limit, a crash or a compaction, or when the brief already carries ticks or a `**Base:**`, or the
> tree has commits or changes since Base. It says only what step 0 adds on a resume.

A build outlives the session that started it: after a usage limit, a crash or a compaction you
remember nothing that isn't on disk. The two ways that goes wrong are building on a tree you don't
understand and deciding the work is finished because some of it is there.

- **What was recorded** — the brief's ticks and Revisions, the ledger's last section, and the last
  status block of your stage log if a coordinating session gave you one.
- **What actually happened** — `git log --oneline -20` since the brief's `**Base:**`, and the
  uncommitted changes. Work the record doesn't explain is settled first, never built on as found:
  - **Your own unfinished slice** — after a compaction, only what your stage log or the brief's
    Revisions records as yours: finish it, or set it aside in a WIP commit on a side branch or a
    named `git stash`, return to the last green commit and say so. Never a hard reset.
  - **Anything else**, uncommitted or unpushed, may be the user's: leave it untouched, say what is
    there and ask. When nobody can answer, stop without building on it and name it in your last
    line.
- **How to run things** — rediscover only what is missing or no longer runs, from the sources
  step 0 names.
- **Is it green?** — every test that was green stays green and every ticked criterion's test
  passes; a tick whose test fails is unticked, and fixing it comes before the next criterion.
