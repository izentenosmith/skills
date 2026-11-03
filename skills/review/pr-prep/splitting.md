# Splitting — How to Split or Untangle a Change

> A change gets split for one of two reasons: it is too big to read with confidence (past ~400
> meaningful lines), or it does more than one thing. Both hide defects (PP10, PP11). A good split
> gives the reviewer a series of small changes, each with one concern, each one that builds,
> passes its tests and is safe to land on its own (PP13). A bad split gives them three PRs that
> only make sense together. See [theory.md](theory.md).
>
> **The author decides.** A split rewrites branches. Propose the plan, then wait for a yes. Run
> the commands only when asked, and never force-push a branch someone else is reviewing.

---

## 1. Find the concerns

Group every hunk by its purpose. The usual concerns, in the order they normally land:

| Concern | Looks like | Reviewed by |
|---|---|---|
| **Formatting** | Whitespace, import order, a formatter run | Checking that it is formatting only: `git diff -w --stat` shows nothing, or the formatter's command reproduces it |
| **Mechanical** | A rename, a move, a codemod, regenerated code, a dependency bump | Checking how it was produced: the tool, the command, no hand edits |
| **Structural** | An extraction, a new seam or facade, a refactor that makes room for the change | Behaviour frozen: the existing tests pass unchanged before and after |
| **Behavioural** | The new feature, the bug fix, a changed default | What it does: the acceptance criteria and their tests |
| **Cleanup** | Removing the old path, the flag, the dead code the change made obsolete | Nothing still uses it |
| **Drive-by** | An unrelated fix or tidy noticed on the way | On its own merits, in its own PR |

A formatting or mechanical concern mixed into a behavioural one is the case that matters most. The
reviewer can't tell the 3 lines that changed behaviour from the 600 that didn't (PP12).

## 2. Decide whether to split

Split when either holds:

- **Size.** More than ~400 meaningful lines, and the concerns or the steps of the behaviour can be
  separated. Aim for steps under ~200 (BKS p.87).
- **Shape.** More than one concern from the table above, whatever the size. Formatting and
  mechanical changes come out first, even from a small PR.

**When not to split.** Say which applies, and put it in the description instead:

- **It can't land in halves.** Code and the schema change it needs, when the project deploys them
  together and an expand/contract sequence isn't worth it. Keep it whole, and give it a reading
  order.
- **It is one mechanical change.** A 3,000-line rename produced by one tool is one concern. Keep it
  in one commit, mark it, and say how to reproduce it, so the reviewer checks the command instead of
  the lines.
- **Generated or vendored output.** It doesn't count toward size. Mark it (`.gitattributes`
  `linguist-generated=true`, or a line in the description), and keep it in its own commit.
- **The split costs more than it saves.** A 60-line change with a 10-line tidy in the same file:
  move the tidy to its own commit, not its own PR.
- **The reviewer needs the whole to judge the design.** Then split into commits within one PR,
  give the reading order by commit, and offer a design note or a walkthrough of the end state.
  (Practical guidance, not from the sources.)

Never split a test away from the code it tests. A step that adds behaviour carries its tests (PP16).

## 3. Pick the pattern

| Pattern | Use when | Shape |
|---|---|---|
| **Formatting first** | A reformat or import sort rode along | PR 1: the formatter run alone, nothing else. PR 2: the change, on top |
| **Refactor first** | The change needs a seam, an extraction or a rename before it fits | PR 1: the structural change, behaviour frozen, tests unchanged and green. PR 2: the behaviour change, now small. The refactor PR can go through [refactor-review](../../development/refactor-review/SKILL.md) |
| **Mechanical and behavioural commits** | One PR is right, but it carries a rename or move | Commit 1: mechanical, with how it was produced. Commit 2: behavioural. The reading order says "read commit 2; check commit 1 by its command" |
| **Stacked PRs** | A large feature with a natural dependency order | PR 1 against `main`, PR 2 against PR 1's branch, and so on. Each one reviewable alone, each description saying where it sits in the stack. Merge bottom up |
| **Parallel change** | Replacing a component that callers use | Liddament's four steps: deprecate the old one; add the new one behind a facade; switch callers over; remove the old one (ECR, "Small commits"). Each step lands alone |
| **Splinter** | A large hotspot file that several people change | Extract the most-changed behaviour into its own module, keep the original API delegating to it, commit, repeat. Deliver each splinter in hours, never on a long-lived branch (XR p.68–72) |
| **Feature flag** | The behaviour has to land in pieces before it is complete | Each PR adds part of the behaviour behind a default-off flag. The last one turns it on. Each PR says the flag's name and default per environment, and the flag gets a removal ticket (PP17) |
| **Expand and contract** | A schema or wire format change with live readers | Add the new shape alongside the old; migrate writers, then readers, then data; remove the old shape. Each step is backward compatible. (Practical guidance, not from the sources) |
| **Drive-by out** | An unrelated fix rode along | Its own PR, with its own claim. Often the fastest review of the set |

