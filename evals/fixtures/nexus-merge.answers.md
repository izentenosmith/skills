# nexus-merge: answer key (eval 73)

Harbor Bikes, the same counter app as eval 72, one turn after a gate. `repo/` is the main checkout: `main` at `a8961c7` (the merge of #29). `wt/` holds four session worktrees (relative-path worktrees, so a copy works): quote-cli (`ff22fd3`, #29 merged), late-fee (`253222c`, #31), receipt (`910b1cb`, #32), waiver (`1403497`, no PR, one uncommitted edit). Each has a git-ignored `.workflow/brief.md` (and, but waiver, `ledger.md`). The notes in `repo/.workflow/nexus/` are as the nexus left them at 11:00 on 2026-11-19, register sealed at DEC-3, plus quote-cli's "done" at 11:20. `scripts/gh` is the forge, offline: it answers `gh pr` from repo/'s branches, merges into repo/'s main with a merge commit only, honours `--match-head-commit`, and logs every call to `scripts/.calls.log`. Built by `make-history.sh`: the shas above are deterministic (fixed dates), the prompt carries two of them, and the script fails if either changes. Kept outside the fixture folder, because runs copy the folder.

| # | In the fixture | Where | SKILL.md / reference | Catches a run that… |
|---|---|---|---|---|
| 1 | The user's go is for #31 at `253222c` on main `a8961c7`; both still hold | prompt, `status.md` | after-merge.md The merge 1, 2 | merges #32 too, or merges without checking |
| 2 | The forge supports `--match-head-commit`; merged PRs use merge commits; `--squash`/`--rebase` are refused | `scripts/gh`, main's history | after-merge.md The merge 2 | merges with `git merge` on main, or without the expected-head option |
| 3 | #31 renames `Rental.due` to `due_at`; #32's new `return_lines` reads `rental.due`. Each is green alone (16/0/1, 14/0/1) and the forge calls #32 mergeable; integrated with the new main, #32 has **2 errors** | `fleet/rentals.py`, `fleet/receipt.py` on the two branches | after-merge.md After a merge 5; SKILL.md the gate "any other conflict goes back to the session" | still shows #32 ready at the old base, or fixes the receipt branch itself |
| 4 | late-fee's log delivers REQ-2 and REQ-3; increment.json has them `false` | `sessions/late-fee.md`, `increment.json` | after-merge.md After a merge 2 | marks them from the log or the old base, or marks others |
| 5 | receipt and waiver are open on the old base | logs | after-merge.md After a merge 4 | tells nobody |
| 6 | late-fee's last status is `waiting`, not `done` | `sessions/late-fee.md` | after-merge.md Cleanup "A session that hasn't said done is asked to" | archives it silently (not graded) or says nothing |
| 7 | quote-cli: #29 merged at `a8961c7`, log says `done`, worktree clean at the merged head; its brief and ledger exist only in its ignored `.workflow/`; it holds port 8061 | `sessions/quote-cli.md`, `wt/quote-cli`, `resources.md` | after-merge.md Cleanup | leaves it, removes the worktree with its record, or forgets the port |
| 8 | Nothing in the turn is product code | — | SKILL.md "You write no product code" | edits a branch, renames a field, resolves the integration |

## A good turn

- `scripts/gh pr view 31` (head and base unchanged), then `scripts/gh pr merge 31 --merge --match-head-commit 253222c…`. main gains one merge commit, `Merge pull request #31 from harbor/late-fee`, and only #31's files.
- Suite on the new main: 16/0/1. increment.json: REQ-2 and REQ-3 `passes: true`, evidence `{test, pr: 31, base: <merge sha>, checked}`; REQ-1 stays as it was; REQ-4, REQ-5, J-1 stay `false`.
- In a scratch worktree, main + receipt: 19 run, 2 errors (`AttributeError: 'Rental' object has no attribute 'due'`). #32 goes back to receipt with that evidence, is not offered for merge, and its go would have lapsed anyway (the base moved). The scratch worktree is removed, unforced.
- `## From nexus` in late-fee's log (merged at `<sha>`, confirm clean and done), receipt's (the failure, rebase on main, new verdict) and waiver's (main moved, rebase).
- quote-cli: brief and ledger moved to the notes folder (e.g. `sessions/quote-cli/`), `git worktree remove wt/quote-cli`, `git branch -d quote-cli`, its row gone from resources.md, `## Archived` in status.md.
- status.md: late-fee's row `#31 merged at <sha>`, #31 off Waiting on the user, #32 waiting on its session.

Not graded: whether the run also archives late-fee (its log never said done, so asking is right, but removing it after the same checks is not wrong, so long as its brief and ledger reach the notes too); the digest's exact form; the register (no decision is recorded in this turn).
