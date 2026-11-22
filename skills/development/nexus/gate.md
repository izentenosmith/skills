# The PR gate — every line, before a PR reaches the user

Open this at step 6 of every turn, for each PR a session says is ready, and again when a merge moves the base under a PR already listed as ready to merge. Every line is checked against the record — the session's log, its worktree, the forge's check results — never against the session's summary.

A line you could not check — a checker that would not run included — is written as **not verified**, never left out. The brief and ledger in the session's worktree are checked by script, from the repo root (`pipeline.md`, section "Checking your own output"; error codes in `ledger-format.md`):

```
python3 -I <this skill's folder>/scripts/brief.py  check  <worktree>/.workflow/brief.md
python3 -I <this skill's folder>/scripts/ledger.py check  <worktree>/.workflow/ledger.md
python3 -I <this skill's folder>/scripts/ledger.py status <worktree>/.workflow/ledger.md
```

- [ ] **GO on the head.** The log's last tyr-verdict is GO and names the PR's head now — or `git diff --stat <GO sha>..<head>` shows only `.workflow/` paths. `ledger.py check` reports no error and `status` prints `computed verdict: GO`: a GO the log states and the ledger does not compute is not a GO.
- [ ] **Brief approved.** `brief.py check` reports no `B` code, and the brief reads `**Status:** approved` with Revisions that cite the `DEC-n`. A PR built on a draft goes to the user as the approval decision, not as ready to merge.
- [ ] **In scope.** The diff touches only what the slice's brief covers; anything else, a formatter's rewrite included, is named.
- [ ] **Rulings cited.** Every decision the diff rests on names its `DEC-n`.
- [ ] **Findings settled.** `ledger.py status` lists nothing as `open red`, `open blocking` or `open inconclusive`. Minors the verdict carried as tracked follow-ups are allowed, and go on the digest's **Carried** line, where the user's go covers them.
- [ ] **Waivers ruled.** Every id on `ledger.py status`'s `waived:` line matches a `DEC-n` in the sealed register; one that does not counts as open.
- [ ] **Test counts with the skipped number.** Passed, failed **and skipped**, from the run on the head: a suite that skips tests is not the suite that passes them.
- [ ] **CI ran something.** A green check counts only if its log shows the tests ran.
- [ ] **Entries claimed, each with its test.** A `Delivers:` line for every `increment.json` entry the slice was given, naming a test that ran in the count above — or a `Not delivered:` line, which reaches the user as a decision, not a merge.
- [ ] **Required runs done** — the acceptance run, the full load, whatever the brief requires. A run that could not happen is not silently merged: the PR reaches the user with that run named as **not verified**.
- [ ] **Integrated with today's base.** In a scratch worktree, without credentials or production access, merge the latest base (and any PR going in ahead of this one) into the branch, then build, compile every test, and run the suite on the result. Conflicts that are rows added to the same shared document keep every row; any other conflict goes back to the session — you don't resolve code.
- [ ] **Mergeable** according to the forge, and targeting the base branch — a PR stacked on another is retargeted once its parent merges, before it does.
- [ ] **Numbered files** carry the number you assigned, renamed by the session before its GO (`after-merge.md`, section "Merging"): one above the highest of base, release branch and production, claimed by no other open PR.
- [ ] **Carried items listed** from the log's `Carried:` lines, or `none`: minors the verdict carried, noted smells, open ship-checklist items, `unconfirmed` Revisions entries — each `I01` from `brief.py check` and each `open minor` and `carried smell` from `ledger.py status` among them. A GO with no `Carried:` line goes back for it.
- [ ] **Not verified, said plainly**: the runs skipped, the environments not exercised, the owner checks still open.

A PR that fails a line goes back to its session with the line, the evidence and what would satisfy it. One exception: a session briefed before its contract asked for a brief approval or `Carried:` lines, whose PR was already at the gate, is not sent back for them — write each as **not verified** in the digest, so the user's go covers it knowingly.
