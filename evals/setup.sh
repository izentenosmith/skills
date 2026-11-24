#!/usr/bin/env bash
# Prepare the eval fixtures. Run once after cloning.
#   - the five pipeline fixtures, and the variants the later pipeline evals (60-75) use, get a virtualenv with pytest (build output, gitignored)
#   - the incident, release-notes, review, repo-memory, refactor-standalone, teardown-empty, teardown-weakened and nexus (72-73) fixtures get their git history built (nested repos, gitignored)
#   - the compose fixture needs nothing: it is graded from files, never executed
set -euo pipefail
cd "$(dirname "$0")/fixtures"

echo "== pipeline fixtures =="
for f in base tdd refactor teardown verdict tdd-planted tdd-contradiction brief-nexus design-round2 design-adr \
         at-red-baseline at-stub refactor-uncovered brief-archive; do
  [ -d "$f/.venv" ] || python3 -m venv "$f/.venv"
  "$f/.venv/bin/pip" -q install pytest
  printf '%-10s ' "$f"
  # A report, not a gate: the teardown and verdict fixtures carry planted defects,
  # one of which fails outside roughly 06:00-18:00 local time, and tdd-contradiction
  # ships six acceptance tests that are red by design, and at-red-baseline's suite is red
  # before any work (eval 64). Setup builds the venvs;
  # a red fixture suite is expected and must not stop it.
  (cd "$f" && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -1) || true
done

echo
echo "== tyr-verdict fixtures (evals 70-71) =="
# verdict-red's suite is red by design (two failures on a fixed clock); verdict-bar's is green with one skip.
for f in verdict-red verdict-bar; do
  [ -d "$f/.venv" ] || python3 -m venv "$f/.venv"
  "$f/.venv/bin/pip" -q install pytest
  printf '%-12s ' "$f"
  (cd "$f" && .venv/bin/python -m pytest tests/ -q -p no:cacheprovider 2>&1 | tail -1) || true
done

echo
echo "== hotfix-accounts (eval 76) =="
# Standard library only (CI runs unittest), so a bare venv: run.py treats a
# fixture with tests/ as unbuilt until it has .venv/bin/python.
f=hotfix-accounts
[ -d "$f/.venv" ] || python3 -m venv --without-pip "$f/.venv"
(cd "$f" && .venv/bin/python -m unittest discover -s tests -p '*_test.py' 2>&1 | tail -1) || true

echo
echo "== incident fixture =="
./incident/make-history.sh

echo
echo "== release-notes fixture =="
./release-notes/make-history.sh

echo
echo "== review fixtures (evals 49-53) =="
for f in pr-review pr-prep code-xray test-review concurrency; do
  printf '%-12s ' "$f"
  ./$f/make-history.sh
  echo "$(git -C $f/repo rev-list --all --count) commits"
done

echo
echo "== repo-memory fixture (eval 55) =="
./repo-memory/make-history.sh

echo
echo "== refactor-standalone fixture (eval 66) =="
./refactor-standalone/make-history.sh
echo "$(git -C refactor-standalone/repo rev-list --all --count) commits"

echo
echo "== devils-advocate fixtures (evals 68-69) =="
for f in teardown-empty teardown-weakened; do
  printf '%-18s ' "$f"
  ./$f/make-history.sh
  echo "$(git -C $f/repo rev-list --all --count) commits, HEAD $(git -C $f/repo rev-parse --short HEAD)"
done

echo
echo "== nexus fixtures (evals 72-73): git histories, and nexus-merge's worktrees (git 2.48+) =="
for f in nexus-setup nexus-merge; do
  EVALS_FIXTURE_BUILD=1 ./$f/make-history.sh
done

echo
echo "== compose fixture =="
printf '%-10s %s\n' compose "$(find compose -type f | wc -l | tr -d ' ') files, nothing to build"
