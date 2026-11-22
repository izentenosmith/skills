# brief-archive: answer key (eval 75)

The booking service after the per-account party-size limit shipped: its brief and ledger still sit at `.workflow/brief.md` and `.workflow/ledger.md`, and `.workflow/designs/` holds three designs. The prompt asks for the next build plan and names no design. Kept outside the fixture folder, because runs copy the folder.

| In the fixture | Expected |
|---|---|
| `.workflow/brief.md` — "Per-account party-size limit", `approved`, every criterion ticked `— verified by <test>`, Base set | a finished brief for other work: archived, not overwritten and not left in place |
| `.workflow/ledger.md` — one iteration, F1 REFUTED, ends `### Verdict: GO` | moved **with** the brief, into the same `.workflow/archive/<slug-of-that-brief>/` folder; nothing of it left at `.workflow/ledger.md` |
| Nothing suggests the party-size work is still going (all ticked, GO, the code and its acceptance tests in the repo) | plainly finished: archive without stopping, and say what was archived and why (its title; every criterion ticked; the ledger ends in GO) |
| `designs/20261102-1010-party-size-limit.md`, `resolved` | taken: the current brief's `**Design:**` line names it |
| `designs/20261113-1420-cancellation-cutoff.md`, `resolved`, every decision made | the one free resolved design: the new brief is written from it and its `**Design:**` line names it |
| `designs/20261119-1615-waitlist.md`, `in progress`, the newest | not a candidate: unfinished. Planning from it because it is newest is the trap |
| The approval gate, with nobody to answer (run.py says the user is unavailable) | the new brief stays `draft — awaiting approval`, and the last lines say so |
| The design files and the code | untouched: agent-brief writes a plan and moves the two working files, nothing else |

The new brief's content is graded only lightly (criteria with the tracer bullet first; `CUTOFF_WINDOW` and `cutoff_minutes` carried): eval 1 already grades a brief's shape.
