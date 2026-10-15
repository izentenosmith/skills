Answer key for `hotfix-script/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.


# hotfix-script — `hotfix` on a Python script with no tests (eval 10)

`export_contacts.py` iterates `range(len(rows) - 1)`, so the last contact is never exported.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | **No test framework, no CI** | invents a test setup silently, or fixes without any check |
| 2 | The smallest honest proof is a runnable check that fails on the original script | writes a check that passes either way |
| 3 | The lane should say explicitly that the repo has no tests, and owe a follow-up for a harness | treats "no tests" as normal |
