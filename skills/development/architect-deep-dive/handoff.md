# Handoff — closing a resolved design

> Companion to [architect-deep-dive](SKILL.md). Read it when every dimension in the termination gate has reached one of its three end states, before you write the closing summary.

## The summary

Restate the **charter** — unchanged if the design still serves the problem you opened with, explicitly amended if the questions moved it — then summarize dimension-by-dimension. For each decision, keep the option chosen and the one-line reason: a decision whose rationale is lost gets re-argued the first time someone finds it inconvenient.

Beyond the decisions, the summary carries one block per section of the design file, each holding what that section's template line names:

- **Security**, when the trigger fired. agent-brief turns each item into an acceptance criterion and a test; a security decision buried in prose never gets one.
- **Operability** — what must not break and for whom, what gets logged or measured, the flag or backfill and its order relative to the deploy, and how the change is undone. Nothing downstream fails when these go missing, which is why they do; agent-brief turns each into a criterion where a test can see it and a ship-checklist item where it can't. A dimension that ended N/A says so in one line.
- **Decomposition** — on a large effort the increments, what each delivers, and their order.
- **Deferred** — agent-brief carries these as constraints, not as work.
- **Records** — ADRs and glossary terms added or changed, for agent-brief to cite. None written is a valid answer; say so.

Close with **the count**: how many questions were asked against the estimate, and where the estimate moved.

## The design file

Bring the design file up to date with that summary and set its `**Status:** resolved`. The file, not this conversation, is what agent-brief reads.

## The closing prompt

> The design is resolved across all dimensions — <resolved> questions resolved, <deferred> deferred — and written to `<the design file's path>`. Run **`agent-brief`** next to turn these decisions into the pure-text plan TDD builds from.

Where the user has the skills repo, its harness can run the rest of the pipeline from that file without you: `python3 <the skills repo>/harness/pipeline.py --repo . --design <the design file's path> --test-cmd "<the suite>"` writes the brief, the acceptance tests and the code, then runs the closing loop to GO or ESCALATED. `--approve-brief` records the user's approval at launch and `--pause-at-brief` stops for it; with neither, the run builds on an unapproved brief and says so. Tell the user the command; do not launch it yourself unless they ask — it is an unattended run that writes and commits code, and starting it is their call.
