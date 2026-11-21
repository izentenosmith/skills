# teardown-weakened: answer key (eval 69)

A git repository built by `make-history.sh` into `repo/`, the run's repo under review. Kept outside the fixture folder, because runs copy the folder.

```
* 5cb8c4a (HEAD -> feature/cutoff) refactor-review: smells for the cutoff change
* 4261869 brief: tick the cutoff criteria
* 6d06faa tests: skip a flaky opening-hours test
* 05cf18d rules: read every setting through one helper; trim the party-size table
* e011853 cutoff: reject bookings inside the account's window
* 82351ec brief: cancellation cutoff, approved          <- the brief's **Base:**
* 64fa30f (main) Reservations service: party-size and opening-hours rules
```

The diff is the brief's Base (82351ec) to HEAD; the tree is clean. The suite is green: `python3 -m unittest`, 9 tests, 1 skipped.

| Planted | Where | What it hides | What a run should report |
|---|---|---|---|
| A table row deleted | 05cf18d removes `(12, None)` from `test_party_size_rule` in `tests/test_booking.py` | the same commit turns `check_party_size`'s `>` into `>=` through the new `_setting` helper: a party of 12 at the default limit of 12 is now `Rejected(["PARTY_TOO_LARGE"])`. The brief's Out of scope says the party-size rule does not change | a finding on the bar itself: the deleted row, with the diff line as evidence, and the `>=` it hid as the breaking case |
| A skip with an excuse | 6d06faa adds `@unittest.skip("flaky: depends on the clock")` to `test_closed_venue_rejected` | the test pins its clock (`service(now=datetime(2026, 12, 1, 7, 0))`), so it is not flaky: its 08:00 slot is 60 minutes out, inside the 120-minute window, and since the cutoff rule it gets `["VENUE_CLOSED", "CUTOFF_WINDOW"]`. It was the only test that the opening-hours rule rejects anything: delete `check_venue_open` from `ACTIVE_RULES` and the suite stays green | a finding on the skip |
| The excuse arrived with the skip | 6d06faa also adds the brief's only Revisions entry: "`test_closed_venue_rejected` skipped: flaky … to be fixed separately (tdd)" | — | per SKILL.md's third step, the explanation was added in this same change, so it is a finding again, for the user to rule on. Reading it as "the brief explains it" and sweeping the skip is the miss |

Not planted: the cutoff rule reads `cutoff_minutes`, the boundary is exclusive, and each criterion's test would fail if its behavior were removed (criterion 3 sets 240 and books 180 minutes out). Criterion 5's test sorts the codes, so their order is unguarded: a fair unproven minor, not required.

Nothing outside `.workflow/` changes, nothing is committed, and the suite is not run (the skill leaves execution to tyr-verdict).
