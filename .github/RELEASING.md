# Releasing

A release is an annotated git tag `vX.Y.Z` on `main`, with its entry in
[CHANGELOG.md](../CHANGELOG.md). Installs pin to the tag (see
[Pinning a version](../README.md#pinning-a-version)), so a tag is never moved or reused once
pushed: a mistake is fixed by the next patch release.

## 1. Pick the number

Read `## [Unreleased]` in the changelog against the rules at its top. Any major item makes it a
major release, otherwise any minor item a minor one, otherwise a patch.

## 2. Open a release pull request

On a branch from an up-to-date `main`:

1. Move everything under `## [Unreleased]` into a new section directly below it, headed exactly
   `## [X.Y.Z] - YYYY-MM-DD` (the date the release is cut). Leave `## [Unreleased]` in place and
   empty. Keep that heading form: tooling reads it.
2. Update the link references at the bottom of the changelog:

   ```markdown
   [Unreleased]: https://github.com/izentenosmith/skills/compare/vX.Y.Z...HEAD
   [X.Y.Z]: https://github.com/izentenosmith/skills/compare/vPREVIOUS...vX.Y.Z
   ```

3. If the README's pinning example names a version, move it to the new one.
4. Set the plugin's `"version"` to `X.Y.Z` in both `.claude-plugin/marketplace.json` and
   `skills/.codex-plugin/plugin.json`. Plugin installs update only when this number changes, and
   `check_repo.py` fails until both match the new changelog heading.
5. Run `python3 .github/scripts/check_repo.py` (0 problems), commit as
   `release: X.Y.Z`, and open the pull request. `main` needs the four CI checks green.

## 3. Merge, then tag on main

The owner tags after the pull request is merged, on the merge commit:

```bash
git switch main
git pull --ff-only origin main
git log -1 --oneline            # the release PR's merge commit
git tag -a vX.Y.Z -m "skills X.Y.Z"
git push origin vX.Y.Z
```

Push the tag by name, not with `--tags`, so no stray local tag goes with it.

## 4. Optionally, a GitHub release

Either from the tag's message:

```bash
gh release create vX.Y.Z --title "X.Y.Z" --notes-from-tag
```

or with the changelog section as the notes:

```bash
awk '/^## \[X\.Y\.Z\]/{f=1;next} /^## \[|^\[/{f=0} f' CHANGELOG.md > /tmp/notes.md
gh release create vX.Y.Z --title "X.Y.Z" --notes-file /tmp/notes.md
```

## 5. Check the pin

From an empty directory, confirm the tag installs:

```bash
npx skills add izentenosmith/skills@vX.Y.Z --list
```

and that the plugin installs at the new version (in a throwaway config, so your own is untouched):

```bash
export CLAUDE_CONFIG_DIR="$(mktemp -d)"
claude plugin marketplace add izentenosmith/skills
claude plugin install izentenosmith-skills@izentenosmith
claude plugin details izentenosmith-skills@izentenosmith   # X.Y.Z, Skills (46): 43 skills and 3 commands
```
