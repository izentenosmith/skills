# Self-Review — The Author's Checklist

> The reviewer is going to run an omission checklist on your change. Run it first. If you forgot
> something, the reviewer is likely to forget it too (BKS p.111), so this pass catches what review
> would miss as well as what it would find. See [theory.md](theory.md) for PP1, PP4 and PP15–PP17.
>
> **How to run it.** One item at a time. Take the item, sweep the **whole** diff for it, tick it or
> note what you found, then move to the next. Don't read the diff once trying to hold all twenty
> items in mind; one item across the whole change works better (BKS p.133–134). When an item turns
> up a new kind of problem, re-check the items you already ticked for the same kind.
>
> **Find, then fix.** Record what each item finds. Fix after the sweep, smallest change first, and
> show the list to the author before applying anything. A behaviour fix gets a red test first,
> through `tdd`.
>
> Each item is a true/false statement about the change. Tick it only when it is true.

Set up once:

```bash
base=$(git merge-base origin/main HEAD)     # or the PR's target branch
git diff --stat "$base"...HEAD; git status --short
```

---

## 1. Read it as a reviewer would

- [ ] **1. I read the whole diff once, top to bottom, outside my editor.** `git diff "$base"...HEAD`
  in a terminal, or `git diff --word-diff` for prose. A different view makes your own errors stand
  out (BKS p.95). List every hunk that surprised you. Those go in the description's "careful eye"
  section, or get fixed.
- [ ] **2. Every hunk serves the claim.** For each hunk, name the acceptance criterion it serves.
  A hunk that serves none is Tangling: move it to its own commit or PR
  ([splitting.md](splitting.md)), or drop it (PP7, PP11).
- [ ] **3. Every acceptance criterion has a hunk.** A criterion with no implementation is Missing:
  finish it, or move it to Out of scope and say so in the description (PP7).

## 2. Debris

```bash
git diff "$base"...HEAD -U0 | grep -nE '^\+.*(console\.(log|debug)|print\(|println!|dbg!|pdb\.set_trace|breakpoint\(\)|binding\.pry|debugger;|var_dump|\bdd\(|fmt\.Print)'
git diff "$base"...HEAD -U0 | grep -nE '^\+.*(\.only\(|\bfit\(|\bfdescribe\(|\bxit\(|@skip|@Ignore|@Disabled|t\.Skip|pytest\.mark\.skip)'
git diff "$base"...HEAD -U0 | grep -nE '^\+.*(TODO|FIXME|XXX|HACK)'
git diff "$base"...HEAD -U0 | grep -nE '^\+.*(eslint-disable|noqa|nolint|@ts-ignore|# type: ignore|@SuppressWarnings|rubocop:disable)'
```

A match is a candidate, not a verdict. Some projects print on purpose.

- [ ] **4. No debug output.** No print, log-at-debug or breakpoint line added for your own
  debugging. Logging that belongs in production is deliberate, at the right level, and carries no
  secrets or personal data (PP17).
- [ ] **5. No commented-out or dead code.** Version control keeps the old version (CC p.318, C5).
  No unreachable branch, unused function, parameter or import that the change added or orphaned
  (CC p.323, G9; CC p.324, G12).
- [ ] **6. No stray files and no secrets.** `git diff --name-status "$base"...HEAD`: no `.env`,
  scratch script, editor or OS file, local config, large binary, or file you don't recognise ("Oh,
  did I change that one?", BKS p.29). No key, token, password or connection string in the diff.
  If one was ever committed on the branch, removing it isn't enough; it needs rotating, and the
  author decides how to purge history.
- [ ] **7. No focused, skipped or silenced checks.** No `.only`, `fit`, skip or ignore added to a
  test, and no lint or type suppression without a reason next to it. Turning off a failing check
  trades a green build for later debugging (CC p.320, G4; CC p.344, T4).
- [ ] **8. Every TODO references a ticket.** Or it goes (ECR; PP3, PP17).

## 3. Tests

- [ ] **9. Every new behaviour and every bug fix has a test that fails without the change.**
  Name the test per acceptance criterion. Prove the failure when you can: run the new tests
  against the base in a scratch worktree, and record the command and the result.

  ```bash
  scratch=$(mktemp -d)/base
  git worktree add --detach "$scratch" "$base"
  cp path/to/new_test_file "$scratch"/path/to/    # the new or changed tests only
  (cd "$scratch" && <test command> path/to/new_test_file)   # expect a failure for the right reason
  git worktree remove --force "$scratch"
  ```

  A test that passes on the base doesn't capture the change. A test that fails only because it
  can't import or compile on the base proves nothing either. If you didn't run this, the
  description says "not run", not "tested" (PP8, PP16).

## 4. Omissions

