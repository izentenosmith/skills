# pr-prep fixture (eval 50) — harness only

`make-history.sh` builds `repo/`: **orderdesk**, a stdlib-Python orders service whose CSV export
finance pulls weekly. `main` has 162 commits (2026-03 to 2026-10); the author's branch
`feature/export-filters` (Dana Ortiz, 4 commits, 2026-10-05..08) is checked out. `issues/412.md` is the
ticket. This README and `make-history.sh` are kept out of the run (`HARNESS_ONLY` in `run.py`); the answer
key is `../pr-prep.answers.md`.

Planted:

| # | What | Where |
|---|---|---|
| 1 | 456 meaningful lines (`git diff --numstat main...HEAD`), two concerns: a refactor (277: column registry to `orderdesk/columns.py`, `CsvExporter`, `select_columns` → `resolve_columns`) and the #412 filters (179) | commits 1 and 2–4 |
| 2 | AC-3 (remember the filters between sessions) not implemented; `PrefsStore` already remembers the column choice | `issues/412.md`, `orderdesk/prefs.py` |
| 3 | a debug `print(` in `apply_filters`, three lines of commented-out code in `handle_export`, a TODO with no ticket | `orderdesk/filters.py:72`, `orderdesk/api.py:39-41`, `orderdesk/filters.py:23` |
| 4 | the status filter has no test; `tests/test_filters.py` covers the date range and file name only | `tests/test_filters.py` |
| 5 | `orderdesk/export.py` changed with `docs/export-formats.md` in 22 of its 25 commits on main (88 %); the branch doesn't touch the doc, whose Parameters table lacks `from`, `to`, `status` | history |
| 6 | one test fails on the branch (passes on main): `test_export_includes_every_status`, because `ACTIVE_STATUSES` hides cancelled and refunded when no `status` is given (breaks AC-4) | `tests/test_api.py` |
| 7 | `wip` and `fix typo` commits to fold | branch history |
| 8 | main moved on by two commits after the branch point (a two-dot diff shows them reversed) | `orderdesk/countries.py` |

The history is about 160 commits because self-review.md treats under ~150 commits as too thin for the
co-change check; most are one-line registry additions (carriers, shipping countries, warehouse closures).
