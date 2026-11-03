# Analyses — What Each One Measures, How the Script Computes It, and How It Lies

> One section per analysis: **Measures**, **Computed** (what `scripts/xray.py` actually does),
> **Thresholds**, **Read it**, and **False readings**. Section 0 comes first because every number
> below is relative. One dirty input at the top of a ranking distorts everything under it (X19).
> The thresholds agree with peer-review's
> [history-signals.md](../peer-review/history-signals.md). This file goes further: how the
> script decides each one, and what to do when it misreads.
>
> The examples are real runs of the script on this skills repo (one author, 54 non-merge
> commits) and on a synthetic repo built to trip every signal.

---

## 0. Clean the input first

### 0.1 The data check, before any analysis

Run these and write down what they say. The answers become the report's **data-quality line**.

```bash
git rev-list --count --no-merges HEAD                 # commits in all; the window count is in the script's header
git rev-list --count --merges HEAD                    # 0 merges + 1 author often means squash or rebase merges
git shortlog -sne --no-merges HEAD | head -20         # aliases: one person under two names or emails
git log --no-merges --format='%h %s' --shortstat HEAD \
  | awk '/files? changed/ { if ($1 > 50) print prev, $1 } { prev = $0 }'   # mass commits
```

| You see | It means | Do |
|---|---|---|
| Under ~150 commits in the window | Every signal is weak (X20). The script adds a `thin history` caveat | Run the analyses, label every result weak, and make no refactoring target from history alone |
| One author, or one author with most of the commits | Solo project, squash merges, or migrated history credited to whoever migrated it (XR p.191). The script adds a caveat | Drop the social analyses (knowledge, fragmentation, reviewers, unfamiliar). Keep the technical ones (X19) |
| A "build master", bot or merge account at the top of `shortlog` | Migrated or merged history | Same: distrust the social data, and say so |
| The same person under two names | Aliases split their knowledge and inflate the author count | Add a `.mailmap` at the repo root. The script reads authors as `%aN`, so git applies the mailmap for it |
| Commits touching hundreds of files | Reformats, rename sweeps, vendor bumps, licence headers | The script drops commits over `--max-files` (default 50) from every count. Lower it if sweeps of 30–50 files are common (not from the sources) |
| A recent big move (`src/` → `packages/`) | Renames aren't followed. History restarts at the new path | See 0.3 |

### 0.2 What the script already leaves out

- **Merge commits** (`--no-merges`). Their changes are counted once, in the commits they merge.
- **Mass commits**, those touching more than `--max-files` files after exclusions. The count of
  dropped ones is in `meta.mass_commits_dropped`.
- **Excluded paths**, from every count: lockfiles (`*.lock`, `package-lock.json`, `pnpm-lock.yaml`,
  `go.sum`…), minified and source-map files, `vendor/`, `node_modules/`, `dist/`, `build/`,
  `third_party/`, generated code (`*_pb2.py`, `*.pb.go`, `*.generated.*`, `*.g.dart`,
  `*.designer.cs`), snapshots, `CHANGELOG*`, and binary assets. Add more with `--exclude GLOB`
  (repeatable). A pattern matches the full path or the bare file name.
- **Files that no longer exist** at the analysed commit are left out of the rankings.
- **Binary files.** `numstat` gives them no added-line count, and complexity is never measured on a
  blob with a NUL byte.

### 0.3 The pitfalls the script can't fix for you

