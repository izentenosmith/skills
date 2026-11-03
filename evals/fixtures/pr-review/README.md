# pr-review fixture — `peer-review` on a partly-done PR (eval 49)

A pull request on Ledgerline, a small stdlib-Python billing service (invoices, late fees,
customer statements, card payments, the monthly CSV export).

```
make-history.sh   builds repo/ (gitignored — it is a nested git repo)
repo/             main: 203 commits, 2026-01-06 to 2026-10-20; feature/late-fee-config checked out, 3 commits on top
PR.md             the PR's title and description, as exported from GitHub
```

Build it with `../../setup.sh`, or directly:

```bash
./make-history.sh
```

The history is generated in loops, but every commit really changes the files it names. All
year, `billing/fees.py` (the fee policy) and the policy text in `billing/statement.py` have
changed together. The branch changes the first and not the second.

What is planted, and what a correct review says, is in `../pr-review.answers.md` — outside
this folder, because everything in it is copied into the run. This README and
`make-history.sh` are kept out of the run too (`HARNESS_ONLY` in `run.py`).
