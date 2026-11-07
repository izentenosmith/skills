# repo-memory fixture (eval 55)

Harness-only: `run.py` keeps this file and `make-history.sh` out of the run (`HARNESS_ONLY`).

`make-history.sh` builds `repo/`: Larkspur, a stdlib-Python appointment-reminder service (reminders, SMS
through the Relay provider, an email fallback, a billing export), 12 commits from 2026-09-01 to
2026-11-04 by two authors (`@example.invalid`), deterministic. Shared memory (`.memory/`) was installed on
2026-09-08 and dreamed once on 2026-10-05. A month of code changes and careless in-session captures
followed. `python3 -m unittest discover -s tests` passes inside it.

What is planted, and what `memlint.py` shows for it, is in
[../repo-memory.answers.md](../repo-memory.answers.md).