| Pitfall | What it does to the numbers | What to do |
|---|---|---|
| **Squash merges** | One commit per PR, authored by whoever squashed. Coupling survives inside each squash, but the work's internal history is gone, and with several authors per PR the social data is wrong (XR p.191) | Say so on the data-quality line. Trust hotspots and coupling. Distrust knowledge, unless the squasher is the PR author |
| **Aliases** | One person counted as two authors. Fragmentation goes up, the main developer's share goes down, and a "departed" alias can raise false knowledge loss | `.mailmap`, then re-run (XR p.124) |
| **Mass commits** | A reformat makes every file co-change with every other and resets code age | `--max-files`. Check that the dropped count is plausible. A reformat under the cut-off still resets **age** and **trend**. Read a sudden flat jump in a trend as style, not complexity (XR p.39) |
| **Renames not followed** | The script reads with `--no-renames`. A moved file starts its history again at the new path, and its old commits belong to a path that no longer exists, so they drop out of the rankings. In this repo, the early skills lived at top-level paths like `tdd/` before moving under `skills/`, so their early history isn't counted | Start the window after the move (`--months`), or accept that a moved file looks young and cold. Say so for any file moved inside the window (not from the sources: the book only names renames as a difficulty, XR p.31) |
| **Generated code under a name the defaults miss** | A generated client or migration snapshot tops the ranking (XR p.191) | `--exclude 'src/generated/*'` and re-run. Check the top 10 by eye every time |
| **Docs and config counted as code** | The defaults keep Markdown and YAML, because in some repos (this one) they are the product. In this repo `README.md` is hotspot #1, with complexity 0 | In an application repo, add `--exclude '*.md'` (and docs folders) to match history-signals.md §0. A file at the top with tiny complexity is a magnet for edits, not debt (XR p.31, p.100) |
| **Copied fixtures and examples** | Near-identical directories make every file a "clone twin" of its copy. In this repo, `pr --base HEAD~8` returned 112 clone-twin signals, nearly all between copied eval fixtures. Excluding them also changed which commits counted as mass commits (3 dropped before, 1 after), because the cut-off counts files after exclusions | `--exclude 'evals/fixtures/*'` or the equivalent |
| **Pair and mob programming** | One author on commits several people made. Knowledge concentrates on whoever typed | Treat the knowledge data as team-level, not person-level (XR p.136, p.191) |
| **Paused projects** | Every file looks old | Windows count back from the analysed commit, never from today, so a paused repo reads as it was when work stopped (XR p.80–81) |

### 0.4 Windows

Every window counts back from a fixed commit: the merge-base in `pr`, `--rev` (default `HEAD`)
everywhere else. A re-run on the same commits gives the same answer, however much later it runs.

| Analysis | Window | Flag | Source |
|---|---|---|---|
| Hotspots, coupling | 12 months | `--months 12` (default) | XR p.100–101 |
| Rising hotspots | the same window, compared with one shifted back two months | fixed in the script | XR p.181 |
| Knowledge, fragmentation | about 3 months, or since the last reorganisation | `knowledge --months 3` | XR p.121, p.128 |
| Knowledge loss | the hotspot window: the main developer must still have commits in it | `knowledge` (12 months) | XR p.189 |
| Complexity growth (PR) | branch point to head | `pr` does it | XR p.180 |
| Complexity trend | the file's whole history | `trend` does it | XR p.104 |
| Active author | committed within 90 days of the analysed commit | `--active-days 90` | practical guidance (not from the sources) |

The `pr` command uses one window for everything, 12 months by default. Its knowledge reads fall
back to the file's whole history when the window has no commit to it.

---

## 1. Hotspots (`hotspots`, and `hotspot` in `pr`)

**Measures.** Change frequency (the interest rate) against size (the principal) (X5, X3).

**Computed.**
- Commits per file in the window, counting only files present at the analysed commit.
- Non-blank lines and indentation complexity of the file at that commit.
- Rank by commits, then by lines.
- A file is a **hotspot** when it ranks in the top 10% of the ranked files (at least 1, at most 10)
  **and** has at least 3 commits in the window.
- `Age (days)` is the time since the file's last change, counted back from the analysed commit.

**Thresholds.** The top ~10 per subsystem (XR p.108). The hotspots commonly take 10–15% of all
commits (XR p.112). Check that share on your own data: sum the top rows' commits and divide by the
window count.

**Read it.**
- Read the **Lines** column next to **Commits**. A large file with many commits is a hotspot. A
  tiny file with many commits is a configuration point or a magnet (a version file, a route table, a
  README).
