# The sub-session contract

Paste this into the first message of every session the nexus starts, with the `<…>` filled in. It is what makes a session's turns readable without its transcript: a session that never saw it free-texts its questions, says "waiting for the run" without saying which, and coins its own label series.

---

You are building one pull request for **<increment>**: **<slice>**. Run the development pipeline on it — architect-deep-dive (if the slice's design is not already resolved), agent-brief, acceptance-tests, tdd, refactor-review, devils-advocate, tyr-verdict — in this worktree, on branch `<branch>` from `<base branch>` at `<sha>`.

A coordinating session, the **nexus**, runs several sessions like you at once. It judges your PR on your stage log, not on what you tell it, and it is the only one who sees across sessions.

**Shared notes:** `<absolute path>/` · **Your log:** `<absolute path>/sessions/<slug>.md` · **Your scratch names:** <databases, ports, paths>

**Commands** (from `env.md` in the shared notes — use these, don't rediscover them): test `<full suite>` · focused `<one test or file>` · lint `<commands or none>` · build `<command or none>` · start `<how to run the app, or none>` · smoke `<the check that it is up>`. **Baseline:** the suite on `<base branch>` at `<sha>` was <passed>/<failed>/<skipped>. **You deliver:** <REQ-ids from `increment.json`, each in a line>.

**Before you ask anything, read** `decisions.md`. **At the start of each stage, read** `findings.md`. **Before citing a label or using a shared resource, read** `labels.md` and `resources.md`.

### Start of every session

You begin with no memory of your last session: after a usage limit, a crash, a compaction or a closed window, what you remember is whatever is on disk. Each time you start or are resumed, before any new work, in this order:

1. **Where you are.** `pwd`, the branch, and `git status`: the worktree and branch this brief names, and nothing else.
2. **Your log's last status block.** It is the hand-over: what was in flight, the command that was running, the step after it. On a first start there is none; write your log's header.
3. **`git log --oneline -20`** and the uncommitted changes. Commits the log doesn't mention, or changes it doesn't explain, are settled before anything else: finish the slice they belong to, or go back to the last green commit and say so in the log. Don't build on work you can't account for.
4. **The brief and its ticks**, where a brief exists: what is done, and the first criterion that isn't.
5. **`decisions.md` and `findings.md`**, for what changed while you were away.
6. **The suite, then the acceptance command.** Compare the counts with your log's last counts, or with the baseline above on a first start. A test that was green and is red is fixed before new work, and one that is red on the baseline too goes to the nexus as a question. Starting a feature on a broken tree makes both harder to fix. Where the slice has something to run, start it with the start command and run the smoke check too.

Then say in one line what you found and continue from **Next**. A command in this brief that no longer works is a question for the nexus, with the output, not a reason to find your own.

### Your log

Append to your log at the end of every turn: what you did and the evidence (commands, counts, commits). Record every tyr-verdict with **the commit it applies to**: a GO with no commit is not a GO the nexus can accept. Record test counts as passed, failed **and skipped**.

When your PR is ready, add one line per increment entry you were given, naming the test that proves it: `Delivers: REQ-<n> → <test id>`. An entry you could not deliver is a line too, `Not delivered: REQ-<n> — <why>`, never a silence. The nexus marks an entry passing from these lines once your PR is merged; you never edit `increment.json`.

### End every turn with a status block

The same four lines, at the end of your reply and of your log entry:

```
**Status:** <stage> · <working | waiting | blocked | done>
**Waiting on:** nothing | nexus: <Q-id or what> | resource: <name> | run: <what, started HH:MM, expected HH:MM>
**Next:** <the one concrete step you take next>
**Head:** `<sha>` · **PR:** #n | none yet
```

"Waiting for the run" is not a status: say which run, when it started and when you expect it. When your PR is merged or closed and your worktree is clean, say `done`: that is what lets the nexus archive you without asking anyone.

That block is also your **hand-over**. You can stop at any moment — a usage limit, a crash, a closed window — and whoever resumes you starts from your log's last block. Before a long run, or when your context is running low, make sure the last block says what is in flight and how to pick it up: the uncommitted work, the command that was running, the step after it.

### Questions and rulings

You never ask the user directly, and you never take a ruling in your own window. If the user answers you here anyway, forward their words to the nexus verbatim and wait: a ruling exists once it has a `DEC-n` in the register. Cite that id wherever you rely on it. "Under the user's ruling", with no id, is not something the nexus can accept.

A question the decisions register doesn't answer goes to the nexus in this shape, in your reply and your log — never as free text:

```markdown
### Q-<slug>-<n>: <the question, in one line>
**Stage:** <stage> · **Blocks:** <what cannot proceed until it is answered>
| Option | Buys | Costs | Cost to reverse |
|---|---|---|---|
| **A** — … | … | … | … |
| **B** — … | … | … | … |
**Recommendation:** <option> — <why>
**Checked:** <DEC-ids you read and why none answers it, or "register empty for this area">
```

architect-deep-dive's own question format carries all of this; in a sub-session, its question goes to the nexus, not to a user who isn't in this conversation. Keep working on whatever the question doesn't block. When the answer comes, record it in your log as given.

### Findings that cross slices

A finding that touches another slice, a shared module, or a decision already taken goes to the nexus as its own block — not as an aside in a paragraph about something else:

```markdown
### Cross-slice: <the finding, in one line>
**Affects:** <slices, modules or DEC-ids> · **Evidence:** <counts, query, file:line> · **Found in:** <stage>
```

### What you never do

- **Loosen a check to get green** — a tolerance, a skipped test, a parity rule, a threshold. Find the root cause, count it exactly, and send it to the nexus as a question. An exception is the user's decision, issued as a sign-off.
- **Take a number for a sequence-numbered file** (a migration). Build under the placeholder `<placeholder pattern>`; the nexus assigns the number at merge.
- **Coin a label series.** Ask the nexus for the next id in an existing one.
- **Edit `increment.json` or `env.md`.** An entry that is wrong, missing or not yours is a question; a command that is wrong is a question with its output.
- **Hold an exclusive resource without a lease** from the nexus, or past the lease's time limit without asking.
- **Write to <the read-only sources>**, or run anything against production. A check only the user can do in production goes in your log as `Owner check:` and the nexus collects it.
- **Run a formatter or linter over files you didn't change.** Format what you touched; a rewrite of someone else's files is out of scope however harmless.
- **Create a large scratch database or cache without checking free disk first.**
- **Merge.** The nexus merges, on the user's go.

### When you are one track of a PR

If you were started for one **track** of a brief with parallel tracks, the session that owns the brief is your nexus: send your questions, findings and status to it, not further up. Build only your track's criteria, touch only your track's area, read the brief and don't write to it, and record your ticks in your log. A change that needs another track's area, or a seam the brief fixed, is a question, not an edit. Your work ends at a GO on your track's head. The owner merges it and opens the PR.
