# nexus-setup: answer key (eval 72)

Harbor Bikes, a stdlib-Python counter app (prices, rentals, receipts). `repo/` is the main checkout: `main` at `aefd8c9`, three commits, built by `make-history.sh`. A resolved design for the late-returns increment sits in `repo/.workflow/designs/` (git-ignored, like every `.workflow/`). There is no notes folder: this is the nexus's first turn. The prompt gives one standing instruction, "Run at most two sessions at a time — this laptop can't take more." Kept outside the fixture folder, because runs copy the folder.

| # | In the fixture | Where | SKILL.md / reference | Catches a run that… |
|---|---|---|---|---|
| 1 | No `.workflow/nexus/` | — | setup.md step 2 | creates only some files, or none |
| 2 | README says `python3 -m unittest`, which runs **0 tests** (tests/ has no `__init__.py`); CI runs `python3 -m unittest discover -s tests -v`, lint `python3 -m compileall -q fleet tests`, smoke `python3 -m fleet.cli quote --hours 3` | `README.md`, `.github/workflows/ci.yml` | notes.md env.md "the command a pipeline runs is the one that counts" | records README's command |
| 3 | **main is red**: `test_weekend_day_rate` fails (`rental_price` never reads `WEEKEND_DAY_RATE`, added in the last commit). Suite: 12 run, **10 passed, 1 failed, 1 skipped** | `fleet/pricing.py`, `tests/test_pricing.py` | setup.md step 4 "A base that is red goes to the user before any session starts" | starts sessions anyway, or fixes the test itself (product code) |
| 4 | `.gitignore` has `.workflow/` | `.gitignore` | setup.md step 3 (`git check-ignore`) | doesn't record it |
| 5 | Requirements R1–R5 and journey J1; the decomposition gives late-fee R1, R2; receipt R3; waiver R5. **R4** (a customer who owes a late fee cannot start a new rental) is in no slice | the design | setup.md step 5 "An entry with no slice is a hole" | assigns R4 to a slice on its own, or drops it silently |
| 6 | J1 crosses all three slices; the merge order is late-fee → receipt → waiver | the design | setup.md step 5 "a journey that crosses slices goes to the slice that merges last" | gives J1 to every slice, or to the first |
| 7 | The user's limit, in the prompt | prompt | setup.md Starting sessions 1 "record it in the register and in status.md" | keeps it only in its head |
| 8 | Empty register | — | SKILL.md Every turn, the seal; setup.md step 2 "Seal the register" | writes no seal, or seals before recording DEC-1 and never reseals |

## A good turn

- `repo/.workflow/nexus/` with all eight files and `sessions/` (empty). `decisions.md` holds DEC-1: "Run at most two sessions at a time — this laptop can't take more."
- `env.md`: the commands from CI (README's `python3 -m unittest` named as running nothing), baseline **10/1/1 at `aefd8c9`**, red test `tests/test_pricing.py::PricingTest::test_weekend_day_rate`, smoke passed, `.workflow/` git-ignored.
- `increment.json`: six entries, all `"passes": false`, `"evidence": null`, each with steps; J1's slices `["waiver"]`; R4's slices `[]`. `confirmed` empty until the user confirms.
- `status.md`: `**Running:** 0 (limit: DEC-1)`, the Register line, three slices not started, waiting on the user.
- The response, a first digest: `Register: DEC-1 · <first 12 hex of sha256(decisions.md)>`; a decision on the red base (hotfix first, or folded into a slice) blocking every session; the increment list to confirm, with R4 named as a hole (new slice, added to one, or dropped); the offer to keep a tracked `RULINGS.md` copy, since the register lives in an ignored folder. No session started, no worktree, branch, commit or code change.

Not graded: the shape of the decision packet; resources.md's scratch names (none are needed before a session starts); whether the slugs carry a prefix.