- A large, hot file whose complexity is high goes to the X-ray (§3).
- Generic names (`utils`, `common`, `core`, `misc`) at the top suggest low cohesion: unrelated code
  pulled into one place (XR p.72, p.85).
- Run it per subsystem (`--repo` on a sub-checkout, or `--exclude` everything else) when one area
  dominates.

**False readings.**
- Generated or vendored code the defaults missed (0.3).
- A file refactored into something small still carries its old history (XR p.218). The Lines column
  shows it.
- **Untouchable code.** A module the team is afraid to change never becomes a hotspot. Hotspots
  supervise what does get worked on, so it doesn't end up the same way (XR p.44).
- An old hotspot, one with no recent commits, matters less (X21, XR p.218). Read the Age column.

On this repo the top of the list is `README.md` (19 commits, complexity 0), then
`evals/README.md`, then `evals/grade.py` (10 commits, 3,787 lines, complexity 6,350). Only the
third is debt in the X1 sense.

## 2. Rising hotspots (`rising` in `hotspots` and `pr`)

**Measures.** Where effort is moving (X8).

**Computed.**
- A second ranking from the same-length window shifted back two months.
- A file with at least 3 commits is **rising** when it climbed 10 or more places.
- A file that was unranked two months ago also counts as rising when it is now in the top 10 and
  more than 10 files are ranked.

**Read it.** New code taking a lot of effort. Confirm it's up to par while it is still cheap to
change (XR p.183). It isn't a problem on its own.

**False readings.** In a young repo, where most files didn't exist two months ago, nearly every
active file is "rising". In this repo, 9 of the top 10 are. Ignore the flag when the repo or
component is younger than about four months (not from the sources).

## 3. X-ray: the functions inside a hotspot (`xray FILE`, and `hot-function` in `pr`)

**Measures.** Change frequency per function, inside one file (X6).

**Computed.**
- `git log -p -U0` on the file, keeping only the window's commits, so mass commits are dropped here
  too.
- Each diff hunk is attributed to git's **hunk-header context**, the enclosing function line that
  git prints after `@@ … @@`. Each commit counts once per function.
- In `pr`, the functions the diff touches get their counts. `hot-function` fires when a touched
  function changed in at least **3** window commits **and** in at least **25%** of the file's
  window commits (practical guidance, not from the sources).

**Read it.**
- The top two or three functions usually hold most of the file's changes. They are the refactoring
  target, not the file (X6, X21).
- Then read those functions' length and nesting by eye.
- XR's examples are a 197-line function in a 2,500-line test file, and a 238-line function changed
  82 times in a year (XR p.41, p.105–106).

