# Writing the item

A ticket is not the specification. It is a pointer to a shared understanding — the conversation that produced it, the examples, the sketch, the agreed check — and its text has to be good enough that someone who wasn't in the conversation can find their way back to it (Patton, *User Story Mapping*, ch. 6–8). Three parts, every time: the **card** (title and short description), the **conversation** it summarizes (links, examples, decisions), and the **confirmation** (how everyone will know it's done).

## Titles

- **A short verb phrase in the reader's vocabulary** — "Export the stock card to a spreadsheet", "Reject duplicate supplier invoices". A good title is one people can say out loud in a standup; if the team refers to an item by its number, the title is too weak.
- **No prefixes the fields already carry** — no `[Backend]`, no module name, no `BUG:` when the type is Bug.
- **The outcome, not the activity** — "Invoice totals match the sum of their lines", not "Fix invoice calculation".

## Descriptions, by kind

Write in the profile's language and the tool's format (the adapter says whether that's HTML, Markdown or Atlassian Document Format). The sections below are the content; render them as headings or bold labels.

### Story — new capability

- **Who** — the person or role who benefits. Not "as a developer" or "as the product owner": if the beneficiary is the team, it's a task.
- **What** — what they can do once this ships, in their words.
- **Why** — the outcome it serves; for larger items, the metric that will show it worked.
- **Acceptance criteria** — what will be checked to confirm it's done, as concrete examples (this input → that result), not adjectives.
- **Demo** — how it will be shown at review. Answering this often surfaces a missing piece, such as realistic test data.
- **Out of scope** — what a reader might assume is included and isn't.
- **Open questions** — each with who will answer it.

The "As a … I want … so that …" sentence is optional — a conversation starter, not a format to enforce.

### Bug — current behavior is wrong

- **Context** — what the system is supposed to do here.
- **Actual** — what happens, with the exact input, account type, environment and time.
- **Expected** — what should happen.
- **Steps to reproduce** — numbered, minimal, starting from a state anyone can reach.
- **Impact** — who is affected and how many, if known; data written wrongly says so explicitly.
- **Evidence** — log lines, request ids, screenshots (redacted).
- **Technical notes** — only what's known, marked as known or suspected.

### Spike — research with no code deliverable

- **Question** — the one thing this will find out.
- **Why now** — the decision waiting on the answer.
- **Time box** — hours or days, after which it stops whatever it found.
- **Output** — a written answer, a prototype to throw away, a recommendation. Not production code.

### Task — technical work with no direct user outcome

- **What changes**, **why it matters** (who cares, even indirectly), and **how it's verified**. Development steps inside a story belong as child tasks of that story, not as backlog items of their own.

### Incident — a production failure

Opened **when the failure starts**, not after it's fixed — the tracker's created time is otherwise meaningless for restore-time metrics. Carries the incident label from [labels.md](labels.md).

- **Symptom and severity**, **start time** (from evidence, UTC), **detected by**, **current status**, and a link to the incident log. Kept short; the log is the record.

### Follow-up — owed by a hotfix, an incident or a post-mortem

- **Outcome** — an observable property of the system, not an instruction to people ("a migration that rewrites more than N rows requires a dry-run artifact in review", not "be careful with migrations").
- **Origin** — the hotfix, incident or post-mortem, with its link and the contributing factor it answers.
- **Action type** — mitigate, prevent or process ([labels.md](labels.md)).
- **What's in place meanwhile**, **owner**, **due date**.

## Finished work — documenting retroactively

When the work already shipped, the description ends with its trace ([traceability.md](traceability.md)): commits, PR, and scope (`git show --stat --format='' <sha> | tail -1`). A feature template goes on features — "Actual behavior" doesn't apply to something that didn't exist.

## Closing

Two separate questions: **did we build what we agreed?** (the acceptance criteria, checked) and **now that we see it, should it change?** A change discovered at review is a **new item**, linked to this one — not a reopened one, which erases when the original was done.
