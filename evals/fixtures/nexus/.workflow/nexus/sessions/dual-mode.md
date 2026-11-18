# dual-mode — 4.1 dual mode
**Worktree:** ~/wt/dual-mode · **Branch:** corte/4.1-dual-mode · **PR:** #214 · **Scratch:** scratch_dual, port 5443

## tdd — 2026-11-15 18:30
Flag interface done: `DualMode.isOn(slice)`. Migration `db/migrations/V144__dual_mode_flag.sql` adds the `dual_mode_flag` table.

## refactor-review — 2026-11-16 09:50
Two smells noted, both carried: Long Parameter List on `DualReader.compare(...)`, Feature Envy in `FlagCache`.

## devils-advocate prep — 2026-11-16 10:45
Before I start the teardown I need two things.

First, a design question I didn't get to in the design review: does the flag switch per warehouse or once globally? Per warehouse would let ops cut over the pilot warehouse (Tilbury) first and leave the other eleven on legacy; that's another column in dual_mode_flag and a warehouse argument everywhere isOn is called — about 40 call sites — and the rollback plan in the runbook is written for one switch. Global is what we have: one row, and the runbook works as is, but it's all twelve warehouses or none. Moving from global to per-warehouse later means a migration and touching all the call sites again; going back the other way is easy. I'd lean per-warehouse because ops asked about a pilot, but it's not my call.

Second, surcharge rates: Postgres stores rate as NUMERIC(9,4), legacy shows three decimals. 18 surcharge rows differ at the fourth decimal on the scratch load. Proposing we sign that off as **D1** so I can reference it in the compare report.

Also, an owner check for whoever has production access: the nightly sync login (`svc_sync`) on the production ledger2008 instance must not have db_datawriter. I can't verify that from here.

**Status:** devils-advocate · waiting
**Waiting on:** nexus: the switch question and the D1 sign-off
**Next:** devils-advocate teardown
**Head:** `f07aa31` · **PR:** #214