**False readings.**
- **Wrong context lines.** Git's default rule names the nearest line that starts at column 0. For
  Python methods that is the `class` line, and in data-heavy files it is a constant
  (`CHECKS = {` shows up in this repo's `evals/grade.py`). Turn on git's language driver locally,
  without touching the repo's tracked files:

  ```bash
  printf '*.py diff=python\n*.java diff=java\n*.go diff=golang\n*.rb diff=ruby\n*.rs diff=rust\n*.cs diff=csharp\n*.php diff=php\n*.kt diff=kotlin\n' >> .git/info/attributes
  ```

  On a test file of class methods, this turned "`class A:` 4 commits" into "`def m3(self, x):` 4
  commits".
- **Edits to a signature line** are attributed to the function *before* it, because the context is
  the line above the hunk.
- **Overloads** share a name, so they count as one unit. The book groups them on purpose (XR p.42).
- **Precision.** For an exact count of one function, use
  `git log -L:<funcname>:<file> --after=<window start> | grep -c '^commit '`. It is slow on large
  files (XR p.106, p.210–211).

## 4. Complexity trend (`trend FILE`)

**Measures.** Whether a file is getting harder to work in, against its own past (X7).

**Computed.**
- Up to `--samples` (default 12) evenly spaced revisions from the file's non-merge history, oldest
  first, plus the analysed commit itself when its content differs. A merge can produce content
  that no single branch commit had.
- For each sample: non-blank lines, indentation complexity (the sum of logical indentation levels,
  where a tab or four spaces is one level), the mean per line, and the maximum depth.

**Read it.**
- **Complexity rising faster than lines.** The mean goes up: code is being patched with nested
  conditionals (XR p.38).
- **Both rising together, mean flat.** The file is growing, not necessarily rotting. Ask whether it
  has too many responsibilities (XR p.44).
- **A drop that stays down** after a refactoring is the confirmation X22 asks for.

`evals/grade.py` in this repo went from 267 to 3,787 lines with the mean flat at about 1.7. That
reads as a file accumulating one check per eval, a cohesion question, not a nesting problem.

**False readings.**
- **An indentation-style change** (2 → 4 spaces, tabs → spaces) shows a jump or a drop that isn't
  real (XR p.39).
- **Two-space code** (JavaScript, Ruby, YAML) counts one level per four spaces, so it reads coarser.
  The trend still works. Absolute values across languages never compare (XR p.39).
- **Parallel branches** interleave by date. A dip followed by a rise can be two branches, not a
  refactoring. The last row is always the analysed commit.
- **Component trends** (summing the files of a component per month) aren't in the script. Run
  `trend` on the component's top files, or sum by hand (XR p.109–111).

## 5. Complexity growth on a branch (`complexity-growth` in `pr`)

**Measures.** New complexity this change adds, relative to the file's state on the branch (X7).

**Computed.**
- Complexity at the merge-base and at every commit on the branch except the head. The **minimum** of
  those is the baseline.
- Fires when the head is more than **10%** above the baseline, **and** at least **4** levels above
  it, **and** the merge-base version has at least **20** non-blank lines, **and** the file has a
  code extension.
- Weight `high` when the file is a hotspot, `medium` otherwise. New files never fire, because they
  have no merge-base version.

**Read it.** Name the likely cause (XR p.181):
- misplaced behaviour (extract a class),
- conditional logic squeezed in for a feature (a missing abstraction),
- or "the code is fine". Then say so and drop it.

In a hotspot it becomes a lens-N finding in peer-review. In a cold file it stays in the risk map.

**False readings.**
- A file that was deliberately simplified earlier on the branch and then regrown reads as growth
  against that low point. That is the intent: the minimum avoids "refactored, then regrew" (XR
  p.180).
- A large percentage on a small file is a small change. The 4-level and 20-line floors hold the
  worst of that back (XR p.181).

## 6. Code age (`Age (days)` in `hotspots`, and `stable-code` in `pr`)

**Measures.** Days since the file last changed, before the analysed commit (X12).

**Computed.**
- The last non-merge, non-mass commit to the path, across all history.
- `stable-code` fires for a **modified** file whose last change was **365 days** or more before the
  merge-base.

**Read it.**
- `stable-code` together with `knowledge-loss` on the same file is ignorant surgery. Ask for a test
  that pins the old behaviour, and for the rationale in the PR (XR p.83).
- In codebase mode, a package whose files have very different ages may be two concepts to split
  (XR p.88–89). The script doesn't group by package, so read the Age column for one folder at a
  time.

**False readings.**
- Age is shallow. Any touch, even a comment or a reformat under the mass-commit cut-off, makes a
  file young (XR p.91).
- A moved file looks young (0.3).

## 7. Change coupling (`coupling`)

**Measures.** Files that change in the same commits: the dependencies the code doesn't show (X9).

**Computed.**
- For every window commit, after exclusions and the mass-commit drop, each unordered pair of its
  files gets one shared commit.
- **Degree** = shared ÷ the average of the two files' window commits (Code Maat's definition, XR
  p.204).
- `cross_boundary` is true when the two paths' top-level folders differ.

**Thresholds.** At least **20** shared commits and a degree of at least **50%** to list a pair
(`--min-shared`, `--min-degree`) (XR p.49). For a warning, use 80% (XR p.185).

