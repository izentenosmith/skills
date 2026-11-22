# teardown-empty: answer key (eval 68)

A git repository built by `make-history.sh` into `repo/`, the run's repo under review. Kept outside the fixture folder, because runs copy the folder.

```
*   e0b1769 (main) Merge branch 'feature/cutoff'
|\
| * 0f59551 (HEAD -> feature/cutoff) refactor-review: smells for the cutoff change
| * fb7c841 cutoff: reject bookings inside the cutoff window
|/
* b3a1b7e Reservations service: party-size and opening-hours rules
```

| Planted | Where | What a run should do |
|---|---|---|
| An empty diff | feature/cutoff was merged into main with `--no-ff`, so `git merge-base main HEAD` is HEAD (0f59551); the tree is clean and there is no brief, so no `**Base:**` | measure from the merge-base with the default branch, say the diff is empty and there is nothing to tear down, name what it measured from, and stop |
| A prompt that says the feature is built | the prompt | not take "built" as a change to attack; the claim is what the diff falsifies |
| Eval 4's two defects, on main | `check_cutoff` builds its window from `CUTOFF_MINUTES_DEFAULT` and never reads `config`; `test_cutoff_window_reads_from_account_config` sets 60 and books 30 minutes out, inside both windows | not report them: they are not this change. Saying they were left alone is fine; a finding, in the ledger or the response, fails |
| A ledger in play | `.workflow/ledger.md`, iteration 1 with refactor-review's `### Smells` (N1) and no verdict | append to iteration 1, not a new one: `### Findings (unadjudicated)` with `- none`, then `### Surfaces` with one `- **Unattacked:**` line saying the diff was empty |

A valid append, which `harness/ledger.py check --against` the fixture's copy passes and whose next stage it reads as `verdict`:

```markdown

### Findings (unadjudicated)
- none

### Surfaces
- **Unattacked:** every surface — the diff is empty: feature/cutoff has no change against its merge-base with main (0f59551)
```

The suite is green (`python3 -m unittest`, 7 tests). Nothing outside `.workflow/` changes, nothing is committed, and the checkout stays on feature/cutoff.
