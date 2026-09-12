# Benchmark — six-stage pipeline

`delta` = assertions this session's edits added. `cap` = does the stage work at all.

| eval | from | n | delta (mean ± sd) | delta base | gain | cap | cap base |
|---|---|---|---|---|---|---|---|
| 0-architect-charter-and-options | i1 | 3 | 0.97 ± 0.05 | 0.00 | +0.97 | 1.00 | 1.00 |
| 1-brief-ordered-criteria | i1 | 3 | 1.00 ± 0.00 | 0.00 | +1.00 | 1.00 | 0.86 |
| 2-tdd-reads-brief-vertical | i1 | 3 | 1.00 ± 0.00 | 0.50 | +0.50 | 0.78 | 0.83 |
| 3-refactor-promotes-noted-smell | i2 | 3 | 1.00 ± 0.00 | 0.14 | +0.86 | 0.75 | 0.75 |
| 4-teardown-finds-vacuous-test | i2 | 3 | 0.92 ± 0.14 | 0.25 | +0.67 | 1.00 | 1.00 |
| 5-verdict-cuts-and-slices | i2 | 3 | 1.00 ± 0.00 | 0.40 | +0.60 | 1.00 | 0.83 |

**Delta — current 0.98 vs baseline 0.22**
**Capability — current 0.92 vs baseline 0.88**

## Delta assertions the baseline also passed (still non-discriminating)

**eval-2-tdd-reads-brief-vertical**
- brief revised in place when reality contradicted it

**eval-3-refactor-promotes-noted-smell**
- prior venue_id smell explicitly left, not silently dropped

**eval-4-teardown-finds-vacuous-test**
- does not re-report the refuted party-size finding

**eval-5-verdict-cuts-and-slices**
- F4 struck as an already-refuted repeat, citing the prior verdict
- verdicts written back to the ledger

## Delta assertions that varied across repetitions

**eval-0-architect-charter-and-options**
- charter estimates a question count (2/3)

**eval-4-teardown-finds-vacuous-test**
- unproven findings name what would settle them (2/3)