These mirror the reviewer's omission list, lens J in
[peer-review's lenses.md](../peer-review/lenses.md#j--omissions), in the author's words. When the
two disagree, lens J is the reference.

- [ ] **10. No expected co-change is missing.** Run [the co-change check](#the-co-change-check)
  below. Each partner it lists is in the diff, or you can say why it doesn't need to change. A test
  file that usually changes with its code and didn't is the commonest one (XR p.50, p.184–186).
- [ ] **11. No clone twin was left behind.** Search for near-copies of each function you edited
  (`git grep -n '<a distinctive line from it>'`). Each got the same fix, or the difference is
  intended and named (XR p.107–108).
- [ ] **12. Every caller is updated.** For each changed signature, return shape, error, default or
  contract: `git grep` every call site, including scripts, jobs, other packages and tests.
- [ ] **13. Every new input is validated at the boundary, and every new call that can fail has an
  error path** that cleans up after itself.
- [ ] **14. A schema or semantics change has its migration, backfill and rollback story.** The
  rollback goes in the description.
- [ ] **15. Configuration exists in every environment.** New keys in the example env, the
  deployment manifests, the secrets store, and feature-flag defaults per environment.
- [ ] **16. Docs and user-facing text match.** README, API docs, changelog, help, error messages,
  translations.
- [ ] **17. The new failure mode is observable.** A log, metric or alert where an operator would
  need one; security events (denials, admin actions) logged.
- [ ] **18. Permissions are wired.** A new action is in the authorisation model; a new route is
  behind the auth middleware.
- [ ] **19. What the change made obsolete is gone, and the required bumps are made.** Old flags,
  config, docs and code removed or ticketed; version, build or changelog bumps the project
  requires (BKS p.63).
- [ ] **20. The un-happy siblings are handled.** A fix for one case of a pattern, and the other
  cases of the same pattern in the code you touched.

## 5. Run what CI runs

- [ ] **21. The checks CI runs pass locally, or are recorded as not run.** Build, tests, lint,
  type check, format. Record each command and its exact outcome for the description's "How to
  verify" section. Never write a result you didn't see (PP8). A flaky failure is re-run before it
  is called flaky, and named as flaky in the description.

## 6. Your own list

- [ ] **22. My personal list is clear.** Keep a short list of the mistakes reviewers keep finding in
  your changes. Start from the 2–5 you remember most recently, let it settle at 15–20 items, and
  retire an item after a few months with no catches (BKS p.94–95, p.111, p.135–137). Run it the
  same way, one item at a time. It belongs to you; it is never a measure of you (PP19).

---

## The co-change check

Files that usually change in the same commits as the ones you changed, and are absent from your
diff, are candidates for a forgotten change (XR p.184–186). This is a quick approximation from
`git log`; if the code-xray skill is installed, its `xray.py pr` command gives the fuller answer
with its exclusions.

```bash
base=$(git merge-base origin/main HEAD)
inpr=$(mktemp); git diff --name-only "$base"...HEAD > "$inpr"
git log --no-merges --after="12 months ago" --format='--%h' --name-only "$base" \
  | awk 'FNR == NR { inpr[$0] = 1; next }
         /^--/ { flush(); next }
         NF    { files[++k] = $0 }
         END   { flush()
                 for (p in pair) { split(p, f, SUBSEP)
                   if (rev[f[1]] >= 5 && pair[p] / rev[f[1]] >= 0.5)
                     printf "%s -> %s  %d of %d commits\n", f[1], f[2], pair[p], rev[f[1]] } }
         function flush(   i, j) {
           if (k > 0 && k <= 50)
             for (i = 1; i <= k; i++) if (files[i] in inpr) { rev[files[i]]++
               for (j = 1; j <= k; j++) if (!(files[j] in inpr)) pair[files[i], files[j]]++ }
           k = 0 }' "$inpr" - | sort
rm "$inpr"
```

Each line reads "changed file → absent partner, shared commits of the changed file's commits".
It counts history up to the branch point, skips merge commits and commits touching more than 50
files (a reformat co-changes everything with everything), and needs at least 5 commits on the
changed file before it says anything.

**Reading the result.**

- **80% or more** is a strong expectation. Either the partner is in the change, or the description
  says why it doesn't need to change. Readiness mode treats a missing strong partner as a `major`
  gap.
- **50–80%** is worth a look. Open the partner and decide.
- **Expected coupling** (a module and its test) that is absent is the most useful hit, because it
  usually means the test wasn't updated (XR p.50).
- **Lockfiles, changelogs and generated files** show up as partners often. Ignore them unless the
  project requires the bump.
- **Thin history** (under a few weeks of activity, or under about 150 commits) makes the numbers
  meaningless. Say the check was skipped and why (XR p.191).
- An override is fine. If the coupling is one you are deliberately breaking, say so in the
  description (XR p.186).