**Read it.**
- **Expected.** A file and its test. A handler and its schema. Fine, and a warning when the pair
  breaks.
- **Surprising.** Pairs across top-level folders, layers, services or languages, two unrelated
  tests, or two near-identical files. These point to copy-paste, a missing abstraction or a leaky
  protocol (XR p.50–52). These are the rows worth a sentence in the report.
- **Clusters.** One file coupled to many others is a change magnet. A cluster of co-evolving files
  across layers can be a bounded-context candidate, at more than 80% and 15–20 times a year (XR
  p.146–147).

**False readings.**
- **Split commits.** Code and its test committed separately show no coupling (XR p.54). Where commit
  messages carry ticket IDs, group by ticket by hand. The script has no logical change sets (XR
  p.164–165).
- **Small repos.** With few commits, nothing reaches 20 shared commits. On this repo
  `coupling` returns an empty table at the defaults. With `--min-shared 5` it finds
  `evals/README.md` ↔ `evals/grade.py` (9 shared, 82%), expected documentation of one tool, and
  `README.md` ↔ `skills/database/README.md` (7, 54%, cross-boundary), an index that lists every
  skill. Lower thresholds only with a weak-signal label.
- **Asymmetric pairs.** A small file that always changes with a big one gets a low degree, because
  the degree averages the two counts. Look at the shared count too.

## 8. Missing co-change (`missing-cochange` in `pr`)

**Measures.** A strongly coupled partner absent from this change (X10).

**Computed.** For each changed file, every partner with at least `--min-shared` (default 20) shared
window commits and a degree of at least `--warn-degree` (default 0.8) that exists at the head and
isn't in the change.

**Read it.** A question, never a block: "`billing/tax.py` changed with `billing/tax_rules.yaml`
in 30 commits (98%), but not here. Does this change need the rules file too?" peer-review's verifier
answers it from the code. Silence when nothing is missing.

**False readings.**
- A coupling being refactored away still fires until it decays. That is why it is a question with
  an override (XR p.186).
- Split commits hide real partners (§7).

## 9. Component-level coupling and hotspots (codebase mode, Deep)

**Measures.** The same analyses, with files grouped into logical components (X13).

**Computed.** Not by `xray.py`. The script marks `cross_boundary` on file pairs only. This snippet
groups paths into components (the first `DEPTH` folders, or your own mapping) and counts component
commits, contributors, fragmentation, and component-pair coupling. Run it from a scratch directory
with `python3 -I`, never inside the work tree:

```python
# python3 -I components.py REPO [DEPTH] [MONTHS] [TEAMS.csv]
# Component-level hotspots, coordination and change coupling. Read-only; run from a scratch directory.
import collections, csv, subprocess, sys
repo = sys.argv[1]
depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
months = float(sys.argv[3]) if len(sys.argv) > 3 else 12
teams = dict(csv.reader(open(sys.argv[4]))) if len(sys.argv) > 4 else {}   # author,team rows

def component(path):                   # edit this to map globs to your real components
    return "/".join(path.split("/")[:-1][:depth]) or "(root)"

def git(*args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout

ref = int(git("log", "-1", "--format=%ct", "HEAD"))
log = git("log", "--no-merges", "--no-renames", "--format=tformat:@@%at\t%aN", "--name-only", "HEAD")
revs, shared, people = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
for block in log.split("@@")[1:]:
    head, *files = [ln for ln in block.split("\n") if ln]
    at, author = head.split("\t", 1)
    if int(at) < ref - months * 30.44 * 86400 or not files or len(files) > 50:
        continue                       # outside the window, or a mass commit
    comps = sorted({component(f) for f in files})
    revs.update(comps)
    for c in comps:
        people[c][teams.get(author, author)] += 1
    for i, a in enumerate(comps):
        for b in comps[i + 1:]:
            shared[a, b] += 1

print("| Component | Commits | Contributors | Fragmentation |\n|---|---|---|---|")
for c, n in revs.most_common(15):
    total = sum(people[c].values())
    frag = 1 - sum((k / total) ** 2 for k in people[c].values())
    print(f"| `{c}` | {n} | {len(people[c])} | {frag:.2f} |")
print("\n| A | B | Shared | Degree |\n|---|---|---|---|")
for (a, b), n in sorted(shared.items(), key=lambda kv: -kv[1] / ((revs[kv[0][0]] + revs[kv[0][1]]) / 2)):
    degree = n / ((revs[a] + revs[b]) / 2)
    if n >= 10 and degree >= 0.3:      # component pairs co-change more often than file pairs; tune both
        print(f"| `{a}` | `{b}` | {n} | {degree:.0%} |")
```

