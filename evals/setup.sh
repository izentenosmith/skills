#!/usr/bin/env bash
# Prepare the eval fixtures. Run once after cloning.
#   - the five pipeline fixtures get a virtualenv with pytest (build output, gitignored)
#   - the incident fixture gets its git history built (a nested repo, gitignored)
#   - the compose fixture needs nothing: it is graded from files, never executed
set -euo pipefail
cd "$(dirname "$0")/fixtures"

echo "== pipeline fixtures =="
for f in base tdd refactor teardown verdict; do
  [ -d "$f/.venv" ] || python3 -m venv "$f/.venv"
  "$f/.venv/bin/pip" -q install pytest
  printf '%-10s ' "$f"
  (cd "$f" && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -1)
done

echo
echo "== incident fixture =="
./incident/make-history.sh

echo
echo "== compose fixture =="
printf '%-10s %s\n' compose "$(find compose -type f | wc -l | tr -d ' ') files, nothing to build"
