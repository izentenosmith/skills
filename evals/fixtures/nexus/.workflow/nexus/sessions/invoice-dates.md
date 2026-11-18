# invoice-dates — 4.3 invoice date fix
**Worktree:** ~/wt/invoice-dates · **Branch:** corte/4.3-invoice-dates · **PR:** none yet · **Scratch:** scratch_dates, port 5445

## architect-deep-dive — 2026-11-16 10:30
Design file `.workflow/designs/20261116-1002-invoice-date-fix.md`. Charter written. Question 2 of ~6:

legacy stores issued_at in the server's local time and every report shifts it again on display, so about 3% of historical invoices show the previous day. Should the migrated issued_at reproduce what legacy shows (shifted), or be corrected to the true UTC instant? Correcting is cleaner and is what an auditor would want; reproducing keeps the new screens identical to the old ones. Which do we want?

**Status:** architect-deep-dive · waiting
**Waiting on:** nexus: question 2
**Next:** question 3 (historical invoices before 2000)
**Head:** `7c1e9a2` · **PR:** none yet
