# The loop-back pass and the single track

> Companion to the [tdd](SKILL.md) skill. Read the first section when you were sent remediation
> slices from the ledger; read the second when your brief says you are one track. Everything else in
> SKILL.md applies unchanged — these sections say only what differs.

## You were sent remediation slices — the loop-back edge

This stage also runs as the fix step of the closing loop. When `tyr-verdict` returns NO-GO, its confirmed defects arrive as remediation slices already shaped like acceptance criteria, in `.workflow/ledger.md` under the last iteration's `### Remediation slices`.

- **Build them red-green exactly as you would a fresh brief** — one slice, one test seen red on the behavior, one commit.
- **A red run is a slice too.** When tyr-verdict's own run before the verdict was red, the slice is `- [ ] [blocker] R<id> — red run: <the failing tests, by name>` with no finding behind it (`ledger-format.md`, section "A red run before the verdict"). Make the named tests pass.
- **Close each slice as it goes green** by appending a line under `### Closed slices` in a new `## Iteration <n+1>` of the ledger:
  - a finding's slice: `- [x] F<id> — verified by <test name>`
  - a red-run slice, the same way: `- [x] R<id> — verified by <test>`
- **Never tick or move the line tyr-verdict wrote.** The ledger is an append-only log; the opening line and the closing line together are the record, and that record is how the loop proves it is making progress rather than circling.
- **Each closed slice is its own save point**, exactly as a criterion is (SKILL.md, **Save points**) — a remediation that breaks something else must be revertable without losing the ones that held.
- **Check your append.** Before the first one, copy the ledger as it stands to a scratch file outside the repo. Before handing off, run the checker from the repo root: `python3 -I <this skill's folder>/scripts/ledger.py check .workflow/ledger.md --against <copy>` (the grammar and the error codes are in `ledger-format.md`). A problem it reports is fixed, not explained in the response.
- **Then send the result back** through refactor-review → devils-advocate → tyr-verdict.

## Your brief says you are one track

When you were started for one track of a brief that lists **Parallel tracks**, the brief belongs to the session that started you, and you build only your part of it:

- **Build your track's criteria, in their order, and touch only your track's area.** A criterion that needs a change in another track's area, or in a seam the brief fixed, is a question for that session. Don't make the edit.
- **Read the brief at the path you were given, but don't write to it.** Every write to the brief described anywhere in SKILL.md — a revision, Base, a tick naming its test, a Ship checklist tick — goes to your stage log for the owning session instead. That session ticks the brief when it merges your track.
- **Your Base is the commit you were started from**: track 0's seams, already built. Record it in your stage log.
