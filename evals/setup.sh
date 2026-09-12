#!/usr/bin/env bash
# Create the per-fixture virtualenv the eval runs need. Run once after cloning.
# The venvs are gitignored: they are build output, not fixture content.
set -euo pipefail
cd "$(dirname "$0")/fixtures"
for f in base tdd refactor teardown verdict; do
  [ -d "$f/.venv" ] || python3 -m venv "$f/.venv"
  "$f/.venv/bin/pip" -q install pytest
  printf '%-10s ' "$f"
  (cd "$f" && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -1)
done