It doesn't apply the script's path exclusions, so generated and vendored folders show up as
components of their own. Ignore them, or filter `files` the same way. It prints contributor counts
only, never names. With a `TEAMS.csv`, contributors become teams.

**Thresholds.** Book anchors for layered systems: about 30% coupling between layers when stable, up
to 70% when growing features (XR p.141–142). The cut-offs in the snippet are starting points, not
from the sources.

**Read it.**
- The component with the most commits is the **architectural hotspot**. Run the file-level analyses
  inside it next (XR p.99–102).
- Two components coupled at a high degree are, for change purposes, one component. Either the
  boundary is in the wrong place or a protocol between them leaks (XR p.167).
- When most commits cross layers, the layering separates the wrong concerns (XR p.142).

**False readings.** Every pitfall in §0 applies with more force, because one sweep touches every
component at once. The mass-commit cut-off is the only guard.

## 10. Clone twins (`clone-twin` in `pr`)

**Measures.** Near-duplicates of a changed file that may need the same edit (X11).

**Computed.**
- Candidates are the changed file's coupling partners (at least 3 shared commits and 50% degree),
  plus any file at the head with the **same file name** in another folder.
- Similarity is the Jaccard index of their sets of normalised lines: stripped, longer than 3
  characters, containing a word character, with at least 10 such lines in each file.
- At **0.5** or more it is a twin. Weight `high` when the twin isn't in the change ("check it needs
  the same edit"), `low` when both changed ("check they got the same edit").
- A pair where both files changed is listed twice, once from each side.

**Read it.** Open both and diff them. A guard, condition or type check in one and missing in the
other is a candidate latent bug for peer-review's lens J or A (XR p.107–108). Otherwise ask for the
difference to be named, or the twins moved next to each other (proximity, XR p.63–67).

**False readings.**
- **File level, not function level.** The book's clones are functions. A shared function inside two
  otherwise different files won't reach 0.5.
- **Clones that never co-changed and have different names** aren't candidates. That fits X11
  (uncoupled clones cost little), but it means the check is not a duplicate finder.
- **Fixtures, examples and templates** copied on purpose (0.3).

## 11. Knowledge: main developer, fragmentation, knowledge loss (`knowledge`, and `knowledge-loss` in `pr`)

**Measures.** Who knows each file, how diffused the work is, and where the knowledge has left (X14,
X15, X16).

**Computed.**
- **Main developer**: the author with the most added lines to the file in the window. When no
  lines were added (deletions only), the author with the most commits. When the window has no
  commit to the file, the whole history is used.
- `main_share`: that author's share of added lines.
- **Authors**: distinct authors in the window.
- **Fragmentation**: `1 − Σ(cᵢ/C)²` over per-author **commit** counts. 0 is one author; near 1 is
  many with diffused effort (XR p.122–123).
- **Active**: the author has a commit, to any file, within `--active-days` (default 90) of the
  analysed commit.
- **Knowledge loss**: the main developer is inactive **and** holds at least 50% of the added lines.

**Read it.**
- **Knowledge loss on a hotspot is the urgent kind.** Triage the rest by criticality, then age. Old
  abandoned code matters less (XR p.189).
- In codebase mode, run it as a **simulation**. Ask which areas would be orphaned if a known leaver
  were inactive, while they can still hand over (XR p.189). The script can't mark someone as
  leaving. Read their files from the full table by hand. That is routing, not rating.
