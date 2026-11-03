# Answer key — pr-prep (eval 50)

The run is pr-prep in author mode on `feature/export-filters` (base `main`, merge-base = main~2).

**Tier: Heavy.** 456 meaningful lines (production + tests) in 7 files — over ~400 — and two concerns.

**Concerns.**
- Structural (277): `orderdesk/columns.py` (new, moved from export.py), `orderdesk/export.py` (`CsvExporter`), the
  import/rename in `orderdesk/api.py`, `tests/test_columns.py`, `tests/test_export.py`.
- Behavioural (#412, 179): `orderdesk/filters.py`, `orderdesk/api.py`, `tests/test_filters.py`.

**Split plan:** refactor first (behaviour frozen; `tests/test_api.py` and the moved tests pass unchanged), then the
filters on top. Proposed and left for the author's yes; no branch created, nothing rewritten.

**Alignment:** Missing + Tangling. AC-3 (remember the filters) has no hunk → Out of scope / follow-up, said plainly,
not ticked. AC-4 (no filters → unchanged) is contradicted by the default `ACTIVE_STATUSES`.

**Self-review findings (all left for the author; the prompt says don't change code):**
- debug print `orderdesk/filters.py:72`; commented-out code `orderdesk/api.py:39-41`; TODO without a ticket
  `orderdesk/filters.py:23`.
- the status filter has no test (AC-2: `status=`, unknown status → 400).
- co-change: `orderdesk/export.py -> docs/export-formats.md  22 of 25 commits` (88 %); the doc's Parameters table
  needs `from`, `to`, `status`.
- `python3 -m unittest discover -s tests -t .` (what `make test`/CI runs): Ran 41 tests, FAILED (failures=1),
  `test_export_includes_every_status` ('4' != '6'). Green on main.
- fold `wip` and `fix typo` (`--fixup` + `rebase -i --autosquash`, run by the author).

**Description:** claim, `#412`, AC-n checkboxes with their source (AC-3 not ticked, in Out of scope), what changed,
out of scope, how to verify with the real run (the failure quoted, never "all tests pass"), risk (finance's
month-end import; the default statuses) with rollback (revert), a reading order naming the files, a careful-eye note.
