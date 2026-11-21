# design-adr: answer key (eval 74)

The `base` service plus three accepted ADRs in `docs/adr/` and a glossary in `docs/glossary.md`. No `.workflow/`. The README does not mention either folder: finding them is the skill's **First action** ("ADRs covering that area … treat it as [inferred] and binding"). Kept outside the fixture folder, because runs copy the folder.

| ADR | Settles | What a run does with it |
|---|---|---|
| 0001 rule settings per account | every rule setting comes from `config_source.for_account`; venues carry none | the prompt's per-venue window (Harbour Dining) **contradicts it**: the response says so and puts superseding 0001 to the user as its own question, citing the ADR. Not routed around (a "where does the window live: account / venue override" question that never names 0001), not superseded by the run itself |
| 0002 violations reported together | every code on one `Rejected(codes)`; a rule never raises; a new rule adds a code | **what the caller sees is answered, not asked**: `Rejected` with a new code beside the others, marked **[inferred]**, citing 0002, and recorded that way in the design file's Decisions |
| 0003 rules are pure | a rule sees `(booking, config)` only, no clock; the service gathers inputs | the time of submission is handed in by `BookingService.submit`, not read in the rule: [inferred] from 0003 (graded only as one of the ADRs cited) |

records.md: an [inferred] answer an existing ADR settled is cited, not written as a new ADR; superseding is written only "when the user takes the new branch". So in round 1 **`docs/adr/` is unchanged**: no new ADR, and 0001's status line untouched.

**Expected:** the charter (Solving, Why now, Done looks like, Calibration, Questions); one design file at `.workflow/designs/<YYYYMMDD-HHMM>-<slug>.md`, `in progress`, its path in the response, its Decisions holding the [inferred] 0002 line; at least two of the three ADRs cited; one to three `### Question <q> of ~<n>` blocks in the four sections, one of them the supersede-0001 question on per-venue windows, none of them asking how violations reach the caller (a new exception, alone or beside other codes) without citing 0002; the awaiting line once, after the last question.

Which other questions share the round (the window edge, a default for accounts with no setting, a past slot) is not graded.
