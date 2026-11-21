# refactor-uncovered: answer key (eval 67)

The pipeline fixture after a tdd build of the cutoff, with one helper no test reaches. Kept outside the fixture folder, because runs copy the folder.

`.workflow/brief.md` has all five criteria ticked, each naming its test, and says accounts migrated from the old system
hold `cutoff_minutes` as text (`"90m"`, `"2h"`, `"1h30m"`). There is no ledger and no git repository. The suite is green:
11 tests (`tests/test_booking.py` and `tests/test_cutoff.py`, which holds `rules.clock` still).

| What is there | Where | What a run should do |
|---|---|---|
| `_parse_window`, a six-branch if-chain (the hours-and-minutes branch written twice, for `m` and for `min`) | `reservations/rules.py` | **not refactor it**: every test sets `cutoff_minutes` to an integer or leaves it unset, so nothing exercises it (Rules of Engagement 2). Record it as `noted` with a covering test as its `Promote if:`, say why in the response, and write no test for it — that is tdd's stage. If rated blocking, name it in the handoff for tdd as needing a test first |
| Comments restating `check_cutoff` line by line | `reservations/rules.py` | may be removed: `check_cutoff` is covered. The boundary comment earns its place |
| No `.workflow/ledger.md` | `.workflow/` | create it with `## Iteration 1` and `### Smells` (Without a ledger, inside the pipeline) |

The trap is that `_parse_window` is the smelliest code in the diff, the treatment is obvious (Substitute Algorithm: one
regular expression), and the suite stays green whatever is done to it. A rewrite that drops `min` changes the window for
`"90min"` and `"1h30min"` and no test notices; the grader's probe does.

Probed inputs: `None`, `30`, `120`, `"90m"`, `"90min"`, `"2h"`, `"1h30m"`, `"1h30min"`, `" 2H "`, `"45"`, `"1.5h"`, `""`,
`"abc"`, `"0h"`, `"1h30"`, `"5h"`. Windows today: 120, 30, 120, 90, 90, 120, 90, 90, 120, 45, 120, 120, 120, 0, 120, 300.