- **High fragmentation in a hotspot** is the diffusion-of-responsibility pattern: many minor
  contributors and no owner (XR p.126). It calls for an owner, or for areas of responsibility,
  not for more people.

**False readings.** Aliases, squash merges, pairing and migrated history (0.3). An author on leave
reads as inactive. A main developer who moved teams but is still reachable counts as "lost" here
and isn't, in practice. The flag is a prompt to ask, not a fact about anyone.

## 12. Unfamiliar author and suggested reviewers (`unfamiliar`, `reviewers` in `pr`)

**Computed.**
- `unfamiliar` fires when the change's author (`--author`, default the head commit's author) never
  committed to the file in all history **and** the file has 3 or more authors in the window.
- **Suggested reviewers**: for every changed file with history, each active author other than the
  change's author adds their added-line share of that file. The top `--reviewers` (default 3) are
  suggested, with the files they know.

**Read it.**
- `unfamiliar` raises review depth on that file. A minor contributor in fragmented code is where
  defect risk rises (XR p.121, p.124). It says nothing about the author's skill.
- The reviewer list is a routing suggestion: these people know the touched code (XR p.187). Add
  someone from a consuming team to widen knowledge boundaries (XR p.127, p.161). The `weight` sorts
  the suggestions and is never shown as a score.

**False readings.** The head commit's author may be a bot or whoever rebased. Pass `--author` when
you know better.

## 13. Coordination and team boundaries (codebase mode, Deep, by hand)

**Measures.** Where teams have to coordinate to change the code (X14, X17).

**Computed.** Not by `xray.py`. Use the component snippet (§9) with a `TEAMS.csv` of `author,team`
rows (XR p.129, p.205). Contributors then count teams, and fragmentation is across teams.

**Read it.**
- **A component many teams change** is an operational boundary that is too wide. Find an owner,
  split it, or accept the coordination knowingly (XR p.126–131).
- **Two coupled components owned by different teams** need coordination on every change. The
  remedies run from living with it, if the teams are close, to transferring ownership, redefining
  the protocol, or merging the components. Re-measure a few weeks later (XR p.167–168).
- **Integration tests** often carry most of the coordination, because every team edits them (XR
  p.132).

**False readings.** A wrong or stale team map. People on several teams, such as coaches or
platform
engineers, belong in a team of their own or out of the map (XR p.136). Keep the map out of the
report. Only team names appear, never a person's.

---

## Thresholds at a glance

| Threshold | Value | Flag | Source |
|---|---|---|---|
| Thin history | < 150 commits in the window | fixed | XR p.191 |
| Mass commit | > 50 files after exclusions | `--max-files` | practical guard (not from the sources) |
| Hotspot | top 10% of ranked files (1–10), ≥ 3 commits | fixed | XR p.108, p.112 |
| Rising | climbed ≥ 10 places vs two months earlier | fixed | XR p.181–182 |
| Coupling listed | ≥ 20 shared commits, degree ≥ 50% | `--min-shared`, `--min-degree` | XR p.49 |
| Missing co-change | ≥ 20 shared commits, degree ≥ 80% | `--min-shared`, `--warn-degree` | XR p.185 |
| Complexity growth | > 10% over the branch minimum, ≥ +4 levels, ≥ 20 base lines, code file | fixed | XR p.180–181 (floors: practical guidance) |
| Stable code | ≥ 365 days since last change | fixed | XR p.83 (the year: practical guidance) |
| Knowledge loss | main developer inactive, ≥ 50% of added lines | `--active-days` (90) | XR p.188–189 (the 90 days and 50%: practical guidance) |
| Unfamiliar | author never touched the file, ≥ 3 authors | fixed | XR p.121, p.124 |
| Hot function | ≥ 3 commits and ≥ 25% of the file's commits | fixed | practical guidance (not from the sources) |
| Clone twin | line-set Jaccard ≥ 0.5 | fixed | practical guidance. The book uses co-change plus similarity (XR p.57, p.107) |
