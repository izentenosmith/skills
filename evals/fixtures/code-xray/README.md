# code-xray fixture (eval 51)

Harness-only: `run.py` keeps this file and `make-history.sh` out of the run (`HARNESS_ONLY`).

`make-history.sh` builds `repo/`: Shopwell, a stdlib-Python shop backend with a JavaScript checkout page,
303 commits from 2025-11-03 to 2026-10-27 by five authors (`@example.invalid`), deterministic from a fixed
seed. `HEAD` is `main`. `python3 -m unittest discover -s tests` passes inside it.

What is planted, and what the skill's script shows for it (`python3 -I skills/review/code-xray/scripts/xray.py
<cmd> --repo repo`), is in [../code-xray.answers.md](../code-xray.answers.md).