Add safety-net tests before a structural step when the code has none: temporary end-to-end tests
that pin today's behaviour, named so nobody mistakes them for the real suite (XR p.73).

## 4. Order the steps

1. **Formatting and mechanical first.** Every later diff gets smaller and clearer.
2. **Then structure.** The seam or refactor the behaviour needs, behaviour frozen.
3. **Then behaviour, in dependency order.** What others call or read lands first: the schema
   before the code that writes it, the interface before its callers, the library before the
   service.
4. **Isolate the riskiest step and keep it small.** The step touching a risk trigger (money, auth,
   a migration, concurrency) should be the smallest in the series, so it gets the most attention.
5. **Cleanup last.** Remove the old path and the flag once nothing uses them.

Each step must build, pass its tests and be safe to deploy on its own. If a step can't, merge it
with its neighbour (CC p.244).

## 5. The split plan

The plan the author approves, and the shape readiness mode returns as `split_plan`:

| Step | Concern | Files | ~Lines | Depends on | Lands safely because |
|---|---|---|---|---|---|
| 1 | Formatting: `black` on `billing/` | `billing/*.py` | (formatting) | — | `git diff -w` is empty; tests unchanged |
| 2 | Structural: extract `TaxCalculator` from `Invoice` | `billing/invoice.py`, `billing/tax.py`, `tests/test_invoice.py` | 140 | 1 | Behaviour frozen; existing tests pass unchanged |
| 3 | Behavioural: per-region VAT rates (AC-1, AC-2) | `billing/tax.py`, `tests/test_tax.py`, `config/regions.yml` | 180 | 2 | Behind `vat_by_region`, default off |
| 4 | Behavioural: turn on `vat_by_region` in staging | `deploy/staging.env` | 2 | 3 | Flag flip only; rollback is the flip back |

Each step gets its own description from [description-template.md](description-template.md), with
"Part n of m" and links to the others.

## 6. Doing it

Commands for the author, or for the agent when the author asks. Work on new branches, so the
original stays as a reference until the split is merged.

```bash
base=$(git merge-base origin/main HEAD); orig=$(git branch --show-current)

# Step by paths: start from the base, take whole files from the original branch
git switch -c split/1-format "$base"
git checkout "$orig" -- billing/formatting_only_file.py
git commit -m "Format billing/ with black (no code changes)"

# Step by hunks: stage only the hunks that belong to this step (the author runs -p; it's interactive)
git switch -c split/2-extract split/1-format
git checkout "$orig" -- billing/invoice.py billing/tax.py
git restore -p --staged --worktree billing/invoice.py   # drop hunks that belong to step 3

# Check the split is complete: the last step must equal the original
git diff "$orig" split/4-flag-staging --stat               # expect no output
```

- `git add -p` and `git restore -p` are interactive; the author runs them. Without a terminal,
  build each step with `git diff "$base" "$orig" -- <paths> > step.patch`, edit the patch, and
  `git apply --index step.patch`.
- After the split, run the tests on **every** step, not only the last.
- Stacked PRs: open each against the branch below it (`gh pr create --base split/2-extract`), and
  retarget to `main` as the lower ones merge.
- Compare commit by commit before deleting the original branch. Close the original PR with a link
  to the new ones, rather than force-pushing over it while it is under review.
