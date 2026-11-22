# refactor-standalone: answer key (eval 66)

refactor-review used outside the pipeline. Kept outside the fixture folder, because runs copy the folder.

`make-history.sh` builds `repo/`: **parcels**, a stdlib-Python shipping-quote library (`python3 -m unittest discover -s tests -t .`).
Fixed dates and authors, so the SHAs are stable:

| Commit | Branch | What |
|---|---|---|
| `ceb1cb8` | `main` | `standard_quote`, `format_label` and their tests |
| `e9dfce9` | `feature/express-quotes` | `express_quote`: 60% over standard, a Saturday surcharge; five tests |
| `13a1664` | `feature/express-quotes` (checked out, clean) | no Saturday surcharge abroad; one more test |

`main...HEAD`: `parcels/rates.py` +18, `tests/test_rates.py` +23/−1. Suite: 13 tests, OK. There is no `.workflow/`.

| What is there | Where | What a run should do |
|---|---|---|
| A clean tree on a branch | `repo/` | review `main...feature/express-quotes` (the merge-base with `main`), and say so; the working diff is empty |
| No `.workflow/`, so no brief and no ledger | `repo/` | create neither; put the noted smells and their `Promote if:` lines in the response; say the carried smells were unavailable |
| Duplicate Code: `express_quote` repeats `standard_quote`'s zone check, weight check and price | `parcels/rates.py` | fix it (worthwhile or blocking): e.g. Extract Function `_base_price` returning the **unrounded** price, used by both. Touching `standard_quote` (on `main`) is allowed: the new code cannot be cleaned without it |
| Comments restating every line of `express_quote` | `parcels/rates.py` | remove them; name the 1.6 and 5.00 if it likes |
| A behaviour trap: express rounds once, at the end | `parcels/rates.py` | keep it. `express = standard_quote(...) * 1.6` rounds twice: 2.345 kg domestic gives 10.21, not 10.20. The tests use whole kilos and stay green; the grader's probe does not |
| Smells on `main`, outside the diff: a Long Parameter List and comment-narrated duplication | `parcels/labels.py` `format_label` | leave the file byte-identical; at most record it as `noted` with a promote condition |
| Save points | — | one technique, tests, commit, on `feature/express-quotes`; every new commit green; `main` not moved |

Not graded: which smells are found beyond the duplication, which severities, the commit messages, the `**Pass:**` line and the stopping rule (eval 3 grades those).
