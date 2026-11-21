# Environment — booking rules, increment 3
**Recorded:** 2026-11-12 10:10 at `4e1b7a9` · **Sources:** README.md, the CI workflow

## Commands
- **Test (full):** `.venv/bin/python -m pytest tests/ -q` — from CI
- **Test (focused):** `.venv/bin/python -m pytest tests/test_booking.py -q -k <name>`
- **Lint / type-check:** none
- **Build:** none
- **Start:** none: a library
- **Smoke:** none

## Baseline
- **Suite on `4e1b7a9`:** 4/0/0, under a second
- **Red on the base:** none
- **Smoke on `4e1b7a9`:** none

## Per session
- the worktree's `.venv` is already built
- **Working files:** the sessions' `.workflow/` is untracked and not ignored in this repo
