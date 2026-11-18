---
name: heldout-evals
description: An eval marked "split": "heldout" in evals.json is a test set; its failures never edit the skill
type: convention
source: evals/evals.json (eval 59), evals/README.md "Held-out evals"
verified: 2026-11-18
volatility: low
---

Eval 59 (`hotfix-py`) is the first held-out eval, added 2026-11-18: hotfix on a fixture it was never
edited against, as a twin of eval 8. The key `"split": "heldout"` in `evals/evals.json` marks it.

**Why:** every other eval scores a skill on the fixture it was iteratively edited against, so the
suite's 0.99 on delta can't tell a better skill from one fitted to its fixture.

**How to apply:** never edit a skill from a held-out eval's failure, transcript or assertion text.
If it shows a real gap, write a new train eval for the same instruction and fix against that. The
rules are in `evals/README.md` under "Held-out evals". `run.py` and `check_repo.py`
ignore the key; `aggregate.py` reads it to keep a held-out eval out of the two overall lines and
give it a line of its own.
