# Merging, and after a merge — marking, cleanup and the end of the increment

Open this when a PR with a sequence-numbered file nears the gate, when the user gives a go to merge, in the turn a merge lands, at step 7's sweep of every turn when a session is `done` with its PR merged or closed, and when the last PR has merged. The gate that comes before a merge is in `gate.md`.

## Merging

Two of your rules meet here. You write no product code, and a renamed migration is product code. A GO and the user's go are each pinned to a head commit (rules 1 and 2), and any commit after them moves that head. So the number is settled before the final verdict, the session makes the rename, and the merge itself changes nothing.

**The number comes before the verdict.**

1. When a session reports that a PR with a sequence-numbered file is ready for its final tyr-verdict, or brings it to the gate still under a placeholder, assign the number: one above the highest of the base branch, the release branch, production, and any number already assigned to a PR that merges ahead of it. Record it in `resources.md`.
2. The session renames its placeholder, commits, re-runs its suite, and records its tyr-verdict GO on that head. You never make the rename. The gate is run on that head.
3. **If the base moved after the GO so that the number must change** — another PR merged with that number, or a hotfix took it — assign the new number, and the session makes one commit that renames the file and does nothing else. Then check two things yourself: `git diff --stat <GO head>..<new head>` shows that one file renamed, with no line changed anywhere, and the integrated suite (`gate.md`'s **Integrated with today's base**) passes on the new head. If both hold, carry the GO forward to the new head and say so in the digest: `GO at <old sha>, carried to <new sha>: rename only, V<n> → V<m>`. This is the one exception to rule 1, and it is narrow on purpose: a file name is the only thing a verdict on the code cannot be changed by. Anything else in that diff, and the GO has lapsed: the session needs a verdict on the new head.
4. The exception carries the GO, never the user's go. A go given at the earlier head has lapsed (rule 2): show the PR again at the new head.

**The merge.** Only on the user's go for that PR at that head, given in this conversation (rule 2).

1. Check that the PR's head and the base's are still the ones on the **Ready to merge** line the user answered. If either moved, the go has lapsed: re-run the gate and ask again.
2. Merge the PR with the forge's normal merge for this repo, the method its merged PRs already use. The check above and the merge are two moments, so where the forge supports it, merge with its expected-head option (`gh pr merge --match-head-commit <sha>`): a push that lands between them then fails the merge instead of going in unjudged. Never a force push, never a rewrite of the base branch, never a push to the base that goes around the PR. A merge the forge refuses — a conflict, a required check — is not worked around: the PR goes back through the gate.
3. Record the merge commit in `status.md`: the session's row reads `#n merged at <merge commit>`, and the PR leaves **Waiting on the user**.
4. Remove the gate's scratch integration worktree, unforced like every other. It is yours and holds only the trial merge; if git refuses, say what `git status` shows there and leave it for the user.
5. Go on to [After a merge](#after-a-merge), then the [Cleanup](#cleanup--when-a-sessions-work-is-merged) checklist.

## After a merge

1. Confirm the base branch gained only that PR's files.
2. Run the suite on the base's new head, and for each entry the PR delivered, see its test pass there. Only then set `"passes": true` in `increment.json`, with the test, the PR, the head and the date as its evidence.
3. An entry that was passing and whose test now fails goes back to `false`, becomes an `X-n`, and is routed to the session whose merge broke it.
4. Tell every open session that the base moved — the new head, and whether they must rebase or renumber — and update `status.md`.
5. Re-run the gate's **Integrated with today's base** line, on the new base, for every PR still listed under **Ready to merge**, before any of them can merge. Each was integrated with a base that no longer exists, and two branches that pass alone and fail together is the failure you are here to catch. The base move also lapses the user's go for each, exactly as a head move does (rule 2): show it again with the new base sha.

## Cleanup — when a session's work is merged

A finished session left standing costs disk, keeps leases and scratch names nobody is using, and makes `status.md` show work that is no longer running. So clean up in the same turn the merge lands, and sweep again at step 7 of every turn ([SKILL.md](SKILL.md#every-turn--read-route-record)). It needs no question to the user — it is the one thing you remove on your own — which is why every line below is a check that nothing can be lost.

- [ ] **It is finished.** The PR is merged on the forge at the head you gated, and the session's last status is `done`. A session that hasn't said `done` is asked to; it may still be writing its log.
- [ ] **Nothing lives only there.** A worktree with uncommitted or unpushed work is never removed: say what is in it and ask.
  - In its worktree, `git status` shows no uncommitted change and no untracked file, and the branch's head is the head that was merged — compare the two shas, since after a squash merge the branch's commits are not in the base and never will be. One commit past the merged head, or one untracked scratch file, and the worktree stays.
  - Ignored files do not block. Installed dependencies, build output and caches are in every worktree that ever ran the suite, and can be rebuilt; holding a worktree for them would hold all of them.
  - The session's own `.workflow/` brief and ledger are the one exception, and the reason to look at ignored files at all (`git status --ignored -- .workflow`): whether they are tracked, untracked or ignored, put them in the notes folder beside its log first — moved, or copied where they are committed, since deleting a tracked file is itself an uncommitted change — so the record outlives the worktree and the unforced remove below has nothing to refuse.
- [ ] **Its entries are marked**, as [After a merge](#after-a-merge) says; one whose test fails on the base's head goes to the user as failing again, not to the archive.
- [ ] **What it held is released.** Its leases, scratch names and ports in `resources.md`, and its place in any queue.
- [ ] **Archive the session**, with whatever your environment offers, **then remove the worktree and delete the merged branch** — `git worktree remove` and `git branch -d`, never their forced forms: both refuse when work would be lost, and a refusal is a reason to stop and ask, not to force. An unforced `git worktree remove` refuses only for modified or untracked files (and for submodules); ignored files do not stop it and go with the worktree, which is what the check above allows. After a squash merge `git branch -d` refuses a branch you have just shown to be merged: leave that branch and note it in `status.md` rather than forcing it. The remote branch is the forge's or the user's to delete.
- [ ] **Record it** under `## Archived` in `status.md`: the slug, the PR, the merge commit, the date, and that the worktree is gone.

**A PR closed without merging** is cleaned up the same way only when the user closed it or confirmed the close (a `DEC-n`) — anyone on the forge can close a PR — and its branch is pushed, so the work survives the worktree; the branch itself is kept. Otherwise report the close and leave everything in place. **A track's child** is cleaned up by its owner (`tracks.md`).

## When the increment is done

Merged PRs are not the test: **`increment.json` is.** The increment is done when every entry passes on the base branch's current head or carries the `DEC-n` under which the user dropped it — checked by one last run of the suite and the smoke check on that head, not by adding up the merges. An entry still failing when the last PR has merged is work nobody was given: say so, and ask the user whether it becomes a new slice or a dropped entry. You never close it yourself.

Then: every PR merged or closed, every session archived and its worktree removed (or kept, with the reason, for the user), `findings.md` with no open X-n that belongs to this increment, and the owner checks listed for the user. Close `status.md` with the increment's summary: entries passing and dropped, PRs merged, decisions taken, sign-offs issued, what was never verified.
